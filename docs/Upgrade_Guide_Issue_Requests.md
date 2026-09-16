# Upgrade Guide — Issue Requests, Audit Trail Names, and the New Look

Unlike every previous update, **this one genuinely needs a small database
change** — a new table, `issue_requests`. Everything else in this update
(the visual redesign, the audit trail fix, the Issued Documents report) is
code-only, same as always.

## What's new

- **A completely new look** — same layout and navigation you already
  know, restyled with a deeper color palette and genuinely tactile 3D
  buttons (they visibly press down when clicked).
- **Audit trail entries now show real names**, not raw ID numbers — e.g.
  "ISSUED to Arjun Rao (local:docuser)" instead of "ISSUED to user 3".
  This applies to issue, return, and the new approval actions.
- **An "Issued Documents" report** (sidebar → Issued Documents) — every
  currently-issued copy in one list: who has it, why, when it's due, and
  whether it's overdue.
- **Viewers can now request a document be issued to them**, instead of
  being unable to get a copy issued at all. A Doc Cell User or Admin sees
  the request, and can approve it (which issues the copy directly to the
  original requester, not to whoever approved it) or reject it with a
  reason.

## Upgrading an EXISTING installation (you already have real data)

1. **Back up first** — either your SQLite file, or a SQL Server backup
   per `docs/Backup_Setup_Guide.md` if you're already on production. This
   step should always come first, on principle, even though the upgrade
   below is designed to be safe.
2. **Stop the running application.**
3. Replace the application code the same way as every previous update —
   unzip the new version over your existing `gmp-docsystem` folder,
   keeping your database file (or your SQL Server connection settings)
   exactly as they are. Do **not** copy over any file you've personally
   edited with real values (like a filled-in `start_server.bat`) — keep
   your own edited copy.
4. **Run the one-time upgrade script**, using the exact same connection
   settings you already use for everything else (activate this
   project's virtual environment first — see "Python Version & Virtual
   Environment" in the installation guide if you haven't set this up):
   ```
   venv\Scripts\activate
   call deployment\windows\set_db_env.bat
   python upgrade_add_issue_requests.py
   ```
   (Skip the `call` line if you're on the local SQLite file rather than
   SQL Server — it's only needed to load your SQL Server connection
   details.)
   This adds the new table and the two new permissions, and grants them
   to the right roles. It checks before doing anything, so it's safe to
   run even if you're not sure whether it's already been done — running
   it twice does nothing the second time.
5. Restart the application.
6. Confirm it worked: log in as a Viewer, open any available document,
   and confirm you see a **Request Issue** button. Log in as a Doc Cell
   User and confirm **Issue Requests** appears in the sidebar with that
   pending request visible.

## Starting completely fresh (new installation, no data yet)

Nothing extra to do — `python -m app.seed` already includes everything
in this update. Just follow the normal installation guide from the
start.

## What I verified before sending this to you

I didn't just write the upgrade script and assume it works — I built a
simulated "old" database (seeded with only last round's permissions and
without the new table, to genuinely stand in for your real database as
it exists today), ran the upgrade script against it, and confirmed:
existing user accounts were completely untouched, the new table was
added, the two new permissions were created, and each role received
exactly the right grant (Viewer got the ability to request; Doc Cell
User, Doc Cell Admin, and Sysadmin all got the ability to approve).
Running the script a second time afterward correctly did nothing further
— every step reported "already exists — skipping."

I then ran the entire feature live end-to-end on a fresh installation: a
Viewer requested a document, a Doc Cell User approved it, and I confirmed
the copy was issued to the *original requester* — not the approver — and
that the audit trail correctly recorded who requested it, who approved
it, and who it was issued to, all by name.
