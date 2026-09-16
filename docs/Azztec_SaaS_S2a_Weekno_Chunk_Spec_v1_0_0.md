# Azztec SaaS — S2a Weekno Chunk Spec

**File:** Azztec_SaaS_S2a_Weekno_Chunk_Spec_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-15 · **Author:** Adriaan
**Status:** Draft — **OD-48 and OD-49 need 🤙 before anything is built.**
**Target path:** `docs/Azztec_SaaS_S2a_Weekno_Chunk_Spec_v1_0_0.md` (+ project knowledge)
**Parent spec:** `Azztec_SaaS_Planner_Port_Spec_v1_0_6.md` §2 (the `pm_engine.weekNo` row), §6 (S2), §8 (`test_weekno.py`)
**Source of truth:** `workmate_pm_engine_code_v2_5_0.py` 471–529 (the verbatim `GetWeekNoANDYear` port) · `workmate_planner_code_v1_3_1.py` 762–767, 977, 1004 (what the write path does with it) · `dbWorkmate_KT.dbo.GetWeekNoAndYear` and both databases' `Week_No`, read on the box 2026-09-15 (§2)
**Closes:** the outstanding `GetWeekNoAndYear` query (Index 1.8.0 §6 step 6). Unblocks S2b's `move_wo`.
**Signed decisions in force:** D-3 (portable — this module has no SQL at all), D-4 (module layout), OD-8 (Python 3 rounding semantics, documented not patched), OD-10 (`PORTED_FROM` names the Ignition source), Ways of Working §4 (pair rule), §5 (never re-emit a file you have not read; a decision about data is blocked on reading the table), Landmines §D (Jython → Python 3 traps)

---

## 1. Scope — two cards, then stop

| # | Deliverable | Target path | Version | Change |
|---|---|---|---|---|
| 1 | `Azztec_SaaS_app_core_weekno_v1_0_0.py` | `backend/app/core/weekno.py` | **new** | the verbatim `_netWeekNoAndYear` port + the two public twins (§3) |
| 2 | `Azztec_SaaS_test_weekno_v1_0_0.py` | `backend/tests/test_weekno.py` | **new** | pair of card 1, **zero DB**, 25 cases (§5) |

**Untouched:** every `app/planner/*` module, `app/core/*` except the new file, every frontend file, every test except the new one, `pyproject.toml`, both KT databases, RST.

**Nothing writes.** No database is opened, no server is needed, no route is added. The module ships with **no caller** — S2b's `service.move_wo` is its first one. That is deliberate: it is the only piece of the write stack that can be built and proved without touching RST.

**Not in this slice:** `loadWO`, `movePreview`, `move_wo`, `undo_move`, `set_estimate`, the write SQL, the routes, the schemas, `@dnd-kit`, the confirm dialog, the undo toast, the JWT swap (§9.2 places each).

**The cut available at the gate:** fold this into S2b. **Not recommended** — it is zero-DB and zero-risk, its references needed reconciling before anything could be signed (§2 changed the test plan the Port Spec carried), and a wrong `Week_No` written by `move_wo` is a silent data defect on a `NOT NULL` column that the release engine also reads.

## 2. Evidence — read on the box 2026-09-15, before any 🤙

### 2.1 Reference 2 is an ISO rewrite, not a transcription

`dbWorkmate_KT.dbo.GetWeekNoAndYear`, read through `dbWorkmate_KT.sys.sql_modules` joined to `.sys.objects` / `.sys.schemas` (never `OBJECT_DEFINITION()` — Landmines §B):

```sql
CREATE FUNCTION dbo.GetWeekNoAndYear (@date DATE)
RETURNS VARCHAR(8)
AS
BEGIN
    DECLARE @isoWeek INT = DATEPART(ISO_WEEK, @date);
    DECLARE @isoYear INT =
        CASE
            WHEN @isoWeek >= 52 AND MONTH(@date) = 1 THEN YEAR(@date) - 1
            WHEN @isoWeek = 1  AND MONTH(@date) = 12 THEN YEAR(@date) + 1
            ELSE YEAR(@date)
        END;
    RETURN FORMAT(@isoYear, '0000') + '.' + RIGHT('0' + CAST(@isoWeek AS VARCHAR), 2);
END;
```

It is **ISO-8601 week + week-year**, not a line-for-line copy of `clsGeneralOperation.GetWeekNoANDYear`. It is also an orphan at KT — gateway references 0, dependencies 0 (KT Schema Delta §5.2) — so nothing has ever called it. Port Spec §8 called it one of three independent references; it is not independent of ISO, and it is not a second copy of the algorithm. **It is an equivalence oracle**, and a good one: it is the shape a later engineer at KT reached for when they wanted the same answer.

