/* ============================================================================
   File      = R3_Print_Attachment_Probe_v1_0_1.sql
   Version   = 1.0.1
   Type      = READ ONLY diagnostic - temp tables only, no writes. T-SQL against the
               Workmate.NET schema, not dialect-portable (a one-off probe, like 01-04).
   DB        = dbWorkmate_RST_Test (RST data as of 26 Aug 2026), run through
               scripts/Invoke-RstTestSql.ps1 (database pinned)
   Author    = Adriaan (Azzmax)
   Purpose   = RST printing fault - Word disconnects (RPC_E_DISCONNECTED) while Workmate.NET
               converts a Word attachment in clsGeneralOperation.CreateImagesFromFiles_WO, and
               every attachment after it in that print is skipped (Take 5 included).
               Where SMP-ME-030-1 (Inspect Air Lube Filter Unit) is used - as a procedure and as a
               plain attachment - on which work orders and PM masters, the failing and working
               work orders side by side, and how much of the RST work order printing goes
               through Word.
   Model     = procedure definitions live in Location_Procedure and Asset_Procedure, and
               Procedure_Path holds either the text itself or a file path. WO_Procs (work orders)
               and WO_Procs-like WO_M_Procs (PM masters) hold Location_ID, Asset_ID and a numeric
               Proc_ID. The print resolves a row as Location_Procedure when Location_ID is above 0,
               otherwise as Asset_Procedure (frmMyWoReports). Plain attachments live in
               WO_Attachment (with Print_Flag) and WO_M_Attachment.
               Open means a WO_N_Header status other than C, D or V.
   Sections  = A definitions / K every column that names the file / D how WO_Procs rows resolve /
               B work orders carrying the Air Lube procedure / C the open ones / E PM masters /
               L work order attachments naming the file / M PM master attachments naming it /
               G named PM masters side by side / H newest work order of each named PM /
               I open work orders by attachment type / J Word files on the most open work orders /
               F counts
   Changelog (newest first)
     1.0.1  2026-09-30  1.0.0 joined WO_Procs on a composite L..P.. key, but WO_Procs keeps
                        Location_ID, Asset_ID and a plain numeric Proc_ID (section D of the first
                        run, and frmWOMaintenance), so every procedure join came back empty. Rows
                        now resolve the way the print does. Added plain attachments (WO_Attachment,
                        WO_M_Attachment) after R3b showed SMP-ME-030 being attached 11 times through
                        wmsp_WO_AttachmentInsertUpdate, a search of every Path/Title/File column in
                        the database, and a count of WO_Procs rows that carry both a Location_ID and
                        an Asset_ID (the save loop in frmWOMaintenance never clears either).
     1.0.0  2026-09-30  initial
   ============================================================================ */
SET NOCOUNT ON;

IF OBJECT_ID('tempdb..#Def') IS NOT NULL DROP TABLE #Def;
CREATE TABLE #Def (
    Lvl          char(1)                               NOT NULL,
    Owner_ID     varchar(20)   COLLATE DATABASE_DEFAULT NOT NULL,
    Owner_Short  varchar(60)   COLLATE DATABASE_DEFAULT NULL,
    Procedure_ID varchar(20)   COLLATE DATABASE_DEFAULT NOT NULL,
    ProcKey      varchar(50)   COLLATE DATABASE_DEFAULT NOT NULL,
    Title        nvarchar(200) COLLATE DATABASE_DEFAULT NULL,
    Req          varchar(5)    COLLATE DATABASE_DEFAULT NULL,
    PrintFlag    varchar(5)    COLLATE DATABASE_DEFAULT NULL,
    Active       varchar(5)    COLLATE DATABASE_DEFAULT NULL,
    PathText     nvarchar(max) COLLATE DATABASE_DEFAULT NULL,
    Ext          varchar(8)    COLLATE DATABASE_DEFAULT NOT NULL DEFAULT '',
    FileName     nvarchar(260) COLLATE DATABASE_DEFAULT NULL
);

