<#
Azztec_SaaS_Probe_RST_v1_0_0.ps1
Version:  1.0.0   Date: 2026-09-10   Author: Adriaan
Spec:     Azztec_SaaS_Data_Layer_and_RST_DB_v1_0_0.md §8.1-8.6
Purpose:  Run the §8 probes against a restored dbWorkmate and print one labelled block per probe,
          so the whole §4 check is a single run and a single paste.

READ-ONLY: every statement below is a SELECT. No INSERT / UPDATE / DELETE / DDL, no writes of any
          kind. Safe to run against real RST data. There is deliberately no -Execute switch.

Run:      powershell / pwsh, from anywhere:
              .\Azztec_SaaS_Probe_RST_v1_0_0.ps1 | Tee-Object -FilePath .\probe_rst.txt
          Windows auth by default (needs read on dbWorkmate). For the SQL login instead:
              .\Azztec_SaaS_Probe_RST_v1_0_0.ps1 -Username svc_workmate -Password '<pw>'

Needs:    Import-Module SqlServer (22.x). Probes that hit a missing table report the error and the
          run continues - RST is pre-Ignition, so several 8.4/8.5 tables are expected to be absent.

Changelog: 1.0.0 initial.
#>
[CmdletBinding()]
param(
    [string]$ServerInstance = 'localhost',
    [string]$Database       = 'dbWorkmate',
    [string]$Username,
    [string]$Password
)

$ErrorActionPreference = 'Continue'
$VERSION = '1.0.0'

Write-Host ("== Azztec SaaS RST probes {0} -> {1}\{2} ==" -f $VERSION, $ServerInstance, $Database) -ForegroundColor Cyan
Write-Host ("   run {0}  (read-only)" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) -ForegroundColor DarkGray

if (-not (Get-Module -ListAvailable -Name SqlServer)) {
    Write-Host "! SqlServer module not found - Install-Module SqlServer -Scope CurrentUser" -ForegroundColor Red
    exit 1
}
Import-Module SqlServer -ErrorAction Stop

# common args for every call
$conn = @{
    ServerInstance         = $ServerInstance
    Database               = $Database
    TrustServerCertificate = $true
    QueryTimeout           = 300
    ErrorAction            = 'Stop'
}
if ($Username) { $conn['Username'] = $Username; $conn['Password'] = $Password }

$script:ok   = 0
$script:fail = 0

function Probe {
    param([string]$Label, [string]$Sql)
    Write-Host ""
    Write-Host ("-- {0} " -f $Label).PadRight(78, '-') -ForegroundColor Cyan
    try {
        $rows = Invoke-Sqlcmd @conn -Query $Sql
        if ($null -eq $rows -or @($rows).Count -eq 0) {
            Write-Host "   (no rows)" -ForegroundColor DarkGray
        } else {
            ($rows | Format-Table -AutoSize | Out-String -Width 200).TrimEnd() | Write-Host
        }
        $script:ok++
    } catch {
        Write-Host ("   ! {0}" -f $_.Exception.Message) -ForegroundColor Yellow
        $script:fail++
    }
}

# ---------------------------------------------------------------- 8.1 shape
Probe '8.1a database shape' @'
SELECT DB_NAME() AS db, compatibility_level, collation_name, state_desc, recovery_model_desc
FROM sys.databases WHERE name = DB_NAME();
'@

Probe '8.1b work order counts and date range' @'
SELECT (SELECT COUNT(*) FROM dbo.WO_N_Header) AS wo_open_tbl,
       (SELECT COUNT(*) FROM dbo.WO_C_Header) AS wo_closed_tbl,
       (SELECT MIN(Request_Start_Date) FROM dbo.WO_N_Header) AS first_start,
       (SELECT MAX(Request_Start_Date) FROM dbo.WO_N_Header) AS last_start;
'@

# ------------------------------------------------- 8.2 domains the rules need
Probe '8.2a status x type domains (drives cat / engineOwned)' @'
SELECT RTRIM(Status) AS s, RTRIM(WO_Type_Flag) AS t, COUNT(*) AS n
FROM dbo.WO_N_Header GROUP BY RTRIM(Status), RTRIM(WO_Type_Flag) ORDER BY 3 DESC;
'@

