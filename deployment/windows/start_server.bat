@echo off
REM ============================================================================
REM  GMP Document Tracking System — Server Startup Script
REM
REM  HOW TO USE THIS FILE:
REM  1. Edit the lines below marked "CHANGE THIS" to match your setup.
REM  2. Double-click this file to start the server manually (a black window
REM     will stay open — that IS the server running; closing that window
REM     stops the server).
REM  3. For the server to start automatically and keep running even when no
REM     one is logged in, don't double-click this file directly — instead
REM     follow the "Run as a Windows Service" section of the installation
REM     guide, which points a tool called NSSM at this exact file.
REM
REM  ABOUT PASSWORDS WITH SPECIAL CHARACTERS (@ : / # % etc.):
REM  The four separate DB_ settings below (server/name/user/password) let
REM  you type your real password exactly as it is, with no changes needed —
REM  even if it contains @ or any other special character. This is the
REM  recommended approach and is what this file uses by default.
REM
REM  ABOUT PYTHON VERSIONS:
REM  This file runs the app using THIS PROJECT'S OWN dedicated virtual
REM  environment (a "venv"), not whichever "python" happens to be first on
REM  your computer's PATH. This matters if you have more than one Python
REM  version installed for different projects — it guarantees this project
REM  always uses the exact right one, with the exact right packages,
REM  regardless of what else is installed. See the "Python Version & Virtual
REM  Environment" section of the installation guide to set this up once,
REM  the first time — after that, this file just works.
REM ============================================================================

REM CHANGE THIS: full path to the folder where you unzipped the application
cd /d "C:\GMPDocTrack\gmp-docsystem"

REM Your SQL Server connection details now live in ONE shared file,
REM set_db_env.bat, right next to this file — edit your real server name,
REM database, username, and password there (not here), so both this
REM script AND any diagnostic script you run by hand always agree.
call "%~dp0set_db_env.bat"

REM CHANGE THIS: a long random value, used to protect user login sessions.
REM              Generate one yourself (any long random text works) and never
REM              share it or commit it anywhere public.
set SESSION_SECRET=REPLACE_WITH_A_LONG_RANDOM_VALUE

REM ⚠ DO NOT COMMIT THIS FILE TO GIT / GITHUB AFTER EDITING SESSION_SECRET
REM    ABOVE. Check "git status" or GitHub Desktop's changed-files list
REM    before every commit. See GitHub_Setup_Guide.md for the full checklist.

REM If you're using Active Directory login instead of local accounts,
REM uncomment and fill in these three lines (remove the "REM " from the
REM start of each):
REM set AUTH_MODE=AD
REM set AD_SERVER=ldap://your-domain-controller.yourcompany.local
REM set AD_DOMAIN=YOURCOMPANY
REM set AD_BASE_DN=DC=yourcompany,DC=local

echo Starting GMP Document Tracking System...
echo Server will be available at http://localhost:8000 on this machine,
echo and at http://THIS-COMPUTER-NAME:8000 from other computers on the network.
echo.
echo Do not close this window while people are using the system.
echo.

if not exist "venv\Scripts\python.exe" (
    echo ERROR: This project's virtual environment was not found at:
    echo   venv\Scripts\python.exe
    echo.
    echo This means the one-time setup hasn't been done yet, or this file's
    echo "CHANGE THIS" path above doesn't point at the right folder.
    echo See "Python Version and Virtual Environment" in the installation
    echo guide for the exact steps, then run this file again.
    pause
    exit /b 1
)

REM Using the venv's own python.exe directly (instead of just "python") means
REM this always runs with the exact Python version and packages set up for
REM THIS project specifically — it works correctly even when run
REM unattended as a Windows Service via NSSM, which a manually-typed
REM "activate" command would not survive.
venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
