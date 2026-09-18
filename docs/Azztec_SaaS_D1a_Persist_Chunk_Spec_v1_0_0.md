# Azztec SaaS — D1a Forensic Persist Chunk Spec

**File:** Azztec_SaaS_D1a_Persist_Chunk_Spec_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-19 · **Author:** Adriaan
**Status:** Draft — **OD-55…OD-61 need 🤙 before anything is built.** The box evidence is read (§2.4, Block D1-E pasted 2026-09-19), so the gate is the only thing outstanding. This is the first slice that writes rows to RST: `dry_run` first, Marker Law on the smoke's own row.
**Target path:** `docs/Azztec_SaaS_D1a_Persist_Chunk_Spec_v1_0_0.md` (+ project knowledge)
**Parent:** `Azztec_SaaS_D1_Forensic_Trail_Audit_v1_0_1.md` (the audit, §6.1) · Architecture D-8 · log 2026-09-19 §10. **Slice D1a is not architecture decision D-1.**
**Source of truth:** `workmate.diag` 1.3.0 and the four `Workmate/Diag/*` named queries; KT's `fn_Diag_UserTrail`, `vw_Diag_Problems` and `vw_Diag_WhoIsOn`, read from `dbWorkmate_KT` today (§2.3); `dbo.Diag_Log` on RST as `0001` landed it (§2.4). From the PK cards, not memory: `diag.py` 1.1.1, `main.py` 1.0.4, `deps.py` 1.0.0, `config.py` 1.1.0, `db.py` 1.0.0, `.env.example` 1.0.1, `planner/router.py` 1.1.1, `test_smoke` 1.1.1, `test_diag_wiring` 1.0.1, `test_openapi_contract` 1.0.0, `test_planner_repo` 1.0.2.
**Closes:** OD-47 (as OD-55). **Does not close:** item 28 (the browser route) — D1b.
**Writes:** `dbo.Diag_Log` on `dbWorkmate` — inserts (the writer, the self-test marker) and deletes (the purge). No other table. No frontend file, **no contract change** (the new routes are `include_in_schema=False`, so `openapi_0_4_0.json` is untouched and `pnpm gen:api` is not run).
**Signed decisions in force:** D-3 (portable SQL with `-- PG-CONVERT:` tags, `dbo.`, `COALESCE`, `CURRENT_TIMESTAMP`), D-8, OD-12 (the actor seam), OD-15 (the flat error body carries `rid`), OD-19 / OD-20 (`/health` reports where records persist and whether anything prints), OD-42 (no database routines cross from KT), Ways of Working §2 (the constant is bumped with the header or `/health` lies) and §6 (suites bare, gate on `$LASTEXITCODE`).

---

## 1. Scope — thirteen cards, one `.env` hand step, then stop

Switch the diagnostics on: every `[F]`/`[G]`/`[E]` line that matters reaches `dbo.Diag_Log` with the person on it, and give us three ways to read it back — a PowerShell script for the smoke, two dev-only routes, and the self-test that proves the path end to end.

