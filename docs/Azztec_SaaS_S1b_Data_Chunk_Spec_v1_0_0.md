# Azztec SaaS — S1b Data Chunk Spec (planner/sql.py + planner/repo.py)

**File:** Azztec_SaaS_S1b_Data_Chunk_Spec_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-11 · **Author:** Adriaan
**Status:** Draft — OD-11…OD-13 need 🤙 before Claude Code leaves plan mode
**Target path:** `docs/Azztec_SaaS_S1b_Data_Chunk_Spec_v1_0_0.md` (+ project knowledge)
**Parent spec:** `Azztec_SaaS_Planner_Port_Spec_v1_0_0.md` §2, §3, §6 (S1) · `Azztec_SaaS_Data_Layer_and_RST_DB_v1_0_0.md` §4–§7
**Source of truth:** `docs/reference/workmate_planner_code_v1_3_1.py` lines 532–706 (SQL + fetch)
**Depends on:** `app/planner/rules.py` 1.0.0 (shipped, tag `s1a-rules-1.0.0`) · `app/core/db.py` 1.0.0
**Signed decisions in force:** OD-1, OD-6 (raw log 2026-09-10) · OD-8, OD-9, OD-10 (raw log 2026-09-11)

---

## 1. Why S1 is being split

Port spec §6 lists S1 as one slice: rules + sql + repo + service + schemas + router + the whole React grid. That
is four pair-rule boundaries in one slice and it cannot smoke as a unit. S1a (rules) shipped on its own and the
discipline held. The rest splits the same way:

| Chunk | Contents | Gated on |
|-------|----------|----------|
| S1a ✅ | `rules.py` + `test_planner_rules.py` | shipped 2026-09-11, tag `s1a-rules-1.0.0` |
| **S1b (this)** | `sql.py` + `repo.py` + `test_planner_repo.py` | nothing outstanding |
| S1c | `service.range_data` + `schemas.py` + `router.py` (`/range`) + `test_planner_api.py` | **OD-7**, OD-12 |
| S1d | `loadWO` + `movePreview` + `/preview` — **moved into S2** (OD-13) | OD-13 |
| S1e | React `PlannerGrid` and the feature folder | S1c green |

## 2. Scope — build exactly three files, then stop

| Deliverable | Target path | Version |
|-------------|-------------|---------|
| `workmate_planner_sql_v1_0_0.py` | `backend/app/planner/sql.py` | 1.0.0 |
| `workmate_planner_repo_v1_0_0.py` | `backend/app/planner/repo.py` | 1.0.0 |
| `workmate_test_planner_repo_v1_0_0.py` | `backend/tests/test_planner_repo.py` | 1.0.0 |

**Stop line.** No `service.py`, no `schemas.py`, no `router.py`, no `loadWO`, no Pydantic model, no FastAPI
import. `repo.py` returns plain dicts, exactly as `fetchWOs` / `fetchLabour` / `fetchSkillRows` /
`fetchPriorities` do today. Read-only: nothing in this chunk writes, so DRY_RUN does not arise — the test
fixture still runs inside a rolled-back transaction (Ways of Working §4) because `dbWorkmate` is real RST data.

## 3. `sql.py` — five statements, dialect-portable

Each carries the NQ-style header from Data Layer §4 (`# name:`, `# dialect:`, `# params:`).

| Constant | From | Params | Notes |
|----------|------|--------|-------|
| `WO_RANGE_NOPIN` / `WO_RANGE_PINNED` | `_woSql()` 560 | `from_d`, `to_d` | see §3.1 |
| `LABOUR_RANGE` | `_LABOUR_SQL` 597 | `from_d`, `to_d` | see §3.4 |
| `WORKER_SKILLS` | `_WORKER_SQL` 611 | — | `Users.Active = 'Y'` **and** `User_Skill.Active NOT IN ('0','N')` — RST carries both domains (raw log 8.2b/8.2c) |
| `PRIORITIES` | `_PRIORITY_SQL` 625 | — | **`ORDER BY Sort_Sequence, Priority_Id` is load-bearing.** RST has four-way ties on `Sort_Sequence` (raw log 8.2f); the second key is the only thing keeping the JSON contract order stable |
| `UOM_LR_STD` / `UOM_MODAL` | `hoursUomId()` 539/547 | — | see OD-11 |

### 3.1 The pin problem — two constants, not a function

`_woSql()` is a *function* because `_pinSelect()` (247) injects three correlated subselects when `WO_N_Plan`
exists and three literals (`0 AS Pinned, NULL AS Prev_Start, NULL AS Pinned_On`) when it does not. `sql.py`
holds static constants and the CI grep gate reads that file, so ship **two named constants** sharing one body:

