# Azztec SaaS — Planner Port Spec (P-PLN1-SaaS)

**File:** Azztec_SaaS_Planner_Port_Spec_v1_0_1.md · **Version:** 1.0.1 · **Date:** 2026-09-13 · **Author:** Adriaan
**Status:** Active — S1a…S1f shipped; S1g next. OD-1, OD-6…OD-29 signed (§9); OD-2…OD-5 open. Read the newest raw log for the box; this file is the design.
**Source of truth (in project knowledge):** `workmate_planner_code_v1_3_1.py`, `workmate_planner_api_code_v1_8_3.py`,
`workmate_planner_ai_code_v1_1_0.py`, `workmate_planner_chat_code_v1_2_1.py`, `workmate_planner_test_code_v1_0_0.py`,
`PlannerCalendar_v1_3_0_view.json`, `Planner_v1_8_1.html` (+ `wm-ui.css`/`wm-ui.js`) — the UI oracle; line numbers in the chunk specs refer to it, `Workmate_Planner_Assistant_Prompts_v1_0_0.md`
**Legacy behaviour authority:** `Workmate_NET_Manual` Labour Resource module (pp.157–168) via `Workmate_NET_Logic_Reference_v1_1.md`

---

## 1. Purpose

Port the live KT Planner to FastAPI + React **behaviour-for-behaviour**, running first against the RST data, keeping the
JSON contract byte-compatible so (a) the Ignition planner is the parity oracle and (b) `Planner_v1_8_1.html` can be pointed at
the new API as a smoke test — which is why the `/range` envelope keeps `ok`, `apiVersion`, `actor`, `ms` (OD-14). Genuine
Ignition parity (`scripts/parity_range.py`) is still blocked on a KT dev copy; what S1a–S1f claim is wire-level contract
correctness and screenshot-level behaviour parity on RST. The planner was deliberately built for this: everything the UI shows is assembled in
`workmate.planner` from pure functions over plain dicts; `planner_api.route()` is a pure request→response function;
`planner_chat.parse()` is the LLM seam.

## 2. Ignition → SaaS mapping

| Ignition piece | SaaS home | Port type |
|----------------|-----------|-----------|
| `workmate.planner` pure rules (`category`, `engineOwned`, `hoursFor`, `assignedFor`, `classifyTeams`, `buildWorkers`, `initialsOf`, `workerLoad`, `capacityByWeek`, `workerWeeks`, `moveRules`, `estimateRules`, `labourRules`, `civilDays`, `weekStart`, `parseIso`, `iso`, `timeOf`) | `backend/app/planner/rules.py` | **1:1**, same names, same dict keys, Python 3 |
| `workmate.planner` SQL (`_woSql`, `_LABOUR_SQL`, `_WORKER_SQL`, `_PRIORITY_SQL`, `_loadSql`, pin selects) | `backend/app/planner/sql.py` | rewrite to dialect-portable form (COALESCE, CURRENT_TIMESTAMP, tags) — same columns, same aliases |
| `fetchWOs / fetchLabour / labourRows / fetchSkillRows / fetchPriorities / workers / rangeData / loadWO / hoursUomId / pinTableExists` | `backend/app/planner/repo.py` (+ `service.range_data`) | same output dicts; `system.db` → `db.rows()`. `loadWO` and `movePreview` are S2 (OD-13): they return raw `datetime`s for the writer, no consumer in a read-only slice. `UOM_MODAL` and `_PRIORITY_SQL` carry a `, UOM_Id` / `, Priority_Id` tie-break the source lacked (OD-11); `sql.py` preserves `ORDER BY Sort_Sequence, Priority_Id` |
| `moveWO / undoMove / setEstimate / unpin / addLabour / removeLabour / setCapacity / movePreview` | `backend/app/planner/service.py` | same signatures in snake_case (`move_wo(wo_id, to_iso, user_id, expect_start_iso=None, confirm=False, dry_run=True, conn=None)`), same result dicts, one `engine.begin()` per call |
| `pm_engine.weekNo` (`_netWeekNoAndYear`) | `backend/app/core/weekno.py` | 1:1 (.NET algorithm) with unit tests against known KT values |
| `workmate.planner_api.route()` + WebDev shims | `backend/app/planner/router.py` (`APIRouter(prefix="/api/v1/planner")`) | routes keep names and bodies; sid/tok gate → `deps.get_current_actor()` (OD-12: the dev user id when `WORKMATE_ENV=dev`, 401 otherwise — one seam, swapped for the JWT dependency in S2); `/ui`, `/lib/*` → gone (`app.frontend()`); `/open` → client-side navigation; errors are the flat OD-15 body; `'bad window'` string-matching → `service.WindowError` caught by type (OD-16) |
| `workmate.planner_ai` | `backend/app/planner_ai/` (S5) | 1:1 pure; `fetchHistory` → repo |
| `workmate.planner_chat` | `backend/app/planner_chat/` (S5b) | 1:1; session context dict keyed by JWT `sub` |
| `workmate.planner_test` t_* | `backend/tests/test_planner_*.py` | one pytest per t_* |
| `PlannerCalendar_v1_3_0` host view (iframe, sid/uid/tok, `wm-plan-open`) | none — the SPA is the host | drop |
| `Planner_v1_8_1.html` single-file UI | `web/src/features/planner/*` (+ `routes/planner.tsx`, `lib/dates.ts`) | re-implement in React; behaviour parity, not pixel parity — but the oracle's CSS ports as-is under `.wm-planner` (OD-27) so a screenshot can be held next to the Ignition planner. Its pure rendering rules port 1:1 into `features/planner/rules.ts` (camelCase names kept, no `Date`, no DOM); `windowFor` / `navAnchor` into `lib/dates.ts`. S1f draws week / twoweek / month; S1g the rest of read-only (§7) |
| Diag wiring (`sendMessage 'debug-log'` + `dbo.Diag_Log`) | `app/core/diag.py` + request-id middleware, wired by `diag.configure()` from `create_app()` (OD-18) | keep tags [F]/[G]/[E] and message texts; assert emission with `capfd`, never the call |
| `System_Configuration PLANNER_*` switches | same table via `config_value(key, default)` — **table with code defaults, no seed, nothing written to RST** (OD-7; RST has no `PLANNER_*` rows) | keep the four operational knobs: `PLANNER_AUTOPILOT`, `PLANNER_AUTOPILOT_MAX_MOVES`, `PLANNER_AUTOPILOT_MAX_WEEKS`, `PLANNER_NIGHTLY_WEEKS`; `PLANNER_AUTOPILOT_USER_ID` stays in the table and is decided in S5; **`PLANNER_DEV_USER_ID` is not a knob — it moved to `.env` as `WORKMATE_DEV_USER_ID`** (OD-7, 2026-09-11); retire `PLANNER_SID_GATE`, `PLANNER_TOKEN_SECRET`, `PLANNER_UI_DIR` (proposals move to a table, OD-4) |

