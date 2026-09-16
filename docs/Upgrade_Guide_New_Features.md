# Upgrade Guide — Adding the New Facilities

Good news: **no database schema changes are needed.** Every new feature maps
onto tables that already existed in your database (SystemConfig for company
settings, Department/DocumentType for master data, the existing storage
hierarchy tables, etc.). This is a **code-only upgrade**.

## Procedure

1. **Stop the running app** (Ctrl+C, or stop your service/process manager).

2. **Back up your current `gmpdoctrack.db`** (or your SQL Server database, if
   you're already on production) before touching anything — standard
   precaution, not because this upgrade needs it.

3. **Replace the application code**, keeping your database file in place:
   ```bash
   # from the folder containing your OLD gmp-docsystem/
   mv gmp-docsystem/gmpdoctrack.db /tmp/gmpdoctrack.db.bak   # save your data
   rm -rf gmp-docsystem/app                                    # remove old code
   unzip -o gmp-docsystem.zip                                  # unpack the new build
   mv /tmp/gmpdoctrack.db.bak gmp-docsystem/gmpdoctrack.db    # restore your data
   ```
   (If you're on SQL Server in production, you only need to replace the
   `app/` folder and `requirements.txt` — the database itself needs no
   changes at all.)

4. **Reinstall dependencies** (unchanged, but do this to be safe):
   ```bash
   cd gmp-docsystem
   pip install -r requirements.txt
   ```

5. **Restart the app:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

Your existing users, documents, storage hierarchy, and audit trail are
untouched. The new admin/master-data/storage-map pages will simply appear
in the sidebar the next time you log in.

## What's new and where to find it

| Facility | Role required | Location |
|---|---|---|
| Company name & logo | System Admin | Sidebar → **Company Settings** |
| Add new user | System Admin | Sidebar → **Users & Roles** → *+ Add New User* |
| Edit a user's role (add/remove) | System Admin | Sidebar → **Users & Roles** (✕ button removes, dropdown adds) |
| Add/edit storage room | Doc Cell Admin | Sidebar → **Storage Rooms** → *+ Add* / *Edit* |
| Documents in one storage room | Doc Cell Admin | Storage Rooms → *Documents Here* link per room |
| Add/edit storage map (rack/sub-rack/shelf/position) | Doc Cell Admin | Sidebar → **Manage Storage Map** |
| Documents at one storage location | **All roles** | Sidebar → **Find by Location**, or click any location code |
| Add/edit department | Doc Cell Admin | Sidebar → **Departments** |
| Add/edit document type | Doc Cell Admin | Sidebar → **Document Types** |
| Room/location picker at document registration | Doc Cell Admin / Sysadmin (whoever has DOC_CREATE) | Sidebar → **Register Document** — cascading Room→Rack→Sub-Rack→Shelf→Position dropdowns, optional at registration time |
| Export document locations to Excel | Anyone with REPORTS_VIEW (Sysadmin, Doc Cell Admin, Doc Cell User) | Sidebar → **Export Locations (Excel)** |
| Issue with to-whom + purpose | Sysadmin, Doc Cell Admin, Doc Cell User | Document detail page → *Issue* button (unchanged, already had this) |
| Transfer to another location | Sysadmin, Doc Cell Admin | Document detail page → *Transfer* button — now uses the same cascading room/rack/sub-rack/shelf/position picker instead of a flat list |

## One-time setup after upgrading

- **Set your company name/logo**: log in as a Sysadmin, go to Company
  Settings, and fill it in. Until you do, the header just shows the generic
  "GMP Document Storage & Tracking System" title — this is expected, not a
  bug.
- **Nothing else requires setup** — departments, document types, and the
  storage hierarchy from your existing data (or the demo seed data) will
  show up in the new management screens exactly as they already existed.

## What I verified before sending this to you

I ran a live end-to-end test of every item above against a fresh copy of
this build: logged in, saved a company name and confirmed it appeared in
the header immediately, created a new local user and assigned/removed a
role, added a new rack to the storage map, registered a new document with
an initial location selected through the cascading picker, confirmed it
appeared correctly on the document detail page, transferred it to a
different location and confirmed the location code updated correctly,
pulled up the documents-in-a-room view and documents-at-a-location view
(both showed the right document), and downloaded the Excel export and
opened it programmatically to confirm the data was accurate. Everything
passed.