INSERT INTO #Def (Lvl, Owner_ID, Procedure_ID, ProcKey, Title, Req, PrintFlag, Active, PathText)
SELECT 'L',
       COALESCE(CAST(TRY_CONVERT(int, p.Location_ID) AS varchar(20)), '?'),
       COALESCE(CAST(TRY_CONVERT(int, p.Procedure_ID) AS varchar(20)), '?'),
       CONCAT('L', TRY_CONVERT(int, p.Location_ID), 'P', TRY_CONVERT(int, p.Procedure_ID)),
       RTRIM(CAST(p.Procedure_Title AS nvarchar(200))),
       RTRIM(CAST(p.Required AS varchar(5))),
       RTRIM(CAST(p.Print_flag AS varchar(5))),
       RTRIM(CAST(p.Active AS varchar(5))),
       LTRIM(RTRIM(CAST(p.Procedure_Path AS nvarchar(max))))
FROM   dbo.Location_Procedure p;

INSERT INTO #Def (Lvl, Owner_ID, Procedure_ID, ProcKey, Title, Req, PrintFlag, Active, PathText)
SELECT 'A',
       COALESCE(CAST(TRY_CONVERT(int, p.Asset_ID) AS varchar(20)), '?'),
       COALESCE(CAST(TRY_CONVERT(int, p.Procedure_ID) AS varchar(20)), '?'),
       CONCAT('A', TRY_CONVERT(int, p.Asset_ID), 'P', TRY_CONVERT(int, p.Procedure_ID)),
       RTRIM(CAST(p.Procedure_Title AS nvarchar(200))),
       RTRIM(CAST(p.Required AS varchar(5))),
       RTRIM(CAST(p.Print_flag AS varchar(5))),
       RTRIM(CAST(p.Active AS varchar(5))),
       LTRIM(RTRIM(CAST(p.Procedure_Path AS nvarchar(max))))
FROM   dbo.Asset_Procedure p;

UPDATE d SET Owner_Short = RTRIM(CAST(l.Short_Location_ID AS varchar(60)))
FROM   #Def d JOIN dbo.Location l ON CAST(TRY_CONVERT(int, l.Location_ID) AS varchar(20)) = d.Owner_ID
WHERE  d.Lvl = 'L';

UPDATE d SET Owner_Short = RTRIM(CAST(a.Short_asset_Id AS varchar(60)))
FROM   #Def d JOIN dbo.Asset a ON CAST(TRY_CONVERT(int, a.Asset_ID) AS varchar(20)) = d.Owner_ID
WHERE  d.Lvl = 'A';

