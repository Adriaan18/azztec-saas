# Azztec SaaS — Raw Log 2026-09-11 (S1c)

**File:** Azztec_SaaS_Raw_Log_2026-09-11_v1_1_0.md · **Version:** 1.1.0 · **Author:** Adriaan
**Supersedes:** `Azztec_SaaS_Raw_Log_2026-09-11_v1_0_0.md` §6, §8, §9 (§1–§5, §7 carried forward and extended here)
**Session:** S1c audit → spec → build → smoke. `service.range_data` + `schemas.py` + `deps.py` + `router.py` (`/range`) + `test_planner_api.py`.

---

## 1. Decisions signed this session

| ID | Decision | Why |
|----|----------|-----|
| **OD-14** | `/range` envelope keeps `ok`, `apiVersion`, `actor`, `ms`. **`gate` dropped.** | `Planner_v1_8_1.html` (the parity smoke UI) reads all four at src 856 / 1476–1479. `gate` retired with the sid gate. |
| **OD-15** | Error body is flat `{ok:false, code, message, rid}` app-wide. | D-9. `main.py` 0.1.0 already emitted it for `INTERNAL`; one shape beats matching Ignition's nested `{error:{code,message}}`. Cost: the legacy UI banner degrades to "HTTP 400" on `/range` failure. Accepted. |
| **OD-16** | `service.WindowError(ValueError)` with `code='BAD_WINDOW'`; router catches the **type**. | Ignition string-matched `'bad window'` / `'too wide'` in the API layer. Never again. |
| **OD-17** | The queued API 404 handler stays out of S1c. | It's a doc-correction, not this slice. The known red stays red until `pnpm build` — it's a useful signal that there's no frontend. |

OD-1, OD-6 through OD-13 unchanged. Don't re-litigate.

## 2. Shipped and tagged

| File | Version | Path |
|------|---------|------|
| `Azztec_SaaS_app_planner_service_v1_0_1.py` | 1.0.1 | `backend/app/planner/service.py` |
| `Azztec_SaaS_app_planner_schemas_v1_0_0.py` | 1.0.0 | `backend/app/planner/schemas.py` |
| `Azztec_SaaS_app_core_deps_v1_0_0.py` | 1.0.0 | `backend/app/core/deps.py` |
| `Azztec_SaaS_app_planner_router_v1_0_1.py` | 1.0.1 | `backend/app/planner/router.py` |
| `Azztec_SaaS_app_main_v1_0_2.py` | 0.2.1 | `backend/app/main.py` |
| `Azztec_SaaS_test_planner_api_v1_0_0.py` | 1.0.0 | `backend/tests/test_planner_api.py` |

Spec: `Azztec_SaaS_S1c_Api_Chunk_Spec_v1_0_0.md`.

The `.1` bumps on service/router/main are ruff-only, no behaviour change: UP031 (`%`-format → f-strings, Ignition message text preserved) and B008 (`Depends()` in argument defaults → `Annotated`, on the two S0 routes carried over from `main.py` 0.1.0 — pre-existing, surfaced only because `main.py` changed).

Commit `planner api 1.0.1 — S1c /range`, tag **`s1c-api-1.0.1`** (the spec §10 said `1.0.0`, written before the ruff bump — tag the shipped router version).

## 3. Suite state

**100 tests, 99 pass, 1 known red.** 21 new in `test_planner_api.py`, all green first run including `test_range_by_wo_index_matches_full_scan` and `test_range_response_model_rejects_drift`. Ruff: `All checks passed!`.

Known red is unchanged and expected: `test_smoke.py::test_api_404_is_json_not_spa` — `StaticFiles directory 'C:\dev\workmate-saas\web\dist' does not exist` surfaces as a 500, not a 404. Clears when `pnpm build` runs.

## 4. Live probe — RST baseline and the perf answer

Dev server, `WORKMATE_ENV=dev`, `WORKMATE_DEV_USER_ID=1`, dbWorkmate.

