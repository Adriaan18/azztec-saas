# Azztec SaaS — Dev Environment Install (Windows, surgical)

**File:** Azztec_SaaS_Dev_Environment_Install_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-10 · **Author:** Adriaan
**Status:** Active. Run top to bottom once; §11 is the daily loop.
**Companions:** `Azztec_SaaS_Bootstrap_Windows_v1_0_0.ps1` (§2), `Azztec_SaaS_Scaffold_Repo_v1_0_0.ps1` (§5), `Azztec_SaaS_dotenv_example_v1_0_0.txt`

---

## 0. Assumptions

- Windows 11 x64, an admin PowerShell 7 window (`Win+X → Terminal (Admin)`), winget present (`winget --version`).
- A local SQL Server instance already exists (the Ignition Dev DB lives on it). If not, §2 installs SQL Server 2025 Developer.
- The RST backup file is on disk, e.g. `C:\dev\backups\RST_Workmate.bak`.
- Working folder `C:\dev\`. Repo becomes `C:\dev\workmate-saas\`.

Every step ends with a check. Paste the check output into the chat when something doesn't match.

## 1. Download the delivered files

Put every `Azztec_SaaS_*` file from the Download cards into `C:\dev\azztec-saas-kit\` (the scaffold script reads from there).

## 2. Install the tools (one script)

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
C:\dev\azztec-saas-kit\Azztec_SaaS_Bootstrap_Windows_v1_0_0.ps1
```

What it installs (winget IDs, verified 2026-09-10) — skip any already present:

| Tool | winget id | Note |
|------|-----------|------|
| Git | `Git.Git` | also gives Claude Code its Bash tool |
| PowerShell 7 + Windows Terminal | `Microsoft.PowerShell`, `Microsoft.WindowsTerminal` | |
| VS Code | `Microsoft.VisualStudioCode` | |
| uv | `astral-sh.uv` | Python manager (0.12.x) |
| Node.js 24 LTS | `OpenJS.NodeJS.LTS` | Node 26 → LTS on 2026-10-28, move then |
| pnpm | `pnpm.pnpm` | not corepack |
| ODBC Driver 18 for SQL Server | `Microsoft.msodbcsql.18` | 18.6.2.1; pyodbc needs the 64-bit driver |
| SSMS | `Microsoft.SQLServerManagementStudio` | if winget's is older than 21, use the Microsoft download page |
| Docker Desktop | `Docker.DockerDesktop` | for Postgres 18 + Adminer (PG track); needs WSL2 — reboot after |
| Claude Code | `irm https://claude.ai/install.ps1 \| iex` (native, auto-updating) | winget `Anthropic.ClaudeCode` also works, no auto-update |
| *(only if no instance)* SQL Server 2025 Developer | `Microsoft.SQLServer.2025.Developer` | free, full-featured, non-production |
| *(optional)* DBeaver | `DBeaver.DBeaver.Community` | |

Then Python:

```powershell
uv python install 3.13
uv python list | Select-String 3.13
```

**Check (script prints this block):** `git`, `uv`, `node` (v24.x), `pnpm`, `docker`, `claude` versions and `Get-OdbcDriver` showing *ODBC Driver 18 for SQL Server*.

## 3. SQL Server: auth, network, login

1. SSMS → connect (Windows auth) → server *Properties → Security* → **SQL Server and Windows Authentication mode** → OK.
2. *SQL Server Configuration Manager → SQL Server Network Configuration → Protocols → TCP/IP → Enabled*; restart the SQL Server service.
3. Run in SSMS:

```sql
CREATE LOGIN svc_workmate WITH PASSWORD = N'<strong-password>', CHECK_POLICY = OFF;
```

**Check:** `sqlcmd -S localhost -U svc_workmate -P <pw> -Q "SELECT @@VERSION" -C` (`-C` = trust the self-signed cert). If `-S localhost` fails use `-S .\<INSTANCE>` or `tcp:localhost,1433`.

## 4. Restore the RST backup as `dbWorkmate`

