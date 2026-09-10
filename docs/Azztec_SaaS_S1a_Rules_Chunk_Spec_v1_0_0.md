# Azztec SaaS — S1a Rules Chunk Spec (planner/rules.py)

**File:** Azztec_SaaS_S1a_Rules_Chunk_Spec_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-11 · **Author:** Adriaan
**Status:** Draft — OD-8…OD-10 need 🤙 before Claude Code leaves plan mode
**Target path:** `docs/Azztec_SaaS_S1a_Rules_Chunk_Spec_v1_0_0.md` (+ project knowledge)
**Parent spec:** `Azztec_SaaS_Planner_Port_Spec_v1_0_0.md` §2, §5, §6 (S1), §8
**Source of truth:** `docs/reference/workmate_planner_code_v1_3_1.py` (lines cited below)
**Parity oracle:** `docs/reference/workmate_planner_test_code_v1_0_0.py` — `t_rules`, `t_workers`, `t_moverules`, `t_dst`
**Signed decisions in force:** OD-1 (raw log 2026-09-10 §1), OD-6 (same)

---

## 1. Scope — build exactly two files, then stop

| Deliverable | Target path | Version |
|-------------|-------------|---------|
| `workmate_planner_rules_v1_0_0.py` | `backend/app/planner/rules.py` | 1.0.0 |
| `workmate_test_planner_rules_v1_0_0.py` | `backend/tests/test_planner_rules.py` | 1.0.0 |

**No database. No imports from `app.core.db`. No SQLAlchemy. No FastAPI.** `rules.py` imports `datetime` and
nothing else from anywhere.

**Stop line.** `sql.py`, `repo.py`, `service.py`, `schemas.py`, `router.py` are the *next* chunk of S1 and are
not touched here — not even a stub, not even a docstring placeholder. Pair rule: the two files above ship
together or neither ships.

## 2. Inventory — what crosses, what is rewritten, what stays behind

### 2.1 Ports 1:1, unchanged logic (source lines)

| Function | Src | Note |
|----------|-----|------|
| `category(status, typeFlag)` | 262 | DONE > PM > REQ > WO |
| `engineOwned(status, typeFlag)` | 274 | **OD-1: unchanged.** On RST every engine-owned PM comes back locked — that is the decision working |
| `hoursFor(wo, labourRows)` | 282 | returns a **tuple** `(float, str)` |
| `assignedFor(wo, labourRows)` | 297 | ordered unique ints |
| `classifyTeams(skillRows)` | 312 | returns `{supplierId: {id, short, name, internal, users}}` — `users` is in the dict but not in the docstring; keep it, the contract needs it |
| `buildWorkers(skillRows)` | 335 | returns `(workers, teamList)` |
| `initialsOf(shortId, name)` | 375 | keep the `EXT-` strip and the `1 < len(s) <= 4` bound exactly |
| `workerLoad(wos, labourRows)` | 387 | **int** keys, incl. `0` = unassigned. The `str()` conversion is `service.range_data`'s job (src 738), not this function's |
| `capacityByWeek(...)` | 413 | week walk rewritten (§3.5), arithmetic unchanged |
| `workerWeeks(...)` | 462 | week walk rewritten (§3.5); output keys are `str(uid)` — that one **is** this function's job |
| `moveRules(wo, toIso, todayIso)` | 856 | every code, reason and message string byte-identical |
| `estimateRules(wo, hours)` | 906 | |
| `labourRules(...)` | 1223 | see OD-9 |
| `civilDays(isoFrom, isoTo)` | 206 | **ports untouched** — already pure `datetime.date` (OD-6) |
| `_civil(isoDay)` | 196 | helper for the above |
| `_weekKeyOf(isoDay)` | 457 | helper for `workerWeeks` |
| `_s` / `_i` / `_f` | 117 / 121 / 130 | the coercion twins. `_i` truncates toward zero (`int(float(...))`) — do not "fix" to `int()` or `floor()` |
| `_fmtDelta(delta)` | 778 | **easy to miss.** It sits in the write-side block of the source but `moveRules` calls it at line 897 for the `LABOUR_MULTI` text. It comes here; `service.py` imports it in S2 |

Constants that come across: `_LOCKED_STATUSES`, `_CONFIRM_STATUSES`, `_ENGINE_FROZEN`, `_MAX_ESTIMATE`,
`_MAX_LABOUR_HOURS`, `_MAX_HRS_PER_WEEK`, `COLOURS`, `STATUS_TITLES`. `_MAX_HRS_PER_WEEK` is only used by
`setCapacity` (S4 service) — it still lives here so every rule number sits in one file.

### 2.2 Rewritten on stdlib (OD-6)

`parseIso`, `iso`, `timeOf`, `weekStart` are `system.date.*` today. They are **rewritten, not ported**. Full
signatures in §3.

