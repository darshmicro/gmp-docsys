from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import io

from ..database import get_db
from ..auth import get_current_user, require_permission
from ..audit import log_audit
from ..models import (
    StorageRoom, Rack, SubRack, Shelf, Position, DocumentCopy, Document,
)
from ..services.location import refresh_position_cache, full_location_breadcrumb
from ..templating import templates

router = APIRouter()


def _ip(request: Request):
    return request.client.host if request.client else None


# ----------------------------------------------------------------- ROOMS --

@router.get("/storage")
def storage_home(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    rooms = db.query(StorageRoom).filter(StorageRoom.is_active == True).all()  # noqa: E712
    return templates.TemplateResponse("storage_rooms.html", {"request": request, "user": user, "rooms": rooms})


@router.get("/storage/rooms/new")
def new_room_form(request: Request, user=Depends(require_permission("MASTER_EDIT"))):
    return templates.TemplateResponse("room_form.html", {"request": request, "user": user, "room": None})


@router.post("/storage/rooms/new")
def create_room(request: Request, db: Session = Depends(get_db),
                 user=Depends(require_permission("MASTER_EDIT")),
                 code: str = Form(...), name: str = Form(...), building: str = Form(None),
                 floor: str = Form(None), area: str = Form(None)):
    room = StorageRoom(code=code, name=name, building=building, floor=floor, area=area, created_by=user.full_name)
    db.add(room)
    db.commit()
    db.refresh(room)
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Master Data", action="CREATE", record_type="StorageRoom", record_id=room.id,
               new_value=f"{code} - {name}")
    return RedirectResponse(url="/storage", status_code=303)


@router.get("/storage/rooms/{room_id}/edit")
def edit_room_form(room_id: int, request: Request, db: Session = Depends(get_db),
                    user=Depends(require_permission("MASTER_EDIT"))):
    room = db.query(StorageRoom).filter(StorageRoom.id == room_id).first()
    return templates.TemplateResponse("room_form.html", {"request": request, "user": user, "room": room})


@router.post("/storage/rooms/{room_id}/edit")
def edit_room(room_id: int, request: Request, db: Session = Depends(get_db),
              user=Depends(require_permission("MASTER_EDIT")),
              code: str = Form(...), name: str = Form(...), building: str = Form(None),
              floor: str = Form(None), area: str = Form(None), is_active: bool = Form(False)):
    room = db.query(StorageRoom).filter(StorageRoom.id == room_id).first()
    old = f"{room.code} - {room.name} (active={room.is_active})"
    room.code, room.name, room.building, room.floor, room.area = code, name, building, floor, area
    room.is_active = is_active
    room.modified_by = user.full_name
    room.modified_date = datetime.utcnow()
    db.commit()
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Master Data", action="UPDATE", record_type="StorageRoom", record_id=room_id,
               old_value=old, new_value=f"{code} - {name} (active={is_active})")
    return RedirectResponse(url="/storage", status_code=303)


@router.get("/storage/rooms/{room_id}/documents")
def documents_in_room(room_id: int, request: Request, db: Session = Depends(get_db),
                       user=Depends(require_permission("MASTER_EDIT"))):
    """List of documents kept in one storage room — Doc Cell Admin only."""
    room = db.query(StorageRoom).filter(StorageRoom.id == room_id).first()
    copies = (
        db.query(DocumentCopy)
        .join(Position, DocumentCopy.current_position_id == Position.id)
        .join(Shelf, Position.shelf_id == Shelf.id)
        .join(SubRack, Shelf.sub_rack_id == SubRack.id)
        .join(Rack, SubRack.rack_id == Rack.id)
        .filter(Rack.room_id == room_id)
        .all()
    )
    return templates.TemplateResponse("room_documents.html", {
        "request": request, "user": user, "room": room, "copies": copies,
    })


# ------------------------------------------------------------ STORAGE MAP --
# Add/edit for each level of Room -> Rack -> Sub-Rack -> Shelf -> Position.

