# Azztec SaaS — Raw Log 2026-09-11 (S1d)

**File:** Azztec_SaaS_Raw_Log_2026-09-11_v1_2_0.md · **Version:** 1.2.0 · **Date:** 2026-09-11 · **Author:** Adriaan
**Supersedes:** `Azztec_SaaS_Raw_Log_2026-09-11_v1_1_0.md` §7, §8, §9 (§1–§6 carried forward and extended here)
**Session:** S1d audit → scope cut → spec → build → two smoke rounds. The diagnostics seam, the conditional SPA mount, the OpenAPI contract guard.
**Status:** append-only ground truth. Corrections go in a later dated log, not by editing this one.
**Goes to:** `docs/raw/` in the repo AND project knowledge.

---

## 1. Decisions signed this session

| ID | Decision | Why |
|----|----------|-----|
| **OD-18** | `diag.configure()` is called from `create_app()`. One stdout handler on `workmate.diag`, level from `WORKMATE_LOG_LEVEL`, bare `%(message)s`, `propagate=False`, idempotent. Root is never touched. | Two failure points, not one: no handler AND an effective level of root's WARNING. Attaching a handler alone fixes nothing. Self-attach on "no effective handler" was rejected — `hasHandlers()` walks ancestors, so pytest's caplog handler satisfies it and the branch never fires. That is how the gap survived three slices. |
| **OD-19** | `app.frontend()` mounts only when `dist/index.html` exists. **Reverses OD-17.** | The API stopped depending on the SPA mount, which is what the queued correction asked for (1.0.0 §7) — not "a frontend appeared". OD-17's rationale (the red as a no-frontend signal) is preserved and moved: `/health` reports `frontend: "missing"` and startup emits `[G] frontend not built`, a line that was invisible until the same slice fixed the logger. |
| **OD-20** | `/health` gains `diagWired`; `diag` keeps meaning persist mode. `versions` reads each module's `__version__`. | 1.1.0 §8.1 caught `/health` reporting `diag: "stdout"` as a third masking instrument — it describes where records *would* persist, not whether anything prints. |

**Scope cut at the audit gate.** 1.1.0 §9 proposed S1d = diag fix + `pnpm build` + generated client. Only the diag fix survived. `pnpm build` and the TS client went to S1e, and the API 404 handler was replaced by the conditional mount. Reasons in §6.

OD-1, OD-6…OD-17 unchanged except OD-17 as noted. Don't re-litigate.

## 2. Shipped and tagged

| File | Version | Path |
|------|---------|------|
| `Azztec_SaaS_app_core_diag_v1_1_1.py` | 1.1.1 | `backend/app/core/diag.py` |
| `Azztec_SaaS_app_core_config_v1_1_0.py` | 1.1.0 | `backend/app/core/config.py` |
| `Azztec_SaaS_app_main_v1_0_3.py` | 0.3.0 | `backend/app/main.py` |
| `Azztec_SaaS_dotenv_example_v1_0_1.txt` | 1.0.1 | `backend/.env.example` |
| `Azztec_SaaS_test_diag_wiring_v1_0_1.py` | 1.0.1 | `backend/tests/test_diag_wiring.py` |
| `Azztec_SaaS_test_openapi_contract_v1_0_0.py` | 1.0.0 | `backend/tests/test_openapi_contract.py` |
| `Azztec_SaaS_test_smoke_v1_1_0.py` | 1.1.0 | `backend/tests/test_smoke.py` |
| `Azztec_SaaS_test_planner_api_v1_0_1.py` | 1.0.1 | `backend/tests/test_planner_api.py` |

Spec: `Azztec_SaaS_S1d_Diag_Chunk_Spec_v1_0_0.md`.

Commit **`b1caa50`**, tag **`s1d-diag-1.1.1`** — 9 files, 1,320 insertions, 36 deletions (the ninth is the generated `docs/api/openapi_0_3_0.json`). Tag carries 1.1.1, not the spec's 1.1.0, for the same reason S1c tagged `1.0.1`: tag what shipped.

`diag.py` went 1.1.0 → 1.1.1 mid-slice (§4.2). `test_diag_wiring.py` 1.0.0 → 1.0.1 is a docstring correction only; its twelve tests are byte-identical.

## 3. Suite state

**125 tests, all green, zero red, zero skips.** First all-green suite since S0. The one red carried since 2026-09-10 — `test_api_404_is_json_not_spa` — is cleared by OD-19.

Composition: 101 before this slice (+4 `test_smoke`, +12 `test_diag_wiring`, +8 `test_openapi_contract`). **The pre-slice count was 101, not the 100 recorded in 1.1.0 §3** — same drift as 79→80 in 1.0.0 §2, a file gaining a test after the log was written. Count from the run, never from the previous log.

