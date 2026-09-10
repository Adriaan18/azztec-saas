<#
Azztec_SaaS_Scaffold_Repo_v1_0_0.ps1
Version:  1.0.0   Date: 2026-09-10   Author: Adriaan
Spec:     Azztec_SaaS_Dev_Environment_Install_v1_0_0.md §5, Architecture §5 (repo layout), Claude Code Workflow §2
Purpose:  Create the workmate-saas monorepo: layout, backend (uv, pinned deps, starter files), web (TanStack CLI scaffold +
          libs + /api proxy + gen:api), docs mirror, .claude baseline, git init + first commit.
Run:      pwsh:  .\Azztec_SaaS_Scaffold_Repo_v1_0_0.ps1 -Root C:\dev\workmate-saas -Kit C:\dev\azztec-saas-kit
Needs:    bootstrap done (git, uv, node, pnpm on PATH); the kit folder holds every Azztec_SaaS_* file plus the
          workmate_planner_*.py / PlannerCalendar_*.json reference sources.
Changelog: 1.0.0 initial.
#>
[CmdletBinding()]
param(
    [string]$Root = 'C:\dev\workmate-saas',
    [string]$Kit  = 'C:\dev\azztec-saas-kit',
    [switch]$SkipWeb
)
$ErrorActionPreference = 'Stop'
$VERSION = '1.0.0'
Write-Host "== Azztec SaaS scaffold $VERSION -> $Root ==" -ForegroundColor Cyan
if (-not (Test-Path $Kit)) { throw "Kit folder not found: $Kit" }

function Latest { param([string]$Pattern)
    $f = Get-ChildItem -Path $Kit -Filter $Pattern -File | Sort-Object Name | Select-Object -Last 1
    if (-not $f) { throw "kit file missing: $Pattern" }
    return $f.FullName
}
function Put { param([string]$Pattern, [string]$Dest)
    $src = Latest $Pattern
    New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
    Copy-Item $src $Dest -Force
    Write-Host ("  {0,-42} <- {1}" -f (Resolve-Path $Dest -Relative), (Split-Path $src -Leaf))
}

# 1. layout
$dirs = 'backend\app\core','backend\app\planner','backend\tests','backend\alembic\versions','web','docs\raw','docs\reference','scripts','.claude\rules','.claude\skills','.vscode'
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path (Join-Path $Root $d) | Out-Null }
Set-Location $Root

# 2. starter files (highest version in the kit wins)
Put 'Azztec_SaaS_pyproject_v*.toml'        'backend\pyproject.toml'
Put 'Azztec_SaaS_app_main_v*.py'           'backend\app\main.py'
Put 'Azztec_SaaS_app_core_config_v*.py'    'backend\app\core\config.py'
Put 'Azztec_SaaS_app_core_db_v*.py'        'backend\app\core\db.py'
Put 'Azztec_SaaS_app_core_diag_v*.py'      'backend\app\core\diag.py'
Put 'Azztec_SaaS_test_smoke_v*.py'         'backend\tests\test_smoke.py'
Put 'Azztec_SaaS_dotenv_example_v*.txt'    'backend\.env.example'
Put 'Azztec_SaaS_docker_compose_v*.yml'    'docker-compose.yml'
Put 'Azztec_SaaS_CLAUDE_md_v*.md'          'CLAUDE.md'
foreach ($f in 'backend\app\__init__.py','backend\app\core\__init__.py','backend\app\planner\__init__.py','backend\tests\__init__.py') {
    if (-not (Test-Path $f)) { New-Item -ItemType File -Path $f -Force | Out-Null }
}
Set-Content 'backend\.python-version' '3.13'
Set-Content 'backend\README.md' "# workmate-saas backend`n`nuv run fastapi dev app/main.py"
Get-ChildItem $Kit -Filter 'Azztec_SaaS_*.md' | Where-Object Name -notlike 'Azztec_SaaS_CLAUDE_md*' | Copy-Item -Destination 'docs' -Force
Get-ChildItem $Kit -Include 'workmate_planner_*.py','PlannerCalendar_*.json','Workmate_PG_Forward_Compat*.md','Workmate_Planner_Assistant_Prompts*.md' -File -Recurse | Copy-Item -Destination 'docs\reference' -Force
Get-ChildItem $Kit -Filter 'Azztec_SaaS_*.ps1' | Copy-Item -Destination 'scripts' -Force

