# Azztec SaaS — Project Knowledge Index

**File:** Azztec_SaaS_Project_Knowledge_Index_v1_5_0.md · **Version:** 1.5.0 · **Date:** 2026-09-13 · **Author:** Adriaan
**Status:** Active
**Project:** Workmate Standalone Edition (FastAPI + React + PostgreSQL) — the Azztec Enterprise SaaS rebuild of Workmate CMMS
**Read this first** in every new chat. It says what exists, what to read next, and the standing rules.

---

## 1. What this project is

Workmate is being rebuilt from Ignition Perspective (the "Ignition Edition", live at KT) into a standalone product: **FastAPI backend + React frontend**, PostgreSQL as the target database, MSSQL as the development reality. Development runs against **`dbWorkmate` on the local SQL Server, restored from the Red Stag Timber (RST) Workmate database — ~20 years of real CMMS data**. The first function built is the **Planner** (P-PLN1), ported 1:1 from the live Ignition planner (same JSON contract, same pure rules).

The AI brain (`workmate-ai`, Layers 3–8) is the same service for both editions — see `Workmate_AI_Architecture_v1_2.md`.

**Where the build is:** backend `/api/v1/planner/range` is live on RST and green — S1a (rules) · S1b (sql+repo) · S1c (service+schemas+deps+router) · S1d (diagnostics wiring), 125 tests, unchanged since S1d. `web/` (S1e) carries the **read-only planner, complete**: S1f shipped `PlannerGrid` (week / twoweek / month on real RST data with the oracle's DOM and CSS, the OD-24/26 rail, OD-25 bars, 6M disabled, deep links through `app.frontend()`); S1g shipped the rest — the filters row with the oracle's full precedence, the rail's team filter and click-to-filter, the read-only Selected WO card (OD-5), the day dialog as a plain component (OD-31), keyboard `← → T Esc`, the OD-30 cancellation test, `router.tsx` deleted; **155 frontend tests in 11 files** on ESLint 10.10.0 / TypeScript 6.0.3. Slice tag **`s1g-readonly-1.1.1`** at `449f19d`; docs commits `23c90ea` (the five compiled docs from log 09-13 1.0.0) and **`c4e17f9`** (the KT delta) on top — HEAD `c4e17f9`, tree clean at the close of log 1.1.0 (the four `docs/reference/` files and that log were pending — `git status` says). Both suites re-verified **bare** on the box 2026-09-13, second session: 125 passed exit 0, 155 in 11 files exit 0. OD-32 (priority badge colour by rank) was signed, built and **withdrawn the same day** against `dbo.Priority` — rank is not priority on RST. Both memory caps are applied (§5).

**The KT production database is on the box.** `dbWorkmate_KT` — restored 2026-09-13 from a `KTSQL02` backup, **READ_ONLY**, compat 100, on the same instance as RST's `dbWorkmate` — closed a five-session blocker (item 26 reclassified) and produced `Azztec_SaaS_KT_Schema_Delta_v1_0_0.md`: 46 KT-only tables triaged to 21 real and 25 junk, 10 real column additions, 12 routines classified, nine questions for the uplift audit. No OD was signed, no build ran and nothing was written to any database in that session — everything it produced is audit input.

**Next is not a build.** The **backend audit** — items **30** (alternating `/range` latency on a clean box, DMV wait types first), **29** (`Priority.Colour` to the badge — now evidenced on both databases) and **21** (`initialsOf` on parentheses) — then the **uplift audit** (item **32**: one additive migration scripted from `dbWorkmate_KT`'s catalog, never typed; the nine questions in delta §8), then the S2 audit (move / undo / estimate, the first slice that writes to RST). Tips (item 33) is its own audit whenever Adriaan wants it.

## 2. Read order for a new chat

| # | File | Why |
|---|------|-----|
| 1 | `Azztec_SaaS_Project_Knowledge_Index_v1_5_0.md` | this file |
| 2 | **`Azztec_SaaS_Raw_Log_2026-09-13_v1_1_0.md`** | **where the build actually is** — the KT-database session: no OD, no build; the eight mistakes (§4, seven of them now Landmines §A/§B), what the KT copy verified (§5: provenance, the delta headline, `WO_N_Plan` read, item 29 both sides, identity/diag/tips, the orphans), the open list (§7, 14 items), next (§8). Supersedes 2026-09-13 1.0.0's §7–§9; that log's §1–§6 (the S1g record) still stand. Supersedes this file's §6 on anything they disagree about |
| 3 | `Azztec_SaaS_Ways_of_Working_v1_3_2.md` | how every deliverable is produced and gated — **run the suites bare, verify before you commit** |
| 4 | `Azztec_SaaS_Platform_Landmines_v1_5_0.md` | the gotchas, all verified with dates — **§F "the box" first on any "it's slow", and its last two lines before blaming the box**; §B before any `sqlcmd` or `.bak` work |
| 5 | `Azztec_SaaS_Architecture_and_Stack_v1_0_4.md` | the stack, decisions D-1…D-12, repo layout as on disk, version pins (§3.2 re-verified on the box 2026-09-12, unchanged through S1g); §3.3 the two databases |
| 6 | `Azztec_SaaS_Data_Layer_and_RST_DB_v1_0_0.md` | the RST database, schema truths, dialect rules |
| 7 | `Azztec_SaaS_Planner_Port_Spec_v1_0_3.md` | the first function — contract, routes, rules, slices S1a–S1g done, the three audits before S2, tests, every signed OD incl. the withdrawn one |
| 8 | **`Azztec_SaaS_KT_Schema_Delta_v1_0_0.md`** | **before anything touching the database** — what KT has that RST lacks, what is used, what should cross; the uplift audit's input (its §8 questions); the `WO_N_Plan` / `Diag_Log` / `Ignition_User_Map` DDL as read |
| 9 | the chunk spec for the slice in hand (`S1a`…`S1g`) | the template and the precedent |
| 10 | `Azztec_SaaS_Dev_Environment_Install_v1_0_0.md` · `Azztec_SaaS_Community_and_Research_v1_0_0.md` · `Azztec_SaaS_Claude_Code_Workflow_v1_0_0.md` | setup once; research when stuck; the chat ↔ Claude Code loop |

Read 1–4 always. 5–8 before touching Planner code or the database. **The raw logs outrank the compiled docs on current state** — compiled docs describe the design, logs describe the box. Once a log's doc set has been applied (this Index is that, for 2026-09-13 1.1.0 §6), the next audit reads the docs, not the log.

## 3. The file set — live inventory

Everything below should be in project knowledge at the version shown. If a file is live in the repo and missing from this table, project knowledge is stale. Checked against the actual project files on 2026-09-13, second session (§6.2).

### 3.1 Compiled docs

| File | Version |
|------|---------|
| `Azztec_SaaS_Project_Knowledge_Index` | **1.5.0** |
| `Azztec_SaaS_Ways_of_Working` | **1.3.2** |
| `Azztec_SaaS_Platform_Landmines` | **1.5.0** |
| `Azztec_SaaS_Architecture_and_Stack` | **1.0.4** |
| `Azztec_SaaS_Data_Layer_and_RST_DB` | 1.0.0 |
| `Azztec_SaaS_Planner_Port_Spec` | **1.0.3** |
| **`Azztec_SaaS_KT_Schema_Delta`** | **1.0.0** — evidence complete, nothing signed; committed `c4e17f9`, target `docs/` |
| `Azztec_SaaS_Dev_Environment_Install` | 1.0.0 (corrections queued since 2026-09-10 — a fifth session unapplied; the web scaffold command is stale — use `scripts/scaffold-web.ps1`; Vite is on 3000; `sqlcmd -E -C` replaces the SSMS steps) |
| `Azztec_SaaS_Community_and_Research` | 1.0.0 |
| `Azztec_SaaS_Claude_Code_Workflow` | 1.0.0 |
| `Azztec_SaaS_CLAUDE_md` | 1.0.0 |

### 3.2 Chunk specs (the per-slice template)

`Azztec_SaaS_S1a_Rules_Chunk_Spec` 1.0.0 · `Azztec_SaaS_S1b_Data_Chunk_Spec` 1.0.0 · `Azztec_SaaS_S1c_Api_Chunk_Spec` 1.0.0 · `Azztec_SaaS_S1d_Diag_Chunk_Spec` 1.0.0 · `Azztec_SaaS_S1e_Web_Chunk_Spec` 1.0.0 · `Azztec_SaaS_S1f_Grid_Chunk_Spec` 1.0.0 (append-only; its §6.0 counts, §10 card list and §8 ports are corrected in log 2026-09-12 1.1.0 §7, not in the file) · `Azztec_SaaS_S1g_Readonly_Chunk_Spec` 1.0.0 (append-only; its OD-32 is withdrawn and its `planner.css` 1.1.0 shipped as 1.1.1, the `SelectedWOCard`/`DayDialog` tests as 1.0.1 — corrected in log 2026-09-13 1.0.0 §2/§4.1, not in the file; committed in `0cb41b8`, one commit after the slice, because it was not in Downloads when the slice committed)

### 3.3 Raw logs (append-only, never edited)

`Azztec_SaaS_Raw_Log_2026-09-10` 1.0.0 · `Azztec_SaaS_Raw_Log_2026-09-11` 1.0.0 · 1.1.0 · 1.2.0 · `Azztec_SaaS_Raw_Log_2026-09-12` 1.0.0 · 1.1.0 · `Azztec_SaaS_Raw_Log_2026-09-13` 1.0.0 · **1.1.0**

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
| `backend/app/planner/sql.py` | 1.0.1 | `..._app_planner_sql_v1_0_1.py` (the `_PRIORITY_SQL` column names are at 201–204 — read them, don't remember them) |
| `backend/app/planner/repo.py` | 1.0.0 | `..._app_planner_repo_v1_0_0.py` |
| `backend/app/planner/service.py` | 1.0.1 | `..._app_planner_service_v1_0_1.py` |
| `backend/app/planner/schemas.py` | 1.0.0 | `..._app_planner_schemas_v1_0_0.py` |
| `backend/app/planner/router.py` | 1.0.1 | `..._app_planner_router_v1_0_1.py` |

### 3.4b Frontend code — current repo state (S1e + S1f + S1g)

| Module | Version | Delivered as |
|--------|---------|--------------|
| `web/openapi-ts.config.ts` | 1.0.1 | `Azztec_SaaS_web_openapi_ts_config_v1_0_1.ts` |
| `web/eslint.config.js` | 1.0.0 | `Azztec_SaaS_web_eslint_config_v1_0_0.js` |
| `web/src/main.tsx` | 1.0.0 | `Azztec_SaaS_web_main_v1_0_0.tsx` (the CLI's file + `QueryClientProvider` + Query devtools) |
| `web/src/routes/planner.tsx` | 1.0.1 | `Azztec_SaaS_web_routes_planner_v1_0_1.tsx` (exports `Route` only; version in the header) |
| `web/src/lib/dates.ts` | 1.1.0 | `Azztec_SaaS_web_lib_dates_v1_1_0.ts` (the only module touching `Date`) |
| `web/src/features/planner/usePlannerRange.ts` | 1.0.0 | `Azztec_SaaS_web_usePlannerRange_v1_0_0.ts` |
| `web/src/features/planner/rules.ts` | **1.1.0** | `Azztec_SaaS_web_planner_rules_v1_1_0.ts` (filter + capacity precedence, rank map, dialog/card rows — no `Date`, no DOM) |
| `web/src/features/planner/store.ts` | **1.1.0** | `Azztec_SaaS_web_planner_store_v1_1_0.ts` (filters, `clearFilters`, `dayOpen`, `clearSelect`) |
| `web/src/features/planner/planner.css` | **1.1.1** | `Azztec_SaaS_web_planner_css_v1_1_1.css` (S1g blocks; zero `.pri.r*` colour rules — OD-32 withdrawn) |
| `web/src/features/planner/range.fixture.ts` | **1.1.0** | `Azztec_SaaS_web_planner_range_fixture_v1_1_0.ts` (test helper; RST-shaped priorities, two labour rows, `hasPO`, a two-day span) |
| `web/src/features/planner/WOCard.tsx` | **1.0.1** | `Azztec_SaaS_web_planner_WOCard_v1_0_1.tsx` (`priRank` prop; title unchanged) |
| `web/src/features/planner/DayCell.tsx` | **1.0.1** | `Azztec_SaaS_web_planner_DayCell_v1_0_1.tsx` (day-head click; cell/list click clears) |
| `web/src/features/planner/CapacityBar.tsx` | 1.0.0 | `Azztec_SaaS_web_planner_CapacityBar_v1_0_0.tsx` (also exports `WeekStrip`; 1.0.1 taking `nWorkers` is open item 27) |
| `web/src/features/planner/PlannerGrid.tsx` | **1.0.1** | `Azztec_SaaS_web_planner_PlannerGrid_v1_0_1.tsx` (filters → capacity precedence, rank map, grid background click) |
| `web/src/features/planner/PlannerHeader.tsx` | 1.0.0 | `Azztec_SaaS_web_planner_PlannerHeader_v1_0_0.tsx` |
| `web/src/features/planner/WorkerPanel.tsx` | **1.1.0** | `Azztec_SaaS_web_planner_WorkerPanel_v1_1_0.tsx` (team filter, `.on`, click-to-filter) |
| `web/src/features/planner/PlannerView.tsx` | **1.1.0** | `Azztec_SaaS_web_planner_PlannerView_v1_1_0.tsx` (composition + document keyboard `← → T Esc`) |
| `web/src/features/planner/FiltersRow.tsx` | **1.0.0** | `Azztec_SaaS_web_planner_FiltersRow_v1_0_0.tsx` (S1g) |
| `web/src/features/planner/SelectedWOCard.tsx` | **1.0.0** | `Azztec_SaaS_web_planner_SelectedWOCard_v1_0_0.tsx` (S1g, read-only, `Open` disabled per OD-5) |
| `web/src/features/planner/DayDialog.tsx` | **1.0.0** | `Azztec_SaaS_web_planner_DayDialog_v1_0_0.tsx` (S1g, plain component on the oracle's CSS — OD-31) |

Generated on the box, committed, never cards: `web/src/api/client/**` (17 files, openapi-ts 0.99.0 from `openapi_0_3_0.json`), `web/src/routeTree.gen.ts`. CLI-written, committed as-is: `package.json` (+ `pnpm-lock.yaml`, ESLint 10), `vite.config.ts` (+proxy), `vitest.config.ts` (no setupFiles, no globals), `tsconfig.json`, `prettier.config.js`, `.prettierignore`, `pnpm-workspace.yaml`, `src/styles.css`, `src/routes/__root.tsx`, `src/routes/index.tsx` (not in PK — paste it before touching it). **`src/router.tsx` is deleted** (S1g, `449f19d`; open item 20 closed). `web/dist/` is gitignored. No `components.json`, no `components/ui/` — shadcn is not installed (OD-31).

### 3.5 Tests

| File | Version |
|------|---------|
| `backend/tests/test_smoke.py` | 1.1.0 |
| `backend/tests/test_planner_rules.py` | 1.0.0 |
| `backend/tests/test_planner_repo.py` | 1.0.1 |
| `backend/tests/test_planner_api.py` | 1.0.1 |
| `backend/tests/test_diag_wiring.py` | 1.0.1 |
| `backend/tests/test_openapi_contract.py` | 1.0.0 |
| `web/src/lib/dates.test.ts` | 1.1.0 |
| `web/src/features/planner/usePlannerRange.test.tsx` | 1.0.0 |
| `web/src/features/planner/rules.test.ts` | **1.1.0** (55 cases) |
| `web/src/features/planner/WOCard.test.tsx` | **1.0.1** |
| `web/src/features/planner/CapacityBar.test.tsx` | 1.0.0 |
| `web/src/features/planner/PlannerGrid.test.tsx` | **1.0.1** (covers `DayCell`) |
| `web/src/features/planner/WorkerPanel.test.tsx` | **1.1.0** |
| `web/src/features/planner/FiltersRow.test.tsx` | **1.0.0** |
| `web/src/features/planner/SelectedWOCard.test.tsx` | **1.0.1** (the spec said 1.0.0; 1.0.1 shipped) |
| `web/src/features/planner/DayDialog.test.tsx` | **1.0.1** (same) |
| `web/src/features/planner/PlannerView.test.tsx` | **1.1.0** (the one file that stubs `fetch`; covers `PlannerHeader`, the wire and the OD-30 abort) |

Backend **125** · frontend **155 in 11 files**, as counted 2026-09-13 and re-verified bare (exit 0) in the second session — count from the run. Not yet reviewed in chat: `backend/tests/conftest.py` (see log 2026-09-11 1.2.0 §8.4).

### 3.6 Config and scripts

`Azztec_SaaS_pyproject` 1.0.0 (`addopts = "-q"` at line 49 — never add a second `-q`) · `Azztec_SaaS_dotenv_example` 1.0.1 · `Azztec_SaaS_docker_compose` 1.0.0 (waits for Docker's first clean start under the `.wslconfig` cap — open item 17) · `Azztec_SaaS_Bootstrap_Windows` 1.0.0 · `Azztec_SaaS_Scaffold_Repo` 1.0.1 (its web section is stale — 1.0.2 pointing at `scaffold-web.ps1` still queued, fifth session) · `Azztec_SaaS_Scaffold_Web` 1.0.1 (web/ only, idempotent)

### 3.7 Reference sources — the parity oracle

The raw Ignition sources the port is measured against (from `MainSCADA_Timberlands_2026-09-10_1900.zip`): `workmate_planner_code_v1_3_1.py` · `workmate_planner_api_code_v1_8_3.py` · `workmate_planner_ai_code_v1_1_0.py` · `workmate_planner_chat_code_v1_2_1.py` · `workmate_planner_test_code_v1_0_0.py` · `PlannerCalendar_v1_3_0_view.json` · `Planner_v1_8_1.html` + `wm-ui.css` / `wm-ui.js` (line numbers in the chunk specs refer to these).

**Extracted 2026-09-13 into `docs/reference/`** (from the same export, for the audits that need them): `workmate_pm_engine_code_v2_5_0.py` (65,249 B — S2's weekno reference, the verbatim `GetWeekNoANDYear` port) · `workmate_identity_code_v1_1_1.py` (7,892 B — OD-2's precedent, the self-healing `resolve`) · `TipBadge_2026-09-10_view.json` (4,953 B) · `TipPopup_2026-09-10_view.json` (6,972 B — the two together are item 33's pattern). All four in project knowledge; their commit was pending at the close of log 1.1.0. The export itself (33 MB) is on the box, **not in PK** — upload it to a chat only when a module's audit needs it, and extract that module's files as versioned cards rather than carrying the zip around.

**The other oracle is a database:** `dbWorkmate_KT` (§5). `Azztec_SaaS_KT_Schema_Delta_v1_0_0.md` (§3.1) is what the two oracles said together — **the database says what exists, the gateway export says what is used** — and it is read before anything touches the database.

Also present: `Workboard_v1_0_0.html` — the Ignition Work Board (P-WB1 slice S1, 2026-09-07, served from `workmate.workboard_api`, shares the planner's `wm-ui` kit). Not a planner-port input; the oracle for a later Work Board port. Lives in no SaaS repo path.

Generated, committed, not hand-edited: `docs/api/openapi_0_3_0.json`.

Not in project knowledge, by decision: the **Forensics pack** (8 files, ~2,700 lines, `diag` schema, own middleware/SDK/provider, night-replay design) — handed over 2026-09-13 and set aside by Adriaan ("forget about Forensics, we have diag"); not audited, no decisions taken (open item 31). If it returns it needs its own audit against `diag.py` 1.1.1, D-6/D-8, OD-18…OD-20, the Alembic plan and the privacy question its own OD-3 raises.

### 3.8 Carry-over from the Workmate Dev project (copy, do not rewrite)

`Workmate_PG_Forward_Compat_v1_0.md` · `Workmate_AI_Architecture_v1_2.md` · `Workmate_Planner_Assistant_Prompts_v1_0_0.md` · `Workmate_Forensic_Diagnostics_Standard_v1_1_0.md` · `Workmate_Security_Enforcement_Standard_v1_0_0.md` · `Workmate_NET_Logic_Reference_v1_1.md` + `Workmate_NET_Manual_Index.md` · `All_Tables_InDetail.csv` + `All_Stored_Procedures_and_Views.csv` · `Workmate_Knowledge_Journal_v3_7.md` §3.

## 4. Standing rules (one screen)

1. **Sequence:** audit → spec → 🤙 → one slice → versioned raw file(s) as Download cards → smoke → raw log → next. Never run ahead of 🤙. The audit may cut the scope it was handed; an unsigned dependency is the next audit's first line, not this build's next step.
2. **Version everything, never overwrite.** Delivered filename carries `_vX_Y_Z`; the file carries `__version__` / a header (route files: header only). Tag the version that **shipped**, not the one the spec predicted. A withdrawn decision keeps its ID, struck through, with the reason (OD-32).
3. **Raw source files only**, one per Download card, via `present_files`. No inline code dumps, no zips. Each card states **PK: add / replaces `<version>`**. Save every card before the block that copies it runs — Downloads is not a staging area, and it has now eaten a deliverable in two consecutive sessions.
4. **Pair rule:** every library slice ships with its tests. Pure rules are tested with zero DB — and a zero-DB test must actually be zero-DB; zero-network means the stubbed fetch is asserted never called.
5. **`DRY_RUN = True` first** on anything that writes; Marker Law (residue = 0) on anything touching real data — the RST DB is real data even in dev. S2 is the first slice that writes to it. `dbWorkmate_KT` is READ_ONLY and stays that way.
6. **Fact-check before build:** confirm columns / codes / flags against the schema CSVs and the DB. Never re-emit a file you have not read — CLI-written files, generated code, the oracle's strings and **column names** included. **A decision about data is blocked on reading the table, not on 🤙** — the pasted rows go in the spec before it is signed. Say "the API doesn't send it", never "it isn't there". **The database says what exists, the gateway export says what is used** — grep a candidate against the export before calling it load-bearing.
7. **Dialect-portable SQL** (COALESCE / CURRENT_TIMESTAMP / CONCAT / OFFSET-FETCH / `dbo.` / `-- PG-CONVERT:` tags). The CI gate greps the whole file — describe banned tokens, never spell them.
8. **Forensic diagnostics** on every request outcome: [F] what happened, [G] why blocked, [E] crash — one `diag.log()` seam, wired by `diag.configure()`. Assert **emission**, not the call.
9. **Check the box before the code.** On any "it's slow": free memory and the top-5 processes by working set first, verbatim. Healthy `/range` is 70–700 ms; over 2 s is the box (Landmines §F) — unless the box is clean, in which case it is open item 30 and the evidence is DMV wait types during a slow request, not another box check.
10. **Comms:** short, direct, NZ-casual. Console output pasted verbatim before proceeding — and wait for the prompt before pasting the next block. Shell blocks complete and copy-pasteable, starting with `cd C:\dev\workmate-saas…`; servers in their own windows via `Start-Process`; **both suites bare** (plain `uv run pytest`, plain `pnpm test`), read the count with your eyes, gate on `$LASTEXITCODE` — never on a `Select-String` whose pattern is a guess; one browser tab during a smoke; after every drop, `Test-Path` each target by exact name — the verification line is the evidence, not the copy's silence, and it is `Format-List`ed or in its own block or PowerShell drops its columns. 🤙 = go.
11. **Verify before you commit.** A gate you write and don't enforce is not a gate; a verification that returns nothing is a failure, not a pass. **Close every session with a raw log** and the doc updates it implies. Carry forward every open item you do not close. The next session applies that doc set first, then audits from the docs.

## 5. Environment snapshot (verified 2026-09-13)

| Thing | Value |
|-------|-------|
| Dev machine | Windows 11 x64, 32 GB, Windows PowerShell 5.1 in practice; execution policy `CurrentUser RemoteSigned`. A fresh window opens in `system32` |
| Dev DB | local SQL Server `AzztecDev` (Standard Developer Edition 64-bit 17.0.1000.7) → `dbWorkmate` restored from the **RST** backup, compat 170, at the instance default `…\MSSQL17.MSSQLSERVER\MSSQL\DATA\`; SQL login `svc_workmate` (`VIEW SERVER STATE`, not `VIEW SERVER PERFORMANCE STATE`); dev actor `WORKMATE_DEV_USER_ID=1` (SYS_USER). **`max server memory` = 8192 MB, applied 2026-09-13** via `sqlcmd -S localhost -E -C` under the Windows login (`AzztecDev\Azzte`, sysadmin) — `sqlcmd` needs `-C` for the self-signed cert; SSMS not needed |
| Dev DB — the KT copy | **`dbWorkmate_KT`** on the same instance: `KTSQL02`'s `dbWorkmate` (SQL Server 2022 16.0.4275, compat 100, created 2026-02-13; full backup 2026-09-13 00:32, 78.7 MB) restored 2026-09-13 `WITH MOVE` to the instance defaults, then **`SET READ_ONLY`**. Physical version 957 → 998 on the way in — **AzztecDev → KTSQL02 is never possible**. `svc_workmate` has **no user in it yet** (read-write flip, create, flip back — only when `parity_range.py` runs). Every comparison is three-part-name SQL and read-only; a cross-database batch starts with `SELECT DB_NAME()` (Landmines §B). The `.bak` lives at `C:\SQLBackups\` — the engine opens it as `NT Service\MSSQLSERVER`, not as you (error 2 = path, 5 = ACL) |
| Docker Desktop | **capped**: `.wslconfig` `[wsl2] memory=8GB swap=2GB` written 2026-09-13; down since; its first clean start under the cap closes open item 17 (it held 45 GB of the box on 2026-09-12 and starved SQL Server) |
| Live reference | Ignition gateway `MainSCADA_Timberlands` (KT) — the parity oracle. **Copy obtained** (item 26 reclassified): the database above plus the project export `MainSCADA_Timberlands_2026-09-10_1900.zip` (33 MB, on the box, not in PK; 1,986 views, 1,700 named queries, 382 scripts). `scripts/parity_range.py` is still unbuilt. KT's own `Diag_Log` holds the Ignition planner's `[F] range … rows=… labour=… workers=36 pinTable=True in 147 ms` lines — the oracle's real counts and timings |
| Backend | Python 3.13.15 (uv 0.12.12), FastAPI 0.141.x, SQLAlchemy 2.0.5x (sync Core), pyodbc 5.3 + ODBC Driver 18 |
| Frontend | node v24.19.0, pnpm 12.3.4 · `@tanstack/cli` 0.71.0 scaffold, `--router-only --toolchain eslint` · React 19.3.0, Router 1.170.35, Query 5.102.8, Vite 8.3.0, **TypeScript 6.0.3** (OD-28; TS 7.0.2 published, not taken), Vitest 5.0.0 + RTL 16.3.3 + jsdom 30.0.1, hey-api 0.99.0, **ESLint 10.10.0** + Prettier 3.9.6, zustand 5.0.15, tailwindcss 4.3.3, date-fns 4.4.0, zod 4.6.1 — no `pnpm add` in S1g (OD-31) |
| Target DB | PostgreSQL 18.6 (Docker on dev — see the Docker row) |
| Repo | `C:\dev\workmate-saas` — `backend/`, `web/`, `docs/`, `scripts/`, `.claude/`. HEAD **`c4e17f9`** (the KT delta; `23c90ea` before it is the five compiled docs from log 09-13 1.0.0; the docs commit for this set lands on top). Tags: **`s1g-readonly-1.1.1`** at `449f19d`, `s1f-grid-1.0.1` at `8f742b4`, `s1e-web-1.0.1` at `963fcca`, `s1d-diag-1.1.1` at `b1caa50` |
| Claude Code | 2.1.267 native, `C:\Users\Azzte\.local\bin\claude.exe` (added to PATH manually) |
| Ports | API 8000, **Vite 3000** (Node binds `localhost` to `::1` — port checks try both stacks), Postgres 5432, Adminer 8080 |
| Git author | `AzztecEnterprise <azztecdev@gmail.com>` |
| `/range` on RST | healthy singles 0.12–0.65 s; the standing week 2026-09-14..20 = 273 rows; June 2026-06-01..07-05 = 3221 rows; the August 42-day month = 3784; Mon 14 Sep 2026 = 106 PMs / 203.8 h; 363 workers = 179 internal + 184 contractors, 14 teams, 14 priority rows. **The same window alternating ~1.2 s / ~8–10 s on the 60 s poll with the box clean is open item 30**, not the box |
| KT numbers | 36 workers, 4 priority rows (**A/B/C/D** at `Sort_Sequence` 1–4, no ties, `#FF8000` on all four), 4 `WO_N_Plan` rows (all `Pinned='N'`); 280 tables / 24 views / 1099 procs against RST's 255 / 67 / 1121 |

**Mark-of-the-Web rule:** every Download card carries the zone tag. `Unblock-File` after each drop — and remember it is not a copy; `Test-Path` each target by exact filename, and read that line as the evidence (Ways of Working §2).

## 6. Picking up the build

1. Read `Azztec_SaaS_Raw_Log_2026-09-13_v1_1_0.md` — §7 is the open list (14 items), §8 next, §5 what the KT copy verified, §4 the eight mistakes. Log 1.0.0 §1–§6 still stand for the S1g record.
2. **The box first:** free memory + top-5 processes by working set, pasted. Docker should be down or capped (Landmines §F).
3. **Suites bare:** `cd C:\dev\workmate-saas\backend; uv run pytest; $LASTEXITCODE` → expect **125 passed** and `0`. `cd ..\web; pnpm test; $LASTEXITCODE` → expect **155 passed in 11 files** and `0`. Read the counts; never pipe them through a pattern you have not seen match. Anything else means the tree moved since this Index.
4. Backend in its own window: `Start-Process powershell -ArgumentList '-NoExit','-Command','cd C:\dev\workmate-saas\backend; uv run fastapi dev app/main.py'` → expect the boot lines (`[F] diag wired` first, no `[G] frontend not built` — `dist/` exists) and `/health` `frontend: "built"`. If `frontend: "missing"`, `pnpm --dir web build` first; `dist/` is gitignored. Vite, when needed, in a third window on `:3000`. One browser tab.
5. **The backend audit before any spec** — three small backend items, no frontend: **30** (the alternating `/range` latency; gather `sys.dm_exec_requests` wait types *during* a slow request first — `svc_workmate` can read them), **29** (`Priority.Colour` to the badge — evidenced on both databases now: RST fourteen rows with a varied `Colour`, KT four rows all `#FF8000` so the oracle colours from the letter class in CSS; the shape to sign is paint-from-payload where the colours vary, `.pri.A–D` where every row matches; `_PRIORITY_SQL` + `schemas.Priority` gain `colour`, regenerate the client, then a `DRY_RUN`-first `UPDATE dbo.Priority SET Colour` on the dev copy with the old values printed first; read `sql.py` 201–204 for the column names), **21** (`initialsOf` on parentheses — byte-1:1 with the oracle, so a departure needs an OD). 29 + 21 could be one backend slice with their tests.
6. **The uplift audit** (item 32) — read `Azztec_SaaS_KT_Schema_Delta_v1_0_0.md` in full; its §8 nine questions are the agenda, the sharp ones being `WO_N_Plan` on RST now (flips `pinTable` true, 2,364 PMs pin-movable — OD-1's intended end state), migration numbering against S3's 0002, and what fills `Diag_Log`'s NOT NULL columns. The migration is scripted from `dbWorkmate_KT`'s catalog at build time, never typed; `DRY_RUN` first.
7. Then the S2 audit proper (Port Spec §6). One query still outstanding, blocking nothing: the body of `GetWeekNoAndYear` from `dbWorkmate_KT.sys.sql_modules` (`sqlcmd -S localhost -E -C -y 0 -w 8000 -Q "…"` — no `-W`, no `-h`).

### 6.1 Signed, so nobody re-litigates

OD-1 and OD-6 (2026-09-10); OD-7…OD-20 (2026-09-11, S1a–S1d gates); OD-21…OD-25 (2026-09-11, S1e gate: toolchain, generator, 42-day cap, internal-by-default rail, the oracle's capacity bar); OD-26…OD-29 (2026-09-12, S1f gate: rail toggles + count line, the oracle's CSS ported under `.wm-planner`, TypeScript 6.x / ESLint 10, URL = `mode` + `anchor`); **OD-30…OD-34** (2026-09-13, S1g gate: cancellation aborts in the browser and runs to completion on the server; no shadcn in a port; hover parity; chrome says only what is true). **OD-32 is signed-then-withdrawn** — priority colour by rank was falsified by `dbo.Priority` the same day; the rank classes render colourless, still tested; the replacement is item 29, a backend slice. **Nothing was signed in the KT-database session** — its output is audit input (log 1.1.0 §1). One-liners and gates in Port Spec 1.0.3 §9; terms in §1 of the log named there.

### 6.2 Project knowledge vs this inventory (checked 2026-09-13, second session)

**Clean.** The five compiled docs 1.4.0 §6.2 said to remove (Index 1.3.0, Landmines 1.3.0, Ways of Working 1.3.0, Architecture 1.0.2, Port Spec 1.0.1) are gone from the project files. Present: the delta report, log 2026-09-13 1.1.0, the four `docs/reference/` files (§3.7), every S1g card at its shipped version, both S1g-era spec and log.

**After this docs commit, remove by hand:** Index 1.4.0, Landmines 1.4.0, Ways of Working 1.3.1, Architecture 1.0.3, Port Spec 1.0.2. Raw logs are the exception — every version stays.

## 7. Changelog

- 1.5.0 (2026-09-13) Reissued after the KT-database session (log 2026-09-13 1.1.0 §6). §1 state: HEAD `c4e17f9` with both docs commits, suites re-verified bare, `dbWorkmate_KT` on the box and the delta written, nothing signed; next = backend audit → uplift audit (32) → S2. §2 read order leads with log 1.1.0 and the 1.5.0 / 1.3.2 / 1.5.0 / 1.0.4 / 1.0.3 set; the KT delta enters at 8, before anything touching the database. §3.1 gains the delta report and the fifth-session note on the Install doc; §3.3 the new log; §3.5 the bare re-verification; §3.6 fifth session on Scaffold_Repo; §3.7 the four `docs/reference/` files, the export-on-the-box rule and the two-oracles line. §4: Downloads twice (3), `dbWorkmate_KT` read-only (5), the database-says/export-says rule (6), wait-for-the-prompt, bare suites, `$LASTEXITCODE` and the `Format-List` clause (10), verify-before-commit (11). §5: RST compat 170, the new `dbWorkmate_KT` row, the Live reference row rewritten as obtained, HEAD `c4e17f9`, the KT numbers row. §6 pick-up: 14 open items, bare suites with `$LASTEXITCODE`, the item-29 evidence on both sides, the uplift audit as step 6, the outstanding `GetWeekNoAndYear` query. §6.1 notes nothing signed in session two. §6.2 rewritten from the actual project files: clean, five compiled docs to remove after this commit.
- 1.4.0 (2026-09-13) Reissued after S1g (log 2026-09-13 1.0.0 §7). §1 state: the read-only planner complete, HEAD `0cb41b8`, tag `s1g-readonly-1.1.1` at `449f19d`, 155 + 125, OD-32 withdrawn, caps applied, the backend audit named as next. §2 read order leads with log 09-13 and the 1.4.0 / 1.3.1 / 1.4.0 / 1.0.3 / 1.0.2 set; docs-not-log once the set is applied. §3.1 the new versions and the Install doc's `sqlcmd` correction; §3.2 the S1g spec with its in-log corrections; §3.3 the new log; §3.4 the `sql.py` column-name pointer; §3.4b the twelve S1g versions and three new components, `router.tsx` deleted, `index.tsx` not in PK, no shadcn files; §3.5 the S1g test versions (two shipped at 1.0.1 against a 1.0.0 spec) and 155 in 11; §3.6 the `addopts` and Docker notes; §3.7 the Forensics pack recorded as set aside (item 31). §4: withdrawn IDs kept (2), Downloads rule (3), S2 writes (5), column names + table-before-🤙 + "the API doesn't send it" (6), the item-30 caveat (9), plain `uv run pytest` / one tab / the verification line (10), doc set first (11). §5 re-verified from the S1g session: SQL cap applied, `dbWorkmate` path, `sqlcmd -E -C`, Docker capped and down, HEAD and tags, the `/range` numbers row. §6 pick-up: `Select-String`, both counts, one tab, the backend audit order with what each item needs. §6.1 extended to OD-34 with the withdrawal. §6.2 rewritten from the actual project files: clean, five compiled docs to remove after this commit.
- 1.3.0 (2026-09-13) Reissued after S1f (log 2026-09-12 1.1.0 §7). §1 state: `PlannerGrid` read-only shipped, HEAD `8f742b4`, tag `s1f-grid-1.0.1`, 96 + 125. §2 read order leads with log 1.1.0 and the 1.3.0 / 1.0.2 / 1.0.1 compiled set. §3: S1f spec, the new log, the fourteen S1f frontend files (3.4b) and six test files (3.5), `router.tsx` marked dead, Scaffold_Repo 1.0.1 now in PK, `Workboard_v1_0_0.html` recorded in §3.7, the handover brief explained. §4 gains the memory-first rule and the shell/window discipline. §5 re-verified from the S1f session: SQL Server edition and the uncapped memory, the Docker row, ESLint 10, TypeScript 6 / TS 7, Vite on 3000, the S1f dependency versions. §6 pick-up steps: box first, `-Last 6`, servers via `Start-Process`, both suite counts, the S1g audit order. §6.1 extended to OD-29. §6.2 rewritten from the actual project files: the eight gaps are filled, four superseded files named for removal.
- 1.2.0 (2026-09-12) Reissued after S1e. §1 state: `web/` exists, tag `s1e-web-1.0.1`. Read order now leads with the 2026-09-12 log. §3 gains the frontend code table (3.4b), the two Vitest files, the S1e spec, the new log, and the scaffold-web script; Scaffold_Repo's on-box 1.0.1 flagged as not uploaded. §5 frontend row filled in from the box. §6 pick-up steps cover both suites and the `dist/`-present boot; §6.1 replaced by the five signed decisions; §6.2 names the project-knowledge gaps.
- 1.1.0 (2026-09-11) Reissued after S1d. Read order puts the newest raw log second and states that logs outrank compiled docs on current state. §3 replaced with the full live inventory — backend modules, tests, chunk specs, logs — so a missing file in project knowledge is visible at a glance. §4 absorbs the scope-cut, tag-what-shipped, PK-marking, read-before-re-emitting and emission-testing rules. §5 re-verified against the box. §6 replaces the completed first-session checklist with how to pick the build up, and names the one unsigned decision blocking S1e.
- 1.0.0 (2026-09-10) Initial. Built from the Workmate Dev project state as of 2026-09-10 (Planner 1.3.1 / API 1.8.3 / UI 1.7.1 live at KT).
