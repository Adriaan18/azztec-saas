# Azztec SaaS — Project Knowledge Index

**File:** Azztec_SaaS_Project_Knowledge_Index_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-10 · **Author:** Adriaan
**Status:** Draft — awaiting 🤙
**Project:** Workmate Standalone Edition (FastAPI + React + PostgreSQL) — the Azztec Enterprise SaaS rebuild of Workmate CMMS
**Read this first** in every new chat. It says what exists, what to read next, and the standing rules.

---

## 1. What this project is

Workmate is being rebuilt from Ignition Perspective (the "Ignition Edition", live at KT) into a standalone
product: **FastAPI backend + React frontend**, PostgreSQL as the target database, MSSQL as the development
reality. Development runs against **`dbWorkmate` on the local SQL Server, restored from the Red Stag Timber (RST)
Workmate database — ~20 years of real CMMS data**. The first function built is the **Planner** (P-PLN1), ported
1:1 from the live Ignition planner (same JSON contract, same pure rules).

The AI brain (`workmate-ai`, Layers 3–8) is the same service for both editions — see `Workmate_AI_Architecture_v1_2.md`.

## 2. Read order for a new chat

| # | File | Why |
|---|------|-----|
| 1 | `Azztec_SaaS_Project_Knowledge_Index_v1_0_0.md` | this file |
| 2 | `Azztec_SaaS_Ways_of_Working_v1_0_0.md` | how every deliverable is produced and gated |
| 3 | `Azztec_SaaS_Architecture_and_Stack_v1_0_0.md` | the stack ("what else?"), decisions D-1…D-12, repo layout, version pins |
| 4 | `Azztec_SaaS_Platform_Landmines_v1_0_0.md` | gotchas: FastAPI / SQLAlchemy / pyodbc / React / Vite / legacy data / Jython→Py3 |
| 5 | `Azztec_SaaS_Data_Layer_and_RST_DB_v1_0_0.md` | the RST database, schema truths, dialect rules, tables the Planner touches |
| 6 | `Azztec_SaaS_Planner_Port_Spec_v1_0_0.md` | the first function — contract, routes, rules, slices, acceptance |
| 7 | `Azztec_SaaS_Dev_Environment_Install_v1_0_0.md` | surgical install (winget), scaffold, smoke checks |
| 8 | `Azztec_SaaS_Community_and_Research_v1_0_0.md` | where to ask, what to read, the tricks that save days |
| 9 | `Azztec_SaaS_Claude_Code_Workflow_v1_0_0.md` | the chat ↔ Claude Code loop; git is the shared memory |

Read 1–4 always. Read 5–6 before touching Planner code. Read 7 once (setup). Read 8 when stuck. Read 9 before the first Claude Code session.

## 3. The file set

### 3.1 New — this set (all v1.0.0, 2026-09-10)