# 3. repo hygiene
Set-Content '.gitattributes' "* text=auto eol=lf`n*.ps1 text eol=crlf`n*.bak binary"
Set-Content '.gitignore' @'
.env
.env.*
!.env.example
*.bak
backend/.venv/
backend/.pytest_cache/
backend/.ruff_cache/
__pycache__/
web/node_modules/
web/dist/
web/test-results/
web/playwright-report/
.claude/settings.local.json
'@
Set-Content '.vscode\settings.json' @'
{
  "files.eol": "\n",
  "editor.formatOnSave": true,
  "[python]": { "editor.defaultFormatter": "charliermarsh.ruff", "editor.codeActionsOnSave": { "source.organizeImports": "explicit" } },
  "[typescript]": { "editor.defaultFormatter": "esbenp.prettier-vscode" },
  "[typescriptreact]": { "editor.defaultFormatter": "esbenp.prettier-vscode" },
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/Scripts/python.exe",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["backend/tests"]
}
'@

# 4. .claude baseline (Claude Code Workflow §5)
Set-Content '.claude\settings.json' @'
{
  "permissions": {
    "allow": [
      "Bash(uv run *)", "Bash(uv sync*)", "Bash(uv lock*)", "Bash(uvx library-skills*)",
      "Bash(pnpm *)", "Bash(git status*)", "Bash(git diff*)", "Bash(git log*)", "Bash(git add *)", "Bash(git commit *)", "Bash(git tag *)",
      "Bash(ruff *)", "Bash(pytest*)"
    ],
    "deny": [
      "Bash(git push --force*)", "Bash(rm -rf *)", "Bash(Remove-Item * -Recurse*)",
      "Read(**/.env)", "Read(**/.env.*)", "Read(**/*.bak)",
      "Bash(uv run alembic downgrade*)", "Bash(sqlcmd *)"
    ]
  }
}
'@
Set-Content '.claude\rules\sql.md' @'
# SQL rules (apply to backend/app/**/sql.py and any SQL string)
- Portable form only: COALESCE not ISNULL, CURRENT_TIMESTAMP not GETDATE(), CONCAT() not +, OFFSET/FETCH (with ORDER BY) not TOP, always dbo. prefix, no bracket-quoted identifiers.
- Anything MSSQL-only gets a line above it: `-- PG-CONVERT: <what changes on PostgreSQL>`.
- No `:colon` inside SQL comments (SQLAlchemy text() treats it as a bind). Escape a literal colon as `\:`.
- RTRIM() every legacy char(n) column in SELECT and in comparisons.
- Named binds `:name`; lists via `bindparam(name, expanding=True)`.
- Never write SCOPE_IDENTITY() or RETURNING in module SQL — call `db.insert_returning_id()`.
- Header per statement: `# name:`, `# dialect: portable | MSSQL-specific — see PG-CONVERT tags (n)`, `# params:`.
'@
Set-Content '.claude\rules\tests.md' @'
# Test rules (apply to backend/tests/**)
- Pair rule: every new/changed library module ships with tests in the same slice.
- Pure rules tests use plain dicts, no database.
- DB tests use the rolled-back connection fixture; nothing commits. The dev DB holds real RST data.
- Any function that writes keeps `dry_run=True` as its default; never call it with `dry_run=False` in a test.
- HTTP tests use TestClient with dependency overrides for the actor.
'@
Set-Content '.claude\rules\frontend.md' @'
# Frontend rules (apply to web/**)
- `src/api/client/**` is generated by `pnpm gen:api` — never edit; regenerate after backend contract changes.
- All Date handling goes through `src/lib/dates.ts` (date-fns civil-day arithmetic). Never `new Date("YYYY-MM-DD")`.
- Server state = TanStack Query (array keys, staleTime > 0, refetchIntervalInBackground false); client state = Zustand.
- Drag/drop = @dnd-kit/core: one DndContext, PointerSensor distance 6, pointerWithin, DragOverlay; droppable id = ISO date, draggable id = `wo-<id>`.
- Planner JSON keys are the Ignition contract — do not rename in the UI layer either.
- shadcn/ui components are owned source under src/components/ui; add via `pnpm dlx shadcn@latest add <name>`.
'@

