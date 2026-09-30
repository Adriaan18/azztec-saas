/* ============================================================================
   File      = R3b_QL_Attachment_History_v1_0_0.sql
   Version   = 1.0.0
   Type      = READ ONLY diagnostic - temp tables only, no writes. T-SQL, not portable.
   DB        = dbWorkmate_QL_RST_Test (the RST Query_Log, Oct 2023 to 14 Sep 2026). Reads the
               procedure keys from dbWorkmate_RST_Test in the same instance. Run with sqlcmd
               -d dbWorkmate_QL_RST_Test (the Invoke-RstTestSql wrapper pins the other database).
   Author    = Adriaan (Azzmax)
   Purpose   = When the "Inspect Air Lube Filter Unit" procedure (SMP-ME-030-1) was defined or
               changed in Workmate, and when it was put on PM masters and work orders - by whom
               and from which form. Companion to R3_Print_Attachment_Probe_v1_0_0.sql.
   Log shape = Workmate.NET writes every INSERT / UPDATE / DELETE it runs, and every stored
               procedure call whose name contains one of those words, into Query_Log
               (clsDatabase). Single quotes are stored as the character & and a stored procedure
               call is logged as  exec  wmsp_Name &value&,&value&,...  so the procedure key is
               matched between an ampersand or a quote on each side. User_Id is the Workmate
               user number.
   Cost      = one full scan of Query_Log (about 19 million rows, 15 GB) - a few minutes.
   Changelog (newest first)
     1.0.0  2026-09-30  initial
   ============================================================================ */
SET NOCOUNT ON;

IF OBJECT_ID('tempdb..#Keys') IS NOT NULL DROP TABLE #Keys;
CREATE TABLE #Keys (
    ProcKey varchar(50) COLLATE DATABASE_DEFAULT NOT NULL,
    Pat     varchar(80) COLLATE DATABASE_DEFAULT NOT NULL
);

INSERT INTO #Keys (ProcKey, Pat)
SELECT s.k, CONCAT('%[&'']', s.k, '[&'']%')
FROM (
    SELECT CONCAT('L', RTRIM(CAST(p.Location_ID AS varchar(20))), 'P', RTRIM(CAST(p.Procedure_ID AS varchar(20)))) COLLATE DATABASE_DEFAULT AS k
    FROM   dbWorkmate_RST_Test.dbo.Location_Procedure p
    WHERE  CAST(p.Procedure_Path AS nvarchar(max)) LIKE N'%SMP-ME-030%'
       OR  CAST(p.Procedure_Path AS nvarchar(max)) LIKE N'%Air Filter Lube%'
       OR  CAST(p.Procedure_Title AS nvarchar(200)) LIKE N'%Air Lube Filter%'
    UNION
    SELECT CONCAT('A', RTRIM(CAST(p.Asset_ID AS varchar(20))), 'P', RTRIM(CAST(p.Procedure_ID AS varchar(20)))) COLLATE DATABASE_DEFAULT
    FROM   dbWorkmate_RST_Test.dbo.Asset_Procedure p
    WHERE  CAST(p.Procedure_Path AS nvarchar(max)) LIKE N'%SMP-ME-030%'
       OR  CAST(p.Procedure_Path AS nvarchar(max)) LIKE N'%Air Filter Lube%'
       OR  CAST(p.Procedure_Title AS nvarchar(200)) LIKE N'%Air Lube Filter%'
) s;

IF OBJECT_ID('tempdb..#Hit') IS NOT NULL DROP TABLE #Hit;
SELECT q.[DateTime] AS At,
       q.[User_Id]  AS Usr,
       RTRIM(CAST(q.[Active_Form] AS varchar(100))) AS Form,
       q.[Query]    AS Q,
       v.Verb,
       v.Tbl,
       CASE WHEN q.[Query] LIKE '%SMP-ME-030%' OR q.[Query] LIKE '%Air Filter Lube%' OR q.[Query] LIKE '%Air Lube Filter%'
            THEN 'names file/title' ELSE 'uses key' END AS Why
