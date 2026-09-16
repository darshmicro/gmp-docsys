-- ============================================================================
-- GMP Document Tracking System — Database Backup Script
-- ============================================================================
-- This creates a timestamped, integrity-checked backup file every time it
-- runs. It's meant to be run automatically once a day via Windows Task
-- Scheduler (see backup_database.bat and docs/Backup_Setup_Guide.md) — not
-- something you need to run by hand, though you can to test it.
--
-- WITH CHECKSUM makes SQL Server verify the backup as it's written, so a
-- corrupted backup is caught immediately rather than discovered months
-- later when you actually need to restore it.
--
-- Backup COMPRESSION is used automatically when your SQL Server edition
-- supports it (Standard/Enterprise) and is automatically skipped on
-- SQL Server Express, which does not support it — attempting to use it on
-- Express would make every single backup fail outright, so this is
-- detected and handled here rather than assuming one edition or the other.
--
-- The destination folder is NOT hardcoded here — it comes from
-- backup_database.bat as a variable called BackupFolder, so there's only
-- ONE place (the .bat file) where that path is ever set.
-- ============================================================================
SET NOCOUNT ON;

DECLARE @Timestamp NVARCHAR(20) =
    REPLACE(REPLACE(REPLACE(CONVERT(VARCHAR(19), GETDATE(), 120), '-', ''), ':', ''), ' ', '_');
DECLARE @BackupFile NVARCHAR(600) = N'$(BackupFolder)\GMPDocTrack_' + @Timestamp + N'.bak';

-- EngineEdition 4 = SQL Server Express, which doesn't support backup
-- compression. Every other edition value supports it.
DECLARE @SupportsCompression BIT = CASE WHEN SERVERPROPERTY('EngineEdition') = 4 THEN 0 ELSE 1 END;
DECLARE @Sql NVARCHAR(MAX);

IF @SupportsCompression = 1
BEGIN
    SET @Sql = N'BACKUP DATABASE [GMPDocTrack] TO DISK = @File WITH FORMAT, COMPRESSION, CHECKSUM, NAME = N''GMPDocTrack Scheduled Full Backup'', STATS = 10;';
END
ELSE
BEGIN
    PRINT 'Note: this SQL Server edition does not support backup compression — skipping it (this is normal on Express edition).';
    SET @Sql = N'BACKUP DATABASE [GMPDocTrack] TO DISK = @File WITH FORMAT, CHECKSUM, NAME = N''GMPDocTrack Scheduled Full Backup'', STATS = 10;';
END

EXEC sp_executesql @Sql, N'@File NVARCHAR(600)', @File = @BackupFile;

PRINT 'Backup completed: ' + @BackupFile;