# 5. backend deps
Write-Host "`n-- backend: uv sync" -ForegroundColor Cyan
Push-Location 'backend'
uv python pin 3.13 | Out-Null
uv sync
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env'; Write-Host "  created backend\.env - fill WORKMATE_DB_PASSWORD and WORKMATE_SECRET_KEY" -ForegroundColor Yellow }
Pop-Location

# 6. web scaffold (TanStack CLI). If it prompts, answer: React, TypeScript, file-based routing.
if (-not $SkipWeb) {
    Write-Host "`n-- web: create-tsrouter-app" -ForegroundColor Cyan
    if (-not (Test-Path 'web\package.json')) {
        Remove-Item 'web' -Recurse -Force -ErrorAction SilentlyContinue
        pnpm dlx create-tsrouter-app@latest web --template file-router --tailwind --package-manager pnpm --toolchain eslint+prettier --add-ons shadcn,tanstack-query --no-git
        if ($LASTEXITCODE -ne 0) { Write-Host "  ! scaffold failed - run interactively:  pnpm dlx @tanstack/cli@latest create web" -ForegroundColor Yellow }
    }
    if (Test-Path 'web\package.json') {
        Push-Location 'web'
        pnpm add @dnd-kit/core @dnd-kit/utilities date-fns @date-fns/tz zustand zod lucide-react
        pnpm add -D @hey-api/openapi-ts @tanstack/react-query-devtools @playwright/test
        # gen:api script + vite /api proxy, applied with node so JSON/TS stay valid
        Set-Content 'patch-scaffold.cjs' @'
const fs = require("fs");
const pkg = JSON.parse(fs.readFileSync("package.json", "utf8"));
pkg.scripts = pkg.scripts || {};
pkg.scripts["gen:api"] = "openapi-ts -i http://localhost:8000/openapi.json -o src/api/client -c @hey-api/client-fetch";
fs.writeFileSync("package.json", JSON.stringify(pkg, null, 2) + "\n");
const vc = fs.existsSync("vite.config.ts") ? "vite.config.ts" : "vite.config.js";
let s = fs.readFileSync(vc, "utf8");
if (!s.includes("proxy")) {
  s = s.replace(/defineConfig\(\{/, "defineConfig({\n  server: { proxy: { '/api': 'http://localhost:8000', '/docs': 'http://localhost:8000', '/openapi.json': 'http://localhost:8000' } },");
  fs.writeFileSync(vc, s);
}
const dup = pkg.devDependencies && pkg.devDependencies["@tailwindcss/postcss"];
console.log("patched package.json + " + vc + (dup ? " | NOTE: remove @tailwindcss/postcss (duplicate of @tailwindcss/vite)" : ""));
'@
        node patch-scaffold.cjs
        Remove-Item 'patch-scaffold.cjs'
        Pop-Location
    }
}

# 7. git
if (-not (Test-Path '.git')) {
    git init -b main | Out-Null
    git add -A
    git commit -q -m "scaffold: workmate-saas S0 (kit $VERSION)"
    Write-Host "`n  git: initial commit on main" -ForegroundColor Green
}

Write-Host @"

== done ==
next:
  cd $Root\backend ; uvx library-skills --claude          # official FastAPI skill -> ..\.claude\skills
  uv run pytest -q ; uv run fastapi dev app/main.py       # http://localhost:8000/api/v1/health
  cd $Root\web ; pnpm gen:api ; pnpm dev                  # http://localhost:5173
  claude                                                   # in $Root - reads CLAUDE.md + .claude\rules
"@ -ForegroundColor Cyan