INTO   #Hit
FROM   dbo.Query_Log q
CROSS APPLY (SELECT LTRIM(REPLACE(REPLACE(REPLACE(LEFT(q.[Query], 300), CHAR(13), ' '), CHAR(10), ' '), CHAR(9), ' ')) AS s) a
CROSS APPLY (SELECT UPPER(LEFT(a.s, CHARINDEX(' ', a.s + ' ') - 1)) AS w1,
                    LTRIM(SUBSTRING(a.s, CHARINDEX(' ', a.s + ' ') + 1, 300)) AS r1) b
CROSS APPLY (SELECT CASE WHEN UPPER(LEFT(b.r1, 5)) IN ('INTO ', 'FROM ') THEN LTRIM(SUBSTRING(b.r1, 6, 300)) ELSE b.r1 END AS r2) c
CROSS APPLY (SELECT LEFT(b.w1, 12) AS Verb,
                    LEFT(LEFT(c.r2, PATINDEX('%[ (&,]%', c.r2 + ' ') - 1), 80) AS Tbl) v
WHERE  q.[Query] LIKE '%SMP-ME-030%'
   OR  q.[Query] LIKE '%Air Filter Lube%'
   OR  q.[Query] LIKE '%Air Lube Filter%'
   OR  EXISTS (SELECT 1 FROM #Keys k WHERE q.[Query] LIKE k.Pat);

DECLARE @nKeys int, @nHit int, @first varchar(19), @last varchar(19);
SELECT @nKeys = COUNT(*) FROM #Keys;
SELECT @nHit = COUNT(*), @first = CONVERT(varchar(19), MIN(At), 120), @last = CONVERT(varchar(19), MAX(At), 120) FROM #Hit;
PRINT CONCAT('Procedure keys = ', @nKeys, '; logged statements found = ', @nHit, '; first = ', COALESCE(@first, '-'), '; last = ', COALESCE(@last, '-'));
GO

PRINT '=== A) the Air Lube procedure keys looked up in dbWorkmate_RST_Test ===';
SELECT ProcKey, Pat FROM #Keys ORDER BY ProcKey;
GO

PRINT '=== B) logged statements by kind, target and form ===';
SELECT Why, Verb, Tbl, Form, COUNT(*) AS N, COUNT(DISTINCT Usr) AS Users,
       CONVERT(varchar(16), MIN(At), 120) AS First_At,
       CONVERT(varchar(16), MAX(At), 120) AS Last_At
FROM   #Hit
GROUP BY Why, Verb, Tbl, Form
ORDER BY MIN(At);
GO

PRINT '=== C) by month ===';
SELECT CONVERT(varchar(7), At, 120) AS Month_, Why, COUNT(*) AS N
FROM   #Hit
GROUP BY CONVERT(varchar(7), At, 120), Why
ORDER BY 1, 2;
GO

PRINT '=== D) every statement that names the file or the procedure title, oldest first ===';
SELECT CONVERT(varchar(19), At, 120) AS At, Usr, Form,
       LEFT(REPLACE(REPLACE(REPLACE(Q, CHAR(13), ' '), CHAR(10), ' '), '|', '/'), 400) AS Query_Text
FROM   #Hit
WHERE  Why = 'names file/title'
ORDER BY At;
GO

PRINT '=== E) statements that use a procedure key - the first 25 and the last 25 ===';
WITH k AS (
    SELECT h.At, h.Usr, h.Form, h.Q,
           ROW_NUMBER() OVER (ORDER BY h.At)      AS rn_first,
           ROW_NUMBER() OVER (ORDER BY h.At DESC) AS rn_last
    FROM   #Hit h
    WHERE  h.Why = 'uses key'
)
SELECT CONVERT(varchar(19), At, 120) AS At, Usr, Form,
       LEFT(REPLACE(REPLACE(REPLACE(Q, CHAR(13), ' '), CHAR(10), ' '), '|', '/'), 220) AS Query_Text
FROM   k
WHERE  rn_first <= 25 OR rn_last <= 25
ORDER BY At;
GO

DROP TABLE #Hit; DROP TABLE #Keys;