| # | Deliverable | Target | Version | Change |
|---|---|---|---|---|
| 1 | `Azztec_SaaS_app_core_diag_v1_2_0.py` | `backend/app/core/diag.py` | 1.1.1 → **1.2.0** | the OD-55 fill, `PERSIST_SQL` set, one writer thread with a bounded queue and batching (OD-57), counters and a rate-limited stdout `[E]` on failure, `redact()` (OD-58), the read de-dupe (OD-59), `flush()` |
| 2 | `Azztec_SaaS_test_diag_persist_v1_0_0.py` | `backend/tests/test_diag_persist.py` | **new** | pair of 1 — zero DB |
| 3 | `Azztec_SaaS_app_diag_sql_v1_0_0.py` | `backend/app/diag/sql.py` | **new** | INSERT, TRAIL, PROBLEMS, WHOISON, USERS, PURGE_BATCH, PURGE_COUNT — portable, tagged |
| 4 | `Azztec_SaaS_app_diag_repo_v1_0_0.py` | `backend/app/diag/repo.py` | **new** | `trail()`, `problems()`, `who_is_on()`, `users()`, `purge(days, dry_run)` |
| 5 | `Azztec_SaaS_app_diag_router_v1_0_0.py` | `backend/app/diag/router.py` | **new** | `GET /_diag/trail`, `/_diag/whoison`, `/_diag/users`, `POST /_diag/purge` — dev-only, out of the schema |
| 6 | `Azztec_SaaS_test_diag_trail_v1_0_0.py` | `backend/tests/test_diag_trail.py` | **new** | pair of 3–5 — statements compile with no DB; the round trip is DB-gated |
| 7 | `Azztec_SaaS_app_core_deps_v1_1_0.py` | `backend/app/core/deps.py` | 1.0.0 → **1.1.0** | the resolved actor also lands on `request.state.actor` |
| 8 | `Azztec_SaaS_app_main_v1_1_0.py` | `backend/app/main.py` | 1.0.4 → **1.1.0** | the outcome line carries the actor and persists by policy; lifespan starts the writer and the daily purge and flushes on shutdown; the self-test reads its marker back; `/health` gains `diagPersist`; the diag router is mounted |
| 9 | `Azztec_SaaS_app_core_config_v1_2_0.py` | `backend/app/core/config.py` | 1.1.0 → **1.2.0** | `diag_persist`, `diag_purge` |
| 10 | `Azztec_SaaS_dotenv_example_v1_1_0.txt` | `backend/.env.example` | 1.0.1 → **1.1.0** | the two switches; the dev-user comment names Azzmax (21) |
| 11 | `Azztec_SaaS_scripts_Show_DiagTrail_v1_0_0.ps1` | `scripts/Show-DiagTrail.ps1` | **new** | the trail-read rule's reader — ASCII only, works when the app will not boot |
| 12 | `Azztec_SaaS_test_smoke_v1_1_2.py` | `backend/tests/test_smoke.py` | 1.1.1 → **1.1.2** | **only if** `test_health_shape_and_db` asserts an exact key set — read at build time, never re-emitted unread |
| 13 | `Azztec_SaaS_D1a_Persist_Chunk_Spec_v1_0_0.md` | `docs/` | **new** | this file |

**Hand step, not a card:** `backend\.env` — `WORKMATE_DEV_USER_ID=1` → **`21`** (OD-56). `get_settings()` is `lru_cache`d, so the server restarts.

**Untouched:** every `app/planner/*` file, the whole `web/` tree, `alembic/`, every other table.

**Not in this slice:** the browser error route and the viewer page (D1b, item 28); rights or roles on the trail (the auth slice — until then dev-only, OD-61); the Night Shift morning report (its own slice, after this one); shipping KT's three routines as routines (OD-42 — they are ported as queries).

## 2. Evidence

### 2.1 The oracle — `workmate.diag` 1.3.0

Four calls, each persisted asynchronously and streamed to the live console: `log` → Tier `S`, `forensic` → `F` / `info`, `guard` → `G` / `warn`, `error` → `E` / `error` with the traceback captured into `Detail`. Attribution comes from the Perspective session (`Session_Id`, `Wm_User_Id` NULL when ≤ 0, `Site_Code`). A call without a session persists with no user — **18,406 of KT's 69,656 rows (26 %)** are exactly that. Its own changelog records the failure this slice must not repeat: the live gateway's table stayed empty because a lineage without persistence was deployed, and every persist path swallows its errors by design.

### 2.2 KT's reader, read today

| Routine | Shape |
|---|---|
| `fn_Diag_UserTrail(@userName varchar(40), @minutesBack int)` | `Diag_Log` LEFT JOIN `Users`, `RTRIM(User_Name) LIKE '%…%' OR RTRIM(Short_User_Id) LIKE '%…%'`, `Logged_At >= DATEADD(minute, -@minutesBack, CURRENT_TIMESTAMP)` — already carrying `-- PG-CONVERT: interval` |
| `vw_Diag_Problems` | the same join, `Tier IN ('E','G')`, `Logged_At >= DATEADD(day, -1, CURRENT_TIMESTAMP)` |
| `vw_Diag_WhoIsOn` | last 30 minutes grouped by user: `Last_Seen`, `Rows_30min`, `Errors` (`Tier='E'`), `Blocked` (`Tier='G'`) |

