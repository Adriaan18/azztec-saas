# Azztec SaaS — Project Knowledge Index

**File:** Azztec_SaaS_Project_Knowledge_Index_v1_1_0.md · **Version:** 1.1.0 · **Date:** 2026-09-11 · **Author:** Adriaan
**Status:** Active
**Project:** Workmate Standalone Edition (FastAPI + React + PostgreSQL) — the Azztec Enterprise SaaS rebuild of Workmate CMMS
**Read this first** in every new chat. It says what exists, what to read next, and the standing rules.

---

## 1. What this project is

Workmate is being rebuilt from Ignition Perspective (the "Ignition Edition", live at KT) into a standalone product: **FastAPI backend + React frontend**, PostgreSQL as the target database, MSSQL as the development reality. Development runs against **`dbWorkmate` on the local SQL Server, restored from the Red Stag Timber (RST) Workmate database — ~20 years of real CMMS data**. The first function built is the **Planner** (P-PLN1), ported 1:1 from the live Ignition planner (same JSON contract, same pure rules).

The AI brain (`workmate-ai`, Layers 3–8) is the same service for both editions — see `Workmate_AI_Architecture_v1_2.md`.

**Where the build is:** backend `/api/v1/planner/range` is live on RST and green. S1a (rules) · S1b (sql+repo) · S1c (service+schemas+deps+router) · S1d (diagnostics wiring) all shipped and tagged. Suite 125, all green. Next is **S1e — the React planner**, blocked on one decision (§6.1).

## 2. Read order for a new chat

| # | File | Why |
|---|------|-----|
| 1 | `Azztec_SaaS_Project_Knowledge_Index_v1_1_0.md` | this file |
| 2 | **`Azztec_SaaS_Raw_Log_2026-09-11_v1_2_0.md`** | **where the build actually is** — state, open list, next slice. Supersedes this file's §6 on anything they disagree about |
| 3 | `Azztec_SaaS_Ways_of_Working_v1_1_0.md` | how every deliverable is produced and gated |
| 4 | `Azztec_SaaS_Platform_Landmines_v1_1_0.md` | the gotchas, all verified with dates |
| 5 | `Azztec_SaaS_Architecture_and_Stack_v1_0_0.md` | the stack, decisions D-1…D-12, repo layout, version pins |
| 6 | `Azztec_SaaS_Data_Layer_and_RST_DB_v1_0_0.md` | the RST database, schema truths, dialect rules |
| 7 | `Azztec_SaaS_Planner_Port_Spec_v1_0_0.md` | the first function — contract, routes, rules, slices, acceptance |
| 8 | the chunk spec for the slice in hand (`S1a`…`S1d`) | the template and the precedent |
| 9 | `Azztec_SaaS_Dev_Environment_Install_v1_0_0.md` · `Azztec_SaaS_Community_and_Research_v1_0_0.md` · `Azztec_SaaS_Claude_Code_Workflow_v1_0_0.md` | setup once; research when stuck; the chat ↔ Claude Code loop |

Read 1–4 always. 5–7 before touching Planner code. **The raw logs outrank the compiled docs on current state** — compiled docs describe the design, logs describe the box.

## 3. The file set — live inventory

Everything below should be in project knowledge at the version shown. If a file is live in the repo and missing from this table, project knowledge is stale.

### 3.1 Compiled docs

| File | Version |
|------|---------|
| `Azztec_SaaS_Project_Knowledge_Index` | **1.1.0** |
| `Azztec_SaaS_Ways_of_Working` | **1.1.0** |
| `Azztec_SaaS_Platform_Landmines` | **1.1.0** |
| `Azztec_SaaS_Architecture_and_Stack` | 1.0.0 |
| `Azztec_SaaS_Data_Layer_and_RST_DB` | 1.0.0 |
| `Azztec_SaaS_Planner_Port_Spec` | 1.0.0 (corrections queued — log 1.2.0 §7) |
| `Azztec_SaaS_Dev_Environment_Install` | 1.0.0 (corrections queued) |
| `Azztec_SaaS_Community_and_Research` | 1.0.0 |
| `Azztec_SaaS_Claude_Code_Workflow` | 1.0.0 |
| `Azztec_SaaS_CLAUDE_md` | 1.0.0 |

### 3.2 Chunk specs (the per-slice template)

`Azztec_SaaS_S1a_Rules_Chunk_Spec` 1.0.0 · `Azztec_SaaS_S1b_Data_Chunk_Spec` 1.0.0 · `Azztec_SaaS_S1c_Api_Chunk_Spec` 1.0.0 · `Azztec_SaaS_S1d_Diag_Chunk_Spec` 1.0.0

