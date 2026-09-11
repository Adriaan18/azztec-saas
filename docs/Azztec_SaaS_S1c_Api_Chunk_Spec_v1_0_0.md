# Azztec SaaS — S1c API Chunk Spec (`/range`)

**File:** Azztec_SaaS_S1c_Api_Chunk_Spec_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-11 · **Author:** Adriaan
**Status:** Draft — awaiting 🤙 before the build
**Slice:** S1c — `service.range_data` + `schemas.py` + `deps.py` + `router.py` (`GET /api/v1/planner/range`) + `tests/test_planner_api.py`
**Sits on:** `rules.py` 1.0.0 (S1a) · `sql.py` 1.0.1 + `repo.py` 1.0.0 (S1b) · `main.py` 0.1.0, `db.py` 1.0.0, `diag.py` 1.0.0, `config.py` 1.0.0 (S0)
**Parent spec:** `Azztec_SaaS_Planner_Port_Spec_v1_0_0.md` §3 (contract), §4 (routes), §6 (S1), §8 (tests)
**Source of truth:** `workmate_planner_code_v1_3_1.py` `rangeData` (src 711–746) · `workmate_planner_api_code_v1_8_3.py` `_range` (src 571–594)

---

## 1. Scope

Read-only. One route. Nothing writes, nothing needs `dry_run`.

**In:** the window guard, the four fetch calls, the pure assembly, the JSON contract, the actor stub, the 400/401/405 behaviour, the `[F]`/`[G]` lines, and the test pair.

**Out:** `/preview`, `loadWO`, `movePreview` (OD-13 → S2) · real JWT (S2, replaces the stub) · React (S1e) · the `.gitignore` symlink fix and the API 404 handler (queued corrections, OD-17) · anything that writes.

## 2. Decisions carried in

| ID | Signed | What it means here |
|----|--------|--------------------|
| OD-6 | 2026-09-10 | `today` is the only tz point; `WORKMATE_TZ` defaults `Pacific/Auckland`; `tzdata` is load-bearing on Windows |
| OD-7 | 2026-09-11 | dev actor comes from `.env` `WORKMATE_DEV_USER_ID`, not `System_Configuration` |
| OD-10 | 2026-09-11 | `libVersion` = `rules.__version__` (1.0.0), not `>= '1.3.1'` |
| OD-12 | 2026-09-11 | `deps.get_current_actor()` is the interim identity seam; swapped for JWT in S2 |
| **OD-14** | **2026-09-11** | envelope keeps `ok`, `apiVersion`, `actor`, `ms`; **`gate` is dropped** (retired with the sid gate) |
| **OD-15** | **2026-09-11** | error body is flat `{ok:false, code, message}` per D-9, app-wide. The legacy UI banner degrades to `HTTP 400` on `/range` failure — accepted |
| **OD-16** | **2026-09-11** | `service.WindowError(ValueError)` carrying `code='BAD_WINDOW'`; the router catches the **type**, never a string |
| **OD-17** | **2026-09-11** | the API 404 handler stays out; the suite keeps its 1 known red until `pnpm build` |

Verified from the box on 2026-09-11 (signature dump): `repo` has **no** `workers()`, so the service composes it. `repo.clear_caches()` exists. `rules` carries `COLOURS`, `STATUS_TITLES` (9 entries), `PORTED_FROM`, and no write-side constants.

## 3. `app/planner/service.py` 1.0.0

One public function this slice. Plain `def`, sync, takes a `Connection` (D-2: never DB I/O in `async def`).

### 3.1 Signature

```python
class WindowError(ValueError):
    code = "BAD_WINDOW"

def range_data(conn: Connection, from_iso: str, to_iso: str) -> dict[str, Any]:
```

Returns a plain dict in the Ignition shape. The router validates it and adds the envelope. The service never builds Pydantic models, never logs the request outcome, and never raises anything but `WindowError` for a bad window.

### 3.2 Algorithm — ordered, 1:1 with src 711–746