They are ported as **queries in `sql.py`**, not as routines (OD-42), with the same tags. One deliberate difference: the SaaS trail takes a **user id**, not a name — the id is what the actor seam already has, and a name `LIKE` would match two people.

### 2.3 `Workmate/Diag/Diag_Trail` 1.0.1 (the viewer's query)

`TOP 500`, newest first, `userId = 0` means everyone, `problemsOnly` as a bit, the user rendered `Name (id)`. D1a's `TRAIL` keeps all four behaviours; the `Name (id)` rendering moves to the client in D1b.

### 2.4 `dbo.Diag_Log` on RST, as `0001` landed it — Block D1-E, 2026-09-19

| Column | Type | Null |
|---|---|---|
| `Diag_Id` | `int` identity | no |
| `Logged_At` | `datetime2(3)` (7 bytes) | no |
| `Session_Id` | `varchar(64)` | no |
| `Wm_User_Id` | `int` | **yes** |
| `Site_Code` | `varchar(8)` | yes |
| `Source` | `varchar(64)` | no |
| `Tier` | `char(1)` | no |
| `Msg_Level` | `varchar(8)` | no |
| `Message` | `nvarchar(1000)` (2,000 bytes) | no |
| `Detail` | `nvarchar(max)` | yes |

Indexes `PK_Diag_Log` (clustered), `IX_Diag_Log_LoggedAt`, `IX_Diag_Log_User_LoggedAt`. **0 rows.** No `DIAG%` row exists in `System_Configuration`, so the retention default applies (OD-60). The dev actor is `1` and `WORKMATE_ENV=dev`. **Azzmax is `User_Id 21`** — `User_Name 'Azzmax logon'`, `Short_User_Id 'AZZ'`, `AD_Login_ID 'AZZ'`, `Active 'Y'`, and it is the only match.

### 2.5 The SaaS as it stands

- `diag.py` 1.1.1 — `log()` always prints one JSON line; `PERSIST_SQL = None`, and `_persist` binds only `level, source, message[:990], detail, actor, rid`: **`Session_Id`, `Tier` and `Msg_Level` are unbound and all three are NOT NULL**, `actor 0` would land as `0` rather than NULL, a **thread per row** takes a pooled connection each, and every exception is swallowed.
- `main.py` 1.0.4 — the middleware mints `rid`, logs `[E] … crashed` on an exception and one outcome line per `/api` call tagged by status, `persist=False`, **with no actor**; `X-Request-Id` on every response. `lifespan` logs `startup db=…` and `startup tz=…`, and disposes the engine on the way out. `/health` reports `diag` (persist mode) and `diagWired`.
- `deps.get_current_actor(request)` — dev override or `[G] no identity` + 401. It never writes to `request.state`.
- `db.py` — `rows / scalar / execute / insert_returning_id / config_value(conn, key, default) / db_error / ping`, all taking a `Connection`.
- `test_smoke` 1.1.1 asserts `diag in ('stdout','diag_log')` and `diagWired is True`, and that `versions` match the modules. `test_openapi_contract` reads `app.openapi()`, so a route out of the schema changes nothing. DB-gated tests skip through a module-scoped `conn()` fixture that calls `pytest.skip(f"database unreachable: …")` — the two skips in today's 194 / 2.
- The planner's own lines: `[G] range refused` and `[F] range … in N ms`, both with the actor. The web polls `/range` every 60 s while the tab is in front.

## 3. The changes, exactly

### 3.1 `app/core/diag.py` 1.2.0 (card 1)