@router.get("/storage/map")
def storage_map_manage(request: Request, db: Session = Depends(get_db), user=Depends(require_permission("MASTER_EDIT"))):
    rooms = db.query(StorageRoom).filter(StorageRoom.is_active == True).all()  # noqa: E712
    tree = []
    for room in rooms:
        racks = db.query(Rack).filter(Rack.room_id == room.id, Rack.is_active == True).all()  # noqa: E712
        rack_nodes = []
        for rack in racks:
            sub_racks = db.query(SubRack).filter(SubRack.rack_id == rack.id, SubRack.is_active == True).all()  # noqa: E712
            sub_rack_nodes = []
            for sr in sub_racks:
                shelves = db.query(Shelf).filter(Shelf.sub_rack_id == sr.id, Shelf.is_active == True).all()  # noqa: E712
                shelf_nodes = []
                for sh in shelves:
                    positions = db.query(Position).filter(Position.shelf_id == sh.id, Position.is_active == True).all()  # noqa: E712
                    shelf_nodes.append({"shelf": sh, "positions": positions})
                sub_rack_nodes.append({"sub_rack": sr, "shelves": shelf_nodes})
            rack_nodes.append({"rack": rack, "sub_racks": sub_rack_nodes})
        tree.append({"room": room, "racks": rack_nodes})
    return templates.TemplateResponse("storage_map_manage.html", {"request": request, "user": user, "tree": tree})


@router.get("/storage/racks/new")
def new_rack_form(request: Request, room_id: int, db: Session = Depends(get_db),
                   user=Depends(require_permission("MASTER_EDIT"))):
    room = db.query(StorageRoom).filter(StorageRoom.id == room_id).first()
    return templates.TemplateResponse("rack_form.html", {"request": request, "user": user, "room": room, "rack": None})


@router.post("/storage/racks/new")
def create_rack(request: Request, db: Session = Depends(get_db),
                 user=Depends(require_permission("MASTER_EDIT")),
                 room_id: int = Form(...), rack_number: str = Form(...), description: str = Form(None)):
    rack = Rack(room_id=room_id, rack_number=rack_number, description=description, created_by=user.full_name)
    db.add(rack)
    db.commit()
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Master Data", action="CREATE", record_type="Rack", record_id=rack.id,
               new_value=rack_number)
    return RedirectResponse(url="/storage/map", status_code=303)


@router.get("/storage/racks/{rack_id}/edit")
def edit_rack_form(rack_id: int, request: Request, db: Session = Depends(get_db),
                    user=Depends(require_permission("MASTER_EDIT"))):
    rack = db.query(Rack).filter(Rack.id == rack_id).first()
    return templates.TemplateResponse("rack_form.html", {"request": request, "user": user, "room": rack.room, "rack": rack})


@router.post("/storage/racks/{rack_id}/edit")
def edit_rack(rack_id: int, request: Request, db: Session = Depends(get_db),
              user=Depends(require_permission("MASTER_EDIT")),
              rack_number: str = Form(...), description: str = Form(None), is_active: bool = Form(False)):
    rack = db.query(Rack).filter(Rack.id == rack_id).first()
    old = f"{rack.rack_number} (active={rack.is_active})"
    rack.rack_number, rack.description, rack.is_active = rack_number, description, is_active
    rack.modified_by = user.full_name
    rack.modified_date = datetime.utcnow()
    db.commit()
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Master Data", action="UPDATE", record_type="Rack", record_id=rack_id,
               old_value=old, new_value=f"{rack_number} (active={is_active})")
    return RedirectResponse(url="/storage/map", status_code=303)


@router.get("/storage/subracks/new")
def new_subrack_form(request: Request, rack_id: int, db: Session = Depends(get_db),
                      user=Depends(require_permission("MASTER_EDIT"))):
    rack = db.query(Rack).filter(Rack.id == rack_id).first()
    return templates.TemplateResponse("subrack_form.html", {"request": request, "user": user, "rack": rack, "sub_rack": None})


@router.post("/storage/subracks/new")
def create_subrack(request: Request, db: Session = Depends(get_db),
                    user=Depends(require_permission("MASTER_EDIT")),
                    rack_id: int = Form(...), sub_rack_number: str = Form(...), capacity: int = Form(None)):
    sr = SubRack(rack_id=rack_id, sub_rack_number=sub_rack_number, capacity=capacity, created_by=user.full_name)
    db.add(sr)
    db.commit()
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Master Data", action="CREATE", record_type="SubRack", record_id=sr.id,
               new_value=sub_rack_number)
    return RedirectResponse(url="/storage/map", status_code=303)


@router.get("/storage/subracks/{sub_rack_id}/edit")
def edit_subrack_form(sub_rack_id: int, request: Request, db: Session = Depends(get_db),
                       user=Depends(require_permission("MASTER_EDIT"))):
    sr = db.query(SubRack).filter(SubRack.id == sub_rack_id).first()
    return templates.TemplateResponse("subrack_form.html", {"request": request, "user": user, "rack": sr.rack, "sub_rack": sr})


