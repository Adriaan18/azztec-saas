# =============================================================================
# Azztec_SaaS_scripts_Invoke_RstTestSql_v1_0_6.ps1  ->  scripts/Invoke-RstTestSql.ps1
# Version:  1.0.6   Date: 2026-09-30   Author: Adriaan
# Spec:     RST PM repair test, slices R2/R4 (chat 2026-09-23/24, OD-83/84). Runs one .sql file
#           against dbWorkmate_RST_Test and nothing else.
#
# WHY A WRAPPER: Parag's 01..04 scripts carry no USE - they run in whatever database the
# connection is in. 02 with @Commit = 1 against dbWorkmate (dev) or any other database would
# write there. This script PINS the database: it is a constant, not a parameter, and the
# file is refused if its code contains a USE statement or a three-part name into a protected db.
#
# What it does:
#   1. reads the file, strips comments, refuses USE / dbWorkmate[.._KT/_KT_RFID].(dbo|sys). references,
#      prints its header Version line so the log shows which version ran
#   2. -Set '@Name=value','@Name2=value2' (an array, or one comma-separated string; PowerShell does
#      not allow a parameter twice): rewrites each literal DECLARE in a COPY of the file under the
#      log dir (the source is never edited), prints the line before and after, runs the copy.
#      Only a DECLARE whose value is a quoted string or an integer literal can be set; a computed
#      one (02's @sfx = REPLACE(...)) is refused. Not allowed with -OnDevReadOnly.
#   3. proves the context (DB_NAME(), @@SERVERNAME, GETDATE()) on the pinned database
#   4. runs it with sqlcmd -E -C -b -d <pinned> -W -s "|" -i <file>, saves the whole output to
#      logs\rst_test\<name>_<yyyyMMdd_HHmmss>.txt
#   5. prints a summary: every "=== ... ===" section with its row count and, where a section's
#      last column has few distinct values (Flag, Action), a tally; the D) and F) blocks in full;
#      every line that reports a count, a suffix, a commit, a rollback or an error
#   6. exit code: 1 if sqlcmd failed OR the output carries a Msg NNNN / "ERROR - rolled back" line
#      (02/03 catch their own errors and PRINT them, so sqlcmd -b alone reports success); gate on it
#
# -OnDevReadOnly: runs the file against the dev copy dbWorkmate instead (RST's real data as of the
# 26 Aug backup) for READ-ONLY diagnostics only (01), while a real RST .bak is awaited. Guards:
#   - static: the code may not contain BEGIN TRAN / COMMIT / ROLLBACK, INSERT INTO / DELETE FROM /
#     SELECT INTO / CREATE TABLE / DROP TABLE on anything but a #temp table, TRUNCATE, ALTER, MERGE,
#     EXEC( / sp_executesql (a word inside a PRINT string counts too - conservative on purpose)
#   - runtime: the file runs between a BEGIN TRAN (XACT_ABORT ON) and a ROLLBACK from two guard
#     files, and the guard's own PRINT line must close the output with trancount=0
#
# Usage:
#   .\scripts\Invoke-RstTestSql.ps1 -File .\scripts\rst_pm_repair\01_Identify_Wrong_WO_M_Task_StartDate_v1_0_1.sql
#   .\scripts\Invoke-RstTestSql.ps1 -File .\scripts\rst_pm_repair\02_Repair_WO_M_Task_StartDate_v1_0_1.sql
#   .\scripts\Invoke-RstTestSql.ps1 -File <02> -Set '@Commit=1','@SkipGapTasks=1'
#   .\scripts\Invoke-RstTestSql.ps1 -File <04> -Set '@sfx=20260924_0630'
#   .\scripts\Invoke-RstTestSql.ps1 -File <01> -OnDevReadOnly
#
# ASCII only (Ways of Working s2, Landmines sA). No colon inside a SQL comment.
#
# Changelog:
#   1.0.6  Two summary bugs found by R3 v1.0.0 (2026-09-30). (1) The "Label : value" filter that keeps
#          02's count lines out of the row count also threw away every result row holding a drive
#          path (O:\...), so section A showed 0 rows while the log held them - the filter now only
#          applies to lines without a column separator. (2) The Version line is found as
#          "Version :" or "Version =" (the R3 probes keep colons out of SQL comments).
#   1.0.5  A script's own CATCH ("ERROR - rolled back: ...") or a Msg line now makes the wrapper exit
#          1. 03 v1.0.0 failed to compile in the rehearsal, its CATCH printed the error, sqlcmd
#          exited 0, and the block chained on to the commit as if the dry run had passed.
#   1.0.4  -Set usage: an array ('@a=1','@b=2') or one comma-separated string, never the switch
#          twice - 1.0.3's header said "repeatable", which PowerShell refuses. Values quoted in the
#          examples because a bare @Name is splatting syntax to PowerShell.
#   1.0.3  Row counting: once a section's column-name row carried a pipe, only lines with a pipe are
#          rows. 1.0.2 counted 02's closing "*** DRY RUN ... ***" line as a header row (141 vs the
#          140 the script itself printed). The echoed count lines were right; the section count lied.
#   1.0.2  Section parser accepts any "=== title ===" header (02/03/04 have no letter), tallies the
#          last column of a section when it is a small enum, echoes count/suffix/commit/rollback
#          lines. -Set @Name=value rewrites a literal DECLARE in a copy of the file so 02 commit,
#          04 and 03 can be run without hand-editing the source. Full rewrite of 1.0.1.
#   1.0.1  -OnDevReadOnly: read-only diagnostics against dev dbWorkmate under a static check plus a
#          BEGIN TRAN / ROLLBACK wrap. Comment stripping before the static checks.
#   1.0.0  Initial R2.
# =============================================================================
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $File,
    [string[]] $Set = @(),          # '@Name=value','@Name2=value2' (array or comma-separated); rewrites literal DECLAREs in a copy
    [string]   $Server  = 'localhost',
    [string]   $LogDir  = 'logs\rst_test',
    [int]      $Preview = 5,        # rows echoed per section
    [switch]   $OnDevReadOnly       # run against dev dbWorkmate, static-checked + wrapped in a rolled-back transaction
)