## 3. The JSON contract (unchanged keys)

`GET /api/v1/planner/range?from=YYYY-MM-DD&to=YYYY-MM-DD` → `RangeData` — the Ignition `rangeData` keys below **plus the flat envelope** (OD-14, 2026-09-11): `ok: true`, `apiVersion` (`router.__version__`), `actor`, `ms`. `gate` is dropped (retired with the sid gate). `Planner_v1_8_1.html` reads all four. Errors are the flat app-wide body `{ok:false, code, message, rid}` (OD-15); a bad window is `service.WindowError` with `code='BAD_WINDOW'`, caught by type in the router → 400 (OD-16). The `from` key needs `Field(alias="from")` on the model **and** `Query(alias="from")` on the parameter, and the generated TS client must emit `from=` on the wire — three places, each pinned by a test (Landmines §A/§C).

| Key | Type | Notes |
|-----|------|-------|
| `ok`, `apiVersion`, `actor`, `ms` | bool, str, int, int | the envelope (OD-14) — not Ignition `rangeData` keys, but the same wire the oracle UI reads |
| `from`, `to`, `today` | `YYYY-MM-DD` | window inclusive; 400 `BAD_WINDOW` on bad window or > 400 days; `today` resolved in `WORKMATE_TZ` (OD-6). The UI never asks for more than 42 inclusive days (OD-23) — the 400-day ceiling is an API capability, not a window the UI may request |
| `wos[]` | WO dict | `id, sid, title, status, statusTitle, type, cat (DONE/PM/REQ/WO), start, startTime (HH:mm or ''), end, days, weekNo, prog, priId, pri, estimate, resp, asset, assetTitle, loc, locTitle, hasPO, engineOwned, pinned, pinnedOn, engineDate, locked, movable, hrs, hrsSrc ('labour'/'estimate'/''), assigned[userId]` |
| `labour[]` | labour row dict | `resId, woId, userId, hours, rate, note, date, skillId, skillTitle, uomId` |
| `workers[]` | worker dict | `id, sid, name, initials, skills[{id,title,sysId,hrsPerWeek,supplierId}], hrsPerWeek, teamId, team, internal` — internal first, then by name |
| `teams[]` | team dict | `id, short, name, internal, users` — internal first |
| `priorities[]` | `{id, short, title}` | active, by `Sort_Sequence` |
| `colours` | `{DONE:'#81C784', PM:'#4DD0E1', REQ:'#F48FB1', WO:'#FFC65C'}` | shipped so UI and Home page agree |
| `weeks[]` | `{weekStart, planned, unknown, count, capacity, pct}` | Mon–Sun weeks touching the window; capacity = internal workers' `hrsPerWeek` |
| `load` | `{"<userId>": hours}` | key `"0"` = unassigned |
| `counts` | `{wo, pm, done, total}` | the parity numbers |
| `pinTable` | bool | `WO_N_Plan` exists |
| `workerWeeks` | `{"<userId>": [{weekStart, planned, capacity, pct, flag (over/ok/under/empty)}]}` | flag thresholds: over >100, ok 80–100, under 1–79 with capacity, empty 0. On RST `pct` runs to four figures (placeholder `Hrs_Per_Week`, Landmines §E) — rendered as the oracle does, `width: min(100, pct)%` with the real number in the label (OD-25). `pct` uses Python 3 half-to-even rounding: ≤1 off Ignition at exact .5, documented not patched (OD-8) |
| `uomHours` | int | the `LRStd` UOM id — resolved at runtime (RST: 12 LABOUR HOURS); assert the resolution, not the number |
| `libVersion` | str | `rules.__version__` — a new lineage starting at 1.0.0 with `PORTED_FROM = "workmate.planner 1.3.1"` (OD-10); the S6 `t_versions` port asserts `PORTED_FROM`, not `>= '1.3.1'` |