@router.post("/storage/subracks/{sub_rack_id}/edit")
def edit_subrack(sub_rack_id: int, request: Request, db: Session = Depends(get_db),
                  user=Depends(require_permission("MASTER_EDIT")),
                  sub_rack_number: str = Form(...), capacity: int = Form(None), is_active: bool = Form(False)):
    sr = db.query(SubRack).filter(SubRack.id == sub_rack_id).first()
    old = f"{sr.sub_rack_number} (active={sr.is_active})"
    sr.sub_rack_number, sr.capacity, sr.is_active = sub_rack_number, capacity, is_active
    sr.modified_by = user.full_name
    sr.modified_date = datetime.utcnow()
    db.commit()
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Master Data", action="UPDATE", record_type="SubRack", record_id=sub_rack_id,
               old_value=old, new_value=f"{sub_rack_number} (active={is_active})")
    return RedirectResponse(url="/storage/map", status_code=303)


@router.get("/storage/shelves/new")
def new_shelf_form(request: Request, sub_rack_id: int, db: Session = Depends(get_db),
                    user=Depends(require_permission("MASTER_EDIT"))):
    sr = db.query(SubRack).filter(SubRack.id == sub_rack_id).first()
    return templates.TemplateResponse("shelf_form.html", {"request": request, "user": user, "sub_rack": sr, "shelf": None})


@router.post("/storage/shelves/new")
def create_shelf(request: Request, db: Session = Depends(get_db),
                  user=Depends(require_permission("MASTER_EDIT")),
                  sub_rack_id: int = Form(...), shelf_number: str = Form(...), capacity: int = Form(None)):
    shelf = Shelf(sub_rack_id=sub_rack_id, shelf_number=shelf_number, capacity=capacity, created_by=user.full_name)
    db.add(shelf)
    db.commit()
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Master Data", action="CREATE", record_type="Shelf", record_id=shelf.id,
               new_value=shelf_number)
    return RedirectResponse(url="/storage/map", status_code=303)


@router.get("/storage/shelves/{shelf_id}/edit")
def edit_shelf_form(shelf_id: int, request: Request, db: Session = Depends(get_db),
                     user=Depends(require_permission("MASTER_EDIT"))):
    shelf = db.query(Shelf).filter(Shelf.id == shelf_id).first()
    return templates.TemplateResponse("shelf_form.html", {"request": request, "user": user, "sub_rack": shelf.sub_rack, "shelf": shelf})


@router.post("/storage/shelves/{shelf_id}/edit")
def edit_shelf(shelf_id: int, request: Request, db: Session = Depends(get_db),
               user=Depends(require_permission("MASTER_EDIT")),
               shelf_number: str = Form(...), capacity: int = Form(None), is_active: bool = Form(False)):
    shelf = db.query(Shelf).filter(Shelf.id == shelf_id).first()
    old = f"{shelf.shelf_number} (active={shelf.is_active})"
    shelf.shelf_number, shelf.capacity, shelf.is_active = shelf_number, capacity, is_active
    shelf.modified_by = user.full_name
    shelf.modified_date = datetime.utcnow()
    db.commit()
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Master Data", action="UPDATE", record_type="Shelf", record_id=shelf_id,
               old_value=old, new_value=f"{shelf_number} (active={is_active})")
    return RedirectResponse(url="/storage/map", status_code=303)


@router.get("/storage/positions/new")
def new_position_form(request: Request, shelf_id: int, db: Session = Depends(get_db),
                       user=Depends(require_permission("MASTER_EDIT"))):
    shelf = db.query(Shelf).filter(Shelf.id == shelf_id).first()
    return templates.TemplateResponse("position_form.html", {"request": request, "user": user, "shelf": shelf, "position": None})


@router.post("/storage/positions/new")
def create_position(request: Request, db: Session = Depends(get_db),
                     user=Depends(require_permission("MASTER_EDIT")),
                     shelf_id: int = Form(...), position_number: str = Form(...)):
    pos = Position(shelf_id=shelf_id, position_number=position_number, created_by=user.full_name)
    db.add(pos)
    db.commit()
    db.refresh(pos)
    refresh_position_cache(db, pos.id)
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Master Data", action="CREATE", record_type="Position", record_id=pos.id,
               new_value=pos.location_code)
    return RedirectResponse(url="/storage/map", status_code=303)


