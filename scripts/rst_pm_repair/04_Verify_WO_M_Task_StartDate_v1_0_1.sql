/* ============================================================================
   File      : 04_Verify_WO_M_Task_StartDate_v1_0_1.sql
   Version   : 1.0.1
   Type      : SSMS verification - READ ONLY (temp table only, no writes)
   DB        : RST dbWorkmate, or the restored test copy (dbWorkmate_RST_Test)
   Author    : Adriaan (Azztec) - companion to 01/02/03
   Changelog (newest first)
     1.0.1  2026-09-24  Rehearsal on the RST copy (02 commit, 118 tasks / 122 headers) left 4 rows in
                        section 4 that were neither BACKDATE-skipped nor X - they are 01 section B
                        masters (no unreleased open subtask left, so 02 has nothing to anchor to).
                        Section 4 wording corrected; new column Subtask_Rows_After_Last_Released
                        (0 = no schedule ahead -> rebuild the PM in Workmate). Logic unchanged.
     1.0.0  2026-09-23  initial
   Use
     @sfx = ''        baseline before 02: sections 3-4 only (pre-repair state)
     after 02 commit  sections 1-2 row counts = the counts 02 printed; section 3 = 0;
                      section 4 = BACKDATE-skipped + X + 01-section-B masters only
     after 03 commit  sections 1-2 = 0 -> rollback is exact
   Parameters: @sfx = backup suffix printed by 02 (optional for the baseline run)
   ============================================================================ */
SET NOCOUNT ON;

DECLARE @sfx varchar(20) = '';     -- backup suffix printed by 02_Repair, e.g. '20260924_0630'; '' = baseline (sections 3-4 only)

/* ---------- released PM work orders (Normal + Archive, linked children excluded), ids CHAR(160)-safe ---------- */
IF OBJECT_ID('tempdb..#R') IS NOT NULL DROP TABLE #R;
SELECT RTRIM(REPLACE(Short_WO_Id, CHAR(160), '')) AS WO_No, CAST(Request_Start_Date AS date) AS D
INTO   #R
FROM   WO_N_Header WHERE ISNULL(Linked_to_WO, 0) = 0
UNION ALL
SELECT RTRIM(REPLACE(Short_WO_Id, CHAR(160), '')), CAST(Request_Start_Date AS date)
FROM   WO_C_Header WHERE ISNULL(Linked_to_WO, 0) = 0;
CREATE CLUSTERED INDEX ix_R ON #R (WO_No, D);

/* ---------- 1-2. diff against the backup tables (only when @sfx given) ---------- */
IF @sfx <> ''
BEGIN
    DECLARE @tTask sysname = 'WO_M_Task_Backup_PMStartFix_'   + @sfx;
    DECLARE @tHdr  sysname = 'WO_M_Header_Backup_PMStartFix_' + @sfx;
    IF OBJECT_ID('dbo.' + @tTask) IS NULL OR OBJECT_ID('dbo.' + @tHdr) IS NULL
        PRINT 'Backup tables not found for suffix ' + @sfx + ' - sections 1-2 skipped'
    ELSE
    BEGIN
        DECLARE @sql nvarchar(max) = N'
PRINT ''=== 1) WO_M_Task rows differing from backup (Start_Date / Next_Service_Value) ===''; 
SELECT RTRIM(h.Short_WO_Id) AS PM, h.Repeat_Type_Flag AS Repeat_Type, RTRIM(t.Task_Id) AS Task,
       CONVERT(varchar(10), b.Start_Date, 120) AS Backup_Start_Date,
       CONVERT(varchar(10), t.Start_Date, 120) AS Current_Start_Date,
       DATEDIFF(dd, b.Start_Date, t.Start_Date) AS Diff_Days,
       b.Next_Service_Value AS Backup_NSV, t.Next_Service_Value AS Current_NSV
FROM   dbo.WO_M_Task t
JOIN   dbo.' + QUOTENAME(@tTask) + N' b ON b.WO_Id = t.WO_Id AND b.Task_Id = t.Task_Id
JOIN   dbo.WO_M_Header h ON h.WO_ID = t.WO_Id
WHERE  ISNULL(t.Start_Date, ''19000101'') <> ISNULL(b.Start_Date, ''19000101'')
   OR  ISNULL(t.Next_Service_Value, -1) <> ISNULL(b.Next_Service_Value, -1)
ORDER BY h.Short_WO_Id, t.Task_Id;
PRINT ''Task rows differing from backup   : '' + CAST(@@ROWCOUNT AS varchar(10));