Keep the KT dev copy: rename it first, then restore RST under the name the app expects.

```sql
-- 4.1 rename the existing KT dev copy (skip if it doesn't exist)
ALTER DATABASE dbWorkmate SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
ALTER DATABASE dbWorkmate MODIFY NAME = dbWorkmate_KT;
ALTER DATABASE dbWorkmate_KT SET MULTI_USER;

-- 4.2 find the logical file names inside the backup
RESTORE FILELISTONLY FROM DISK = N'C:\dev\backups\RST_Workmate.bak';

-- 4.3 restore (replace <DataLogical>/<LogLogical> with the names from 4.2)
RESTORE DATABASE dbWorkmate FROM DISK = N'C:\dev\backups\RST_Workmate.bak'
WITH MOVE N'<DataLogical>' TO N'C:\SQLData\dbWorkmate.mdf',
     MOVE N'<LogLogical>'  TO N'C:\SQLData\dbWorkmate_log.ldf',
     STATS = 10;

-- 4.4 lift the compatibility level to the instance maximum (170 on SQL 2025, 160 on 2022)
SELECT compatibility_level FROM sys.databases WHERE name = 'dbWorkmate';
ALTER DATABASE dbWorkmate SET COMPATIBILITY_LEVEL = 160;   -- adjust

-- 4.5 map the login (dev: ddladmin so Alembic can create Workmate-added tables)
USE dbWorkmate;
CREATE USER svc_workmate FOR LOGIN svc_workmate;
ALTER ROLE db_datareader ADD MEMBER svc_workmate;
ALTER ROLE db_datawriter ADD MEMBER svc_workmate;
ALTER ROLE db_ddladmin  ADD MEMBER svc_workmate;
```

**Check:** run Data Layer doc §8.1–8.4 probes and paste the output (row counts, date range, status/flag domains, Ignition-era tables present or not).

## 5. Create the repo (one script)

```powershell
C:\dev\azztec-saas-kit\Azztec_SaaS_Scaffold_Repo_v1_0_0.ps1 -Root C:\dev\workmate-saas
```

It: creates the monorepo layout → `uv init` + `uv add` the pinned backend deps → drops the starter files into place
(`pyproject.toml`, `app/main.py`, `app/core/*.py`, `tests/test_smoke.py`, `.env.example`, `docker-compose.yml`, `CLAUDE.md`, `docs/`)
→ scaffolds `web/` with the TanStack CLI (file-router, Tailwind v4, shadcn + tanstack-query add-ons, pnpm, eslint+prettier)
→ adds the frontend libs (`@dnd-kit/core`, `date-fns`, `@date-fns/tz`, `zustand`, `zod`, `@hey-api/openapi-ts`, `lucide-react`) → `git init` + first commit.

Manual after the script:

```powershell
cd C:\dev\workmate-saas\backend
Copy-Item .env.example .env          # fill WORKMATE_DB_PASSWORD, WORKMATE_SECRET_KEY
uvx library-skills --claude          # official FastAPI skill → ..\.claude\skills
```

## 6. Backend smoke

```powershell
cd C:\dev\workmate-saas\backend
uv sync
uv run pytest -q
uv run fastapi dev app/main.py       # http://localhost:8000/docs
```

**Check:** browser `http://localhost:8000/api/v1/health` →
`{"app":"workmate-saas","version":"0.1.0","env":"dev","db":"ok","dbKind":"mssql","dbName":"dbWorkmate","tz":"Pacific/Auckland"}`.
`db:"ok"` proves ODBC 18 + login + TrustServerCertificate are right. If it says `error: ... certificate chain ...` see §12.

## 7. Frontend smoke

```powershell
cd C:\dev\workmate-saas\web
pnpm install
pnpm gen:api                         # typed client from http://localhost:8000/openapi.json (backend must be running)
pnpm dev                             # http://localhost:5173  — /api and /docs proxy to 8000
pnpm test; pnpm build
```

`vite.config.ts` proxy (the scaffold writes it):

