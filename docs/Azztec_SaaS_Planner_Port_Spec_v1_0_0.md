# Azztec SaaS — Planner Port Spec (P-PLN1-SaaS)

**File:** Azztec_SaaS_Planner_Port_Spec_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-10 · **Author:** Adriaan
**Status:** Draft — OD-1…OD-6 need 🤙 before S1
**Source of truth (attach to project knowledge):** `workmate_planner_code_v1_3_1.py`, `workmate_planner_api_code_v1_8_3.py`,
`workmate_planner_ai_code_v1_1_0.py`, `workmate_planner_chat_code_v1_2_1.py`, `workmate_planner_test_code_v1_0_0.py`,
`PlannerCalendar_v1_3_0_view.json`, `Planner_v1_7_1.html` (+ `wm-ui.css`/`wm-ui.js`), `Workmate_Planner_Assistant_Prompts_v1_0_0.md`
**Legacy behaviour authority:** `Workmate_NET_Manual` Labour Resource module (pp.157–168) via `Workmate_NET_Logic_Reference_v1_1.md`

---

## 1. Purpose

Port the live KT Planner to FastAPI + React **behaviour-for-behaviour**, running first against the RST data, keeping the
JSON contract byte-compatible so (a) the Ignition planner is the parity oracle and (b) `Planner_v1_7_1.html` can be pointed at
the new API as a smoke test. The planner was deliberately built for this: everything the UI shows is assembled in
`workmate.planner` from pure functions over plain dicts; `planner_api.route()` is a pure request→response function;
`planner_chat.parse()` is the LLM seam.

## 2. Ignition → SaaS mapping

| Ignition piece | SaaS home | Port type |
|----------------|-----------|-----------|
| `workmate.planner` pure rules (`category`, `engineOwned`, `hoursFor`, `assignedFor`, `classifyTeams`, `buildWorkers`, `initialsOf`, `workerLoad`, `capacityByWeek`, `workerWeeks`, `moveRules`, `estimateRules`, `labourRules`, `civilDays`, `weekStart`, `parseIso`, `iso`, `timeOf`) | `backend/app/planner/rules.py` | **1:1**, same names, same dict keys, Python 3 |
| `workmate.planner` SQL (`_woSql`, `_LABOUR_SQL`, `_WORKER_SQL`, `_PRIORITY_SQL`, `_loadSql`, pin selects) | `backend/app/planner/sql.py` | rewrite to dialect-portable form (COALESCE, CURRENT_TIMESTAMP, tags) — same columns, same aliases |
| `fetchWOs / fetchLabour / labourRows / fetchSkillRows / fetchPriorities / workers / rangeData / loadWO / hoursUomId / pinTableExists` | `backend/app/planner/repo.py` (+ `service.range_data`) | same output dicts; `system.db` → `db.rows()` |
| `moveWO / undoMove / setEstimate / unpin / addLabour / removeLabour / setCapacity / movePreview` | `backend/app/planner/service.py` | same signatures in snake_case (`move_wo(wo_id, to_iso, user_id, expect_start_iso=None, confirm=False, dry_run=True, conn=None)`), same result dicts, one `engine.begin()` per call |
| `pm_engine.weekNo` (`_netWeekNoAndYear`) | `backend/app/core/weekno.py` | 1:1 (.NET algorithm) with unit tests against known KT values |
| `workmate.planner_api.route()` + WebDev shims | `backend/app/planner/router.py` (`APIRouter(prefix="/api/v1/planner")`) | routes keep names and bodies; sid/tok gate → JWT dependency; `/ui`, `/lib/*` → gone (`app.frontend()`); `/open` → client-side navigation |
| `workmate.planner_ai` | `backend/app/planner_ai/` (S5) | 1:1 pure; `fetchHistory` → repo |
| `workmate.planner_chat` | `backend/app/planner_chat/` (S5b) | 1:1; session context dict keyed by JWT `sub` |
| `workmate.planner_test` t_* | `backend/tests/test_planner_*.py` | one pytest per t_* |
| `PlannerCalendar_v1_3_0` host view (iframe, sid/uid/tok, `wm-plan-open`) | none — the SPA is the host | drop |
| `Planner_v1_7_1.html` single-file UI | `web/src/features/planner/*` | re-implement in React; behaviour parity, not pixel parity |
| Diag wiring (`sendMessage 'debug-log'` + `dbo.Diag_Log`) | `app/core/diag.py` + request-id middleware | keep tags [F]/[G]/[E] and message texts |
| `System_Configuration PLANNER_*` switches | same table via `config_value()` | keep keys: `PLANNER_AUTOPILOT`, `PLANNER_AUTOPILOT_MAX_MOVES`, `PLANNER_AUTOPILOT_MAX_WEEKS`, `PLANNER_AUTOPILOT_USER_ID`, `PLANNER_NIGHTLY_WEEKS`, `PLANNER_DEV_USER_ID`; retire `PLANNER_SID_GATE`, `PLANNER_TOKEN_SECRET`, `PLANNER_UI_DIR` (proposals move to a table or `WORKMATE_DATA_DIR`) |