### 3.3 Raw logs (append-only, never edited)

`Azztec_SaaS_Raw_Log_2026-09-10` 1.0.0 · `Azztec_SaaS_Raw_Log_2026-09-11` 1.0.0 · 1.1.0 · **1.2.0**

Each supersedes named sections of the last. Read the newest first, then walk back for anything it doesn't cover.

### 3.4 Backend code — current repo state

| Module | Version | Delivered as |
|--------|---------|--------------|
| `backend/app/main.py` | 0.3.0 | `Azztec_SaaS_app_main_v1_0_3.py` |
| `backend/app/core/config.py` | 1.1.0 | `..._app_core_config_v1_1_0.py` |
| `backend/app/core/db.py` | 1.0.0 | `..._app_core_db_v1_0_0.py` |
| `backend/app/core/diag.py` | 1.1.1 | `..._app_core_diag_v1_1_1.py` |
| `backend/app/core/deps.py` | 1.0.0 | `..._app_core_deps_v1_0_0.py` |
| `backend/app/planner/rules.py` | 1.0.0 | `..._app_planner_rules_v1_0_0.py` |
| `backend/app/planner/sql.py` | 1.0.1 | `..._app_planner_sql_v1_0_1.py` |
| `backend/app/planner/repo.py` | 1.0.0 | `..._app_planner_repo_v1_0_0.py` |
| `backend/app/planner/service.py` | 1.0.1 | `..._app_planner_service_v1_0_1.py` |
| `backend/app/planner/schemas.py` | 1.0.0 | `..._app_planner_schemas_v1_0_0.py` |
| `backend/app/planner/router.py` | 1.0.1 | `..._app_planner_router_v1_0_1.py` |

### 3.5 Tests

| File | Version |
|------|---------|
| `backend/tests/test_smoke.py` | 1.1.0 |
| `backend/tests/test_planner_rules.py` | 1.0.0 |
| `backend/tests/test_planner_repo.py` | 1.0.1 |
| `backend/tests/test_planner_api.py` | 1.0.1 |
| `backend/tests/test_diag_wiring.py` | 1.0.1 |
| `backend/tests/test_openapi_contract.py` | 1.0.0 |

Not yet reviewed in chat: `backend/tests/conftest.py` (see log 1.2.0 §8.4).

### 3.6 Config and scripts

`Azztec_SaaS_pyproject` 1.0.0 · `Azztec_SaaS_dotenv_example` **1.0.1** · `Azztec_SaaS_docker_compose` 1.0.0 · `Azztec_SaaS_Bootstrap_Windows` 1.0.0 · `Azztec_SaaS_Scaffold_Repo` 1.0.0 (v1.0.2 with `-SkipBackend` pending the §6.1 decision)

### 3.7 Reference sources — the parity oracle

The raw Ignition sources the port is measured against (from `MainSCADA_Timberlands_2026-09-10_1900.zip`): `workmate_planner_code_v1_3_1.py` · `workmate_planner_api_code_v1_8_3.py` · `workmate_planner_ai_code_v1_1_0.py` · `workmate_planner_chat_code_v1_2_1.py` · `workmate_planner_test_code_v1_0_0.py` · `PlannerCalendar_v1_3_0_view.json` · `Planner_v1_8_1.html` + `wm-ui.css` / `wm-ui.js`.

Generated, committed, not hand-edited: `docs/api/openapi_0_3_0.json`.

### 3.8 Carry-over from the Workmate Dev project (copy, do not rewrite)

`Workmate_PG_Forward_Compat_v1_0.md` · `Workmate_AI_Architecture_v1_2.md` · `Workmate_Planner_Assistant_Prompts_v1_0_0.md` · `Workmate_Forensic_Diagnostics_Standard_v1_1_0.md` · `Workmate_Security_Enforcement_Standard_v1_0_0.md` · `Workmate_NET_Logic_Reference_v1_1.md` + `Workmate_NET_Manual_Index.md` · `All_Tables_InDetail.csv` + `All_Stored_Procedures_and_Views.csv` · `Workmate_Knowledge_Journal_v3_7.md` §3.

## 4. Standing rules (one screen)

