# Azztec SaaS — Project Knowledge Index

**File:** Azztec_SaaS_Project_Knowledge_Index_v1_3_0.md · **Version:** 1.3.0 · **Date:** 2026-09-13 · **Author:** Adriaan
**Status:** Active
**Project:** Workmate Standalone Edition (FastAPI + React + PostgreSQL) — the Azztec Enterprise SaaS rebuild of Workmate CMMS
**Read this first** in every new chat. It says what exists, what to read next, and the standing rules.

---

## 1. What this project is

Workmate is being rebuilt from Ignition Perspective (the "Ignition Edition", live at KT) into a standalone product: **FastAPI backend + React frontend**, PostgreSQL as the target database, MSSQL as the development reality. Development runs against **`dbWorkmate` on the local SQL Server, restored from the Red Stag Timber (RST) Workmate database — ~20 years of real CMMS data**. The first function built is the **Planner** (P-PLN1), ported 1:1 from the live Ignition planner (same JSON contract, same pure rules).

The AI brain (`workmate-ai`, Layers 3–8) is the same service for both editions — see `Workmate_AI_Architecture_v1_2.md`.

**Where the build is:** backend `/api/v1/planner/range` is live on RST and green — S1a (rules) · S1b (sql+repo) · S1c (service+schemas+deps+router) · S1d (diagnostics wiring), 125 tests. `web/` exists (S1e: TanStack Router file-based + Query, Vite 8, Vitest 5, the generated hey-api client, `usePlannerRange` with the 42-day cap). **S1f shipped the read-only `PlannerGrid`**: week / twoweek / month on real RST data with the oracle's DOM and CSS, the OD-24/26 workers rail, OD-25 capacity bars, 6M disabled, deep-links through `app.frontend()` from a code-split `dist/`; 96 frontend tests in 8 files on ESLint 10. HEAD `8f742b4`, tag `s1f-grid-1.0.1`. Next is **S1g — the rest of the read-only planner** (§6), which opens with an audit whose first line is request concurrency/cancellation.

## 2. Read order for a new chat

| # | File | Why |
|---|------|-----|
| 1 | `Azztec_SaaS_Project_Knowledge_Index_v1_3_0.md` | this file |
| 2 | **`Azztec_SaaS_Raw_Log_2026-09-12_v1_1_0.md`** | **where the build actually is** — the S1f record: decisions, mistakes, the box incident, the open list (26 items), the next slice. Supersedes 1.0.0's §7–§9; 1.0.0 §1–§6 (the S1e record) still stand. Supersedes this file's §6 on anything they disagree about |
| 3 | `Azztec_SaaS_Ways_of_Working_v1_3_0.md` | how every deliverable is produced and gated |
| 4 | `Azztec_SaaS_Platform_Landmines_v1_3_0.md` | the gotchas, all verified with dates — **§F "the box" first on any "it's slow"** |
| 5 | `Azztec_SaaS_Architecture_and_Stack_v1_0_2.md` | the stack, decisions D-1…D-12, repo layout as on disk, version pins (§3.2 re-verified on the box 2026-09-12) |
| 6 | `Azztec_SaaS_Data_Layer_and_RST_DB_v1_0_0.md` | the RST database, schema truths, dialect rules |
| 7 | `Azztec_SaaS_Planner_Port_Spec_v1_0_1.md` | the first function — contract, routes, rules, slices S1a–S1g, tests, every signed OD |
| 8 | the chunk spec for the slice in hand (`S1a`…`S1f`) | the template and the precedent |
| 9 | `Azztec_SaaS_Dev_Environment_Install_v1_0_0.md` · `Azztec_SaaS_Community_and_Research_v1_0_0.md` · `Azztec_SaaS_Claude_Code_Workflow_v1_0_0.md` | setup once; research when stuck; the chat ↔ Claude Code loop |

Read 1–4 always. 5–7 before touching Planner code. **The raw logs outrank the compiled docs on current state** — compiled docs describe the design, logs describe the box.

## 3. The file set — live inventory

Everything below should be in project knowledge at the version shown. If a file is live in the repo and missing from this table, project knowledge is stale. Checked against the actual project files on 2026-09-13 (§6.2).