Ruff: `All checks passed!` — but see §4.4.

## 4. Mistakes caught this session

### 4.1 The eight files never reached the repo

First smoke run came back with the old failure and nothing else changed. `Unblock-File` had run against `$env:USERPROFILE\Downloads` — clearing zone tags where the files sat — and no `Copy-Item` followed. Exactly 1.0.0 §4.1 again.

Diagnosed from the failure output alone, before touching anything, on three independent tells:

1. the traceback rendered `test_api_404_is_json_not_spa` with **no docstring** — 1.1.0 has one on the line after the `def`;
2. a "Captured log call" section was present at all — `diag.py` 1.1.1 sets `propagate=False`, so caplog's root handler would see nothing;
3. StaticFiles still raised, so `main.py` was still 0.2.1.

**Lesson, stronger than 1.0.0 §4.1:** a smoke that reproduces the *previous* failure exactly is evidence the drop failed, not evidence the fix failed. Read the traceback for version tells before debugging the code.

### 4.2 `diag.py` 1.1.0 bound its stream at construction — six reds

`logging.StreamHandler(sys.stdout)` holds the stream **object** it is handed. `capfd.readouterr()` returned empty while the identical line appeared in pytest's "Captured stdout call" section.

Cause, reproduced deliberately before shipping a fix: pytest's default `--capture=fd` is not only an fd redirect — its `SysCapture` half **replaces `sys.stdout`** as well. The `capfd` fixture then replaces it **again** on entry, after the autouse fixture that called `configure()`. The handler kept writing to the previous object. A two-handler probe confirmed it: the eagerly-bound handler wrote to the session capture, the late-bound one to the fixture's.

Fixed in 1.1.1 with `_StdoutHandler`, a `stream` property resolving `sys.stdout` at emit time — the exact shape the stdlib uses for its own `logging._StderrHandler`. No test changed.

**The spec's own landmine note was wrong.** S1d §7.1 said "use capfd, not capsys, because a StreamHandler binds its stream at construction". Right diagnosis, wrong remedy: capfd is the correct *reader*, but nothing bound at construction survives either capture mode. Corrected in `test_diag_wiring.py` 1.0.1.

### 4.3 Spec defect, caught at build

S1d §7.1 tests 6 and 7 specified the `[F]`/`[G]` proofs through `/_diag/self-test` and `/range`. Both resolve a `Depends(db.get_conn)`, so both would have dragged a DB connection into a file the spec calls zero-DB. Shipped instead: direct emission proofs for all three tags plus one real round-trip on `/api/v1/does-not-exist`, which needs no DB. Twelve test items, not ten. The route-level `[F] range …` proof lives in `test_planner_api.py`, where the fixtures already exist.

### 4.4 `ruff format` reformatted 2 of the 8 delivered files

Cards are not ruff-clean on arrival. The `uv run ruff format .` step in the smoke is load-bearing, not cosmetic, and it must run **before** `ruff check` and pytest.

### 4.5 `/health` was about to lie

`main.py` 0.2.1 hardcoded `"config": "1.0.0"` in `versions`. Stale the moment `config.py` bumped to 1.1.0. Ways of Working §2 says the constant is bumped with the header "or `/api/v1/health` lies" — a literal makes that impossible to honour. Now reads `config.__version__`, pinned by `test_health_versions_match_the_modules`.

### 4.6 OD-18's stated cost was wrong

The decision priced `propagate=False` as "the three caplog lines in `test_planner_api.py` go red". They did not: pytest still shows "Captured log call" for `workmate.diag` records. A plain process disagrees — `propagate False | handlers [StreamHandler <stdout>] | root []`. Unexplained; see §8.4.

The migration to capfd was still right, for the other reason in OD-18: caplog proves `diag.log()` was **called**, capfd proves the line **reached stdout**. The masking test became the proving one. The decision stands; its rationale needs the correction above.

## 5. Verified this session

Dev server, `WORKMATE_ENV=dev`, `WORKMATE_DEV_USER_ID=1`, dbWorkmate.

**Boot, in order** — every line new to the console as of this slice:

```
[F] diag wired level=INFO stream=stdout diag=1.1.1
[G] frontend not built dist=C:\dev\workmate-saas\web\dist
[F] startup db=ok dialect=mssql
[F] startup tz=Pacific/Auckland
```

**Requests:**

