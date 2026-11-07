# Azztec SaaS — DP3 Planner Moves — Chunk Spec

**File:** Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md · **Version:** 1.0.1 · **Date:** 2026-11-07 · **Author:** Adriaan
**Status:** **Signed 🤙 2026-11-07** — OD-104…OD-115 as proposed in 1.0.0, with Block DP3-E's output (08:07, read-only, `dbWorkmate_DP1_Test`). The probe raised two questions, answered the same morning with the recommended option each time: **OD-116** (SPAN is shown, never asked) and **OD-117** (the `Update` rows carry Workmate.NET's date format). 1.0.1 fills §3.5 with the evidence and folds both into §4–§6 and §8; no other OD moved.
**Slice:** DP3, the third of four for the Redstag test drop (Monday 2026-11-09). It builds as two slices:
- **DP3a** — backend and contract: move, undo and preview over HTTP, smoked with `curl.exe` before any UI exists
- **DP3b** — web: drag, confirm, toast, undo, Ctrl+Z, rights-aware

DP3b needs DP3a committed (it builds on the regenerated client).
**Target path:** `docs/` + project knowledge: add 1.0.1 (1.0.0 never goes in).
**Sits on:** `b4c4e65` (docs close); code at `1eaf3de`, tag `dp2b-signin-1.0.0`; migration head `0002`; backend 401 passed / 2 skipped; frontend 461 in 28 files; app 0.6.0, `docs/api/openapi_0_6_0.json` (12 paths).
**Oracle:** `docs/reference/workmate_planner_code_v1_3_1.py` (write side 752–1190), `docs/reference/workmate_planner_api_code_v1_8_3.py` (write routes 659–758, preview 995–1000; byte-identical in every function this slice ports to the 1.9.1 in the 2026-11-05 gateway export), `Planner_v1_8_1.html` (project knowledge; S2/S3 write UI — `whyNotMovable`, `applyMoveLocally`, `doMove`, `undoLast`, `handleWriteError`, `showConfirm`, `onPointerDown/Move/Up`, `endDrag`, `toast`, `wire`). Read 2026-11-07; nothing ported from Workmate.NET.

---

## 1. Why this slice exists

Redstag tests the Planner on Monday, and Andrew's bar is that it moves work, not just shows it. DP3 is the first slice that writes work-order data: a WO's dates, its subtasks', its planned labour's, a pin row for engine-owned PMs, and the audit rows that say who did it. Everything it writes, the Ignition planner has written at KT since September; the port keeps its statements, its result dicts and its feel, closes one race the oracle left open, and says where it departs.

DP2 left two things for it: a real actor on every write (`Principal.user_id`) and `require('planner', 'RW')` for move and undo (DP2 spec §11.3).

## 2. Scope

**In (DP3a):** `GET /api/v1/planner/preview`, `POST /api/v1/planner/move`, `POST /api/v1/planner/undo`; `load_wo`, `move_preview`, `move_wo`, `undo_move`; the pin on an engine-owned PM's first move and its release on a move back; the audit rows; the diag lines; app 0.7.0 and the regenerated client.

**In (DP3b):** drag a chip to another day (week, two-week, month); the confirm dialog when the server asks; the toast with Undo; Ctrl+Z (a stack of 10); the poll paused while a drag, a write or a dialog is live; every move affordance absent at RO.

**Out:** estimate (OD-105); the Unpin button (S3) and planned labour (S4); the day dialog's Plan hours / Open actions; Suggest, the nightly proposal, the assistant; the 6M view; the parity script (S6); `Query_Log` (OD-109); the `actor #21` label becoming a name (DP4's list, §10).

## 3. Evidence

### 3.1 What the oracle does

**`moveWO`** (`workmate.planner` 1.3.1, 940–1052), in order:
1. `loadWO` (820–853): the header (`Request_Start_Date`, `Request_End_Date`, `Week_No`, status, type), `Duration_In_Hours` and whether a details row exists, the three pin columns, every subtask `Req_Start_Date`, and the planned-labour dates grouped by `Res_Date` with counts. `NOT_FOUND` when there is no header.
2. The optimistic lock: `expectStartIso[:10] != start` → `STALE` with `currentStart`.
3. `moveRules` (856–903, ported 1:1 as `rules.py` 1.1.0 533–631): refuse `LOCKED_STATUS` (C/D), `ENGINE_OWNED` (a PM with no pin table — never at RST since `0001`), `NO_START`, `BAD_DATE`, `NO_CHANGE`; confirm reasons `PAST`, `ACTIVE` (V), `SPAN`, `LABOUR_MULTI`; `willPin` / `willUnpin` / `pinnedAfter`.
4. `CONFIRM` + `movePreview` unless `confirm`; `NO_IDENTITY` when the user id is ≤ 0.
5. The plan dict; `dryRun` returns it untouched.
6. One transaction: the header (`Request_Start_Date`, `Request_End_Date`, `Week_No` = `pm_engine.weekNo(newStart)`, rowcount must be 1) → subtasks, one `UPDATE … DATEADD(DAY, delta, Req_Start_Date), Week_No = weekNo(newDay)` per distinct old day, descending when the delta is positive so no row is moved twice → planned labour, one `DATEADD` over every `'L'` row with a date → the pin (`_upsertPin` 1120–1130 on `willPin`, `Pinned = 'N'` on `willUnpin`) → the audit rows (783–797): `Rescheduled` (or `Rescheduled (undo)`), `Pinned` / `Unpinned` when relevant, and `Update` rows in the .NET `clsSimpleComparer` shape for `Request_Start_Date` and, when there is an end, `Request_End_Date`. Any failure rolls back and returns `WRITE_FAILED`; nothing raises past the library.
7. `undoMove` (1055–1059) is `moveWO(confirm=True, eventName='Rescheduled (undo)')` to the `undo` dict the move returned.