1. `from_d = rules.parseIso(from_iso)`, `to_d = rules.parseIso(to_iso)`.
2. Guard: `if from_d is None or to_d is None or from_d > to_d:` → `raise WindowError("bad window %r..%r (expected yyyy-MM-dd, from <= to)" % (from_iso, to_iso))`. `from_d > to_d` replaces `system.date.isAfter`; `parseIso` is calendar-strict (09-11 §6) so `2026-02-31` lands here, not on 3 March.
3. Guard: `if (rules.civilDays(rules.iso(from_d), rules.iso(to_d)) or 0) > 400:` → `raise WindowError("window too wide (max 400 days)")`. **Exactly 400 passes**, 401 does not.
4. `pin_table = repo.pin_table_exists(conn)` — cached per engine; called for the `pinTable` contract key.
5. `wos = repo.fetch_wos(conn, from_d, to_d)` — inclusive dates in, `_exclusive_end` handled inside the repo.
6. `labour = repo.fetch_labour(conn, from_d, to_d)`.
7. `wlist, teams = rules.buildWorkers(repo.fetch_skill_rows(conn))` — this is the `workers()` composition; it lives here because `repo.workers()` does not exist.
8. **Index the labour once** (§3.3), then per WO: `wo['hrs']`, `wo['hrsSrc'] = rules.hoursFor(wo, mine)` and `wo['assigned'] = rules.assignedFor(wo, mine)`.
9. Counts: `wo` = `cat` in `('WO','REQ')`, `pm` = `PM`, `done` = `DONE`, `total` = `len(wos)`.
10. Assemble the dict in src key order (§3.5).

### 3.3 The labour index — the one deliberate deviation

`rules.hoursFor(wo, labourRows)` and `rules.assignedFor(wo, labourRows)` each scan the whole list and filter on `woId` internally. `rangeData` calls both per WO, so the Ignition source is O(wos × labour). KT's dataset hides it; RST does not — 169,678 headers across 2003→2026 means a 400-day window is roughly 8,000 WOs, each walking every labour row.

Fix, without touching `rules.py`:

```python
by_wo: dict[int, list[dict[str, Any]]] = {}
for r in labour:
    by_wo.setdefault(int(r.get("woId") or 0), []).append(r)
...
mine = by_wo.get(int(wo.get("id") or 0), ())
h, src = rules.hoursFor(wo, mine)
```

Both functions filter on `woId` anyway, so passing the pre-filtered subset is **provably identical output**, O(wos + labour) total, and `rules.py` stays byte-1:1 with the port. Pinned by `test_range_by_wo_index_matches_full_scan` (§7.3) — if anyone ever changes the filter inside `rules`, that test goes red.

### 3.4 `today` and the time zone

```python
@lru_cache
def _tz() -> ZoneInfo:
    return ZoneInfo(get_settings().tz)

def _today_iso() -> str:
    return rules.iso(datetime.now(_tz()).date())
```

`iso(system.date.now())` (src 732) is the single OD-6 point. A bad `WORKMATE_TZ` or a missing `tzdata` wheel raises `ZoneInfoNotFoundError` at request time and `/range` 500s. To make the cause one grep away, `main.py` 0.2.0 probes `_tz()` in the lifespan inside its existing `try` and logs `[E] startup tz=<value> invalid` — same "boot anyway, report loudly" habit `main.py` already applies to the DB. **This is the one judgement call in the spec; say if you'd rather it hard-fails the boot.**

### 3.5 The returned dict — every key, in src order