| Call | Result | Console |
|------|--------|---------|
| `/health` | 200, `diagWired: true`, `frontend: "missing"`, versions db 1.0.0 / diag 1.1.1 / config 1.1.0 / planner 1.0.1 | `[F] … 200 4ms` |
| `/_diag/self-test` | 200, `wired: true` | `[F] diag self-test` + `[F] … 200 2ms` |
| `/range` standing window | 200, **counts 0/273/0/273** | `[F] range 2026-09-14..2026-09-20 rows=273 labour=269 workers=363 pinTable=False in 523 ms` |
| `/range?from=2026-02-31` | 400 `BAD_WINDOW`, flat body | `[G] range refused: bad window …` |
| `/api/v1/does-not-exist` | **404** JSON, `code: NOT_FOUND` | `[G] … 404 0ms` |
| `POST /range` | **405**, `code: METHOD_NOT_ALLOWED` | `[G] … 405 0ms` |

`counts` is **identical to the 1.1.0 §4 baseline** — the wiring slice changed nothing in the data path. The `rid` matches across the router's rich line and the middleware line on every request.

### 5.1 New facts

- **`workers=363` on a one-week window.** Every worker gets a `workerWeeks` entry whether or not they have work — 363 of them against 273 WOs. A larger contributor to the 21 MB / 400-day ceiling (1.1.0 §9 carry-in 3) than the WOs are. S1e design input: the grid likely wants internal-and-assigned only.
- **523 ms cold against 180 ms in 1.1.0 §4**, same window, same rows. First request after boot: cold pool, `hours_uom_id` and `pin_table_exists` not yet cached. **Neither number is the baseline** until a warm second call is recorded.
- **Worker capacity is placeholder data on RST.** `hrsPerWeek` is 1.0 for most people, so user 692 renders pct 1000 and user 80 pct 2400. Ported behaviour, not a defect — but capacity bars will look broken in S1e until the UI decides what to do with a 1.0 capacity.
- `fastapi dev` prints the boot lines **twice**: the import string is resolved once in the reloader parent and again in the watchfiles child, so module-level `create_app()` runs in both. Harmless while `PERSIST_SQL` is None; once migration 0004 lands, every boot writes two `Diag_Log` rows.
- The generated `docs/api/openapi_0_3_0.json` is written with CRLF on Windows; git normalises it on commit (warning only).

## 6. Why the S1d scope was cut

Recorded so it is not re-proposed.

- **`pnpm build` is gated on an unsigned decision that fell off the log.** The web toolchain 🤙 (`eslint` vs `biome`, `create-tsrouter-app` vs `@tanstack/cli`, scaffold v1.0.2 `-SkipBackend`) was 1.0.0 §8.1, "the oldest open item". 1.1.0 supersedes §8 and does not carry it; nothing in 1.1.0 §1 signs it. It is neither open nor signed — it is **missing**. Restored to §8 below.
- **`pnpm build` was the wrong lever for the red.** `test_api_404_is_json_not_spa` tests an API contract. Building a frontend would have made it pass without fixing what it tests. OD-19 fixes the dependency instead.
- **The generated client can't smoke.** Nothing imports it, so "it generated" is the whole acceptance test. Its schema-side value was taken for free instead, with no Node: `test_openapi_contract.py` pins the `from` alias on both the parameter and the model, the 20 keys, absent `gate`, `additionalProperties: false`, and the 400 `ApiError` ref.
- **A catch-all `/api/{rest:path}` route was considered and rejected.** Starlette only falls back to its `Match.PARTIAL` 405 when **no** route returns `Match.FULL`; a later catch-all full-matches on path and would have turned `POST /planner/range` into a 404. Fixing a red by reddening a green is not a trade. Guarded by `test_planner_range_post_is_still_405` in the smoke file as well as the planner suite.

## 7. Doc-correction queue

Applied this session in `Azztec_SaaS_Platform_Landmines_v1_1_0.md` and `Azztec_SaaS_Ways_of_Working_v1_1_0.md`: the logging-wiring traps, the capture-mode trap, the catch-all/405 trap, the `app.frontend()` missing-dist trap, the `from` alias, UP031/B008, the whole-file SQL gate, and the instrument law. Index reissued at 1.1.0 with the full current file set and the project-knowledge policy.

Still queued, unapplied:

- **Port Spec §2:** `PLANNER_DEV_USER_ID` → `.env` `WORKMATE_DEV_USER_ID` (OD-7).
- **Port Spec §6:** S1 splits into S1a–S1e; `/preview` moves to S2 (OD-13). S1d as built is not in §6 at all — the lettering is a session convention.
- **Port Spec §9:** OD-1, OD-6 signed 09-10; OD-7…OD-13 09-11; OD-14…OD-17 09-11; OD-18…OD-20 09-11.
- **Port Spec §3:** the contract key list should carry the OD-14 envelope.
- **Port Spec §8:** "`get_current_user` overridden" — the dependency is `get_current_actor`.
- **Landmines §E:** `Priority.Colour` "always `#FF8000`" is KT-only; `WO_C_Activity` labour can be empty; triggers are PO-only on RST. Carried from 09-10, still unapplied.
- **Architecture / D-6:** the SPA html-fallback under `/api/` once a `dist/` exists (§8.6).
- **`.gitignore`:** `backend/.claude/skills/` and `backend/.agents/skills/` — symlinks into `.venv`.
- **Install doc / Bootstrap script:** the 2026-09-10 §8 corrections.

## 8. Open list

1. **🤙 the web toolchain.** `eslint` vs `biome`, `create-tsrouter-app` vs `@tanstack/cli`, then scaffold v1.0.2 with `-SkipBackend`. **Restored after falling off 1.1.0 §8.** Blocks all of S1e; nothing else is blocked by it now the suite is green.
2. **KT dev copy** for genuine Ignition parity. `scripts/parity_range.py` is blocked on it. S1d claims contract correctness, not parity.
3. **OD-2 open:** which `Users` rows map to logins. Dev actor is `1` (SYS_USER), deliberately not a real person.
4. **Unexplained:** under pytest, `workmate.diag` records still reach a root handler despite `propagate=False` (§4.6). Plain process disagrees. The only file in the test tree never reviewed in chat is `tests/conftest.py` — look there first. Blocks nothing.
5. **21 MB at 400 days**, and `workers=363` on one week (§5.1). The UI must cap its window; API stays as-is.
6. **SPA html-fallback under `/api/`**: once `dist/` exists, a browser navigation to `/api/v1/nope` with `Accept: text/html` gets `index.html`. `curl`/`TestClient` send `*/*` and still get JSON, so the suite stays honest. Fix in **S7**, where there is a real `dist/` to test against.
7. **Double boot lines** under `fastapi dev` (§5.1) — revisit before migration 0004 sets `PERSIST_SQL`.
8. **Cosmetic:** `[F] diag self-test` logs `actor: 0` while the response body says `actor: 1`; the route does not pass actor to `diag.log()`. S2 picks it up with the real JWT.
9. **For the parity oracle, not to fix now:** workers with `capacity 0.0` and real planned hours (e.g. user 338, planned 74.0) come back `pct 0, flag "ok"`, where Port Spec §3's thresholds read like `empty`. May be exactly what Ignition does. Check against the KT copy.
10. `TestClient` `StarletteDeprecationWarning` recommending `httpx2` — next dependency bump.
11. `.gitignore` symlink fix — carried, unchanged.

## 9. Next slice

**S1e — the React planner.** Opens with the §8.1 toolchain 🤙, not a build command. Then scaffold, `pnpm build`, the generated client, `PlannerGrid`, and `scripts/parity_range.py` when the KT copy lands.

**Four things the S1e audit must carry in:**

1. **The toolchain decision is the first line of the audit**, not an assumption. It has been missing for two logs.
2. **The `from` alias, third occurrence.** The schema side is now pinned (`test_openapi_contract.py`); what the generator *emits* for a parameter aliased `from` is still unknown. Also unsettled: Architecture §3.2 pins `@hey-api/openapi-ts` while 1.1.0 §9 carry-in 2 says check `openapi-typescript`. Different packages — one emits a client, one emits types. Decide before generating.
3. **The window cap is a design input, not an afterthought.** 21 MB at 400 days, and 363 workers on a single week. `usePlannerRange(from,to)` needs the guard before the hook is written.
4. **Capacity rendering.** RST `hrsPerWeek` is mostly a 1.0 placeholder, so the bars will show 1000%+ on real data. Decide what the grid does with a 1.0 capacity before it is drawn.

Also carrying: use **2026-06-01..2026-06-07** (12/42/604/658) for anything needing category variety — the standing window is 273/273 PM (1.1.0 §5).

## 10. Changelog

- 1.2.0 (2026-09-11) S1d shipped and tagged `s1d-diag-1.1.1`. OD-18…OD-20 signed, OD-17 reversed. Suite all-green for the first time since S0 (125). Scope cut recorded in §6; the missing web-toolchain decision restored to the open list.
- 1.1.0 (2026-09-11) S1c shipped and tagged. OD-14…OD-17 signed. RST baseline and 400-day perf recorded. Diag console gap found and logged as the top open item.
- 1.0.0 (2026-09-11) Env, SQL Server, RST restore, backend smoke, S1a, S1b.
