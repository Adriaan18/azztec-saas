# Azztec SaaS — Raw Log 2026-09-10

**File:** Azztec_SaaS_Raw_Log_2026-09-10_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-10 · **Author:** Adriaan
**Session:** first-session checklist (Project Knowledge Index §6) — environment, DB, scaffold, backend smoke
**Status:** append-only ground truth. Corrections go in a later dated log, not by editing this one.
**Goes to:** `docs/raw/` in the repo AND project knowledge.

---

## 1. Decisions signed this session (🤙)

- **OD-1 🤙** `engineOwned()` ports 1:1, no RST branch, no new code paths. Without `dbo.WO_N_Plan` every engine-owned PM is `locked: True, movable: False`. On RST that is **2,364 PMs** (status A 2,363 + H 1; `_ENGINE_FROZEN = ('V','C','D')`). Expect no PM to drag in the S1 smoke — that is the decision working, not a defect. S3 migration 0002 unlocks them.
- **OD-6 🤙** all day math on civil dates; `WORKMATE_TZ` (default `Pacific/Auckland`) touches exactly one point — resolving "now" to a civil date. Porting consequence: `civilDays` ports untouched (already pure `datetime.date`); `parseIso`, `iso`, `timeOf`, `weekStart` are **rewritten** on stdlib, not ported — they are `system.date.*` today. `weekStart` flips from Ignition's 1=Sunday convention to Python's 0=Monday; tests need an explicit **Sunday** case.
- **OD-7 raised, open.** RST has **no `PLANNER_*` rows** in `System_Configuration` (probe 8.4b). Every `config_value()` switch falls to its default, including `PLANNER_DEV_USER_ID` (which OD-2 leans on). Options: seed migration vs defaults-in-code with the table as override. Needs 🤙; does not block the rules chunk.
- OD-2, OD-3, OD-4, OD-5 — still open. None block the rules chunk of S1.

## 2. Environment facts (this box, verified)

