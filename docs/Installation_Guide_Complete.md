# Complete Installation Guide (No IT Background Required)

This guide assumes you have never set up a server or a database before. Every
step tells you exactly what to click or type, and what you should see
happen. Take it slowly, one step at a time — there's no rush.

**Read this first — the big picture:**

You will set up the system on **one central computer** (called "the server"
in this guide — it could be an actual Windows Server machine, or just a
regular Windows desktop/laptop that stays on all the time and is connected
to your office network). Everyone else — every other person who needs to
use the system — does **not install anything at all**. They just get a
simple icon on their desktop that opens the system in their web browser,
the same way they'd open a website. All the data lives in one place (the
database, on the server), and every user's browser talks to that one
central place. Nothing is ever stored on any individual person's computer.

This matches how the system was designed: it's a website that only your
company can see (not the public internet), and everyone just visits it.

---

## Part 1 — What You Need Before Starting

- [ ] **One computer to act as the server.** It should be left on and
  connected to your office network at all times (or as close to "always
  on" as you can manage). A Windows machine is assumed throughout this
  guide.
- [ ] **Microsoft SQL Server** installed somewhere reachable from that
  server. If your company doesn't have this yet, **SQL Server Express**
  is a free edition suitable for small-to-medium document volumes —
  search "download SQL Server Express" on Microsoft's website and run
  the installer, choosing the "Basic" installation type when asked. It's
  fine to install this on the very same computer as the server described
  above.
- [ ] **SQL Server Management Studio (SSMS)** — this is the free, visual
  tool you'll use to talk to the database (no coding required, mostly
  point-and-click). Search "download SQL Server Management Studio" on
  Microsoft's website and install it on the server computer.
- [ ] **Python**, version 3.11 or newer. Search "download Python" on
  python.org, download the Windows installer, and run it. **Important:**
  on the very first screen of the Python installer, tick the checkbox
  that says **"Add python.exe to PATH"** before clicking Install — this
  one checkbox saves a lot of trouble later.
- [ ] The **gmp-docsystem.zip** file you were given, saved somewhere you
  can find it (e.g. your Downloads folder) on the server computer.

If any of these are already set up by someone else at your company (an IT
department, even a small one), you can skip the parts of this guide that
they've already done and jump to whichever section you still need.

---

## Part 2 — Unpack the Application