### 2.3 Stays behind — not in this chunk

`version()`/`_VERSION` (→ `__version__`, OD-10) · `_err` · `_log` · `_query` · `_rows` · `configValue` ·
`pinTableExists` · `_pinSelect` · `hoursUomId` · `_woSql`/`_LABOUR_SQL`/`_WORKER_SQL`/`_PRIORITY_SQL`/`_loadSql`
and every other SQL constant · `fetchWOs` · `fetchLabour` · `labourRows` · `fetchSkillRows` · `fetchPriorities` ·
`workers` · `rangeData` · `loadWO` · `movePreview` · `moveWO` · `undoMove` · `setEstimate` · `unpin` · `_upsertPin` ·
`addLabour` · `removeLabour` · `setCapacity` · `_upd` · `_queryTx` · `_weekNoFor` · `_shiftDays` · `_fmtDate` ·
`_eventRow` · `_fieldDiffDetail` · `_fmtHours` · `_skillRowFor` · `_userName` · `DRY_RUN`.

`DRY_RUN` lands in `service.py` in S2, not here. `_fmtHours` is write-side only (src 1094, 1289, 1357) — it goes
with the service, unlike `_fmtDelta`.

## 3. The four rewrites, exactly

Hard type rule: **`parseIso` and `weekStart` both return `datetime.date`.** `capacityByWeek` and `workerWeeks`
compare them with `<=`; mixing `date` and `datetime` raises `TypeError` at runtime.

### 3.1 `parseIso(s) -> date | None`
`_s(s)`; `return None` if `len(s) < 10`; build `date` from `s[:10]` inside `try/except Exception`. Anything
unparseable is `None` — `moveRules(w, 'nope', …)` returning `BAD_DATE` depends on it.

### 3.2 `iso(d) -> str`
`''` when `d` is None, else `d.strftime('%Y-%m-%d')`. Must accept **both** `date` and `datetime` — the repo hands
it naive datetimes straight off pyodbc in S1b.

### 3.3 `timeOf(d) -> str`
`''` when `d` is None or has no `.hour` (a `date`); else `d.strftime('%H:%M')`, and `''` when that is `'00:00'`.
Midnight and "no time" stay indistinguishable, exactly as today. RST carries a time on 37.7% of
`Request_Start_Date` (raw log §5).

### 3.4 `weekStart(d) -> date`
`d - timedelta(days=d.weekday())`, after normalising a `datetime` down to its `.date()` (Ignition midnights
first, src 218). This is the convention flip OD-6 called out: Ignition `getDayOfWeek` is 1=Sunday with
`back = (dow - 2) % 7`; Python `weekday()` is 0=Monday. Both give 6 for a Sunday — **the Sunday case is the
test that proves it** (§5).

### 3.5 The two week walks
Inside `capacityByWeek` (src 431, 436) and `workerWeeks` (src 475, 477):

- `while not system.date.isAfter(ws, end):` → `while ws <= end:`
- `ws = system.date.addDays(ws, 7)` → `ws = ws + timedelta(days=7)`

And inside `moveRules` (src 887): `iso(system.date.addDays(parseIso(wo.get('end')), delta))` →
`iso(parseIso(wo.get('end')) + timedelta(days=delta))`.

## 4. Traps — Landmines §A/§D applied to these specific lines

1. **camelCase survives.** Function names and every dict key stay exactly as they are (`engineOwned`, `hrsPerWeek`,
   `weekStart`, `pinnedAfter`). `service.py` goes snake_case; `rules.py` does not. Confirmed safe: `pyproject.toml`
   selects `E,F,I,B,UP,SIM` — pep8-naming (`N`) is **not** enabled, so Ruff will not flag them. Do not let a `SIM`
   or `UP` autofix reorder the `flag` if/elif chain in `workerWeeks` (src 517–526) — branch order is behaviour.
2. **Bare `except:`** at src 126, 135, 180, 202 → `except Exception:`.
3. **Tabs → 4 spaces.** The source is tab-indented.
4. **String date comparison is deliberate.** `newStart < _s(todayIso)` (src 889) and `wo['end'] > wo['start']`
   (src 893) compare `yyyy-MM-dd` strings. Leave them as strings; converting to dates changes the empty-string
   guard behaviour.
5. **`round()` divergence** — OD-8.
6. **No `float` "cleanup".** `hoursFor` returns `round(x, 2)` floats and the tests compare with `==`. Do not
   introduce `Decimal` here; Pydantic's `Decimal`-as-string problem (Landmines §A) is a mapper concern in S1b.
7. **`%r` in the BAD_DATE message** (src 876) behaves the same in Py3 for `str` and `None`. Keep the format string.

## 5. Test plan — `tests/test_planner_rules.py`, zero DB

Port the four pure cases from the Night Shift pack as parametrised pytest, keeping the assertion values:

