# Azztec SaaS — S1d Diag Chunk Spec (the diagnostics seam)

**File:** Azztec_SaaS_S1d_Diag_Chunk_Spec_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-11 · **Author:** Adriaan
**Status:** Draft — awaiting 🤙 before the build
**Slice:** S1d — `diag.configure()` wiring + `WORKMATE_LOG_LEVEL` + conditional SPA mount + OpenAPI contract test + three test files
**Sits on:** `main.py` 0.2.1 · `service.py` 1.0.1 · `router.py` 1.0.1 · `schemas.py` 1.0.0 · `deps.py` 1.0.0 (S1c, tag `s1c-api-1.0.1`) · `diag.py` 1.0.0 · `config.py` 1.0.0 (S0)
**Parent spec:** `Azztec_SaaS_Planner_Port_Spec_v1_0_0.md` §6 (S1) · Architecture D-6, D-8, D-9 · Ways of Working §7
**Source of the defect:** `Azztec_SaaS_Raw_Log_2026-09-11_v1_1_0.md` §8.1 (open list, top item) and §9 carry-in 1
**Naming:** the port spec has one S1 row; a/b/c/d is the session chunking convention (log 1.1.0 §9). S1d is a proposal signed at the audit gate, not a spec row.

---

## 1. Scope

Backend only. **Zero Node.** Nothing writes to the database, nothing needs `dry_run`, no route contract changes.

**In:** the logging wiring that makes `[F]`/`[G]` visible, the level setting, the stdout stream, the conditional SPA mount that flips the known red, the OpenAPI schema guard on the `from` alias, and three test files.

**Out:**

- `pnpm build`, the web scaffold, and the generated TS client → **S1e**, which opens with the web-toolchain 🤙, not a build command. That decision (`eslint` vs `biome`, `create-tsrouter-app` vs `@tanstack/cli`, scaffold v1.0.2 `-SkipBackend`) was 1.0.0 §8.1 and **did not carry into 1.1.0 §8** — it is neither open nor signed. It comes back as the first line of the S1e audit.
- Log 1.1.0 §9 carry-in **2** (what the generator emits for a parameter aliased `from`) — needs the generator, so S1e. §4 of this spec pins the *schema* half, which is the half that can regress silently today.
- Log 1.1.0 §9 carry-in **3** (the 21 MB / 400-day window cap) — a `PlannerGrid` design input, S1e.
- `dbo.Diag_Log` persistence. `PERSIST_SQL` stays `None` until migration 0004; `persist_mode()` keeps returning `stdout` and means exactly what it means today.
- The SPA html-fallback under `/api/` once a `dist/` exists (§5.3 residual) → queued for **S7**, where there is a real `dist/` to test against.

## 2. Decisions carried in

| ID | Signed | What it means here |
|----|--------|--------------------|
| D-8 | 2026-09-10 | diagnostics are structured JSON on **stdout**; one `diag.log()` seam |
| D-6 | 2026-09-10 | `app.frontend()` serves the SPA; API lives under `/api/v1` |
| OD-15 | 2026-09-11 | flat `{ok:false, code, message, rid}` app-wide — already implemented by the `StarletteHTTPException` handler in `main.py` 0.2.1 (log 1.1.0 §6.3) |
| OD-17 | 2026-09-11 | the API 404 handler stayed out of S1c; the red was kept as the "no frontend" signal |

### 2.1 Decisions this gate must sign

**OD-18 — the wiring shape.** `diag.configure()` is called from `create_app()`; it attaches one `StreamHandler(sys.stdout)` to the `workmate.diag` logger with a bare `%(message)s` formatter, sets that logger's level from `WORKMATE_LOG_LEVEL` (default `INFO`), sets `propagate = False`, and is idempotent. Root is never touched.

- *Why not self-attach on "no effective handler" (§8.1 option A):* `Logger.hasHandlers()` walks ancestors, so under pytest caplog's root handler makes it `True` and the branch never fires. The fix would be invisible to the suite — which is precisely how this defect survived three slices.
- *Why `propagate = False`:* exactly one line, regardless of what any deployment later does to root. Cost is three lines in one file (below). Nothing else in the suite reads `caplog`.
- *Cost:* `test_planner_api.py` lines 257–261 assert through `caplog`, which sits on root. They migrate to `capfd` in the same slice — and in doing so become the first test that proves a diag line actually reached stdout, rather than proving `diag.log()` was called.

**OD-19 — the SPA mount becomes conditional; this reverses OD-17.** `app.frontend()` mounts only when `dist/index.html` exists. With no frontend built, `/api/v1/does-not-exist` matches no route, Starlette raises its own 404, and the existing `StarletteHTTPException` handler returns JSON. The known red flips green **because the API stopped depending on the SPA mount**, which is what the queued correction asked for (log 1.0.0 §7), not because a frontend appeared.