- Windows 11 x64. Shell used all session: **Windows PowerShell 5.1** (`5.1.26100.9168`). PowerShell 7 is installed but was not used; both bootstrap and scaffold scripts run clean under 5.1.
- Execution policy was `Undefined` at every scope → falls to Restricted. Set **`CurrentUser RemoteSigned`** (persists). Earlier `-Scope Process Bypass` died with its window — do not rely on it.
- **Mark-of-the-Web rule:** every file that arrives as a Download card carries the zone tag and fails under RemoteSigned. Run `Get-ChildItem C:\dev\azztec-saas-kit -Recurse | Unblock-File` **after** each drop, before running anything. Bitten twice this session.
- Claude Code **2.1.267** native install at `C:\Users\Azzte\.local\bin\claude.exe`. The installer does not add itself to PATH; `C:\Users\Azzte\.local\bin` was added to User PATH manually (same folder uv wanted for its Python shims).
- Bootstrap version block: git 2.55.0, uv 0.12.12, Python 3.13.15, node v24.19.0, pnpm 12.3.4, docker 29.7.2, code 1.137.0, ODBC Driver 18 (both 32- and 64-bit; the block's "(32-bit)" was the script printing the first hit only).
- **SSMS install failed** (winget exit 1626, and winget only offers 20.2.1; stack wants 21/22). Not retried. DB tooling in use instead: **SqlServer PowerShell module 22.4.5.1** (`Invoke-Sqlcmd -TrustServerCertificate`) and the **VS Code MSSQL extension** 1.45.1 (installed, not yet used). `sqlcmd.exe` is not on PATH and was not needed.
- **`uvx library-skills --claude`** detected project root as `backend\` (where `pyproject.toml` is) and installed the `fastapi` skill at **`backend\.claude\skills\fastapi`** (symlink into `.venv`), plus `backend\.agents\skills\fastapi` and the `library-skills` tool skill. The Install doc's `..\.claude\skills` was wrong. `typer` skill offered and declined (fastapi-cli dependency, not in the stack). **Unverified:** whether Claude Code launched from the repo root discovers a nested `backend\.claude\skills\`. Test with `/` on first launch; junction from root if not.

## 3. SQL Server (installed this session — the "existing instance" in the env snapshot did not exist on this box)

- **SQL Server 2025 Developer, RTM 17.0.1000.7**, default instance `MSSQLSERVER`, registry key `MSSQL17.MSSQLSERVER`. Installed via `winget install -e --id Microsoft.SQLServer.2025.Developer`.
- Mixed-mode auth: registry `LoginMode` 1 → **2**. TCP/IP: `SuperSocketNetLib\Tcp\Enabled` 0 → **1**. Service restarted. Both done from the terminal, no SSMS / Configuration Manager.
- Listening on **static 1433**, IPv4 and IPv6. `-S localhost` works as the doc's check assumes.
- `AzztecDev\Azzte` is **sysadmin** (winget basic install added the installing user).
- Login **`svc_workmate`** created (`CHECK_POLICY = OFF`). Password was set once at creation, then **mismatched** with what went into `.env`; resolved by `ALTER LOGIN` to match `.env`. **The only place that password now lives is `backend\.env`** (gitignored). If `.env` is lost, `ALTER LOGIN` again.
- Instance default data/log path: `C:\Program Files\Microsoft SQL Server\MSSQL17.MSSQLSERVER\MSSQL\DATA\`.

## 4. dbWorkmate restore (Install doc §4)

- Source: `C:\dev\backups\RST_Workmate.bak` (dated 8/09/2026). Logical names `dbWorkmate` (D) / `dbWorkmate_log` (L); physical names inside the backup were `F:\SQLData\` and `G:\SQLLogs\` (RST server drives) — `MOVE` was mandatory.
- Restored to the **instance default path**, not the doc's `C:\SQLData\` (does not exist here). Log file named `dbWorkmate_log.ldf` (doc convention; backup had `dbWorkmate.ldf`).
- 629,882 pages ≈ 4.8 GB, 78.5 s. **One-way upgrade:** internal version **957 (SQL 2022) → 998 (SQL 2025)**. This `.mdf` can never go back to a 2022 instance. The `.bak` is untouched.
- Compat level lifted **160 → 170** (§4.4, instance max). Recovery model set **FULL → SIMPLE** (deviation: dev box, no log-backup chain, `.bak` is the recovery plan).
- §4.1 (rename KT dev copy) skipped — no KT copy on this instance.
- **26 orphaned principals** in the restored DB (all `RSTIMBER\` Windows users and RST SQL users, none mapped to a login here). Left alone; several likely own schemas.
- `svc_workmate` mapped as DB user with `db_datareader`, `db_datawriter`, `db_ddladmin` (§4.5 as written; no pre-existing user of that name in the backup).

## 5. §8 probe results (Azztec_SaaS_Probe_RST_v1_0_0.ps1, 14/14 ok, output kept at kit\probe_rst.txt)

- 8.1 compat 170, `SQL_Latin1_General_CP1_CI_AS`, SIMPLE. `WO_N_Header` **169,678** rows / `WO_C_Header` **453,133**; `Request_Start_Date` **2003-10-01 → 2026-12-22**. Far above KT volume — `Request_Start_Date` indexing matters for `/range` and the parity script.
- 8.2a status × type: C/N 75,925 · C/M 72,501 · D/M 12,796 · D/N 4,667 · A/M 2,363 · V/N 703 · A/N 347 · V/M 341 · R/N 32 · P/N 2 · H/M 1. Statuses present: C D A V R P H (subset of Landmines §E; no K or F). All map through `category()` — P and H fall to the defaults, no unmapped status.
- 8.2b `Users.Active` **Y/N** (443/677). 8.2c `User_Skill.Active` **1/0** (668/314). Exactly the split §E warns about; `_WORKER_SQL` already handles both.
- 8.2d **eight** UOM rows with `LRStd = 1`, all Active. `hoursUomId()` does `TOP 1 … ORDER BY UOM_Id` → resolves to **12 LABOUR HOURS**. Deterministic, correct.
- 8.2e **77** suppliers with `Internal_Dept = '1'`, mostly individual initials, plus DELETE / REDUNDANT / XMAS. Drives `worker.internal` and capacity — watch for capacity pollution from the junk rows.
- 8.2f 14 priorities with **four-way ties** on `Sort_Sequence`. `_PRIORITY_SQL` ends `ORDER BY Sort_Sequence, Priority_Id` — that second key is the only thing making the order deterministic. **Port must keep it or the JSON contract order drifts.** `Priority.Colour` has 14 distinct values on RST (§E's "always `#FF8000`" is KT-specific).
- 8.3 **37.7%** of `Request_Start_Date` carry a time (KT ~50%). `timeOf()` copes.
- 8.4a Ignition-era tables present: **`WO_Event_History` only.** Absent: `WO_N_Plan` (→ OD-1), `Diag_Log`, `Module_Settings`, `App_User`. Migrations must create `Diag_Log` and `App_User`.
- 8.4b **no `PLANNER_*` rows** → OD-7.
- 8.5a `WO_N_Activity` labour, 730 days: 472,288 rows, 368,299.59 hrs, 255 people. 8.5b `WO_C_Activity`: **0 rows** despite 453k closed headers — on RST the §E union is effectively `WO_N_Activity` alone. S5 (planner_ai) concern only.
- 8.6 six triggers, **all on `PO_*` tables** (`UpdateLastSaveDate_*`). None on `WO_N_Header` / `WO_N_Resource` / `WO_Event_History` → the OUTPUT-clause hazard does not touch the planner write path (S1–S4). It lands on the PO module.

## 6. Repo scaffold (Install doc §5)

- **Scaffold 1.0.0 bug:** `Put()` threw *"Cannot bind argument to parameter 'Path' because it is an empty string"* on root-level destinations (`docker-compose.yml`, `CLAUDE.md`) — `Split-Path` returns `''` for a bare filename. Fixed in **`Azztec_SaaS_Scaffold_Repo_v1_0_1.ps1`** (guarded directory creation, otherwise identical). 1.0.0 stays in the kit and `scripts/`.
- Backend: all 9 starter files placed, `uv sync` 65 packages — fastapi 0.141.1, sqlalchemy 2.0.52, pyodbc 5.3.0, psycopg 3.3.5, alembic 1.19.2, pytest 9.1.1, ruff 0.16.6. `backend\.env` created from `.env.example`; `WORKMATE_DB_PASSWORD` and `WORKMATE_SECRET_KEY` filled (Notepad edit did not save first time — set via PowerShell `-replace`).
- **Web scaffold FAILED** at Scaffold line 147: `create-tsrouter-app` is **deprecated** ("use `tanstack create --router-only`"), and `--toolchain eslint+prettier` is **no longer valid** — allowed values are `biome` or `eslint`. Line 146 had already deleted `web\`; line 150's guard then skipped both `pnpm add` rounds and the vite proxy patch. **There is no `web/` app.** Decision pending: `eslint` (+ Prettier by hand, matches Architecture doc) vs `biome` (one tool, stack change), and whether to move to `@tanstack/cli create --router-only`. Needs 🤙; Architecture §3.2 and Install §7 need a dated correction either way.
- `git init -b main` + initial commit succeeded — **without a web app in it.**
- Reference sources in `docs/reference/`: all five `workmate_planner_*.py` + `PlannerCalendar_v1_3_0_view.json`. **Not copied** (no matching pattern in the scaffold): `Planner_v1_8_1.html`, `wm-ui.css`, `wm-ui.js` — sit in the kit only. **Missing from the kit entirely:** `Workmate_PG_Forward_Compat*.md`, `Workmate_Planner_Assistant_Prompts*.md` (both listed as sources of truth in the port spec).
- Kit has `Planner_v1_8_1.html`; port spec names `Planner_v1_7_1.html` as the parity/smoke reference. **Which is the live KT UI is unresolved.**

## 7. Backend smoke (Install doc §6) — CLOSED

- `uv run pytest -q` → **2 passed, 1 failed.**
- `test_health_shape_and_db` **passes** → `db: "ok"` — ODBC 18 + `svc_workmate` + `TrustServerCertificate` + `dbWorkmate` proven end to end. `test_diag_self_test` passes.
- `test_api_404_is_json_not_spa` **fails** with `RuntimeError("StaticFiles directory '…\web\dist' does not exist.")` — direct consequence of the missing web app. Clears after `pnpm build` (StaticFiles needs the directory to exist before it evaluates the Accept header). Deliberately left red as the signal that the frontend does not exist.
- **Note for later:** `main.py` 1.0.0 has no explicit API 404 handler; an `/api/...` miss depends on the SPA mount being healthy. Robustness gap, not urgent.

## 8. Doc corrections queued (apply as dated changes in the next versions)

- **Install doc:** "existing instance" assumption (§0/§5 snapshot) → not on a fresh box; §3 steps 1–2 are registry writes, no SSMS needed; §4.3 target `C:\SQLData\` → instance default path; §4 add the one-way 957→998 upgrade warning and `RECOVERY SIMPLE`; §5 `uvx library-skills` lands under `backend\.claude\skills`, not `..\.claude\skills`; §6 note the expected 2/3 until `pnpm build`.
- **Architecture §3.2 / Install §7:** `create-tsrouter-app` deprecated; `--toolchain eslint+prettier` invalid. Pending the toolchain 🤙.
- **Landmines §E:** `Priority.Colour` "always `#FF8000`" is KT-only (RST: 14 colours); `WO_C_Activity` labour can be empty (RST); triggers are PO-only on RST.
- **Port spec:** status Draft → OD-1, OD-6 signed 2026-09-10; add OD-7; note P/H statuses exist on RST; `sql.py` must preserve `ORDER BY Sort_Sequence, Priority_Id`.
- **Bootstrap script:** version block prints only the first ODBC driver hit — show both platforms.

## 9. Open items carried forward

1. 🤙 web toolchain (`eslint` vs `biome`) and CLI (`create-tsrouter-app` vs `@tanstack/cli`) → then scaffold v1.0.2 with `-SkipBackend`.
2. 🤙 OD-7 (`PLANNER_*` seed vs defaults).
3. **KT dev copy** for the S1 parity oracle — source and delivery. Gates S1 acceptance, not the rules port.
4. Planner UI reference: 1.7.1 vs 1.8.1 — which is live at KT.
5. Copy `Planner_*.html` / `wm-ui.*` into `docs/reference/`; locate `Workmate_PG_Forward_Compat` and `Workmate_Planner_Assistant_Prompts`.
6. Verify Claude Code sees `backend\.claude\skills\fastapi`; junction from root if not.
7. OD-2 / OD-3 / OD-4 / OD-5.

## 10. Next build step (unblocked)

**S1 rules chunk, in Claude Code:** `app/planner/rules.py` + `tests/test_planner_rules.py`, porting from `docs/reference/workmate_planner_code_v1_3_1.py` — 1:1 names and dict keys, per OD-1 (`engineOwned` unchanged) and OD-6 (four date functions rewritten on stdlib, Sunday test). No DB. Stop before `sql.py` / `repo.py` / router. Plan mode first.

## 11. Changelog

- 1.0.0 (2026-09-10) Initial.
