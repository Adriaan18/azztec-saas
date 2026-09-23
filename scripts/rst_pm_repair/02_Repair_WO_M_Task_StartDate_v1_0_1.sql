/* ============================================================================
   File      : 02_Repair_WO_M_Task_StartDate_v1_0_1.sql
   Version   : 1.0.1
   Type      : SSMS data repair - WRITES WO_M_Task + WO_M_Header when @Commit = 1
   DB        : RST dbWorkmate (Workmate.NET 7.1.4.5)
   Author    : Parag (Workmate Team) v1.0.0 - Azztec review amendments v1.0.1
   Changelog (newest first)
     1.0.1  2026-09-23  Azztec review
            - CHAR(160) non-breaking spaces stripped from Task_Id and every Short id before
              any cross-table match (same reason as 01 v1.0.1: a missed match moves
              Start_Date BACKWARDS).
            - Last_Released now read from #Rel: Normal + Archive (per @IncludeArchive),
              linked child work orders excluded.
            - New switch @SkipBackdatedTasks (default 1): a task whose "correct" date is
              earlier than its newest released work order is reported and SKIPPED.
              Set to 0 only after the BACKDATE rows in 01 section A have been reviewed.
            - Residue check after the task update (must be 0, else the run is rolled back).
            - Prints the backup suffix to use with 03_Rollback.
            - Logic otherwise unchanged from 1.0.0. @Commit default stays 0 (dry run).
     1.0.0  2026-09-16  Parag - original
   Run order : 01 (read only) -> 02 with @Commit = 0 -> review preview -> 02 with @Commit = 1
   Rollback  : 03_Rollback_WO_M_Task_StartDate_v1_0_0.sql with the suffix printed by this run
   ============================================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @Commit             bit = 0;   -- 0 = dry run (rollback), 1 = save
DECLARE @Mode               bit = 0;   -- 0 = any work order (same number+date) in Normal counts as released (recommended); 1 = only V/C/D
DECLARE @IncludeArchive     bit = 1;   -- 1 = work order (same number+date) in WO_C_Header counts as released
DECLARE @UseWO_N_Subtasks   bit = 1;   -- 1 = row (same number+date) in WO_N_Subtasks counts as released
DECLARE @OnlyActivePMs      bit = 1;   -- 1 = skip PMs whose header Status is C or D
DECLARE @IncludeMeterPMs    bit = 1;   -- 1 = repair Repeat_Type_Flag = 'CM' PMs too (Start_Date + Next_Service_Value)
DECLARE @SkipGapTasks       bit = 0;   -- 1 = do not touch tasks flagged GAP (see 01 section A)
DECLARE @SkipBackdatedTasks bit = 1;   -- 1 = do not touch tasks flagged BACKDATE (correct date earlier than newest released WO)

BEGIN TRY
BEGIN TRANSACTION;

/* ---------- 0. backup tables with date-time suffix (only when saving) ---------- */
DECLARE @sfx varchar(20) = REPLACE(REPLACE(REPLACE(CONVERT(varchar(16), GETDATE(), 120), '-', ''), ' ', '_'), ':', '');
IF @Commit = 1
BEGIN
    DECLARE @bk  nvarchar(max) = N'SELECT * INTO dbo.WO_M_Task_Backup_PMStartFix_'   + @sfx + N' FROM WO_M_Task; '
                               + N'SELECT * INTO dbo.WO_M_Header_Backup_PMStartFix_' + @sfx + N' FROM WO_M_Header;';
    EXEC (@bk);
    PRINT 'Backup tables created: WO_M_Task_Backup_PMStartFix_' + @sfx + ', WO_M_Header_Backup_PMStartFix_' + @sfx;
    PRINT 'Rollback: run 03_Rollback_WO_M_Task_StartDate_v1_0_0.sql with @sfx = ''' + @sfx + '''';
END

/* ---------- 1. released work order numbers + dates ---------- */
IF OBJECT_ID('tempdb..#Rel') IS NOT NULL DROP TABLE #Rel;
SELECT RTRIM(REPLACE(Short_WO_Id, CHAR(160), '')) AS WO_No, CAST(Request_Start_Date AS date) AS D, 'N' AS Src, Status, ISNULL(Linked_to_WO, 0) AS Linked INTO #Rel FROM WO_N_Header;
IF @IncludeArchive = 1
    INSERT INTO #Rel (WO_No, D, Src, Status, Linked)
    SELECT RTRIM(REPLACE(Short_WO_Id, CHAR(160), '')), CAST(Request_Start_Date AS date), 'C', Status, ISNULL(Linked_to_WO, 0) FROM WO_C_Header;
CREATE CLUSTERED INDEX ix_Rel ON #Rel (WO_No, D);

/* ---------- 1b. subtask rows already moved to WO_N_Subtasks ---------- */
IF OBJECT_ID('tempdb..#NS') IS NOT NULL DROP TABLE #NS;
SELECT n.WO_ID, RTRIM(REPLACE(n.Short_SubTask_ID, CHAR(160), '')) AS No, CAST(n.Req_Start_Date AS date) AS D INTO #NS FROM WO_N_Subtasks n;
CREATE CLUSTERED INDEX ix_NS ON #NS (WO_ID, No, D);

/* ---------- 1c. tasks with converged rows in WO_X_Subtasks ---------- */
IF OBJECT_ID('tempdb..#X') IS NOT NULL DROP TABLE #X;
SELECT DISTINCT x.WO_ID, RTRIM(REPLACE(x.Task_Id, CHAR(160), '')) AS TaskKey INTO #X FROM WO_X_Subtasks x;
CREATE CLUSTERED INDEX ix_X ON #X (WO_ID, TaskKey);

/* ---------- 2. subtasks with released information ---------- */
IF OBJECT_ID('tempdb..#Sub') IS NOT NULL DROP TABLE #Sub;
SELECT  s.WO_Id, s.Task_Id, k.TaskKey, s.Req_Start_Date, CAST(s.Req_Start_Date AS date) AS D,
        s.Status AS Sub_Status, s.Meter_ID, s.Meter_Reading,
        k.SubNo AS OwnNo,
        CASE WHEN RIGHT(k.SubNo, 2) = '-S' THEN LEFT(k.SubNo, LEN(k.SubNo) - 2) ELSE k.SubNo END AS MasterNo,
        CAST(NULL AS char(1)) AS N_Status,
        CAST(0 AS bit)        AS InArchive,
        CAST(0 AS bit)        AS InNSubtasks
INTO    #Sub
FROM    WO_M_Subtasks s
JOIN    WO_M_Header h ON h.WO_ID = s.WO_Id
CROSS APPLY (SELECT RTRIM(REPLACE(s.Short_SubTask_Id, CHAR(160), '')) AS SubNo,
                    RTRIM(REPLACE(s.Task_Id, CHAR(160), '')) AS TaskKey) k
WHERE   (@OnlyActivePMs = 0 OR h.Status NOT IN ('C','D'))
  AND   (@IncludeMeterPMs = 1 OR h.Repeat_Type_Flag <> 'CM');
CREATE CLUSTERED INDEX ix_Sub ON #Sub (WO_Id, TaskKey);

UPDATE x SET N_Status = r.Status
FROM   #Sub x JOIN #Rel r ON r.Src = 'N' AND r.D = x.D AND (r.WO_No = x.OwnNo OR r.WO_No = x.MasterNo);
UPDATE x SET InArchive = 1
FROM   #Sub x WHERE EXISTS (SELECT 1 FROM #Rel r WHERE r.Src = 'C' AND r.D = x.D AND (r.WO_No = x.OwnNo OR r.WO_No = x.MasterNo));
UPDATE x SET InNSubtasks = 1
FROM   #Sub x WHERE @UseWO_N_Subtasks = 1
  AND  EXISTS (SELECT 1 FROM #NS n WHERE n.WO_ID = x.WO_Id AND n.D = x.D AND (n.No = x.OwnNo OR n.No = x.MasterNo));

/* ---------- 3. new values per task ---------- */
IF OBJECT_ID('tempdb..#Fix') IS NOT NULL DROP TABLE #Fix;
SELECT  t.WO_Id, t.Task_Id, tk.TaskKey, h.Repeat_Type_Flag, t.Repeat_for_Following_12_Months AS Repeat12,
        t.Start_Date AS Old_Start,
        CAST(CAST(c.New_Start AS date) AS datetime) AS New_Start,
        t.Next_Service_Value AS Old_NSV,
        CASE WHEN h.Repeat_Type_Flag = 'CM' THEN c.New_NSV END AS New_NSV,
        lr.Last_Released,
        CASE WHEN ex.Expected_Next IS NOT NULL AND c.New_Start > DATEADD(dd, 7, ex.Expected_Next)
              AND NOT EXISTS (SELECT 1 FROM #Sub b WHERE b.WO_Id = t.WO_Id AND b.TaskKey = tk.TaskKey
                                                     AND b.D > lr.Last_Released AND b.D < CAST(c.New_Start AS date))
             THEN 1 ELSE 0 END AS IsGap,
        CASE WHEN lr.Last_Released IS NOT NULL AND CAST(c.New_Start AS date) < lr.Last_Released THEN 1 ELSE 0 END AS IsBackdate,
        CASE WHEN EXISTS (SELECT 1 FROM #X xx WHERE xx.WO_ID = t.WO_Id AND xx.TaskKey = tk.TaskKey) THEN 1 ELSE 0 END AS HasX
INTO    #Fix
FROM    WO_M_Task t
JOIN    WO_M_Header  h ON h.WO_ID = t.WO_Id
LEFT JOIN WO_M_Details d ON d.WO_ID = t.WO_Id
CROSS APPLY (SELECT RTRIM(REPLACE(t.Task_Id, CHAR(160), '')) AS TaskKey,
                    RTRIM(REPLACE(h.Short_WO_Id, CHAR(160), '')) AS PMNo) tk
OUTER APPLY (   /* newest released work order of this PM from #Rel (Normal + Archive per @IncludeArchive), linked child work orders excluded */
        SELECT MAX(r.D) AS Last_Released
        FROM   #Rel r
        WHERE  r.WO_No LIKE tk.PMNo + '-%' AND r.Linked = 0
) lr
OUTER APPLY (
        SELECT  MIN(x.Req_Start_Date) AS New_Start,
                MIN(CASE WHEN x.Req_Start_Date = m.mn THEN x.Meter_Reading END) AS New_NSV
        FROM    #Sub x
        CROSS APPLY (SELECT MIN(y.Req_Start_Date) mn FROM #Sub y
                     WHERE y.WO_Id = x.WO_Id AND y.TaskKey = x.TaskKey
                       AND ISNULL(y.Sub_Status,'') NOT IN ('C','D','V')
                       AND y.InArchive = 0 AND y.InNSubtasks = 0
                       AND ( (@Mode = 0 AND y.N_Status IS NULL)
                          OR (@Mode = 1 AND ISNULL(y.N_Status,'') NOT IN ('V','C','D')) )
                       AND (h.Repeat_Type_Flag <> 'CM' OR d.Meter_Id IS NULL OR y.Meter_ID = d.Meter_Id)) m
        WHERE   x.WO_Id = t.WO_Id AND x.TaskKey = tk.TaskKey
          AND   ISNULL(x.Sub_Status,'') NOT IN ('C','D','V')
          AND   x.InArchive = 0 AND x.InNSubtasks = 0
          AND   ( (@Mode = 0 AND x.N_Status IS NULL)
               OR (@Mode = 1 AND ISNULL(x.N_Status,'') NOT IN ('V','C','D')) )
          AND   (h.Repeat_Type_Flag <> 'CM' OR d.Meter_Id IS NULL OR x.Meter_ID = d.Meter_Id)
) c
OUTER APPLY (
        SELECT CASE WHEN h.Repeat_Type_Flag = 'CD' AND ISNUMERIC(t.CD_Freq) = 1 AND lr.Last_Released IS NOT NULL THEN
                    CASE d.Freq_Unit WHEN 'D' THEN DATEADD(dd, CAST(t.CD_Freq AS float),     lr.Last_Released)
                                     WHEN 'W' THEN DATEADD(dd, CAST(t.CD_Freq AS float) * 7, lr.Last_Released)
                                     WHEN 'M' THEN DATEADD(mm, CAST(t.CD_Freq AS float),     lr.Last_Released) END
               END AS Expected_Next
) ex
WHERE   (@OnlyActivePMs = 0 OR h.Status NOT IN ('C','D'))
  AND   (@IncludeMeterPMs = 1 OR h.Repeat_Type_Flag <> 'CM')
  AND   c.New_Start IS NOT NULL
  AND  (   CAST(t.Start_Date AS date) <> CAST(c.New_Start AS date)
        OR (h.Repeat_Type_Flag = 'CM' AND c.New_NSV IS NOT NULL AND ISNULL(t.Next_Service_Value,-1) <> c.New_NSV) );

/* ---------- 4. preview ---------- */
PRINT '=== tasks that will be updated ===';
SELECT  RTRIM(h.Short_WO_Id) AS PM, f.Repeat_Type_Flag AS Repeat_Type, RTRIM(f.Task_Id) AS Task, f.Repeat12,
        CONVERT(varchar(10), f.Old_Start, 120) AS Old_Start_Date,
        CONVERT(varchar(10), f.New_Start, 120) AS New_Start_Date,
        CONVERT(varchar(10), f.Last_Released, 120) AS Last_Released_WO,
        f.Old_NSV AS Old_Next_Service_Value,
        f.New_NSV AS New_Next_Service_Value,
        CASE WHEN f.HasX = 1 THEN 'X-SUBTASKS' WHEN f.IsBackdate = 1 THEN 'BACKDATE' WHEN f.IsGap = 1 THEN 'GAP' ELSE '' END AS Flag,
        CASE WHEN f.HasX = 1 THEN 'SKIPPED (X-subtasks)'
             WHEN f.IsBackdate = 1 AND @SkipBackdatedTasks = 1 THEN 'SKIPPED (BACKDATE)'
             WHEN f.IsGap = 1 AND @SkipGapTasks = 1 THEN 'SKIPPED (GAP)'
             ELSE 'UPDATE' END AS Action
FROM    #Fix f JOIN WO_M_Header h ON h.WO_ID = f.WO_Id
ORDER BY h.Short_WO_Id, f.Task_Id;

/* ---------- 5. update tasks ---------- */
UPDATE t SET Start_Date         = f.New_Start,
             Next_Service_Value = CASE WHEN f.Repeat_Type_Flag = 'CM' AND f.New_NSV IS NOT NULL THEN f.New_NSV ELSE t.Next_Service_Value END
FROM   WO_M_Task t JOIN #Fix f ON f.WO_Id = t.WO_Id AND f.Task_Id = t.Task_Id
WHERE  f.HasX = 0
  AND  (@SkipGapTasks = 0 OR f.IsGap = 0)
  AND  (@SkipBackdatedTasks = 0 OR f.IsBackdate = 0);
PRINT 'WO_M_Task rows updated : ' + CAST(@@ROWCOUNT AS varchar(10));

/* ---------- 5b. residue check: every task marked UPDATE must now carry its new date ---------- */
DECLARE @Residue int;
SELECT @Residue = COUNT(*)
FROM   #Fix f JOIN WO_M_Task t ON t.WO_Id = f.WO_Id AND t.Task_Id = f.Task_Id
WHERE  f.HasX = 0
  AND  (@SkipGapTasks = 0 OR f.IsGap = 0)
  AND  (@SkipBackdatedTasks = 0 OR f.IsBackdate = 0)
  AND  CAST(t.Start_Date AS date) <> CAST(f.New_Start AS date);
PRINT 'Residue (tasks still wrong after update, must be 0) : ' + CAST(@Residue AS varchar(10));
IF @Residue <> 0 RAISERROR('Residue check failed - task update did not land on every row', 16, 1);

/* ---------- 6. update PM headers  (Request_Start_Date = MIN(Start_Date) of its tasks) ---------- */
IF OBJECT_ID('tempdb..#Hdr') IS NOT NULL DROP TABLE #Hdr;
SELECT  h.WO_ID, h.Request_Start_Date AS Old_Req_Start, h.Request_End_Date AS Old_Req_End,
        CAST(CAST(m.MinStart AS date) AS datetime) AS New_Req_Start,
        CAST(CAST(DATEADD(hh, ISNULL(d.Duration_In_Hours,0), DATEADD(dd, ISNULL(d.Duration_In_Days,0), m.MinStart)) AS date) AS datetime) AS New_Req_End
INTO    #Hdr
FROM    WO_M_Header h
JOIN   (SELECT WO_Id, MIN(Start_Date) AS MinStart FROM WO_M_Task WHERE Start_Date IS NOT NULL GROUP BY WO_Id) m ON m.WO_Id = h.WO_ID
LEFT JOIN WO_M_Details d ON d.WO_ID = h.WO_ID
WHERE   (@OnlyActivePMs = 0 OR h.Status NOT IN ('C','D'))
  AND   (@IncludeMeterPMs = 1 OR h.Repeat_Type_Flag <> 'CM')
  AND   NOT EXISTS (SELECT 1 FROM #X xx WHERE xx.WO_ID = h.WO_ID)
  AND   CAST(h.Request_Start_Date AS date) <> CAST(m.MinStart AS date);

PRINT '=== PM headers that will be updated ===';
SELECT  RTRIM(h.Short_WO_Id) AS PM, h.Repeat_Type_Flag AS Repeat_Type,
        CONVERT(varchar(10), x.Old_Req_Start, 120) AS Old_Request_Start, CONVERT(varchar(10), x.New_Req_Start, 120) AS New_Request_Start,
        CONVERT(varchar(10), x.Old_Req_End, 120)   AS Old_Request_End,   CONVERT(varchar(10), x.New_Req_End, 120)   AS New_Request_End
FROM    #Hdr x JOIN WO_M_Header h ON h.WO_ID = x.WO_ID ORDER BY h.Short_WO_Id;

UPDATE h SET Request_Start_Date = x.New_Req_Start, Request_End_Date = x.New_Req_End
FROM   WO_M_Header h JOIN #Hdr x ON x.WO_ID = h.WO_ID;
PRINT 'WO_M_Header rows updated : ' + CAST(@@ROWCOUNT AS varchar(10));

DROP TABLE #Hdr; DROP TABLE #Fix; DROP TABLE #Sub; DROP TABLE #X; DROP TABLE #NS; DROP TABLE #Rel;

IF @Commit = 1
BEGIN
    COMMIT TRANSACTION;
    PRINT '*** COMMITTED *** backup suffix = ' + @sfx;
END
ELSE
BEGIN
    ROLLBACK TRANSACTION;
    PRINT '*** DRY RUN - rolled back, nothing saved. Set @Commit = 1 to apply. ***';
END
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    PRINT 'ERROR - rolled back: ' + ERROR_MESSAGE();
END CATCH
