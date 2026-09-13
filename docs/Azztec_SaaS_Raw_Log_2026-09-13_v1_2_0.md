# Azztec SaaS — Raw session log 2026-09-13 (backend audit + S1h)

**File:** Azztec_SaaS_Raw_Log_2026-09-13_v1_2_0.md · **Version:** 1.2.0 · **Date:** 2026-09-13 · **Author:** Adriaan
**Append-only.** Supersedes §8 (open list) and §9 (next slice) of `Azztec_SaaS_Raw_Log_2026-09-13_v1_1_0.md`; that log's §1–§7 still stand, and its §6 correction queue is now **applied** (§2 below).
**Session:** the third of 2026-09-13, running past midnight into 09-14 on the box clock. The doc set from 1.1.0 §6, then the **backend audit** (items 30, 29, 21), then **S1h built and shipped**. Nothing was written to any database.
**Ended at:** HEAD `85d4e95`, tree clean, tag `s1h-priority-initials-1.1.0` at `5443ac1`. Backend **156 passed** (exit 0, 5.44 s), frontend **155 passed in 11 files** (exit 0).

---

## 1. Decisions signed this session

| ID | Decision | How |
|---|---|---|
| **OD-36** | `Priority.colour` ships the column as stored, `''` for NULL, validated nowhere in the backend. No enum, no hex check, no default — a backend default would be indistinguishable from real data downstream. | **🤙 signed** |
| **OD-37** | `router.__version__` → 1.1.0 for a field added inside a sub-model, version line only. `apiVersion` is the only contract signal a generated client sees; a client pinned to 1.0.1 must not be able to receive two shapes. Same reasoning takes `rules.py` to 1.1.0 rather than a patch. | **🤙 signed** |
| **OD-35** | `initialsOf` departs from the oracle: bracketed segments come out of the name before the first-and-last pick. The parity script (item 26) must carry `workers[].initials` as an **expected** diff. | **Delegated, not signed** — "sounds good, do what you think works best". Recorded as delegated deliberately: Ways of Working §1 says "looks good" is not 🤙, and this is the OD with a downstream consequence, so the distinction is worth keeping in the record. Taken exactly as the spec §6 proposed. |

## 2. Shipped and committed

| Commit | Content |
|---|---|
| **`4db5932`** | the compiled set from log 1.1.0 §6 — Index **1.5.0**, Landmines **1.5.0**, Ways of Working **1.3.2**, Architecture **1.0.4**, Port Spec **1.0.3**. 5 files, 943 insertions |
| **`5443ac1`** | **S1h** — `sql.py` 1.1.0, `repo.py` 1.1.0, `schemas.py` 1.1.0, `rules.py` 1.1.0, `router.py` 1.1.0, `test_planner_rules.py` 1.1.0, `test_planner_api.py` 1.1.0, `test_planner_repo.py` 1.0.2. 8 files, 308 insertions, 40 deletions. Tag `s1h-priority-initials-1.1.0` |
| **`85d4e95`** | `Azztec_SaaS_S1h_Priority_Initials_Chunk_Spec_v1_0_0.md`, 341 insertions |

`c905c67` (log 1.1.0 + the four `docs/reference/` oracle files) had already landed before this session opened, so the doc set was one clean commit of exactly five files. **Still to remove by hand from project knowledge:** Index 1.4.0, Landmines 1.4.0, WoW 1.3.1, Architecture 1.0.3, Port Spec 1.0.2. Raw logs stay.

## 3. Suite state

Backend `uv run pytest`: **156 passed, 2 warnings in 5.44 s**, exit 0. The arithmetic checks out and was predicted before the run: 125 + 26 (new `initialsOf` cases, parametrised) + 5 (priority colour) = 156. `tests/test_planner_rules.py` alone reads **70 passed in 0.08 s**, against a 44 baseline. Frontend `pnpm test`: **155 passed in 11 files**, exit 0, unchanged — S1h touched no frontend file and did not regenerate the client. Ruff clean across all eight files.

## 4. The backend audit

