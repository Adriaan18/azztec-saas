# Azztec SaaS — Raw session log 2026-09-15 (doc set applied + the S2 audit + S2a weekno)

**File:** Azztec_SaaS_Raw_Log_2026-09-15_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-15 · **Author:** Adriaan

**Session:** the doc set from log 2026-09-14 1.1.0 §8 applied, then the **S2 audit**, then **S2a built and shipped**. The session ran past midnight — the S2a drops and smoke carry box timestamps of 16/09. **Nothing was written to any database.** `dbWorkmate` was read only for schema and `Week_No` pairs; `dbWorkmate_KT` was read over Windows auth and is still `READ_ONLY`; `dbWorkmate_KT_RFID` was not touched.

Supersedes log 2026-09-14 1.1.0 §8 (applied), §9 and §10. That log's §1–§7 still stand for the uplift audit and S1j.

## 1. Decisions signed this session

| ID | Decision | Gate |
|---|---|---|
| **OD-48** | The weekno port returns **two twins and no float**. `week_no_and_year(d) -> str` is byte-1:1 with `pm_engine` 2.5.0's `_netWeekNoAndYear` and is the primary artefact; `week_no(d) -> Decimal` is built **from that string**, never from a float. The oracle's `float('%d.%02d')` is dropped: `Week_No` is `numeric(6,2)` NOT NULL (§5.4) and `2026.01` is not exactly representable as a float, so a float round-trips through the driver as a value nobody chose and pins badly in a test. **Not a contract change** — `wos[].weekNo` on the wire still comes from `repo._wo_dict` reading the column. It *is* a departure on the return type, recorded as one; `PORTED_FROM` stays `2.5.0` | 🤙 |
| **OD-49** | **The three references in Port Spec §8 are not three.** (a) `WO_N_Header.Week_No` is **struck as a reference** — it is copied from the subtask at release and never recomputed, so it is not a function of the start date at all (§5.2); the test file carries the reason so nobody re-adds it. (b) `dbWorkmate_KT.dbo.GetWeekNoAndYear` is reclassified from "a second transcription" to an **equivalence oracle** — it is an ISO-8601 rewrite and an orphan at KT (§5.1); its answers on thirteen branch dates are pinned as a table. (c) The standing gate is `date.isocalendar()` across 2000–2040, which reproduces `pm_engine`'s own equivalence claim inside the suite instead of quoting it | 🤙 |

## 2. Shipped and committed

**Doc set** (`b0d3a4f`): Index **1.8.0**, Landmines **1.8.0**, Ways of Working **1.3.5**, Port Spec **1.0.6**, Architecture **1.0.7** — five cards, **1027 insertions**, the 2026-09-14 1.1.0 §8 queue applied in full. 118 anchored edits, every anchor asserted to match exactly once before the card was cut; headers checked against filenames mechanically; a stale-pointer sweep caught three `uplift-audit question N` references that the queue had not listed (§6.2).

**S2a** (`5a4802a`, tag **`s2a-weekno-1.0.1`**) — 3 paths, 548 insertions, 0 deletions:

| File | Version | Note |
|---|---|---|
| `backend/app/core/weekno.py` | **1.0.0** | new — the verbatim `_netWeekNoAndYear` port + `week_no_and_year()` / `week_no()` (OD-48). Pure: no I/O, no SQL, no logging. File-wide `# ruff: noqa: UP031` — the `'%d.%02d'` expression *is* the contract value |
| `backend/tests/test_weekno.py` | **1.0.1** | new — pair of the module, **zero DB**, 25 cases (§5.5). 1.0.0 was superseded before the commit (§6.1) and never reached the repo |
| `docs/…S2a…Chunk_Spec_v1_0_0.md` | 1.0.0 | the spec, inside the slice commit — third slice running |

The module ships with **no caller** — S2b's `service.move_wo` is its first. Deliberate: it is the only part of the write stack that can be built and proved without touching RST.

## 3. Suite state

Backend **194 passed, 2 skipped**, exit 0 (13.43 s, then 5.27 s). Frontend **170 in 11 files**, exit 0 — untouched, no frontend file is in this slice. `uv run alembic current` → **`0001 (head)`**.

The **2 skipped** are still the two OD-1 tests in `test_planner_repo.py`, and S2a had to keep them at exactly 2: this slice opens no connection, so a third skip would mean something else moved.

## 4. The S2 audit

### 4.1 What the read-through changed before any OD was signed