**The API** (`planner_api` 1.8.3): `_move` (724–743) validates `woId`/`toIso`, resolves the actor, calls the library with `dryRun=False`, logs one `_diagWrite` line (666–699) and maps the dict through `_writeResult` (702–710) and `_CODE_HTTP` (659–663): `NOT_FOUND` 404, `STALE` 409, `NO_IDENTITY` 403, `CONFIRM` **200**, rule refusals 422, `BAD_REQUEST` 400, `WRITE_FAILED` / `INTERNAL` 500. `_preview` (995–1000) maps `movePreview` the same way.

**The UI** (`Planner_v1_8_1.html`): a pointer drag on the grid (6 px before it starts; a not-movable chip toasts `whyNotMovable` instead; the ghost is a clone of the chip; the target is `elementFromPoint` → the nearest `[data-date]`, outlined dashed; Esc and `pointercancel` end it; the click that follows a drag is swallowed for 50 ms). A drop on another day posts `{woId, toIso, expectStartIso: wo.start, confirm}`. **Ok** → push `undo` (stack 10), apply the new dates to the cached window, toast `Moved X → <Mon 16 Nov 2026> (+n d)` plus a pin note, with an Undo button, for 6.5 s, then a silent reload. **CONFIRM** → `showConfirm`: `MOVE X?`, old → new, the reasons, the labour moves, the subtask count, Cancel / Move it, Enter = Move it. **STALE** → toast and refresh. **NO_IDENTITY** → banner. Ctrl+Z → `undoLast`. The 60 s poll and the focus reload skip while busy, dragging or a dialog is open.

### 3.2 What the SaaS already has (read from the repo at `b4c4e65`)

- `rules.py` 1.1.0: `moveRules` and `estimateRules` ported 1:1, `_fmtDelta`, `parseIso` / `iso` / `civilDays` on `datetime.date`. **Unchanged by DP3.**
- `core/weekno.py` 1.0.0: `week_no(d) -> Decimal` (numeric(6,2), OD-48), built for exactly this write.
- `repo.pin_table_exists`, `sql._PIN_COLS` / `_NOPIN_COLS`, `sql.ALL_STATEMENTS` (the dialect gate and the colon-in-comment gate in `test_planner_repo.py` are parametrised over it, so a new statement is gated by being registered).
- `core/deps.py` 1.2.0: `require(page, right)`, `require_csrf`, the principal per request; `main.py` puts `require('planner','RO')` on the whole planner router. The web client's interceptor already sends `X-Azztec-Request: 1` on every POST (DP2b).
- The DOM contract S1f/S1g built for this: `div.chip[data-wo][data-movable]` with `.mv` when movable, `.cell[data-date]` in every mode, `.chip{touch-action:none;-webkit-user-drag:none}`. Not yet ported: the drag states, the ghost, the toast, the confirm dialog's `.mv` / `.sub` / list rules.
- `PlannerView` 1.1.0 is props-driven (`mode`, `anchor`, `onSearch`); `routes/planner.tsx` 1.0.1 binds them; `useSession()` and `auth/rules.allows(have, need)` exist for the right.
- `chipTitle` already says `drag to move` on movable chips (OD-33 parity) — a promise the read-only build could not keep.

### 3.3 RST facts already on record