Write results keep the Ignition dict shapes (`{ok, code, message, sid, preview?, undo?, …}`).

## 4. Routes

| Ignition (WebDev `/planner/...`) | SaaS | Body / query | Result codes |
|----------------------------------|------|--------------|--------------|
| `GET /health` | `GET /api/v1/health` (app-wide) | — | `versions` read from each module's `__version__` (never literals); `db: ok`; `frontend: built \| missing`; `diagWired` (is the handler attached) and `diag` (persist mode) as two facts (OD-20) |
| `GET /range` | `GET /api/v1/planner/range` | `from, to` | 200 RangeData + envelope (§3); 400 `BAD_WINDOW` (OD-16) |
| `GET /_echo` | `GET /api/v1/_diag/self-test` | — | actor, diag persist path (no `gate`) |
| `POST /open` | client-side `navigate('/workorders/$id')` | — | — |
| `POST /move` | `POST /api/v1/planner/move` | `{woId, toIso, expectStartIso, confirm}` | 200 `{ok:true, …undo}` · 200 `{ok:false, code:'CONFIRM', preview}` · 409 `STALE` · 422 `LOCKED_STATUS/ENGINE_OWNED/NO_START/BAD_DATE/NO_CHANGE` · 401/403 `NO_IDENTITY` |
| `POST /undo` | `POST /api/v1/planner/undo` | `{woId, toIso, expectStartIso}` | as move, confirm implied |
| `POST /estimate` | `POST /api/v1/planner/estimate` | `{woId, hours}` | 200 · 422 `LOCKED_STATUS/BAD_HOURS/NO_DETAILS` |
| `POST /unpin` | `POST /api/v1/planner/unpin` | `{woId}` | 200 · 422 |
| `POST /labour` | `POST /api/v1/planner/labour` | `{woId, userId, skillId, hours, resDate, note}` | 200 · 422 `LOCKED_STATUS/NO_USER/USER_INACTIVE/NO_SKILL/BAD_HOURS/BAD_DATE` |
| `POST /labour/remove` | `POST /api/v1/planner/labour/remove` | `{woId, resId}` | 200 (returns the row for undo) |
| `POST /capacity` | `POST /api/v1/planner/capacity` | `{userId, sysSkillId, hrsPerWeek}` | 200 · 422 (0..168) |
| `GET /preview` | `GET /api/v1/planner/preview` | `woId, to` | movePreview — **S2** with `loadWO` (OD-13), not S1 |
| `GET /suggest` | `GET /api/v1/planner/suggest` | `from, weeks, lookahead, capacity, woId` | S5 |
| `GET /history` | `GET /api/v1/planner/history` | `woId` | S5 |
| `GET/POST /settings` | `GET/POST /api/v1/planner/settings` | `{key, value}` (whitelist) | S5 |
| `POST /nightly` | `POST /api/v1/planner/nightly` + CLI `workmate planner nightly` | `{weeks, apply}` | S5 |
| `POST /chat` | `POST /api/v1/planner/chat` | `{text, woId, reset}` | S5b |
| `POST /_diag` | `POST /api/v1/_diag/client` | `{level, message, detail}` | browser errors — not built yet; deferred past S1g with the `?debug=1` trail and localStorage prefs |

Actor: `deps.get_current_actor()` (OD-12) returns `WORKMATE_DEV_USER_ID` from `.env` when `WORKMATE_ENV=dev` (dev actor `1` = `SYS_USER`, deliberately not a real person) and 401 otherwise. Every write needs `User_Id > 0`; the JWT `sub` (D-5) replaces the seam in S2 — `app/auth/` still appears in no slice (§6). The diag middleware is scoped to `/api` (Landmines §A).

## 5. Rules that must survive untouched