| Key | Source | Note |
|-----|--------|------|
| `from`, `to` | `rules.iso(from_d/to_d)` | normalised, not echoed |
| `today` | `_today_iso()` | OD-6 |
| `wos` | `repo.fetch_wos` + `hrs`/`hrsSrc`/`assigned` | |
| `labour` | `repo.fetch_labour` | full list, not the index |
| `workers`, `teams` | `rules.buildWorkers(...)` | internal first, then name |
| `priorities` | `repo.fetch_priorities(conn)` | `ORDER BY Sort_Sequence, Priority_Id` is load-bearing (09-11 §5) |
| `colours` | `rules.COLOURS` | shipped so UI and Home agree |
| `weeks` | `rules.capacityByWeek(wos, wlist, iso(from_d), iso(to_d))` | `workerIds=None` → internal workers |
| `load` | `dict([(str(k), v) for k, v in rules.workerLoad(wos, labour).items()])` | **stringified here, not in the repo** (src 738); key `"0"` = unassigned |
| `counts` | `{wo, pm, done, total}` | the parity numbers |
| `pinTable` | step 4 | |
| `workerWeeks` | `rules.workerWeeks(wos, labour, wlist, iso(from_d), iso(to_d))` | already emits `str` keys |
| `uomHours` | `repo.hours_uom_id(conn)` | cached; RST resolves 12 LABOUR HOURS |
| `libVersion` | `rules.__version__` | OD-10; there is no `rules.version()` |

`workerLoad` and `workerWeeks` take the **full** labour list — they are O(n) already and index internally.

## 4. `app/planner/schemas.py` 1.0.0

Pydantic v2 models, camelCase field names throughout (Ruff `N` is not enabled, 09-11 §3, so `hrsPerWeek` needs no suppression).

### 4.1 The reserved-word landmine

`from` is a Python keyword and cannot be a field name. On `RangeData` only:

```python
model_config = ConfigDict(populate_by_name=True, extra="forbid")
from_: str = Field(alias="from")
```

FastAPI serialises with `by_alias=True` by default, so the wire key is `from`. Same alias is needed on the **query parameter** (§6.1) — the trap bites twice. Add it to Landmines §A.

### 4.2 Models

`Wo`, `LabourRow`, `Skill`, `Worker`, `Team`, `Priority`, `WeekLoad`, `Counts`, `WorkerWeek`, `RangeData`. Fields exactly as port spec §3, declared in src order so a printed body diffs cleanly against the Ignition one (cosmetic only — Jython 2.7 dicts were unordered, so key order was never contract).

`RangeData` adds the OD-14 envelope: `ok: bool`, `apiVersion: str`, `actor: int`, `ms: int`. **No `gate` field.**

### 4.3 Drift guard

Every model carries `extra="forbid"`. The router does `RangeData.model_validate(data)` before returning, so:

- a key the service **adds** → `ValidationError` → 500 with the rid, loud;
- a key the service **drops** → missing required field → same.

Without `extra="forbid"` FastAPI would silently swallow an added key and the parity test would pass on a broken contract. Pinned by `test_range_response_model_rejects_drift`.

## 5. `app/core/deps.py` 1.0.0 (OD-12)

```python
def get_current_actor(request: Request) -> int:
```

- `s.is_dev and s.dev_user_id > 0` → return `int(s.dev_user_id)`.
- otherwise → `[G] no identity` and 401 `NO_IDENTITY`, flat body per OD-15.

Swapped wholesale for the JWT dependency in S2. `/range` is read-only, so this is not yet a security decision.

**Prerequisite before the smoke:** `.env` needs `WORKMATE_DEV_USER_ID` set to a real RST `Users.User_Id`, or `/range` 401s in dev too. OD-2 is still open, so any active user does for now — it is only echoed as `actor` this slice and not stamped on anything until S2. One-off probe (SSMS/`Invoke-Sqlcmd`, not module SQL, so `TOP` is fine here):

```sql
SELECT TOP 5 User_Id, RTRIM(Short_User_Id) AS sid, RTRIM(User_Name) AS name
FROM dbo.Users WHERE RTRIM(COALESCE(Active, '')) = 'Y' ORDER BY User_Id;
```

## 6. `app/planner/router.py` 1.0.0

```python
router = APIRouter(prefix="/planner", tags=["planner"])
```

Mounted under the existing `/api/v1` router in `main.py` → `/api/v1/planner/range`.

### 6.1 The route

