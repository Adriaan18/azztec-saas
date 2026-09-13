# Azztec SaaS — Raw session log 2026-09-14 (doc set + S1i priority paint + the KT RFID copy)

**File:** Azztec_SaaS_Raw_Log_2026-09-14_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-14 · **Author:** Adriaan
**Append-only.** Supersedes §8 (open list) and §10 (next) of `Azztec_SaaS_Raw_Log_2026-09-13_v1_2_0.md`; that log's §1–§7 still stand, and its §9 correction queue is now **applied** (§2 below).
**Session:** the first of 2026-09-14. The doc set from log 1.2.0 §9, the **item-29 frontend audit**, then **S1i built and shipped**. One database was written — a new RFID development copy, restored deliberately (§7). `dbWorkmate` and `dbWorkmate_KT` were not touched.
**Ended at:** HEAD `e0a3501`, tree clean, tag `s1i-priority-paint-1.2.0`. Backend **156 passed** (exit 0, 4.85 s), frontend **170 passed in 11 files** (exit 0).

---

## 1. Decisions signed this session

| ID | Decision | How |
|---|---|---|
| **OD-38** | The published `Priority` schema changed while `main.py.__version__` did not, so the export had no filename to land on. `main.py` → **0.4.0**, export `docs/api/openapi_0_4_0.json`, the 0.3.0 file leaves the tree, `openapi-ts.config.ts` → 1.0.2. `info.version` *is* `main.__version__`, and minor-for-a-new-field is the standing bump rule. | **🤙 signed** |
| **OD-39** | Payload colour paints per row only if it passes `^#[0-9A-Fa-f]{6}$`, and per payload only when there are **≥ 2 distinct usable colours** (case-folded). RST's seven paint; KT's four identical `#FF8000` rows fall to `.pri.A–D` and keep their letters. Accepted consequence: a payload with exactly one usable colour paints nothing. | **🤙 signed** |
| **OD-40** | Text colour on a painted badge is whichever of `#2b2b2b` (the base `.pri` colour) and `#ffffff` has the higher WCAG contrast; ties go dark. A contrast floor, **not the oracle's aesthetic** — applied to `.pri.A` (`#EF6C57`) it picks dark where the oracle hand-picked white, and it never runs there. | **🤙 signed** |
| **OD-41** | One map: `priBadgeMap → {rank, bg, fg}` replaces `priRankMap` at both badge sites; the badge takes `badge?: PriBadge` and applies inline `backgroundColor` / `color` longhands, which beat the stylesheet's `background` shorthand with no CSS change. `priRank`/`priRankMap`/`priClass` stay exported and `priBadgeMap` calls `priRankMap`, so the rank contract has one implementation. | **🤙 signed** |

All four were signed together after the audit and before any code. `router.py` 1.1.1 (§6.1) was flagged mid-slice and signed as a format-only bump.

## 2. Shipped and committed

| Commit | Content |
|---|---|
| **`eb647da`** | the compiled set from log 1.2.0 §9 — Index **1.6.0**, Landmines **1.6.0**, Ways of Working **1.3.3**, Architecture **1.0.5**, Port Spec **1.0.4**. 5 files, 957 insertions |
| **`e0a3501`** | **S1i** — `main.py` 0.4.0, `router.py` 1.1.1, `test_smoke.py` 1.1.1, `openapi-ts.config.ts` 1.0.2, `rules.ts` 1.2.0, `rules.test.ts` 1.2.0, `range.fixture.ts` 1.2.0, `WOCard.tsx` 1.1.0, `WOCard.test.tsx` 1.1.0, `DayCell.tsx` 1.1.0, `PlannerGrid.tsx` 1.1.0, `PlannerGrid.test.tsx` 1.1.0, `DayDialog.tsx` 1.1.0, `DayDialog.test.tsx` 1.1.0, the S1i spec, the regenerated `types.gen.ts`, and the contract as a **rename** `openapi_0_3_0.json → openapi_0_4_0.json` (99% similar). 17 files, 738 insertions, 118 deletions. Tag `s1i-priority-paint-1.2.0` |