`log()` keeps its signature and its stdout line **unchanged** — 1.1.1's behaviour is what `test_diag_wiring` pins. What changes is what happens after the line is printed:

```python
PERSIST_SQL = sql.INSERT          # from app.diag.sql, set at import; None disables persistence
def record(level, message, detail, actor, source, request_id) -> dict   # the row as it will be written
def redact(value: Any) -> Any                                          # OD-58, at any depth
def should_persist(level, source, message, actor, dedupe_key) -> bool   # OD-59
def start_writer() / flush(timeout: float = 2.0) / counters() -> dict    # OD-57
```

**The row (OD-55).** `Tier` = the tag; `Msg_Level` = `{F: 'info', G: 'warn', E: 'error', S: 'info'}`; `Source` = the caller's `source`; `Session_Id` = the request id, `''` for boot and background lines; `Wm_User_Id` = the actor or **NULL when 0**; `Site_Code` NULL; `Message` cut to **1000** characters (`nvarchar(1000)`, not the 2,000 bytes `sys.columns` reports); `Detail` = redacted JSON cut to 8,000; `Logged_At` = `CURRENT_TIMESTAMP` in the statement, so the database clock stamps it. **Every field is cut to its column before it is queued**, so one long value cannot fail a whole batch.

**The writer (OD-57).** One daemon thread, one `queue.Queue(maxsize=10_000)`, batches of up to 100 rows or 1 second, `executemany` on its own connection from the engine. Overflow drops the newest row and counts it, and the next written row's `Detail` carries `{"dropped": n}`. A failed batch is counted, printed **once** to stdout as `[E] diag persist failed` (then every hundredth) and retried once before the batch is dropped. `counters()` feeds `/health`. `flush()` drains within its timeout at shutdown.

**Volume (OD-59).** `[G]` and `[E]` always persist. Any line whose `source` names a write persists. A read's `[F]` persists once per `(actor, message-shape)` per 15 minutes — a small in-process LRU, so the 60 s planner poll stops costing 480 rows per person per day. Everything still prints.

### 3.2 `app/diag/sql.py` 1.0.0 (card 3)

Module-level statements, the planner's `sql.py` shape, `dbo.`-qualified, named binds, `-- PG-CONVERT:` tags where a dialect differs:

- `INSERT` — the ten columns above, `CURRENT_TIMESTAMP` for `Logged_At`.
- `TRAIL` — `TOP 500` (`-- PG-CONVERT: LIMIT`), newest first, `WHERE (:userId = 0 OR L.Wm_User_Id = :userId) AND (:problemsOnly = 0 OR L.Tier IN ('E','G')) AND L.Logged_At >= DATEADD(minute, -:minutesBack, CURRENT_TIMESTAMP)`, LEFT JOIN `Users` for `User_Name` / `Short_User_Id`, `RTRIM` on both (`char` padding).
- `PROBLEMS` — `vw_Diag_Problems`' body as a query, the window as a bind.
- `WHOISON` — `vw_Diag_WhoIsOn`' body, the 30 minutes as a bind.
- `USERS` — the distinct users with rows in the window, `Name (id)` left to the caller.
- `PURGE_COUNT` / `PURGE_BATCH` — `DATEADD(day, -:days, CURRENT_TIMESTAMP)` (`-- PG-CONVERT: interval`), the delete batched by `Diag_Id` (`≤ 5,000` rows a pass).

### 3.3 `app/diag/repo.py` 1.0.0 · `router.py` 1.0.0 (cards 4, 5)

`repo` returns plain dicts through `db.rows`, cleaned by `db._clean` as the planner's does (`Decimal` → int, `char` → `RTRIM`). `purge(conn, days, dry_run=True)` returns `{"cutoffDays": days, "rows": n, "deleted": 0|n, "dryRun": bool}` and loops the batch until it deletes nothing.

`router` mounts under the existing `/api/v1` with `include_in_schema=False` on every route and a `_dev_only()` dependency that raises 404 outside `WORKMATE_ENV=dev` (OD-61):