### 4.1 Item 30 — the alternating `/range` latency is **not reproducible**, and the instance is why

Two blocks of evidence on a box with 18.1 GB free, no Docker, `sqlservr` at 0.44 GB:

- **Eight singles at 20 s spacing:** HTTP 402–496 ms, the API's own `ms` 333–419. Inside SQL, per request: the WO select 168–216 ms, labour 67–123 ms, `has_table` 0 ms. One pooled `svc_workmate` session throughout, `newest_login` never moved.
- **Five-wide burst:** all five done in **1.94 s** wall clock, each 1.2–1.9 s. Not the 9.8–11.7 s each recorded pre-reboot. Five requests sharing a box, which is what linear scaling looks like.
- **Pool rotation after the burst:** the pool grew 1 → 5 on demand, then six singles rotated through sessions 82, 55, 65, 57, 56, 55, 65 — every one +68k logical reads, every one 330–440 ms. **No slow connection in the rotation**, which kills the "three bad connections in a five-connection FIFO" hypothesis that the pre-reboot 1.2/8.1/1.2/8.1/9.7/1.2 sequence suggested.
- `plan_generation_num` 1 on every statement — no recompiles. Per-session waits are exchange (`CXSYNC_PORT`, `CXCONSUMER`, `LATCH_EX`) plus `ASYNC_NETWORK_IO` shipping a 2.2 MB payload: normal for a parallel plan streaming 3221 rows.

All three hypotheses named in the item — the four `text()` selects, the pool, plan reuse — are disproven on this instance. **What changed is the instance, not the code.** Before the reboot, SQL had been squeezed to a 0.1 GB working set by Docker and *never restarted*: `max server memory` was raised and Docker shut down, the box read clean, and SQL was still faulting its buffer pool back in the whole time. `sqlserver_start_time` 16:22:41 — the reboot took that state with it, and `dm_exec_query_stats` only holds this afternoon onward.

**Status: not reproducible, protocol recorded.** The two blocks above are the reproduction script if it returns. No code change follows. `dbo.Diag_Log` does not exist on RST (`PERSIST_SQL` is `None`, migration 0004 never landed), so there is no latency history to query — it has to be reproduced live, which is worth knowing before the next attempt.

**The landmine this earns:** Landmines §F says "over 2 s is the box". It needs "…and a memory-squeezed SQL Server is still the box, for hours after the box itself reads clean. Free RAM is not a recovered buffer pool — only a restart is."

### 4.2 What the audit found on the way past

- **`has_table` runs twice per request** — `execs` climbed by exactly 2 per `/range`, once in `service.range_data` and again inside `fetch_wos`. 0 ms each, but a round trip each. Cosmetic; not fixed, not an item.
- **The WO select is the expensive one:** 47,333 logical reads per execution, ~190 ms, parallel, most of its wait in exchange. Five per-row correlated subqueries (three on `WO_N_Plan`, two `EXISTS` on the PO tables) are why. → **item 37**.
- Two new deprecation warnings in the backend suite → **item 38**.

## 5. Facts verified this session

### 5.1 `dbo.Priority` — the payload is **seven** rows on RST, not fourteen

`Active` is `1`/`0` on RST and the `NOT IN ('0','N')` filter drops half the table. Seven rows reach `priorities[]`, and **every colour among them is distinct**:

```
id  short  title           seq  colour
 1  P2     Priority 2      1    #FF9F40
 5  P1     Priority 1      1    #FF0000
 2  P3     Priority 3      2    #74EE66
12  P5     Priority 5      3    #C499C1
13  P6     Priority 6      3    #C0C0C0
 4  P4     Priority 4      4    #0080FF
 6  N/A    Not Applicable  5    #FFFFFF
```

All three `#FF0000` duplicates (WK-END, SHUT, P2S) and both `#808040`s are on **inactive** rows. Confirmed from the wire after the slice shipped: `distinct colours: 7 of 7`. Second oracle agrees on the count — `dm_exec_query_stats` reports `max_rows` 7 on that statement.