$script:VERSION = '1.0.6'
$ErrorActionPreference = 'Stop'
$Database = if ($OnDevReadOnly) { 'dbWorkmate' } else { 'dbWorkmate_RST_Test' }   # PINNED on purpose - not a parameter
$protected = @('dbWorkmate', 'dbWorkmate_KT', 'dbWorkmate_KT_RFID')

function Say([string] $Tag, [string] $Text) { Write-Host ("[{0}] {1}" -f $Tag, $Text) }
function Fail([string] $Text) { Say 'G' $Text; exit 1 }
function Invoke-Native {
    param([string] $Exe, [string[]] $ArgList)
    $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $out = & $Exe @ArgList 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    return , @{ Code = $code; Lines = @($out | ForEach-Object { "$_" }) }
}
function Invoke-SqlScalar([string] $Query, [string] $Db) {
    $r = Invoke-Native 'sqlcmd' @('-S', $Server, '-E', '-C', '-b', '-d', $Db, '-W', '-h', '-1', '-Q', $Query)
    if ($r.Code -ne 0) { throw ("sqlcmd exit {0}: {1}" -f $r.Code, ($r.Lines -join ' ')) }
    foreach ($l in $r.Lines) { $t = $l.Trim(); if ($t -ne '') { return $t } }
    return ''
}