OD-17's rationale — "the red is a useful signal that there's no frontend" — is fair and is preserved, moved somewhere better: `/api/v1/health` already reports `frontend: "missing"`, and startup now emits `[G] frontend not built dist=<path>`. That line was invisible before this slice. The diag fix is what makes it safe to stop using a red test as a status light.

**OD-20 — `/health` gains `diagWired: bool`.** `diag` keeps its current meaning (persist mode). Log 1.1.0 §8.1 caught `/health` reporting `diag: "stdout"` as a third masking instrument: it describes where records *would* persist, not whether anything prints. Both facts now ship, separately.

## 3. `app/core/diag.py` 1.1.0

`log()` keeps its signature, its record shape, its `[F]`/`[G]`/`[E]` tags and its persist path byte-for-byte. This slice adds wiring only.

### 3.1 The defect, stated exactly

Two failure points, not one:

1. `workmate.diag` has no handler, and nothing attaches one to root. uvicorn's `LOGGING_CONFIG` configures `uvicorn`, `uvicorn.error` and `uvicorn.access` only — it has no `root` key.
2. The logger's level is `NOTSET`, so its effective level is root's **WARNING**. `[F]`/`[G]` go in at `INFO` and are discarded at the level check, **before any handler would be consulted**. Attaching a handler alone fixes nothing.

`[E]` survives by accident through `logging.lastResort` (a `_StderrHandler` at WARNING, no formatter) — bare message, **stderr**, wrong stream per D-8. That is why log 1.0.0 §3 could quote the `[E]` StaticFiles line verbatim while neither log quotes a single `[F]` line.

### 3.2 New API

```python
_HANDLER_ATTR = "_workmate_diag"

def configure(level: str = "INFO", stream: TextIO | None = None) -> logging.Logger:
    """Idempotent. Attaches exactly one stdout handler to 'workmate.diag'. Never touches root."""

def is_wired() -> bool:
    """True when this module's own handler is attached — what /health reports."""
```

- `stream` defaults to `sys.stdout` **resolved at call time**, never bound at import.
- Formatter is `logging.Formatter("%(message)s")`. `log()` already `json.dumps`es the whole record including `ts`, so a prefix would break "one line = one JSON object" and make the console un-`jq`-able. Grepping the console for the line that explains a 500 is the entire point (§8.1).
- Idempotence: a handler this module attached carries `_HANDLER_ATTR`; `configure()` removes any it finds before attaching, so repeated `create_app()` calls cannot stack handlers.
- `configure()` is the entry point **any** process calls. The Typer CLI (D-7, S5 `workmate planner nightly`) does not go through `create_app()` — noted here so it is not rediscovered as the same bug in a scheduled job.

## 4. `app/core/config.py` 1.1.0 and `.env.example` 1.0.1

One field: `log_level: str = "INFO"` → `WORKMATE_LOG_LEVEL`. `.env.example` gains the key next to `WORKMATE_TZ`.

**Carry the 1.1.0 §5 trap into the smoke:** `.env` edits do not reliably reach disk from a chained PowerShell heredoc, and `get_settings()` is `lru_cache`d so a watchfiles reload does not pick up `.env` changes. Verify with `Select-String`, restart the server, do not blame code.

## 5. `app/main.py` 0.3.0

### 5.1 Configure first

`configure()` is the first statement in `create_app()`, before the middleware and before the lifespan. The lifespan's own `[F] startup db=…` line must be captured by it, and that line is the boot-time proof the wiring holds.

`app = create_app()` at module scope means importing `app.main` configures logging as a side effect. Acceptable for an application module; it would not be for a library, which is why `diag.py` itself does nothing at import.

### 5.2 Conditional mount (OD-19)

```python
dist = _dist_dir(s.frontend_dist)
if (dist / "index.html").exists():
    app.frontend("/", directory=str(dist), check_dir=(s.env == "prod"))
else:
    diag.log("G", f"frontend not built dist={dist}", source="main")
```

**Do not add a catch-all `/api/{rest:path}` route.** Starlette collects a `Match.PARTIAL` for a real route with a wrong method but only falls back to it when **no** route returns `Match.FULL`. A later catch-all full-matches on path, wins, and `POST /api/v1/planner/range` returns 404 instead of 405 — breaking the green `test_range_post_is_405`. Fixing a red by reddening a green is not a trade. Pinned by §7.3 test 6.

### 5.3 Residual, queued not built

