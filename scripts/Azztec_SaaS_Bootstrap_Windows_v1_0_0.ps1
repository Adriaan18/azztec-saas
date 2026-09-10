<#
Azztec_SaaS_Bootstrap_Windows_v1_0_0.ps1
Version:  1.0.0   Date: 2026-09-10   Author: Adriaan
Spec:     Azztec_SaaS_Dev_Environment_Install_v1_0_0.md §2
Purpose:  Install (or verify) every tool the Workmate SaaS dev environment needs, via winget, then print a version block.
Run:      admin PowerShell 7:  Set-ExecutionPolicy -Scope Process Bypass; .\Azztec_SaaS_Bootstrap_Windows_v1_0_0.ps1
Switches: -WithSqlServer (SQL Server 2025 Developer, only if you have no instance)  -WithDBeaver  -SkipDocker  -SkipClaude
Idempotent: already-installed packages are skipped.
Changelog: 1.0.0 initial.
#>
[CmdletBinding()]
param(
    [switch]$WithSqlServer,
    [switch]$WithDBeaver,
    [switch]$SkipDocker,
    [switch]$SkipClaude
)
$ErrorActionPreference = 'Continue'
$VERSION = '1.0.0'
Write-Host "== Azztec SaaS bootstrap $VERSION ==" -ForegroundColor Cyan

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "winget not found - install 'App Installer' from the Microsoft Store, then re-run." -ForegroundColor Red
    exit 1
}

function Install-Pkg {
    param([string]$Id, [string]$Label)
    $installed = winget list --id $Id -e --accept-source-agreements 2>$null | Select-String -SimpleMatch $Id
    if ($installed) { Write-Host "  = $Label ($Id) already installed" -ForegroundColor DarkGray; return }
    Write-Host "  + installing $Label ($Id)" -ForegroundColor Green
    winget install -e --id $Id --accept-package-agreements --accept-source-agreements --silent
    if ($LASTEXITCODE -ne 0) { Write-Host "    ! winget returned $LASTEXITCODE for $Id - install it manually if the check below fails" -ForegroundColor Yellow }
}

$packages = @(
    @{ Id = 'Git.Git';                              Label = 'Git' },
    @{ Id = 'Microsoft.PowerShell';                 Label = 'PowerShell 7' },
    @{ Id = 'Microsoft.WindowsTerminal';            Label = 'Windows Terminal' },
    @{ Id = 'Microsoft.VisualStudioCode';           Label = 'VS Code' },
    @{ Id = 'astral-sh.uv';                         Label = 'uv' },
    @{ Id = 'OpenJS.NodeJS.LTS';                    Label = 'Node.js 24 LTS' },
    @{ Id = 'pnpm.pnpm';                            Label = 'pnpm' },
    @{ Id = 'Microsoft.msodbcsql.18';               Label = 'ODBC Driver 18 for SQL Server' },
    @{ Id = 'Microsoft.SQLServerManagementStudio';  Label = 'SSMS' }
)
if (-not $SkipDocker)  { $packages += @{ Id = 'Docker.DockerDesktop';               Label = 'Docker Desktop' } }
if ($WithSqlServer)    { $packages += @{ Id = 'Microsoft.SQLServer.2025.Developer';  Label = 'SQL Server 2025 Developer' } }
if ($WithDBeaver)      { $packages += @{ Id = 'DBeaver.DBeaver.Community';            Label = 'DBeaver' } }

foreach ($p in $packages) { Install-Pkg -Id $p.Id -Label $p.Label }

# refresh PATH for this session so the checks below see the new tools
$env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')

if (-not $SkipClaude) {
    if (Get-Command claude -ErrorAction SilentlyContinue) {
        Write-Host "  = Claude Code already installed" -ForegroundColor DarkGray
    } else {
        Write-Host "  + installing Claude Code (native installer)" -ForegroundColor Green
        try { Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression } catch { Write-Host "    ! Claude Code install failed: $_  (alternative: winget install Anthropic.ClaudeCode)" -ForegroundColor Yellow }
        $env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')
    }
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "  + uv python install 3.13" -ForegroundColor Green
    uv python install 3.13
}

function Show-Version { param([string]$Name, [scriptblock]$Cmd)
    try { $v = (& $Cmd 2>&1 | Select-Object -First 1); Write-Host ("  {0,-14} {1}" -f $Name, $v) } catch { Write-Host ("  {0,-14} MISSING" -f $Name) -ForegroundColor Red }
}
Write-Host "`n== version block (paste into the chat) ==" -ForegroundColor Cyan
Show-Version 'git'     { git --version }
Show-Version 'pwsh'    { $PSVersionTable.PSVersion.ToString() }
Show-Version 'uv'      { uv --version }
Show-Version 'python'  { uv python find 3.13 }
Show-Version 'node'    { node -v }
Show-Version 'pnpm'    { pnpm -v }
Show-Version 'docker'  { docker --version }
Show-Version 'claude'  { claude --version }
Show-Version 'code'    { code --version }
$odbc = Get-OdbcDriver -ErrorAction SilentlyContinue | Where-Object Name -like 'ODBC Driver 18*' | Select-Object -First 1
if ($odbc) { Write-Host ("  {0,-14} {1} ({2})" -f 'odbc18', $odbc.Name, $odbc.Platform) } else { Write-Host ("  {0,-14} MISSING" -f 'odbc18') -ForegroundColor Red }
Write-Host "`nNext: Install doc §3 (SQL Server auth/login) -> §4 (restore RST) -> §5 (scaffold)." -ForegroundColor Cyan