/* attachment type the way Workmate decides it - by the file extension, after a trim */
UPDATE d SET Ext = x.Ext,
             FileName = CASE WHEN x.Ext IN ('docx','doc','dot','pdf','xls','image','txt','path?') AND z.c LIKE N'%\%'
                             THEN LEFT(RIGHT(z.c, CASE WHEN CHARINDEX(N'\', REVERSE(z.c)) > 0 THEN CHARINDEX(N'\', REVERSE(z.c)) - 1 ELSE 0 END), 260) END
FROM   #Def d
CROSS APPLY (SELECT RTRIM(LTRIM(REPLACE(REPLACE(REPLACE(COALESCE(d.PathText, N''), NCHAR(13), N' '), NCHAR(10), N' '), NCHAR(9), N' '))) AS c) z
CROSS APPLY (SELECT CASE
                 WHEN z.c = N''                                        THEN 'empty'
                 WHEN z.c LIKE N'%.docx'                               THEN 'docx'
                 WHEN z.c LIKE N'%.doc'                                THEN 'doc'
                 WHEN z.c LIKE N'%.dot'                                THEN 'dot'
                 WHEN z.c LIKE N'%.pdf'                                THEN 'pdf'
                 WHEN z.c LIKE N'%.xls' OR z.c LIKE N'%.xlsx'          THEN 'xls'
                 WHEN z.c LIKE N'%.jpg' OR z.c LIKE N'%.jpeg' OR z.c LIKE N'%.png'
                   OR z.c LIKE N'%.bmp' OR z.c LIKE N'%.gif'  OR z.c LIKE N'%.tif' THEN 'image'
                 WHEN z.c LIKE N'%.txt'                                THEN 'txt'
                 WHEN z.c LIKE N'[A-Za-z]:\%' OR z.c LIKE N'\\%'       THEN 'path?'
                 ELSE 'text' END AS Ext) x;

IF OBJECT_ID('tempdb..#AirKeys') IS NOT NULL DROP TABLE #AirKeys;
SELECT DISTINCT d.ProcKey INTO #AirKeys
FROM   #Def d
WHERE  d.PathText LIKE N'%SMP-ME-030%' OR d.PathText LIKE N'%Air Filter Lube%' OR d.Title LIKE N'%Air Lube Filter%';

/* WO_Procs resolved the way the print resolves it */
IF OBJECT_ID('tempdb..#WP') IS NOT NULL DROP TABLE #WP;
SELECT w.WO_ID,
       TRY_CONVERT(int, w.Location_ID) AS Loc,
       TRY_CONVERT(int, w.Asset_ID)    AS Ast,
       TRY_CONVERT(int, w.Proc_ID)     AS ProcNo,
       CAST(RTRIM(CAST(w.Printed AS varchar(5))) AS varchar(5)) COLLATE DATABASE_DEFAULT AS Printed,
       CAST(CASE WHEN TRY_CONVERT(int, w.Location_ID) > 0 THEN CONCAT('L', TRY_CONVERT(int, w.Location_ID), 'P', TRY_CONVERT(int, w.Proc_ID))
                 WHEN TRY_CONVERT(int, w.Asset_ID) > 0    THEN CONCAT('A', TRY_CONVERT(int, w.Asset_ID), 'P', TRY_CONVERT(int, w.Proc_ID))
                 ELSE CONCAT('?P', TRY_CONVERT(int, w.Proc_ID)) END AS varchar(50)) COLLATE DATABASE_DEFAULT AS RKey,
       CASE WHEN TRY_CONVERT(int, w.Location_ID) > 0 AND TRY_CONVERT(int, w.Asset_ID) > 0 THEN 1 ELSE 0 END AS BothIds
INTO   #WP
FROM   dbo.WO_Procs w;
CREATE INDEX ix_WP_Key ON #WP (RKey);
CREATE INDEX ix_WP_WO  ON #WP (WO_ID);

IF OBJECT_ID('tempdb..#WMP') IS NOT NULL DROP TABLE #WMP;
CREATE TABLE #WMP (
    WO_ID   int                                   NULL,
    Task    varchar(30) COLLATE DATABASE_DEFAULT  NULL,
    Printed varchar(5)  COLLATE DATABASE_DEFAULT  NULL,
    RKey    varchar(50) COLLATE DATABASE_DEFAULT  NULL,
    BothIds int                                   NULL
);
IF OBJECT_ID('dbo.WO_M_Procs') IS NOT NULL
    INSERT INTO #WMP (WO_ID, Task, Printed, RKey, BothIds)
    SELECT p.WO_ID,
           RTRIM(CAST(p.Task_Id AS varchar(30))),
           RTRIM(CAST(p.Printed AS varchar(5))),
           CASE WHEN TRY_CONVERT(int, p.Location_ID) > 0 THEN CONCAT('L', TRY_CONVERT(int, p.Location_ID), 'P', TRY_CONVERT(int, p.Proc_ID))
                WHEN TRY_CONVERT(int, p.Asset_ID) > 0    THEN CONCAT('A', TRY_CONVERT(int, p.Asset_ID), 'P', TRY_CONVERT(int, p.Proc_ID))
                ELSE CONCAT('?P', TRY_CONVERT(int, p.Proc_ID)) END,
           CASE WHEN TRY_CONVERT(int, p.Location_ID) > 0 AND TRY_CONVERT(int, p.Asset_ID) > 0 THEN 1 ELSE 0 END
    FROM   dbo.WO_M_Procs p;

/* plain work order attachments, typed the same way */
IF OBJECT_ID('tempdb..#WA') IS NOT NULL DROP TABLE #WA;
SELECT a.WO_ID,
       CAST(RTRIM(CAST(a.Print_Flag AS varchar(5))) AS varchar(5)) COLLATE DATABASE_DEFAULT AS Print_Flag,
       CAST(LEFT(RTRIM(CAST(a.Attachment_Title AS nvarchar(200))), 200) AS nvarchar(200)) COLLATE DATABASE_DEFAULT AS Title,
       CAST(z.c AS nvarchar(max)) COLLATE DATABASE_DEFAULT AS PathText,
       CAST(CASE WHEN z.c = N'' THEN 'empty'
                 WHEN z.c LIKE N'%.docx' THEN 'docx' WHEN z.c LIKE N'%.doc' THEN 'doc' WHEN z.c LIKE N'%.dot' THEN 'dot'
                 WHEN z.c LIKE N'%.pdf' THEN 'pdf'
                 WHEN z.c LIKE N'%.xls' OR z.c LIKE N'%.xlsx' THEN 'xls'
                 WHEN z.c LIKE N'%.jpg' OR z.c LIKE N'%.jpeg' OR z.c LIKE N'%.png'
                   OR z.c LIKE N'%.bmp' OR z.c LIKE N'%.gif'  OR z.c LIKE N'%.tif' THEN 'image'
                 WHEN z.c LIKE N'%.txt' THEN 'txt'
                 ELSE 'other' END AS varchar(8)) COLLATE DATABASE_DEFAULT AS Ext,
       CAST(CASE WHEN z.c LIKE N'%\%'
                 THEN LEFT(RIGHT(z.c, CASE WHEN CHARINDEX(N'\', REVERSE(z.c)) > 0 THEN CHARINDEX(N'\', REVERSE(z.c)) - 1 ELSE 0 END), 260)
                 ELSE LEFT(z.c, 260) END AS nvarchar(260)) COLLATE DATABASE_DEFAULT AS FileName
INTO   #WA
FROM   dbo.WO_Attachment a
CROSS APPLY (SELECT RTRIM(LTRIM(REPLACE(REPLACE(COALESCE(CAST(a.Attachment_Path AS nvarchar(max)), N''), NCHAR(13), N''), NCHAR(10), N''))) AS c) z;
CREATE INDEX ix_WA_WO ON #WA (WO_ID);

DECLARE @nDef int, @nAir int, @nWP int, @nWMP int, @nWA int;
SELECT @nDef = COUNT(*) FROM #Def;
SELECT @nAir = COUNT(*) FROM #AirKeys;
SELECT @nWP  = COUNT(*) FROM #WP;
SELECT @nWMP = COUNT(*) FROM #WMP;
SELECT @nWA  = COUNT(*) FROM #WA;
PRINT CONCAT('Definitions = ', @nDef, '; Air Lube procedure keys = ', @nAir, '; WO_Procs rows = ', @nWP,
             '; WO_M_Procs rows = ', @nWMP, '; WO_Attachment rows = ', @nWA);
GO

PRINT '=== A) procedure definitions - SMP-ME-030 / Air Lube first, then Take 5 and the stacker oiler checks ===';
SELECT d.Lvl,
       COALESCE(d.Owner_Short, CONCAT('#', d.Owner_ID)) AS Owner,
       d.ProcKey,
       LEFT(d.Title, 50) AS Title,
       d.Req, d.PrintFlag, d.Active,
       LEFT(REPLACE(REPLACE(REPLACE(COALESCE(d.PathText, N''), NCHAR(13), N' '), NCHAR(10), N' '), N'|', N'/'), 130) AS Path_or_Text,
       d.Ext
FROM   #Def d
WHERE  d.PathText LIKE N'%SMP-ME-030%' OR d.PathText LIKE N'%Air Filter Lube%' OR d.Title LIKE N'%Air Lube%'
   OR  d.Title LIKE N'%Take 5%' OR d.PathText LIKE N'%Take 5 Work Order Version%' OR d.Title LIKE N'%Oiler%'
ORDER BY CASE WHEN d.PathText LIKE N'%SMP-ME-030%' OR d.Title LIKE N'%Air Lube%' THEN 0 ELSE 1 END, d.Title, d.Lvl, d.Owner_Short;
GO

PRINT '=== K) every Path / Title / File column in the database that names SMP-ME-030 or Air Filter Lube ===';
IF OBJECT_ID('tempdb..#K') IS NOT NULL DROP TABLE #K;
CREATE TABLE #K (Tbl nvarchar(260) COLLATE DATABASE_DEFAULT, Col nvarchar(260) COLLATE DATABASE_DEFAULT, N int);
DECLARE @sql nvarchar(max);
SELECT @sql = STRING_AGG(CAST(
           N'INSERT INTO #K (Tbl, Col, N) SELECT ' + QUOTENAME(s.name + N'.' + t.name, N'''') + N', ' + QUOTENAME(c.name, N'''')
         + N', COUNT(*) FROM ' + QUOTENAME(s.name) + N'.' + QUOTENAME(t.name)
         + N' WHERE CAST(' + QUOTENAME(c.name) + N' AS nvarchar(max)) LIKE N''%SMP-ME-030%'''
         + N' OR CAST(' + QUOTENAME(c.name) + N' AS nvarchar(max)) LIKE N''%Air Filter Lube%'';' AS nvarchar(max)), NCHAR(10))
FROM   sys.tables t
JOIN   sys.schemas s ON s.schema_id = t.schema_id
JOIN   sys.columns c ON c.object_id = t.object_id
JOIN   sys.types ty ON ty.user_type_id = c.user_type_id
WHERE  t.is_ms_shipped = 0
  AND  t.name NOT LIKE N'%Backup_PMStartFix%'
  AND  ty.name IN (N'char', N'varchar', N'nchar', N'nvarchar', N'text', N'ntext')
  AND  (c.name LIKE N'%Path%' OR c.name LIKE N'%Title%' OR c.name LIKE N'%File%');
IF @sql IS NOT NULL EXEC sys.sp_executesql @sql;
SELECT Tbl, Col, N FROM #K WHERE N > 0 ORDER BY N DESC, Tbl, Col;
GO

PRINT '=== D) WO_Procs - how the rows resolve (the print takes Location_ID first, then Asset_ID) ===';
SELECT CASE WHEN p.BothIds = 1 THEN 'both ids - taken as location'
            WHEN p.Loc > 0     THEN 'location'
            WHEN p.Ast > 0     THEN 'asset'
            ELSE 'neither' END AS Resolves_As,
       CASE WHEN d.ProcKey IS NULL THEN 'no definition' ELSE 'definition found' END AS Found,
       COUNT(*) AS N_Rows,
       COUNT(DISTINCT p.WO_ID) AS WOs
FROM   #WP p
LEFT JOIN #Def d ON d.ProcKey = p.RKey
GROUP BY CASE WHEN p.BothIds = 1 THEN 'both ids - taken as location'
              WHEN p.Loc > 0     THEN 'location'
              WHEN p.Ast > 0     THEN 'asset'
              ELSE 'neither' END,
         CASE WHEN d.ProcKey IS NULL THEN 'no definition' ELSE 'definition found' END
ORDER BY COUNT(*) DESC;
GO

PRINT '=== B) work orders carrying the Air Lube procedure - by table (N normal / C archive), status and print flag ===';
SELECT x.Src, x.Status, x.Printed, COUNT(DISTINCT x.WO_ID) AS WOs,
       CONVERT(varchar(10), MIN(x.D), 120) AS First_Start,
       CONVERT(varchar(10), MAX(x.D), 120) AS Last_Start
FROM (
    SELECT 'N' AS Src, RTRIM(h.Status) AS Status, p.Printed, p.WO_ID, CAST(h.Request_Start_Date AS date) AS D
    FROM   #WP p JOIN #AirKeys k ON k.ProcKey = p.RKey JOIN dbo.WO_N_Header h ON h.WO_ID = p.WO_ID
    UNION ALL
    SELECT 'C', RTRIM(h.Status), p.Printed, p.WO_ID, CAST(h.Request_Start_Date AS date)
    FROM   #WP p JOIN #AirKeys k ON k.ProcKey = p.RKey JOIN dbo.WO_C_Header h ON h.WO_ID = p.WO_ID
) x
GROUP BY x.Src, x.Status, x.Printed
ORDER BY x.Src, x.Status, x.Printed;
GO

PRINT '=== C) open work orders (not C/D/V) that carry the Air Lube procedure ===';
SELECT RTRIM(h.Short_WO_Id) AS WO,
       RTRIM(h.Status) AS Status,
       CONVERT(varchar(10), h.Request_Start_Date, 120) AS Start_Date,
       p.Printed,
       p.RKey
FROM   #WP p
JOIN   #AirKeys k ON k.ProcKey = p.RKey
JOIN   dbo.WO_N_Header h ON h.WO_ID = p.WO_ID
WHERE  h.Status NOT IN ('C', 'D', 'V')
ORDER BY h.Request_Start_Date, h.Short_WO_Id;
GO

PRINT '=== E) PM masters that carry the Air Lube procedure (WO_M_Procs) ===';
SELECT RTRIM(m.Short_WO_Id) AS PM,
       RTRIM(m.Status) AS PM_Status,
       RTRIM(m.Repeat_Type_Flag) AS Repeat_Type,
       p.Task,
       p.Printed,
       p.RKey
FROM   #WMP p
JOIN   #AirKeys k ON k.ProcKey = p.RKey
JOIN   dbo.WO_M_Header m ON m.WO_ID = p.WO_ID
ORDER BY m.Short_WO_Id, p.Task;
GO

PRINT '=== L) work order attachments (WO_Attachment) that name SMP-ME-030 or Air Filter Lube ===';
SELECT RTRIM(COALESCE(n.Short_WO_Id, c.Short_WO_Id, CONCAT('#', a.WO_ID))) AS WO,
       CASE WHEN n.WO_ID IS NOT NULL THEN 'N' WHEN c.WO_ID IS NOT NULL THEN 'C' ELSE '?' END AS Src,
       RTRIM(COALESCE(n.Status, c.Status)) AS Status,
       CONVERT(varchar(10), COALESCE(n.Request_Start_Date, c.Request_Start_Date), 120) AS Start_Date,
       a.Print_Flag,
       LEFT(a.Title, 40) AS Title,
       LEFT(a.FileName, 60) AS File_Name,
       a.Ext
FROM   #WA a
LEFT JOIN dbo.WO_N_Header n ON n.WO_ID = a.WO_ID
LEFT JOIN dbo.WO_C_Header c ON c.WO_ID = a.WO_ID
WHERE  a.PathText LIKE N'%SMP-ME-030%' OR a.PathText LIKE N'%Air Filter Lube%' OR a.Title LIKE N'%Air Filter Lube%' OR a.Title LIKE N'%Air Lube Filter%'
ORDER BY Src, COALESCE(n.Request_Start_Date, c.Request_Start_Date);
GO

PRINT '=== M) PM master attachments (WO_M_Attachment) that name SMP-ME-030 or Air Filter Lube ===';
IF OBJECT_ID('dbo.WO_M_Attachment') IS NOT NULL
    SELECT RTRIM(m.Short_WO_Id) AS PM,
           RTRIM(m.Status) AS PM_Status,
           RTRIM(CAST(a.Task_ID AS varchar(30))) AS Task,
           LEFT(RTRIM(CAST(a.Attachment_Title AS nvarchar(200))), 40) AS Title,
           LEFT(REPLACE(CAST(a.Attachment_Path AS nvarchar(max)), N'|', N'/'), 130) AS Path_Text
    FROM   dbo.WO_M_Attachment a
    JOIN   dbo.WO_M_Header m ON m.WO_ID = a.WO_ID
    WHERE  CAST(a.Attachment_Path AS nvarchar(max)) LIKE N'%SMP-ME-030%' OR CAST(a.Attachment_Path AS nvarchar(max)) LIKE N'%Air Filter Lube%'
       OR  CAST(a.Attachment_Title AS nvarchar(200)) LIKE N'%Air Filter Lube%' OR CAST(a.Attachment_Title AS nvarchar(200)) LIKE N'%Air Lube Filter%'
    ORDER BY m.Short_WO_Id, a.Task_ID;
ELSE
    PRINT 'table dbo.WO_M_Attachment is missing - section M skipped';
GO

IF OBJECT_ID('tempdb..#Named') IS NOT NULL DROP TABLE #Named;
CREATE TABLE #Named (Pfx varchar(40) COLLATE DATABASE_DEFAULT NOT NULL, Grp varchar(10) COLLATE DATABASE_DEFAULT NOT NULL);
INSERT INTO #Named (Pfx, Grp) VALUES
    ('3CL-COM-014', 'failing'), ('3PL-PMG-009', 'failing'), ('U-LU-00319', 'failing'),
    ('6SR-MEP-002', 'working'), ('2KN-KLM-094', 'working');

PRINT '=== G) the named PM masters side by side - procedures and attachments (failing 3CL-COM-014, 3PL-PMG-009, U-LU-00319 / working 6SR-MEP-002, 2KN-KLM-094) ===';
SELECT n.Grp,
       RTRIM(m.Short_WO_Id) AS PM,
       p.Task,
       'proc' AS Kind,
       p.Printed AS Prt,
       COALESCE(LEFT(d.Title, 45), CONCAT('? ', p.RKey)) AS Title,
       COALESCE(LEFT(d.FileName, 60), N'') AS File_Name,
       COALESCE(d.Ext, '?') AS Ext
FROM   #WMP p
JOIN   dbo.WO_M_Header m ON m.WO_ID = p.WO_ID
JOIN   #Named n ON n.Pfx = RTRIM(m.Short_WO_Id)
LEFT JOIN #Def d ON d.ProcKey = p.RKey
UNION ALL
SELECT n.Grp,
       RTRIM(m.Short_WO_Id),
       RTRIM(CAST(a.Task_ID AS varchar(30))),
       'attach',
       '',
       LEFT(RTRIM(CAST(a.Attachment_Title AS nvarchar(200))), 45),
       LEFT(RIGHT(RTRIM(CAST(a.Attachment_Path AS nvarchar(max))),
                  CASE WHEN CHARINDEX(N'\', REVERSE(RTRIM(CAST(a.Attachment_Path AS nvarchar(max))))) > 0
                       THEN CHARINDEX(N'\', REVERSE(RTRIM(CAST(a.Attachment_Path AS nvarchar(max))))) - 1 ELSE 0 END), 60),
       CASE WHEN RTRIM(CAST(a.Attachment_Path AS nvarchar(max))) LIKE N'%.docx' THEN 'docx'
            WHEN RTRIM(CAST(a.Attachment_Path AS nvarchar(max))) LIKE N'%.doc'  THEN 'doc'
            WHEN RTRIM(CAST(a.Attachment_Path AS nvarchar(max))) LIKE N'%.pdf'  THEN 'pdf'
            ELSE 'other' END
FROM   dbo.WO_M_Attachment a
JOIN   dbo.WO_M_Header m ON m.WO_ID = a.WO_ID
JOIN   #Named n ON n.Pfx = RTRIM(m.Short_WO_Id)
ORDER BY 1, 2, 3, 4, 6;
GO

PRINT '=== H) newest released work order of each named PM, plus 2KN-260921-003 - procedures and attachments ===';
WITH last_wo AS (
    SELECT n.Grp, MAX(h.WO_ID) AS WO_ID
    FROM   #Named n JOIN dbo.WO_N_Header h ON h.Short_WO_Id LIKE n.Pfx + '-%'
    GROUP BY n.Grp, n.Pfx
    UNION ALL
    SELECT 'working', MAX(h.WO_ID) FROM dbo.WO_N_Header h WHERE RTRIM(h.Short_WO_Id) = '2KN-260921-003'
)
SELECT l.Grp,
       RTRIM(h.Short_WO_Id) AS WO,
       RTRIM(h.Status) AS Status,
       CONVERT(varchar(10), h.Request_Start_Date, 120) AS Start_Date,
       'proc' AS Kind,
       p.Printed AS Prt,
       COALESCE(LEFT(d.Title, 45), CONCAT('? ', p.RKey)) AS Title,
       COALESCE(LEFT(d.FileName, 60), N'') AS File_Name,
       COALESCE(d.Ext, '?') AS Ext
FROM   last_wo l
JOIN   dbo.WO_N_Header h ON h.WO_ID = l.WO_ID
JOIN   #WP p ON p.WO_ID = h.WO_ID
LEFT JOIN #Def d ON d.ProcKey = p.RKey
UNION ALL
SELECT l.Grp,
       RTRIM(h.Short_WO_Id),
       RTRIM(h.Status),
       CONVERT(varchar(10), h.Request_Start_Date, 120),
       'attach',
       a.Print_Flag,
       LEFT(a.Title, 45),
       LEFT(a.FileName, 60),
       a.Ext
FROM   last_wo l
JOIN   dbo.WO_N_Header h ON h.WO_ID = l.WO_ID
JOIN   #WA a ON a.WO_ID = h.WO_ID
ORDER BY 1, 2, 5, 7;
GO

PRINT '=== I) open work orders (not C/D/V) - what gets printed, by kind, print flag and attachment type ===';
SELECT x.Kind, x.Prt, COUNT(*) AS N_Rows, COUNT(DISTINCT x.WO_ID) AS WOs, x.Ext
FROM (
    SELECT 'proc' AS Kind, p.Printed AS Prt, p.WO_ID, COALESCE(d.Ext, '?') AS Ext
    FROM   #WP p JOIN dbo.WO_N_Header h ON h.WO_ID = p.WO_ID LEFT JOIN #Def d ON d.ProcKey = p.RKey
    WHERE  h.Status NOT IN ('C', 'D', 'V')
    UNION ALL
    SELECT 'attach', a.Print_Flag, a.WO_ID, a.Ext
    FROM   #WA a JOIN dbo.WO_N_Header h ON h.WO_ID = a.WO_ID
    WHERE  h.Status NOT IN ('C', 'D', 'V')
) x
GROUP BY x.Kind, x.Prt, x.Ext
ORDER BY x.Kind, COUNT(*) DESC;
GO

PRINT '=== J) Word files ticked to print on the most open work orders (not C/D/V) - procedures and attachments ===';
SELECT TOP 20 x.Kind, LEFT(x.File_Name, 70) AS File_Name, COUNT(DISTINCT x.WO_ID) AS Open_WOs
FROM (
    SELECT 'proc' AS Kind, d.FileName AS File_Name, p.WO_ID
    FROM   #WP p JOIN dbo.WO_N_Header h ON h.WO_ID = p.WO_ID JOIN #Def d ON d.ProcKey = p.RKey
    WHERE  h.Status NOT IN ('C', 'D', 'V') AND d.Ext IN ('doc', 'docx', 'dot') AND p.Printed = 'Y'
    UNION ALL
    SELECT 'attach', a.FileName, a.WO_ID
    FROM   #WA a JOIN dbo.WO_N_Header h ON h.WO_ID = a.WO_ID
    WHERE  h.Status NOT IN ('C', 'D', 'V') AND a.Ext IN ('doc', 'docx', 'dot') AND a.Print_Flag = 'Y'
) x
GROUP BY x.Kind, LEFT(x.File_Name, 70)
ORDER BY COUNT(DISTINCT x.WO_ID) DESC;
GO

PRINT '=== F) counts ===';
DECLARE @lp int, @ap int, @def int, @word int, @pdf int, @air int, @wp int, @both int, @bothOpen int, @wmp int, @wmpBoth int, @wa int, @waWordOpen int;
SELECT @lp   = COUNT(*) FROM dbo.Location_Procedure;
SELECT @ap   = COUNT(*) FROM dbo.Asset_Procedure;
SELECT @def  = COUNT(*) FROM #Def;
SELECT @word = COUNT(*) FROM #Def WHERE Ext IN ('doc', 'docx', 'dot');
SELECT @pdf  = COUNT(*) FROM #Def WHERE Ext = 'pdf';
SELECT @air  = COUNT(*) FROM #AirKeys;
SELECT @wp   = COUNT(*), @both = SUM(BothIds) FROM #WP;
SELECT @bothOpen = COUNT(*) FROM #WP p JOIN dbo.WO_N_Header h ON h.WO_ID = p.WO_ID WHERE p.BothIds = 1 AND h.Status NOT IN ('C', 'D', 'V');
SELECT @wmp  = COUNT(*), @wmpBoth = SUM(BothIds) FROM #WMP;
SELECT @wa   = COUNT(*) FROM #WA;
SELECT @waWordOpen = COUNT(*) FROM #WA a JOIN dbo.WO_N_Header h ON h.WO_ID = a.WO_ID WHERE h.Status NOT IN ('C', 'D', 'V') AND a.Ext IN ('doc', 'docx', 'dot') AND a.Print_Flag = 'Y';
SELECT @lp AS Location_Proc, @ap AS Asset_Proc, @def AS Definitions, @word AS Word_Defs, @pdf AS PDF_Defs, @air AS Air_Keys,
       @wp AS WO_Procs, @both AS WO_Procs_Both_Ids, @bothOpen AS Both_Ids_Open, @wmp AS WO_M_Procs, @wmpBoth AS WO_M_Both_Ids,
       @wa AS WO_Attach, @waWordOpen AS Open_Word_Attach_Printed;
GO

DROP TABLE #Named; DROP TABLE #K; DROP TABLE #WA; DROP TABLE #WMP; DROP TABLE #WP; DROP TABLE #AirKeys; DROP TABLE #Def;