1. **Sequence:** audit → spec → 🤙 → one slice → versioned raw file(s) as Download cards → smoke → raw log → next. Never run ahead of 🤙. The audit may cut the scope it was handed; an unsigned dependency is the next audit's first line, not this build's next step.
2. **Version everything, never overwrite.** Delivered filename carries `_vX_Y_Z`; the file carries `__version__` / a header. Tag the version that **shipped**, not the one the spec predicted.
3. **Raw source files only**, one per Download card, via `present_files`. No inline code dumps, no zips. Each card states **PK: add / replaces `<version>`**.
4. **Pair rule:** every library slice ships with its `test_*.py`. Pure rules are tested with zero DB — and a zero-DB test must actually be zero-DB.
5. **`DRY_RUN = True` first** on anything that writes; Marker Law (residue = 0) on anything touching real data — the RST DB is real data even in dev.
6. **Fact-check before build:** confirm columns / codes / flags against the schema CSVs and the DB. Never re-emit a file you have not read.
7. **Dialect-portable SQL** (COALESCE / CURRENT_TIMESTAMP / CONCAT / OFFSET-FETCH / `dbo.` / `-- PG-CONVERT:` tags). The CI gate greps the whole file — describe banned tokens, never spell them.
8. **Forensic diagnostics** on every request outcome: [F] what happened, [G] why blocked, [E] crash — one `diag.log()` seam, wired by `diag.configure()`. Assert **emission**, not the call.
9. **Comms:** short, direct, NZ-casual. Console output pasted verbatim before proceeding. 🤙 = go.
10. **Close every session with a raw log** and the doc updates it implies. Carry forward every open item you do not close.

## 5. Environment snapshot (verified 2026-09-11)

| Thing | Value |
|-------|-------|
| Dev machine | Windows 11 x64, Windows PowerShell 5.1 in practice; execution policy `CurrentUser RemoteSigned` |
| Dev DB | local SQL Server → `dbWorkmate` restored from the **RST** backup; SQL login `svc_workmate`; dev actor `WORKMATE_DEV_USER_ID=1` (SYS_USER) |
| Live reference | Ignition gateway `MainSCADA_Timberlands` (KT) — the parity oracle, **copy not yet obtained** |
| Backend | Python 3.13.15 (uv 0.12.12), FastAPI 0.141.x, SQLAlchemy 2.0.5x (sync Core), pyodbc 5.3 + ODBC Driver 18 |
| Frontend | node v24.19.0, pnpm 12.3.4 — **not yet scaffolded** |
| Target DB | PostgreSQL 18.6 (Docker on dev) |
| Repo | `C:\dev\workmate-saas` — `backend/`, `web/`, `docs/`, `scripts/`, `.claude/`. HEAD `b1caa50`, tag `s1d-diag-1.1.1` |
| Claude Code | 2.1.267 native, `C:\Users\Azzte\.local\bin\claude.exe` (added to PATH manually) |
| Ports | API 8000, Vite 5173, Postgres 5432, Adminer 8080 |
| Git author | `AzztecEnterprise <azztecdev@gmail.com>` |

**Mark-of-the-Web rule:** every Download card carries the zone tag. `Unblock-File` after each drop — and remember it is not a copy (Ways of Working §2).

## 6. Picking up the build

Replaces the old first-session checklist, which is complete.

1. Read `Azztec_SaaS_Raw_Log_2026-09-11_v1_2_0.md` — §8 is the open list, §9 is the next slice and its four carry-ins.
2. `cd C:\dev\workmate-saas\backend; uv run pytest -q` → expect **125 green, zero red**. Anything else means the tree moved since this Index.
3. `uv run fastapi dev app/main.py` → expect four boot lines, `[F] diag wired` first.
4. Audit the next slice before proposing a spec.

### 6.1 The one decision blocking S1e

**The web toolchain has never been signed** — `eslint` vs `biome`, `create-tsrouter-app` vs `@tanstack/cli`, then scaffold v1.0.2 with `-SkipBackend`. It was raised 2026-09-10, called "the oldest open item" in log 1.0.0 §8.1, and then fell out of log 1.1.0 §8 entirely. It is restored in 1.2.0 §8.1. Nothing in `web/` can start until it has a 🤙 — and the generator question rides with it (`@hey-api/openapi-ts` emits a client, `openapi-typescript` emits types; Architecture §3.2 and log 1.1.0 §9 name different ones).

## 7. Changelog

- 1.1.0 (2026-09-11) Reissued after S1d. Read order puts the newest raw log second and states that logs outrank compiled docs on current state. §3 replaced with the full live inventory — backend modules, tests, chunk specs, logs — so a missing file in project knowledge is visible at a glance. §4 absorbs the scope-cut, tag-what-shipped, PK-marking, read-before-re-emitting and emission-testing rules. §5 re-verified against the box. §6 replaces the completed first-session checklist with how to pick the build up, and names the one unsigned decision blocking S1e.
- 1.0.0 (2026-09-10) Initial. Built from the Workmate Dev project state as of 2026-09-10 (Planner 1.3.1 / API 1.8.3 / UI 1.7.1 live at KT).