Once a `dist/` exists, a browser navigation to `/api/v1/nope` with `Accept: text/html` gets `index.html` from the SPA fallback rather than a JSON 404. `curl`/`TestClient` send `Accept: */*` and still get JSON, so the suite stays honest. The real fix belongs where a `dist/` exists to test it — **S7 (serve)**. Added to the doc-correction queue.

### 5.4 `/health` (OD-20)

Adds `"diagWired": diag.is_wired()`. `diag` unchanged. `versions.diag` picks up `1.1.0`, `versions.config` becomes `1.1.0`. New field → minor bump, hence 0.3.0.

## 6. `backend/tests/test_openapi_contract.py` 1.0.0

Reads `app.openapi()` — **never `router.routes`** (Landmines §A: FastAPI 0.137 made it a tree of intermediate objects). Zero DB.

The `from` alias bites twice today and the schema half has nothing guarding it: `Field(alias="from")` on the model and `Query(alias="from")` on the parameter are independent, and only the runtime body is currently asserted (`test_range_from_key_is_literal_from`). A regression on the parameter alias would produce a 422 in the generated client, a slice later, far from its cause.

## 7. Tests (pair rule)

### 7.1 `tests/test_diag_wiring.py` 1.0.0 — new, zero DB

1. `test_configure_attaches_exactly_one_handler`
2. `test_configure_is_idempotent` — call twice, still one
3. `test_diag_logger_level_is_info` — `isEnabledFor(INFO)` is True; **the assertion that would have failed before this slice**
4. `test_configure_does_not_touch_root` — no `_workmate_diag` handler on root; root level unchanged
5. `test_diag_does_not_propagate` — `propagate is False` (OD-18)
6. `test_f_line_reaches_stdout` — `capfd`, `GET /api/v1/_diag/self-test`, a `[F]` line on `out`
7. `test_g_line_reaches_stdout` — `capfd`, `/range?from=2026-02-31…` → `[G] range refused`
8. `test_e_line_goes_to_stdout_not_stderr` — `diag.log("E", …)` direct; the D-8 point, and the end of the `lastResort` accident
9. `test_every_emitted_line_is_valid_json` — `json.loads` each captured line
10. `test_health_reports_diag_wired` — `diagWired is True`, `diag == "stdout"`

**Instrument law for this file: `capfd`, never `capsys`, never `caplog`.** A `StreamHandler` binds its stream object at construction; `capsys` swaps `sys.stdout` at the Python level and the handler keeps the old object. `capfd` captures at the file descriptor, which is what pytest's default `--capture=fd` already redirects. These tests require default capture — under `-s` they read empty. `addopts = "-q"` in `pyproject.toml`, so the default holds.

### 7.2 `tests/test_planner_api.py` 1.0.1 — instrument migration

Lines 257–261 move from `caplog` to `capfd`. **Preserve the existing assertion text verbatim** — the `[F] range …` message is Ignition text kept under CLAUDE.md law 10, and this is a patch bump: same assertions, honest instrument. No other change to the file.

### 7.3 `tests/test_smoke.py` 1.1.0

1. `test_api_404_is_json_not_spa` — unchanged source, **now green** (OD-19). The one red in the suite since 2026-09-10.
2. `test_health_reports_frontend_missing` — `frontend == "missing"` while `web/dist` is absent; the signal OD-17 was protecting, relocated
3. `test_diag_self_test_record_shape` — the existing assertion, kept, now explicitly documented as testing the **return value**, with §7.1 test 6 as its emission twin
4. `test_root_is_404_without_dist` — the conditional mount does not silently serve something else
5. `test_planner_range_post_is_405_still` — the §5.2 regression guard, asserted from the smoke file too so it cannot be lost with the planner suite
6. (as above, cross-referenced)

### 7.4 Suite expectation

100 → **~116 tests, all green, zero skips, zero reds.** First all-green suite since S0. Confirm the exact count from the run, do not trust this number.

## 8. Smoke (paste verbatim)

```powershell
cd C:\dev\workmate-saas\backend
uv run ruff format . ; uv run ruff check .
uv run pytest -q
uv run pytest tests/test_diag_wiring.py tests/test_openapi_contract.py -v
```

The proof-of-fix probe — the same one that exposed the defect, re-run:

```powershell
uv run python -c "import logging, app.main; l=logging.getLogger('workmate.diag'); r=logging.getLogger(); print('diag lvl', logging.getLevelName(l.getEffectiveLevel()), 'handlers', l.handlers, 'prop', l.propagate); print('root handlers', r.handlers)"
```

Expect one `StreamHandler (stdout)`, effective `INFO`, `prop False`, root untouched.

