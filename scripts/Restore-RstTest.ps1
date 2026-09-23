# =============================================================================
# Azztec_SaaS_scripts_Restore_RstTest_v1_0_5.ps1  ->  scripts/Restore-RstTest.ps1
# Version:  1.0.5   Date: 2026-09-24   Author: Adriaan
# Spec:     RST PM repair test, slice R1 (chat 2026-09-23). Target name from
#           Azztec_SaaS_RST_Findings_v1_0_0.md s6 ("restore as dbWorkmate_RST_Test").
#
# Stages an RST .bak into C:\SQLBackups (a COPY, never a move - a moved file keeps its old ACL,
# Landmines sB) and restores it as a throwaway test copy on the local instance so Parag's
# 01..04 PM Start_Date scripts can be run against real RST data before RST runs them live.
#
# DRY RUN BY DEFAULT. Without -Write it:
#   1. finds the source file (exact name, then name + .bak, then name*), prints size/attributes
#      (a Dropbox online-only placeholder shows SparseFile/ReparsePoint and hydrates on copy)
#   2. checks sqlcmd + the instance, reads the SQL service account
#   3. refuses any protected name (dbWorkmate, dbWorkmate_KT, dbWorkmate_KT_RFID, system dbs)
#      and refuses a -DbName that already exists (never WITH REPLACE, never an overwrite)
#   4. copies the .bak into -Stage (idempotent: same name + same length = reuse), grants the
#      service account read on the FILE (the engine opens it as the service, not as you)
#   5. RESTORE HEADERONLY  - which database, which server, when, which engine version
#   6. RESTORE FILELISTONLY - logical names and sizes (KT's log was dbTLL_log.ldf; read, don't assume)
#   7. builds the WITH MOVE list to the instance default paths, checks name collisions in
#      sys.master_files, checks free disk on the data drive
#   8. RESTORE VERIFYONLY  - the backup is complete and readable (skip with -SkipVerify)
#   9. PRINTS the RESTORE + ALTER it would run, and stops.
# With -Write it runs steps 1-8 again, then the RESTORE, then SET RECOVERY SIMPLE, then reads the
# new database back (sys.databases row, file sizes, five table counts). Compat level is left as the
# backup carried it on purpose - the scripts must behave as they will at RST.
# No svc_workmate user is created: everything here runs as the Windows login (sqlcmd -E -C).
#
# Usage:
#   .\scripts\Restore-RstTest.ps1                          # dry run, default source + name
#   .\scripts\Restore-RstTest.ps1 -Write                   # after the go on the dry run
#   .\scripts\Restore-RstTest.ps1 -Bak 'C:\path\x.bak' -DbName dbWorkmate_RST_Test -ExpectDbName dbWorkmate
#   .\scripts\Restore-RstTest.ps1 -Bak ... -FileBase dbWorkmate_RST_Test_dev   # physical file names, when the default ones are taken
#
# Gate it on BOTH $? and $LASTEXITCODE. Every failure path ends in exit 1; a thrown exception is
# trapped and also ends in exit 1, so $LASTEXITCODE no longer reports the last native command.
#
# ASCII only (Ways of Working s2, Landmines sA). No colon inside a SQL comment.
#
# What the first RST .bak was (read from its header 2026-09-23, restored, then identified from
# the .NET source): dbWorkmate_QL on RSTSQL01 is NOT the application database. Workmate.NET opens a
# second connection to DatabaseName + "_QL" (clsGeneralOperation.cs 115, frmLogin.cs 1923) and
# writes every INSERT/UPDATE/DELETE it runs into Query_Log there. RST's application database is
# dbWorkmate, so -ExpectDbName defaults to dbWorkmate again; the QL copy was renamed
# dbWorkmate_QL_RST_Test on the instance and kept as evidence. RST is SQL Server 2022 (16.0.1160,
# compat 160), collation SQL_Latin1_General_CP1_CI_AS.
#
# Changelog:
#   1.0.5  -FileBase: the base name for the physical files (default = -DbName). Needed because the
#          QL copy was renamed dbWorkmate_QL_RST_Test but its files kept the names
#          dbWorkmate_RST_Test.mdf / _log.ldf, so the sys.master_files collision check (correctly)
#          refused the next restore under that name. Renaming a database never renames its files;
#          the tidy-up (MODIFY FILE + offline + move) is a separate, later step.
#   1.0.4  -ExpectDbName back to dbWorkmate: 1.0.2 encoded the header's name as the truth, and the
#          header's name was the Query_Log sidecar. The gate was right the first time; the
#          conclusion drawn from the evidence was not. Header comment corrected.
#   1.0.3  The -Write read-back failed AFTER a clean restore (2026-09-23, 229 s, 1,931,842 pages,
#          957 -> 998): CONCAT of sys.databases.name with recovery_model_desc raised Msg 451.
#          The *_desc columns of the catalog views are collated Latin1_General_CI_AS_KS_WS
#          whatever the server collation is (AzztecDev's is SQL_Latin1_General_CP1_CI_AS), so any
#          string operator mixing them with name/physical_name conflicts. COLLATE DATABASE_DEFAULT
#          on every *_desc column in the read-back. Nothing before the read-back changed.
#   1.0.2  The real 1.0.0 bug, found by 1.0.1's raw dump: `@( )` around a function that returns
#          `, $array` nests the array one level deeper. `.Keys` still reads through it (member
#          enumeration unrolls property access) while `.Contains()` binds to the ARRAY's own method
#          and `['name']` indexing returns null - so every key "missed" while the keys were plainly
#          there, and the file list read as 1 file. Functions now return the bare array and the call
#          site's `@( )` does the collecting; Assert-Keys also insists the row is a dictionary.
#          1.0.1's diagnosis (padded names) was wrong: sqlcmd -W trims as documented. Also prints
#          CompressedBackupSize against the staged file length, and -ExpectDbName is dbWorkmate_QL.
#   1.0.1  Trim names and values, check every parsed table for the keys the script needs (raw lines
#          dumped on a miss), instance paths as two scalar reads, read-back rows as single strings,
#          whole body in a try/catch that exits 1, prints which sqlcmd it is. The dump it added is
#          what found the real bug; the trim was not the fix.
#   1.0.0  Initial R1.
# =============================================================================
[CmdletBinding()]
param(
    [string] $Bak          = 'C:\Users\Azzte\Dropbox\Downloads\dbworkmate_ql-14-09-26',
    [string] $Stage        = 'C:\SQLBackups',
    [string] $DbName       = 'dbWorkmate_RST_Test',
    [string] $ExpectDbName = 'dbWorkmate',     # the header's DatabaseName must equal this for -Write ('' = don't check)
    [string] $FileBase     = '',               # base name of the .mdf/.ldf on disk; '' = same as -DbName
    [string] $Server       = 'localhost',
    [string] $ServiceName  = 'MSSQLSERVER',
    [switch] $Write,
    [switch] $SkipVerify
)