- `WO_Event_History`: `Sys_WO_Event_Id numeric(18,0)`, `WO_ID numeric(18,0)` NOT NULL, `User_Id_Edited_By`, `Edited_Date datetime`, `Event_Name varchar(150)`, `event_details varchar(max)` (the 990 cap is the writer's convention), `server_name varchar(50)`, `Source_Form varchar(50)` (Landmines §E, measured 2026-09-19).
- **`server_name` is NULL on every RST row**; `Source_Form` holds `WO Maintenance` 190,573 · `WO ScheduleX` 43,288 · `WOW` 14,059 · `WO Timesheet` 1 (Landmines §E).
- Triggers on RST are PO-only (Landmines §E, 2026-09-11).
- `dbWorkmate_DP1_Test` is a pristine RST restore at head `0002`, **compatibility level 160**, where sign-in works; `WO_N_Plan` exists and is empty; dev `dbWorkmate` is at `0001` and nobody can sign in there (raw log 11-07 §5, §9).
- At compat ≥ 130 a `datetime` compared with a `datetime2` is converted exactly, so a value read back and bound again does not compare equal (`.057` is stored as `.0566667`). The write path never compares datetimes by equality (OD-110).
- Planner rights at RST: RWD 24 · RW 389 · RO 1 · NA 29 — **413 of 443 active accounts can move** (DP2 spec §3.4, §11.3).

### 3.4 Where this departs from the Port Spec's S2 plan

| Port Spec 1.0.8 said | DP3 does | Why |
|---|---|---|
| `@dnd-kit/core`, `DragOverlay` | the oracle's pointer drag (OD-106) | the DOM contract is already the oracle's; no install two days out |
| optimistic edit with rollback | apply on ok, then refetch (OD-113) | that is what the oracle does, so there is nothing to roll back |
| the JWT seam (OD-12) | the DP2 session principal | OD-97 replaced it |
| `Server_Name` per OD-3 | OD-108 closes OD-3 | |
| `dry_run=True` first | kept, plus a body flag the smoke uses (OD-111) | |

### 3.5 Block DP3-E (2026-11-07 08:07, `dbWorkmate_DP1_Test`, read-only; sqlcmd exit 0, no `Msg` line)

| Probe | Found | Consequence |
|---|---|---|
| P0 | DP1_Test: compat **160**, head `0002`, SQL Server 17.0.1000.7. Dev `dbWorkmate`: compat **170**. Also on the box: `dbWorkmate_KT` (100, read-only), `_KT_RFID`, `_QL_RST_Test`, `_RST_Test` | both test targets are ≥ 130, so §3.3's datetime rule holds everywhere (OD-110) |
| P1 | `WO_Event_History.Sys_WO_Event_Id` is an **identity**; the other seven columns as §3.3. `WO_N_Plan`: `Pinned char(1) NOT NULL DEFAULT 'N'`, `Note varchar(255)`, `Server_Name varchar(50)`, **`Entry_Date datetime NOT NULL DEFAULT getdate()`**, `Last_Save_Date` NULL. `WO_N_Header`: `Week_No numeric(6,2) NOT NULL`, both request dates `datetime` NULL, and **no edited / modified stamp** (only `Entry_date`, `User_Id_Created_By`, `Server_Name`). `WO_N_Subtasks.Week_No` is `numeric(18,2)` NULL. `WO_N_Resource.Res_Date` `datetime` NULL, `Resource_Type char(1)` | the oracle's inserts work as written: the pin insert leaves `Entry_Date` to its default and `Last_Save_Date` NULL until the next pin update (parity); a move stamps nothing on the header beyond its three columns |
| P2 | **No trigger** on any of the five. `WO_Event_History` is a heap with no index. `WO_N_Resource`'s key is `(Res_Id, WO_Id)` and no index leads with `WO_Id`, so the labour statements scan its 136,702 rows (as `/range`'s labour read already does). `WO_N_Subtasks`' key leads with `WO_ID`. `WO_N_Resource`'s eight foreign keys touch neither `WO_Id` nor `Res_Date` | nothing fires behind a move; the labour scan is a cost to watch, not a blocker |
| P3 | 3,789 open; none without a start or an end; a time of day on **658 starts** and **2,713 ends**; **3,650 end on a later day than they start (96 %)**; end before start 0; engine-owned PMs **2,364**; Active (`V`) 1,044; `Week_No` never NULL. Before-counts: `WO_N_Plan` 0 / 0, `WO_Event_History` 247,921 / 247,921, `Diag_Log` 85 / 178 (DP1_Test / dev) | the header's time of day is real data, kept by OD-110; the 96 % is **OD-116**; the counts are §8's baseline |
| P4 | 80,550 subtask rows, **none on an open WO**. 2,530 open WOs carry 2,993 planned-labour (`'L'`) rows: no NULL date, **no time of day**, **no WO with two times on one day**. 303 parts (`'P'`) rows sit on open WOs; only `'L'` moves (oracle) | the oracle's labour grouping stays (it equals grouping by day on this data). The subtask shift is ported for parity but **no RST row can exercise it** — it is proven by reading and by the dry plan only (§8) |
| P5 | Twelve months to the backup: `Update` 232,536 · `Create` 15,376 · `DELETE` 9 — no `Rescheduled` name exists at RST. `server_name` NULL on every row of every form; the longest `event_details` is 3,915 characters (`WO ScheduleX`). **Workmate.NET's date change reads `{Request_Start_Date} changed from {26/08/2026 12:00:00 am} to {2/09/2026 12:00:00 am}`** | **OD-117**; the 990 cap stays ours (the column is `varchar(max)`) |
| P6 | No open non-PM WO from 2026-08-01 has both subtasks and labour (P4 says why). Candidates: **A** 654458 `2KN-260608-002` (`A`, type `N`, 22 Dec 00:00 → 23 Dec 15:18, 2 labour rows); **B** 658823 `2BS-MEP-014-0001` (PM, `A`, 16 → 23 Dec, 2 labour rows); **C** 657188 `2BS-ELI-004-0002` (closed, 5 Dec); **V** 661118 `3ED-260811-002` (Active, 21 Dec → 20 Jan). Open work by start month: Jul 290 · Aug 1,019 · Sep 1,068 · Oct 5 · Nov 4 · Dec 199 | §8. On Monday most open work sits in August and September — before today — so a move there asks for `PAST` (correct); December is where a move goes straight through |

## 4. Decisions (signed 🤙 2026-11-07; OD-116 and OD-117 answered the same morning from DP3-E)