## 3. The JSON contract (unchanged keys)

`GET /api/v1/planner/range?from=YYYY-MM-DD&to=YYYY-MM-DD` → `RangeData`:

| Key | Type | Notes |
|-----|------|-------|
| `from`, `to`, `today` | `YYYY-MM-DD` | window inclusive; 400 on bad window or > 400 days |
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
| `workerWeeks` | `{"<userId>": [{weekStart, planned, capacity, pct, flag (over/ok/under/empty)}]}` | flag thresholds: over >100, ok 80–100, under 1–79 with capacity, empty 0 |
| `uomHours` | int | the `LRStd` UOM id |
| `libVersion` | str | `rules.__version__` — the port reports its own version here |

Write results keep the Ignition dict shapes (`{ok, code, message, sid, preview?, undo?, …}`).

## 4. Routes

| Ignition (WebDev `/planner/...`) | SaaS | Body / query | Result codes |
|----------------------------------|------|--------------|--------------|
| `GET /health` | `GET /api/v1/health` (app-wide) | — | versions of app, rules, api; `db: ok` |
| `GET /range` | `GET /api/v1/planner/range` | `from, to` | 200 RangeData; 400 bad window |
| `GET /_echo` | `GET /api/v1/_diag/self-test` | — | actor, gate, diag persist path |
| `POST /open` | client-side `navigate('/workorders/$id')` | — | — |
| `POST /move` | `POST /api/v1/planner/move` | `{woId, toIso, expectStartIso, confirm}` | 200 `{ok:true, …undo}` · 200 `{ok:false, code:'CONFIRM', preview}` · 409 `STALE` · 422 `LOCKED_STATUS/ENGINE_OWNED/NO_START/BAD_DATE/NO_CHANGE` · 401/403 `NO_IDENTITY` |
| `POST /undo` | `POST /api/v1/planner/undo` | `{woId, toIso, expectStartIso}` | as move, confirm implied |
| `POST /estimate` | `POST /api/v1/planner/estimate` | `{woId, hours}` | 200 · 422 `LOCKED_STATUS/BAD_HOURS/NO_DETAILS` |
| `POST /unpin` | `POST /api/v1/planner/unpin` | `{woId}` | 200 · 422 |
| `POST /labour` | `POST /api/v1/planner/labour` | `{woId, userId, skillId, hours, resDate, note}` | 200 · 422 `LOCKED_STATUS/NO_USER/USER_INACTIVE/NO_SKILL/BAD_HOURS/BAD_DATE` |
| `POST /labour/remove` | `POST /api/v1/planner/labour/remove` | `{woId, resId}` | 200 (returns the row for undo) |
| `POST /capacity` | `POST /api/v1/planner/capacity` | `{userId, sysSkillId, hrsPerWeek}` | 200 · 422 (0..168) |
| `GET /preview` | `GET /api/v1/planner/preview` | `woId, to` | movePreview |
| `GET /suggest` | `GET /api/v1/planner/suggest` | `from, weeks, lookahead, capacity, woId` | S5 |
| `GET /history` | `GET /api/v1/planner/history` | `woId` | S5 |
| `GET/POST /settings` | `GET/POST /api/v1/planner/settings` | `{key, value}` (whitelist) | S5 |
| `POST /nightly` | `POST /api/v1/planner/nightly` + CLI `workmate planner nightly` | `{weeks, apply}` | S5 |
| `POST /chat` | `POST /api/v1/planner/chat` | `{text, woId, reset}` | S5b |
| `POST /_diag` | `POST /api/v1/_diag/client` | `{level, message, detail}` | browser errors |