```python
_WO_RANGE_BODY = """SELECT h.WO_ID, ... {pin} FROM dbo.WO_N_Header h ..."""
_PIN_COLS = """COALESCE((SELECT x.Pinned ... ORDER BY x.WO_ID OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY), 0) AS Pinned, ..."""
_NOPIN_COLS = "0 AS Pinned, CAST(NULL AS datetime) AS Prev_Start, CAST(NULL AS datetime) AS Pinned_On "
WO_RANGE_PINNED = _WO_RANGE_BODY.format(pin=_PIN_COLS)
WO_RANGE_NOPIN  = _WO_RANGE_BODY.format(pin=_NOPIN_COLS)
```

`repo.fetch_wos` picks one on `table_exists(conn, "WO_N_Plan")`. **On RST today that is always `WO_RANGE_NOPIN`**
(raw log 8.4a) — the pinned variant ships untested against real data until the S3 migration, and its test is a
SQL-compiles check, not a row check. Note the explicit `CAST(NULL AS datetime)`: bare `NULL` columns are
untyped, and pyodbc and psycopg disagree about what they hand back.

### 3.2 Dialect rewrites required (Data Layer §5)

| Today | Port | Count |
|-------|------|-------|
| `ISNULL(x, y)` | `COALESCE(x, y)` | ~40 across the five statements |
| `SELECT TOP 1` | `ORDER BY … OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY` | 5 (3 pin subselects + 2 UOM) |
| `?` positional | `:from_d` / `:to_d` / `:wo_id` named binds | every statement |

`FETCH NEXT` is valid on both engines (PG treats `NEXT` and `FIRST` as synonyms), so no `-- PG-CONVERT:` tag is
needed for the rewritten TOPs — that is the point of rewriting them. No `GETDATE()` in the read path. `dbo.`
prefixes are already present. **No colons in SQL comments** (Landmines §B — SQLAlchemy `text()` reads `:name`
inside comments as a bind).

Gate before shipping:

```
grep -rn "ISNULL\|GETDATE()\|SELECT TOP\|\[dbo\]" backend/app/planner/sql.py
```

must return nothing at all for this chunk.

### 3.3 `to_d` is exclusive

The source calls `_query(sql, [fromD, system.date.addDays(toD, 1)])` against `>= ? AND < ?`. The `+1 day` lives
in **`repo.py`**, not in the SQL and not in the caller. Header comment says so on both range statements.

### 3.4 Labour is scoped by the WO's start date, not `Res_Date`

`_LABOUR_SQL` joins `WO_N_Header` and filters on `h.Request_Start_Date` — so a labour row dated well outside the
window still comes back if its WO starts inside it. `workerWeeks` then buckets it by `Res_Date`, which may fall
outside `weekKeys` and silently not be counted. Deliberate, not a bug; the parity script needs to know before
someone "fixes" it.

## 4. `repo.py` — same output dicts, snake_case function names

| Source | Port | Output |
|--------|------|--------|
| `fetchWOs(fromD, toD)` 632 | `fetch_wos(conn, from_d, to_d)` | list of WO dicts |
| `fetchLabour(fromD, toD)` 675 + `_labourDict` 668 | `fetch_labour(conn, …)` + `_labour_dict` | list of labour dicts |
| `fetchSkillRows()` 685 | `fetch_skill_rows(conn)` | list of skill-row dicts |
| `fetchPriorities()` 699 | `fetch_priorities(conn)` | `{id, short, title}` |
| `hoursUomId()` 532 | `hours_uom_id(conn)` | int — RST resolves **12 LABOUR HOURS** (raw log 8.2d) |
| `pinTableExists()` 238 | `db.table_exists(conn, "WO_N_Plan")` | drop the wrapper, call db.py directly |

**Function names go snake_case. Dict KEYS stay camelCase** — `sid`, `startTime`, `hasPO`, `engineOwned`,
`pinnedOn`, `engineDate`, `hrsSrc`, `skillTitle`, `supplierShort`, `internalDept`. They are the JSON contract and
the input shape `rules.py` already expects. A snake_case key here breaks `hoursFor`, `buildWorkers` and the UI in
one move.

Other rules:

- `repo.py` imports from `app.planner.rules` for `category`, `engineOwned`, `civilDays`, `iso`, `timeOf`,
  `STATUS_TITLES`, `_LOCKED_STATUSES` — do not re-implement any of them.
- **Keep the `_i` / `_f` / `_s` mappers on every field** even though `db.rows()` already strips strings and turns
  `Decimal` into int/float. `_clean` returns an `int` for an integral numeric, and `weekNo` (numeric `2026.38`)
  must be a float in the contract. Belt and braces, as Landmines §B says for `char(n)`.
- `hours_uom_id` caches. Module global like the Jython `_hoursUom` is wrong here — it would outlive a tenant
  switch (D-12). Cache per engine: `@lru_cache` keyed on `conn.engine.url`, or a dict on the engine. State which
  in the file header.
- No `try/except` swallowing around the queries except where the source swallows (`hoursUomId`'s two probes,
  which fall through to `0`). A failed `fetch_wos` must raise so the router can turn it into a 500 with a `[E]`
  line — `db_error()` is for the message, not for hiding it.

## 5. Open decisions — 🤙 required

