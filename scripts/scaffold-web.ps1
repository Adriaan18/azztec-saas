<#
Azztec_SaaS_Scaffold_Web_v1_0_1.ps1  ->  scripts/scaffold-web.ps1
Version:  1.0.1   Date: 2026-09-12   Author: Adriaan
Spec:     Azztec_SaaS_S1e_Web_Chunk_Spec_v1_0_0.md s5.1 . OD-21, OD-22
Purpose:  Create and provision web/ ONLY. Never writes outside web/. Idempotent: skips the CLI when
          web/package.json exists, skips pnpm add for packages already present, writes config files
          only when absent, and prints every action it takes or skips.
Run:      from the repo root:   .\scripts\scaffold-web.ps1
Why not Scaffold_Repo v1.0.2 -SkipBackend: its steps 3-4 Set-Content .gitignore, .vscode and .claude
          unconditionally (outside the SkipWeb guard) - on a live repo that clobbers them. Spec s5.1.
Changelog:
  1.0.1  ASCII only - Windows PowerShell 5.1 reads a BOM-less UTF-8 .ps1 as ANSI and mangled the section
         signs. vitest.config.ts imports './vite.config.ts' (Vite native config loader warns without the
         extension) and an existing file is patched. .prettierignore gains dist and src/routeTree.gen.ts.
         package.json loses the dead "pnpm" field that pnpm 12 no longer reads (allowBuilds lives in
         pnpm-workspace.yaml, written by pnpm approve-builds). Step 8 checks eslint.config.js ignores
         the generated client. First run of 1.0.0 on the box: 2026-09-12, blocked by ERR_PNPM_IGNORED_BUILDS.
  1.0.0  Initial.
#>
[CmdletBinding()]
param(
    [switch]$SkipCli   # provision an existing web/ without running the TanStack CLI
)
$ErrorActionPreference = 'Stop'
$VERSION = '1.0.1'

# 0. locate root and guard against the wrong directory
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
Write-Host "== Azztec SaaS scaffold-web $VERSION -> $Root\web ==" -ForegroundColor Cyan
foreach ($must in 'backend\app\main.py', 'docs\api\openapi_0_3_0.json') {
    if (-not (Test-Path $must)) { throw "guard: '$must' not found under $Root - run from the workmate-saas repo" }
}
foreach ($tool in 'node', 'pnpm') {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "guard: $tool not on PATH" }
}

function Say  { param([string]$m) Write-Host ("  " + $m) }
function Did  { param([string]$m) Write-Host ("  + " + $m) -ForegroundColor Green }
function Skip { param([string]$m) Write-Host ("  = " + $m + " (already there)") -ForegroundColor DarkGray }
function Warn { param([string]$m) Write-Host ("  ! " + $m) -ForegroundColor Yellow }

function Read-Pkg {
    return (Get-Content 'package.json' -Raw | ConvertFrom-Json)
}
function Has-Dep {
    param($pkg, [string]$name)
    $d  = $pkg.dependencies    ; $dd = $pkg.devDependencies
    return (($d  -and $d.PSObject.Properties[$name]) -or ($dd -and $dd.PSObject.Properties[$name]))
}
function Ensure-Deps {
    # installs only the missing ones, in one pnpm add call
    param([string[]]$names, [switch]$Dev)
    $pkg = Read-Pkg
    $missing = @($names | Where-Object { -not (Has-Dep $pkg $_) })
    $present = @($names | Where-Object {      (Has-Dep $pkg $_) })
    foreach ($p in $present) { Skip $p }
    if ($missing.Count -eq 0) { return }
    if ($Dev) { pnpm add -D @missing } else { pnpm add @missing }
    if ($LASTEXITCODE -ne 0) { throw "pnpm add failed for: $($missing -join ' ') - if the error is ERR_PNPM_IGNORED_BUILDS, run 'pnpm approve-builds' in web\ and re-run this script" }
    foreach ($m in $missing) { Did "added $m$(if ($Dev) { ' (dev)' })" }
}
function Ensure-Line {
    # append a line to a text file if no line equals it
    param([string]$file, [string]$line)
    $lines = @()
    if (Test-Path $file) { $lines = @(Get-Content $file) }
    if ($lines -contains $line) { Skip "$file has '$line'"; return }
    Add-Content $file $line
    Did "$file += '$line'"
}

