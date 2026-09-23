/* ============================================================================
   File      : 01_Identify_Wrong_WO_M_Task_StartDate_v1_0_1.sql
   Version   : 1.0.1
   Type      : SSMS diagnostic - READ ONLY (temp tables only, no writes)
   DB        : RST dbWorkmate (Workmate.NET 7.1.4.5)
   Author    : Parag (Workmate Team) v1.0.0 - Azztec review amendments v1.0.1
   Changelog (newest first)
     1.0.1  2026-09-23  Azztec review
            - CHAR(160) non-breaking spaces stripped from Task_Id and every Short id before
              any cross-table match. RTRIM does not remove them; .NET strips them in 16
              places in frmReleasePMWO. A missed match makes a released subtask look
              unreleased, which would move Start_Date BACKWARDS.
            - Last_Released_WO now read from #Rel: Normal + Archive (per @IncludeArchive),
              linked child work orders excluded (as .NET GetLastRel_Or_LastRelExp_Date).
            - New flag BACKDATE: correct date is EARLIER than the last released work order.
              Those rows need a human look (moved/deleted/PO-blocked occurrence), not a repair.
            - New section F: data hygiene counts (CHAR(160) rows, orphan subtasks).
            - Logic otherwise unchanged from 1.0.0.
     1.0.0  2026-09-16  Parag - original
   Parameters: see DECLAREs below
   Returns   : result sets A-F with PRINT headers
   ============================================================================ */
SET NOCOUNT ON;

DECLARE @Mode             bit = 0;   -- 0 = any work order (same number+date) in Normal counts as released (recommended); 1 = only V/C/D
DECLARE @IncludeArchive   bit = 1;   -- 1 = work order (same number+date) in WO_C_Header counts as released
DECLARE @UseWO_N_Subtasks bit = 1;   -- 1 = row (same number+date) in WO_N_Subtasks counts as released
DECLARE @OnlyActivePMs    bit = 1;   -- 1 = skip PMs whose header Status is C or D
DECLARE @IncludeMeterPMs  bit = 1;   -- 1 = include Repeat_Type_Flag = 'CM' PMs

/* ---------- 1. every PM work order number + date that exists in Normal or Archive ---------- */
IF OBJECT_ID('tempdb..#Rel') IS NOT NULL DROP TABLE #Rel;
SELECT RTRIM(REPLACE(Short_WO_Id, CHAR(160), '')) AS WO_No, CAST(Request_Start_Date AS date) AS D, 'N' AS Src, Status, ISNULL(Linked_to_WO, 0) AS Linked
INTO   #Rel
FROM   WO_N_Header;
IF @IncludeArchive = 1
    INSERT INTO #Rel (WO_No, D, Src, Status, Linked)
    SELECT RTRIM(REPLACE(Short_WO_Id, CHAR(160), '')), CAST(Request_Start_Date AS date), 'C', Status, ISNULL(Linked_to_WO, 0) FROM WO_C_Header;
CREATE CLUSTERED INDEX ix_Rel ON #Rel (WO_No, D);

/* ---------- 1b. subtask rows already moved to WO_N_Subtasks (12-month block) ---------- */
IF OBJECT_ID('tempdb..#NS') IS NOT NULL DROP TABLE #NS;
SELECT n.WO_ID, RTRIM(REPLACE(n.Short_SubTask_ID, CHAR(160), '')) AS No, CAST(n.Req_Start_Date AS date) AS D INTO #NS FROM WO_N_Subtasks n;
CREATE CLUSTERED INDEX ix_NS ON #NS (WO_ID, No, D);

/* ---------- 1c. tasks that have converged rows in WO_X_Subtasks ---------- */
IF OBJECT_ID('tempdb..#X') IS NOT NULL DROP TABLE #X;
SELECT DISTINCT x.WO_ID, RTRIM(REPLACE(x.Task_Id, CHAR(160), '')) AS TaskKey INTO #X FROM WO_X_Subtasks x;
CREATE CLUSTERED INDEX ix_X ON #X (WO_ID, TaskKey);

/* ---------- 2. subtasks with their "released" information ---------- */
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