@router.get("/storage/positions/{position_id}/edit")
def edit_position_form(position_id: int, request: Request, db: Session = Depends(get_db),
                        user=Depends(require_permission("MASTER_EDIT"))):
    pos = db.query(Position).filter(Position.id == position_id).first()
    return templates.TemplateResponse("position_form.html", {"request": request, "user": user, "shelf": pos.shelf, "position": pos})


@router.post("/storage/positions/{position_id}/edit")
def edit_position(position_id: int, request: Request, db: Session = Depends(get_db),
                   user=Depends(require_permission("MASTER_EDIT")),
                   position_number: str = Form(...), is_active: bool = Form(False)):
    pos = db.query(Position).filter(Position.id == position_id).first()
    old = f"{pos.location_code} (active={pos.is_active})"
    pos.position_number, pos.is_active = position_number, is_active
    pos.modified_by = user.full_name
    pos.modified_date = datetime.utcnow()
    db.commit()
    refresh_position_cache(db, pos.id)
    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Master Data", action="UPDATE", record_type="Position", record_id=position_id,
               old_value=old, new_value=f"{pos.location_code} (active={is_active})")
    return RedirectResponse(url="/storage/map", status_code=303)


# ------------------------------------------------------- LOCATION LOOKUPS --

@router.get("/storage/location/{position_id}/documents")
def documents_at_location(position_id: int, request: Request, db: Session = Depends(get_db),
                           user=Depends(require_permission("MASTER_VIEW"))):
    """List of documents kept at one storage location — open to ALL roles
    (every role holds MASTER_VIEW), unlike the room-level listing above
    which is Doc Cell Admin only."""
    pos = db.query(Position).filter(Position.id == position_id).first()
    breadcrumb = full_location_breadcrumb(db, position_id) if pos else None
    copies = db.query(DocumentCopy).filter(DocumentCopy.current_position_id == position_id).all()
    return templates.TemplateResponse("location_documents.html", {
        "request": request, "user": user, "position": pos, "breadcrumb": breadcrumb, "copies": copies,
    })


@router.get("/storage/map/lookup")
def location_lookup(request: Request, db: Session = Depends(get_db), user=Depends(require_permission("MASTER_VIEW"))):
    """Simple picker: choose a location code from a dropdown to jump to its document list."""
    positions = db.query(Position).filter(Position.is_active == True).order_by(Position.location_code).all()  # noqa: E712
    return templates.TemplateResponse("location_lookup.html", {"request": request, "user": user, "positions": positions})


# ---------------------------------------------------------------- EXPORT --

@router.get("/storage/export/document-locations.xlsx")
def export_document_locations(request: Request, db: Session = Depends(get_db),
                               user=Depends(require_permission("REPORTS_VIEW"))):
    """Exports current document/copy locations to Excel (Section 21/37)."""
    from openpyxl import Workbook

    log_audit(db, user_id=user.id, user_name=user.full_name, ip_address=_ip(request),
               module="Reports", action="EXPORT", record_type="DocumentLocations",
               reason="Document location Excel export")

    wb = Workbook()
    ws = wb.active
    ws.title = "Document Locations"
    headers = ["Document Number", "Title", "Revision", "Copy No.", "Copy Status",
               "Location Code", "Room", "Rack", "Sub-Rack", "Shelf", "Position", "Current Custodian"]
    ws.append(headers)

    copies = db.query(DocumentCopy).all()
    for c in copies:
        doc = db.query(Document).filter(Document.id == c.document_id).first()
        if c.current_position_id:
            b = full_location_breadcrumb(db, c.current_position_id)
            room, rack, sub_rack, shelf, position, loc_code = (
                b["room"], b["rack"], b["sub_rack"], b["shelf"], b["position"], b["location_code"])
        else:
            room = rack = sub_rack = shelf = position = loc_code = ""
        custodian = c.current_custodian.full_name if c.current_custodian else ""
        ws.append([doc.document_number, doc.title, doc.revision_number, c.copy_number, c.copy_status,
                   loc_code, room, rack, sub_rack, shelf, position, custodian])

    for col_cells in ws.columns:
        length = max(len(str(cell.value)) if cell.value else 0 for cell in col_cells)
        ws.column_dimensions[col_cells[0].column_letter].width = min(max(length + 2, 10), 40)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"document_locations_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