Probe '8.2b Users.Active domain' @'
SELECT RTRIM(Active) AS a, COUNT(*) AS n FROM dbo.Users GROUP BY RTRIM(Active);
'@

Probe '8.2c User_Skill.Active domain' @'
SELECT RTRIM(Active) AS a, COUNT(*) AS n FROM dbo.User_Skill GROUP BY RTRIM(Active);
'@

Probe '8.2d UOM - the LRStd hours unit (uomHours)' @'
SELECT UOM_Id, RTRIM(UOM_Title) AS uom_title, RTRIM(LRStd) AS lrstd
FROM dbo.Unit_of_Measure WHERE RTRIM(LRStd) IN ('Y','1');
'@

Probe '8.2e internal suppliers (drives worker.internal)' @'
SELECT Supplier_ID, RTRIM(Short_Supplier_Id) AS short_id, RTRIM(Internal_Dept) AS internal_dept
FROM dbo.Supplier WHERE RTRIM(Internal_Dept) IN ('1','Y');
'@

Probe '8.2f priorities' @'
SELECT Priority_Id, RTRIM(Short_Priority_Id) AS short_id, RTRIM(Colour) AS colour, Sort_Sequence
FROM dbo.Priority ORDER BY Sort_Sequence;
'@

# -------------------------------------------------- 8.3 time-of-day share
Probe '8.3 pct of Request_Start_Date carrying a time (KT was ~50%)' @'
SELECT COUNT(*) AS rows_with_date,
       SUM(CASE WHEN CAST(Request_Start_Date AS time) <> '00:00:00' THEN 1 ELSE 0 END) AS with_time,
       SUM(CASE WHEN CAST(Request_Start_Date AS time) <> '00:00:00' THEN 1 ELSE 0 END) * 100.0
         / NULLIF(COUNT(*),0) AS pct_with_time
FROM dbo.WO_N_Header WHERE Request_Start_Date IS NOT NULL;
'@

# ------------------------------------------------ 8.4 Ignition-era tables
Probe '8.4a Ignition-era tables present? (WO_N_Plan absent => OD-1 locked PMs)' @'
SELECT name FROM sys.tables
WHERE name IN ('WO_N_Plan','WO_Event_History','Diag_Log','Module_Settings','App_User')
ORDER BY name;
'@

Probe '8.4b PLANNER_* configuration switches' @'
SELECT RTRIM(System_ConfigCol) AS cfg_col, RTRIM(System_ConfigVal) AS cfg_val
FROM dbo.System_Configuration WHERE System_ConfigCol LIKE 'PLANNER%';
'@

# ------------------------------------- 8.5 labour history depth (planner_ai)
Probe '8.5a WO_N_Activity labour, last 730 days' @'
SELECT COUNT(*) AS rows_l, SUM(Quantity) AS hrs, COUNT(DISTINCT User_ID) AS people
FROM dbo.WO_N_Activity
WHERE RTRIM(Trx_Type) = 'L' AND Activity_Date >= DATEADD(day,-730,CURRENT_TIMESTAMP);
'@

Probe '8.5b WO_C_Activity labour, last 730 days' @'
SELECT COUNT(*) AS rows_l, SUM(Quantity) AS hrs, COUNT(DISTINCT User_ID) AS people
FROM dbo.WO_C_Activity
WHERE RTRIM(Trx_Type) = 'L' AND Activity_Date >= DATEADD(day,-730,CURRENT_TIMESTAMP);
'@

# ------------------------------------------ 8.6 triggers (OUTPUT clause hazard)
Probe '8.6 triggers (OUTPUT clause hazard - Landmines)' @'
SELECT OBJECT_NAME(parent_id) AS tbl, name AS trigger_name, is_disabled
FROM sys.triggers WHERE parent_id <> 0 ORDER BY 1, 2;
'@

Write-Host ""
Write-Host ("== probes complete: {0} ok, {1} failed ==" -f $script:ok, $script:fail) -ForegroundColor Cyan
Write-Host "Paste this whole output into the chat. Differences vs the KT facts in Landmines §E" -ForegroundColor DarkGray
Write-Host "become a dated line in the raw log, and an OD in the port spec if they change a rule." -ForegroundColor DarkGray