Consequence: paint-from-payload is **unambiguous on RST**, which is the opposite of what reading the fourteen-row table suggested. Ties survive the filter (P2/P1 at 1, P5/P6 at 3), so OD-11's tie-break still matters and OD-32 stays withdrawn. KT is unchanged: four rows, no ties, `#FF8000` on all four, so there the letter class is what paints. `Colour` is `varchar(255) NULL` on **both** databases — free text, no constraint, no guaranteed hex.

**Item 29's queued `DRY_RUN`-first `UPDATE dbo.Priority SET Colour` is withdrawn.** It was queued when we did not know what RST held; every active row carries a distinct, sensible value. There is nothing to repair, so item 29 turned out to be entirely read-only.

### 5.2 `initialsOf` fails in **two** ways, and only one was on the record

Every RST `User_Name` matching `LIKE '%(%'` was read — roughly 300 rows. Brackets are the rule there, not the exception, and the oracle splits into:

- **one-word bracket, visibly broken:** `JP Paalvast (TS)` → `J(`, `Aaron Wilson (Livewires)` → `A(`, `Big Mow (FORMA)` → `B(`. `(TS)`, `(Livewires)`, `(FORMA)`, `(Agsam)`, `(Boilerhouse)`, `(Lakeland)`, `(Contractor)`, `(Tradestaff)`, `(Richmond)`, `(Finnco)`.
- **multi-word bracket, silently wrong:** `parts[-1]` becomes the last word *inside* the brackets. `Adam Donald (Max Edkins)` → **`AE`**, `Terry Herangi-Kingi (Max Edkins)` → **`TE`**, `Spencer Calvert (Summer Student)` → **`SS`**, `Night Shift Primary (Livewires)` → **`NP`**. Plausible-looking initials for the wrong person, and `(Max Edkins)` alone covers dozens of active users.

Landmines §E recorded only the first class and so **understated the defect**. The second is why this stopped being cosmetic.

Edges in the real data: `Gary Colbert ( FORMA )` → `G)` from the bare `)` token; `Max Webber R2 (Max Edkins` has an unbalanced bracket (User_Id 996); `Allan Andrewson(Temp)` → `AA`, correct **by accident** because there is no space before the bracket; `Angela Southerland (no longer in us` is truncated in the column. Short ids of 2–4 characters (`BINS`, `JIMH`, `LESB`, `MAXE`, `SAMR`, `BOBS`, `TAHI`) never reach the name path at all.

Verified on the wire after the slice: **`initials still carrying a bracket: 0`**, with `JP Paalvast (TS)` → `JP`, `Adam Donald (Max Edkins)` → `AD`, and `Adam Donald R2 (Max Edkins)` → `AR` — item 35 behaving exactly as the test pins it.

## 6. Mistakes caught this session

### 6.1 Downloads ate a card for the **third** time

The S1h spec was never saved out of Downloads, so the commit that should have carried nine files carried eight and the spec needed its own follow-up commit (`85d4e95`). Landmines §A records two prior losses; this is three. The rule already exists — *save the card before the block runs, Downloads is not a staging area* — and it keeps costing. **Every block that copies from Downloads now begins with `Test-Path` on each source and prints it**, so a missing card fails loudly on line one instead of two screens later.

### 6.2 Two version constants bumped in the docstring but not in the code

`repo.py` and `schemas.py` went out of my hands with `Version: 1.1.0` in the header block and `__version__ = "1.0.0"` two lines further down. That is precisely the failure Ways of Working §2 exists to stop — *the `__version__` constant is bumped with the header, or `/health` lies*. Caught by a scripted header-vs-constant comparison across all five modules before the cards were emitted, not by reading. **The check is mechanical and belongs in every build from now on:** parse `^Version:` and `__version__` out of each file and assert they agree.

### 6.3 A test I wrote would have failed on the KT copy — on correct data