1. **The pure half is already built.** `rules.py` 1.1.0 carries `moveRules` (533–631), `estimateRules` (634–652) and `labourRules` (655) byte-1:1 with the oracle at 856/906, green at 70 cases. **S2 does not touch `rules.py`** — the biggest parity risk was already retired, and what is left is SQL, transactions, routes and UI.
2. **The scope as handed is four slices, not one.** S2a weekno · S2b the write core · S2c the write routes · S2d the frontend (§10).
3. **The JWT swap comes out of S2 entirely.** OD-12 puts it "in S2", but OD-2 (which RST `Users` map to logins) is **open** and waiting on Andrew's list, `app/auth/` appears in no slice, and D-5 wants an `App_User` migration plus argon2. An unsigned dependency is the next audit's first line, not a step in this build. The routes take `Depends(get_current_actor)` and do not care what fills it, so the swap stays a one-line change.
4. **Item 37 does not land in S2a–S2d** — none of them touches `WO_RANGE_*`.

### 4.2 Two strings the port would carry verbatim, both now false

- `moveRules`'s `ENGINE_OWNED` message reads *"run the S3 DDL (WO_N_Plan) to allow planner pins"* (`rules.py` 1.1.0, 559). Wrong twice since `0001`: the table came with the uplift, not S3, and on RST the branch is unreachable. Still reachable on a client database before migration, and fixing it edits a byte-1:1 parity string — **item 44**, a decision, not a defect.
- `Server_Name = 'Perspective'` is hardcoded in **two** places, not one: `_eventRow` (`planner` 1.3.1, 791) and `_upsertPin` (1128). OD-3 swaps it to `'SaaS'` in S2b; both sites, or the pin rows lie about their origin — **item 45**.

## 5. Facts verified this session

### 5.1 The KT function is an ISO rewrite, not a transcription

`dbWorkmate_KT.dbo.GetWeekNoAndYear`, read through `dbWorkmate_KT.sys.sql_modules` joined to `.sys.objects` / `.sys.schemas` (never `OBJECT_DEFINITION()`): `DATEPART(ISO_WEEK, @date)` plus the two-case week-year adjustment (week ≥ 52 in January → previous year; week 1 in December → next year), `FORMAT(@isoYear,'0000') + '.' + RIGHT('0' + …, 2)`. It is ISO-8601, not a line-for-line copy of `clsGeneralOperation.GetWeekNoANDYear`, and it is an orphan at KT (gateway references 0, dependencies 0), so nothing has ever called it. **Answers the outstanding query carried since 2026-09-13.**

### 5.2 `Week_No` is not a function of the start date — on either database

Distinct `(Request_Start_Date, Week_No)` pairs:

```
KT  2026-09-17 -> 2026.35, 2026.36, 2026.37, 2026.38     (four values, one start date)
RST 2026-01-01 -> 2025.53, 2026.01
RST 2025-12-31 -> 2025.53, 2026.01
RST 2025-12-29 -> 2025.53, 2026.01
RST 2025-12-28 -> 2025.52, 2025.53
```

And 2025 has no ISO week 53 at all (1 Jan 2025 was a Wednesday, non-leap). This is exactly what `pm_engine` 2.5.0 says at 476: **`WO_N_Header.Week_No` is COPIED from the subtask, never recomputed** — it is the PM's *release* week, and the start date has moved since. A test asserting `week_no(start) == Week_No` would have gone red against perfectly good data on **both** databases: the same class as `test_range_priority_order_is_not_alphabetical`, except the premise is wrong everywhere rather than on one site. The Port Spec had it listed as a reference for a year.

### 5.3 The port agrees with both, measured

Thirteen branch dates against the function's own answers, run before the cards were written: `2019-12-30 → 2020.01` (the `num6 > 52 and not flag` reset) · `2020-12-31 → 2020.53` (`flag` keeps week 53) · `2021-01-01 → 2020.53` (`num6 == 0` recurses) · `2025-12-26/28 → 2025.52` · `2025-12-29/31 → 2026.01` · `2026-01-01/03/04 → 2026.01` · `2026-09-07 → 2026.37` · **`2026-09-14 → 2026.38`** (the Port Spec §8 figure, now checked rather than recalled) · `2026-12-21 → 2026.52`. **Thirteen for thirteen**, and `.NET` = SQL function = ISO on every one.