Then `uv run fastapi dev app/main.py` and, in a second terminal:

```powershell
curl.exe "http://localhost:8000/api/v1/_diag/self-test"
curl.exe "http://localhost:8000/api/v1/planner/range?from=2026-09-14&to=2026-09-20"
curl.exe "http://localhost:8000/api/v1/planner/range?from=2026-02-31&to=2026-09-20"
curl.exe -i "http://localhost:8000/api/v1/does-not-exist"
curl.exe -X POST "http://localhost:8000/api/v1/planner/range?from=2026-09-14&to=2026-09-20"
curl.exe "http://localhost:8000/api/v1/health"
```

**Paste the whole dev-server terminal.** That is the deliverable of this slice — JSON `[F]` lines on stdout where there were none, including the `[G] frontend not built` line at boot.

Optional, and the input S1e generates from:

```powershell
uv run python -c "import json, app.main; open('../docs/api/openapi_0_3_0.json','w').write(json.dumps(app.main.app.openapi(), indent=2))"
```

## 9. Acceptance

- Suite all green, zero skips, **zero reds** — the first time.
- The dev console shows one JSON `[F]` line per `/range` request, on stdout, valid JSON, carrying rows/labour/workers/pinTable/ms. The bad window shows `[G] range refused`.
- `[G] frontend not built` appears once at boot.
- `/api/v1/does-not-exist` → 404 JSON with no frontend built; `POST /api/v1/planner/range` → still **405**.
- `/health`: `frontend: "missing"`, `diag: "stdout"`, `diagWired: true`.
- OpenAPI carries `from` on both the parameter and the `RangeData` schema; no `from_`; no `gate`.

Nothing here claims Ignition parity — that still needs the KT dev copy (1.1.0 §8.2) and it still gates S1 acceptance, not this build.

## 10. Deliverables (one Download card each, on 🤙)

| # | File | Version | Target |
|---|------|---------|--------|
| 1 | `Azztec_SaaS_app_core_diag_v1_1_0.py` | 1.1.0 | `backend/app/core/diag.py` |
| 2 | `Azztec_SaaS_app_core_config_v1_1_0.py` | 1.1.0 | `backend/app/core/config.py` |
| 3 | `Azztec_SaaS_app_main_v1_0_3.py` | 0.3.0 | `backend/app/main.py` |
| 4 | `Azztec_SaaS_dotenv_example_v1_0_1.txt` | 1.0.1 | `backend/.env.example` |
| 5 | `Azztec_SaaS_test_diag_wiring_v1_0_0.py` | 1.0.0 | `backend/tests/test_diag_wiring.py` |
| 6 | `Azztec_SaaS_test_openapi_contract_v1_0_0.py` | 1.0.0 | `backend/tests/test_openapi_contract.py` |
| 7 | `Azztec_SaaS_test_smoke_v1_1_0.py` | 1.1.0 | `backend/tests/test_smoke.py` |
| 8 | `Azztec_SaaS_test_planner_api_v1_0_1.py` | 1.0.1 | `backend/tests/test_planner_api.py` |

Ruff from the start: f-strings, never `%`-formatting (UP031); `Annotated[T, Depends(...)]`, never `Depends()` in an argument default (B008).

Commit `diag wiring 1.1.0 — S1d`, tag `s1d-diag-1.1.0`.

Mark-of-the-Web: `Unblock-File` after the drop, and check `Length` on every target — log 1.0.0 §4.1.

## 11. Doc corrections this slice queues

- **Landmines §A:** `logging.getLogger(name)` with no handler and no level is silent for `INFO` and escapes to `lastResort` (stderr, WARNING+) for `ERROR`. A library logger needs a level **and** a handler; `hasHandlers()` is useless as a guard because caplog satisfies it.
- **Landmines §A:** `capfd`, not `capsys`, for anything asserting on a `StreamHandler` — the stream object is bound at construction.
- **Landmines §A:** a catch-all route under an API prefix defeats Starlette's `Match.PARTIAL` 405 fallback.
- **Ways of Working §7:** name the instrument law — a diagnostics test that asserts a function's return value is not a diagnostics test.
- **S7 / Architecture D-6:** the SPA html-fallback under `/api/` (§5.3).
- Everything still queued from 1.1.0 §7 is unchanged and unapplied.

## 12. Changelog

- 1.0.0 (2026-09-11) Initial. Scope cut at the audit gate from the 1.1.0 §9 proposal: `pnpm build` and the generated client dropped to S1e behind the unsigned web-toolchain decision; the API 404 handler replaced by a conditional SPA mount; an OpenAPI contract test added to cover the `from` alias without Node. OD-18…OD-20 raised for signature at this gate.