### 3.1 Compiled docs

| File | Version |
|------|---------|
| `Azztec_SaaS_Project_Knowledge_Index` | **1.3.0** |
| `Azztec_SaaS_Ways_of_Working` | **1.3.0** |
| `Azztec_SaaS_Platform_Landmines` | **1.3.0** |
| `Azztec_SaaS_Architecture_and_Stack` | **1.0.2** |
| `Azztec_SaaS_Data_Layer_and_RST_DB` | 1.0.0 |
| `Azztec_SaaS_Planner_Port_Spec` | **1.0.1** (read in full and reissued 2026-09-13 — the correction queue since 2026-09-10 is applied) |
| `Azztec_SaaS_Dev_Environment_Install` | 1.0.0 (corrections queued since 2026-09-10; the web scaffold command is stale — use `scripts/scaffold-web.ps1`; Vite is on 3000) |
| `Azztec_SaaS_Community_and_Research` | 1.0.0 |
| `Azztec_SaaS_Claude_Code_Workflow` | 1.0.0 |
| `Azztec_SaaS_CLAUDE_md` | 1.0.0 |

### 3.2 Chunk specs (the per-slice template)

`Azztec_SaaS_S1a_Rules_Chunk_Spec` 1.0.0 · `Azztec_SaaS_S1b_Data_Chunk_Spec` 1.0.0 · `Azztec_SaaS_S1c_Api_Chunk_Spec` 1.0.0 · `Azztec_SaaS_S1d_Diag_Chunk_Spec` 1.0.0 · `Azztec_SaaS_S1e_Web_Chunk_Spec` 1.0.0 · **`Azztec_SaaS_S1f_Grid_Chunk_Spec` 1.0.0** (append-only; its §6.0 counts, §10 card list and §8 ports are corrected in log 2026-09-12 1.1.0 §7, not in the file)

### 3.3 Raw logs (append-only, never edited)

`Azztec_SaaS_Raw_Log_2026-09-10` 1.0.0 · `Azztec_SaaS_Raw_Log_2026-09-11` 1.0.0 · 1.1.0 · 1.2.0 · `Azztec_SaaS_Raw_Log_2026-09-12` 1.0.0 · **1.1.0**

Each supersedes named sections of the last. Read the newest first, then walk back for anything it doesn't cover. The handover brief (`Azztec_SaaS_Handover_Brief_<date>_vX_Y_Z.md`) is a starter pasted into the first message of a new chat — not project knowledge; regenerate it from the newest log.

### 3.4 Backend code — current repo state (unchanged since S1d)

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

### 3.4b Frontend code — current repo state (S1e + S1f)

