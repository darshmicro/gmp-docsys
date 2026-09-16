@echo off
REM ============================================================================
REM  GMP Document Tracking System — Automated Backup Script
REM
REM  HOW TO USE THIS FILE:
REM  1. Edit the settings below marked "CHANGE THIS".
REM  2. Test it once by double-clicking it — check the Backups folder
REM     afterward for a new .bak file, and check backup_log.txt for
REM     "Backup completed" with no errors above it.
REM  3. Once it works, follow "Automate It With Task Scheduler" in the
REM     installation guide to make Windows run this automatically every
REM     night — you do not need to keep double-clicking it yourself.
REM
REM  WHAT THIS DOES:
REM  - Creates a new, timestamped backup of the GMPDocTrack database
REM    (compressed automatically if your SQL Server edition supports it —
REM    this is skipped automatically on SQL Server Express, which doesn't).
REM  - Deletes backup files older than the number of days you set below,
REM    so the Backups folder doesn't grow forever and fill up the disk.
REM  - Writes a log of what happened to backup_log.txt in the same folder
REM    as this script, so you (or whoever checks on this) can confirm it
REM    actually ran successfully without having to remember to look.
REM ============================================================================

REM CHANGE THIS: your SQL Server's name (same value you used in start_server.bat)
set SERVER_NAME=YOUR_SERVER_NAME

REM CHANGE THIS: where backups are stored. Ideally this should be a
REM              DIFFERENT physical drive than the one SQL Server's data
REM              files are on — a backup stored on the same drive doesn't
REM              protect you if that drive fails.
set BACKUP_FOLDER=C:\GMPDocTrack\Backups

REM CHANGE THIS (if you want): how many days of backups to keep before
REM              automatically deleting the oldest ones.
set RETENTION_DAYS=14

set SCRIPT_DIR=%~dp0
set LOG_FILE=%SCRIPT_DIR%backup_log.txt

if not exist "%BACKUP_FOLDER%" mkdir "%BACKUP_FOLDER%"

echo ============================================ >> "%LOG_FILE%"
echo Backup run started: %DATE% %TIME% >> "%LOG_FILE%"

REM This uses Windows Authentication (-E) to connect to SQL Server — the
REM account that Task Scheduler runs this under must have permission to
REM back up the database (a member of the db_backupoperator role, or a
REM SQL Server admin account). This means no password has to be stored
REM anywhere in this file.
REM
REM The -v BackupFolder=... part passes your BACKUP_FOLDER setting above
REM through to backup_database.sql, so that folder only ever needs to be
REM set in this one place — the .sql file itself has no hardcoded path.
sqlcmd -S %SERVER_NAME% -E -v BackupFolder="%BACKUP_FOLDER%" -i "%SCRIPT_DIR%backup_database.sql" >> "%LOG_FILE%" 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo BACKUP FAILED — see above for the error. >> "%LOG_FILE%"
) else (
    echo Backup step finished successfully. >> "%LOG_FILE%"
)

echo Cleaning up backups older than %RETENTION_DAYS% days... >> "%LOG_FILE%"
forfiles /p "%BACKUP_FOLDER%" /m *.bak /d -%RETENTION_DAYS% /c "cmd /c del @path" >> "%LOG_FILE%" 2>&1

echo Backup run finished: %DATE% %TIME% >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"