| Window | Status | counts (wo/pm/done/total) | `ms` | wall | bytes |
|--------|--------|---------------------------|------|------|-------|
| 2026-09-14..2026-09-20 (standing) | 200 | 0 / 273 / 0 / **273** | 180 | 0.307 s | 293,389 |
| 2026-06-01..2026-06-07 (past week) | 200 | 12 / 42 / 604 / **658** | — | — | — |
| 2025-09-14..2026-10-19 (400 days, the max) | 200 | — | — | 3.266 s | **21,345,597** |
| 2026-02-31..2026-09-20 | 400 | `BAD_WINDOW` | — | — | — |

Standing window envelope: `today` 2026-09-11, `pinTable` false, `uomHours` 12, `libVersion` 1.0.0, `apiVersion` 1.0.1, `actor` 1. Calendar-strict `parseIso` rejected 31 February rather than rolling it to 3 March.

**Scaling is linear.** 57× the days gave 73× the bytes and ~18× the wall time. That is the §3.3 labour index working: the Ignition per-WO full scan would have been O(wos × labour) and run into minutes at ~20k WOs. The deviation is now proven on real data, not just in a unit test.

**21 MB is not a browser payload.** The 400-day maximum is an API capability, not a window the UI should ever request. Practical cap is a few weeks. Carried to §9.

## 5. RST ground truth — additions

Extends §5 of the 1.0.0 log. All verified this session.

- `dbo.Users.User_Id` is NUMERIC → arrives as `Decimal` in Python. `User_Id = 1` is `SYS_USER` / "System User".
- **Dev actor is `1` (SYS_USER) on purpose**, not a real person. When S2 starts stamping `Created_By`, nothing gets falsely attributed to a live employee. Swap once OD-2 settles which `Users` rows map to logins.
- **The standing window is PM-only** — 273 of 273 rows classify `PM`. Not a defect: forward-dated work in a maintenance system is nearly all preventive, corrective WOs arrive reactively, and nothing in the future is `DONE`. Confirmed by the past week, which returns all three of WO/PM/DONE.
- **Consequence:** the standing window exercises one branch of `rules.category()`. Anything needing category variety — parity runs especially — should use **2026-06-01..2026-06-07** (12/42/604/658). `test_range_counts_are_consistent` passes trivially on three branches at the standing window; that's a known limitation of the fixture, not of the test.
- `.env` edits do not reliably reach disk from a chained PowerShell heredoc. Verify with `Select-String` + `uv run python -c "...get_settings()..."` before blaming code — a whole debugging round went to an edit that silently never saved. `get_settings()` is `lru_cache`d, so a watchfiles reload does **not** pick up `.env` changes; restart the server.

## 6. Deliberate deviations from the Ignition source

Extends §6 of the 1.0.0 log.