```python
@router.get("/range", response_model=RangeData, responses={400: {"model": ApiError}})
def get_range(
    request: Request,
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    conn: Connection = Depends(db.get_conn),
    actor: int = Depends(get_current_actor),
) -> RangeData:
```

Plain `def` (D-2). `responses={400: ...}` so the generated TS client knows the failure shape.

### 6.2 Flow

1. `t0 = time.perf_counter()`.
2. `data = service.range_data(conn, from_, to)`.
3. On `WindowError as e`: `diag.log("G", "range refused: %s" % e, request_id=rid, actor=actor)` then `return JSONResponse({"ok": False, "code": e.code, "message": str(e)}, status_code=400)`. Returning a `Response` bypasses `response_model` — legal and intended.
4. `ms = int((time.perf_counter() - t0) * 1000)`; set `ok=True`, `apiVersion=__version__`, `actor`, `ms`.
5. `[F]` line, Ignition text kept verbatim (CLAUDE.md law 10):
   `"range %s..%s rows=%d labour=%d workers=%d pinTable=%s in %d ms"`
6. `return RangeData.model_validate(data)`.

Any other exception falls through to the `main.py` middleware, which already logs `[E]` and returns `{ok:false, code:"INTERNAL", message, rid}` at 500 — the OD-15 shape, unchanged.

### 6.3 Diagnostics — one line, not three

Ignition logs in both `rangeData` (src 743) and `_range` (src 592); our middleware already logs `GET /api/v1/planner/range 200 12ms`. Three lines per request is noise. **The service stays silent** (it is a library) and the router emits the one rich line carrying the parity numbers. The middleware line stays as-is.

## 7. `backend/tests/test_planner_api.py` 1.0.0 (pair rule)

`TestClient` + a real connection inside a transaction that is rolled back (D-10, §4 of Ways of Working). Standing window **2026-09-14..2026-09-20** (09-11 §5). Zero skips is the standard set by S1b — every guard below is written to stay shut on RST.

### 7.1 Fixtures

- module-scoped `client` with `TestClient(app)`;
- `conn` from `db.get_engine().connect()` inside `conn.begin()` … `rollback()`, wired in as `app.dependency_overrides[db.get_conn]`;
- `app.dependency_overrides[deps.get_current_actor] = lambda: <dev user id>`;
- `repo.clear_caches()` in setup — otherwise test order decides what `hours_uom_id` and `pin_table_exists` cached, and the suite goes flaky three slices from now.