| Route | Query | Returns |
|---|---|---|
| `GET /_diag/trail` | `userId=0`, `minutesBack=30`, `problemsOnly=false` | `{ok, rows: [...], count}` |
| `GET /_diag/whoison` | `minutesBack=30` | `{ok, rows}` |
| `GET /_diag/users` | `minutesBack=1440` | `{ok, rows}` |
| `POST /_diag/purge` | `days` (default from config), `dry_run=true` | the purge dict |

### 3.4 `app/core/deps.py` 1.1.0 · `app/main.py` 1.1.0 (cards 7, 8)

`get_current_actor` sets `request.state.actor` before returning, and on the 401 path sets `0`. The middleware reads `getattr(request.state, "actor", 0)` **after** `call_next` — the dependency has run by then — and passes it to `diag.log`, with `persist=` decided by the OD-59 policy (`≥ 400`, `≥ 2,000 ms`, or a non-GET method). `lifespan` calls `diag.start_writer()` before the first line and `diag.flush()` on the way out, and starts the daily purge task when `WORKMATE_DIAG_PURGE` is true (first run five minutes after boot, then every 24 h, days from `System_Configuration` via `db.config_value`, default 60 — `dry_run=False` there, and one `[S]` row per run with the count). `/_diag/self-test` writes its marker, flushes, **reads it back by `rid`** and returns `{"persisted": true|false, "diagId": n}`. `/health` gains `diagPersist` — `{mode, queued, written, failed, dropped, lastOkAt, lastError}` — and `versions` gains `diagApi`.

### 3.5 `config.py` 1.2.0 · `.env.example` 1.1.0 (cards 9, 10)

