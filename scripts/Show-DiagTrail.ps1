# =============================================================================
# Azztec_SaaS_scripts_Show_DiagTrail_v1_0_1.ps1  ->  scripts/Show-DiagTrail.ps1
# Version:  1.0.1   Date: 2026-09-19   Author: Adriaan
# Spec:     Azztec_SaaS_D1a_Persist_Chunk_Spec_v1_0_0.md s3.6 . OD-55, OD-56
#
# The trail-read rule's reader: after every test, the test identity's rows over the test window, pasted
# verbatim, compared with the predicted trail in the spec's smoke section.
#
# It goes straight at the table with sqlcmd rather than through the API on purpose - it still works when
# the app will not boot, which is exactly when the trail matters most. Read-only: it never writes.
#
# Rows come back OLDEST LAST so a paste reads in the order things happened. Detail is cut to -DetailChars
# with a trailing marker; the full text is in the table (and in the viewer, once D1b ships).
#
# Usage:
#   .\scripts\Show-DiagTrail.ps1                        # everyone, last 15 minutes
#   .\scripts\Show-DiagTrail.ps1 -UserId 21 -Minutes 30
#   .\scripts\Show-DiagTrail.ps1 -ProblemsOnly          # [E] and [G] only
#
# ASCII only (Ways of Working s5). No colon inside a SQL comment - text() is not the only reader that
# would take it for a bind, and the habit is cheap.
#
# Changelog:
#   1.0.1  Rows written in one batch share Logged_At (CURRENT_TIMESTAMP is the statement's clock), so the
#          sort is Logged_At THEN Diag_Id - identity order is emission order. Seen on the first table read.
#          A downloaded .ps1 carries Mark-of-the-Web; Unblock-File once, or it will not load (RemoteSigned).
#   1.0.0  Initial D1a.
# =============================================================================
[CmdletBinding()]
param(
    [int]    $UserId = 0,
    [int]    $Minutes = 15,
    [switch] $ProblemsOnly,
    [int]    $Rows = 200,
    [int]    $DetailChars = 300,
    [string] $Server = 'localhost',
    [string] $Database = 'dbWorkmate'
)

$problems = if ($ProblemsOnly) { 1 } else { 0 }

$sql = @"
SET NOCOUNT ON;
SELECT DB_NAME() AS db;
SELECT
    CONVERT(varchar(23), T.Logged_At, 121)                  AS Logged_At,
    COALESCE(CAST(T.Wm_User_Id AS varchar(10)), '-')        AS Usr,
    COALESCE(T.User_Name, '')                               AS User_Name,
    T.Tier,
    T.Source,
    T.Message,
    CASE WHEN LEN(COALESCE(T.Detail, '')) > $DetailChars
         THEN LEFT(T.Detail, $DetailChars) + ' ...'
         ELSE COALESCE(T.Detail, '') END                    AS Detail,
    T.Session_Id
FROM (
    SELECT TOP ($Rows)
        L.Diag_Id, L.Logged_At, L.Wm_User_Id, RTRIM(U.User_Name) AS User_Name,
        L.Tier, L.Source, L.Message, L.Detail, L.Session_Id
    FROM dbo.Diag_Log L
    LEFT JOIN dbo.Users U ON U.User_Id = L.Wm_User_Id
    WHERE ($UserId = 0 OR L.Wm_User_Id = $UserId)
      AND ($problems = 0 OR L.Tier IN ('E', 'G'))
      AND L.Logged_At >= DATEADD(minute, -$Minutes, CURRENT_TIMESTAMP)
    ORDER BY L.Logged_At DESC, L.Diag_Id DESC
) T
ORDER BY T.Logged_At ASC, T.Diag_Id ASC;
"@

Write-Host ("Diag trail - user {0}, last {1} min, problemsOnly={2}, {3} on {4}" -f `
    $(if ($UserId) { $UserId } else { 'everyone' }), $Minutes, [bool]$ProblemsOnly, $Database, $Server)

sqlcmd -S $Server -E -C -d $Database -W -s "|" -Q $sql
if ($LASTEXITCODE -ne 0) { Write-Host "sqlcmd exit $LASTEXITCODE" }
