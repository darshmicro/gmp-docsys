# Setting Up Automatic Database Backups

This makes SQL Server save a fresh backup of your data every night,
automatically, with no one needing to remember to do it — and cleans up
old backups after a set number of days so they don't fill up the disk.

**Why this matters more than the audit-trail security we set up earlier:**
the DENY rules from Part 5 of the installation guide stop anyone from
*editing or deleting* records through the application. They do nothing
to protect you from a hard drive failing, a server being stolen, ransomware,
or someone accidentally deleting the wrong file. Backups are the only real
protection against those.

---

## Part A — One-Time Setup

1. Create a folder for backups to live in — ideally on a **different
   physical drive** than the one SQL Server's data is on (a backup
   stored on the same drive doesn't help if that drive itself fails):
   ```
   C:\GMPDocTrack\Backups
   ```
   (If your `C:\GMPDocTrack` folder is on your only drive, this is still
   far better than no backup at all — just know that a second drive, or
   copying backups elsewhere periodically per Part E below, is the safer
   long-term setup.)

2. Open the folder `C:\GMPDocTrack\gmp-docsystem\deployment\windows\` and
   find `backup_database.bat`. Right-click → **Edit**.

3. Change the `SERVER_NAME` line to your actual SQL Server name — the
   same value you used in `start_server.bat`.

4. Check the `BACKUP_FOLDER` line matches the folder you created in
   step 1 (it already does if you used the exact path above).

5. Leave `RETENTION_DAYS` at 14, or change it to however many days of
   backups you want kept before old ones are automatically deleted.

6. Save and close.

7. **Make sure the Windows account you're currently logged in as has
   permission to back up SQL Server.** The narrowest, safest way to grant
   this (rather than making yourself a full SQL Server admin just for
   backups): in SSMS, expand **Security** → **Logins**. If your Windows
   login isn't already listed, right-click **Logins** → **New Login...**,
   click **Search...** to find your Windows account, and add it. Either
   way, double-click your login, click **User Mapping** on the left, tick
   the box next to **GMPDocTrack**, and in the role list below tick
   **`db_backupoperator`**. Click **OK**.

   (If that role doesn't appear for some reason, checking `sysadmin` under
   **Server Roles** instead will also work — it's just broader permission
   than backups strictly need.)

8. **Test it manually once:** double-click `backup_database.bat`. It
   runs silently (no window stays open) — check two things afterward:
   - A new file appeared in `C:\GMPDocTrack\Backups`, named something
     like `GMPDocTrack_20260315_020000.bak`.
   - Open `backup_log.txt` (same folder as the script) and confirm it
     says "Backup completed" with no error text above it.

   **A message about "no files found" during cleanup is normal and not
   an error** the first several times you run this — it just means no
   backup is old enough yet to need deleting.

   **If you're on SQL Server Express**, you may notice the log mentions
   skipping "backup compression" — that's expected and not an error.
   Express doesn't support that specific feature, so the script
   automatically detects that and leaves it out; your backup still works
   the same, the file is just a bit larger on disk than it would be on
   Standard/Enterprise edition.

If step 8 doesn't produce a `.bak` file, the log file will show why —
usually either the server name is wrong, or your Windows account doesn't
have backup permission (redo step 7).

---

## Part B — Automate It With Task Scheduler

This makes Windows run the backup by itself, every night, with nobody
needing to remember or click anything.

1. Press the Windows key, type `Task Scheduler`, press Enter.
2. On the right side, click **Create Basic Task...**
3. Name it `GMPDocTrack Nightly Backup`, click **Next**.
4. Choose **Daily**, click **Next**.
5. Pick a time when the system is least likely to be in use — for
   example, 2:00 AM — click **Next**.
6. Choose **Start a program**, click **Next**.
7. Click **Browse...** and select
   `C:\GMPDocTrack\gmp-docsystem\deployment\windows\backup_database.bat`
8. Click **Next**, then **Finish**.
9. **Important extra step:** find the task you just created in the
   middle list of Task Scheduler, right-click it, choose **Properties**.
   On the **General** tab, select **"Run whether user is logged on or
   not"** — this makes sure the backup still runs at 2 AM even if no one
   is logged into that computer at the time. Click **OK** (you may be
   asked for that Windows account's password to confirm this change).

That's it — from now on, this runs automatically every night. You can
manually trigger it any time from Task Scheduler (right-click the task →
**Run**) to test it again without waiting for 2 AM.

---

## Part C — Checking That It's Actually Working (Do This Weekly, At First)

It's easy to set this up, forget about it, and only discover months
later that it silently stopped working. Until you trust it, check
weekly:

1. Look in `C:\GMPDocTrack\Backups` — you should see roughly one `.bak`
   file per day, up to your retention limit (14 by default).
2. Open `backup_log.txt` and skim for the word "FAILED" anywhere.

## Part D — Lock the Backup Folder So Nobody Can Accidentally Delete a Backup

There are actually **three different things** that touch this folder, and
each needs a different level of access — this is why a single "make it
read-only" checkbox can't do this properly on its own:

1. **SQL Server itself** — it's SQL Server's own background service,
   not you and not the scheduled task, that physically writes each
   `.bak` file. It needs permission to **create** files here, but never
   needs to delete anything.
2. **The nightly cleanup step** (the part of `backup_database.bat` that
   deletes backups older than your retention limit) — this genuinely
   needs delete permission, or the automatic cleanup breaks.
3. **You, browsing in File Explorer** — this is the one we want to
   *not* have delete permission, so an accidental Delete key press can't
   remove a backup.

The trick is making sure #2 runs as a **different Windows account** than
the one you log in and browse with — otherwise Windows has no way to
tell "the automated cleanup deleting an old file" apart from "you
deleting a file by mistake," since as far as Windows permissions are
concerned, those would be the exact same account doing both things.

### Step 1 — Find out which account SQL Server itself runs as

1. Open **SQL Server Configuration Manager** (search for it in the Start
   menu).
2. Click **SQL Server Services** in the left panel.
3. Find your instance (e.g. "SQL Server (SQLEXPRESS)") and look at the
   **Log On As** column. Write down this exact value — commonly
   something like `NT Service\MSSQLSQLEXPRESS` for a default Express
   install, though it can differ.

### Step 2 — Create a dedicated account just for the nightly cleanup

Don't reuse your own personal login for this — a dedicated account means
your own everyday account never needs delete permission on this folder
at all.

1. Search **Computer Management** in the Start menu, open it.
2. Expand **Local Users and Groups** → right-click **Users** →
   **New User...**
3. **User name:** `GMPBackupService` (or any name you'll recognize).
4. Set a strong password. **Untick** "User must change password at next
   logon." **Tick** "Password never expires" (this account runs
   unattended every night, so it can never be prompted to change it).
5. Click **Create**, then **Close**.

### Step 3 — Give that new account permission to run backups

Same process as before, just for the new account instead of your own:

1. In SSMS, expand **Security** → **Logins** → right-click **Logins** →
   **New Login...**
2. Click **Search...**, find `GMPBackupService`, click **OK**.
3. Click **User Mapping** on the left, tick the box next to
   **GMPDocTrack**, and tick **`db_backupoperator`** in the role list.
4. Click **OK**.

### Step 4 — Set the actual folder permissions

1. Right-click `C:\GMPDocTrack\Backups` → **Properties** → **Security**
   tab → **Edit...**
2. If **Users**, **Authenticated Users**, or **Everyone** is listed with
   **Modify** or **Full control** ticked, select it and either click
   **Remove**, or untick Modify/Full control and tick only
   **Read & execute** instead. This is the step that actually removes
   everyday accidental-delete risk — don't skip it.
3. Click **Add...**, type the exact SQL Server service account name from
   Step 1, click **Check Names**, then **OK**.
4. With that account selected, tick **Write** and **Read & execute**
   only. **Leave Modify and Full control unticked** — this account can
   create new backups but can never delete one.
5. Click **Add...** again, type `GMPBackupService` (the account from
   Step 2), click **Check Names**, then **OK**.
6. With that account selected, tick **Modify** (this includes delete —
   needed for the automatic cleanup to keep working).
7. Click **OK** to save everything.

### Step 5 — Point the scheduled task at the new dedicated account

If you already set up Task Scheduler using your own account per Part B,
switch it over now:

1. Open **Task Scheduler**, find **GMPDocTrack Nightly Backup**.
2. Right-click → **Properties** → **General** tab.
3. Click **Change User or Group...**, type `GMPBackupService`, click
   **OK**.
4. Confirm **"Run whether user is logged on or not"** is still selected.
5. Click **OK** — you'll be asked for that account's password; enter the
   one you set in Step 2.

### Step 6 — Prove it actually worked

1. In Task Scheduler, right-click the task → **Run**.
2. Check `backup_log.txt` for "Backup completed" and "Backup step
   finished successfully" — confirms SQL Server could still write a new
   file.
3. **Now try to delete one of the `.bak` files yourself**, in File
   Explorer, using your own everyday account. Windows should refuse
   with a permissions error. If it lets you delete it, something in
   Step 4 didn't take — double check which account you were logged in
   as when doing Step 4 versus now.
4. After enough days pass (or once you're confident, by temporarily
   lowering `RETENTION_DAYS` to 0 and running the task once), confirm
   old backups still get cleaned up automatically — this confirms the
   dedicated account's delete permission is working for the automated
   path specifically, even though yours is blocked.

---

## Part E — The Backup Itself Needs Protecting Too (Recommended)

A backup sitting right next to the live database protects you from data
*corruption* or accidental deletion inside the database, but not from
losing the whole computer (theft, fire, major hardware failure). For
real protection, periodically copy the contents of
`C:\GMPDocTrack\Backups` to at least one of:
- An external drive, disconnected and stored elsewhere when not copying
- A different computer on your network
- A company-approved cloud storage location, if your organization has one

This doesn't need to be automated right away — even manually copying the
folder to a USB drive once a week is far better than only having backups
on the same machine as the live system.

## How to Actually Restore From a Backup (Hopefully You Never Need This)

If you ever do need to restore:

1. Open SSMS, right-click **Databases** → **Restore Database...**
2. Under Source, choose **Device**, click the "..." button, click
   **Add**, and browse to the `.bak` file you want to restore from.
3. Click **OK**, review the file list that appears, click **OK** again.

**This will overwrite the current database with the backup's contents.**
If the current database has data you might still need, back it up first
(run `backup_database.bat` one more time) before restoring an older one.
