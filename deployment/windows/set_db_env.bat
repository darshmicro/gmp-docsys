@echo off
REM ============================================================================
REM  Database Connection Settings — the ONE place you edit these.
REM
REM  Both start_server.bat and any helper/diagnostic script you run by hand
REM  (test_db_connection.py, check_users.py, check_permissions.py, etc.)
REM  load your real connection details from this file, instead of you
REM  retyping the same four lines in every new Command Prompt window.
REM
REM  HOW TO USE THIS, when running a helper script yourself:
REM      cd C:\GMPDocTrack\gmp-docsystem
REM      venv\Scripts\activate
REM      call deployment\windows\set_db_env.bat
REM      python check_users.py
REM
REM  The "call" command loads these settings into YOUR CURRENT window —
REM  editing this file alone does not affect any window that's already
REM  open, or any new window you open later. You still need to "call" it
REM  in each new window before running a script that needs the database,
REM  but you never again need to retype or re-paste the actual values.
REM ============================================================================

set DB_SERVER=YOUR_SERVER_NAME
set DB_NAME=GMPDocTrack
set DB_USER=svc_gmpdoctrack
set DB_PASSWORD=CHANGE_THIS_PASSWORD_1234!

REM ============================================================================
REM  ⚠ DO NOT COMMIT THIS FILE TO GIT / GITHUB AFTER EDITING THE PASSWORD
REM     ABOVE. If this project is in a GitHub repository, check "git status"
REM     or GitHub Desktop's changed-files list before every commit and make
REM     sure this file (set_db_env.bat) is never included once it contains
REM     your real password. See GitHub_Setup_Guide.md for the full checklist.
REM ============================================================================