### 2.2 Reference 3 is not a reference — `Week_No` is not a function of the start date

Distinct `(Request_Start_Date, Week_No)` pairs, both databases:

```
src start_date  week_no      src start_date  week_no
--- ----------  -------      --- ----------  -------
KT  2026-09-07  2026.37      RST 2026-01-01  2025.53
KT  2026-09-14  2026.38      RST 2026-01-01  2026.01
KT  2026-09-17  2026.35      RST 2025-12-31  2025.53
KT  2026-09-17  2026.36      RST 2025-12-31  2026.01
KT  2026-09-17  2026.37      RST 2025-12-29  2025.53
KT  2026-09-17  2026.38      RST 2025-12-29  2026.01
                             RST 2025-12-28  2025.52
                             RST 2025-12-28  2025.53
```

One start date carries **four** different `Week_No` values at KT and **two** at RST, and 2025 has no ISO week 53 at all (1 Jan 2025 was a Wednesday, non-leap). This is exactly what `pm_engine` 2.5.0 says at 476: **`WO_N_Header.Week_No` is COPIED from the subtask, never recomputed.** It is the PM's *release* week; the start date has moved since.

**Consequence:** a test that samples `(start, Week_No)` and asserts `week_no(start) == Week_No` goes red against perfectly good data on both databases. Same class as `test_range_priority_order_is_not_alphabetical` (Ways of Working §6), except the premise is wrong everywhere rather than on one site. The Port Spec's third reference is struck, on evidence, and §5 says so in the test file so nobody writes it in six months.

### 2.3 The port agrees with the SQL function and with ISO — measured, not asserted

`_netWeekNoAndYear` transcribed from `pm_engine` 486–514 and run against the function's own answers on the thirteen dates that exercise its branches:

```
date        .NET port  SQL fn    ISO       agree
2019-12-30  2020.01    2020.01   2020.01   yes      num6 > 52 -> reset to week 1, year + 1
2020-12-31  2020.53    2020.53   2020.53   yes      flag True -> week 53 survives
2021-01-01  2020.53    2020.53   2020.53   yes      num6 == 0 -> recurse into 2020-12-31
2025-12-26  2025.52    2025.52   2025.52   yes
2025-12-28  2025.52    2025.52   2025.52   yes
2025-12-29  2026.01    2026.01   2026.01   yes
2025-12-31  2026.01    2026.01   2026.01   yes
2026-01-01  2026.01    2026.01   2026.01   yes      num2 == num3 == 4, flag True
2026-01-03  2026.01    2026.01   2026.01   yes
2026-01-04  2026.01    2026.01   2026.01   yes
2026-09-07  2026.37    2026.37   2026.37   yes
2026-09-14  2026.38    2026.38   2026.38   yes      the Port Spec §8 figure, now checked
2026-12-21  2026.52    2026.52   2026.52   yes
```