/* ---------- 3. correct start date (and, for meter PMs, next service value) per task ---------- */
IF OBJECT_ID('tempdb..#Task') IS NOT NULL DROP TABLE #Task;
SELECT  t.WO_Id, t.Task_Id, tk.TaskKey, h.Repeat_Type_Flag, t.Repeat_for_Following_12_Months AS Repeat12,
        t.Start_Date AS Current_Start, t.Next_Service_Value AS Current_NSV,
        c.New_Start, c.From_Subtask, c.Candidates,
        CASE WHEN h.Repeat_Type_Flag = 'CM' THEN c.New_NSV END AS New_NSV,
        lr.Last_Released,
        CASE WHEN EXISTS (SELECT 1 FROM #X xx WHERE xx.WO_ID = t.WO_Id AND xx.TaskKey = tk.TaskKey) THEN 1 ELSE 0 END AS HasX,
        /* expected next date = last released work order + task frequency (date PMs only) */
        CASE WHEN h.Repeat_Type_Flag = 'CD' AND ISNUMERIC(t.CD_Freq) = 1 AND lr.Last_Released IS NOT NULL THEN
             CASE d.Freq_Unit WHEN 'D' THEN DATEADD(dd, CAST(t.CD_Freq AS float),     lr.Last_Released)
                              WHEN 'W' THEN DATEADD(dd, CAST(t.CD_Freq AS float) * 7, lr.Last_Released)
                              WHEN 'M' THEN DATEADD(mm, CAST(t.CD_Freq AS float),     lr.Last_Released) END
        END AS Expected_Next,
        /* subtask rows of any status between the last released work order and the correct date */
        (SELECT COUNT(*) FROM #Sub b WHERE b.WO_Id = t.WO_Id AND b.TaskKey = tk.TaskKey
                                       AND b.D > lr.Last_Released AND b.D < CAST(c.New_Start AS date)) AS Rows_Between,
        /* BACKDATE = the "correct" date is earlier than the newest released work order of this PM */
        CASE WHEN c.New_Start IS NOT NULL AND lr.Last_Released IS NOT NULL AND CAST(c.New_Start AS date) < lr.Last_Released
             THEN 1 ELSE 0 END AS IsBackdate
INTO    #Task
FROM    WO_M_Task t
JOIN    WO_M_Header  h ON h.WO_ID  = t.WO_Id
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
                MIN(CASE WHEN x.Req_Start_Date = m.mn THEN x.OwnNo END)          AS From_Subtask,
                MIN(CASE WHEN x.Req_Start_Date = m.mn THEN x.Meter_Reading END)  AS New_NSV,
                COUNT(*) AS Candidates
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
WHERE   (@OnlyActivePMs = 0 OR h.Status NOT IN ('C','D'))
  AND   (@IncludeMeterPMs = 1 OR h.Repeat_Type_Flag <> 'CM');

/* ---------- 4a. RESULT: tasks whose Start_Date (or, for meter PMs, Next_Service_Value) is wrong ---------- */
PRINT '=== A) WO_M_Task rows whose Start_Date / Next_Service_Value differ from the correct values ===';
SELECT  RTRIM(h.Short_WO_Id)                        AS PM,
        h.Status                                    AS PM_Status,
        k.Repeat_Type_Flag                          AS Repeat_Type,
        RTRIM(k.Task_Id)                            AS Task,
        k.Repeat12,
        CASE WHEN k.Repeat_Type_Flag = 'CM' THEN RTRIM(t.CM_Freq) ELSE RTRIM(t.CD_Freq) END + ISNULL(d.Freq_Unit,'') AS Freq,
        CONVERT(varchar(10), k.Current_Start, 120)  AS Current_Start_Date,
        CONVERT(varchar(10), k.New_Start, 120)      AS Correct_Start_Date,
        DATEDIFF(dd, k.Current_Start, k.New_Start)  AS Diff_Days,
        k.Current_NSV                               AS Current_Next_Service_Value,
        k.New_NSV                                   AS Correct_Next_Service_Value,
        k.From_Subtask                              AS Correct_From_Subtask,
        k.Candidates                                AS Unreleased_Subtasks,
        CONVERT(varchar(10), k.Last_Released, 120)  AS Last_Released_WO,
        CONVERT(varchar(10), k.Expected_Next, 120)  AS Expected_Next_By_Freq,
        k.Rows_Between                              AS Subtask_Rows_Between,
        CASE WHEN k.HasX = 1 THEN 'X-SUBTASKS'
             WHEN k.IsBackdate = 1 THEN 'BACKDATE'
             WHEN k.Expected_Next IS NOT NULL AND k.New_Start > DATEADD(dd, 7, k.Expected_Next) AND k.Rows_Between = 0 THEN 'GAP'
             ELSE '' END AS Flag
FROM    #Task k
JOIN    WO_M_Task    t ON t.WO_Id = k.WO_Id AND t.Task_Id = k.Task_Id
JOIN    WO_M_Header  h ON h.WO_ID = k.WO_Id
LEFT JOIN WO_M_Details d ON d.WO_ID = k.WO_Id
WHERE   k.New_Start IS NOT NULL
  AND  (   CAST(k.Current_Start AS date) <> CAST(k.New_Start AS date)
        OR (k.Repeat_Type_Flag = 'CM' AND k.New_NSV IS NOT NULL AND ISNULL(k.Current_NSV,-1) <> k.New_NSV) )
ORDER BY h.Short_WO_Id, k.Task_Id;

/* ---------- 4b. RESULT: tasks where no correct date can be worked out ---------- */
PRINT '=== B) tasks with NO unreleased open subtask left (nothing to update; CD masters here have run out of schedule -> rebuild the PM) ===';
SELECT  RTRIM(h.Short_WO_Id) AS PM, h.Status AS PM_Status, k.Repeat_Type_Flag AS Repeat_Type, RTRIM(k.Task_Id) AS Task, k.Repeat12,
        CONVERT(varchar(10), k.Current_Start, 120) AS Current_Start_Date,
        CONVERT(varchar(10), k.Last_Released, 120) AS Last_Released_WO,
        (SELECT COUNT(*) FROM #Sub x WHERE x.WO_Id = k.WO_Id AND x.TaskKey = k.TaskKey) AS Subtask_Rows
FROM    #Task k JOIN WO_M_Header h ON h.WO_ID = k.WO_Id
WHERE   k.New_Start IS NULL
ORDER BY h.Short_WO_Id, k.Task_Id;

/* ---------- 4c. RESULT: PM headers whose Request_Start_Date would change ---------- */
PRINT '=== C) WO_M_Header rows whose Request_Start_Date differs from MIN(correct task start) ===';
SELECT  RTRIM(h.Short_WO_Id) AS PM, h.Status AS PM_Status, h.Repeat_Type_Flag AS Repeat_Type,
        CONVERT(varchar(10), h.Request_Start_Date, 120) AS Current_Request_Start,
        CONVERT(varchar(10), m.New_PM_Start, 120)       AS Correct_Request_Start,
        CONVERT(varchar(10), h.Entry_date, 120)         AS Entry_Date_unchanged
FROM    WO_M_Header h
JOIN   (SELECT WO_Id, MIN(ISNULL(New_Start, Current_Start)) AS New_PM_Start FROM #Task GROUP BY WO_Id) m ON m.WO_Id = h.WO_ID
WHERE   CAST(h.Request_Start_Date AS date) <> CAST(m.New_PM_Start AS date)
ORDER BY h.Short_WO_Id;

/* ---------- 4d. summary ---------- */
PRINT '=== D) summary ===';
SELECT  (SELECT COUNT(*) FROM #Task) AS Tasks_Checked,
        (SELECT COUNT(*) FROM #Task WHERE New_Start IS NOT NULL AND CAST(Current_Start AS date) <> CAST(New_Start AS date)) AS Tasks_Wrong_Date,
        (SELECT COUNT(*) FROM #Task WHERE New_Start IS NOT NULL AND CAST(Current_Start AS date) <> CAST(New_Start AS date) AND Repeat_Type_Flag = 'CD' AND ISNULL(Repeat12,'N') <> 'Y') AS Path1_Date_PM,
        (SELECT COUNT(*) FROM #Task WHERE New_Start IS NOT NULL AND Repeat_Type_Flag = 'CM'
                                      AND (CAST(Current_Start AS date) <> CAST(New_Start AS date) OR (New_NSV IS NOT NULL AND ISNULL(Current_NSV,-1) <> New_NSV))) AS Path2_Meter_PM,
        (SELECT COUNT(*) FROM #Task WHERE New_Start IS NOT NULL AND CAST(Current_Start AS date) <> CAST(New_Start AS date) AND Repeat12 = 'Y') AS Path3_Repeat12,
        (SELECT COUNT(*) FROM #Task WHERE New_Start IS NOT NULL AND CAST(Current_Start AS date) <> CAST(New_Start AS date) AND IsBackdate = 1) AS Tasks_Flagged_BACKDATE,
        (SELECT COUNT(*) FROM #Task WHERE New_Start IS NOT NULL AND CAST(Current_Start AS date) <> CAST(New_Start AS date)
                                      AND Expected_Next IS NOT NULL AND New_Start > DATEADD(dd, 7, Expected_Next) AND Rows_Between = 0) AS Tasks_Flagged_GAP,
        (SELECT COUNT(*) FROM #Task WHERE HasX = 1) AS Tasks_With_X_Subtasks,
        (SELECT COUNT(*) FROM #Sub WHERE InNSubtasks = 1) AS Subtask_Rows_Found_In_WO_N_Subtasks,
        (SELECT COUNT(*) FROM #Task WHERE New_Start IS NULL) AS Tasks_No_Candidate;

/* ---------- 4e. RESULT: tasks with converged rows (handled by a different rule in code; repair skips them) ---------- */
PRINT '=== E) tasks that have rows in WO_X_Subtasks (skipped by the repair script) ===';
SELECT  RTRIM(h.Short_WO_Id) AS PM, h.Status AS PM_Status, RTRIM(k.Task_Id) AS Task,
        CONVERT(varchar(10), k.Current_Start, 120) AS Current_Start_Date,
        (SELECT COUNT(*) FROM WO_X_Subtasks x WHERE x.WO_ID = k.WO_Id AND RTRIM(REPLACE(x.Task_Id, CHAR(160), '')) = k.TaskKey) AS X_Rows
FROM    #Task k JOIN WO_M_Header h ON h.WO_ID = k.WO_Id
WHERE   k.HasX = 1
ORDER BY h.Short_WO_Id, k.Task_Id;

/* ---------- 4f. data hygiene: ids carrying CHAR(160), orphan subtasks ---------- */
PRINT '=== F) data hygiene (all counts should be 0; non-zero CHAR(160) counts mean v1.0.0 of these scripts would mis-match ids) ===';
SELECT 'WO_M_Task.Task_Id has CHAR(160)'            AS Check_Name, COUNT(*) AS Rows_Found FROM WO_M_Task      WHERE CHARINDEX(CHAR(160), Task_Id) > 0
UNION ALL SELECT 'WO_M_Subtasks.Task_Id has CHAR(160)',          COUNT(*) FROM WO_M_Subtasks  WHERE CHARINDEX(CHAR(160), Task_Id) > 0
UNION ALL SELECT 'WO_M_Subtasks.Short_SubTask_Id has CHAR(160)', COUNT(*) FROM WO_M_Subtasks  WHERE CHARINDEX(CHAR(160), Short_SubTask_Id) > 0
UNION ALL SELECT 'WO_X_Subtasks.Task_Id has CHAR(160)',          COUNT(*) FROM WO_X_Subtasks  WHERE CHARINDEX(CHAR(160), Task_Id) > 0
UNION ALL SELECT 'WO_N_Subtasks.Short_SubTask_ID has CHAR(160)', COUNT(*) FROM WO_N_Subtasks  WHERE CHARINDEX(CHAR(160), Short_SubTask_ID) > 0
UNION ALL SELECT 'WO_M_Header.Short_WO_Id has CHAR(160)',        COUNT(*) FROM WO_M_Header    WHERE CHARINDEX(CHAR(160), Short_WO_Id) > 0
UNION ALL SELECT 'WO_N_Header.Short_WO_Id has CHAR(160)',        COUNT(*) FROM WO_N_Header    WHERE CHARINDEX(CHAR(160), Short_WO_Id) > 0
UNION ALL SELECT 'WO_C_Header.Short_WO_Id has CHAR(160)',        COUNT(*) FROM WO_C_Header    WHERE CHARINDEX(CHAR(160), Short_WO_Id) > 0
UNION ALL SELECT 'WO_M_Subtasks rows with no matching WO_M_Task (orphans)', COUNT(*)
          FROM   WO_M_Subtasks s
          WHERE  NOT EXISTS (SELECT 1 FROM WO_M_Task t WHERE t.WO_Id = s.WO_Id
                             AND RTRIM(REPLACE(t.Task_Id, CHAR(160), '')) = RTRIM(REPLACE(s.Task_Id, CHAR(160), '')));

DROP TABLE #Task; DROP TABLE #Sub; DROP TABLE #X; DROP TABLE #NS; DROP TABLE #Rel;