1. **Labour indexed by `woId` once** (spec §3.3). `rules.hoursFor` / `rules.assignedFor` get the pre-filtered subset instead of the full list. Both filter on `woId` internally so output is identical; cost drops from O(wos × labour) to O(wos + labour). `rules.py` stays byte-1:1. Pinned by `test_range_by_wo_index_matches_full_scan`.
2. **`gate` dropped** from the envelope (OD-14).
3. **Flat error body** instead of Ignition's nested `error` object (OD-15), rendered by a `StarletteHTTPException` handler in `main.py` so 401/404/405 match `INTERNAL`. This is the error *shape* only — not the queued API 404 handler.
4. **One `[F]` line per request**, not two. Ignition logged in both `rangeData` and `_range`; the service is silent (it's a library) and the router emits the rich line. The middleware line is separate and stays.
5. **`extra="forbid"` on every schema**, and the router runs `RangeData.model_validate()` before returning. Contract drift raises loudly instead of being silently dropped by `response_model`.
6. **Startup tz probe.** `main.py` lifespan calls `service.resolve_tz()` and logs `[E] startup tz=<value> invalid` on a bad zone, then boots anyway — same habit already applied to a dead DB.

## 7. Doc-correction queue

Carried from 1.0.0 §7, plus:

- **Landmines §A:** `from` is a Python keyword. The `/range` contract key needs `Field(alias="from")` on the model **and** `Query(alias="from")` on the route parameter. The trap bites twice and will bite a third time in the generated TS client.
- **Landmines:** ruff config bans `%`-formatting (UP031) and `Depends()` in argument defaults (B008). Use f-strings and `Annotated[T, Depends(...)]` from the start.
- **Port Spec §3:** the contract key list should carry the OD-14 envelope (`ok`, `apiVersion`, `actor`, `ms`) — it currently lists only the `rangeData` keys, which cost an audit cycle to reconcile against `_range`.
- **Port Spec §8:** `test_planner_api.py` says "`get_current_user` overridden" — the dependency is `get_current_actor`.
- **Index §6 checklist:** superseded, as before.

## 8. Open list

1. **Diag lines never reach the dev console.** `logging.getLogger('workmate.diag')` has `disabled=False, handlers=[]`, nothing attaches a handler to root, and uvicorn only configures its own loggers — so records fall through to `lastResort` (WARNING+, stderr) and every `[F]`/`[G]` is dropped. Tests pass because `caplog` attaches its own handler, and `/health` reporting `diag: "stdout"` describes the *persist* mode, not whether anything is actually printing. **Fix before S2** — the entire write-path forensic habit depends on being able to grep the console for the line that explains a 500. Either `diag.py` self-attaches a `StreamHandler` when it finds no effective handler, or `main.py` runs `dictConfig` in the lifespan.
2. **KT dev copy still needed** for genuine Ignition parity. `scripts/parity_range.py` (port spec §6 S1 smoke) is blocked on it. S1c claims contract correctness, **not** parity.
3. **OD-2 open:** which `Users` rows map to logins. Dev actor is a placeholder until then.
4. **21 MB at 400 days.** UI must cap its window; `usePlannerRange(from,to)` needs a guard. API stays as-is.
5. `.gitignore` symlink fix — carried, unchanged.
6. `web/dist` missing → the known red. Clears with `pnpm build`.
7. Minor: `TestClient` emits a `StarletteDeprecationWarning` recommending `httpx2`. Harmless, worth picking up at the next dependency bump.

## 9. Next slice

**Naming:** the port spec has **one** S1 row covering rules → sql/repo → service/schemas/router → React. The a/b/c lettering is a session convention for chunking it, so there is no pre-defined "S1d" to point at. What's genuinely left in S1: the generated TS client, `pnpm build`, the React `PlannerGrid` (month/week, cards, legend, counts, capacity bars, worker panel, 60 s quiet poll), and `scripts/parity_range.py`.

**Proposal — S1d = the diag handler fix (§8.1) + `pnpm build` + generated client.** Small, and it clears two things at once: the console goes readable before any write path exists, and the known red goes green. `/range` is now in the OpenAPI schema, so the client generates against a real route. Parity script stays blocked on the KT copy; React follows as S1e.

**Three things the next audit must carry in:**

1. **The diag handler gap.** If the next slice touches the frontend, `window.onerror → POST /api/v1/_diag/client` lands in exactly the same silent logger. Fix it first or the client-side forensics are born broken.
2. **The `from` alias, third occurrence.** Check what `openapi-typescript` emits for a parameter aliased `from` — the model alias and the query alias both have to survive codegen or the generated client calls the route with the wrong key.
3. **The 21 MB ceiling.** `PlannerGrid`'s window guard is a design input, not an afterthought — decide the cap before the query hook is written.

Also worth carrying: use **2026-06-01..2026-06-07** for anything needing category variety (§5).

## 10. Changelog

- 1.1.0 (2026-09-11) S1c shipped and tagged. OD-14…OD-17 signed. RST baseline and 400-day perf recorded. Diag console gap found and logged as the top open item.
- 1.0.0 (2026-09-11) Env, SQL Server, RST restore, backend smoke, S1a, S1b.