try {
Write-Host ("Invoke-RstTestSql {0}  database={1} (pinned)  server={2}  mode={3}" -f $script:VERSION, $Database, $Server, $(if ($OnDevReadOnly) { 'DEV READ-ONLY (guarded)' } else { 'TEST COPY' }))

# ---- 1. the file -------------------------------------------------------------
if (-not (Test-Path -LiteralPath $File -PathType Leaf)) { Fail ("file not found: {0}" -f $File) }
$fi = Get-Item -LiteralPath $File
$text = Get-Content -LiteralPath $fi.FullName -Raw
# the checks read the CODE: block and line comments stripped first (04's header has a line that starts with "Use")
$code = [regex]::Replace($text, '(?s)/\*.*?\*/', ' ')
$code = [regex]::Replace($code, '(?m)--.*$', '')
if ($code -match '(?im)^\s*USE\s') { Fail 'file contains a USE statement - it would leave the pinned database. Refused.' }
foreach ($p in $protected) {
    if ($code -match ('(?i)\b' + [regex]::Escape($p) + '\s*\.\s*(dbo|sys)\s*\.')) { Fail ("file references {0}.dbo. - a protected database. Refused." -f $p) }
}
$verLine = ($text -split "`r?`n" | Where-Object { $_ -match '^\s*Version\s*[:=]' } | Select-Object -First 1)
$verText = if ($verLine) { $verLine.Trim() } else { 'no Version line (unversioned file)' }
Say 'F' ("file {0}  {1} B  {2}" -f $fi.Name, $fi.Length, $verText)
if ($code -match '(?im)^\s*DECLARE\s+@Commit\s+bit\s*=\s*(\d)') { Say 'F' ("file declares @Commit = {0}" -f $Matches[1]) }
if ($OnDevReadOnly) {
    $bad = @()
    if ($code -match '(?i)\b(BEGIN\s+TRAN|COMMIT|ROLLBACK)\b') { $bad += 'transaction statements' }
    if ($code -match '(?i)\b(INSERT\s+INTO|DELETE\s+FROM|DELETE)\s+(?!#)[\[A-Za-z]') { $bad += 'INSERT/DELETE on a non-temp table' }
    if ($code -match '(?i)\bINTO\s+(?!#)[\[A-Za-z]') { $bad += 'SELECT INTO a non-temp table' }
    if ($code -match '(?i)\b(CREATE|DROP)\s+TABLE\s+(?!#)[\[A-Za-z]') { $bad += 'CREATE/DROP of a non-temp table' }
    if ($code -match '(?i)\b(TRUNCATE|ALTER|MERGE)\b') { $bad += 'TRUNCATE/ALTER/MERGE' }
    if ($code -match '(?i)\bEXEC\s*\(|sp_executesql') { $bad += 'dynamic SQL' }
    if ($bad.Count -gt 0) { Fail ("-OnDevReadOnly refused: file contains {0}. Only read-only diagnostics (01) run on dev." -f ($bad -join '; ')) }
    Say 'F' 'static check passed: no transaction statements, no writes to permanent tables, no dynamic SQL'
}

# ---- 2. -Set: rewrite literal DECLAREs in a copy ----------------------------
if (-not (Test-Path -LiteralPath $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$runFile = $fi.FullName
if ($Set.Count -gt 0) {
    if ($OnDevReadOnly) { Fail '-Set is not allowed with -OnDevReadOnly' }
    $new = $text; $tag = ''
    $Set = @($Set | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
    foreach ($s in $Set) {
        if ($s -notmatch '^@?([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { Fail ("-Set '{0}' is not @Name=value" -f $s) }
        $name = $Matches[1]; $value = $Matches[2]
        $rx = [regex]('(?im)^(\s*DECLARE\s+@' + [regex]::Escape($name) + '\s+[A-Za-z0-9_]+(?:\([^)]*\))?\s*=\s*)(''(?:[^'']|'''')*''|[0-9]+)(\s*;)')
        $m = $rx.Matches($new)
        if ($m.Count -ne 1) { Fail ("-Set @{0}: found {1} literal DECLARE line(s) for it (need exactly 1; a computed value cannot be set)" -f $name, $m.Count) }
        $old = $m[0].Groups[2].Value
        if ($old.StartsWith("'")) { $lit = "'" + $value.Replace("'", "''") + "'" }
        elseif ($value -match '^[0-9]+$') { $lit = $value }
        else { Fail ("-Set @{0}: the DECLARE holds an integer, '{1}' is not one" -f $name, $value) }
        $before = $m[0].Value; $after = $m[0].Groups[1].Value + $lit + $m[0].Groups[3].Value
        $new = $new.Substring(0, $m[0].Index) + $after + $new.Substring($m[0].Index + $m[0].Length)
        Say 'F' ("set @{0}: {1}  ->  {2}" -f $name, $before.Trim(), $after.Trim())
        $tag += ('_' + $name + '-' + ($value -replace '[^A-Za-z0-9]', ''))
    }
    $runFile = Join-Path (Resolve-Path $LogDir) ([IO.Path]::GetFileNameWithoutExtension($fi.Name) + '__set' + $tag + '.sql')
    Set-Content -LiteralPath $runFile -Value $new -Encoding UTF8 -NoNewline
    Say 'F' ("running the modified copy {0} (source untouched)" -f $runFile)
}

# ---- 3. the context ----------------------------------------------------------
if (-not (Get-Command sqlcmd -ErrorAction SilentlyContinue)) { Fail 'sqlcmd not on PATH' }
$exists = Invoke-SqlScalar ("SET NOCOUNT ON; SELECT COALESCE(CAST(DB_ID(N'{0}') AS varchar(10)), 'none')" -f $Database) 'master'
if ($exists -eq 'none') { Fail ("{0} is not on the instance - run Restore-RstTest.ps1 first" -f $Database) }
$ctx = Invoke-SqlScalar "SET NOCOUNT ON; SELECT CONCAT('db=', DB_NAME(), ' server=', @@SERVERNAME, ' at=', CONVERT(varchar(19), GETDATE(), 120), ' login=', SUSER_SNAME())" $Database
Say 'F' ("context {0}" -f $ctx)
if ($ctx -notmatch ('^db=' + [regex]::Escape($Database) + ' ')) { Fail ("context is not {0} - stopping" -f $Database) }

# ---- 4. run it ---------------------------------------------------------------
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$outFile = Join-Path $LogDir ("{0}_{1}.txt" -f [IO.Path]::GetFileNameWithoutExtension($fi.Name), $stamp)
$inputs = $runFile
if ($OnDevReadOnly) {
    $g1 = Join-Path (Resolve-Path $LogDir) '_guard_begin.sql'; $g2 = Join-Path (Resolve-Path $LogDir) '_guard_end.sql'
    Set-Content -LiteralPath $g1 -Value "SET XACT_ABORT ON; BEGIN TRANSACTION; PRINT '=== guard: transaction opened on ' + DB_NAME() + ' ===';" -Encoding ASCII
    Set-Content -LiteralPath $g2 -Value "IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION; PRINT '=== guard: rolled back, trancount=' + CAST(@@TRANCOUNT AS varchar(5)) + ' ===';" -Encoding ASCII
    $inputs = "{0},{1},{2}" -f $g1, $runFile, $g2
    Say 'F' 'runtime guard: BEGIN TRANSACTION before the file, ROLLBACK after it'
}
Say 'F' ("running {0} ..." -f [IO.Path]::GetFileName($runFile))
$sw = [Diagnostics.Stopwatch]::StartNew()
$r = Invoke-Native 'sqlcmd' @('-S', $Server, '-E', '-C', '-b', '-d', $Database, '-W', '-s', '|', '-w', '65535', '-i', $inputs)
$sw.Stop()
$header = @(("# {0}  file={1}  {2}  ran={3}  db={4}  exit={5}  seconds={6:n1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $fi.Name, $verText, [IO.Path]::GetFileName($runFile), $Database, $r.Code, $sw.Elapsed.TotalSeconds), ("# context {0}" -f $ctx), '')
Set-Content -LiteralPath $outFile -Value ($header + $r.Lines) -Encoding UTF8
Say 'F' ("sqlcmd exit {0} in {1:n1} s; {2} output lines saved to {3}" -f $r.Code, $sw.Elapsed.TotalSeconds, $r.Lines.Count, $outFile)

# ---- 5. summary --------------------------------------------------------------
$sections = [ordered]@{}; $cur = $null; $n = 0
foreach ($l in $r.Lines) {
    if ($l -match '^===\s*(.+?)\s*===\s*$') {
        $title = $Matches[1]; $n++
        $key = if ($title -match '^([A-Z0-9])\)') { $Matches[1] } else { ('S' + $n) }
        $cur = $key; $sections[$cur] = @{ Title = $title; Lines = @() }; continue
    }
    if ($null -ne $cur) { $sections[$cur].Lines += , $l }
}
if ($sections.Count -eq 0) {
    Say 'F' 'no === section headers in the output; first 40 lines follow'
    $r.Lines | Select-Object -First 40 | ForEach-Object { Write-Host ("  | " + $_) }
} else {
    foreach ($k in $sections.Keys) {
        $body = @($sections[$k].Lines)
        $data = @($body | Where-Object { $_.Trim() -ne '' -and $_ -notmatch '^[- |]+$' -and $_ -notmatch '^\(\d+ rows? affected\)' -and $_ -notmatch '^\s*Msg\s+\d+' -and -not ($_ -notmatch '\|' -and $_ -match '^[A-Za-z*].*\S\s*:\s*\S') })
        $rows = @(); $seenNames = $false; $piped = $false
        foreach ($d in $data) {
            if (-not $seenNames) { if ($d -match '\|' -or $data.Count -eq 1) { $seenNames = $true; $piped = ($d -match '\|') }; continue }
            if ($piped -and $d -notmatch '\|') { continue }
            $rows += , $d
        }
        Say 'F' ("section {0}: {1} row(s)  === {2} ===" -f $k, $rows.Count, $sections[$k].Title)
        if ($k -in @('D', 'F')) { $body | Where-Object { $_.Trim() -ne '' -and $_ -notmatch '^=== guard' } | ForEach-Object { Write-Host ("  | " + $_) } }
        elseif ($rows.Count -gt 0) {
            $tally = @{}
            foreach ($row in $rows) { $v = ($row.Split('|'))[-1].Trim(); if ($v -eq '') { $v = '(none)' }; if ($tally.ContainsKey($v)) { $tally[$v]++ } else { $tally[$v] = 1 } }
            if ($tally.Count -le 8) { Say 'F' ("section {0} last-column tally: {1}" -f $k, (($tally.Keys | Sort-Object | ForEach-Object { "{0}={1}" -f $_, $tally[$_] }) -join ', ')) }
            $rows | Select-Object -First $Preview | ForEach-Object { Write-Host ("  {0}| {1}" -f $k, $_) }
        }
    }
}
$key = @($r.Lines | Where-Object { $_ -match '^\s*Msg\s+\d+|^ERROR|rows (updated|restored)|Residue|Backup tables|Rollback:|backup suffix|COMMITTED|DRY RUN|RESTORED from|differing from|mismatches|earlier than last|No @sfx|not found|no current row|no backup row|^=== guard' })
foreach ($e in $key) { Say $(if ($e -match 'COMMITTED|RESTORED from') { 'S' } elseif ($e -match '^\s*Msg|^ERROR|not found') { 'G' } else { 'F' }) ("  " + $e.Trim()) }
if ($OnDevReadOnly -and -not (($r.Lines | Where-Object { $_ -match '^=== guard: rolled back, trancount=0' }) | Select-Object -First 1)) { Say 'G' 'the guard did not report a clean rollback - read the log before trusting anything above' }
if ($r.Code -ne 0) { Fail ("sqlcmd reported an error (exit {0}) - read {1}" -f $r.Code, $outFile) }
$errLines = @($r.Lines | Where-Object { $_ -match '^\s*Msg\s+\d+|^ERROR' })
if ($errLines.Count -gt 0) { Fail ("the script reported {0} error line(s) - nothing it printed after that counts; read {1}" -f $errLines.Count, $outFile) }
exit 0
}
catch {
    Say 'G' ("stopped: {0}" -f $_.Exception.Message)
    if ($_.InvocationInfo -and $_.InvocationInfo.Line) { Say 'G' ("at line {0}: {1}" -f $_.InvocationInfo.ScriptLineNumber, $_.InvocationInfo.Line.Trim()) }
    exit 1
}
