/* ============================================================================
   File      : 03_Rollback_WO_M_Task_StartDate_v1_0_0.sql
   Version   : 1.0.0
   Type      : SSMS rollback - WRITES WO_M_Task + WO_M_Header when @Commit = 1
   DB        : RST dbWorkmate (Workmate.NET 7.1.4.5)
   Author    : Azztec (review companion to 02_Repair v1.0.1)
   Changelog (newest first)
     1.0.0  2026-09-23  initial
   What it does
     Restores Start_Date + Next_Service_Value on WO_M_Task and Request_Start_Date +
     Request_End_Date on WO_M_Header from the two backup tables that 02_Repair created
     (WO_M_Task_Backup_PMStartFix_<sfx>, WO_M_Header_Backup_PMStartFix_<sfx>).
   Limits
     - Restores EVERY row that differs from the backup, so run it straight after the repair,
       before Workmate.NET has done another login PM release (that run also moves these
       columns). Later than that, restore selected PMs by hand from the backup tables.
     - Tasks or headers added/removed since the backup are reported, not touched.
   Parameters: @sfx (required) = suffix printed by 02, e.g. 20260924_0630 ; @Commit
   ============================================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @sfx    varchar(20) = '';      -- REQUIRED: suffix printed by 02_Repair, e.g. '20260924_0630'
DECLARE @Commit bit         = 0;       -- 0 = dry run (rollback), 1 = restore

IF @sfx = ''
BEGIN
    PRINT 'Set @sfx to the backup suffix printed by 02_Repair first.';
    RETURN;
END

DECLARE @tTask sysname = 'WO_M_Task_Backup_PMStartFix_'   + @sfx;
DECLARE @tHdr  sysname = 'WO_M_Header_Backup_PMStartFix_' + @sfx;

IF OBJECT_ID('dbo.' + @tTask) IS NULL OR OBJECT_ID('dbo.' + @tHdr) IS NULL
BEGIN
    PRINT 'Backup tables not found: dbo.' + @tTask + ' / dbo.' + @tHdr;
    RETURN;
END

DECLARE @sql nvarchar(max);

BEGIN TRY
BEGIN TRANSACTION;

/* ---------- preview ---------- */
SET @sql = N'
PRINT ''=== tasks that will be restored ===''; 
SELECT RTRIM(h.Short_WO_Id) AS PM, RTRIM(t.Task_Id) AS Task,
       CONVERT(varchar(10), t.Start_Date, 120) AS Current_Start_Date,
       CONVERT(varchar(10), b.Start_Date, 120) AS Restore_To_Start_Date,
       t.Next_Service_Value AS Current_NSV, b.Next_Service_Value AS Restore_To_NSV
FROM   dbo.WO_M_Task t
JOIN   dbo.' + QUOTENAME(@tTask) + N' b ON b.WO_Id = t.WO_Id AND b.Task_Id = t.Task_Id
JOIN   dbo.WO_M_Header h ON h.WO_ID = t.WO_Id
WHERE  ISNULL(t.Start_Date, ''19000101'') <> ISNULL(b.Start_Date, ''19000101'')
   OR  ISNULL(t.Next_Service_Value, -1) <> ISNULL(b.Next_Service_Value, -1)
ORDER BY h.Short_WO_Id, t.Task_Id;

PRINT ''=== PM headers that will be restored ===''; 
SELECT RTRIM(h.Short_WO_Id) AS PM,
       CONVERT(varchar(10), h.Request_Start_Date, 120) AS Current_Request_Start,
       CONVERT(varchar(10), b.Request_Start_Date, 120) AS Restore_To_Request_Start,
       CONVERT(varchar(10), h.Request_End_Date, 120)   AS Current_Request_End,
       CONVERT(varchar(10), b.Request_End_Date, 120)   AS Restore_To_Request_End
FROM   dbo.WO_M_Header h
JOIN   dbo.' + QUOTENAME(@tHdr) + N' b ON b.WO_ID = h.WO_ID
WHERE  ISNULL(h.Request_Start_Date, ''19000101'') <> ISNULL(b.Request_Start_Date, ''19000101'')
   OR  ISNULL(h.Request_End_Date,   ''19000101'') <> ISNULL(b.Request_End_Date,   ''19000101'')
ORDER BY h.Short_WO_Id;

/* ---------- restore ---------- */
UPDATE t SET Start_Date = b.Start_Date, Next_Service_Value = b.Next_Service_Value
FROM   dbo.WO_M_Task t
JOIN   dbo.' + QUOTENAME(@tTask) + N' b ON b.WO_Id = t.WO_Id AND b.Task_Id = t.Task_Id
WHERE  ISNULL(t.Start_Date, ''19000101'') <> ISNULL(b.Start_Date, ''19000101'')
   OR  ISNULL(t.Next_Service_Value, -1) <> ISNULL(b.Next_Service_Value, -1);
PRINT ''WO_M_Task rows restored : '' + CAST(@@ROWCOUNT AS varchar(10));

UPDATE h SET Request_Start_Date = b.Request_Start_Date, Request_End_Date = b.Request_End_Date
FROM   dbo.WO_M_Header h
JOIN   dbo.' + QUOTENAME(@tHdr) + N' b ON b.WO_ID = h.WO_ID
WHERE  ISNULL(h.Request_Start_Date, ''19000101'') <> ISNULL(b.Request_Start_Date, ''19000101'')
   OR  ISNULL(h.Request_End_Date,   ''19000101'') <> ISNULL(b.Request_End_Date,   ''19000101'');
PRINT ''WO_M_Header rows restored : '' + CAST(@@ROWCOUNT AS varchar(10));

/* ---------- rows the backup cannot cover (added or removed since) ---------- */
PRINT ''Tasks in backup with no current row : '' + CAST((SELECT COUNT(*) FROM dbo.' + QUOTENAME(@tTask) + N' b
       WHERE NOT EXISTS (SELECT 1 FROM dbo.WO_M_Task t WHERE t.WO_Id = b.WO_Id AND t.Task_Id = b.Task_Id)) AS varchar(10));
PRINT ''Current tasks with no backup row   : '' + CAST((SELECT COUNT(*) FROM dbo.WO_M_Task t
       WHERE NOT EXISTS (SELECT 1 FROM dbo.' + QUOTENAME(@tTask) + N' b WHERE b.WO_Id = t.WO_Id AND b.Task_Id = t.Task_Id)) AS varchar(10));
';
EXEC sp_executesql @sql;

IF @Commit = 1
BEGIN
    COMMIT TRANSACTION;
    PRINT '*** RESTORED from suffix ' + @sfx + ' ***';
END
ELSE
BEGIN
    ROLLBACK TRANSACTION;
    PRINT '*** DRY RUN - rolled back, nothing restored. Set @Commit = 1 to restore. ***';
END
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    PRINT 'ERROR - rolled back: ' + ERROR_MESSAGE();
END CATCH