**Still to remove by hand from project knowledge:** Index 1.5.0, Landmines 1.5.0, WoW 1.3.2, Architecture 1.0.4, Port Spec 1.0.3 — and the fourteen superseded S1i cards (`app_main` 1.0.3, `app_planner_router` 1.1.0, `test_smoke` 1.1.0, `openapi_ts_config` 1.0.1, `rules` 1.1.0, `rules_test` 1.1.0, `range_fixture` 1.1.0, `WOCard` 1.0.1, `WOCard_test` 1.0.1, `DayCell` 1.0.1, `PlannerGrid` 1.0.1, `PlannerGrid_test` 1.0.1, `DayDialog` 1.0.0, `DayDialog_test` 1.0.1). `planner.css` 1.1.1 stays — S1i did not touch it. Raw logs stay.

## 3. Suite state

Backend `uv run pytest`: **156 passed, 2 warnings in 4.85 s**, exit 0 — unchanged, and that is the evidence `main.py`, `router.py` and `test_smoke.py` were version lines only. Run three times this session (before the slice, after the `router.py` card, and with the new `dist/` present) and 156 every time.

Frontend `pnpm test`: **170 passed in 11 files**, exit 0, 31.47 s. **Predicted before the run as 170** from the cards' own `it()` counts — `rules.test.ts` 55 → 65, `WOCard.test.tsx` 10 → 13, `PlannerGrid.test.tsx` 14 → 15, `DayDialog.test.tsx` 7 → 8 — and every per-file count matched. `pnpm lint` exit 0 first pass; `pnpm build` 560 ms, 503 modules.

## 4. The item-29 frontend audit

Six findings, all from files read on the box or in project knowledge, none from memory:

1. **Two badge sites, not one.** `WOCard` (`.chip .pri`) and `DayDialog` (`.dd2 .job .pri` at line 57). Both took rank through `priClass`, so any colour mechanism had to reach both, and `PlannerGrid` builds the map once and passes it down through `DayCell`. That is what made the slice four components rather than one.
2. **The old spec's precedent claim was false.** Port Spec 1.0.3 §9 said the chip would paint "as it already does for category `colours`" — **nothing in the port reads the payload's `colours{}`**. Category colour comes from the `.cat-<cat>` CSS classes; `colours` is on the wire and unused (`usePlannerRange.test.tsx` sends `colours: {}` and nothing notices). The phrase was dropped from 1.0.4 rather than carried. S1i is the first payload-driven paint in the port.
3. **The regeneration breaks `range.fixture.ts` at compile time.** `schemas.Priority.colour` has no default → required in OpenAPI → `colour: string` required in TS. The fixture is annotated `RANGE: RangeData` with five `{id, short, title}` rows, and it is the **only** frontend file that constructs a `Priority` literal (`rules.test.ts` reads `RANGE.priorities`; `usePlannerRange.test.tsx`'s body is untyped). So the regen leaves `pnpm test` green and `pnpm build` red — a type-only failure, which is why the fixture had to be in this slice and not the next.
4. **Two test assertions pin the badge's exact class string** (`'pri P1'`, `'pri P1 r1'`). An inline style leaves them green; a new class would not. Decided deliberately (OD-41) rather than discovered.
5. **The oracle already does the luminance trick by hand** — `.pri.A` and `.pri.D` carry `color:#fff`, `.B` and `.C` keep `#2b2b2b`. That is the precedent OD-40 formalises; it just computes what the oracle eyeballed.
6. **The OpenAPI export had no filename convention to land on** — `info.version` is `main.__version__`, S1h never touched `main.py`, and the config's own header says to bump the input path *when main.py bumps*. That became OD-38.

### 4.1 What the audit read, and what it refused to guess

The committed contract (three-field `Priority`, `info.version 0.3.0`, written 11/09), `app.openapi()` on the box (four fields, `colour` in `required`), `types.gen.ts` 112 (three fields), `package.json` (`"gen:api": "openapi-ts"`), and one `openapi_*.json` on disk. The Index's pick-up step was written to say the export filename question is *the audit's first question*, not a decision — and it turned into OD-38 rather than an invented filename.

## 5. Facts verified this session

### 5.1 The wire, after the slice

```
/health      version 0.4.0   planner 1.1.1   frontend built   db ok   diagWired True
/range       apiVersion 1.1.1   libVersion 1.1.0   ms 226

id  short  title           colour
 1  P2     Priority 2      #FF9F40
 5  P1     Priority 1      #FF0000
 2  P3     Priority 3      #74EE66
12  P5     Priority 5      #C499C1
13  P6     Priority 6      #C0C0C0
 4  P4     Priority 4      #0080FF
 6  N/A    Not Applicable  #FFFFFF

priority rows: 7      distinct colours: 7 of 7      non-hex colours: 0
```

`non-hex colours: 0` is the live check on OD-36's premise: the backend validates nothing, so this is where junk in `Colour` would show. None today — which is why the renderer guard exists rather than trust.

**`libVersion` is `rules.py`, not `rules.ts`.** The smoke prediction called for `libVersion 1.2.0`; it is **1.1.0** and correctly so — the frontend `rules.ts` VERSION never reaches the wire. Mistake in the prediction, not the payload (§6.3), and it makes one committed doc line stale (§9).

### 5.2 The `textOn` table, verified by the run and then by eye

The S1i spec §5.1 predicted all seven by hand; `rules.test.ts` 1.2.0 asserts them and passed first time:

| colour | contrast vs `#2b2b2b` | vs `#ffffff` | `textOn` |
|---|---|---|---|
| `#FFFFFF` | 14.16 | 1.00 | `#2b2b2b` |
| `#74EE66` | 9.55 | 1.48 | `#2b2b2b` |
| `#C0C0C0` | 7.78 | 1.82 | `#2b2b2b` |
| `#FF9F40` | 6.93 | 2.04 | `#2b2b2b` |
| `#C499C1` | 5.85 | 2.42 | `#2b2b2b` |
| `#0080FF` | 3.73 | **3.80** | `#ffffff` |
| `#FF0000` | 3.54 | **4.00** | `#ffffff` |

`#0080FF` is the narrow one at a 2 % margin and was pinned on purpose — any threshold-style rule would flip it. Also asserted: `#9AA3AD` (the base badge background) keeps dark text, `#000000` takes white, `.pri.A` `#EF6C57` picks **dark** where the oracle chose white (the recorded disagreement), `.pri.D` `#6f7c87` agrees with the oracle.

### 5.3 Both badge sites, both white-text cases, on real RST data

Week 14–20 Sep 2026 (`0 WO | 273 PM | 0 done`) showed P2 orange, P3 green, P4 **blue with white text**, P5 mauve — but no P1 or N/A, because that week is pure PM work. The week of 27 Jul – 2 Aug 2026 carries all seven: **P1 `#FF0000` red with white text** (`3CL-OPM-005-0113`), **N/A `#FFFFFF` white with dark text** (`3RM-RMM-013/014-1045`, `3CL-COM-041-1049`), **P6 silver** (`7PJ-260729-001..003`), P5 mauve (`3CL-260729-007/012`). The **day dialog** on Sat 1 Aug painted the same — P1 red on white text, P3 green, P4 blue — so the second site does not silently stay grey. Footer read `lib 1.1.0 · api 1.1.1 · range 166 ms`.

### 5.4 Timings with a third database attached

`/range` on the June 42-day window (3221 rows): **375 ms** inside the API, **414 ms** HTTP. The standing week: **226 ms**, and **166 ms** from the browser. All inside the healthy 70–700 ms band **with `dbWorkmate_KT_RFID` attached and an Ignition gateway connected to it**. Item 30 stays closed.

## 6. Mistakes caught this session

### 6.1 A card went into the repo not format-clean, and `ruff check` can never catch it

`ruff format .` at the top of the smoke reported **2 files reformatted** and `git diff --stat` came back with **fourteen** modified files against thirteen cards. The fourteenth was `backend/app/planner/router.py` — shipped in S1h at `5443ac1` with a `@router.get` decorator **111 characters** long against `pyproject`'s `line-length = 110`.

The sharp part: `[tool.ruff.lint] ignore = ["E501"]`, so **a long line passes `ruff check` indefinitely and only `ruff format` fixes it**. S1h's smoke block ran `ruff check` on its seven files and no format pass, so nothing could have caught it that session. WoW §6 puts `ruff format .` first for exactly this reason.

Resolved as **`router.py` 1.1.1, format-only** — flagged before it was built, not folded into the commit (the S1h `test_planner_repo.py` 1.0.2 precedent: the file on disk must not silently differ from its project-knowledge card). The bump is honest rather than noisy: a patch on `apiVersion` reads as "fix, no contract change", which is what a re-wrap is, and OD-37's concern was a *field* appearing without a minor bump. `test_smoke`'s version assertion reads `planner_router.__version__` instead of a literal, so 1.1.1 flowed through `/health` with no test edit — that rule earning its keep twice in one day.

### 6.2 A commit gate fired on a wrong prediction, which is the gate working

The commit block was written to expect **18 staged paths and 1 deletion** and it refused: git recorded the export as **`R099`** — a 99 % similar rename `openapi_0_3_0.json → openapi_0_4_0.json` — so it is one path, not a delete plus an add. Seventeen paths, zero deletions. The prediction was wrong and the gate caught it before the commit, which is the whole point of writing the expected count into the step. It also records the contract's lineage better than a D+A pair would.

### 6.3 `libVersion` is `rules.py`; I predicted `rules.ts`

The §7 smoke expectation said `libVersion 1.2.0`. `libVersion` is the **backend** `rules.py` `__version__`, untouched by S1i and correctly still 1.1.0; 1.2.0 is the frontend `rules.ts` `VERSION`, which never reaches the wire. Two modules with the same stem, one wire field. Caught by reading the payload against the prediction, which is why predictions get written down.

### 6.4 A winget-pinned SQL Server installer had expired

`winget install -e --id Microsoft.SQLServer.2022.Developer` verified its hash, ran, and died: `FatalActivityException: This version of the installer is no longer supported`, exit 3762504530. The package ships the SSEI **bootstrapper**, not media, and Microsoft retires old stubs. The hash passing is what proves it is not a corrupt download. Same family as S0 losing `web/` to a CLI flag that had stopped existing. It also turned out not to be needed (§7).

## 7. `dbWorkmate_KT_RFID` — a writable KT copy for Ignition RFID work

**Restored this session**, deliberately and outside the SaaS build: `dbWorkmate_KT_RFID` from the same `C:\SQLBackups\dbWorkmate_backup_2026_09_12_233033_4351464.bak` (78,731,776 B) as the parity oracle, `WITH MOVE` to the instance defaults, **read-write**, `COMPATIBILITY_LEVEL 100` to match KT, then `RECOVERY SIMPLE` so the log does not grow unbounded under dev. 9,457 pages in 0.087 s, exit 0. `svc_workmate` created as a `SQL_USER` with `db_datareader` + `db_datawriter` — **no `db_ddladmin`**, because RFID schema changes must come from scripts that can cross to KT, not ad-hoc DDL from a gateway. The Ignition gateway connected successfully.

```
name                 state_desc  is_read_only  compatibility_level  recovery_model_desc
dbWorkmate           ONLINE      0             170                  SIMPLE
dbWorkmate_KT        ONLINE      1             100                  FULL
dbWorkmate_KT_RFID   ONLINE      0             100                  SIMPLE
```

**`dbWorkmate_KT` is untouched and still read-only** — it is the parity oracle and item 26 depends on it being unmutated. Same data in both, so RFID dev and the oracle do not diverge.

**The carry-back rule, decided here:** the restore printed the 957 → 998 upgrade ladder in full, so this copy can never go back onto KTSQL02 (SQL Server 2022). **Carry-backs to KT are DDL scripts, never files** — the same rule item 32 already applies to the uplift migration, in the other direction. That removed the need for a 2022 instance entirely (§6.4), and it swaps in one risk: 2025-only T-SQL that works here and fails at KT. Guards: compat 100 on the dev copy, SSMS scripting target set to SQL Server 2022, no DDL generated from 2025's catalog views without checking the columns exist on 16.x, and — if certainty is wanted over discipline — a throwaway `mssql/server:2022-latest` container as a **validation gate**, not a dev environment. Open item 40.

Two naming notes for the next restore: the backup's logical log file is physically `dbTLL_log.ldf`, not `dbWorkmate_log.ldf`; and the `.bak` filename says 12 Sep 23:30 where Architecture §3.3 records the backup at 13 Sep 00:32.

## 8. Patterns confirmed

- **Predict the count, then read it.** 170 frontend tests were predicted from the cards' own `it()` counts before the run and every per-file number matched; 156 backend was predicted to *not* move and did not, which is what proved two cards were version lines only. A count read without a prediction is a number; a count read against one is evidence.
- **A gate that fires on your own wrong prediction is the gate working** (§6.2). Twice today: the commit path count, and the `libVersion` smoke line.
- **Copy bytes, edit surgically, diff as evidence.** All fourteen cards were `cp`-ed and edited with exact-match replacements. The one wide diff — `DayDialog.tsx`, where the map callback became a block body and re-indented 35 lines — was declared in the card's own changelog before it was delivered, so the width was expected rather than alarming.
- **The mechanical header-vs-`__version__` check paid for itself** — run across all fourteen cards before delivery, all fourteen agreed, and the one file whose on-disk content had drifted from its card (§6.1) was found by the *format* pass, not by reading.
- **A smoke on the browser is not optional.** Both OD-40 white-text cases and the second badge site were only provable by eye, and the first week screenshotted did not contain P1, N/A or P6 — the API had to be queried across a year to find a week that did.

## 9. Doc-correction queue

**Apply before the next audit** (one docs commit):

- **Index → 1.7.0.** §1 state: HEAD `e0a3501`, S1i shipped, 156/170, items 29 and 36 closed, 39 and 40 opened; next is the uplift audit. §3.1 adds the S1i spec; §3.4/3.4b/3.5 the fourteen new versions (and `router.py` **1.1.1**); §3.4b notes the contract is now `openapi_0_4_0.json`. §4 rule 2 gains the format-clean-before-commit point. §5 the `/range` row with the new timings and the third database. §6 pick-up: 170, the uplift audit as step 5, the RFID copy in the environment table. §6.2 the removal list above.
- **Landmines → 1.7.0.** §A: **`ruff check` cannot catch what `ruff format` fixes** — E501 is in the ignore list (§6.1); and the winget SSEI stub expiry (§6.4). §B: the logical-vs-physical log filename (`dbTLL_log.ldf`), and the 957 → 998 ladder as the visible proof of the one-way door. §C: an inline longhand beats a stylesheet shorthand, which is what lets a payload colour win with no CSS rule. §E: the `dbo.Priority` line's renderer guard is no longer pending — the badge paints behind OD-39's gate with OD-40's contrast rule, KT keeps its letter classes.
- **Ways of Working → 1.3.4.** §2: the export filename convention (OD-38) — the exported OpenAPI document is named from `main.__version__`, and a schema change with no app bump is a bump; the format-clean rule stated as *`ruff format .` repo-wide, not `ruff check` per file*. §6: predict the count before the run.
- **Port Spec → 1.0.5.** §3 `priorities[]`: the frontend half is done. §6 gains the S1i row. §7: the `features/planner/` bullet gains `priBadgeMap` and the paint. §9: OD-38…OD-41 recorded, items 29 and 36 closed, items 39 and 40 raised.
- **Architecture → 1.0.6.** §3.2 API-client row and §5: input is `openapi_0_4_0.json`, config 1.0.2. §4 D-9 gains OD-38 as the precedent for versioning the exported document. **§6 step 3 is stale** — it says `apiVersion` and `libVersion` both read 1.1.0; it is `apiVersion` **1.1.1**, `libVersion` **1.1.0** (§5.1, §6.3). §3.3 gains the `dbWorkmate_KT_RFID` row.

## 10. Open items (16)

**Closed this session:** **36** (the renderer guard — built as OD-39's hex gate and OD-40's contrast rule). **Item 29 is now closed in full:** log 1.2.0 §8 listed it as closed on the backend half while its §10 still carried the frontend half as next — that half shipped as S1i, so nothing remains. Arithmetic: 15 open at the close of 1.2.0, minus 36, plus 39 and 40 = **16**.

| # | Item |
|---|---|
| 4 | 6M summary shape |
| 17 | Docker first clean start under the `.wslconfig` cap |
| 24 | hidden-tab poll |
| 25 | prettier not in smoke |
| 26 | `scripts/parity_range.py` + the `svc_workmate` user in the KT copy. **Carries an expected diff:** `workers[].initials` (OD-35) |
| 27 | `CapacityBar` 1.0.1 taking `nWorkers` |
| 28 | `/_diag/client`, `?debug=1` |
| 31 | Forensics pack, set aside |
| 32 | KT uplift migration — scripted from the KT catalog, never typed; delta §8 |
| 33 | tips ⓘ, first non-port component |
| 34 | carry-backs to KT — includes the `initialsOf` fix (OD-35) |
| 35 | role tokens still skew initials (`R2`, `NS`, `SUP`, `CALLOUT`, `PROJECT`) — asserted unfixed in `test_planner_rules.py` 1.1.0 |
| 37 | the WO `/range` select goes parallel, 47k logical reads, five per-row correlated subqueries; `MAXDOP 1` is MSSQL-only so it needs a portable rewrite |
| 38 | Starlette wants `httpx2` for `TestClient`; `anyio.abc.BlockingPortal` deprecated |
| **39** | **New.** `/health`'s own `version` field is the only version not asserted against a module constant — `test_smoke.test_health_versions_match_the_modules` compares `db`, `diag`, `config` and `planner` and skips `main`. One line; deliberately not closed inside a header-only edit (§6.1) |
| **40** | **New.** Ignition RFID work on `dbWorkmate_KT_RFID` (§7): carry-backs to KT are **DDL scripts, never files**; guards are compat 100, an SSMS scripting target of SQL Server 2022, and no DDL generated from 2025 catalog views without checking 16.x columns; an optional throwaway `mssql/server:2022-latest` container as a validation gate before anything reaches KTSQL02. No SQL Server install required — the winget 2022 stub is expired (§6.4) and a second instance turned out unnecessary |

**Numbering hazard, still live:** the OD series is at 41 and the open-item series at 40. `OD-40` and item 40 are different things created in the same session. Always carry the `OD-` prefix.

## 11. Next

1. **The doc set (§9).** Then audit from the docs, not this log.
2. **The uplift audit (item 32)** — one additive migration scripted from `dbWorkmate_KT`'s catalog, never typed; the nine questions in KT delta §8. The sharp ones: `WO_N_Plan` on RST (flips `pinTable` true, ~2,364 PMs pin-movable — OD-1's intended end state), migration numbering against S3's 0002, and what fills `Diag_Log`'s NOT NULL columns. **Nothing frontend is outstanding** — the read-only planner plus S1h plus S1i is complete and green.
3. **S2** (move / undo / estimate) — the first slice that writes to RST. `loadWO`, `movePreview`, `GET /preview` (OD-13), the `weekno` port with `test_weekno.py` against three references, `@dnd-kit`, confirm dialog, undo toast, the JWT seam (OD-12). `dry_run=True` first. S2 inherits the `PriBadge` map for the drag preview.
4. Outstanding query, blocks nothing: the `GetWeekNoAndYear` body from `dbWorkmate_KT.sys.sql_modules` — `sqlcmd -S localhost -E -C -y 0 -w 8000 -Q "…"`, **no `-W`, no `-h`**.
5. Not a slice, whenever wanted: item 40's RFID work, item 33's tips ⓘ, item 39's one-line test.

## 12. Changelog

- 1.0.0 (2026-09-14) The first session of 2026-09-14: the log 1.2.0 §9 doc set applied, the item-29 frontend audit, S1i built and shipped, and a writable KT copy restored for Ignition RFID work. Supersedes §8/§10 of 2026-09-13 1.2.0.