Across 2000-01-01 … 2040-12-31: **14,976 dates, 0 disagreements** with `date.isocalendar()`. `pm_engine`'s comment at 477 says 14,975 — off by one, the range is inclusive at both ends. Nothing turns on it; recorded because the count was read, not repeated.

### 5.4 The columns the value is written into

`WO_N_Header.Week_No` **numeric(6,2) NOT NULL** · `WO_N_Subtasks.Week_No` numeric(18,2) NULL · `WO_C_header.Week_No` numeric(6,2) NULL. Four digits before the point, two after — which is what `'%d.%02d'` produces and what a two-digit week needs. This is what killed the float (OD-48).

### 5.5 The module's own answers, in the smoke

`2019-12-30 2020.01 Decimal('2020.01')` · `2020-12-31 2020.53` · `2021-01-01 2020.53` · `2025-12-28 2025.52` · `2026-01-01 2026.01` · `2026-09-14 2026.38` · `2026-12-21 2026.52` — every string with an exact `Decimal` twin, scale 2, no float anywhere.

25 cases: 13 pinned against the SQL function, 1 ISO gate over 14,976 dates, 3 branch cases, 3 zero-padding, and one each for the exact decimal, the `numeric(6,2)` fit, `date` vs `datetime`, `ValueError` on bad input, and `PORTED_FROM`.

### 5.6 The box

7.8 GB free of 31.4, Docker absent from the top five, two `java` processes (the Ignition gateway on the RFID copy) at 2.87 and 1.29 GB. `/range` was not exercised — no slice touched it.

## 6. Mistakes caught this session

### 6.1 The `UP031` pragma went on the module and not on its pair — and the lint was right twice

`ruff check` exit 1: `UP031` on `test_weekno.py:85`, where the ISO gate built its expected value with `"%d.%02d" % (y, w)` — the module's own expression. The spec (§3.1) put the file-wide pragma on `weekno.py` and never asked whether the test needed one.

The pragma would have been the **wrong fix**. A gate that formats the way the thing it is checking formats is partly circular: it would have agreed with a module that zero-padded wrongly in exactly the same way. Rewritten as `f"{y}.{w:02d}"` — independent of the implementation, and no pragma needed. Shipped as `test_weekno.py` **1.0.1**, flagged before it was built, `test_planner_repo.py` 1.0.2's precedent; the module stayed 1.0.0 and the tag became `s2a-weekno-1.0.1` (tag what shipped). **A lint rule can be right about the code and right about the test design at the same time.**

### 6.2 Project knowledge was not clean at the open, and the Index said it was

Index 1.7.0 §6.2 ended "after this docs commit, remove by hand: Index 1.6.0, Landmines 1.6.0, WoW 1.3.3, Architecture 1.0.5, Port Spec 1.0.4". That hand step was **missed** at the close of the second 09-14 session, so this session opened with five superseded compiled docs in project knowledge — plus `scripts_kt_uplift_ddl` 1.0.0 and `test_kt_uplift` 1.0.0 (both superseded mid-slice, never in the repo) and `pyproject` 1.0.0. Eight files. Index 1.8.0 §6.2 records it as **not clean** rather than asserting clean, and names all thirteen removals. The check has to be run against the project files at the *open*, not trusted from the previous Index's promise.

### 6.3 The doc-correction queue missed three stale pointers