1. On the server computer, find the `gmp-docsystem.zip` file you downloaded.
2. Right-click it and choose **Extract All...**
3. When asked where to extract it, type or browse to `C:\GMPDocTrack\` and
   click **Extract**. (If the `C:\GMPDocTrack` folder doesn't exist yet,
   Windows will create it for you.)
4. You should now have a folder at `C:\GMPDocTrack\gmp-docsystem` containing
   folders named `app`, `sql`, `docs`, and a file named `requirements.txt`.
   If you see those, you've done this step correctly.

---

## Part 3 — Python Version & Virtual Environment, Then Install the Building Blocks

**If you already have more than one version of Python installed** (for
other projects on this same computer), read this section carefully —
it's specifically designed to eliminate that confusion permanently for
this project, so you never have to think about it again after today.

This application needs **Python 3.10 or newer**. Rather than relying on
whichever `python` command happens to run first on your computer (which
is exactly what gets confusing with multiple versions installed), we'll
create a **virtual environment** — a private, self-contained copy of
Python and its packages that belongs only to this project. Once it's
set up, this project always uses exactly the right version and exactly
the right packages, completely independent of any other project on the
same machine.

1. Press the **Windows key**, type `cmd`, and press Enter to open
   Command Prompt.
2. **See which Python versions are already installed** — type:
   ```
   py -0p
   ```
   This lists every Python version Windows knows about, with its full
   file path, something like:
   ```
    -V:3.14 *        C:\Users\yourname\AppData\Local\Programs\Python\Python314\python.exe
    -V:3.9           C:\Users\yourname\AppData\Local\Programs\Python\Python39\python.exe
   ```
   The `*` marks whichever one is currently the system default — but
   that doesn't matter for what we're about to do, since we're going to
   pick one explicitly by name.
3. Type the following, then press Enter:
   ```
   cd C:\GMPDocTrack\gmp-docsystem
   ```
4. **Create the virtual environment**, explicitly naming the version you
   want (any 3.10 or newer from the list in step 2 works fine — if
   you're not sure which to pick, use the highest number you have, e.g.
   `3.14`, matching what appeared in step 2):
   ```
   py -3.14 -m venv venv
   ```
   Replace `3.14` with whichever version number you actually saw listed
   for yourself in step 2. This creates a new folder called `venv` inside
   your project folder — this is that private copy of Python, and it's
   normal for it to take a few seconds to create.
5. **Activate it** — type:
   ```
   venv\Scripts\activate
   ```
   You'll know it worked because your prompt changes to show `(venv)` at
   the start of the line, like:
   ```
   (venv) C:\GMPDocTrack\gmp-docsystem>
   ```
   **From this point on, in this Command Prompt window, `python` and
   `pip` refer only to this project's private copy** — completely
   separate from any other Python version on this computer. This
   matters every time you come back to run one of this project's helper
   scripts (`test_db_connection.py`, `check_users.py`, `python -m
   app.seed`, and so on) by hand — always activate first, in whichever
   window you're using, the same way.
6. With `(venv)` showing in your prompt, install the application's
   dependencies — type the following, then press Enter, and wait (this
   can take a few minutes — you'll see a lot of text scroll by, that's
   expected):
   ```
   pip install -r requirements.txt
   ```
7. Once it finishes, type this and press Enter (this installs the piece
   that lets the application talk to SQL Server specifically):
   ```
   pip install pyodbc
   ```
8. You also need a small Microsoft component called the **"ODBC Driver
   for SQL Server."** Search "Microsoft ODBC Driver 17 for SQL Server
   download" on the web, download it from Microsoft's own website, and
   run the installer, accepting the defaults. (This one isn't a Python
   package, so it's installed system-wide the normal way, not into the
   venv.)

**You do not need to manually activate the venv every time the
application itself runs** — `start_server.bat` (Part 6 below) is already
set up to use this project's venv directly on its own, which is
important since a Windows Service (Part 8) can't run an interactive
"activate" command anyway. Activation is only something you do by hand
when you want to run one of the helper/diagnostic scripts yourself, or
reinstall/update a package.

If any of these commands show a wall of red error text instead of
finishing normally, stop and re-read the exact command you typed for
typos — that's the most common cause. If it still fails, save/copy the
red error text so whoever helps you next (even me, in a follow-up
message) can see exactly what went wrong.

---

## Part 4 — Create the Database

This section uses **SQL Server Management Studio (SSMS)**, the visual tool
you installed in Part 1.

1. Open SSMS (search for it in the Windows Start menu).
2. A "Connect to Server" window appears. For **Server name**, type the
   name of the computer running SQL Server — if it's the same computer
   you're on right now, just type a single period: `.`
   For **Authentication**, leave it as "Windows Authentication" and
   click **Connect**.
3. In the panel on the left (called "Object Explorer"), right-click on
   the word **Databases** and choose **New Database...**
4. In the "Database name" box, type exactly:
   ```
   GMPDocTrack
   ```
   Leave everything else as default, and click **OK**. You should now
   see `GMPDocTrack` appear in the list under Databases.
5. Right-click on the new **GMPDocTrack** database and choose
   **New Query**. A blank white writing area opens — this is where you'll
   paste in the script that builds all the tables.
6. On your computer, open the file
   `C:\GMPDocTrack\gmp-docsystem\sql\schema_sqlserver.sql` using Notepad
   (right-click the file → **Open with** → **Notepad**).
7. Select all the text in Notepad (Ctrl+A) and copy it (Ctrl+C).
8. Switch back to SSMS and paste (Ctrl+V) into that blank query window.
9. **Before running it**, scroll down inside that pasted text (using
   Ctrl+F to search helps) and find the line that says:
   ```
   CREATE LOGIN [svc_gmpdoctrack] WITH PASSWORD = 'CHANGE_THIS_PASSWORD_1234!';
   ```
   Replace `CHANGE_THIS_PASSWORD_1234!` with a strong password of your
   own choosing (keep the single quotes around it). **Write this password
   down somewhere safe right now** — a password manager, or a locked
   drawer if it must be on paper. You will need this exact password again
   in Part 6.
10. Click the **Execute** button (it has a red exclamation mark icon, or
    press F5). This will take a few seconds. At the bottom, you should see
    a message like "Commands completed successfully" and, further down,
    a small results grid showing table names — that's the check built
    into the script confirming your security setup worked (see the next
    section for what that grid means).

If you see red error text instead, the single most common cause is
running the script twice — if you already ran it once, SSMS will
complain the tables "already exist." If that happens and you need to
start over, right-click the `GMPDocTrack` database, choose **Delete**,
and repeat this Part 4 from step 3.

**You have now created the entire database structure and locked down the
audit trail, in one step** — the security section is built into the
script you just ran. See "Understanding What You Just Secured" below for
what it actually did.

---

## Part 5 — Understanding What You Just Secured (The Audit Trail)

The script you ran in Part 4 does something important that's worth
understanding, even briefly:

- It creates a special account, `svc_gmpdoctrack`, that the **application**
  uses to talk to the database — never your personal SQL Server login,
  never "sa."
- It gives that account normal permission to read and write data (so the
  application works normally).
- Then it **specifically and separately removes that account's permission
  to ever change or delete anything in the audit trail table**, and in a
  handful of other tables that record document issue/return/transfer
  history. This is enforced by SQL Server itself, at the database level —
  it has nothing to do with who is logged into the application or what
  role they have inside it. Even someone with the "System Administrator"
  role *inside the application* cannot edit or delete an audit trail
  entry, because the application's own database account is physically
  not allowed to do that operation, full stop.
- The little results grid that appeared after running the script is a
  built-in double-check: it lists any UPDATE/DELETE permissions that
  account has been granted on the audit trail. **It should show zero
  rows.** If you see any rows there, something went wrong — the safest
  fix is to delete the database and redo Part 4 from scratch.

The one honest limitation, explained plainly: a genuine SQL Server
administrator (someone with full "sysadmin" rights on your SQL Server —
typically a very small, trusted group, maybe just you) can always
override this if they deliberately choose to and know how. No database
software can prevent a true administrator from doing anything at all.
What this setup achieves is preventing it from happening *by accident*,
*through the application*, or *by anyone without that special
administrator access* — which covers every realistic day-to-day risk.
If your organization wants extra assurance here, ask whoever manages
your SQL Server to turn on SQL Server's own login-activity auditing, so
any such administrator-level access is itself independently logged.

---

## Part 6 — Connect the Application to the Database

1. Open the folder `C:\GMPDocTrack\gmp-docsystem\deployment\windows\` and
   find the file `set_db_env.bat` — this is the ONE file that holds your
   real SQL Server connection details, shared between the running
   application and any diagnostic script you run by hand later.
2. Right-click it and choose **Edit** (or **Open with** → **Notepad**).
3. Find these four lines:
   ```
   set DB_SERVER=YOUR_SERVER_NAME
   set DB_NAME=GMPDocTrack
   set DB_USER=svc_gmpdoctrack
   set DB_PASSWORD=CHANGE_THIS_PASSWORD_1234!
   ```
   Change two of them:
   - Replace `CHANGE_THIS_PASSWORD_1234!` with the exact password you set
     in Part 4, step 9 — **type it exactly as-is**, even if it contains
     characters like `@`, `:`, `/`, `#`, or `%`. Unlike some older setups,
     this one is specifically designed so you never need to modify or
     "encode" your password in any way — whatever you typed when creating
     the login is exactly what you type here.
   - Replace `YOUR_SERVER_NAME` with your SQL Server's name. If SQL
     Server is on this same computer, you can usually just type a period:
     `.`  If SQL Server was installed as a "named instance" (you'll know
     if the SSMS connection screen in Part 4 showed something like
     `COMPUTERNAME\SQLEXPRESS`), use that same value here.

   Leave `DB_NAME` and `DB_USER` as they are — they already match what
   Part 4's script created.
