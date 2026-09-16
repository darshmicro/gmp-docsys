"""
Builds the canonical Storage Location Code (Section 8/23):

    DR01-R04-SR02-S03-P05

from the Room -> Rack -> SubRack -> Shelf -> Position hierarchy, and keeps
Position.location_code (a denormalized cache for fast search/indexing) in
sync. The hierarchy itself remains fully relational (each level has its own
FK), per Section 23's "do not store location only as free text" requirement
— this cache exists purely to make Section 35's 2-3 second search target
easy to hit without a 5-way join on every query.
"""
from sqlalchemy.orm import Session
from ..models import Position, Shelf, SubRack, Rack, StorageRoom


def storage_hierarchy_json(db: Session) -> dict:
    """Builds the full active Room -> Rack -> Sub-Rack -> Shelf -> Position
    tree as plain nested dicts, for embedding as JSON in a page so cascading
    dropdowns (document registration, add-copy, transfer) can filter
    client-side without a round trip per level."""
    rooms = db.query(StorageRoom).filter(StorageRoom.is_active == True).all()  # noqa: E712
    tree = {"rooms": []}
    for room in rooms:
        racks = db.query(Rack).filter(Rack.room_id == room.id, Rack.is_active == True).all()  # noqa: E712
        room_node = {"id": room.id, "label": f"{room.code} — {room.name}", "racks": []}
        for rack in racks:
            sub_racks = db.query(SubRack).filter(SubRack.rack_id == rack.id, SubRack.is_active == True).all()  # noqa: E712
            rack_node = {"id": rack.id, "label": rack.rack_number, "sub_racks": []}
            for sr in sub_racks:
                shelves = db.query(Shelf).filter(Shelf.sub_rack_id == sr.id, Shelf.is_active == True).all()  # noqa: E712
                sr_node = {"id": sr.id, "label": sr.sub_rack_number, "shelves": []}
                for sh in shelves:
                    positions = db.query(Position).filter(Position.shelf_id == sh.id, Position.is_active == True).all()  # noqa: E712
                    sh_node = {"id": sh.id, "label": sh.shelf_number,
                               "positions": [{"id": p.id, "label": p.position_number, "code": p.location_code}
                                             for p in positions]}
                    sr_node["shelves"].append(sh_node)
                rack_node["sub_racks"].append(sr_node)
            room_node["racks"].append(rack_node)
        tree["rooms"].append(room_node)
    return tree


def build_location_code(db: Session, position_id: int) -> str:
    pos = db.query(Position).filter(Position.id == position_id).one()
    shelf = db.query(Shelf).filter(Shelf.id == pos.shelf_id).one()
    sub_rack = db.query(SubRack).filter(SubRack.id == shelf.sub_rack_id).one()
    rack = db.query(Rack).filter(Rack.id == sub_rack.rack_id).one()
    room = db.query(StorageRoom).filter(StorageRoom.id == rack.room_id).one()

    room_part = room.code.replace("-", "")
    return f"{room_part}-{rack.rack_number}-{sub_rack.sub_rack_number}-{shelf.shelf_number}-{pos.position_number}"


def refresh_position_cache(db: Session, position_id: int, commit: bool = True) -> str:
    code = build_location_code(db, position_id)
    pos = db.query(Position).filter(Position.id == position_id).one()
    pos.location_code = code
    if commit:
        db.commit()
    return code


def full_location_breadcrumb(db: Session, position_id: int) -> dict:
    pos = db.query(Position).filter(Position.id == position_id).one()
    shelf = db.query(Shelf).filter(Shelf.id == pos.shelf_id).one()
    sub_rack = db.query(SubRack).filter(SubRack.id == shelf.sub_rack_id).one()
    rack = db.query(Rack).filter(Rack.id == sub_rack.rack_id).one()
    room = db.query(StorageRoom).filter(StorageRoom.id == rack.room_id).one()
    return {
        "room": room.name,
        "room_code": room.code,
        "rack": rack.rack_number,
        "sub_rack": sub_rack.sub_rack_number,
        "shelf": shelf.shelf_number,
        "position": pos.position_number,
        "location_code": pos.location_code or build_location_code(db, position_id),
    }


def positions_under_room(db: Session, room_id: int) -> list[int]:
    ids = []
    for rack in db.query(Rack).filter(Rack.room_id == room_id).all():
        ids.extend(positions_under_rack(db, rack.id))
    return ids


def positions_under_rack(db: Session, rack_id: int) -> list[int]:
    ids = []
    for sub_rack in db.query(SubRack).filter(SubRack.rack_id == rack_id).all():
        ids.extend(positions_under_subrack(db, sub_rack.id))
    return ids


def positions_under_subrack(db: Session, sub_rack_id: int) -> list[int]:
    ids = []
    for shelf in db.query(Shelf).filter(Shelf.sub_rack_id == sub_rack_id).all():
        ids.extend([p.id for p in db.query(Position).filter(Position.shelf_id == shelf.id).all()])
    return ids


def positions_under_shelf(db: Session, shelf_id: int) -> list[int]:
    return [p.id for p in db.query(Position).filter(Position.shelf_id == shelf_id).all()]


def refresh_positions_and_copies(db: Session, position_ids: list[int]) -> None:
    """
    Call this after editing any level of the hierarchy (rack number, sub-rack
    number, shelf number) whose change would alter the derived location code
    for positions underneath it. Recomputes Position.location_code for every
    affected position AND keeps DocumentCopy.current_location_code (the
    denormalized cache used for fast search) in sync, so a room/rack rename
    never leaves stale codes behind on documents already stored there.
    """
    from ..models import DocumentCopy
    for pid in position_ids:
        code = refresh_position_cache(db, pid, commit=False)
        for copy in db.query(DocumentCopy).filter(DocumentCopy.current_position_id == pid).all():
            copy.current_location_code = code
    db.commit()