The queue named the sections to rewrite. It did not name `Architecture` D-5 / D-12 and `Port Spec` OD-2, which each still said "uplift-audit question 5/6" for questions the uplift audit had **handed on** rather than answered (Q5 to the D-5 auth audit, Q6 to D-12's existing text). Found by grepping the cut files for the phrase, not by reading the queue. **A queue is a list of what changed, not a list of everywhere the change is referenced** — the grep is the gate.

### 6.4 Two predictions, one wrong

- **`29 files left unchanged` predicted, `28` observed.** Both cards had already been dropped before the *first* smoke, so replacing one of them could not raise the count. Mis-modelled the state, not the tree.
- **`1027 insertions` predicted exactly** for the docs commit — computed as the sum of the five cut files' line counts (211 + 235 + 199 + 235 + 147), not guessed. `3 / 0` and `5 / 0` staged-path predictions both held, and `194 passed, 2 skipped` held with the case count re-derived from the card rather than from the spec table (the S1j lesson applied).

### 6.5 An anchor written from memory, refused by the helper

The 1.0.1 edit's second anchor was a docstring passage typed from recollection; it matched zero times and the helper aborted before writing anything. Re-read the file, took the exact text, four edits landed. **The edit helper asserting "exactly one match" is what turned a memory error into a five-second retry instead of a half-written file** — and the write-at-the-end shape is why nothing was left inconsistent.

## 7. Patterns confirmed

- **Read the reference before trusting the doc that names it.** Two of Port Spec §8's three weekno references turned out not to be references at all. The doc had carried them since 1.0.0 and every reissue since re-stated them.
- **Run the claim, don't quote it.** `pm_engine`'s comment asserts ISO equivalence over 2000–2040; reproducing it in the suite cost four lines and turned a comment into a gate (and found the off-by-one in the count).
- **Evidence goes in the spec before the 🤙.** Every value in the pinned table was read off the box and pasted into §2 of the spec; the test file's constants were copied from there, not recomputed.
- **The `Test-Path`-first Downloads block held** — sixth session running, five doc cards, then three slice cards, then one replacement. Zero losses.
- **Predict, then read** caught the one wrong number and confirmed four right ones (§6.4).
- **A superseded card must leave project knowledge the same day** — §6.2 is the third time a hand step has been the weak link, and the first time it was found by checking instead of by a later mistake.

## 8. Doc-correction queue

**For the next session, applied before anything else.** Target: Index **1.9.0**, Landmines **1.9.0**, Ways of Working **1.3.6**, Port Spec **1.0.7**, Architecture **1.0.8**.

1. **Port Spec** — §2 the `pm_engine.weekNo` row → the OD-49 reference set, the SQL function described as an ISO rewrite and an orphan; §6 the S2 row **splits into S2a…S2d** with the S2a row done (tag, the three paths, 194/2, the pinned table) and the JWT swap recorded as outside S2; §8 the `test_weekno.py` bullet rewritten — `WO_N_Header.Week_No` named as **not** an oracle with §5.2's evidence; §9 OD-48 and OD-49 with their gate, items 44 and 45 raised, OD-12's "swapped in S2" corrected to "swapped when auth gets its slice".
2. **Landmines** — §E the `Week_No` line: copied from the subtask at release, not a function of the start date, the four-value evidence, ISO-equivalent on 14,976 dates, and KT's `GetWeekNoAndYear` as an ISO rewrite that nothing calls; §D a new line — Ignition months are **zero-based**, so `getDate(year, 0, 1)` is 1 January and `(year, 11, 31)` is 31 December, and a literal transcription gives a crash or an 11 November that passes most days of the year.
3. **Ways of Working** — §4 or §6: **a test that builds its expected value with the implementation's own expression is not an independent gate** (§6.1); §9 or §2: the superseded-out hand step is checked against the project files at the **open** of a session, never trusted from the previous Index (§6.2); and a doc-correction queue is a list of what changed — grep the cut files for every reference to it (§6.3).
4. **Architecture** — §5 the tree gains `backend/app/core/weekno.py`; §3.1 the tests row → 194 passed, 2 skipped; §4 D-4 or §3.1 may note that `core/` now holds a ported pure module the planner, the PM engine and the Night Shift job all want.
5. **Index** — §1 state (S2a shipped, HEAD `5a4802a`, tag `s2a-weekno-1.0.1`, 194/2 and 170, OD-48/OD-49, items 44–45, nothing written to any database); §2 read order leads with this log; §3.4/§3.5 the two new files; §4 the new rules; §5 the HEAD chain and the new tag; §6 next = the **S2b audit**; §6.1 OD-48/OD-49 and the numbering hazard (OD series 49, item series 45); §6.2 rebuilt from the project files, with the thirteen removals from 1.8.0 §6.2 confirmed done or still outstanding.

## 9. Open items (20)

**Closed this session:** none of the numbered items. The **outstanding `GetWeekNoAndYear` query** (carried since 2026-09-13, never numbered) is answered — §5.1. Arithmetic: 18 open at the close of 2026-09-14 1.1.0, plus 44 and 45 = **20**, and the table below has 20 rows.

| # | Item |
|---|---|
| 4 | 6M summary shape |
| 17 | Docker first clean start under the `.wslconfig` cap — also gates item 42 |
| 24 | hidden-tab poll |
| 25 | prettier not in smoke |
| 26 | `scripts/parity_range.py` — carries an expected diff on `workers[].initials` (OD-35); reads the oracle over Windows auth (OD-45), no user, no flip |
| 27 | `CapacityBar` 1.0.1 taking `nWorkers` |
| 28 | `/_diag/client`, `?debug=1` |
| 31 | Forensics pack, set aside |
| 33 | tips ⓘ, first non-port component — its own audit |
| 34 | carry-backs to KT: the `initialsOf` fix, the `.chip{flex:none}` line, item 43's list. **DDL scripts, never files** |
| 35 | role tokens still skew initials (`R2`, `NS`, `SUP`, `CALLOUT`, `PROJECT`) — asserted **unfixed** in `test_planner_rules.py` 1.1.0 |
| 37 | the WO `/range` select goes parallel, 47k logical reads, five per-row correlated subqueries. No penalty measured on an empty pin table; the rewrite is owed, the urgency is not. **Not in S2a–S2d** |
| 38 | Starlette wants `httpx2` for `TestClient`; `anyio.abc.BlockingPortal` deprecated |
| 39 | `/health`'s own `version` field is the only version not asserted against a module constant — one line, its own `test_smoke` 1.2.0 card |
| 40 | Ignition RFID on `dbWorkmate_KT_RFID` — carry-backs to KT are DDL scripts, never files |
| 41 | `WO_RANGE_PINNED`'s cost on a **populated** `WO_N_Plan` is unmeasured; re-measure once S2 has pinned rows |
| 42 | the PG rendering of `0001` is committed and pinned by test but has **never executed**; gated on item 17 |
| 43 | carry-backs found by the uplift audit (into 34's list) |
| **44** | **New.** `moveRules`'s `ENGINE_OWNED` message still says *"run the S3 DDL (WO_N_Plan)"* — wrong twice since `0001`, unreachable on RST, reachable on a client DB before migration. Fixing it edits a byte-1:1 parity string (OD-34's territory). A decision, not a defect |
| **45** | **New.** `Server_Name = 'Perspective'` is hardcoded in **two** places — `_eventRow` (791) and `_upsertPin` (1128). OD-3's swap to `'SaaS'` must hit both, in S2b |

**Numbering hazard, still live:** the OD series is at **49** and the open-item series at **45**. `OD-44`/item 44 and `OD-45`/item 45 are different things — always carry the `OD-` prefix.

## 10. Next

1. **The doc set (§8).** Then audit from the docs, not this log. The thirteen project-knowledge removals in Index 1.8.0 §6.2 are the first hand step, checked against the project files, not assumed.
2. **The S2b audit** — the write core, and the first slice that writes **data** to RST. Its evidence, read before any OD: `WO_N_Subtasks` (does `Req_Start_Date` / `Week_No` exist on RST, and how many rows per WO), `WO_Event_History` (column names, `event_details` at varchar(1000) → the 990 cap, `server_name` and `Source_Form` lengths), `WO_N_Resource` (`Res_Date`, `Resource_Type 'L'`), and `WO_N_Plan` as `0001` landed it (`Note` length, `Prev_Start` type, `Server_Name` length). Then: the portable renderings of `DATEADD` / `GETDATE()` / `ISNULL` / the subtask date-window trick; `_upsertPin`'s UPDATE-then-INSERT with `Prev_Start` written on the **first** pin only; OD-3's two sites (item 45); `dry_run=True` first, Marker Law after; and a deliberately chosen WO moved and moved back.
3. **Then S2c** (write routes, `Depends(get_current_actor)` unchanged) and **S2d** (dnd-kit, confirm dialog, undo toast, optimistic rollback).
4. **The auth audit, whenever wanted** — OD-2's identity list, `App_User` inheriting `Ignition_User_Map`'s shape (delta Q5, D-5), and only then OD-12's swap.
5. Not slices: item 40's RFID work, item 33's tips ⓘ, item 39's one-line test, item 42's PG run once Docker starts clean.

## 11. Changelog

- 1.0.0 (2026-09-15) The doc set from log 2026-09-14 1.1.0 §8 applied (`b0d3a4f`, five cards, 1027 insertions), the S2 audit, S2a built and shipped (`5a4802a`, tag `s2a-weekno-1.0.1`). OD-48 and OD-49 signed at the gate. The outstanding `GetWeekNoAndYear` query answered — and two of the Port Spec's three weekno references turned out not to be references. S2 cut into S2a…S2d with the JWT swap moved outside it. Items 44 and 45 raised; the open list goes to 20. Nothing was written to any database. Supersedes log 2026-09-14 1.1.0 §8, §9 and §10.
