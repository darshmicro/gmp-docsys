# Putting This Project on GitHub

**This guide is for YOUR OWN organization's private deployment** — the
copy of this system configured with your real server, your real
departments, your real data over time. If you instead want to publish
the generic, reusable application publicly for anyone to download, see
`docs/Publishing_Guide.md` instead — that's a different, separate
repository from the one below, and the two should never be the same
repo.

This walks you through publishing this project to GitHub using
**GitHub Desktop** — a free program with buttons and menus, no typed
commands required. If you're already comfortable with the command line,
skip to "Alternative: Command Line" at the end.

**Before anything else: this must be a PRIVATE repository.** This project
will eventually reflect real internal details of your organization —
storage layouts, department names, and so on. GitHub repositories are
public by default unless you specifically choose private, so pay close
attention to that setting in Step 3 below.

---

## Step 1 — Create a GitHub Account

If you don't already have one, go to **github.com**, click **Sign up**,
and follow the prompts (email, username, password). Free accounts include
unlimited private repositories, which is all you need here.

---

## Step 2 — Install GitHub Desktop

1. Go to **desktop.github.com** and click **Download**.
2. Run the installer. When it opens, sign in with the GitHub account you
   just created.

You do **not** need to separately install Git — GitHub Desktop includes
everything required.

---

## Step 3 — Create the Repository

1. In GitHub Desktop, go to **File → New Repository...**
2. Fill in:
   - **Name**: something like `gmp-doc-tracking-system`
   - **Local Path**: click **Choose...** and pick the folder that
     *contains* your `gmp-docsystem` folder (not the folder itself — this
     matters, see the note below)
   - **Git ignore**: leave this set to **None** — this project already
     ships with its own carefully written `.gitignore` file, so you don't
     want GitHub Desktop to create a second, generic one that might
     conflict with it.
3. Click **Create Repository**.

**Important note on the folder:** GitHub Desktop's "New Repository" wizard
creates a brand new empty folder with the name you typed. Since you
already have a complete `gmp-docsystem` folder from the ZIP file, the
cleanest approach is actually a slightly different path — use
**"Add an Existing Repository"** instead, described next.

### The path that actually works with your existing folder

1. In GitHub Desktop, go to **File → Add Local Repository...**
2. Click **Choose...** and select your existing, already-unzipped
   `gmp-docsystem` folder directly (the one containing `app`, `sql`,
   `docs`, `README.md`, and so on).
3. GitHub Desktop will notice this folder isn't a Git repository yet and
   show a link that says **"create a repository"** — click it.
4. On the screen that appears, the folder name is already filled in.
   Leave **Git ignore** set to **None** (same reason as above — this
   project already has its own). Click **Create Repository**.

---

## Step 4 — Check What's About to Be Included (Important)

Before publishing anything, look at the list of files GitHub Desktop
shows you on the left ("Changes" tab). This is your chance to catch
anything that shouldn't be there.

**You should NOT see any of these in the list.** If you do, stop and
message back before continuing:
- `gmpdoctrack.db`
- Any file inside `app/__pycache__` or similar `__pycache__` folders
- Any file named `start_server.PRODUCTION.bat`, `start_server.local.bat`,
  or similar — only the plain `start_server.bat` template should appear
- Any `.env` file

**Extra check specific to this project, that a filename pattern alone
can't catch:** `start_server.bat` and `deployment/windows/set_db_env.bat`
themselves are expected to appear in this list as tracked files — that's
normal. But **open both of them and confirm `DB_PASSWORD` and
`SESSION_SECRET` still show placeholder text** (like
`CHANGE_THIS_PASSWORD_1234!`), not your real values, before you commit.
If you've already filled in real values for actual use (which the
installation guide has you do), do **not** commit after that point —
either revert just those two lines back to placeholder text first, or
save your real, edited copies under different filenames (e.g.
`set_db_env.PRODUCTION.bat`) that the `.gitignore` will catch
automatically instead.

These are all already excluded by the project's `.gitignore` file, so in
a normal case you won't see them — this step is just a safety check.

---

## Step 5 — Make Your First Commit

1. At the bottom left of GitHub Desktop, there's a box labeled
   "Summary (required)". Type something like:
   ```
   Initial commit — GMP Document Tracking System
   ```
2. Click the blue **Commit to main** button.

A "commit" is just a saved snapshot of the project at this point in time
— think of it like saving a Word document, but GitHub keeps every past
version too.

---

## Step 6 — Publish It to GitHub

1. Click the **Publish repository** button near the top of the window.
2. A dialog appears with a checkbox that says **"Keep this code
   private."** **Make sure this checkbox is TICKED.** This is the single
   most important click in this entire guide.
3. Click **Publish Repository**.

That's it — your project is now on GitHub, in a private repository only
you (and anyone you explicitly invite) can see.

---

## Step 7 — Making Changes Later

Whenever you or someone else edits any file in this project (for
example, applying a future update I send you):

1. Open GitHub Desktop.
2. You'll see the changed files listed automatically.
3. Type a short summary of what changed, click **Commit to main**, then
   click **Push origin** (the button that appears where "Publish
   repository" used to be).

That's the entire ongoing workflow — two buttons.

---

## Giving Other People Access

Since the repository is private, only you can see it by default. To let
a colleague view or contribute:

1. On GitHub.com, go to your repository's page.
2. Click **Settings** → **Collaborators**.
3. Click **Add people** and enter their GitHub username or email.

They'll get an invitation email; once accepted, they can see and clone
the private repository too.

---

## Alternative: Command Line

If you'd rather use the command line (or already have Git installed),
these commands do the same thing as Steps 3–6 above. Run them from
**inside** your `gmp-docsystem` folder:

```bash
git init
git add -A
git commit -m "Initial commit — GMP Document Tracking System"
```

Then create the private repository on GitHub.com first (click the **+**
icon top-right → **New repository** → give it a name → make sure
**Private** is selected → click **Create repository**, and do **not**
tick "Add a README" since you already have one). GitHub will then show
you a remote URL — copy it and run:

```bash
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO-NAME.git
git branch -M main
git push -u origin main
```

You'll be prompted to authenticate — GitHub will guide you through
creating a personal access token if you haven't done this before (GitHub
no longer accepts your account password directly for this).

---

## One Last Reminder

If you ever set up the real production server following
`docs/Installation_Guide_Complete.md`, you'll create an edited copy of
`start_server.bat` containing your actual SQL Server password. **Save
that edited copy under a different filename** — for example
`start_server.PRODUCTION.bat` — so the `.gitignore` rules in this project
automatically keep it out of GitHub. Never type your real database
password into the plain `start_server.bat` file that Git is tracking.