**Env trap:** `test_smoke.py` sets `WORKMATE_ENV=test` at import and `get_settings()` is `lru_cache`d, so `is_dev` is False under pytest and an un-overridden call is a 401. That is convenient (it makes §7.4's 401 test free) but it means any test that flips env must call `get_settings.cache_clear()`.

### 7.2 Contract

1. `test_range_200_shape_on_standing_window`
2. `test_range_keys_match_contract` — set equality against a literal frozenset of the 20 keys (port spec §3 + OD-14), asserting **`gate` is absent**
3. `test_range_from_key_is_literal_from` — `"from" in body`, `"from_" not in body`
4. `test_range_lib_version_is_rules_version`
5. `test_range_envelope` — `ok is True`, `apiVersion == router.__version__`, `actor` == the override, `ms >= 0`

### 7.3 Data behaviour

6. `test_range_counts_are_consistent` — `wo + pm + done == total`, each recounted from `wos`
7. `test_range_today_is_configured_tz` — equals `datetime.now(ZoneInfo(get_settings().tz)).date().isoformat()`
8. `test_range_load_keys_are_strings` — every key `str`, `"0"` permitted
9. `test_range_worker_weeks_keys_are_strings`
10. `test_range_weeks_cover_window` — first `weekStart` is the Monday on/before `from`, last is ≤ `to`
11. `test_range_by_wo_index_matches_full_scan` — for every WO in the window, the served `hrs`/`hrsSrc`/`assigned` equal `rules.hoursFor(wo, full_labour)` / `rules.assignedFor(wo, full_labour)`. This is the proof for §3.3
12. `test_range_pin_table_false_on_rst` — OD-1 ground truth. **Trip-wire: this flips in S3** when migration 0002 lands

### 7.4 Guards and routing

13. `test_range_bad_iso_is_400` — `from=2026-02-31` → 400, flat `{ok:false, code:"BAD_WINDOW", message}`
14. `test_range_reversed_window_is_400`
15. `test_range_exactly_400_days_is_200` — `2025-09-14..2026-10-19`
16. `test_range_401_days_is_400` — `2025-09-14..2026-10-20`
17. `test_range_missing_params_is_422` — FastAPI's own validation
18. `test_range_post_is_405`
19. `test_range_401_without_actor` — override cleared → 401 `NO_IDENTITY`, flat body
20. `test_range_response_model_rejects_drift` — monkeypatch `service.range_data` to add a key → 500 `INTERNAL`

Expected suite after this slice: **~100 tests, all green but the 1 known red** (`test_api_404_is_json_not_spa`, OD-17).

## 8. Smoke (paste verbatim)

```powershell
cd C:\dev\workmate-saas\backend
uv run ruff format . ; uv run ruff check .
Select-String -Path app\planner\sql.py -Pattern "ISNULL|GETDATE\(\)|SELECT TOP|\[dbo\]"   # gate: expect only PG-CONVERT lines
uv run pytest -q
uv run pytest tests/test_planner_api.py -v
uv run fastapi dev app/main.py
```

Then, in a second terminal:

```powershell
curl.exe "http://localhost:8000/api/v1/planner/range?from=2026-09-14&to=2026-09-20"
curl.exe -s -o NUL -w "%{http_code} %{time_total}s %{size_download}b`n" "http://localhost:8000/api/v1/planner/range?from=2025-09-14&to=2026-10-19"
curl.exe "http://localhost:8000/api/v1/planner/range?from=2026-02-31&to=2026-09-20"
```

The second one is the **400-day perf probe** — nobody has measured payload size or `ms` at the contract's maximum window on 20 years of RST. If it comes back grim, that is an S1e paging conversation, not an S1c change.

## 9. Acceptance

- All §7 tests green on `dbWorkmate`, zero skips.
- `/range` on the standing window returns all 20 keys, `from` literal, no `gate`.
- Both 400 guards fire with the flat body; 405 and 401 behave.
- The `[F] range ...` line appears once per request with rows/labour/workers/pinTable/ms.
- `counts` for the standing window recorded in the raw log as the **RST baseline**.

Full Ignition parity is *not* claimed by this slice — that needs the KT dev copy (09-11 §8 item 2), which gates S1 acceptance, not this build.

## 10. Deliverables (one Download card each, on 🤙)

| # | File | Version | Target |
|---|------|---------|--------|
| 1 | `Azztec_SaaS_app_planner_service_v1_0_0.py` | 1.0.0 | `backend/app/planner/service.py` |
| 2 | `Azztec_SaaS_app_planner_schemas_v1_0_0.py` | 1.0.0 | `backend/app/planner/schemas.py` |
| 3 | `Azztec_SaaS_app_core_deps_v1_0_0.py` | 1.0.0 | `backend/app/core/deps.py` |
| 4 | `Azztec_SaaS_app_planner_router_v1_0_0.py` | 1.0.0 | `backend/app/planner/router.py` |
| 5 | `Azztec_SaaS_app_main_v1_0_1.py` | 0.2.0 | `backend/app/main.py` (mount + tz probe) |
| 6 | `Azztec_SaaS_test_planner_api_v1_0_0.py` | 1.0.0 | `backend/tests/test_planner_api.py` |

Commit `planner api 1.0.0 — S1c /range`, tag `s1c-api-1.0.0`.

## 11. Changelog

- 1.0.0 (2026-09-11) Initial. Audit carried in the three items from Raw Log 2026-09-11 §9; OD-14…OD-17 signed at the audit gate; signatures verified from the box (`rules` 1.0.0 / `repo` 1.0.0 / `sql` 1.0.1) rather than assumed.