And across every date from 2000-01-01 to 2040-12-31: **14,976 dates, 0 disagreements with `date.isocalendar()`**. (`pm_engine`'s own comment at 477 says 14,975 — off by one, the range is inclusive at both ends. Noted, nothing turns on it.)

### 2.4 The columns the value is written into

```
tbl              typ      prec  scal  nullable
WO_N_Header      numeric  6     2     NO
WO_N_Subtasks    numeric  18    2     YES
WO_C_header      numeric  6     2     YES
```

`numeric(6,2)` **NOT NULL** on the header. A value of `2026.01` must arrive exact; the scale is 2, which is what `'%d.%02d'` produces and what a two-digit week needs.

### 2.5 What the write path does with it (read from `planner` 1.3.1, not remembered)

- 977: `weekNo = _weekNoFor(newStart)` → one value on `WO_N_Header` per move.
- 1004: `_weekNoFor(new)` **per distinct subtask date**, inside the collision-safe loop — so a multi-subtask move calls it several times with different dates.
- 762–767: `_weekNoFor` raises when the port returns `None`; the move then fails as `INTERNAL` and rolls back. The raise is load-bearing — a `NULL` into `WO_N_Header.Week_No` is a constraint violation, and a silently-wrong week is worse.

## 3. The changes, exactly

### 3.1 `backend/app/core/weekno.py` 1.0.0 (card 1)

File-wide `# ruff: noqa: UP031` with the reason, exactly as `rules.py` 1.1.0 carries it — `'%d.%02d' %` is the oracle's expression producing a contract value, and `UP` would rewrite it.

```
__version__  = "1.0.0"
PORTED_FROM  = "workmate.pm_engine 2.5.0"          # OD-10's precedent
_MAX_DEPTH   = 2                                    # the source's own recursion guard

_net_day_of_week(d)              -> int    # .NET DayOfWeek, Sunday = 0 (Landmines D)
_net_week_no_and_year(d, _depth) -> str | None      # 486-514, line for line
week_no_and_year(d)              -> str    # the public twin; raises ValueError on None
week_no(d)                       -> Decimal         # OD-48
```

`_net_week_no_and_year` is transcribed with the source's variable names (`num`, `num2`, `num3`, `num4`, `flag`, `num6`) kept, so a divergence is a diff against the source rather than an argument about calendars. The two public twins accept `date` or `datetime` and normalise to `date` first.

`week_no_and_year` raises `ValueError` when the transcription returns `None` (bad input or the depth guard), which is `_weekNoFor`'s behaviour at 765–766 in Python's idiom. No logging, no diag — this module is pure and has no I/O.

### 3.2 What it is **not**

No `float` return (OD-48). No SQL. No `system.date`. No caller — `service.py` imports it in S2b. It does not touch `rules.py`, which already holds every other pure function S2 needs (`moveRules` 533, `estimateRules` 634, both green at 70 cases).

## 4. Traps

1. **Ignition months are 0-based.** `system.date.getDate(year, 0, 1)` is **1 January** and `(year, 11, 31)` is **31 December**. A literal transcription writes `date(year, 0, 1)` (crashes) or `date(year, 11, 31)` (11 November — wrong, and it would pass most days of the year).
2. **`system.date.getDayOfWeek` is 1 = Sunday … 7 = Saturday**, and `_netDayOfWeek` subtracts 1 to reach .NET's `0 = Sunday`. In Python that is `(d.weekday() + 1) % 7`, never `d.weekday()` (Landmines §D).
3. **Keep the explicit float.** Jython `/` on two ints floors; the source writes `float(dayOfYear - num4) / 7.0` for that reason. Keep the `float()` and the `7.0`, and keep the `int()` around `math.ceil` — Python 2's `ceil` returned a float, Python 3's returns an int, and the `int()` makes the transcription read the same either way.
4. **`num6 == 0` is reachable and is the recursion.** `math.ceil` of a small negative is `-0.0` → `0` (2021-01-01: `num4 = 3`, `dayOfYear = 1`). Keep the branch; it is pinned by its own case.
5. **`'%d.%02d'` is contract.** Week 5 is `2026.05`. An f-string `f"{num}.{num6}"` gives `2026.5`, which is a different number in a `numeric(6,2)` column.
6. **Never build a `Decimal` from a `float`.** `Decimal(2026.01)` is `2026.0100000000000477...`; `Decimal("2026.01")` is exact. The string twin is the source of the decimal twin, always.
7. **Do not assert against `WO_N_Header.Week_No`** (§2.2). The test file carries the reason at the top so the next reader does not re-add it.
8. **`getDayOfYear` is 1-based** on both sides (`tm_yday`), so no off-by-one adjustment — and do not "fix" one in.
9. **The depth guard is unreachable in practice** (one level of recursion, into 31 December of the previous year, which never itself yields `num6 == 0`). Keep it anyway; it is the source's shape and costs one line.
10. **This is a `core/` module, not a `planner/` one** (Port Spec §2) — the PM engine, the Night Shift job and the planner all want it later.

## 5. Test plan — `backend/tests/test_weekno.py` 1.0.0, zero DB

Zero DB and actually zero DB: the module imports `datetime`, `decimal` and `math`, nothing else — check the import graph, not just the assertions (Ways of Working §4).

| Test | Cases | What it pins |
|---|---|---|
| `test_matches_the_kt_sql_function` | **13** | the §2.3 table, parametrised — the pasted values, not recomputed ones |
| `test_iso_equivalent_2000_to_2040` | 1 | all 14,976 dates against `date.isocalendar()` — `pm_engine`'s own claim, reproduced in the suite instead of quoted |
| `test_num6_zero_recurses_into_the_previous_year` | 1 | 2021-01-01 → `2020.53` |
| `test_over_52_resets_to_week_one` | 1 | 2019-12-30 → `2020.01` |
| `test_flag_keeps_week_53` | 1 | 2020-12-31 → `2020.53` |
| `test_week_is_zero_padded` | **3** | weeks 1, 5 and 53 render `.01`, `.05`, `.53` |
| `test_week_no_is_an_exact_decimal` | 1 | `week_no(2026-01-01) == Decimal("2026.01")` and its `exponent` is `-2` |
| `test_week_no_fits_numeric_6_2` | 1 | every value in the §2.3 table has ≤ 4 integer digits and scale 2 (§2.4) |
| `test_accepts_date_and_datetime` | 1 | a `datetime` with a time of day gives the same answer as its `date` |
| `test_none_raises_value_error` | 1 | the `_weekNoFor` behaviour at 765 |
| `test_ported_from_names_the_source` | 1 | `PORTED_FROM == "workmate.pm_engine 2.5.0"` (OD-10) |

**The docstring at the top of the file records what is deliberately absent:** no test reads a database, and `WO_N_Header.Week_No` is **not** an oracle for this function, with §2.2's two-value rows as the reason.

### 5.1 Counts, predicted

**25 new cases.** Backend today is **169 passed, 2 skipped**; predicted **194 passed, 2 skipped**, exit 0. The 2 skipped must stay 2 — this slice opens no connection, so a third skip means something else moved. Frontend **170 in 11 files**, untouched, not re-run beyond the standing check.

The figure at the gate is the card's own `def test_` count plus its `parametrize` rows, read before the run — S1j predicted 167 for 169 by carrying a stale count (log 09-14 1.1.0 §6.3), so the number above is re-derived from card 2 at the drop, not from this table.

## 6. Open decisions — 🤙 required

| ID | Question | Proposal |
|---|---|---|
| **OD-48** | What does the port return? The oracle's `weekNo()` returns `float('%d.%02d')` (`pm_engine` 521–529). | **Two twins, no float.** `week_no_and_year(d) -> str` is byte-1:1 with the source's `_netWeekNoAndYear` and is the primary artefact; `week_no(d) -> Decimal` is built **from that string** for the column write. The float is dropped. Reasons: `Week_No` is `numeric(6,2)` NOT NULL (§2.4) and `2026.01` is not exactly representable as a float, so a float round-trips through the driver as a value nobody chose; a test that pins a contract value by float equality is a trap; and `Decimal("2026.01")` is exact with scale 2 by construction. **Not a contract change** — `wos[].weekNo` on the wire still comes from `repo._wo_dict`'s `f_(r["Week_No"])`, reading the column, untouched by this slice. It *is* a departure from byte-1:1 on the return type, so it is recorded as one, and `PORTED_FROM` stays `2.5.0`. The alternative (keep the float, convert at the call site) puts the same decision in S2b where it is harder to see. |
| **OD-49** | Port Spec §8 names three references for `test_weekno.py`. §2 says two of them are not what the doc thought. | **Strike reference 3, reclassify reference 2, add a standing gate.** (a) `WO_N_Header.Week_No` is **not a reference** — it is copied from the subtask at release and one start date carries up to four values (§2.2); the test file records this so it is not re-added. (b) `dbWorkmate_KT.dbo.GetWeekNoAndYear` is an **equivalence oracle, not a transcription** — ISO-8601, an orphan at KT, never called; its thirteen answers are pinned as a table (§2.3). (c) The standing gate is `date.isocalendar()` over 2000–2040, which reproduces `pm_engine`'s equivalence claim inside the suite. Net: the port is pinned against the source line-for-line, against the SQL function on thirteen branch dates, and against ISO on 14,976. The Port Spec §8 bullet and §2's `weekno` row are corrected in the next doc set (§9.1). |

**No OD is needed for:** the module path (`app/core/weekno.py`, Port Spec §2), the `# ruff: noqa: UP031` pragma (Landmines §D, `rules.py`'s precedent), or `ValueError` on `None` (the `_weekNoFor` behaviour in Python's idiom).

## 7. Smoke

Nothing below opens a database or starts a server. Cards 1–2 dropped and `Test-Path`-verified first, in their own block.

```
cd C:\dev\workmate-saas\backend
uv run ruff format .
uv run ruff check .
uv run pytest
"pytest exit $LASTEXITCODE"
```

Read the count against **`194 passed, 2 skipped`** (the figure re-derived from card 2 at the drop). Then the module's own answers, printed once so they are in the log next to the evidence:

```
cd C:\dev\workmate-saas\backend
uv run python -c "from datetime import date; from app.core import weekno as w; [print(d, w.week_no_and_year(date.fromisoformat(d)), w.week_no(date.fromisoformat(d))) for d in ('2019-12-30','2020-12-31','2021-01-01','2025-12-28','2026-01-01','2026-09-14','2026-12-21')]"
```

Expect `2020.01 · 2020.53 · 2020.53 · 2025.52 · 2026.01 · 2026.38 · 2026.52`, each with an exact `Decimal` twin. Then commit: **2 staged paths, 0 deletions** (plus this spec if it is saved out of Downloads before the block runs — `f851889`'s precedent, and the third slice running); tag `s2a-weekno-1.0.0`.

## 8. Acceptance

- Two cards in §1, no third. Every other backend module, every frontend file and every other test untouched.
- No database opened, no server started, nothing written anywhere.
- `194 passed, 2 skipped`, exit 0, read from the run — and **still exactly 2 skipped**.
- The thirteen pinned values equal the SQL function's pasted answers; the 2000–2040 gate is green.
- `ruff format .` reports nothing after the drop (format-clean before commit — the `router.py` 1.1.1 lesson).
- `PORTED_FROM` is `workmate.pm_engine 2.5.0`; header `Version:` and `__version__` agree, checked mechanically before the cards are cut.

## 9. Consequences

### 9.1 Doc corrections for the next compiled set

- **Port Spec §8** `test_weekno.py` bullet: three references → the OD-49 set, with `WO_N_Header.Week_No` named as **not** an oracle and why. **§2** the `pm_engine.weekNo` row: same correction, and the SQL function described as an ISO rewrite. **§6** the S2 row splits into S2a…S2d (§9.2); **§9** OD-48 and OD-49 with their gate.
- **Landmines §E** the `Week_No` line: it is copied from the subtask at release and is not a function of the start date — one start date carries up to four values; the `.NET` algorithm is ISO-equivalent on 14,976 dates 2000–2040, and KT's `GetWeekNoAndYear` is an ISO rewrite, an orphan, never called. **§D** gains the Ignition-0-based-months trap.
- **Architecture §5** the tree gains `app/core/weekno.py`; **§3.1** the tests row → 194.
- **Index** §1 state, §3.4 / §3.5 the two new files, §6 next → S2b.

### 9.2 Where the rest of S2 went

**S2b** the write core (`sql.py`, `repo.load_wo`, `service.move_wo/undo_move/set_estimate/move_preview` + tests; `dry_run=True` first — the first slice that writes **data** to RST; its audit reads `WO_N_Subtasks`, `WO_Event_History`, `WO_N_Resource` and the landed `WO_N_Plan` on RST before any OD). **S2c** the write routes (`schemas.py`, `router.py`, `test_planner_api`; `Depends(get_current_actor)` unchanged). **S2d** the frontend (`@dnd-kit`, `ConfirmMoveDialog`, `UndoToast`, optimistic rollback).

**The JWT swap is out of S2 entirely.** OD-12 puts it "in S2", but OD-2 (which RST `Users` map to logins) is open and waiting on Andrew's list, `app/auth/` is in no slice, and D-5 wants an `App_User` migration plus argon2 — an unsigned dependency is the next audit's first line, not a step in this build. The routes take the same dependency either way, so the swap stays a one-line change.

**Item 37 does not land in S2a–S2d** — none of them touches `WO_RANGE_*`.

### 9.3 New open items

- **44** — `moveRules`'s `ENGINE_OWNED` message still reads *"run the S3 DDL (WO_N_Plan) to allow planner pins"* (`rules.py` 1.1.0, 559). Wrong twice since `0001`: the table came with the uplift, not S3, and on RST the branch is now unreachable. It is still reachable on a client database before migration, and fixing it edits a byte-1:1 parity string (OD-34's territory). A decision, not a defect — raise it when a second site exists.
- **45** — `Server_Name = 'Perspective'` is hardcoded in **two** places, not one: `_eventRow` (`planner` 1.3.1, 791) and `_upsertPin` (1128). OD-3 swaps it to `'SaaS'` in S2b; both sites, or the pin rows lie about their origin.

## 10. Changelog

- 1.0.0 (2026-09-15) Initial. Written from the S2 audit: the outstanding `GetWeekNoAndYear` body read from `dbWorkmate_KT.sys.sql_modules`, both databases' `(start, Week_No)` pairs read, the `Week_No` column types read, and the transcribed algorithm run against all three before anything was proposed (§2). Two of the Port Spec's three references turned out not to be references; OD-49 replaces them. Raises OD-48 and OD-49, and open items 44 and 45. Cuts S2 into S2a…S2d and puts the JWT swap outside it (§9.2).