$script:VERSION = '1.0.5'
$ErrorActionPreference = 'Stop'
$mode = if ($Write) { 'WRITE' } else { 'DRY RUN' }
if ($FileBase -eq '') { $FileBase = $DbName }
$protected = @('dbWorkmate', 'dbWorkmate_KT', 'dbWorkmate_KT_RFID', 'master', 'model', 'msdb', 'tempdb')

function Say([string] $Tag, [string] $Text) { Write-Host ("[{0}] {1}" -f $Tag, $Text) }
function Fail([string] $Text) { Say 'G' $Text; exit 1 }

# ---- sqlcmd helpers ----------------------------------------------------------
# Native stderr under $ErrorActionPreference = 'Stop' with 2>&1 throws NativeCommandError in PS 5.1,
# so the native call runs under 'Continue' and the exit code is the gate.
function Invoke-Native {
    param([string] $Exe, [string[]] $ArgList)
    $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $out = & $Exe @ArgList 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    $lines = @($out | ForEach-Object { "$_" })
    return , @{ Code = $code; Lines = $lines }
}
function Invoke-Sql {
    param([string] $Query, [string] $Database = 'master', [switch] $NoHeader)
    $a = @('-S', $Server, '-E', '-C', '-b', '-d', $Database, '-W', '-s', '|', '-w', '65535')
    if ($NoHeader) { $a += @('-h', '-1') }
    $flat = $Query.Replace("`r`n", ' ').Replace("`n", ' ')
    $a += @('-Q', $flat)
    $r = Invoke-Native 'sqlcmd' $a
    if ($r.Code -ne 0) { throw ("sqlcmd exit {0} on: {1}`n{2}" -f $r.Code, $flat, ($r.Lines -join "`n")) }
    return $r.Lines
}
# One value: -h -1, first non-empty line, trimmed
function Invoke-SqlScalar {
    param([string] $Query, [string] $Database = 'master')
    $lines = Invoke-Sql -Query $Query -Database $Database -NoHeader
    foreach ($l in $lines) { $t = $l.Trim(); if ($t -ne '' -and $t -notmatch '^\(\d+ rows? affected\)') { return $t } }
    return ''
}
# Every non-empty line of a -h -1 run, trimmed (for single-string rows)
function Invoke-SqlLines {
    param([string] $Query, [string] $Database = 'master')
    $lines = Invoke-Sql -Query $Query -Database $Database -NoHeader
    return @($lines | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' -and $_ -notmatch '^\(\d+ rows? affected\)' })
}
# First result set of a -s "|" run -> array of ordered hashtables keyed by TRIMMED column name.
# Returns the BARE array (no unary comma): the call site wraps it in @( ), and @( ) around a
# `, $array` return would nest it (the 1.0.0 bug). Names and values are trimmed without a pipeline
# so the keys are plain strings.
function ConvertFrom-SqlcmdTable {
    param([string[]] $Lines)
    $rows = @(); $names = $null
    foreach ($l in $Lines) {
        if ($null -eq $names) {
            if ($l -match '\|') { $names = $l.Split('|'); for ($j = 0; $j -lt $names.Count; $j++) { $names[$j] = $names[$j].Trim() } }
            continue
        }
        if ($l -match '^[- |]+$') { continue }
        if ($l.Trim() -eq '' -or $l -match '^\(\d+ rows? affected\)') { break }
        $vals = $l.Split('|'); for ($j = 0; $j -lt $vals.Count; $j++) { $vals[$j] = $vals[$j].Trim() }
        $h = [ordered]@{}
        for ($i = 0; $i -lt $names.Count; $i++) { $h[[string]$names[$i]] = if ($i -lt $vals.Count) { [string]$vals[$i] } else { $null } }
        $rows += , $h
    }
    return $rows
}
# A parsed table must carry the keys the script reads, or the raw lines are shown and the run stops.
function Assert-Keys {
    param([string] $What, [object[]] $Rows, [string[]] $Raw, [string[]] $Keys)
    if ($Rows.Count -lt 1) { Say 'G' ("{0}: no rows parsed. Raw lines:" -f $What); $Raw | Select-Object -First 6 | ForEach-Object { Write-Host ("  > " + $_) }; exit 1 }
    if (-not ($Rows[0] -is [Collections.IDictionary])) { Say 'G' ("{0}: first row is a {1}, not a dictionary - the parser's array is nested again" -f $What, $Rows[0].GetType().Name); exit 1 }
    $missing = @($Keys | Where-Object { -not $Rows[0].Contains([string]$_) })
    if ($missing.Count -gt 0) {
        Say 'G' ("{0}: parsed row lacks {1}. Keys seen: {2}. Raw lines:" -f $What, ($missing -join ', '), (($Rows[0].Keys | Select-Object -First 12) -join ', '))
        $Raw | Select-Object -First 6 | ForEach-Object { Write-Host ("  > " + $_) }
        exit 1
    }
}
function GB([double] $Bytes) { return [math]::Round($Bytes / 1GB, 2) }
$dbVersionNames = @{ '661' = 'SQL 2008 R2'; '706' = 'SQL 2012'; '782' = 'SQL 2014'; '852' = 'SQL 2016'; '869' = 'SQL 2017'; '904' = 'SQL 2019'; '957' = 'SQL 2022'; '998' = 'SQL 2025' }

try {
Write-Host ("Restore-RstTest {0}  mode={1}  target={2}  files={3}.*  server={4}  expected DatabaseName={5}" -f $script:VERSION, $mode, $DbName, $FileBase, $Server, $ExpectDbName)
Write-Host ("Protected names (never restored over): {0}" -f ($protected -join ', '))

# ---- 1. source file ----------------------------------------------------------
$src = $null
if (Test-Path -LiteralPath $Bak -PathType Leaf) { $src = Get-Item -LiteralPath $Bak }
elseif (Test-Path -LiteralPath ($Bak + '.bak') -PathType Leaf) { $src = Get-Item -LiteralPath ($Bak + '.bak') }
else {
    $dir = Split-Path -Parent $Bak; $leaf = Split-Path -Leaf $Bak
    $cands = @()
    if (Test-Path -LiteralPath $dir) { $cands = @(Get-ChildItem -LiteralPath $dir -File -Filter ($leaf + '*')) }
    if ($cands.Count -eq 1) { $src = $cands[0] }
    elseif ($cands.Count -gt 1) { Fail ("More than one file matches {0}*: {1}" -f $Bak, (($cands | ForEach-Object { $_.Name }) -join ', ')) }
    else { Fail ("Source not found: {0} (also tried .bak and {1}*)" -f $Bak, $leaf) }
}
Say 'F' ("source {0}" -f $src.FullName)
$src | Format-List Name, Length, LastWriteTime, Attributes | Out-String | Write-Host
if ($src.Length -le 0) { Fail 'Source file is 0 bytes - a cloud placeholder that has not been downloaded. Make it available offline in Dropbox and re-run.' }
$isOffline = (($src.Attributes -band [IO.FileAttributes]::Offline) -ne 0) -or (($src.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
if ($isOffline) { Say 'F' 'Source carries Offline/ReparsePoint - a cloud placeholder; the copy below hydrates it, which can take a while.' }

# ---- 2. instance + service account ------------------------------------------
if (-not (Get-Command sqlcmd -ErrorAction SilentlyContinue)) { Fail 'sqlcmd not on PATH' }
$ver = Invoke-Native 'sqlcmd' @('-?')
$verLine = @($ver.Lines | Where-Object { $_.Trim() -ne '' } | Select-Object -First 1)
Say 'F' ("sqlcmd is {0} ({1})" -f (Get-Command sqlcmd).Source, ($verLine -join ''))
$inst = Invoke-SqlScalar "SET NOCOUNT ON; SELECT CONCAT(@@SERVERNAME, '  ', CAST(SERVERPROPERTY('ProductVersion') AS varchar(30)), '  ', CAST(SERVERPROPERTY('Edition') AS varchar(60)))"
Say 'F' ("instance {0}" -f $inst)
$svc = Get-CimInstance Win32_Service -Filter ("Name='{0}'" -f $ServiceName) -ErrorAction SilentlyContinue
if ($null -eq $svc) { Fail ("Service {0} not found - pass -ServiceName" -f $ServiceName) }
$svcAccount = $svc.StartName
Say 'F' ("service {0} runs as {1} ({2})" -f $svc.Name, $svcAccount, $svc.State)

# ---- 3. name gates -----------------------------------------------------------
if ($protected -contains $DbName) { Fail ("'{0}' is protected - pick another -DbName" -f $DbName) }
if ($DbName -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') { Fail ("'{0}' is not a plain identifier" -f $DbName) }
if ($FileBase -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') { Fail ("'{0}' is not a plain file base name" -f $FileBase) }
$exists = Invoke-SqlScalar ("SET NOCOUNT ON; SELECT COALESCE(CAST(DB_ID(N'{0}') AS varchar(10)), 'none')" -f $DbName)
if ($exists -ne 'none') { Fail ("Database '{0}' already exists (db_id {1}). This script never restores over anything - drop it by hand first if that is what you mean." -f $DbName, $exists) }
Say 'F' ("no database named {0} on the instance" -f $DbName)

# ---- 4. stage the file -------------------------------------------------------
if (-not (Test-Path -LiteralPath $Stage)) { New-Item -ItemType Directory -Path $Stage | Out-Null; Say 'F' ("created {0}" -f $Stage) }
$stageName = if ($src.Extension -ieq '.bak') { $src.Name } else { $src.Name + '.bak' }
$staged = Join-Path $Stage $stageName
if (Test-Path -LiteralPath $staged) {
    $cur = Get-Item -LiteralPath $staged
    if ($cur.Length -eq $src.Length) { Say 'F' ("already staged, same length ({0} B) - reusing {1}" -f $cur.Length, $staged) }
    else { Fail ("{0} exists with a different length ({1} B vs source {2} B) - not overwriting; move it aside" -f $staged, $cur.Length, $src.Length) }
} else {
    Say 'F' ("copying {0} B to {1} ..." -f $src.Length, $staged)
    $sw = [Diagnostics.Stopwatch]::StartNew()
    Copy-Item -LiteralPath $src.FullName -Destination $staged
    $sw.Stop()
    $cur = Get-Item -LiteralPath $staged
    if ($cur.Length -ne $src.Length) { Fail ("copy length mismatch: {0} vs {1}" -f $cur.Length, $src.Length) }
    Say 'F' ("copied {0} B in {1:n1} s" -f $cur.Length, $sw.Elapsed.TotalSeconds)
}
$ic = Invoke-Native 'icacls' @($staged, '/grant', ("{0}:(R)" -f $svcAccount))
Say 'F' ("icacls grant {0} read (exit {1}): {2}" -f $svcAccount, $ic.Code, ($ic.Lines -join ' '))

# ---- 5. header ---------------------------------------------------------------
$hdrRaw = Invoke-Sql ("RESTORE HEADERONLY FROM DISK = N'{0}'" -f $staged)
$hdrRows = @(ConvertFrom-SqlcmdTable $hdrRaw)
Assert-Keys 'RESTORE HEADERONLY' $hdrRows $hdrRaw @('DatabaseName', 'ServerName', 'BackupType', 'BackupFinishDate', 'DatabaseVersion', 'BackupSize')
Say 'F' ("header: {0} backup set(s) on the media" -f $hdrRows.Count)
$hdr = $hdrRows[$hdrRows.Count - 1]
$show = @('DatabaseName', 'ServerName', 'MachineName', 'UserName', 'BackupName', 'BackupType', 'BackupStartDate', 'BackupFinishDate',
          'BackupSize', 'CompressedBackupSize', 'Compressed', 'HasBackupChecksums', 'IsCopyOnly', 'IsDamaged',
          'SoftwareVersionMajor', 'SoftwareVersionMinor', 'SoftwareVersionBuild', 'DatabaseVersion', 'CompatibilityLevel',
          'Collation', 'RecoveryModel', 'DatabaseCreationDate', 'Position', 'BackupSetGUID')
foreach ($k in $show) { if ($hdr.Contains($k)) { Write-Host ("  {0,-22} {1}" -f $k, $hdr[$k]) } }
$dbv = "$($hdr['DatabaseVersion'])"
$dbvName = if ($dbVersionNames.ContainsKey($dbv)) { $dbVersionNames[$dbv] } else { 'unknown to this script' }
Write-Host ("  {0,-22} {1} = {2}" -f 'DatabaseVersion means', $dbv, $dbvName)
if ("$($hdr['BackupType'])" -ne '1') { Say 'G' ("BackupType is {0}, not 1 (full database) - read before going further" -f $hdr['BackupType']) }
if ($hdr.Contains('CompressedBackupSize') -and "$($hdr['CompressedBackupSize'])" -match '^\d+$') {
    $cbs = [double]$hdr['CompressedBackupSize']; $delta = [double]$cur.Length - $cbs
    $tag = if ($delta -lt 0) { 'G' } else { 'F' }
    Say $tag ("staged file {0} B vs CompressedBackupSize {1} B: file is {2} B {3}" -f $cur.Length, $hdr['CompressedBackupSize'], [math]::Abs($delta), $(if ($delta -lt 0) { 'SHORTER - a truncated copy is a VERIFYONLY question' } else { 'longer (media header)' }))
}
$headerDb = "$($hdr['DatabaseName'])"
$expectFailed = $false
if ($ExpectDbName -ne '' -and $headerDb -ne $ExpectDbName) {
    Say 'G' ("header DatabaseName is '{0}', expected '{1}' - is this really RST's dbWorkmate? -Write will refuse unless -ExpectDbName is changed" -f $headerDb, $ExpectDbName)
    $expectFailed = $true
}

# ---- 6. file list ------------------------------------------------------------
$flRaw = Invoke-Sql ("RESTORE FILELISTONLY FROM DISK = N'{0}'" -f $staged)
$files = @(ConvertFrom-SqlcmdTable $flRaw)
Assert-Keys 'RESTORE FILELISTONLY' $files $flRaw @('LogicalName', 'PhysicalName', 'Type', 'Size')
Say 'F' ("file list: {0} file(s)" -f $files.Count)
$needBytes = 0.0
foreach ($f in $files) {
    $needBytes += [double]$f['Size']
    Write-Host ("  {0,-4} {1,-30} {2,10} GB  {3}" -f $f['Type'], $f['LogicalName'], (GB ([double]$f['Size'])), $f['PhysicalName'])
}

# ---- 7. move list, collisions, disk -----------------------------------------
$dataPath = Invoke-SqlScalar "SET NOCOUNT ON; SELECT CAST(SERVERPROPERTY('InstanceDefaultDataPath') AS nvarchar(260))"
$logPath  = Invoke-SqlScalar "SET NOCOUNT ON; SELECT CAST(SERVERPROPERTY('InstanceDefaultLogPath') AS nvarchar(260))"
if ($dataPath -notmatch '^[A-Za-z]:\\' -or $logPath -notmatch '^[A-Za-z]:\\') { Fail ("instance default paths not read: data '{0}' log '{1}'" -f $dataPath, $logPath) }
if (-not $dataPath.EndsWith('\')) { $dataPath += '\' }
if (-not $logPath.EndsWith('\')) { $logPath += '\' }
Say 'F' ("instance default paths: data {0}  log {1}" -f $dataPath, $logPath)
$moves = @(); $nData = 0; $nLog = 0
foreach ($f in $files) {
    if ("$($f['Type'])" -eq 'L') {
        $nLog++
        $phys = if ($nLog -eq 1) { "{0}{1}_log.ldf" -f $logPath, $FileBase } else { "{0}{1}_log{2}.ldf" -f $logPath, $FileBase, $nLog }
    } else {
        $nData++
        $phys = if ($nData -eq 1) { "{0}{1}.mdf" -f $dataPath, $FileBase } else { "{0}{1}_{2}.ndf" -f $dataPath, $FileBase, $nData }
    }
    $moves += , @{ Logical = "$($f['LogicalName'])"; Physical = $phys }
}
$inList = ($moves | ForEach-Object { "N'" + $_.Physical.Replace("'", "''") + "'" }) -join ', '
$coll = Invoke-SqlScalar ("SET NOCOUNT ON; SELECT COUNT(*) FROM sys.master_files WHERE physical_name IN ({0})" -f $inList)
if ("$coll" -ne '0') { Fail ("{0} target file path(s) are already owned by a database on this instance (sys.master_files)" -f $coll) }
$onDisk = @()
foreach ($m in $moves) {
    try { if (Test-Path -LiteralPath $m.Physical -ErrorAction Stop) { $onDisk += $m.Physical } }
    catch { Say 'F' ("cannot check {0} on disk from this account ({1}) - the engine refuses an existing file itself" -f $m.Physical, $_.Exception.Message) }
}
if ($onDisk.Count -gt 0) { Fail ("target file(s) already on disk: {0}" -f ($onDisk -join ', ')) }
Say 'F' 'no collision in sys.master_files, no target file on disk'
$drive = [IO.DriveInfo]::new($dataPath.Substring(0, 1))
$freeBytes = [double]$drive.AvailableFreeSpace
Say 'F' ("disk {0} free {1} GB; the files need {2} GB" -f $drive.Name, (GB $freeBytes), (GB $needBytes))
if ($freeBytes -lt ($needBytes * 1.1)) { Fail 'not enough free disk (need the file sizes plus 10 percent)' }

# ---- 8. verify ---------------------------------------------------------------
if ($SkipVerify) { Say 'F' 'RESTORE VERIFYONLY skipped (-SkipVerify)' }
else {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $v = Invoke-Sql ("RESTORE VERIFYONLY FROM DISK = N'{0}'" -f $staged)
    $sw.Stop()
    Say 'F' ("VERIFYONLY in {0:n1} s: {1}" -f $sw.Elapsed.TotalSeconds, (($v | Where-Object { $_.Trim() -ne '' }) -join ' / '))
}

# ---- 9. the statement --------------------------------------------------------
$moveSql = ($moves | ForEach-Object { "     MOVE N'{0}' TO N'{1}'" -f $_.Logical.Replace("'", "''"), $_.Physical.Replace("'", "''") }) -join ",`n"
$restoreSql = "RESTORE DATABASE [{0}]`nFROM DISK = N'{1}'`nWITH`n{2},`n     STATS = 10;" -f $DbName, $staged, $moveSql
$alterSql = "ALTER DATABASE [{0}] SET RECOVERY SIMPLE;" -f $DbName
Write-Host ''
Write-Host '---- statement ----'
Write-Host $restoreSql
Write-Host $alterSql
Write-Host '-------------------'

if (-not $Write) {
    Say 'F' ("DRY RUN - nothing created. Header DatabaseName='{0}', {1} file(s), {2} GB needed. Re-run with -Write after the go." -f $headerDb, $files.Count, (GB $needBytes))
    exit 0
}
if ($expectFailed) { Fail ("refusing -Write: header DatabaseName '{0}' is not '{1}'" -f $headerDb, $ExpectDbName) }
if ($hdrRows.Count -ne 1) { Fail ("refusing -Write: {0} backup sets on the media; this script restores a single-set file only" -f $hdrRows.Count) }

# ---- 10. restore -------------------------------------------------------------
Say 'F' ("restoring {0} ..." -f $DbName)
$sw = [Diagnostics.Stopwatch]::StartNew()
$r = Invoke-Sql $restoreSql
$sw.Stop()
foreach ($l in $r) { if ($l.Trim() -ne '') { Write-Host ("  " + $l) } }
Say 'F' ("RESTORE done in {0:n1} s" -f $sw.Elapsed.TotalSeconds)
$null = Invoke-Sql $alterSql
Say 'F' 'RECOVERY SIMPLE set'

# ---- 11. read it back (single-string rows, no table parsing) ----------------
$facts = Invoke-SqlLines ("SET NOCOUNT ON; SELECT CONCAT('db=', name, ' id=', database_id, ' compat=', compatibility_level, ' recovery=', recovery_model_desc COLLATE DATABASE_DEFAULT, ' state=', state_desc COLLATE DATABASE_DEFAULT, ' read_only=', is_read_only, ' created=', CONVERT(varchar(19), create_date, 120), ' collation=', collation_name COLLATE DATABASE_DEFAULT) FROM sys.databases WHERE name = N'{0}'" -f $DbName)
foreach ($l in $facts) { Write-Host ("  " + $l) }
$sizes = Invoke-SqlLines ("SET NOCOUNT ON; SELECT CONCAT(type_desc COLLATE DATABASE_DEFAULT, ' ', name COLLATE DATABASE_DEFAULT, ' ', CAST(CAST(size * 8.0 / 1024 / 1024 AS decimal(10,2)) AS varchar(20)), ' GB  ', physical_name COLLATE DATABASE_DEFAULT) FROM sys.master_files WHERE database_id = DB_ID(N'{0}')" -f $DbName)
foreach ($l in $sizes) { Write-Host ("  " + $l) }
$counts = Invoke-SqlLines -Database $DbName "SET NOCOUNT ON; SELECT CONCAT('db=', DB_NAME(), ' WO_N_Header=', (SELECT COUNT(*) FROM dbo.WO_N_Header), ' WO_C_Header=', (SELECT COUNT(*) FROM dbo.WO_C_Header), ' WO_M_Header=', (SELECT COUNT(*) FROM dbo.WO_M_Header), ' WO_M_Task=', (SELECT COUNT(*) FROM dbo.WO_M_Task), ' WO_M_Subtasks=', (SELECT COUNT(*) FROM dbo.WO_M_Subtasks))"
foreach ($l in $counts) { Write-Host ("  " + $l) }
Say 'F' ("{0} is on the instance, read-write, compat as the backup carried it. Nothing else was touched." -f $DbName)
exit 0
}
catch {
    Say 'G' ("stopped: {0}" -f $_.Exception.Message)
    if ($_.InvocationInfo -and $_.InvocationInfo.Line) { Say 'G' ("at line {0}: {1}" -f $_.InvocationInfo.ScriptLineNumber, $_.InvocationInfo.Line.Trim()) }
    exit 1
}