- `moveRules`: refuse `LOCKED_STATUS` (C/D), `ENGINE_OWNED` (PM the engine owns, no pin table), `NO_START`, `BAD_DATE`, `NO_CHANGE`; confirm reasons `PAST`, `ACTIVE` (V), `SPAN` (multi-day), `LABOUR_MULTI`; `willPin` / `willUnpin` / `pinnedAfter`.
- `moveWO` transaction: header start/end shifted by the civil-day delta (time of day kept, NULL end stays NULL), `Week_No = weekNo(newStart)`, subtasks shifted per row in collision-safe order (descending dates when delta > 0), `WO_N_Resource.Res_Date` shifted, `WO_Event_History` 'Rescheduled' + per-field 'Update' rows in the clsSimpleComparer format, `Source_Form='Planner'`; `expectStartIso` optimistic lock; every write returns a dict, never raises past the service boundary; `dry_run=True` default.
- `estimateRules`: 0 ≤ h ≤ 1000, needs a `WO_N_Details` row.
- `labourRules`: active user, ≥1 active skill row, 0 < h ≤ 500, `Res_Date` defaults to WO start; `Res_Id = MAX+1` in-tx; UOM = `LRStd` row; `Supplier_Id` from the skill row.
- `setCapacity`: 0..168 on ONE `User_Skill` row (`Sys_User_Skill_Id`).
- `civilDays`: pure calendar arithmetic; DST test 17↔29 Sep 2026 = ±12.
- Autopilot guardrails (S5): no PMs, priority A/B only, ≤ `PLANNER_AUTOPILOT_MAX_WEEKS` pull, ≤ `PLANNER_AUTOPILOT_MAX_MOVES`/night, never into the past, every move carries its undo. **RST has no A/B priorities** — its domain is `P1`…`P6`/`N/A` (Landmines §E); the S5 audit maps the guardrail onto that before it runs on RST.

**Deliberate deviations, all signed and documented in-file** (the parity tests map around them): `round()` half-to-even (OD-8); `labourRules` returns `resDate` as a `datetime.date`, no ISO twin (OD-9); `UOM_MODAL` / `_PRIORITY_SQL` tie-breaks (OD-11); `WindowError` by type instead of string matching (OD-16); `hoursFor`/`assignedFor` fed a pre-indexed subset from the service instead of scanning the full list per call — provably identical output, `rules.py` byte-1:1, equivalence pinned by a test (Landmines §D); `'%s' %` kept behind a file-wide `# ruff: noqa: UP031`. One oracle quirk kept on purpose: `chipTitle` on a closed WO carries the PM "engine owned" line because `locked` covers C/D — parity, pinned by `rules.test.ts`.

## 6. Slices