`test_range_priority_order_is_not_alphabetical` asserted that the priority shorts are not in alphabetical order. True on RST (P2, P1, P3, P5, P6, P4, N/A). **False on KT**, whose shorts are A, B, C, D and legitimately *are* alphabetical. It would have gone red against a perfectly good database. Replaced with a control-query comparison, which is robust on both and guards more: `repo → service → schema → JSON` cannot quietly reorder. Same trap the spec's own §5.2 warned about — *seven rows is one database's state on one day, not a contract* — and I walked into the adjacent version of it two hours later. **A test whose pass depends on which database it is pointed at is a data assertion wearing a port assertion's clothes.**

### 6.4 The eighth file the spec said would not exist

`repo.py`'s `Pair:` line pointed at `test_planner_repo.py 1.0.0` when the project holds 1.0.1, and that file's own `Pair of:` line pointed at `sql.py 1.0.1 + repo.py 1.0.0` — both stale the moment `PRIORITIES` gained a column. The spec's §8 said "seven files, no eighth". Shipping a knowingly false header to protect a scope line would have been the wrong trade, so `test_planner_repo.py` went out as **1.0.2, header only** — flagged before it was built, not slipped in. Its assertions needed nothing: it checks the port, not the data, and both of its `sql.py` gates (the `MSSQL_ONLY` regex and the colon-in-comment check) were re-run by hand against `sql.py` 1.1.0 and came back clean.

## 7. Patterns confirmed

- **A decision about data is blocked on reading the table.** Both halves of this slice changed shape at the last read: the priority payload turned out to be seven rows with distinct colours (not fourteen with duplicates), and `initialsOf` turned out to have a silent failure class nobody had recorded. Neither was visible from the docs, and both would have produced a defensible-but-wrong slice.
- **Two oracles beat one.** The seven-row count came from a `SELECT` and independently from `dm_exec_query_stats.max_rows` on the same statement. The `initialsOf` behaviour was verified against a local harness and then against the live payload.
- **Copy bytes, edit surgically, diff as evidence.** All eight files were `cp`-ed from the sources and edited with exact-match replacements, so every diff is header, changelog and specified lines only — nothing untouched could drift, and the diff itself is the proof.
- **Assert the unfixed thing.** Item 35 (`Andrew Hornby R2` → `AR`) is pinned by a test that asserts the *wrong* value on purpose, with a comment saying so. A gap with a failing-if-fixed test cannot be forgotten; a gap in a doc can.
- **The box clock rolled past midnight mid-session.** Git dates `5443ac1` and `85d4e95` on 09-14 while every file header and this log read 09-13. Noted, nothing renamed — the session is what it is.

## 8. Open items

**Closed this session:** **21** (`initialsOf` on parentheses — OD-35, shipped) · **29** (`Priority.Colour` to the badge, backend half — shipped; the `UPDATE` withdrawn as unnecessary) · **30** (alternating latency — not reproducible, protocol in §4.1).

| # | Item |
|---|---|
| 4 | 6M summary shape |
| 17 | Docker first clean start |
| 24 | hidden-tab poll |
| 25 | prettier not in smoke |
| 26 | `scripts/parity_range.py` + the `svc_workmate` user in the KT copy. **Now carries an expected diff**: `workers[].initials` against the live Ignition oracle (OD-35) |
| 27 | `CapacityBar` 1.0.1 `nWorkers` |
| 28 | `/_diag/client`, `?debug=1` |
| 31 | Forensics pack set aside |
| 32 | KT uplift migration — scripted from the KT catalog, never typed; the nine questions in KT delta §8 |
| 33 | tips ⓘ, first non-port component |
| 34 | carry-backs to KT — **now includes the `initialsOf` fix** (OD-35) |
| **35** | **New.** Trailing role tokens still skew initials after OD-35: `Andrew Hornby R2 (Max Edkins)` → `AR`, `Max Webber R2 (…` → `MR`. Needs a decision on a site-specific token list (`R2`, `NS`, `SUP`, `CALLOUT`, `PROJECT`). Asserted unfixed in `test_planner_rules.py` 1.1.0 — if that test fails, this was fixed; update it deliberately, do not patch it to match |
| **36** | **New.** `Priority.Colour` is unvalidated `varchar(255)` free text. The renderer must pass `^#[0-9A-Fa-f]{6}$` before the value goes near a style attribute. `N/A` is `#FFFFFF` and the base `.pri` rule sets `color:#2b2b2b`, so light backgrounds read and dark ones need a luminance check. KT's four identical `#FF8000` rows mean payload colour must **not** win outright or KT loses its A–D distinction |
| **37** | **New.** The WO `/range` select goes parallel for 3221 rows and spends most of its wait in exchange; 47k logical reads per execution from five per-row correlated subqueries. `OPTION (MAXDOP 1)` would likely beat it but is MSSQL-only against the portability rule — needs a portable shape (correlated subqueries as joins) and its own measurement |
| **38** | **New.** Backend suite dependency drift: Starlette wants `httpx2` for `TestClient`; `anyio.abc.BlockingPortal` is a deprecated alias. Two warnings, nothing red |