| ID | Decision | Why |
|---|---|---|
| **OD-104** | DP3 builds as **DP3a** (backend + contract, smoked over HTTP) then **DP3b** (web). In and out as §2. | The DP2 split worked: DP3a is proven with `curl.exe` before the UI exists, and each half fits a day. |
| **OD-105** | **Estimate stays out.** The hours badge stays read-only; `POST /estimate` is offered as DP3c after the drop. | Redstag's brief is moves. Estimate writes a different table (`WO_N_Details`) and brings a popover, a route and a smoke of its own for no Monday need. |
| **OD-106** | **The drag is the oracle's pointer drag**, ported as a hook (`useWoDrag.ts`) — no new package. DP3b's commit amends the two lines that name `@dnd-kit` (`CLAUDE.md`'s style line, `.claude/rules/frontend.md`). *Alternative:* `@dnd-kit/core` as those lines say. | S1f/S1g already built the oracle's DOM contract, so the port is about 150 lines of DOM code with nothing to install; the ghost is a clone of the painted chip, so the S1i badge colour comes free (the Port Spec's `DragOverlay` requirement); the feel is the oracle's — 6 px, Esc, touch. `@dnd-kit` would add a dependency, a lockfile change and its own semantics to learn and test two days before the drop. |
| **OD-107** | `POST /move` and `POST /undo` take `require('planner','RW')` and `require_csrf` on the route (the router's RO gate stays); `GET /preview` is a read at RO. The UI moves only when `allows(rights.planner, 'RW')`; at RO there is no drag, no grab cursor, no "drag to move" line and the RO hint. | DP2 §11.3; OD-34 (chrome says only what is true). The API is the gate; the UI hiding is courtesy. |
| **OD-108** | **Provenance (closes OD-3):** `server_name = 'SaaS'` on every `WO_Event_History` row and on a new `WO_N_Plan` row; **`Source_Form = 'Planner'`**. Event names and details are the oracle's: `Rescheduled` / `Rescheduled (undo)` `"<sid>: <from> -> <to> (+n days) via Planner"`; `Pinned` / `Unpinned`; `Update` `"{Request_Start_Date} changed from {<from>} to {<to>}"` and the same for `Request_End_Date` when there is an end — ISO dates, capped at 990 characters. `Edited_Date = CURRENT_TIMESTAMP`; `User_Id_Edited_By` = the signed-in person. *Alternative:* RST's own `'WO ScheduleX'` for `Source_Form`. | RST's `server_name` is NULL on every row, so `'SaaS'` is what tells our writes apart. `'Planner'` says where the change came from; `'WO ScheduleX'` would claim a .NET screen made it. |
| **OD-109** | **No `Query_Log` write.** | The Ignition planner never wrote it; it lives in a sibling database (`<db>_QL`) a test server may not have, and writing it is a cross-database, MSSQL-only statement. `WO_Event_History` and `Diag_Log` carry the audit; DP4's notice says so in one line. |
| **OD-110** | **One transaction per move, owned by the service** (`engine.begin()`), with the load, the rules and the writes inside it. The header `UPDATE` carries the start-day guard (`>= day AND < day + 1`): a move that raced ours makes it touch 0 rows, which is `STALE`, rolled back — never an overwrite. Subtasks: one `UPDATE` per distinct old day in the collision-safe order, `DATEADD` on the column; planned labour: one `DATEADD` `UPDATE`; the `DATEADD`s carry a `PG-CONVERT` tag in the statement header (the OD-60 precedent) and `CAST(:delta AS int)`. The header keeps its time of day (Python datetime + civil delta). No datetime is ever compared by equality. | The oracle's statements, plus the guard it lacked — its load ran outside its transaction. Day ranges are immune to the compat-160 conversion (§3.3). |
| **OD-111** | `dry_run=True` stays the library default. The API body carries `dryRun` (default `false`: the UI's real move); the smoke sends `dryRun: true` first. **The suite never writes:** service tests run dry on the rolled-back connection, and an autouse tripwire in the API tests makes every repo write function raise. | CLAUDE.md #2 and the tests rule; the tripwire turns "never send a real move from a test" from a habit into a failing test. |
| **OD-112** | **Contract:** app **0.7.0** (`openapi_0_7_0.json`, a rename of 0.6.0, OD-38), planner router **1.2.0** (`apiVersion`). Bodies keep the oracle's keys (§5.4); a success adds `actor` (int); `CONFIRM` is 200 `{ok:false, code:'CONFIRM', message, rid, sid, preview}`; refusals are OD-15's flat body plus `sid` (and `currentStart` on `STALE`). HTTP is the oracle's `_CODE_HTTP` for every code DP3 can produce; a malformed body is FastAPI's own 422, as `/range`'s missing parameters are. | `Planner_v1_8_1.html` can still be pointed at the API (Port Spec §1): it reads `code`, `message`, `preview` and `undo`. |
| **OD-113** | **The UI is the oracle's flow:** apply the move when the server says ok (no optimistic pre-apply, so no rollback path), then refetch every cached planner window; confirm only on `CONFIRM`; `STALE` → toast and refetch; `NO_IDENTITY` / `NO_RIGHT` → banner; the 60 s poll and the focus refetch pause while dragging, writing or a dialog is open. **Two deviations:** Ctrl+Z is inert inside a text input or select (the oracle's took the search box's own undo), and a refused undo (`STALE` / 422 / 404) leaves the stack instead of going back on top (the oracle's jammed the stack on the first stale entry); a failed one (network, 500) still goes back. | Parity, minus two defects found reading it. |
| **OD-114** | **PM pins at RST as the oracle does them:** the first move of an engine-owned PM writes its `WO_N_Plan` row (`Pinned 'Y'`, `Prev_Start` = the date it had, never overwritten by a later pin); moving it back onto that date — or undoing — sets `Pinned 'N'` and keeps the row. No Unpin button (S3). | Nothing at RST reads `WO_N_Plan` except this planner, so it costs nothing today and is the record a future PM engine needs; the pin glyph tells a planner which PMs were moved by hand. |
| **OD-115** | Every DP3 smoke runs on **`dbWorkmate_DP1_Test`**; every move it makes is undone in the same block; dev `dbWorkmate` is never written — its `Diag_Log`, `WO_N_Plan` and `WO_Event_History` counts are read before and after. | OD-103; DP1_Test is a pristine RST restore at `0002`, the only database sign-in works on. |
| **OD-116** | **SPAN is shown, never asked.** A move asks for confirmation only for `PAST`, `ACTIVE` or `LABOUR_MULTI`; a `SPAN` reason still travels in `reasons`, the preview lists it and the toast says where the end lands. The decision lives in `service.py` (`CONFIRM_REASONS`) and the preview's `confirm` is the service's; **`rules.py` stays byte-1:1 with the port** and `libVersion` does not move. A registered departure, like OD-35: the S6 parity pack carries it as an expected diff on `confirm`. | P3: 3,650 of 3,789 open WOs at RST end on a later day than they start — the "complete within" window — so the oracle's rule would ask on 96 % of drags, for a shift the planner expects. |
| **OD-117** | **The `Update` rows read as Workmate.NET writes them:** `{Request_Start_Date} changed from {26/08/2026 12:00:00 am} to {2/09/2026 12:00:00 am}` — `d/MM/yyyy h:mm:ss am\|pm`, the stored time of day included — and the same for `Request_End_Date`. The `Rescheduled` summary row keeps the oracle's ISO text. Amends OD-108's "ISO dates" for those rows only. | The oracle's own intent (794–797: "so the planner's rows read the same in history"); P5 shows what "the same" is at RST. |

## 5. DP3a — backend and contract

Versions are the next ones on each file; card names and counts are fixed at the build.

### 5.1 `app/planner/sql.py` 1.2.0 — ten statements, all in `ALL_STATEMENTS`

Reads:
- **`planner.load_wo`** (two variants, the `/range` pin columns reused): `WO_ID`, `Short_WO_Id`, `WO_Title`, `Status`, `WO_Type_Flag` (each `RTRIM(COALESCE(…))`), `Request_Start_Date`, `Request_End_Date` (raw), `COALESCE(Week_No, 0)`, `COALESCE(d.Duration_In_Hours, 0)`, `CASE WHEN d.WO_ID IS NULL THEN 0 ELSE 1 END AS HasDetails`, then `_PIN_COLS` or `_NOPIN_COLS`; `FROM dbo.WO_N_Header h LEFT JOIN dbo.WO_N_Details d ON d.WO_ID = h.WO_ID WHERE h.WO_ID = :wo_id`. The oracle's `_loadSql` (800–810).
- **`planner.subtask_dates`**: `Req_Start_Date` of the WO's subtasks with a date, ordered (812).
- **`planner.labour_dates`**: the WO's `'L'` rows with a date, `Res_Date` and `COUNT(*)`, grouped and ordered (815). The oracle's grouping by the exact value stays: P4 found no time of day on any planned-labour row, so it equals grouping by day.

Writes:
```sql
-- planner.move_header        params wo_id, new_start, new_end, week_no, day_from, day_to
UPDATE dbo.WO_N_Header
   SET Request_Start_Date = :new_start, Request_End_Date = :new_end, Week_No = :week_no
 WHERE WO_ID = :wo_id AND Request_Start_Date >= :day_from AND Request_Start_Date < :day_to

-- planner.shift_subtasks     params wo_id, delta, week_no, day_from, day_to   (PG-CONVERT in the header)
UPDATE dbo.WO_N_Subtasks
   SET Req_Start_Date = DATEADD(day, CAST(:delta AS int), Req_Start_Date), Week_No = :week_no
 WHERE WO_ID = :wo_id AND Req_Start_Date >= :day_from AND Req_Start_Date < :day_to

-- planner.shift_labour       params wo_id, delta   (PG-CONVERT in the header)
UPDATE dbo.WO_N_Resource
   SET Res_Date = DATEADD(day, CAST(:delta AS int), Res_Date)
 WHERE WO_Id = :wo_id AND RTRIM(COALESCE(Resource_Type, '')) = 'L' AND Res_Date IS NOT NULL

-- planner.pin_update         params wo_id, user_id, engine_date, note
UPDATE dbo.WO_N_Plan
   SET Pinned = 'Y', Pinned_By = :user_id, Pinned_On = CURRENT_TIMESTAMP,
       Prev_Start = COALESCE(Prev_Start, :engine_date), Note = :note, Last_Save_Date = CURRENT_TIMESTAMP
 WHERE WO_ID = :wo_id

-- planner.pin_insert         params wo_id, user_id, engine_date, note, server_name   (P1: Entry_Date defaults, Last_Save_Date stays NULL)
INSERT INTO dbo.WO_N_Plan (WO_ID, Pinned, Pinned_By, Pinned_On, Prev_Start, Note, Server_Name)
VALUES (:wo_id, 'Y', :user_id, CURRENT_TIMESTAMP, :engine_date, :note, :server_name)

-- planner.pin_clear          params wo_id
UPDATE dbo.WO_N_Plan SET Pinned = 'N', Last_Save_Date = CURRENT_TIMESTAMP WHERE WO_ID = :wo_id

-- planner.event_insert       params wo_id, user_id, event_name, details, server_name, source_form
INSERT INTO dbo.WO_Event_History
       (WO_ID, User_Id_Edited_By, Edited_Date, Event_Name, event_details, server_name, Source_Form)
VALUES (:wo_id, :user_id, CURRENT_TIMESTAMP, :event_name, :details, :server_name, :source_form)
```
The `-- name` lines above are this spec's labels; in the file each statement gets the house `# name:` / `# dialect:` / `# params:` header, the two `DATEADD` headers read `# dialect: MSSQL date arithmetic -- PG-CONVERT: <col> + make_interval(days => <delta>)`, and no SQL string carries a comment. The oracle's two MSSQL-only spellings (the null-default function and the current-time function) become `COALESCE` and `CURRENT_TIMESTAMP`; the docstring describes them without spelling them (the gate greps the whole file).

### 5.2 `app/planner/repo.py` 1.2.0

- **`load_wo(conn, wo_id) -> dict | None`** — the oracle's `loadWO` dict, same keys (`id sid title status type cat startDate endDate start end weekNo estimate hasDetails engineOwned pinned pinTable hasPinRow engineDate engineDateValue locked subtaskDates labourDates`), with `startDate` / `endDate` / `engineDateValue` the raw datetimes the writer needs. `labourDates` is a list of `(iso, n)`.
- **Writers**, each `-> int` (the rowcount): `move_header`, `shift_subtasks`, `shift_labour`, `upsert_pin` (the update, then the insert when it touched nothing — `_upsertPin`), `clear_pin`, `insert_event`. No commits, no `begin()`: the service owns the transaction.

### 5.3 `app/planner/service.py` 1.1.0

- Constants: `SERVER_NAME = 'SaaS'`, `SOURCE_FORM = 'Planner'` (OD-108), `EVENT_DETAILS_MAX = 990`, `CONFIRM_REASONS = ('PAST', 'ACTIVE', 'LABOUR_MULTI')` (OD-116); `_field_diff_detail(col, old, new)` and `_cap(details)` (oracle 794, 784–786); `_net_datetime(d)` → `26/08/2026 12:00:00 am` (OD-117: day without a leading zero, month with one, 12-hour clock, lower-case am / pm).
- **`move_preview(conn, wo_id, to_iso) -> dict`** — `movePreview` (923–937): the rules dict plus `woId sid title status statusTitle prevStart prevEnd subtasks labourDates`, and `labourMoves [{from, to, rows}]` when the rules pass; `confirm` is the service's (OD-116). `NOT_FOUND` when there is no header.
- **`move_wo(wo_id, to_iso, user_id, expect_start_iso=None, confirm=False, dry_run=True, event_name='Rescheduled', conn=None) -> dict`** — the Port Spec §2 signature. The oracle's steps 1–6 (§3.1), with step 4 asking only for a `CONFIRM_REASONS` reason (OD-116), the `Update` rows in OD-117's format, and OD-110's transaction: with `conn=None` the service opens `engine.connect()` for a dry run and `engine.begin()` for a real one, and a guard miss or a database error raises inside the block so the whole move rolls back, then comes back as `STALE` / `WRITE_FAILED`; with `conn` given the caller owns the transaction (the rolled-back test connection, the S6 `t_rb_move` port). `today` is `today_iso()` (OD-6). Never raises past the boundary except a programming error, which the middleware reports as `INTERNAL`.
- **`undo_move(wo_id, to_iso, user_id, expect_start_iso=None, dry_run=True, conn=None)`** = `move_wo(confirm=True, event_name='Rescheduled (undo)')`.
- **The result** (ok): `{ok, dryRun, woId, sid, prevStart, prevEnd, newStart, newEnd, delta, weekNo, prevWeekNo, subtasks, labourRows, reasons, events, willPin, willUnpin, pinned, engineDate, undo: {woId, toIso, expectStartIso}}` — `weekNo` the float of `week_no(newStart)`, `labourRows` the planned count on a dry run and the rowcount after a write, `engineDate` = the stored one, or the old start when this move pins.
- The service is silent; the router logs (as `range_data`).

### 5.4 `app/planner/schemas.py` 1.2.0 (all `extra="forbid"`, camelCase, the router validates every dict it returns)

- `MoveRequest {woId: int > 0, toIso: str, expectStartIso: str | None = None, confirm: bool = False, dryRun: bool = False}`; `UndoRequest {woId, toIso, expectStartIso: str | None = None, dryRun: bool = False}`.
- `Reason {code, text}`; `UndoRef {woId, toIso, expectStartIso}`; `LabourMove {from (alias), to, rows}`.
- `MovePreview` — the 200 of `/preview` and the `preview` of a `CONFIRM`: `ok code message confirm reasons delta newStart newEnd willPin willUnpin pinnedAfter woId sid title status statusTitle prevStart prevEnd subtasks labourDates labourMoves`.
- `MoveResult` — §5.3's result plus `actor: int`.
- `MoveConfirm {ok: false, code: 'CONFIRM', message, rid, sid, preview: MovePreview}`.
- `WriteError(ApiError)` + `sid: str = ''`, `currentStart: str = ''` — documented on 404 / 409 / 422 / 500.

### 5.5 `app/planner/router.py` 1.2.0

| Route | Gate | 200 | Other |
|---|---|---|---|
| `GET /planner/preview?woId=&to=` | the router's RO | `MovePreview` | 404 · 422 (rule refusal) · FastAPI 422 (missing params) |
| `POST /planner/move` | + `require('planner','RW')` + `require_csrf` | `MoveResult` \| `MoveConfirm` | 403 `NO_RIGHT` / `CSRF` / `NO_IDENTITY` · 404 · 409 `STALE` · 422 · 500 |
| `POST /planner/undo` | the same | `MoveResult` | the same |

One diag line per outcome, the oracle's `_diagWrite` text (CLAUDE.md #10): `[F] move <sid> <from> -> <to> (<delta> d)[ PINNED | pin cleared | still pinned] events=<n>` (`undo …` for undo, `move (dry run) …` when dry); `[F] move <sid> needs confirm: PAST, SPAN`; `[G] move <sid> blocked: <code> - <message>`; `[E] move <sid> FAILED (<code>)` with the driver message as detail. All persist (OD-59: every write and every refusal).

### 5.6 The contract

`main.py` → app **0.7.0** (version line, OD-38); `docs/api/openapi_0_7_0.json` exported from `app.main.app` and committed as a rename of 0.6.0; `web/openapi-ts.config.ts` 1.0.5 points at it; the client regenerated (`moveApiV1PlannerMovePost`-style names are fixed by the route function names, read after the regeneration — never guessed into the web code). `/health` reports `planner` 1.2.0 by reading the module, as now.

### 5.7 Tests (pair rule; counts predicted at the build)

- **`test_planner_move.py` 1.0.0 (new).** Pure: `_field_diff_detail`, `_net_datetime` (midnight, a morning, an afternoon, noon, a one-digit day — P5's own strings), the 990 cap, the collision-safe order, `CONFIRM_REASONS` (SPAN alone asks nothing; SPAN with PAST asks), the plan builder. On the rolled-back connection, read-only and dry only: `load_wo` keys and raw datetimes on a real open WO; `None` for an unknown id; `move_preview` keys; `move_wo(dry_run=True, conn=…)` — `delta`, `newStart`, `weekNo == float(week_no(newStart))`, the `undo` dict, `events == 0`, and the WO's dates unchanged after; `STALE` on a wrong `expectStartIso`; `NO_CHANGE`; `LOCKED_STATUS` on a closed WO; `CONFIRM` with a `PAST` reason and a preview; `NO_IDENTITY` at user 0. Rows are chosen by query in the test, never by a pinned id.
- **`test_planner_api.py` 1.4.0.** The tripwire (OD-111) on every repo writer; `/move` and `/undo` with `dryRun: true` → 200; real refusals over HTTP (404, 409, 422 ×2, `CONFIRM`); an RO principal → 403 `NO_RIGHT`; no `X-Azztec-Request` → 403 `CSRF`; `/preview` 200 / 404; the code → status map through a fake service for `WRITE_FAILED` → 500 and `NO_IDENTITY` → 403.
- **`test_openapi_contract.py` 1.3.0.** The three routes published with their methods; the request bodies forbid extras; 403 / 409 / 422 documented flat; `info.version` 0.7.0.
- **`test_planner_repo.py` 1.0.3** — header only: its `Pair of:` line names `sql.py` / `repo.py` 1.2.0 (the S1h precedent). Its two gates cover the ten new statements by registration.

## 6. DP3b — web

| File | Version | What |
|---|---|---|
| `features/planner/moves.ts` | 1.0.0 new | the calls and their pure helpers: `postMove` / `postUndo` over the generated SDK, catching a network failure; `outcomeOf(status, body)` → `ok` \| `confirm` \| `stale` \| `identity` (NO_IDENTITY, NO_RIGHT) \| `refused` \| `failed`; `whyNotMovable(wo)`, `movedToast(r)` with the pin note and, when the move carried a `SPAN` reason, `· ends <Wed 30 Dec 2026>` (OD-116), `undoneToast(r)` (the oracle's strings otherwise); `applyMove(range, r)` (immutable: `start`, `end`, `weekNo`, `pinned`, `engineDate`); `pushUndo(stack, u)` capped at 10 |
| `features/planner/useWoDrag.ts` | 1.0.0 new | the oracle's pointer drag as a hook: `pointerdown` on the grid wrap (skipping `.hrs`, `input`, `select`, `button`), `pointermove` / `pointerup` / `pointercancel` on the document, 6 px, not-movable → `onRefuse(wo)`; the ghost is the chip's clone in a layer `div` React never renders into, inside `.wm-planner` so the scoped CSS reaches it; `.dragging` on the chip and the root, `.drop` on the target cell unless it is the WO's own day; `elementFromPoint` → `[data-date]`; `cancel()` for Esc; `suppressClick()` true for 50 ms after a drop. Pure helpers exported for the test |
| `features/planner/ConfirmMoveDialog.tsx` | 1.0.0 new | `showConfirm` on the ported `.ovl` / `.dlg`: `MOVE X?`, old → **new** `(+n d)`, title · status, the reasons, the labour moves, the subtask count, Cancel / Move it (focused) |
| `features/planner/Toast.tsx` | 1.0.0 new | the oracle's toast: message, Undo button and `Ctrl+Z` hint when undoable |
| `features/planner/PlannerView.tsx` | 1.2.0 | `canMove` prop (default **false**); at RO the chips' `movable` is mapped false before the grid; the drag, `doMove` / `undoLast` (§3.1, OD-113), busy, the confirm and the toast, the write banner (with ×), Ctrl+Z, Esc ending a drag first, Enter / Esc on the confirm, the poll pause, the click suppression, the hint |
| `features/planner/store.ts` | 1.2.0 | `undo`, `pushUndo`, `popUndo`, `clearUndo` — the stack outlives a visit to WO Maint |
| `features/planner/usePlannerRange.ts` | 1.1.0 | `{ paused }` → `refetchInterval: false` and `refetchOnWindowFocus: false`; `isPlannerRangeKey(key)` for the refetch-everything after a move |
| `features/planner/FiltersRow.tsx` | 1.1.0 | `hint?: string` (default `HINT`) |
| `features/planner/rules.ts` | 1.3.0 | `HINT_RW` = `drag = move · Ctrl+Z = undo · click = select · ← → = navigate · T = today · Esc = clear`; `chipTitle`'s engine-owned line gains `&& wo.movable` — identical on every payload the server sends (an engine-owned PM is movable unless it is locked, and locked is the branch before), and at RO it drops the drag promise |
| `features/planner/planner.css` | 1.2.0 | the oracle's drag rules (`.chip.dragging`, `.ghost`, `.cell.drop`, `.wm-planner.dragging *`), the toast (absolute inside `.wm-planner`, OD-54), the dialog's `.mv` / `.sub` / list rules, the banner's `.x` |
| `routes/planner.tsx` | 1.1.0 | `canMove = !!session && allows(session.rights.planner, 'RW')` from `useSession()` |
| `CLAUDE.md`, `.claude/rules/frontend.md` | 1.1.0 / — | OD-106's two lines (only if OD-106 is signed as proposed) |

**Tests:** `moves.test.ts`, `useWoDrag.test.tsx` (`elementFromPoint` stubbed; `setPointerCapture` is absent in jsdom and wrapped like the oracle's), `ConfirmMoveDialog.test.tsx`, `Toast.test.tsx` new; `PlannerView.test.tsx` 1.3.0 (a drag posts `{woId, toIso, expectStartIso, confirm:false}`; `CONFIRM` → the dialog → Move it → a second post with `confirm:true`; the toast's Undo posts `/undo` with the `undo` dict; at RO no `.mv` and a drag posts nothing), `rules.test.ts` 1.3.0, `usePlannerRange.test.tsx` 1.1.0, `FiltersRow.test.tsx` 1.1.0.

**Untouched:** `WOCard`, `DayCell`, `PlannerGrid`, `DayDialog`, `SelectedWOCard`, `WorkerPanel`, `CapacityBar`, `PlannerHeader`, `lib/dates.ts`.

## 7. Traps

- **Datetimes by range, never by equality** (compat 160, §3.3). The guard and the subtask updates use `[day, day + 1)`.
- **A bound `int` into `DATEADD`** — `CAST(:delta AS int)` keeps the argument an int whatever the driver binds.
- **No colon in any SQL comment; no comment in any SQL string.** The `PG-CONVERT` tag lives in the Python header (the diag precedent).
- **The dialect gate reads the whole file** — the docstring describes the two MSSQL-only spellings without writing them (sql.py 1.0.1's lesson).
- **A refusal returned inside `engine.begin()` commits an empty transaction** (harmless); a write failure must raise inside the block or the partial write commits. The service raises to roll back and turns it into a dict outside the block.
- **`CONFIRM` is a 200 with `ok: false`.** The client discriminates on `ok`, never on the status.
- **The undo's `expectStartIso` is the moved-to date**: a second move before undo makes that undo `STALE` — by design (OD-113 drops it from the stack).
- **The ghost must sit inside `.wm-planner`** (every rule is scoped) and outside React's children (a layer `div` React renders empty).
- **jsdom** has no `elementFromPoint` and no `setPointerCapture`; stub the first, `try` the second.
- **`ruff format --check` is its own gate** (Landmines §A); **Vite dev cannot run in Dropbox** — the browser smoke uses `pnpm build` + `pnpm preview --port 3000 --strictPort` (Landmines §C, §F); **count Vitest through the JSON reporter**.
- **PowerShell 5.1:** no `2>&1` on native calls; `curl.exe` with `-H "X-Azztec-Request: 1"` and a cookie jar on every POST.
- **Never send a real move from a test** — the tripwire fails the test that tries.

## 8. Smoke (outline — exact blocks at the build)

**DP3a** — the API on `127.0.0.1:8010` with `WORKMATE_DB_NAME=dbWorkmate_DP1_Test` for that process only (the DP2a pattern), `curl.exe`, SQL read-backs through `sqlcmd`. The WOs are P6's: **A** 654458, **B** 658823, **C** 657188, **V** 661118; the block first checks each still has the dates P6 read and stops if not.
1. Health: db ok on DP1_Test, app 0.7.0, planner 1.2.0. Before-counts on DP1_Test and dev.
2. AZZ signs in. `GET /preview` for **A** to 29 Dec (+7) → 200, `SPAN` among the reasons and `confirm: false` (OD-116) — unless A's two labour rows sit on two days, when `LABOUR_MULTI` asks (the block reads A's labour days first and expects whichever is true).
3. `POST /move {dryRun:true}` → 200, `dryRun: true`, `events: 0`; A's dates unchanged in SQL.
4. `POST /move` for real (with `confirm` only if step 2 asked) → 200; SQL: the start on 29 Dec 00:00, the end on 30 Dec **15:18** (the time kept), `Week_No` = the returned `weekNo`; both `'L'` rows moved +7; the rows `Rescheduled` (ISO text) and `Update` ×2 in Workmate.NET's format (OD-117), each with `server_name 'SaaS'`, `Source_Form 'Planner'`, user 21. (No RST row can exercise the subtask shift — P4.)
5. The same move again with the old `expectStartIso` → 409 `STALE`.
6. `POST /undo` with the returned `undo` → 200; SQL: every date back where step 2 found it; `Rescheduled (undo)` rows.
7. PM **B**: move → `willPin`, a `WO_N_Plan` row (`Pinned 'Y'`, `Prev_Start` = B's start, `Server_Name 'SaaS'`), a `Pinned` row; undo → `willUnpin`, `Pinned 'N'`, the row kept, an `Unpinned` row.
8. Refusals and asks: closed **C** → 422 `LOCKED_STATUS`; A to its own day → 422 `NO_CHANGE`; an unknown id → 404; A to a past day without `confirm` → 200 `CONFIRM` with `PAST`; Active **V** to a December day → 200 `CONFIRM` with `ACTIVE`; neither ask writes an event row.
9. No `X-Azztec-Request` → 403 `CSRF`. STORESWM: `/move` → 403 `NO_RIGHT`; `/preview` → 200.
10. `Diag_Log` on DP1_Test: `[F] move` / `[F] undo` lines with `events=`, `[G]` for the refusals, no `[E]`. Dev's three counts unchanged.

Then commit and tag `dp3a-moves-api-1.0.0`.

**DP3b** — `pnpm build` + `pnpm preview` on :3000, the API on :8000 against DP1_Test. AZZ: drag A one day → the toast `Moved A → … (+1 d)` with Undo, the chip in its new cell → Undo → back; move again → Ctrl+Z → back; drag A to a past day → the dialog with `PAST` → Cancel (nothing posted) → again → Move it → Ctrl+Z; drag B → the pin glyph → Ctrl+Z → no glyph; with Done showing, drag C → `C is closed - it does not move`; Esc mid-drag ends it with nothing posted. STORESWM: no grab cursor, the RO hint, a drag posts nothing. The server: the event rows and diag lines for exactly those moves, every date back where it started, no `[E]`, dev unchanged; the footer's `actor #21` once loaded (raw log 11-07 §9). Then commit and tag `dp3b-moves-web-1.0.0`.

## 9. Acceptance

- Backend: the predicted count, exit 0; `ruff check` and `ruff format --check` clean. Frontend: the predicted count per file through the JSON reporter, exit 0; `pnpm lint` clean; `pnpm build` exit 0.
- Both smokes PASS with every move undone; no `[E]`; dev `dbWorkmate` untouched.
- `openapi_0_7_0.json` committed as a rename; the client regenerated from it, not by hand.

## 10. What this hands DP4

- The notice gains one line: planner moves are recorded in `WO_Event_History` (`server_name 'SaaS'`, `Source_Form 'Planner'`) and in `Diag_Log`, not in Workmate.NET's `Query_Log`; a moved PM keeps a `WO_N_Plan` row.
- `actor #21` → the person's name in the filters row, now that identity exists (OD-34's "until identity" condition is met) — DP4 or after, not DP3.
- The estimate (OD-105) and Unpin (S3) as the next planner writes, if wanted.

## 11. Changelog

- 1.0.1 (2026-11-07) Signed 🤙 with Block DP3-E's output. §3.5 filled (P0–P6). OD-116 (SPAN shown, never asked — the service decides, `rules.py` untouched) and OD-117 (the `Update` rows in Workmate.NET's date format) added, both the recommended answers to the two questions the probe raised. §5.1: the pin insert as the oracle wrote it (P1); the labour grouping kept (P4). §5.3: `CONFIRM_REASONS`, `_net_datetime`. §5.7: their tests. §6: the toast's end note. §8: the smoke's WOs named (A 654458, B 658823, C 657188, V 661118); the subtask shift cannot be exercised on RST data. No other OD moved.
- 1.0.0 (2026-11-07) Initial, from the DP3 audit: the oracle's write side read in `workmate_planner_code_v1_3_1.py` (752–1190), `workmate_planner_api_code_v1_8_3.py` (659–758, 995–1000; identical to the 1.9.1 export for these functions) and `Planner_v1_8_1.html`; the SaaS bases read from the repo at `b4c4e65`. OD-104…OD-115 proposed. §3.5 waits on Block DP3-E.