Actor: every write needs `User_Id > 0` from the JWT (`sub`); dev override `PLANNER_DEV_USER_ID` only when `WORKMATE_ENV=dev`.

## 5. Rules that must survive untouched

- `moveRules`: refuse `LOCKED_STATUS` (C/D), `ENGINE_OWNED` (PM the engine owns, no pin table), `NO_START`, `BAD_DATE`, `NO_CHANGE`; confirm reasons `PAST`, `ACTIVE` (V), `SPAN` (multi-day), `LABOUR_MULTI`; `willPin` / `willUnpin` / `pinnedAfter`.
- `moveWO` transaction: header start/end shifted by the civil-day delta (time of day kept, NULL end stays NULL), `Week_No = weekNo(newStart)`, subtasks shifted per row in collision-safe order (descending dates when delta > 0), `WO_N_Resource.Res_Date` shifted, `WO_Event_History` 'Rescheduled' + per-field 'Update' rows in the clsSimpleComparer format, `Source_Form='Planner'`; `expectStartIso` optimistic lock; every write returns a dict, never raises past the service boundary; `dry_run=True` default.
- `estimateRules`: 0 ≤ h ≤ 1000, needs a `WO_N_Details` row.
- `labourRules`: active user, ≥1 active skill row, 0 < h ≤ 500, `Res_Date` defaults to WO start; `Res_Id = MAX+1` in-tx; UOM = `LRStd` row; `Supplier_Id` from the skill row.
- `setCapacity`: 0..168 on ONE `User_Skill` row (`Sys_User_Skill_Id`).
- `civilDays`: pure calendar arithmetic; DST test 17↔29 Sep 2026 = ±12.
- Autopilot guardrails (S5): no PMs, priority A/B only, ≤ `PLANNER_AUTOPILOT_MAX_WEEKS` pull, ≤ `PLANNER_AUTOPILOT_MAX_MOVES`/night, never into the past, every move carries its undo.

## 6. Slices

| Slice | Deliverables | Smoke (paste output) |
|-------|--------------|----------------------|
| **S0 scaffold** | repo, `pyproject`, `main.py`, `config.py`, `db.py`, `diag.py`, `test_smoke.py`, migrations 0001–0004, `web/` scaffold, generated client | `uv run pytest -q` green; `/api/v1/health` → `{app, db:"ok", …}`; `pnpm build` green; RST probes §8 of the Data Layer doc pasted |
| **S1 read-only range** | `rules.py` (pure set) + `test_planner_rules.py`; `sql.py`, `repo.py`, `service.range_data`, `schemas.py`, `router.py` (`/range`, `/preview` read); React `PlannerGrid` month/week with cards, legend, counts, capacity bars, worker panel, 60 s quiet poll | parity: `counts` for the same window equal the Ignition `/planner/range` on the same DB snapshot (KT dev DB) — script `scripts/parity_range.py`; RST window renders |
| **S2 move / undo / estimate** | `service.move_wo/undo_move/set_estimate`, weekno port, router writes, confirm dialog, optimistic drag with rollback, undo toast | DST 17↔29 test; `STALE` round-trip with two tabs; `[F] move …` rows in Diag_Log and `WO_Event_History` rows in the clsSimpleComparer format |
| **S3 pins** | `0002_wo_n_plan` migration, pin-aware reads, `unpin` | move a PM → pinned; move back → unpinned (OD-1 decides RST semantics) |
| **S4 labour + capacity** | `add_labour/remove_labour/set_capacity`, labour popup, worker weeks flags | greaser 20 h/week scenario from KT reproduced on RST data |
| **S5 planner_ai** | port `planner_ai` pure + history repo; `/suggest`, `/history`, `/settings`, `/nightly`; CLI `workmate planner nightly`; Task Scheduler job | `planHorizon` on RST returns needs-estimate list + pull-forward plan; nightly writes a proposal row |
| **S5b chat** | `planner_chat.parse()` port + `/chat`; React chat panel; the prompts doc satisfied | every prompt in `Workmate_Planner_Assistant_Prompts_v1_0_0.md` answers as before |
| **S6 parity pack** | every `planner_test.t_*` as pytest; Playwright drag/drop smoke; CI green | `t_versions t_rules t_workers t_moverules t_dst t_chat_parse t_ai_pure t_range t_api_routes t_http t_ai_live t_chat_live t_rb_move t_rb_pin t_rb_labour` all PASS |
| **S7 serve** | `app.frontend()` with the built SPA, reverse proxy, service install, nightly job | one URL, login, planner loads over LAN |