**Numbering hazard:** the OD series and the open-item series both now sit in the mid-30s and `OD-35`/`item 35` are different things created in the same session. Always carry the `OD-` prefix.

## 9. Doc-correction queue

**Apply before the next audit** (one docs commit):

- **Landmines → 1.6.0.** §E `dbo.Priority`: the payload is **seven** rows on RST, the active seven have **distinct** colours, both `#FF0000` triples are inactive (§5.1). §E `initials`: add the multi-word class (`Adam Donald (Max Edkins)` → `AE`) — the entry records only `J(` and understates it; then note the bullet is **closed** by OD-35 with item 35 remaining. §F: free RAM is not a recovered buffer pool, a squeezed SQL Server stays degraded until it restarts (§4.1). §A: the Downloads line records a **third** loss and the `Test-Path`-first rule (§6.1).
- **Ways of Working → 1.3.3.** §2: the mechanical header-vs-`__version__` check before any card is emitted (§6.2). §6: a test whose pass depends on which database it is pointed at is a data assertion in disguise (§6.3). §5: a knowingly false header beats no scope line — fix the pointer and flag the extra file (§6.4).
- **Index → 1.6.0.** §1 state: HEAD `85d4e95`, S1h shipped, 156/155, items 21/29/30 closed, 35–38 opened. §3.1 adds the S1h spec. §5 versions table for all eight files. §6: next is the uplift audit.
- **Port Spec → 1.0.4.** §5 `initialsOf` line moves from "byte-1:1, a fix needs an OD" to "OD-35, departs, item 35 remains". §3 `priorities[]` row gains `colour`. §6 S1h row → done. §9: OD-35/36/37 recorded, items 21/29/30 closed.
- **Architecture → 1.0.5.** §3.3 DB tooling: the `dm_exec_query_stats` / `dm_exec_session_wait_stats` pattern for attributing latency without catching a request mid-flight. §4: OD-36 as the precedent for "the API reports what the column holds".

## 10. Next

1. **Nothing is queued that needs a slice.** The read-only planner plus S1h is complete and green.
2. **The frontend half of item 29** — paint the badge from `colour`, guarded per item 36, with the `openapi-ts` regen. First frontend slice since S1g and needs its own audit and 🤙.
3. **The uplift audit (item 32)** — one additive migration scripted from `dbWorkmate_KT`'s catalog, never typed; the nine questions in KT delta §8.
4. **S2** (move / undo / estimate) — the first slice that writes to RST. `loadWO`, `movePreview`, `GET /preview` (OD-13), the `weekno` port with `test_weekno.py` against three references, `@dnd-kit`, confirm dialog, undo toast, the JWT seam (OD-12). `dry_run=True` first.
5. Outstanding query, blocks nothing: the `GetWeekNoAndYear` body from `dbWorkmate_KT.sys.sql_modules` — `sqlcmd -S localhost -E -C -y 0 -w 8000 -Q "…"`, no `-W`, no `-h`.

## 11. Changelog

- 1.2.0 (2026-09-13) The third session of the day: doc set applied, backend audit (items 30, 29, 21), S1h built and shipped. Supersedes §8/§9 of 1.1.0.