`diag_persist: bool = True` (`WORKMATE_DIAG_PERSIST`) and `diag_purge: bool = True` (`WORKMATE_DIAG_PURGE`; false on every worker but one). The example file's dev-user comment becomes `21 = Azzmax logon (AZZ) - Andrew's administrator login, the test identity (OD-56)`.

### 3.6 `scripts/Show-DiagTrail.ps1` 1.0.0 (card 11)

`-UserId 21 -Minutes 15 [-ProblemsOnly] [-Server localhost] [-Database dbWorkmate]`, `sqlcmd -W -s "|"` straight at the table, newest last so a paste reads in order, `Detail` cut to 300 characters with a `…` marker. ASCII only. It is what the trail-read rule runs after every test from here on.

## 4. Traps

1. `sys.columns.max_length` is **bytes**: `Message` is `nvarchar(1000)`, not 2,000 characters, and `Logged_At`'s 7 bytes mean `datetime2(3)`.
2. Three columns are NOT NULL that 1.1.1 never binds. A single missed bind fails every row — and silently, which is KT's own recorded failure.
3. The writer must never take a request's connection, and must never raise into the caller. It also must never log its own failure **through itself** — that line goes to stdout only.
4. `fastapi dev` boots the app twice, so two writers exist in dev. The purge must not: guard it so only one run happens per interval per process, and set `WORKMATE_DIAG_PURGE=false` on every worker but one in production.
5. The middleware runs before the dependencies resolve, so read `request.state.actor` **after** `call_next`, never before.
6. Lines with no actor (health, 404s, boot) must write NULL, not 0 — `0` is not a `Users.User_Id` and would corrupt every per-person query.
7. `Logged_At` is the **database** clock while the stdout `ts` is the app's. On one box they agree; say so in the header rather than letting a reader assume.
8. Keep the new routes out of the OpenAPI document or `test_openapi_contract` fails and the generated client grows a dev-only API.
9. The purge deletes. `dry_run=True` first, always; batch it so no single statement locks the table; never delete by date range without the batch cap.
10. Marker Law: the smoke's self-test row is deleted by its `Diag_Id` at the end of the DB-gated test, and only that row.
11. `db.config_value` returns a string — `int(value or 60)`, and a junk value falls back to 60 rather than raising.
12. Do not change `log()`'s stdout line: `test_diag_wiring` 1.0.1 pins it, and the console trail is what the rule reads until this slice lands.

## 5. Test plan — predicted

| File | Cases | What |
|---|---|---|
| `tests/test_diag_persist.py` (card 2) | 14 | the fill map for F/G/E/S · `Source`, `Session_Id` cut to 64 · actor 0 → NULL · `Message` cut to 1000 · `Detail` redaction at depth and its 8,000 cut · non-secret keys survive · de-dupe inside 15 minutes, and a different shape is not deduped · overflow drops and counts, and the count reaches the next row · a failed batch counts, prints once to stdout, is not re-persisted · `flush()` drains · `persist_mode()` · the stdout line byte-identical to 1.1.1 |
| `tests/test_diag_trail.py` (card 6) | 10 | every statement compiles and names its binds · `TRAIL` honours `userId=0`, `problemsOnly` and the window · `PROBLEMS` is `Tier IN ('E','G')` · `WHOISON` groups by user · `PURGE_BATCH` caps at 5,000 and carries its tag · **DB-gated:** a marker row inserts, the trail reads it back by `rid`, `problems()` finds its `[E]` twin, `who_is_on()` lists its actor, `purge(dry_run=True)` counts without deleting, and the marker is removed by `Diag_Id` |
| `tests/test_smoke.py` 1.1.2 (card 12) | +2 | `/health` reports `diagPersist` with the counter keys; the self-test says whether its marker persisted |

**Predicted: backend `218 passed, 2 skipped`** (194 + 14 + 10, of which the DB-gated six skip when the database is unreachable — on this box they run), exit 0. **Frontend unchanged: 205 passed in 15 files** — no `web/` file is touched, so it runs once to prove that.

## 6. Open decisions — 🤙 required

| ID | Question | Proposal |
|---|---|---|
| **OD-55** | How the SaaS fills `Diag_Log` | **OD-47, closed:** the mapping in §3.1, measured against the real DDL (§2.4). Every field cut to its column before queueing |
| **OD-56** | The dev actor | **`WORKMATE_DEV_USER_ID=21`** — `Azzmax logon` (AZZ), Andrew's administrator login, as stated 2026-09-16. Background jobs write NULL. `1` (`SYS_USER`) stays the documented fallback for any install with no agreed login. One login per person on Redstag's server, which is the auth slice |
| **OD-57** | Writing at scale, and noticing a dead log | One daemon writer, a bounded queue of 10,000, batches of ≤ 100 rows or ≤ 1 s, counters on `/health`, one stdout `[E]` per hundred failures, and a self-test that reads its own marker back. Rejected: a thread per row (1.1.1), which takes a pooled connection per line |
| **OD-58** | What `Detail` may carry | Never secrets: `password`, `passwd`, `pwd`, `secret`, `token`, `authorization`, `cookie`, `api_key` → `"***"` at any depth, before queueing. Writes log field-level summaries, never raw bodies |
| **OD-59** | Volume | Every `[G]` and `[E]`; every write outcome; a read's `[F]` once per actor per shape per 15 minutes; the per-request outcome line only at status ≥ 400, ≥ 2,000 ms, or a non-GET. The console still prints everything |
| **OD-60** | The purge | In the app: a lifespan task, first run five minutes after boot then every 24 h, only where `WORKMATE_DIAG_PURGE=true`; days from `DIAG_RETENTION_DAYS` (absent → **60**, and it is absent today); the cutoff as `DATEADD(day, -:days, CURRENT_TIMESTAMP)` with a `-- PG-CONVERT: interval` tag — **changed from the audit**, which proposed computing the cutoff in Python: KT's own three routines do it this way and so does the rest of our SQL (D-3). Batches of ≤ 5,000, `dry_run` on the first run of any install, one `[S]` row per run |
| **OD-61** | Who may read the trail | Dev-only: the four routes answer only when `WORKMATE_ENV=dev` and **404** otherwise, and stay out of the OpenAPI contract until D1b. The auth slice replaces the check with an administrator role — the trail is personal information |

## 7. Smoke

**1 — drop.** The S1k shape: sources `Test-Path`ed in Downloads first with the normalised-name fallback; `New-Item -Force backend\app\diag`; copy; every target printed with its size; the header `Version:` against `__version__` on cards 1, 3, 4, 5, 7, 8, 9; `git status --short -uall` (predicted 13 paths).

**2 — format and lint.** `cd backend; uv run ruff format .; uv run ruff check .` → clean.

**3 — backend suite, bare.** `uv run pytest; "$LASTEXITCODE"` → **218 passed, 2 skipped**, exit 0. Then `cd ..\web; pnpm test` → 205 in 15, untouched.

**4 — the actor swap.** `backend\.env`: `WORKMATE_DEV_USER_ID=21`, verified with `Select-String`, then the server restarts (settings are cached).

**5 — boot and prove the path.** Backend in its own window, stdout tee'd as before. Then:
- `Invoke-RestMethod http://localhost:8000/api/v1/health | ConvertTo-Json -Depth 4` → `diag: "diag_log"`, `diagWired: true`, `diagPersist.mode: "diag_log"`, `written: 0`, `failed: 0`, `dropped: 0`.
- `Invoke-RestMethod http://localhost:8000/api/v1/_diag/self-test | ConvertTo-Json -Depth 4` → `persisted: true` with a `diagId` — the marker written and read back.
- Browse `/planner`, change mode once, leave it a minute.
- `scripts\Show-DiagTrail.ps1 -UserId 21 -Minutes 15` → the boot lines with no user, then the planner's `[F] range …` rows **carrying user 21**, one row per distinct window rather than one per poll, and no `[G]`/`[E]`.
- `Invoke-RestMethod -Method Post "http://localhost:8000/api/v1/_diag/purge?dry_run=true" | ConvertTo-Json` → `rows: 0` against a 60-day cutoff, `deleted: 0`.
- `/health` again → `written` greater than zero, `failed: 0`, `dropped: 0`.