| Module | Version | Delivered as |
|--------|---------|--------------|
| `web/openapi-ts.config.ts` | 1.0.1 | `Azztec_SaaS_web_openapi_ts_config_v1_0_1.ts` |
| `web/eslint.config.js` | 1.0.0 | `Azztec_SaaS_web_eslint_config_v1_0_0.js` |
| `web/src/main.tsx` | 1.0.0 | `Azztec_SaaS_web_main_v1_0_0.tsx` (the CLI's file + `QueryClientProvider` + Query devtools) |
| `web/src/routes/planner.tsx` | **1.0.1** | `Azztec_SaaS_web_routes_planner_v1_0_1.tsx` (exports `Route` only; version in the header) |
| `web/src/lib/dates.ts` | **1.1.0** | `Azztec_SaaS_web_lib_dates_v1_1_0.ts` (the only module touching `Date`) |
| `web/src/features/planner/usePlannerRange.ts` | 1.0.0 | `Azztec_SaaS_web_usePlannerRange_v1_0_0.ts` |
| `web/src/features/planner/rules.ts` | **1.0.1** | `Azztec_SaaS_web_planner_rules_v1_0_1.ts` |
| `web/src/features/planner/store.ts` | 1.0.0 | `Azztec_SaaS_web_planner_store_v1_0_0.ts` |
| `web/src/features/planner/planner.css` | **1.0.1** | `Azztec_SaaS_web_planner_css_v1_0_1.css` |
| `web/src/features/planner/range.fixture.ts` | 1.0.0 | `Azztec_SaaS_web_planner_range_fixture_v1_0_0.ts` (test helper) |
| `web/src/features/planner/WOCard.tsx` | 1.0.0 | `Azztec_SaaS_web_planner_WOCard_v1_0_0.tsx` |
| `web/src/features/planner/DayCell.tsx` | 1.0.0 | `Azztec_SaaS_web_planner_DayCell_v1_0_0.tsx` |
| `web/src/features/planner/CapacityBar.tsx` | 1.0.0 | `Azztec_SaaS_web_planner_CapacityBar_v1_0_0.tsx` (also exports `WeekStrip`) |
| `web/src/features/planner/PlannerGrid.tsx` | 1.0.0 | `Azztec_SaaS_web_planner_PlannerGrid_v1_0_0.tsx` |
| `web/src/features/planner/PlannerHeader.tsx` | 1.0.0 | `Azztec_SaaS_web_planner_PlannerHeader_v1_0_0.tsx` |
| `web/src/features/planner/WorkerPanel.tsx` | 1.0.0 | `Azztec_SaaS_web_planner_WorkerPanel_v1_0_0.tsx` |
| `web/src/features/planner/PlannerView.tsx` | 1.0.0 | `Azztec_SaaS_web_planner_PlannerView_v1_0_0.tsx` (props-driven whole view) |

Generated on the box, committed, never cards: `web/src/api/client/**` (17 files, openapi-ts 0.99.0 from `openapi_0_3_0.json`), `web/src/routeTree.gen.ts`. CLI-written, committed as-is: `package.json` (+ `pnpm-lock.yaml`, ESLint 10), `vite.config.ts` (+proxy), `vitest.config.ts` (no setupFiles, no globals), `tsconfig.json`, `prettier.config.js`, `.prettierignore`, `pnpm-workspace.yaml`, `src/styles.css`, `src/routes/__root.tsx`, `src/routes/index.tsx`, and `src/router.tsx` — **dead** (never imported by `main.tsx`; deleted in S1g). `web/dist/` is gitignored.

### 3.5 Tests

| File | Version |
|------|---------|
| `backend/tests/test_smoke.py` | 1.1.0 |
| `backend/tests/test_planner_rules.py` | 1.0.0 |
| `backend/tests/test_planner_repo.py` | 1.0.1 |
| `backend/tests/test_planner_api.py` | 1.0.1 |
| `backend/tests/test_diag_wiring.py` | 1.0.1 |
| `backend/tests/test_openapi_contract.py` | 1.0.0 |
| `web/src/lib/dates.test.ts` | **1.1.0** |
| `web/src/features/planner/usePlannerRange.test.tsx` | 1.0.0 |
| `web/src/features/planner/rules.test.ts` | **1.0.1** |
| `web/src/features/planner/WOCard.test.tsx` | 1.0.0 |
| `web/src/features/planner/CapacityBar.test.tsx` | 1.0.0 |
| `web/src/features/planner/PlannerGrid.test.tsx` | 1.0.0 (covers `DayCell`) |
| `web/src/features/planner/WorkerPanel.test.tsx` | 1.0.0 |
| `web/src/features/planner/PlannerView.test.tsx` | 1.0.0 (the one file that stubs `fetch`; covers `PlannerHeader` and the wire) |

Backend 125 · frontend 96 in 8 files, as counted 2026-09-12 — count from the run. Not yet reviewed in chat: `backend/tests/conftest.py` (see log 2026-09-11 1.2.0 §8.4).

### 3.6 Config and scripts

`Azztec_SaaS_pyproject` 1.0.0 · `Azztec_SaaS_dotenv_example` 1.0.1 · `Azztec_SaaS_docker_compose` 1.0.0 (do not run it until Docker Desktop has a memory cap — Landmines §F) · `Azztec_SaaS_Bootstrap_Windows` 1.0.0 · `Azztec_SaaS_Scaffold_Repo` **1.0.1** (now in project knowledge; its web section is stale — 1.0.2 pointing at `scaffold-web.ps1` still queued) · `Azztec_SaaS_Scaffold_Web` 1.0.1 (web/ only, idempotent)

### 3.7 Reference sources — the parity oracle

The raw Ignition sources the port is measured against (from `MainSCADA_Timberlands_2026-09-10_1900.zip`): `workmate_planner_code_v1_3_1.py` · `workmate_planner_api_code_v1_8_3.py` · `workmate_planner_ai_code_v1_1_0.py` · `workmate_planner_chat_code_v1_2_1.py` · `workmate_planner_test_code_v1_0_0.py` · `PlannerCalendar_v1_3_0_view.json` · `Planner_v1_8_1.html` + `wm-ui.css` / `wm-ui.js` (line numbers in the chunk specs refer to these).

Also present: `Workboard_v1_0_0.html` — the Ignition Work Board (P-WB1 slice S1, 2026-09-07, served from `workmate.workboard_api`, shares the planner's `wm-ui` kit). Not a planner-port input; the oracle for a later Work Board port. Lives in no SaaS repo path.

Generated, committed, not hand-edited: `docs/api/openapi_0_3_0.json`.

### 3.8 Carry-over from the Workmate Dev project (copy, do not rewrite)

`Workmate_PG_Forward_Compat_v1_0.md` · `Workmate_AI_Architecture_v1_2.md` · `Workmate_Planner_Assistant_Prompts_v1_0_0.md` · `Workmate_Forensic_Diagnostics_Standard_v1_1_0.md` · `Workmate_Security_Enforcement_Standard_v1_0_0.md` · `Workmate_NET_Logic_Reference_v1_1.md` + `Workmate_NET_Manual_Index.md` · `All_Tables_InDetail.csv` + `All_Stored_Procedures_and_Views.csv` · `Workmate_Knowledge_Journal_v3_7.md` §3.

## 4. Standing rules (one screen)

1. **Sequence:** audit → spec → 🤙 → one slice → versioned raw file(s) as Download cards → smoke → raw log → next. Never run ahead of 🤙. The audit may cut the scope it was handed; an unsigned dependency is the next audit's first line, not this build's next step.
2. **Version everything, never overwrite.** Delivered filename carries `_vX_Y_Z`; the file carries `__version__` / a header (route files: header only). Tag the version that **shipped**, not the one the spec predicted.
3. **Raw source files only**, one per Download card, via `present_files`. No inline code dumps, no zips. Each card states **PK: add / replaces `<version>`**.
4. **Pair rule:** every library slice ships with its tests. Pure rules are tested with zero DB — and a zero-DB test must actually be zero-DB; zero-network means the stubbed fetch is asserted never called.
5. **`DRY_RUN = True` first** on anything that writes; Marker Law (residue = 0) on anything touching real data — the RST DB is real data even in dev.
6. **Fact-check before build:** confirm columns / codes / flags against the schema CSVs and the DB. Never re-emit a file you have not read — CLI-written files, generated code and the oracle's strings included.
7. **Dialect-portable SQL** (COALESCE / CURRENT_TIMESTAMP / CONCAT / OFFSET-FETCH / `dbo.` / `-- PG-CONVERT:` tags). The CI gate greps the whole file — describe banned tokens, never spell them.
8. **Forensic diagnostics** on every request outcome: [F] what happened, [G] why blocked, [E] crash — one `diag.log()` seam, wired by `diag.configure()`. Assert **emission**, not the call.
9. **Check the box before the code.** On any "it's slow": free memory and the top-5 processes by working set first, verbatim. Healthy `/range` is 70–700 ms; over 2 s is the box (Landmines §F).
10. **Comms:** short, direct, NZ-casual. Console output pasted verbatim before proceeding. Shell blocks complete and copy-pasteable, starting with `cd C:\dev\workmate-saas…`; servers in their own windows via `Start-Process`. 🤙 = go.
11. **Close every session with a raw log** and the doc updates it implies. Carry forward every open item you do not close.

## 5. Environment snapshot (verified 2026-09-12)

| Thing | Value |
|-------|-------|
| Dev machine | Windows 11 x64, 32 GB, Windows PowerShell 5.1 in practice; execution policy `CurrentUser RemoteSigned`. A fresh window opens in `system32` |
| Dev DB | local SQL Server `AzztecDev` (Standard Developer Edition 64-bit 17.0.1000.7) → `dbWorkmate` restored from the **RST** backup; SQL login `svc_workmate` (`VIEW SERVER STATE`, not `VIEW SERVER PERFORMANCE STATE`); dev actor `WORKMATE_DEV_USER_ID=1` (SYS_USER). **`max server memory` uncapped — cap at 8 GB in SSMS under a sysadmin login before the next smoke** |
| Docker Desktop | **off until it has a memory cap** — held 45 GB of the box on 2026-09-12 and starved SQL Server |
| Live reference | Ignition gateway `MainSCADA_Timberlands` (KT) — the parity oracle, **copy not yet obtained** |
| Backend | Python 3.13.15 (uv 0.12.12), FastAPI 0.141.x, SQLAlchemy 2.0.5x (sync Core), pyodbc 5.3 + ODBC Driver 18 |
| Frontend | node v24.19.0, pnpm 12.3.4 · `@tanstack/cli` 0.71.0 scaffold, `--router-only --toolchain eslint` · React 19.3.0, Router 1.170.35, Query 5.102.8, Vite 8.3.0, **TypeScript 6.0.3** (OD-28; TS 7.0.2 published, not taken), Vitest 5.0.0 + RTL 16.3.3 + jsdom 30.0.1, hey-api 0.99.0, **ESLint 10.10.0** + Prettier 3.9.6, zustand 5.0.15, tailwindcss 4.3.3, date-fns 4.4.0, zod 4.6.1 |
| Target DB | PostgreSQL 18.6 (Docker on dev — see the Docker row) |
| Repo | `C:\dev\workmate-saas` — `backend/`, `web/`, `docs/`, `scripts/`, `.claude/`. HEAD **`8f742b4`** (`s1f-grid-1.0.1`; the docs commit for this set lands on top). Previous tags `s1e-web-1.0.1` at `963fcca`, `s1d-diag-1.1.1` at `b1caa50` |
| Claude Code | 2.1.267 native, `C:\Users\Azzte\.local\bin\claude.exe` (added to PATH manually) |
| Ports | API 8000, **Vite 3000** (Node binds `localhost` to `::1` — port checks try both stacks), Postgres 5432, Adminer 8080 |
| Git author | `AzztecEnterprise <azztecdev@gmail.com>` |

**Mark-of-the-Web rule:** every Download card carries the zone tag. `Unblock-File` after each drop — and remember it is not a copy; `Test-Path` each target by exact filename (Ways of Working §2).

## 6. Picking up the build

1. Read `Azztec_SaaS_Raw_Log_2026-09-12_v1_1_0.md` — §8 is the open list (26 items), §9 is S1g and its seven carry-ins, §6 is the box incident.
2. **The box first:** free memory + top-5 processes by working set, pasted. If Docker Desktop is running without a cap, it comes down before anything else (Landmines §F).
3. `cd C:\dev\workmate-saas\backend; uv run pytest -q | Select-Object -Last 6` → expect **125 green, zero red**. `cd ..\web; pnpm test` → expect **96 green in 8 files**. Anything else means the tree moved since this Index.
4. Backend in its own window: `Start-Process powershell -ArgumentList '-NoExit','-Command','cd C:\dev\workmate-saas\backend; uv run fastapi dev app/main.py'` → expect the boot lines (`[F] diag wired` first, no `[G] frontend not built` — `dist/` exists) and `/health` `frontend: "built"`. If `frontend: "missing"`, `pnpm --dir web build` first; `dist/` is gitignored. Vite, when needed, in a third window on `:3000`.
5. Audit the next slice before proposing a spec. The S1g audit opens with request concurrency/cancellation (log §8.18), then the two memory caps (§8.16/§8.17), Adriaan's hover list (§8.22), priority colours as an OD (§8.19).

### 6.1 Signed, so nobody re-litigates

OD-1 and OD-6 (2026-09-10); OD-7…OD-20 (2026-09-11, S1a–S1d gates); **OD-21…OD-25** (2026-09-11, S1e gate: toolchain, generator, 42-day cap, internal-by-default rail, the oracle's capacity bar); **OD-26…OD-29** (2026-09-12, S1f gate: rail toggles + count line, the oracle's CSS ported under `.wm-planner`, TypeScript 6.x / ESLint 10, URL = `mode` + `anchor`). One-liners and gates in Port Spec 1.0.1 §9; terms in §1 of the log named there.

### 6.2 Project knowledge vs this inventory (checked 2026-09-13)

The eight files 1.2.0 §6.2 listed as missing are **all present now** — `rules_v1_0_0.py`, `sql_v1_0_1.py`, `repo_v1_0_0.py`, `test_planner_rules_v1_0_0.py`, `test_planner_repo_v1_0_1.py`, the S1a and S1b chunk specs, raw log 2026-09-11 1.1.0, `Scaffold_Repo_v1_0_1.ps1`. The next backend audit can read `rules.py` instead of reconstructing it; log 1.1.0 §8.11 closes.

**Superseded versions still in project knowledge — remove:** `Azztec_SaaS_test_planner_api_v1_0_0.py` (1.0.1 is there), `Azztec_SaaS_Scaffold_Repo_v1_0_0.ps1` (1.0.1), `Azztec_SaaS_web_planner_css_v1_0_0.css` (1.0.1), `Azztec_SaaS_web_routes_planner_v1_0_0.tsx` (1.0.1). Raw logs are the exception — every version stays. After this docs commit, the same applies to Index 1.2.0, Landmines 1.2.0, Ways of Working 1.2.0, Architecture 1.0.1 and Port Spec 1.0.0.

## 7. Changelog

- 1.3.0 (2026-09-13) Reissued after S1f (log 2026-09-12 1.1.0 §7). §1 state: `PlannerGrid` read-only shipped, HEAD `8f742b4`, tag `s1f-grid-1.0.1`, 96 + 125. §2 read order leads with log 1.1.0 and the 1.3.0 / 1.0.2 / 1.0.1 compiled set. §3: S1f spec, the new log, the fourteen S1f frontend files (3.4b) and six test files (3.5), `router.tsx` marked dead, Scaffold_Repo 1.0.1 now in PK, `Workboard_v1_0_0.html` recorded in §3.7, the handover brief explained. §4 gains the memory-first rule and the shell/window discipline. §5 re-verified from the S1f session: SQL Server edition and the uncapped memory, the Docker row, ESLint 10, TypeScript 6 / TS 7, Vite on 3000, the S1f dependency versions. §6 pick-up steps: box first, `-Last 6`, servers via `Start-Process`, both suite counts, the S1g audit order. §6.1 extended to OD-29. §6.2 rewritten from the actual project files: the eight gaps are filled, four superseded files named for removal.
- 1.2.0 (2026-09-12) Reissued after S1e. §1 state: `web/` exists, tag `s1e-web-1.0.1`. Read order now leads with the 2026-09-12 log. §3 gains the frontend code table (3.4b), the two Vitest files, the S1e spec, the new log, and the scaffold-web script; Scaffold_Repo's on-box 1.0.1 flagged as not uploaded. §5 frontend row filled in from the box. §6 pick-up steps cover both suites and the `dist/`-present boot; §6.1 replaced by the five signed decisions; §6.2 names the project-knowledge gaps.
- 1.1.0 (2026-09-11) Reissued after S1d. Read order puts the newest raw log second and states that logs outrank compiled docs on current state. §3 replaced with the full live inventory — backend modules, tests, chunk specs, logs — so a missing file in project knowledge is visible at a glance. §4 absorbs the scope-cut, tag-what-shipped, PK-marking, read-before-re-emitting and emission-testing rules. §5 re-verified against the box. §6 replaces the completed first-session checklist with how to pick the build up, and names the one unsigned decision blocking S1e.
- 1.0.0 (2026-09-10) Initial. Built from the Workmate Dev project state as of 2026-09-10 (Planner 1.3.1 / API 1.8.3 / UI 1.7.1 live at KT).