| From | Covers | Fixed values that must not drift |
|------|--------|----------------------------------|
| `t_rules` (test src 95) | category, engineOwned, hoursFor, assignedFor, workerLoad | `hoursFor == (6.5,'labour')`; `assignedFor == [12,13,7]`; `workerLoad == {12:13.0, 13:2.5, 7:5.0, 0:3.0}` |
| `t_workers` (110) | buildWorkers, classifyTeams, initialsOf, capacityByWeek, workerWeeks | 5-row skill fixture; `byid[12]['hrsPerWeek'] == 70.0`; teams order `['TM-ELEC','TM-MAINT','METALFORM']`; `initials 'AMET'`/`'KF'`; week starts `2026-08-31 … 2026-09-28`; `weeks[0] planned 6.0 / capacity 110.0 / pct 5`; `workerIds=[12]` → capacity 70.0; `w7` flags `under` then `empty` |
| `t_moverules` (139) | moveRules incl. both pin paths, estimateRules, labourRules | `delta 14`, `newEnd '2026-09-19'`, reasons `['LABOUR_MULTI','SPAN']`; PAST / ACTIVE / LOCKED_STATUS / NO_CHANGE / BAD_DATE / ENGINE_OWNED; `willPin`+`pinnedAfter`; `willUnpin`+`not pinnedAfter` |
| `t_dst` (167) | civilDays, moveRules across DST, weekStart, timeOf | ±12 across 27 Sep 2026; year-end `2026-12-30 → 2027-01-02 == 3`; `weekStart(2026-09-06) == 2026-08-31`; `timeOf` 10:00 vs `''` |

New cases this chunk adds:

- **weekStart, all seven weekdays** of the week containing 2026-09-06, each → `2026-08-31`. The Sunday row is
  the one OD-6 mandates; the other six stop a `(weekday()+1) % 7` "fix" sneaking back in.
- **`parseIso` returns `date`** and `weekStart(parseIso(x))` compares with `<=` without raising (the type rule, §3).
- **`iso()` accepts a `datetime`** as well as a `date`.
- **Rounding**, documenting whatever OD-8 lands on: `capacityByWeek` with capacity 8.0 / planned 1.0 → `pct`.
  Python 3 gives 12, Jython 1.3.1 gives 13.
- **`_fmtDelta`** `+1 day` / `-1 day` / `+14 days`.
- **`civilDays` returns None** on junk input, and `moveRules` turns that into `BAD_DATE`.

## 6. Open decisions — 🤙 required

| ID | Question | Proposal |
|----|----------|----------|
| **OD-8** | `round()` is half-to-even in Python 3, half-away-from-zero in Jython 2.7. Hits `pct` (`int(round(100.0*p/c))`, src 453 and 516) and every `round(x, 2)` hours sum. | **Keep Python 3 semantics.** The S1 parity oracle is `counts`, which rounding cannot touch; the exposure is ≤1 percentage point on a capacity bar. A `_round_half_up()` helper would have to wrap every `round()` in the module to be consistent, which is more port surface than the defect it fixes. Ship the divergence as a named test case so it is documented, not discovered. |
| **OD-9** | `labourRules` returns `'resDate': <date object>` (src 1241) — not JSON-serialisable, consumed only by `addLabour` in S4. | Keep it a `datetime.date`, 1:1. `service.add_labour` formats it. Do not add a `resDateIso` twin — one shape, one source of truth. |
| **OD-10** | What version does `rules.py` report? The contract's `libVersion` is `rules.__version__`, and the Ignition lib is at 1.3.1. | `__version__ = "1.0.0"` (new file, new lineage, Ways of Working §2 bump rules) plus a `PORTED_FROM = "workmate.planner 1.3.1"` constant. Consequence: the S6 port of `t_versions` asserts `PORTED_FROM`, not `>= '1.3.1'`. |

## 7. Smoke

```
cd backend
uv run ruff check app/planner/rules.py tests/test_planner_rules.py
uv run pytest -q tests/test_planner_rules.py
uv run pytest -q
```

Expected: ruff clean; the rules file green; the full run **2 passed, 1 failed** carried over from the raw log
§7 (`test_api_404_is_json_not_spa` stays red until `pnpm build` exists) plus the new rules tests all green.
Console pasted verbatim before the next chunk.

## 8. Acceptance

- Every name and dict key in §2.1 present and spelled as in the source.
- No import in `rules.py` beyond `datetime` (and `from __future__ import annotations`).
- All four ported test groups green with the fixed values in §5 unchanged.
- The Sunday `weekStart` case green.
- `git commit -m "planner rules 1.0.0 — S1a rules chunk"`, tag `s1a-rules-1.0.0`.

## 9. Changelog

- 1.0.0 (2026-09-11) Initial. Audit of `workmate_planner_code_v1_3_1.py` against the port spec; raises OD-8…OD-10.