| ID | Question | Proposal |
|----|----------|----------|
| **OD-11** | `hoursUomId`'s fallback is `GROUP BY UOM_Id ORDER BY COUNT(*) DESC` with no tie-break (src 547) — a tie picks an arbitrary UOM, and the answer is cached for the process lifetime. | Add `, UOM_Id` as the second sort key, same fix `_PRIORITY_SQL` already carries. It is a behaviour change, which is why it needs the gate — but the fallback only fires when no `LRStd` row exists, and RST resolves cleanly to 12, so nothing observable changes today. Note it in the Landmines doc as a KT-side risk. |
| **OD-12** | S1's router needs an actor, but `app/auth/` (D-5: JWT, `App_User`, argon2) is in **no slice** S0–S7. | S1c ships `deps.get_current_actor()` returning the dev user id when `WORKMATE_ENV=dev`, raising 401 otherwise — one seam, swapped for the real JWT dependency in S2. `/range` is read-only so this is not a security decision yet. It does mean OD-7 must land first: the dev id has nowhere to come from on RST. |
| **OD-13** | `/preview` sits in S1 (port spec §6) but `movePreview` → `loadWO` pulls in two more statements and returns `startDate`/`endDate`/`engineDateValue` as raw `datetime` objects for the S2 writer. | Move `loadWO`, `movePreview` and `GET /preview` into **S2**, where those datetimes are actually consumed. S1 ships `/range` only. Port spec §6 gets a dated correction. |

**OD-7 does not block this chunk.** Nothing in `sql.py` or `repo.py` reads `System_Configuration` — the only
`config_value()` caller in the read path is identity, which lands in S1c. That is why S1b is next regardless of
how OD-7 goes.

## 6. Tests — `tests/test_planner_repo.py`

Fixture: `conn = engine.connect()` → `trans = conn.begin()` → yield → `trans.rollback()`. Read-only chunk, but the
fixture is written now so S2 inherits it (Ways of Working §4). Skip the module with a clear reason when the DB is
unreachable — a red suite on a laptop without SQL Server is noise, not signal.

| Test | Asserts |
|------|---------|
| `test_sql_has_no_mssql_only_idioms` | greps the five constants for `ISNULL`/`GETDATE`/`SELECT TOP`/`[dbo]` — the CI gate, as a unit test, no DB needed |
| `test_all_statements_compile` | every constant through `text()` and `conn.execute` with a zero-row window — proves both pin variants parse on the live dialect |
| `test_fetch_wos_shape` | a fixed RST window; every contract key from port spec §3 present; `start` is `yyyy-MM-dd`; `startTime` is `''` or `HH:mm`; `weekNo` is a float |
| `test_to_d_is_inclusive` | a WO starting exactly on `to_d` is returned — the `+1 day` boundary |
| `test_cancelled_excluded` | no `status == 'D'` row in the result (SQL says `<> 'D'`; RST has 12,796 D/M + 4,667 D/N) |
| `test_pin_columns_default_off` | RST has no `WO_N_Plan` → `pinned` False, `engineDate` `''`, `pinnedOn` `''` for every row |
| `test_od1_pms_are_locked` | on a window containing PMs: engine-owned PMs come back `locked=True`, `movable=False`. **This is OD-1 working, not a defect** |
| `test_fetch_priorities_order` | order matches `Sort_Sequence, Priority_Id` — re-query with the second key dropped and assert the orders differ, proving the key is doing work on RST's ties |
| `test_worker_rows_active_domains` | no `Users.Active = 'N'` and no `User_Skill.Active = '0'` rows survive |
| `test_hours_uom_id` | returns `12` on RST, and returns the same object on a second call (cache) |
| `test_rules_consume_repo_output` | `buildWorkers(fetch_skill_rows(conn))` and `hoursFor(wo, fetch_labour(...))` run clean on real rows — the S1a/S1b seam, the thing most likely to be wrong |

## 7. Smoke

```
cd backend
uv run ruff check app/planner/sql.py app/planner/repo.py tests/test_planner_repo.py
grep -rn "ISNULL\|GETDATE()\|SELECT TOP\|\[dbo\]" app/planner/sql.py
uv run pytest -q tests/test_planner_repo.py
uv run pytest -q
```

Expected: ruff clean · grep silent · repo tests green · full run 46 passed + the new ones, 1 failed (`web\dist`,
carried from raw log §7 and now known to surface as a 500 rather than a 404). Console pasted verbatim.

## 8. Acceptance

- The grep gate returns nothing.
- Both pin variants compile against the live dialect.
- `counts`-relevant rows (`cat` values) match a hand-run `SELECT … GROUP BY Status, WO_Type_Flag` on the same
  window — the first real parity check, ahead of the full oracle in §9 item 3 of the raw log.
- `git commit -m "planner sql+repo 1.0.0 — S1b data chunk"`, tag `s1b-data-1.0.0`.

## 9. Changelog

- 1.0.0 (2026-09-11) Initial. Audit of `workmate_planner_code_v1_3_1.py` 532–706; proposes the S1b–S1e split;
  raises OD-11…OD-13.