**6 — the trail read** (the rule, now from the table): the `Show-DiagTrail` output pasted verbatim and compared with the predicted trail above.

**7 — commit.** `git add -A`, `git commit -m "D1a forensic persist - Diag_Log writer, trail routes, purge"`, tag **`d1a-persist-1.0.0`**.

## 8. Acceptance

- Thirteen cards, one `.env` line, nothing else in the tree (13 staged paths plus `.env`, which is gitignored).
- Rows reach `dbo.Diag_Log` with the person on them, the request id in `Session_Id`, and no row carrying user `0`.
- A broken persist path is visible in `/health` and in one stdout line — never silent.
- The trail, who-is-on and purge answer in dev and 404 outside it; the OpenAPI document is byte-identical.
- Backend 218 / 2, frontend 205 / 15, ruff clean, all bare, all read.
- The purge's first run is a dry run, and the only row the smoke deletes is its own marker.

## 9. Consequences

- **Unblocks** the trail-read rule against the table rather than the console, the Night Shift morning report (its `[E]` section and pack results both read this table), and W2/S2b — the first slices to write business data, which will be traceable from the day they land.
- **Doc set:** Architecture D-8 (persist on, the writer, the fill, the volume rule, the purge) and D-5 (the dev actor is 21); Landmines (`max_length` is bytes; NOT NULL columns a writer must bind; the middleware reads the actor after `call_next`; `fastapi dev` runs two writers); Ways of Working (the trail rule, already queued); Index and Port Spec (OD-55…OD-61, slice D1a done, D1b next).
- **Still open after this:** item 28 and the viewer (D1b); rights on the trail (auth); the morning report's mail route, which needs one answer from Adriaan.

## 10. Changelog

- 1.0.0 (2026-09-19) Initial. Written after Block D1-E: the real `Diag_Log` DDL, Azzmax as `User_Id 21`, no `DIAG%` config row, and KT's three routines read in full. OD-60 changed from the audit — `DATEADD` with a `PG-CONVERT` tag, matching KT's own routines and D-3.