# 1. the CLI (OD-21). --router-only disables --add-ons, so Query is added by hand in step 3.
if (-not $SkipCli -and -not (Test-Path 'web\package.json')) {
    Write-Host "`n-- 1. tanstack create (router-only, eslint)" -ForegroundColor Cyan
    pnpm dlx @tanstack/cli@latest create web --router-only --toolchain eslint --no-examples --package-manager pnpm --no-git -y
    if ($LASTEXITCODE -ne 0) { throw "tanstack create exited $LASTEXITCODE - nothing else was done" }
    if (-not (Test-Path 'web\package.json')) { throw "tanstack create returned 0 but web\package.json is missing" }
    Did "web\ created"
} else {
    Write-Host "`n-- 1. tanstack create" -ForegroundColor Cyan
    Skip "web\package.json exists - CLI not run"
}

Push-Location 'web'
try {
    # 2. what the CLI gave us - facts, printed, not assumed
    Write-Host "`n-- 2. inventory of the scaffold" -ForegroundColor Cyan
    $pkg = Read-Pkg
    foreach ($f in 'eslint.config.js', 'eslint.config.mjs', 'eslint.config.ts', 'prettier.config.js', 'prettier.config.mjs', '.prettierrc', '.prettierrc.json', 'biome.json', 'tsconfig.json', 'vite.config.ts', '.cta.json', 'pnpm-workspace.yaml') {
        if (Test-Path $f) { Say "has $f" }
    }
    $hasPrettierCfg = @('prettier.config.js', 'prettier.config.mjs', '.prettierrc', '.prettierrc.json') | Where-Object { Test-Path $_ }
    Say ("prettier config: " + $(if ($hasPrettierCfg) { $hasPrettierCfg -join ', ' } else { 'NONE' }))
    Say ("tailwind: " + $(if (Has-Dep $pkg 'tailwindcss') { 'present' } else { 'ABSENT' }))
    if ((Has-Dep $pkg '@tailwindcss/vite') -and (Has-Dep $pkg '@tailwindcss/postcss')) {
        Warn "both @tailwindcss/vite and @tailwindcss/postcss present (Landmines C) - keep only @tailwindcss/vite; NOT removed by this script"
    }

    # 3. runtime deps. Query first: --router-only cannot add it.
    Write-Host "`n-- 3. runtime deps" -ForegroundColor Cyan
    Ensure-Deps @('@tanstack/react-query', 'date-fns', '@date-fns/tz', 'zustand', 'zod')

    # 4. dev deps: generator, devtools, test stack
    Write-Host "`n-- 4. dev deps" -ForegroundColor Cyan
    Ensure-Deps -Dev @('@hey-api/openapi-ts', '@tanstack/react-query-devtools', 'vitest', '@vitejs/plugin-react', 'jsdom', '@testing-library/react', '@testing-library/dom')

    # 5. Prettier by hand if the eslint add-on did not bring it (it does on @tanstack/cli 0.71.0 - verified 2026-09-12)
    Write-Host "`n-- 5. prettier" -ForegroundColor Cyan
    $pkg = Read-Pkg
    if (-not (Has-Dep $pkg 'prettier')) {
        Ensure-Deps -Dev @('prettier', 'eslint-config-prettier')
    } else { Skip 'prettier' }
    if (-not $hasPrettierCfg) {
        Set-Content 'prettier.config.js' "/** Landmines C: LF on Windows or ESLint and git fight on every file. */`nexport default { endOfLine: 'lf', semi: true, singleQuote: true, printWidth: 110 };`n"
        Did 'wrote prettier.config.js (endOfLine lf)'
    } else { Skip 'prettier config' }
    Ensure-Line '.prettierignore' 'dist'
    Ensure-Line '.prettierignore' 'src/routeTree.gen.ts'

    # 6. vite proxy + package.json scripts + dead pnpm field, applied with node so JSON/TS stay valid
    Write-Host "`n-- 6. vite proxy + package.json" -ForegroundColor Cyan
    Set-Content 'patch-web.cjs' @'
const fs = require("fs");
const pkg = JSON.parse(fs.readFileSync("package.json", "utf8"));
pkg.scripts = pkg.scripts || {};
const want = {
  "gen:api": "openapi-ts",
  "test": "vitest run",
  "test:watch": "vitest",
  "lint": pkg.scripts.lint || "eslint .",
};
const changed = [];
for (const [k, v] of Object.entries(want)) { if (pkg.scripts[k] !== v) { pkg.scripts[k] = v; changed.push(k); } }
if (pkg.pnpm !== undefined) {
  console.log("  + removed dead package.json 'pnpm' field (pnpm 12 ignores it; allowBuilds lives in pnpm-workspace.yaml): " + JSON.stringify(pkg.pnpm));
  delete pkg.pnpm;
} else {
  console.log("  = no 'pnpm' field in package.json (already there)");
}
fs.writeFileSync("package.json", JSON.stringify(pkg, null, 2) + "\n");
console.log("  + scripts " + (changed.length ? "set: " + changed.join(", ") : "unchanged"));
const vc = fs.existsSync("vite.config.ts") ? "vite.config.ts" : "vite.config.js";
let s = fs.readFileSync(vc, "utf8");
if (s.includes("proxy")) {
  console.log("  = " + vc + " proxy (already there)");
} else if (/defineConfig\(\{/.test(s)) {
  s = s.replace(/defineConfig\(\{/, "defineConfig({\n  server: { proxy: { '/api': 'http://localhost:8000', '/docs': 'http://localhost:8000', '/openapi.json': 'http://localhost:8000' } },");
  fs.writeFileSync(vc, s);
  console.log("  + " + vc + " proxy /api,/docs,/openapi.json -> 8000");
} else {
  console.log("  ! " + vc + " has no defineConfig({ - proxy NOT patched, do it by hand");
}
if (fs.existsSync("vitest.config.ts")) {
  let t = fs.readFileSync("vitest.config.ts", "utf8");
  if (t.includes("from './vite.config'")) {
    fs.writeFileSync("vitest.config.ts", t.replace("from './vite.config'", "from './vite.config.ts'"));
    console.log("  + vitest.config.ts: './vite.config' -> './vite.config.ts'");
  }
}
'@
    node patch-web.cjs
    if ($LASTEXITCODE -ne 0) { throw 'patch-web.cjs failed' }
    Remove-Item 'patch-web.cjs'

    # 7. vitest config, separate from vite.config so the router plugin config stays untouched
    Write-Host "`n-- 7. vitest config" -ForegroundColor Cyan
    if (-not (Test-Path 'vitest.config.ts')) {
        Set-Content 'vitest.config.ts' @'
// vitest.config.ts - S1e. Merges the app's vite config; test-only settings live here.
import { defineConfig, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config.ts';

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      include: ['src/**/*.test.{ts,tsx}'],
      exclude: ['src/api/client/**', 'node_modules/**', 'dist/**'],
    },
  }),
);
'@
        Did 'wrote vitest.config.ts'
    } else { Skip 'vitest.config.ts' }

    # 8. delivered config cards - check, don't write
    Write-Host "`n-- 8. delivered configs" -ForegroundColor Cyan
    if (Test-Path 'openapi-ts.config.ts') { Say 'has openapi-ts.config.ts' } else { Warn 'openapi-ts.config.ts missing - drop the card before pnpm gen:api' }
    if ((Test-Path 'eslint.config.js') -and ((Get-Content 'eslint.config.js' -Raw) -match 'src/api/client')) {
        Say 'eslint.config.js ignores src/api/client'
    } else {
        Warn 'eslint.config.js does not ignore src/api/client - pnpm lint will fail on generated code; drop the eslint config card'
    }

    # 9. versions, for the raw log
    Write-Host "`n-- 9. versions" -ForegroundColor Cyan
    Say ("node " + (node -v)) ; Say ("pnpm " + (pnpm -v))
    pnpm ls @hey-api/openapi-ts @tanstack/react-query @tanstack/react-router vitest date-fns react typescript vite --depth 0
    Say ("pnpm-lock.yaml: " + $(if (Test-Path 'pnpm-lock.yaml') { 'present' } else { 'MISSING' }))
}
finally { Pop-Location }

Write-Host @"

== done ==
next (spec s9):  cd web ; pnpm gen:api ; pnpm lint ; pnpm test ; pnpm build
"@ -ForegroundColor Cyan