| File | Type | One line |
|------|------|----------|
| `Azztec_SaaS_Project_Knowledge_Index_v1_0_0.md` | MD | entry point (this) |
| `Azztec_SaaS_Ways_of_Working_v1_0_0.md` | MD | delivery discipline for a git repo + Claude chat |
| `Azztec_SaaS_Architecture_and_Stack_v1_0_0.md` | MD | stack, decisions, repo layout, pins |
| `Azztec_SaaS_Platform_Landmines_v1_0_0.md` | MD | verified gotchas with dates |
| `Azztec_SaaS_Data_Layer_and_RST_DB_v1_0_0.md` | MD | RST DB, dialect-portable SQL, DDL the port needs |
| `Azztec_SaaS_Planner_Port_Spec_v1_0_0.md` | MD | P-PLN1 port: contract + slices S0–S7 |
| `Azztec_SaaS_Dev_Environment_Install_v1_0_0.md` | MD | install + scaffold + smoke, step by step |
| `Azztec_SaaS_Community_and_Research_v1_0_0.md` | MD | forums, docs, reference repos, tricks |
| `Azztec_SaaS_Claude_Code_Workflow_v1_0_0.md` | MD | two surfaces, one repo: laws, `.claude/` baseline, slice loop, guardrails |
| `Azztec_SaaS_CLAUDE_md_v1_0_0.md` | MD | the repo-root `CLAUDE.md` Claude Code reads every session |
| `Azztec_SaaS_Bootstrap_Windows_v1_0_0.ps1` | PS1 | winget installs + version verification |
| `Azztec_SaaS_Scaffold_Repo_v1_0_0.ps1` | PS1 | creates the monorepo, installs deps, drops the starter files in place |
| `Azztec_SaaS_pyproject_v1_0_0.toml` | TOML | backend `pyproject.toml` (pins verified 2026-09-10) |
| `Azztec_SaaS_app_main_v1_0_0.py` | PY | `backend/app/main.py` — app, lifespan, `/api/v1/health`, `app.frontend()` |
| `Azztec_SaaS_app_core_config_v1_0_0.py` | PY | `backend/app/core/config.py` — pydantic-settings |
| `Azztec_SaaS_app_core_db_v1_0_0.py` | PY | `backend/app/core/db.py` — engine factory (MSSQL/PG), `insert_returning_id`, `rows()` |
| `Azztec_SaaS_app_core_diag_v1_0_0.py` | PY | `backend/app/core/diag.py` — forensic [F]/[G]/[E] logging seam |
| `Azztec_SaaS_test_smoke_v1_0_0.py` | PY | `backend/tests/test_smoke.py` — health + DB ping |
| `Azztec_SaaS_docker_compose_v1_0_0.yml` | YML | Postgres 18 + Adminer for the PG track |
| `Azztec_SaaS_dotenv_example_v1_0_0.txt` | TXT | `backend/.env.example` |

### 3.2 Reference sources — copy into the new project's knowledge as-is

These are the raw Ignition sources the Planner port is measured against (from `MainSCADA_Timberlands_2026-09-10_1900.zip`):

| File | What |
|------|------|
| `workmate_planner_code_v1_3_1.py` | Planner library — data + PURE rules + write side (the thing being ported) |
| `workmate_planner_api_code_v1_8_3.py` | HTTP layer — `route()` pure, all routes, gate, diag wiring |
| `workmate_planner_ai_code_v1_1_0.py` | Suggest / planHorizon / history / nightly proposal / autopilot |
| `workmate_planner_chat_code_v1_2_1.py` | Deterministic intent router — `parse()` is the LLM seam |
| `workmate_planner_test_code_v1_0_0.py` | Night Shift pack t_* — the parity test list for the port |
| `PlannerCalendar_v1_3_0_view.json` | Host view (iframe + sid/uid/tok injection + `wm-plan-open` handoff) |