4. Save the file (Ctrl+S) and close Notepad.
5. Now open `start_server.bat` (the file next to it) the same way — Edit
   or Open with Notepad.
6. Find this line:
   ```
   cd /d "C:\GMPDocTrack\gmp-docsystem"
   ```
   Make sure that path matches exactly where you extracted the
   application in Part 2. If you followed this guide exactly, it already
   matches and you don't need to change it. (This file automatically
   loads your connection details from `set_db_env.bat` — you don't need
   to touch that part.)
7. Find this line:
   ```
   set SESSION_SECRET=REPLACE_WITH_A_LONG_RANDOM_VALUE
   ```
   Replace the text after the `=` with any long, random string of your
   own — for example, mash your keyboard for 30-40 characters. This is
   used only to keep login sessions secure; you never need to remember it
   or type it again.
8. Save this file too (Ctrl+S) and close Notepad.
9. **Before running the full application, test the connection on its own
   first** — this saves time, because it gives a much clearer answer than
   scrolling through the application's own startup messages. Open Command
   Prompt, go to your project folder, activate this project's virtual
   environment (see Part 3 if you haven't set this up yet), and load your
   connection details from the same shared file `start_server.bat` uses —
   this is the key step that makes sure this test is checking the exact
   same settings the real application will use:
   ```
   cd C:\GMPDocTrack\gmp-docsystem
   venv\Scripts\activate
   call deployment\windows\set_db_env.bat
   python test_db_connection.py
   ```
   It checks your connection step by step — whether the server name
   resolves, whether anything is listening on the network, and finally
   whether login actually succeeds — and tells you in plain language
   exactly which step failed and what to do about it, including the
   specific fix for "Error Locating Server/Instance Specified" if that's
   what comes up. Fix whatever it points out (editing `set_db_env.bat`
   again if needed), run the same three lines again, and repeat until it
   says "ALL CHECKS PASSED."
10. Once that test passes, double-click `start_server.bat` for real. A
   black window should open and, after a few seconds, show a line like:
   ```
   Uvicorn running on http://0.0.0.0:8000
   ```
   That means it's working and successfully talking to the database.

   **A note if you're upgrading from an older copy of this project** that
   used a single `DATABASE_URL` line instead of the four separate `DB_`
   lines: both still work, but if your password contains `@` or similar
   characters and you were using the old single-line style, you must
   percent-encode those characters yourself in that string (`@` becomes
   `%40`, `:` becomes `%3A`, `/` becomes `%2F`, `#` becomes `%23`, `%`
   becomes `%25`) — or simply switch to the four-line style above, which
   never requires that.
11. **Leave that black window open** for now, and open a web browser on
   that same server computer, and go to:
   ```
   http://localhost:8000
   ```
   You should see the login page. **Do not log in yet** — first, you need
   to create your first real administrator account, which is covered
   next.

---

## Part 6a — Already Have Data From Testing? Migrate It (Optional)

If you already used the system in demo mode (the SQLite file,
`gmpdoctrack.db`) and entered real documents, users, or storage locations
you don't want to lose, there's a script that copies everything across
to SQL Server, exactly once — see `migrate_sqlite_to_sqlserver.py` in the
main project folder. Full instructions are in the comment at the very
top of that file; the short version:

1. Make sure Part 4 (creating the database and running the schema
   script) is already done, and SQL Server is otherwise empty.
2. Open Command Prompt, `cd` into the project folder, activate the
   virtual environment (Part 3), and set these values (using your own
   admin login here, not the restricted `svc_gmpdoctrack` account — type
   your password exactly as-is, even if it contains `@` or other special
   characters):
   ```
   cd C:\GMPDocTrack\gmp-docsystem
   venv\Scripts\activate
   set SOURCE_SQLITE_PATH=.\gmpdoctrack.db
   set DEST_DB_SERVER=YOUR_SERVER_NAME
   set DEST_DB_NAME=GMPDocTrack
   set DEST_DB_USER=YourAdminLogin
   set DEST_DB_PASSWORD=YourPassword
   ```
3. Preview first, with nothing actually written:
   ```
   python migrate_sqlite_to_sqlserver.py --dry-run
   ```
4. If that looks right, run it for real:
   ```
   python migrate_sqlite_to_sqlserver.py
   ```
5. It prints a table at the end confirming every row count matches
   between the old file and SQL Server. Once you see "SUCCESS," your
   data is in SQL Server and you can see it in SSMS. If you migrated
   data this way, you already have your user accounts too — skip ahead
   to Part 8.

If you're starting completely fresh with no data worth keeping, skip
this section entirely and continue to Part 7 below.

---

## Part 7 — Create Your First Administrator Account

The application ships with a small setup script that creates some demo
accounts for testing. In production, run it once to build the basic
structure (departments, permissions, sample storage layout), but you
should immediately change the demo password or remove the demo accounts
afterward.

1. Stop the server for a moment: click into the black window from Part 6
   and press **Ctrl+C**, then press Enter if asked to confirm.
2. In that same window, activate this project's virtual environment
   first (the window from Part 6 ran the server using the venv directly,
   but didn't activate it for you to type commands, so this step is
   still needed even in the same window):
   ```
   venv\Scripts\activate
   ```
   Confirm you see `(venv)` appear at the start of your prompt.
3. Type:
   ```
   python -m app.seed
   ```
   and press Enter. After a few seconds you should see a message ending
   with a list of demo usernames and passwords.
4. Restart the server: double-click `start_server.bat` again (it will
   use the venv directly on its own, same as before — no need to
   activate anything for this step).
5. In your browser, go to `http://localhost:8000`, and log in with:
   - Username: `local:sysadmin`
   - Password: `ChangeMe123!`
6. **Immediately** go to the sidebar link **Change Password** and set a
   real, private password for this account — do this before anyone else
   uses the system.
7. Optional but recommended: go to **Users & Roles** in the sidebar and
   either delete/disable the other three demo accounts
   (`local:docadmin`, `local:docuser`, `local:viewer`) or reset their
   passwords too, so no one can log in with the well-known demo
   passwords in a real production system.
8. Go to **Company Settings** in the sidebar and set your real company
   name and logo — this is the "add company name and logo" feature, and
   it will now appear at the top of the screen for everyone.

---

## Part 8 — Make the Server Start Automatically (No One Has to Remember to Turn It On)

Right now, the system only runs while that black Command Prompt window
stays open — if the server computer restarts, or someone accidentally
closes that window, everyone loses access. To fix this, you'll install a
small free tool called **NSSM** ("the Non-Sucking Service Manager" — an
unusual name, but it's a well-known, widely trusted, free tool) that
turns your `start_server.bat` file into a proper background Windows
service — the same category of thing as, say, your antivirus, which runs
quietly all the time without anyone needing to open a window for it.

1. Search "NSSM download" on the web and download it from the official
   nssm.cc website. It comes as a `.zip` file.
2. Extract it, and inside you'll find folders like `win32` and `win64`.
   Most modern computers should use `win64`. Copy `nssm.exe` from that
   folder to somewhere permanent, e.g. `C:\GMPDocTrack\nssm.exe`.
3. Open Command Prompt **as Administrator**: press the Windows key, type
   `cmd`, then right-click "Command Prompt" in the results and choose
   **Run as administrator**.
4. Type:
   ```
   cd C:\GMPDocTrack
   nssm install GMPDocTrack
   ```
   and press Enter. A small window pops up.
5. In the **Path** box, click the "..." button and browse to
   `C:\GMPDocTrack\gmp-docsystem\deployment\windows\start_server.bat`
   and select it.
6. Click **Install service**.
7. Still in the same Administrator Command Prompt, type:
   ```
   nssm start GMPDocTrack
   ```
   The system will now start automatically every time the server
   computer turns on — no one needs to log in, open anything, or
   remember to do anything.
8. To confirm: open a browser and go to `http://localhost:8000` again —
   the login page should appear, exactly as before, even though you never
   manually opened `start_server.bat` this time.

From now on, if you ever need to stop or restart the application (for
example, after installing an upgrade), use these commands in an
Administrator Command Prompt instead of closing a window:
```
nssm stop GMPDocTrack
nssm start GMPDocTrack
```

---

## Part 9 — Set Up Each User's Desktop (No Installation, No Database — Just an Icon)

This is the part that answers "how do I make it feel like an app on
everyone's computer, without installing anything or putting any database
on their machine." The answer: their computer only ever needs a web
browser (which every Windows computer already has) and a simple icon
that opens straight to the right page. Nothing is installed, and no
data of any kind is stored on their computer — it all stays on the server
you just set up.

**Find out the server's network name or address first:** on the server
computer, press Windows key + R, type `cmd`, press Enter, then type
`hostname` and press Enter — note the name it shows you (e.g.
`OFFICE-SERVER01`). Every step below uses this name.

For each person's computer:

1. Right-click on their Windows Desktop and choose **New → Shortcut**.
2. In the box that appears, paste this (replacing `OFFICE-SERVER01` with
   the real name you found above), depending on which browser they use:

   **For Google Chrome:**
   ```
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --app=http://OFFICE-SERVER01:8000
   ```

   **For Microsoft Edge:**
   ```
   "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --app=http://OFFICE-SERVER01:8000
   ```
3. Click **Next**, name the shortcut something like
   `GMP Document Tracking`, and click **Finish**.
4. (Optional, but nice) Right-click the new shortcut, choose
   **Properties**, click **Change Icon...**, and pick an icon that looks
   more like an application than a bare browser icon.
5. Double-click the shortcut to test it. It should open in a clean window
   with no address bar or browser tabs, showing the login page directly —
   this is the "`--app=`" trick, and it makes an ordinary website open up
   looking and feeling like its own separate application, while still
   being just a browser under the hood. No installation happened, and
   nothing is stored on this computer.

**If you want it to open automatically every time this person logs into
Windows** (rather than them double-clicking the icon whenever they need
it): press Windows key + R, type `shell:startup`, press Enter — this
opens that person's personal Startup folder. Copy the shortcut you just
made into that folder. From now on, it will open by itself every time
they log in.

Repeat this Part 9 once for every person who needs access — it takes
under a minute per person once you've done it once. There's genuinely
nothing else to install on any of these computers, ever.

---

## Part 10 — Everyday Use: Passwords

- **Any user** can change their own password any time by clicking
  **Change Password** in the sidebar and entering their current and new
  password.
- **If someone forgets their password**, a System Administrator can reset
  it: go to **Users & Roles** in the sidebar, find that person's row, and
  click **Reset Password**. Set a temporary password and tell the person
  what it is — in person or by phone, not by email or chat — and ask them
  to change it themselves right afterward using **Change Password**.
- **Note for Active Directory users:** if your company later switches
  this system to log people in with their normal company/Windows
  username and password (instead of the local accounts this guide sets
  up), those users' passwords are controlled entirely by your IT
  department's Active Directory, the same way their email password is.
  Neither "Change Password" nor "Reset Password" inside this application
  can touch an Active Directory password — the application will tell
  them so directly if they try.

---

## Part 10a — Set Up Automatic Backups (Do This Before Going Live)

Everything up to this point protects your data from being edited or
deleted through the application, but does nothing to protect against a
hard drive failing, theft, or accidental damage to the server itself.
See `docs/Backup_Setup_Guide.md` for the full walkthrough — it sets up
SQL Server to save a compressed, verified backup automatically every
night via Windows Task Scheduler, with old backups cleaned up
automatically after 14 days (adjustable). This should be done before
this system holds any data you actually care about.

---

## Troubleshooting Quick Reference

| Problem | Likely cause / fix |
|---|---|
| "Login failed for user 'svc_gmpdoctrack'" | Password in `start_server.bat` doesn't match what you set in Part 4. Re-check both. |
| "Cannot open database GMPDocTrack" | The database name is misspelled somewhere, or SQL Server isn't running — open SSMS and confirm you can connect and see `GMPDocTrack` in the list. |
| Browser says "This site can't be reached" from another computer | The server's Windows Firewall may be blocking port 8000. Ask whoever manages the server firewall to allow incoming connections on TCP port 8000, or search "how to open a port in Windows Firewall" for step-by-step instructions. |
| "invalid username" when logging in | Either you haven't run `python -m app.seed` yet (Part 7), or you're using an account that hasn't been given a role yet — check **Users & Roles** in the sidebar. |
| Someone closed the black Command Prompt window and now nobody can log in | This is exactly what Part 8 (running it as a Windows Service) prevents — set that up so this can't happen again. |

---

## A Note on HTTPS (Encrypted Connections)

This guide sets the system up over plain `http://`, which is normal and
common for internal, trusted-network-only applications like this one, and
matches how the original request described it ("no requirement for
public internet access"). If your organization wants the extra step of
encrypting traffic between browsers and the server (recommended if your
network isn't fully trusted, or if your security policy requires it),
that's a worthwhile follow-up project, but it typically needs either an
internal certificate from your organization's own IT/security team, or
accepting a "not secure" warning in the browser with a self-signed one.
This is a reasonable thing to defer until after your initial rollout is
working — ask me for a walkthrough of that specific step whenever you're
ready for it.