PRINT ''=== 2) WO_M_Header rows differing from backup (Request_Start_Date / Request_End_Date) ===''; 
SELECT RTRIM(h.Short_WO_Id) AS PM, h.Repeat_Type_Flag AS Repeat_Type,
       CONVERT(varchar(10), b.Request_Start_Date, 120) AS Backup_Request_Start,
       CONVERT(varchar(10), h.Request_Start_Date, 120) AS Current_Request_Start,
       CONVERT(varchar(10), b.Request_End_Date, 120)   AS Backup_Request_End,
       CONVERT(varchar(10), h.Request_End_Date, 120)   AS Current_Request_End
FROM   dbo.WO_M_Header h
JOIN   dbo.' + QUOTENAME(@tHdr) + N' b ON b.WO_ID = h.WO_ID
WHERE  ISNULL(h.Request_Start_Date, ''19000101'') <> ISNULL(b.Request_Start_Date, ''19000101'')
   OR  ISNULL(h.Request_End_Date,   ''19000101'') <> ISNULL(b.Request_End_Date,   ''19000101'')
ORDER BY h.Short_WO_Id;
PRINT ''Header rows differing from backup : '' + CAST(@@ROWCOUNT AS varchar(10));';
        EXEC sp_executesql @sql;
    END
END
ELSE
    PRINT 'No @sfx given - baseline run, sections 1-2 skipped';

/* ---------- 3. headers vs MIN(task Start_Date), active masters, X-masters excluded (0 after 02 commit) ---------- */
PRINT '=== 3) active PM headers whose Request_Start_Date <> MIN(task Start_Date), X-masters excluded ===';
SELECT  RTRIM(h.Short_WO_Id) AS PM, h.Repeat_Type_Flag AS Repeat_Type,
        CONVERT(varchar(10), h.Request_Start_Date, 120) AS Request_Start,
        CONVERT(varchar(10), m.MinStart, 120)           AS Min_Task_Start
FROM    WO_M_Header h
JOIN   (SELECT WO_Id, MIN(Start_Date) AS MinStart FROM WO_M_Task WHERE Start_Date IS NOT NULL GROUP BY WO_Id) m ON m.WO_Id = h.WO_ID
WHERE   h.Status NOT IN ('C','D')
  AND   NOT EXISTS (SELECT 1 FROM WO_X_Subtasks x WHERE x.WO_ID = h.WO_ID)
  AND   CAST(h.Request_Start_Date AS date) <> CAST(m.MinStart AS date)
ORDER BY h.Short_WO_Id;
PRINT 'Header mismatches : ' + CAST(@@ROWCOUNT AS varchar(10));

/* ---------- 4. tasks whose Start_Date is earlier than the newest released WO of the master ---------- */
PRINT '=== 4) active tasks with Start_Date earlier than the newest released WO of the master (after 02 commit: only BACKDATE-skipped, X, or 01-section-B masters with no subtask ahead) ===';
SELECT  RTRIM(h.Short_WO_Id) AS PM, h.Repeat_Type_Flag AS Repeat_Type, RTRIM(t.Task_Id) AS Task,
        CONVERT(varchar(10), t.Start_Date, 120)     AS Start_Date,
        CONVERT(varchar(10), lr.Last_Released, 120) AS Last_Released_WO,
        DATEDIFF(dd, lr.Last_Released, t.Start_Date) AS Diff_Days,
        (SELECT COUNT(*) FROM WO_M_Subtasks s WHERE s.WO_Id = t.WO_Id
            AND RTRIM(REPLACE(s.Task_Id, CHAR(160), '')) = RTRIM(REPLACE(t.Task_Id, CHAR(160), ''))
            AND CAST(s.Req_Start_Date AS date) > lr.Last_Released) AS Subtask_Rows_After_Last_Released,
        CASE WHEN EXISTS (SELECT 1 FROM WO_X_Subtasks x WHERE x.WO_ID = t.WO_Id
                          AND RTRIM(REPLACE(x.Task_Id, CHAR(160), '')) = RTRIM(REPLACE(t.Task_Id, CHAR(160), '')))
             THEN 'X-SUBTASKS' ELSE '' END AS Flag
FROM    WO_M_Task t
JOIN    WO_M_Header h ON h.WO_ID = t.WO_Id
CROSS APPLY (SELECT RTRIM(REPLACE(h.Short_WO_Id, CHAR(160), '')) AS PMNo) tk
OUTER APPLY (SELECT MAX(r.D) AS Last_Released FROM #R r WHERE r.WO_No LIKE tk.PMNo + '-%') lr
WHERE   h.Status NOT IN ('C','D')
  AND   t.Start_Date IS NOT NULL
  AND   lr.Last_Released IS NOT NULL
  AND   CAST(t.Start_Date AS date) < lr.Last_Released
ORDER BY h.Short_WO_Id, t.Task_Id;
PRINT 'Tasks earlier than last released WO : ' + CAST(@@ROWCOUNT AS varchar(10));

DROP TABLE #R;