## 7. React UI plan (S1–S4)

- Route `web/src/routes/planner.tsx`; feature folder `features/planner/`: `PlannerGrid` (month/week toggle, Mon–Sun columns), `DayCell` (droppable, `id = ISO date`), `WOCard` (draggable `wo-<id>`, category colour from `colours`, priority letter badge, hrs/hrsSrc, pin/lock glyphs), `CapacityBar` (per week from `weeks`), `WorkerPanel` (workers/teams, `workerWeeks` flags), `SelectedWOCard` (labour rows, estimate edit, unpin), `ConfirmMoveDialog` (preview reasons), `UndoToast`.
- Data: `usePlannerRange(from,to)` TanStack Query, `staleTime 30 s`, `refetchInterval 60 s`, background off when hidden; mutations `useMoveWO`, `useEstimate`, … with optimistic cache edits and rollback on `ok:false`/error.
- State: Zustand store `{view, anchorDate, selectedWoId, filters (hideDone, team, worker)}`; URL search params via TanStack Router for `from/to/view` so links are shareable.
- Dates: `lib/dates.ts` = `civilDays`, `weekStart`, `iso`, `addDays` twins using `date-fns` (`differenceInCalendarDays`, `startOfWeek({weekStartsOn:1})`).
- Drag/drop: `@dnd-kit/core` — `DndContext` + `PointerSensor {distance: 6}` + `pointerWithin`; `onDragEnd` → `moveWO(woId, overId, expectStartIso=wo.start)`; `CONFIRM` opens the dialog; `STALE` invalidates and toasts.
- Diag: `window.onerror` → `POST /api/v1/_diag/client`.

## 8. Tests (pair rule)

- `test_planner_rules.py`: the `t_rules`, `t_moverules`, `t_dst`, `t_workers` cases as parametrised pytest (no DB).
- `test_weekno.py`: known KT `Week_No` values (e.g. 2026-09-14 → 2026.38 — confirm against the KT DB before pinning).
- `test_planner_repo.py`: rolled-back connection fixture; `range_data` on a fixed RST window; `move_wo(dry_run=True)` plan shape.
- `test_planner_api.py`: `TestClient` with `get_current_user` overridden; route matrix from §4 (method-not-allowed → 405, codes).
- `web/src/features/planner/*.test.tsx`: `lib/dates` DST cases; `WOCard` renders category/pin/lock; grid places a WO in the right cell.
- `web/e2e/planner.spec.ts`: drag a WO one day forward, confirm dialog path, undo.

## 9. Open decisions (need 🤙)

| ID | Question | Proposal |
|----|----------|----------|
| **OD-1** | RST has no PM engine and no `WO_N_Plan`. What is `engineOwned()` there? | Keep the rule as coded: without the pin table, engine-owned PMs are `locked` (exactly Ignition 1.1.0 behaviour). Run migration 0002 on RST in S3 so PMs become movable-with-pin; when an RST PM engine exists later it honours the pins. No new code paths. |
| **OD-2** | Identity source on RST — which `Users` map to logins? | `App_User` rows created for Adriaan (dev) + `PLANNER_DEV_USER_ID` in dev; RST people mapped when Andrew (RST) supplies the list. |
| **OD-3** | Audit provenance strings: `server_name='Perspective'`, `Source_Form='Planner'` | `server_name='SaaS'`, keep `Source_Form='Planner'` so reports filter the same way. |
| **OD-4** | Proposal files (`PLANNER_UI_DIR\proposals\*.json`) | new table `dbo.Planner_Proposal (id, created, weeks, json, applied_by)` in S5; no filesystem. |
| **OD-5** | `/open` WOMaint handoff — WOMaint doesn't exist in the SaaS yet | S1–S4: card shows WO details inline; `/workorders/$id` route arrives with the WO module. |
| **OD-6** | Time zone of "today" and week starts | server default `Pacific/Auckland` (`WORKMATE_TZ`), per-tenant later; all day math on civil dates. |

## 10. Changelog

- 1.0.0 (2026-09-10) Initial — from the live KT planner state (lib 1.3.1, api 1.8.3, ai 1.1.0, chat 1.2.1, test 1.0.0, UI 1.7.1).