| Slice | Deliverables | Smoke (paste output) |
|-------|--------------|----------------------|
| **S0 scaffold** — done 2026-09-10 | repo, `pyproject`, `main.py`, `config.py`, `db.py`, `diag.py`, `test_smoke.py`; RST restored; probes 14/14. Migrations 0001–0004 and the `web/` scaffold did **not** ship here (S0 lost `web/` to a CLI flag that had stopped existing — `web/` is S1e) | `uv run pytest -q` green; `/api/v1/health` → `{app, db:"ok", …}`; RST probes §8 of the Data Layer doc pasted |
| **S1a rules** — done 2026-09-11 | `rules.py` 1.0.0 (pure set, `PORTED_FROM`, OD-10) + `test_planner_rules.py` | zero-DB pytest green — `t_rules`/`t_moverules`/`t_dst`/`t_workers` cases; DST 17↔29 = ±12 |
| **S1b sql + repo** — done 2026-09-11 | `sql.py` (dialect-portable, PG-CONVERT tags, OD-11 tie-breaks), `repo.py` + `test_planner_repo.py` (rolled-back connection) | 33 tests on RST, zero skips; `LRStd` → 12 |
| **S1c service + schemas + deps + router** — done 2026-09-11, tag `s1c-api-1.0.1` | `service.range_data` (+ `WindowError`, OD-16), `schemas.py` (`RangeData` + envelope, OD-14/15), `deps.get_current_actor` (OD-12), `router.py` `/range` + `test_planner_api.py` | `/range` on the standing week 2026-09-14..20 → `273/273 PM`; route matrix incl. 405 |
| **S1d diagnostics** — done 2026-09-11, tag `s1d-diag-1.1.1` | `diag.configure()` wiring (OD-18), conditional `app.frontend()` mount (OD-19), `/health` `diagWired` (OD-20), `test_diag_wiring.py` (`capfd`), `test_openapi_contract.py` (the `from` alias guard) | `[F] diag wired` first boot line; 125 backend green |
| **S1e web scaffold + client** — done 2026-09-12, tag `s1e-web-1.0.1` | `web/` via `scripts/scaffold-web.ps1` (OD-21), generated hey-api client from the committed `openapi_0_3_0.json` (OD-22), `lib/dates.ts`, `usePlannerRange` with the 42-day cap (OD-23) | 15 frontend green; `pnpm build` → `dist/`; backend re-run with `dist/` present, `/health` `frontend: "built"` |
| **S1f PlannerGrid read-only** — done 2026-09-12, tag `s1f-grid-1.0.1` | `dates.ts` 1.1.0 (`windowFor`/`navAnchor`), `rules.ts`, `store.ts`, `planner.css` (OD-27), `WOCard`, `DayCell`, `CapacityBar` + `WeekStrip` (OD-25), `PlannerGrid`, `PlannerHeader` (6M disabled), `WorkerPanel` (OD-24/26), `PlannerView`, `routes/planner.tsx` (OD-29), `main.tsx`; ESLint 10 (OD-28); no shadcn, no dnd | week / twoweek / month on real RST data, screenshots held against the Ignition planner; the OD-1 tooltip byte for byte; deep link through `app.frontend()`; 96 frontend + 125 backend green |
| **S1g rest of read-only** — next; opens with an audit | Selected WO card (inline, OD-5: Status · Start · End · Priority · Asset · Location · Hours · Responsible · Planned labour · Open in WO Maintenance · Clear); filters row (team / worker / priority / unassigned / search — brings `capacityWorkers`'s precedence branches and `.wk.on` click-to-filter); day dialog (`showDay`) — **shadcn/ui arrives with it**, by hand; keyboard `← → T`; more on the hover; delete `router.tsx` | audit first line: request concurrency/cancellation (open item 18); the two memory caps before the smoke (Landmines §F); the priority-colour question as an OD (item 19); new tests follow the S1f harness pattern |
| **S2 move / undo / estimate** | `service.move_wo/undo_move/set_estimate`, `loadWO` + `movePreview` + `GET /preview` (OD-13), weekno port, router writes, `@dnd-kit` installed here, confirm dialog, optimistic drag with rollback, undo toast; the actor seam swapped for the JWT dependency (OD-12) | DST 17↔29 test; `STALE` round-trip with two tabs; `[F] move …` rows in Diag_Log and `WO_Event_History` rows in the clsSimpleComparer format; `dry_run=True` first — RST is real data |
| **S3 pins** | `0002_wo_n_plan` migration, pin-aware reads, `unpin` | move a PM → pinned; move back → unpinned (OD-1 decides RST semantics) |
| **S4 labour + capacity** | `add_labour/remove_labour/set_capacity`, labour popup, worker weeks flags | greaser 20 h/week scenario from KT reproduced on RST data |
| **S5 planner_ai** | port `planner_ai` pure + history repo; `/suggest`, `/history`, `/settings`, `/nightly`; CLI `workmate planner nightly`; Task Scheduler job | `planHorizon` on RST returns needs-estimate list + pull-forward plan; nightly writes a proposal row |
| **S5b chat** | `planner_chat.parse()` port + `/chat`; React chat panel; the prompts doc satisfied | every prompt in `Workmate_Planner_Assistant_Prompts_v1_0_0.md` answers as before |
| **S6 parity pack** | every `planner_test.t_*` as pytest (`t_versions` asserts `PORTED_FROM`, OD-10); Playwright drag/drop smoke; CI green; `scripts/parity_range.py` against the KT copy once it exists | `t_versions t_rules t_workers t_moverules t_dst t_chat_parse t_ai_pure t_range t_api_routes t_http t_ai_live t_chat_live t_rb_move t_rb_pin t_rb_labour` all PASS |
| **S7 serve** | `app.frontend()` with the built SPA (mount exists since S1d/S1e; the `/api/` html-fallback that logs a miss as `[F] 200` is fixed here), reverse proxy, service install, nightly job | one URL, login, planner loads over LAN |

Two things this table still does not place, deliberately: **`app/auth/` (D-5)** — the S1c actor stub is the interim (OD-12) and assigning auth a slice is an audit decision, not a doc edit; and the **six-month mode** — the oracle's fourth window needs an API summary shape (`weeks` + `workerWeeks`, no `wos`/`labour`) that is unsigned, so 6M stays a disabled button with a tooltip (open item 4).

## 7. React UI plan (S1–S4)

- **Route** `web/src/routes/planner.tsx` — a thin URL wrapper that exports `Route` and nothing else (anything more defeats code-splitting). Search params are `mode` (`week | twoweek | month`, default `month`) and `anchor` (yyyy-MM-dd, default today), validated by a plain `validateSearch` on `parseIso` (OD-29). `from`/`to` never appear in the URL — `windowFor(mode, anchor)` derives them, which is what keeps every request inside OD-23. The route renders `PlannerView` with mode/anchor as props.
- **Feature folder** `features/planner/` — **S1f, shipped:** `rules.ts` (the oracle's pure rendering rules — `visibleWos`, `capacityWorkers`, `railRows`, `chipTitle`, `fmtH`, `fmtLong`, `barClass`, `pctOf`, `weeksIn` … — camelCase kept, no `Date`, no DOM); `store.ts` (Zustand: cats, selected, railOpen, contractors, loadedOnly — not persisted); `planner.css` (the oracle's grid / chip / strip / bar / rail CSS, same class names, scoped under `.wm-planner`, `.chip{flex:none}` added — OD-27); `WOCard` (`div.chip.cat-<cat>[.locked][.mv][.sel]`, `.pri` badge, `.sid`, `.hrs[.unk]`, `.who`, pin/lock inline SVGs; click → select); `DayCell` (`+N more` cap, scrolling list); `CapacityBar` + `WeekStrip` (OD-25 — `width: min(100, pct)%`, real pct in the label); `PlannerGrid` (Mon–Sun columns, dow row, out-of-month cells dashed, today highlighted); `PlannerHeader` (`Week / 2W / Month` + **6M disabled with a tooltip**, `‹ Today ›`, cats `All WO PM REQ Done`, totals `wo WO | pm PM | done done`, rail toggle); `WorkerPanel` (the OD-24/OD-26 rail: internal by default, contractors off, loaded-only on, the count line `46 of 179 internal · 184 contractors hidden`, per-week bars from `workerWeeks`, `n over · n under` flags); `PlannerView` (the whole view, props-driven — the wire test needs no router); `range.fixture.ts` (2 WO / 2 PM, worker 692 at 1000 %).
- **S1g:** `SelectedWOCard` — inline per OD-5, the Ignition screenshot is the reference: Status · Start · End · Priority · Asset · Location · Hours · Responsible · Planned labour · Open in WO Maintenance · Clear; the filters row (team / worker / priority / unassigned / search, `capacityWorkers`'s selected-worker > team precedence, `.wk.on` click-to-filter); the day dialog (`showDay`) — the first shadcn primitive, installed by hand with it; keyboard `← → T`; the hover measured against the oracle's `showDay` / `renderSelected`, not invented; a `/planner` link on the welcome page; `router.tsx` deleted.
- **S2:** `DayCell` droppable (`id = ISO date`), `WOCard` draggable `wo-<id>`, `ConfirmMoveDialog` (preview reasons), `UndoToast`, mutations `useMoveWO`, `useEstimate`, … with optimistic cache edits and rollback on `ok:false`/error. **S4:** labour rows, estimate edit and unpin on the selected card; capacity edit on the rail row.
- **Data:** `usePlannerRange(from,to)` TanStack Query via the generated `getRangeApiV1PlannerRangeGetOptions` (its key carries the params), refuses > 42 inclusive days before fetching (OD-23), `staleTime 30 s`, `refetchInterval 60 s`, `refetchIntervalInBackground: false` (the hidden-tab pause is untested — open item 24). The no-data state renders cleanly (red banner, empty cells, `0 / ? h`). **Open:** nothing cancels an in-flight `/range` on navigation — signal through hey-api, a debounce, or pool sizing; first line of the S1g audit (open item 18).
- **State:** URL = `mode` + `anchor` only; Zustand = cats, selected, railOpen, contractors, loadedOnly, not persisted (OD-29). This replaces 1.0.0's `{view, anchorDate, selectedWoId, filters}` store and the `from/to/view` URL — `from`/`to` in a URL could name a window outside the cap. Filters join the store in S1g.
- **Dates:** `lib/dates.ts` 1.1.0 — the only module that touches `Date`: `civilDays`, `weekStart`, `parseIso`, `iso`, `addDays` twins on `date-fns` (`differenceInCalendarDays`, `startOfWeek({weekStartsOn:1})`), plus `Mode`/`MODES`/`isMode`, `Window`/`windowFor`, `navAnchor`, `todayIso`, `dowOf`, `daysInMonthOf`, `monthStart`, `isIso`. Strings are parity surface: `fmtLong` builds `Mon`, not `Monday` — read the oracle line before pinning it.
- **Drag/drop (S2):** `@dnd-kit/core` — `DndContext` + `PointerSensor {distance: 6}` + `pointerWithin`; `onDragEnd` → `moveWO(woId, overId, expectStartIso=wo.start)`; `CONFIRM` opens the dialog; `STALE` invalidates and toasts. Not installed until then.
- **Diag:** `window.onerror` → `POST /api/v1/_diag/client` — deferred; the route does not exist yet.
- **Test harness facts** (S1f, every new component test follows them): `vitest.config.ts` has no `setupFiles` and no `globals`, so each test calls `cleanup()` in `afterEach`; no jest-dom — assert on `className` / `style.width` / `textContent`; component tests are zero-network by import graph and fed `range.fixture.ts`; `PlannerView.test.tsx` is the one file that stubs `fetch` and it asserts the request count and the URL (`from=…&to=…`, never `from_`).

## 8. Tests (pair rule)

- `test_planner_rules.py` (S1a): the `t_rules`, `t_moverules`, `t_dst`, `t_workers` cases as parametrised pytest — **zero DB, and actually zero DB** (check the dependency graph, not just the assertion); `test_od8_rounding_documented` pins the half-to-even difference.
- `test_weekno.py` (S2): known KT `Week_No` values (e.g. 2026-09-14 → 2026.38 — confirm against the KT DB before pinning).
- `test_planner_repo.py` (S1b): rolled-back connection fixture; `range_data` on a fixed RST window; `move_wo(dry_run=True)` plan shape arrives in S2.
- `test_planner_api.py` (S1c): `TestClient` with **`get_current_actor`** overridden (the dependency is `get_current_actor`, not `get_current_user`); route matrix from §4 (method-not-allowed → 405, codes); `from=` on the wire.
- `test_diag_wiring.py` (S1d): emission asserted with `capfd` at the stream — never the return value of `diag.log()`, never `caplog`; the handler tested by name. `test_openapi_contract.py` (S1d): the published schema carries `from`, not `from_`. `test_smoke.py`: `/health` versions equal the modules' own constants; `test_root_matches_the_frontend_state` survives the `dist/` flip.
- `web/src/lib/dates.test.ts` (16), `web/src/features/planner/rules.test.ts` (32), `usePlannerRange.test.tsx` (8), `WOCard.test.tsx` (8), `CapacityBar.test.tsx` (8), `WorkerPanel.test.tsx` (8), `PlannerGrid.test.tsx` (11), `PlannerView.test.tsx` (5) — 96 in 8 files as counted 2026-09-12; **count from the run**, never from a doc. Every component test: `cleanup()` in `afterEach`, no jest-dom (§7).
- `web/e2e/planner.spec.ts` (S6): drag a WO one day forward, confirm dialog path, undo.

## 9. Open decisions

The six raised at 1.0.0, with status. Terms of every signed decision are in the dated raw logs (§1 of each); the one-liners here are so nobody re-litigates.

| ID | Question | Decision / proposal | Status |
|----|----------|---------------------|--------|
| **OD-1** | RST has no PM engine and no `WO_N_Plan`. What is `engineOwned()` there? | Ports 1:1, no RST branch. Without the pin table every engine-owned PM is `locked: True, movable: False` — 2,364 on RST. Migration 0002 on RST in S3 makes them movable-with-pin. Expect no PM to drag before S3 — that is the decision working, not a defect. | **signed 2026-09-10** |
| **OD-2** | Identity source on RST — which `Users` map to logins? | `App_User` rows for Adriaan (dev) + `WORKMATE_DEV_USER_ID` in dev (actor `1` = `SYS_USER`); RST people mapped when Andrew (RST) supplies the list. | open |
| **OD-3** | Audit provenance strings: `server_name='Perspective'`, `Source_Form='Planner'` | `server_name='SaaS'`, keep `Source_Form='Planner'` so reports filter the same way. | open (S2) |
| **OD-4** | Proposal files (`PLANNER_UI_DIR\proposals\*.json`) | new table `dbo.Planner_Proposal (id, created, weeks, json, applied_by)` in S5; no filesystem. | open (S5) |
| **OD-5** | `/open` WOMaint handoff — WOMaint doesn't exist in the SaaS yet | S1–S4: the selected card shows WO details inline (S1g draws it); `/workorders/$id` route arrives with the WO module. | open (interim in force) |
| **OD-6** | Time zone of "today" and week starts | `WORKMATE_TZ` (default `Pacific/Auckland`) touches exactly one point — resolving "now" to a civil date; all day math on civil dates; `weekStart` flips from Ignition's 1=Sunday to Python's 0=Monday, with an explicit Sunday test. | **signed 2026-09-10** |

**Signed since, by gate** (don't re-litigate; terms in the log named):

| ID | One line | Gate |
|----|----------|------|
| **OD-7** | The four operational `PLANNER_*` knobs stay table-with-code-defaults, nothing written to RST; `PLANNER_DEV_USER_ID` → `.env` `WORKMATE_DEV_USER_ID`; `PLANNER_AUTOPILOT_USER_ID` decided in S5 | 2026-09-11, log 09-11 1.0.0 |
| **OD-8** | `round()` keeps Python 3 half-to-even; ≤1 on `pct`, never on `counts`; documented not patched | 2026-09-11 |
| **OD-9** | `labourRules` returns `resDate` as `datetime.date`; the S4 service formats it | 2026-09-11 |
| **OD-10** | `rules.py` starts at 1.0.0 with `PORTED_FROM = "workmate.planner 1.3.1"`; `libVersion` reports `__version__` | 2026-09-11 |
| **OD-11** | `UOM_MODAL` and `_PRIORITY_SQL` gain the tie-break the source lacked | 2026-09-11 |
| **OD-12** | `app/auth/` is in no slice; `deps.get_current_actor()` is the interim seam (dev user when `WORKMATE_ENV=dev`, else 401), swapped for JWT in S2 | 2026-09-11 |
| **OD-13** | `loadWO`, `movePreview`, `GET /preview` move from S1 to S2 | 2026-09-11 |
| **OD-14** | `/range` envelope keeps `ok`, `apiVersion`, `actor`, `ms`; `gate` dropped | 2026-09-11, log 09-11 1.1.0 |
| **OD-15** | Error body is flat `{ok:false, code, message, rid}` app-wide | 2026-09-11 |
| **OD-16** | `service.WindowError(ValueError)` with `code='BAD_WINDOW'`; the router catches the type | 2026-09-11 |
| **OD-17** | The API 404 handler stays out of S1c — **reversed by OD-19** | 2026-09-11 |
| **OD-18** | `diag.configure()` from `create_app()`: one stdout handler on `workmate.diag`, level from `WORKMATE_LOG_LEVEL`, `propagate=False`, idempotent; root never touched | 2026-09-11, log 09-11 1.2.0 |
| **OD-19** | `app.frontend()` mounts only when `dist/index.html` exists; `/health` `frontend: "missing"` + `[G] frontend not built` otherwise | 2026-09-11 |
| **OD-20** | `/health` gains `diagWired`; `diag` keeps meaning persist mode; `versions` read each `__version__` | 2026-09-11 |
| **OD-21** | Web toolchain: `@tanstack/cli create web --router-only --toolchain eslint --no-examples --package-manager pnpm --no-git -y` | 2026-09-11 (S1e gate), log 09-12 1.0.0 |
| **OD-22** | Generator `@hey-api/openapi-ts`, bundled fetch client + `@tanstack/react-query` plugin, input = the committed `docs/api/openapi_<ver>.json`, Prettier-only post-process; `openapi-typescript` rejected | 2026-09-11 |
| **OD-23** | `MAX_WINDOW_DAYS = 42` inclusive, client-side in `usePlannerRange`; refused windows never fetch; API unchanged | 2026-09-11 |
| **OD-24** | Workers rail internal by default, contractors behind a toggle; API unchanged | 2026-09-11 |
| **OD-25** | Capacity bar ports the oracle exactly — `width: min(100, pct)%`, `barClass(pct)`, `planned / capacity h (pct%)` degrading to `planned h`; no placeholder heuristic | 2026-09-11 |
| **OD-26** | Rail rows = `workers` in API order filtered to internal; toggles **contractors** (off) and **loaded only** (on, `load[id] > 0`); the header always carries the count line | 2026-09-12 (S1f gate), log 09-12 1.1.0 |
| **OD-27** | The oracle's CSS ports as `features/planner/planner.css`, same class names, scoped under `.wm-planner`; Tailwind/shadcn adoption decided at the first non-port component | 2026-09-12 |
| **OD-28** | Pins: TypeScript 6.x, ESLint 10; TypeScript 7.0.2 published and not taken | 2026-09-12 |
| **OD-29** | URL state = `mode` + `anchor`, plain `validateSearch` on `parseIso`, no zod; `from`/`to` never in the URL; cats / selection / rail toggles in Zustand, not persisted | 2026-09-12 |

**Raised, unsigned — each is an audit's first line, never a build step:** request concurrency and cancellation on `/range` (open item 18, S1g audit); priority badge colours for RST's `P1`…`P6`/`N/A` — colour by `Priority.sortOrder`/id departs from the oracle (item 19); the six-month summary shape (item 4); an `app/auth/` slice (OD-12 interim).

## 10. Changelog

- 1.0.1 (2026-09-13) First reissue, read in full before editing (the 1.0.0 correction queue had carried unapplied since 2026-09-10). Status Draft → Active. Oracle UI is `Planner_v1_8_1.html`. §1 records what parity S1 actually claims. §2: `loadWO`/`movePreview` to S2 (OD-13), OD-11 tie-breaks, `get_current_actor` (OD-12), OD-15/16 error handling, the OD-27 CSS port, and the `PLANNER_*` row rewritten per OD-7 — `PLANNER_DEV_USER_ID` is `.env` `WORKMATE_DEV_USER_ID`. §3 carries the OD-14 envelope and the OD-15/16 error body, the OD-23 cap, the OD-25 rendering, OD-8 rounding, OD-10 lineage. §4: `/health` fields (OD-20), `/preview` → S2, `/_diag/client` deferred, actor paragraph corrected. §5 gains the signed deviations and the RST priority-domain note. §6: S0 as it happened; S1 split into S1a–S1g with tags and dates; S2 gains `/preview`, dnd-kit and the JWT swap; S6/S7 notes; the auth and six-month gaps named. §7 rewritten to what S1f shipped, what S1g/S2/S4 own, OD-29 state split, harness facts. §8: `get_current_actor`, the S1d/S1f test files, count-from-the-run. §9: status on OD-1…OD-6, every signed OD-7…OD-29 with its gate, the unsigned list.
- 1.0.0 (2026-09-10) Initial — from the live KT planner state (lib 1.3.1, api 1.8.3, ai 1.1.0, chat 1.2.1, test 1.0.0, UI 1.7.1).