**Add yourself (not in the zip):** `Planner_v1_7_1.html` from `C:\WorkmateData\Planner\` — the single-file UI the
React planner replaces (visual + behaviour reference), and `wm-ui.css` / `wm-ui.js` from the same folder.

### 3.3 Carry-over from the Workmate Dev project (copy, do not rewrite)

| File | Why it still applies |
|------|----------------------|
| `Workmate_PG_Forward_Compat_v1_0.md` | the dialect rules — now enforced in `backend/app/**/sql.py` |
| `Workmate_AI_Architecture_v1_2.md` | Standalone Edition = §8.1; React chat widget is Layer 2 |
| `Workmate_Planner_Assistant_Prompts_v1_0_0.md` | what the planner chat must keep answering |
| `Workmate_Forensic_Diagnostics_Standard_v1_1_0.md` | [F]/[G]/[E] tags, Diag_Log persistence |
| `Workmate_Security_Enforcement_Standard_v1_0_0.md` | RBAC rules the API must enforce server-side |
| `Workmate_NET_Logic_Reference_v1_1.md` + `Workmate_NET_Manual_Index.md` | legacy behaviour authority (Labour Resource module pp.157–168) |
| `All_Tables_InDetail.csv` + `All_Stored_Procedures_and_Views.csv` | the 227-table legacy schema and 1 091 procs — the RST DB is this schema |
| `Workmate_Knowledge_Journal_v3_7.md` §3 (verified DB facts) | status codes, flags, FK truths |

## 4. Standing rules (one screen)

1. **Sequence:** audit → spec → 🤙 → one slice → versioned raw file(s) as Download cards → smoke → next. Never run ahead of 🤙.
2. **Version everything, never overwrite.** Delivered filename carries `_vX_Y_Z`; the file carries `__version__` (Python) / a header (SQL/MD/TS). Git commits reference the same version. Bump on every change.
3. **Raw source files only**, one per Download card, via `present_files`. No inline code dumps, no zips.
4. **Pair rule:** every library slice ships with its `test_*.py`. Pure rules are tested with zero DB.
5. **`DRY_RUN = True` first** on anything that writes; Marker Law (residue = 0) on anything touching real data — the RST DB is real data even in dev.
6. **Fact-check before build:** confirm columns / codes / flags against the schema CSVs and the .NET reference. Confirm, don't guess.
7. **Dialect-portable SQL** (COALESCE / CURRENT_TIMESTAMP / CONCAT / OFFSET-FETCH / `dbo.` / `-- PG-CONVERT:` tags). Rule from `Workmate_PG_Forward_Compat_v1_0.md`, now with teeth (a grep gate in CI).
8. **Forensic diagnostics** on every request outcome: [F] what happened, [G] why blocked, [E] crash — one `diag.log()` seam.
9. **Comms:** short, direct, NZ-casual. Console output pasted verbatim before proceeding. 🤙 = go.
10. **Close every session with a raw log** `Azztec_SaaS_Raw_Log_YYYY-MM-DD_vX_Y_Z.md` — append-only ground truth.

## 5. Environment snapshot (verified 2026-09-10)

| Thing | Value |
|-------|-------|
| Dev machine | Windows 11 x64, PowerShell 7, admin available |
| Dev DB | local SQL Server (existing instance) → `dbWorkmate` restored from the **RST** backup; SQL login `svc_workmate` |
| Live reference | Ignition gateway `MainSCADA_Timberlands` (KT) — the Planner runs there today; Dev gateway `localhost:8089` |
| Backend | Python 3.13 (uv), FastAPI 0.141.x, SQLAlchemy 2.0.5x (sync Core), pyodbc 5.3 + ODBC Driver 18 |
| Frontend | Node 24 LTS, pnpm, Vite 8, React 19.3, TypeScript, TanStack Router + Query, Tailwind v4, shadcn/ui |
| Target DB | PostgreSQL 18.6 (Docker on dev) |
| Repo | `workmate-saas/` monorepo: `backend/`, `web/`, `docs/`, `scripts/`, `.claude/` — git is the shared memory between this chat and Claude Code |
| Claude Code | native installer (`irm https://claude.ai/install.ps1 \| iex`), runs inside the repo, reads `CLAUDE.md` + `.claude/rules` + `.claude/skills` (FastAPI skill via `uvx library-skills --claude`) |
| Ports | API 8000 (`fastapi dev`), Vite 5173 (proxy `/api` → 8000), Postgres 5432, Adminer 8080 |

## 6. First session checklist (new chat)

1. Paste the Download cards from §3.1 into project knowledge; add §3.2 and §3.3 files.
2. Run `Azztec_SaaS_Bootstrap_Windows_v1_0_0.ps1` (admin PowerShell) → paste the version block it prints.
3. Restore the RST backup as `dbWorkmate` (Install doc §6) → paste the row counts it prints.
4. Run `Azztec_SaaS_Scaffold_Repo_v1_0_0.ps1` → `uv run fastapi dev` → paste `/api/v1/health` JSON.
5. `claude` in the repo → it reads `CLAUDE.md`; run `uvx library-skills --claude` in `backend/` once.
6. 🤙 on `Azztec_SaaS_Planner_Port_Spec_v1_0_0.md` §9 (open decisions OD-1…OD-6) → start **S1 (read-only /range)** in Claude Code.

## 7. Changelog

- 1.0.0 (2026-09-10) Initial. Built from the Workmate Dev project state as of 2026-09-10 (Planner 1.3.1 / API 1.8.3 / UI 1.7.1 live at KT) and web research verified the same day.