```ts
server: { proxy: { '/api': 'http://localhost:8000', '/docs': 'http://localhost:8000', '/openapi.json': 'http://localhost:8000' } }
```

**Check:** the scaffold's index route renders and shows the health JSON fetched through the generated client.

## 8. Postgres track (optional now, mandatory later)

```powershell
cd C:\dev\workmate-saas
docker compose up -d                 # postgres:18 on 5432, adminer on 8080
```

Switch the backend by setting `WORKMATE_DB_KIND=postgresql` and `WORKMATE_DB_URL=postgresql+psycopg://workmate:workmate@localhost:5432/workmate` in `.env`; `/api/v1/health` shows `dbKind:"postgresql"`. Migrations run on both: `uv run alembic upgrade head`.

## 9. Claude Code

```powershell
cd C:\dev\workmate-saas
claude                               # first run: OAuth in the browser
```

It reads `CLAUDE.md`, `.claude/rules/*.md`, `.claude/skills/*` automatically. Workflow: `Azztec_SaaS_Claude_Code_Workflow_v1_0_0.md`.

## 10. VS Code extensions (install from the Extensions pane or `code --install-extension <id>`)

`ms-python.python`, `charliermarsh.ruff`, `ms-python.vscode-pylance` (or `astral-sh.ty`), `dbaeumer.vscode-eslint`, `esbenp.prettier-vscode`,
`bradlc.vscode-tailwindcss`, `ms-mssql.mssql` (the MSSQL extension absorbed Azure Data Studio), `ms-playwright.playwright`,
`tamasfe.even-better-toml`, `ms-azuretools.vscode-docker`, `eamodio.gitlens`, `anthropic.claude-code`.

Workspace settings the scaffold writes: Ruff as Python formatter + format-on-save; Prettier for TS; `files.eol: "\n"`.

## 11. Daily loop (cheat sheet)

```powershell
# terminal 1
cd C:\dev\workmate-saas\backend; uv run fastapi dev app/main.py
# terminal 2
cd C:\dev\workmate-saas\web; pnpm dev
# after a backend contract change
pnpm --dir C:\dev\workmate-saas\web gen:api
# gates before a commit
uv run --directory C:\dev\workmate-saas\backend ruff check . ; uv run --directory C:\dev\workmate-saas\backend pytest -q
pnpm --dir C:\dev\workmate-saas\web test ; pnpm --dir C:\dev\workmate-saas\web build
git -C C:\dev\workmate-saas add -A ; git -C C:\dev\workmate-saas commit -m "planner: S1 range 1.0.0"
```

## 12. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `SSL Provider: The certificate chain was issued by an authority that is not trusted` | ODBC 18 `Encrypt=yes` default → `WORKMATE_DB_TRUST_CERT=true` (dev) — already in `.env.example` |
| `Login failed for user 'svc_workmate'` | mixed-mode auth not enabled (§3.1) or service not restarted |
| `Data source name not found` / driver not found | `Get-OdbcDriver` must list *ODBC Driver 18 for SQL Server* (64-bit); reinstall `Microsoft.msodbcsql.18` |
| `uv: command not found` right after install | open a new terminal (PATH) |
| `ZoneInfoNotFoundError: Pacific/Auckland` | `tzdata` missing from the venv — `uv sync` (it's in pyproject) |
| `fastapi dev` errors about `dist/` | `FASTAPI_ENV=development` is set by `fastapi dev`; under plain uvicorn build the SPA first (`pnpm build`) or set `check_dir=False` |
| Vite: `/api` 404 in the browser | backend not running on 8000, or proxy block missing in `vite.config.ts` |
| Two Tailwind deps after scaffold | keep `@tailwindcss/vite`, remove `@tailwindcss/postcss` + its postcss config |
| Playwright browsers missing | `pnpm exec playwright install chromium` |
| Docker Desktop won't start | enable WSL2 (`wsl --install`), reboot |
| Line-ending churn in git | `.gitattributes` `* text=auto eol=lf` (scaffold writes it); `git add --renormalize .` once |

## 13. Changelog

- 1.0.0 (2026-09-10) Initial.
