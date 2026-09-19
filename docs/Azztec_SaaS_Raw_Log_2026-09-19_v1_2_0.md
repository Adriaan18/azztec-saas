# Azztec SaaS — Raw Log 2026-09-19

**File:** Azztec_SaaS_Raw_Log_2026-09-19_v1_2_0.md · **Version:** 1.2.0 · **Date:** 2026-09-19 · **Author:** Adriaan
**Status:** Session record, append-only. The session opened 2026-09-16 and has now run S1k, D1a and **W1a** on the same day-log. **1.2.0 adds W1a** — the WOMaint read API: audited from fourteen fresh Designer exports, specced, delegated, built, smoked, committed and tagged (§2, §4c, §6). The doc set (§8) is still the one thing not cut.
**Target path:** `docs/Azztec_SaaS_Raw_Log_2026-09-19_v1_2_0.md` (+ project knowledge; replaces 1.1.0)
**Parent:** log 2026-09-15 1.0.0 (its doc-correction queue is **still unapplied** — §8 carries it forward with today's additions).

---

## 1. Decisions this session

| ID | What | State |
|---|---|---|
| **OD-50** | The shell is a port on the oracle's own CSS: `features/shell/`, `data-name` = the oracle's `meta.name`, styles scoped `.wm-shell`, glyphs inline, mounted in `__root.tsx`. No shadcn, no lucide, no Tailwind classes, no `pnpm add` | Taken on "go" (09-16) as **delegated**, built, then **accepted on review** at the smoke (09-19, "this looks perfect"). No separate 🤙 |
| **OD-51** | Only Plannex navigates. Every other control draws as the oracle draws it and does nothing: `cursor: default`, `aria-disabled`, `title="arrives with … (OD-51)"`. Live as well: the clock, `fsBtn` (Fullscreen API), rail Print (`window.print()`) | as above |
| **OD-52** | Gated items: VisualX, the search pill and the Users button are not rendered; logout and the tips toggle are drawn inert | as above |
| **OD-53** | Brand is the constant `AZZTEC`; **WORKMATE mode cut** — its logo PNG never arrived | as above |
| **OD-54** | The day dialog is contained: `.wm-planner{position:relative}`, `.ovl{position:absolute}` | as above, and **verified by measurement** (§5) |
| **OD-47** | How the SaaS fills `Diag_Log` | closed by OD-55 |
| **OD-55…OD-61** | The D1a forensic-persist decisions — the `Diag_Log` fill, Azzmax (21) as the dev actor, one writer thread with a bounded queue, redaction, the volume rule, the in-app purge at 60 days, dev-only trail routes | **🤙 signed 2026-09-19** on `Azztec_SaaS_D1a_Persist_Chunk_Spec_v1_0_0.md` §6 |
| **OD-62** | **W1 ships in two slices**: W1a the read API, W1b the read-only page | Answered "ok" one by one on 2026-09-19, **delegated, not signed** (the OD-50…54 precedent); a 🤙 on `W1a…_v1_0_1.md` converts all ten |
| **OD-63** | The list takes **one `search` term** (sid or title, the NQ's own `OR`) plus `woType` / `includeClosed` / `includeArchive` with the NQ's 0/1/2 semantics; `woTitle` / `shortAssetId` / `shortLocationId` not ported — the view never sets them | as above ("ok, add them later") |
| **OD-64** | **Paging**: `limit` 1–1000 (200), `offset`, `more` from a `limit + 1` fetch, **no total**; order `Entry_date DESC, WO_ID DESC` | as above, with the standing priority stated: **speed, no lagging like the .NET app**. The smoke's three timings are the check (§4c) |
| **OD-65** | The record **LEFT JOINs `WO_N_Details`** and ships `detailsMissing`; one `[G]` per such read | as above |
| **OD-66** | Labels resolved server-side regardless of the reference row's `Active`; **`refs` deferred to W3** | as above |
| **OD-67** | **`progressAll` from `dbo.Progress`** (active, by id); W1b draws one card per row — the oracle's six icons for 1–6, a plain card beyond | as above. Measured at the smoke: **eight** active rows, not nine (§5) |
| **OD-68** | An id found only in `WO_C_header` is **404 `ARCHIVED`**; the archive record read is a later slice | as above |
| **OD-69** | The six routes' `[F]` lines **print, don't persist**; the middleware still persists ≥ 400 / ≥ 2000 ms (OD-59) | as above, **proven in the trail** (§4c) |
| **OD-70** | camelCase contract keys, 88 record keys + the OD-14 envelope; `main` 0.4.0 → **0.5.0**, `openapi_0_5_0.json`, `pnpm gen:api` | as above |
| **OD-71** | The record carries **`filtersFor`** — the `onStartup` handoff rule, computed server-side | as above |

## 2. Shipped and committed

| Commit | What |
|---|---|
| **`d17bac6`**, tag **`s1k-shell-1.0.0`** | S1k shell — 17 files, 4,501 insertions, 17 deletions |
| **`c7de038`**, tag **`d1a-persist-1.0.0`** | D1a — 14 files: `diag.py` 1.2.0, `deps.py` 1.1.0, `config.py` 1.2.0, `main.py` card 1.0.6, `app/diag/{sql,repo,router}.py`, the two test files, `.env.example` 1.1.0, `Show-DiagTrail.ps1` 1.0.1, the D1a spec |
| **`95f0359`** | docs — the WOMaint and D1 audits, `workmate_workorder_code_v1_8_1.py`, `WO_Named_Queries_2026-09-16.md` |
| **`d13819c`**, **`2c4ca9f`** | the 09-19 log 1.1.0, then the five-doc set + handover brief 5.0.0 |
| **`797948a`**, tag **`w1a-api-1.0.0`** | **W1a — 26 paths**: `app/workorders/{sql,rules,repo,schemas,router}.py` 1.0.0 + `__init__.py`; `tests/test_workorders_{rules,repo,api}.py` 1.0.0; `test_openapi_contract.py` **1.1.1**; `main.py` card **1.0.8** (app **0.5.0**); `openapi-ts.config.ts` 1.0.3; `docs/api/openapi_0_5_0.json` in and `openapi_0_4_0.json` out; the four regenerated client files; the spec `W1a…_v1_0_1.md`; six reference cards in `docs/reference/` (the WOMaint view 588,182 B, `WOStatus`, `WOProgress`, `WONumBadge`, `CompleteWithinSeg`, the NQ addendum) |

## 3. Suite state

| | Before W1a | After W1a |
|---|---|---|
| Backend | 218 passed, 2 skipped | **319 passed, 2 skipped** — rules 22, repo 46 (31 no-DB gate + 15 on RST), api 24, contract 8 → 17. **Predicted 319, read 319**, first run, zero skips added |
| Frontend | 205 passed in 15 files | **205 passed in 15 files** — unchanged; re-run because the generated client and `dist/` moved |
| Lint | clean | clean after two same-session re-cuts (§6) |
| Build | 509 modules, `index-*.js` 424,253 B | **unchanged** — nothing in `web/src` imports the new client yet (W1b) |
| Contract | `openapi_0_4_0.json` | **`openapi_0_5_0.json`**, 63,743 B, `info.version 0.5.0`, six `/api/v1/workorders` paths; `gen:api` regenerated 5 files |

## 4. Evidence read this session

*(S1k's and D1a's evidence stands as recorded in 1.1.0 — the two navigation views, the icon library, the 13:07 project export, the KT screenshots, `workmate.nightshift` 1.3.2.)*

**For W1a, fourteen Designer resource exports (2026-09-19, 13:01–13:05 and later), all read in full before the spec:**

- **`WOMaint` v16.28.3** (588,182 B, last modified 2026-09-03 by Adriaan): 110 flex containers, 74 labels, 27 text fields, 18 dropdowns, 10 tables, 11 embedded views, 19 buttons; **94 scripts, 92,869 characters** — 12 message handlers on the root, `onStartup` (9,154 c), 45 event scripts, 36 binding transforms. 18 named queries bound, 4 more called inside transforms, 4 raw `runQuery`/`runPrepQuery` statements typed into scripts.
- **The four symbols**: `WOStatus` (nine cards R H P K A V C D F), `WOProgress` (six cards, ids 1–6), `WONumBadge` v1.3.0 (one label, colour from `left(value,1)`), `CompleteWithinSeg` v1.8.0 (day / week / month / 3-month / next shut / range).
- **56 named queries** in six folders. The 48 shared with the 09-16 bundle are **byte-identical**; eight are new (`Event/Insert`, `Event/Search`, `Priority/Dropdown`, `Template/Get`, `Template/List`, `Workorder Hub/{AreaList, LiveWOList, WOByUser}`) and are now the addendum card.
- **`workmate/workorder/code.py`** — byte-identical to the PK card 1.8.1 (`cmp` clean).
- **The fifteen reference reads** (`Progress/Get`, `Supplier/GetShortId`, the thirteen `…/Dropdown`) — the table and column names the record's label joins use. Their active-only filters are exactly why a read resolves labels without them (OD-66).
- **Stylesheet v2.69** (141,544 B): every `--wo-rgb-*` / `--wo-color-*` token, and eleven of the twelve `wm-*` classes the view uses. **`wm-seg-9px` has no rule** — the same class of finding as `psc-toolbar-btn` in S1k. For W1b.
- **`TipBadge` / `TipPopup`** — byte-identical to the 09-10 cards; not re-cut.

## 4b. D1a — the smoke, measured

*(unchanged from 1.1.0)*

## 4c. W1a — the smoke, measured

Block by block, all exit 0. Server down and proven (zero listeners) before the drop; started fresh at step 6; one PID (30284).

- **Suite** `319 passed, 2 skipped` in 24.07 s, first run, on RST. Re-run with `dist/` present: `319 / 2` in 15.42 s.
- **Contract** exported from `app.main.app`: `"version": "0.5.0"`, six `/api/v1/workorders` paths, 63,743 B; `openapi_0_4_0.json` `git rm`-ed in the same commit. `pnpm gen:api` → 5 files, lint 0, `205 / 15`, build 0, `dist\index.html` 388 B.
- **The request set, against RST:**

| Request | Result | Server ms |
|---|---|---|
| `/health` | `0.5.0`, `workorders 1.0.0`, `persist=diag_log`, `frontend=built` | 6 |
| `/workorders` (defaults) | `count 200, more True`, first `662704`, **0 closed rows in the page** | **76** |
| `?includeClosed=2&limit=3` | three C rows, badges `C\|1LY-260826-003\|6\|0` etc. | 352 |
| `?includeArchive=2&limit=3` | 3 + more | **1167** |
| `?includeArchive=1&limit=3` | 3 + more | 627 |
| `?woType=CP` | `count 0` — RST has no CP location | 52 |
| `?woType=X` | `400 {"ok":false,"code":"BAD_FILTER",…,"rid":…}` | 2 |
| `?search=bin 16` | one row, 662704 | **851** |
| `/workorders/662704` | `week`, prog 6 `100% Complete`, `progressAll` **8**, `detailsMissing false`, the five-title hierarchy, `filtersFor {N,0,0}`, `Planned $0.00 \| Actual $36.52 \| Diff +$36.52` | **122** |
| `/workorders/999999999` | `404 NOT_FOUND` | 13 |
| `/workorders/530062` | `404 ARCHIVED` | 5 |
| `/workorders/143760` (no details) | `200`, `detailsMissing true`, `prog 0`, `within range`, sid `110705/071` | 32 |
| `/events` | 5 rows, newest first, braces stripped, editor `Lionel Rees (Livewires)`, sources `WO Maintenance` ×4 and `WOW` (the Create) | 84 |
| `/linked` · `/queries` · `/pos` | `count 1 root 3CL-260826-010` · 0 · 0 | 3 · 10 · 31 |
| `/api/v1/nope` | `404 NOT_FOUND` flat **with `dist/` mounted** — OD-19 still holds | 8 |

- **The trail, read after two seconds** (`Show-DiagTrail.ps1 -UserId 21 -Minutes 15`): exactly the predicted set — `wo search refused: woType='X'`, `wo 999999999 not found`, `wo 530062 is archived`, `wo 143760 has no WO_N_Details row`, each with its middleware `[G]` twin, and the planner polls' `[F]`s. **Not one `[F]` from a workorders 200** — OD-69 working as signed.
- **`Diag_Log` 147 → 148 → 149 across the last two blocks**, and both additions accounted for: the `/nope` 404 (`[G]`, OD-59), and an `[S] diag purge 0 of 0 rows older than 60 days` at 16:59 — **the daily purge firing five minutes after startup, on its own**. The suite wrote nothing, which is the claim that mattered.

## 5. Facts verified this session

*(S1k's and D1a's facts stand as recorded in 1.1.0.)*

**W1a:**

- **`dbo.Progress` has nine rows on RST, eight of them active** — `9 Machining` is `Active = '0'`. And **zero open WOs sit on an inactive progress row**, so `progressAll = 8` is correct and OD-67's card row covers every open WO, including the 2,346 at `7 Scheduled` and 404 at `8 Assigned`. (The spec predicted nine; the prediction was wrong, the code was right.)
- **RST's open work is 1,084 N + 2,705 M**, against 166 k closed/cancelled live and **453 k archived** — the archive arm is load-bearing here, not a KT curiosity.
- **`Server_Name` is NULL on all 169,678 headers and all 247,921 event rows**; `funGetServerName` returns nothing on RST. `Source_Form` is what .NET actually writes: `WO Maintenance` 190,573 · `WO ScheduleX` 43,288 · `WOW` 14,059 · `WO Timesheet` 1 — **with the space**, not KT's `WOMaint`.
- **`WO_Event_History.event_details` is `varchar(max)`**, not the varchar(1000) the audit brief carried; the 990-character cap is the writer's convention.
- **Seven live headers have no `WO_N_Details` row** (five of them open). The oracle's INNER JOIN shows them blank while still listing them; the port reads them and says so.
- **`WO_Responsible_User` and `WO_Assessment_Log` are empty on RST**; `WO_Query` has 225 rows (Q 121, N 101, A 3). 1,894 linked children; 54,585 WOs carry PO lines.
- **RST short ids are `<area>-YYMMDD-NNN`** across ~75 area prefixes, **zero `WO-`**; KT's are `K-…` with 216 `WO-`. RST has **no CP location at all** (KT has one).
- **`Last_Save_Date` carries milliseconds** (`19:19:04.057`) — a usable optimistic-lock twin for W3.
- **`wmsp_WO_QuerySelectDynamic`** is a nine-column select over `dbo.WO_Query` with the WHERE and ORDER BY pasted in — ports to a static statement with no loss.
- **`"Select"` (double-quoted) parses on RST** under the default `QUOTED_IDENTIFIER ON` — trap 1 never fired.
- **The 23-join record costs 122 ms** on RST; the leading-wildcard `search` costs 851 ms over 169 k rows, and `includeArchive=2` 1,167 ms over 453 k. All under the 2 s persist line, all worth watching (§9, item 53).

## 6. Mistakes caught this session

*(1–12 as recorded in 1.1.0.)*

13. **`ruff format --check` had never run on `main.py`.** The W1a smoke ran it and found five reflows — `SLOW_MS`, a missing blank line before `Conn`, the diag-wired line, the `INTERNAL` `JSONResponse`, `dbName` — **all of them from cards 1.0.5/1.0.6**, none from W1a. D1a's smoke ran `ruff check` only, and `E501` is ignored, so `ruff check` can never catch it. This is the S1h router 1.1.1 lesson repeated on a second file. Fixed as `main.py` card **1.0.8, format only, app version unchanged**. *The smoke runs `ruff format --check` on every slice, not `ruff check` alone.*
14. **`SIM300` (Yoda condition)** in my own new contract test: `assert ENVELOPE <= set(...)`. Re-cut as `test_openapi_contract` **1.1.1** with the operands swapped; no assertion change.
15. **The spec predicted `progressAll = 9`.** It is 8 (§5). A prediction that misses is a finding either way — this one proved the filter is right and the picture row is covered. Recorded in the spec's 1.0.2 at doc-set time.
16. **The acceptance line "`Diag_Log` before == after" was unprovable as written** while a dev server is running: the purge task and any open planner tab write rows on their own schedule. The honest claim is "no row *from the suite*", and that is what was verified (§4c). To be fixed in the W1a spec 1.0.2 and in Ways of Working.
17. **A double download.** `WOMaint_2026-09-19_view (1).json` landed in `docs/reference/` and was renamed before the commit. The drop block's `Test-Path` guard checks presence, not the `(1)` suffix — worth one line in the next drop block.

## 7. Patterns confirmed

*(S1k's and D1a's patterns stand.)*

- **Predict, then read — third use.** 319 / 2 was written into the spec before the run and read back exactly; the only miss inside it (`progressAll`) pointed at a data fact worth knowing rather than a defect.
- **Cross-check the card against itself before it ships.** Every `r["Column"]` in `repo.py` was matched against its statement's select aliases, and every repo dict key against the schema's fields (88 + 4), by script, before the drop. Nothing came back at the smoke.
- **The evidence block is the spec.** Blocks W1-E and its two addenda answered eight design questions before a line was written — the archive arm, the CP rule, the id shape, `Source_Form`, the details orphans, the `Progress` domain, the dynamic proc, the ms on `Last_Save_Date`.
- **A resource export beats a 33 MB project zip.** Fourteen small exports, extracted by script into versioned cards, read in full — the whole audit ran off them.
- **The trail rule, third use.** Predicted five `[G]`s and no `[F]`; read exactly that, and the two unexplained `Diag_Log` rows turned out to be the `/nope` 404 and D1a's purge task proving itself.

## 8. Doc-correction queue — still unapplied, now larger

The five files queued on 09-15 have **not** been cut. They carry S1k §9.1, the two audits, D1a, and now W1a:

- **Index → 1.10.0**: §1 state (HEAD `797948a`, tag `w1a-api-1.0.0`, **319 / 2** and 205 / 15, app 0.5.0), §3 the `app/workorders/` files and the six reference cards, §6 next = **W1b**, OD series at **71**, items at **55**. Also the three stale rows 1.9.0 still carries: the log list stops at 09-14 (09-15, 09-19 1.1.0 and 1.2.0 missing) and the Index row itself says 1.8.0.
- **Landmines → 1.10.0**, from W1a: `ruff check` can never catch a formatting drift while `E501` is ignored — `ruff format --check` is its own gate; `Select` is a reserved word and needs `"Select"`; a leading-wildcard `LIKE` over 170 k rows costs ~850 ms on RST; `Server_Name` is NULL on every RST WO row and `funGetServerName` returns nothing there; `event_details` is `varchar(max)`; `dbo.Progress` has nine rows on RST (one inactive), six at KT; seven live headers have no details row; RST has no CP location; `WO_Responsible_User` and `WO_Assessment_Log` are empty on RST.
- **Ways of Working → 1.4.0**: `ruff format --check` in every smoke; a new package gets its empty `__init__.py` in the drop block (the D1a precedent, twice now); a spec's test counts are read from the cards before the run and a moved count is a spec re-cut, not a note; "no row from the suite" replaces "`Diag_Log` unchanged" while a dev server runs; the drop block should catch a `(1)` double download.
- **Port Spec → 1.0.8**: the W1a row; **OD-5 half-closed** (the record is readable; the page is W1b); the W1b/W2/W3/W4 cut restated from the audit brief.
- **Architecture → 1.0.9**: `app/workorders/` in the tree; the six published paths; app version 0.5.0 and `openapi_0_5_0.json`; D-9 gains the workorders contract; OD-62…OD-71 listed.
- *(the S1k and D1a lines from 1.1.0 carry forward unchanged)*

## 9. Open items (55)

*(46–52 as recorded in 1.1.0.)*

| # | Item |
|---|---|
| **53** | **Read speed on RST**, the standing priority: `search` 851 ms (leading-wildcard `LIKE` over 169 k rows), `includeArchive=2` 1,167 ms (453 k), `includeClosed=2` 352 ms. All honest but slower than the record's 122 ms. Options to weigh at W1b: a prefix match when the term looks like a short id, an index check on `Entry_date` / `Short_WO_Id`, or a debounce and a smaller default page |
| **54** | **`wm-seg-9px` has no rule in stylesheet v2.69** — the `CompleteWithinSeg` segment relies on a class that does not exist. Same class of finding as `psc-toolbar-btn` in S1k; settle it when W1b ports the segment |
| **55** | **`WO_Query` types `N` and `A` on RST** (101 and 3 rows) — the oracle labels only `Q` and `R` and shows the rest raw. What are they, and do they belong in the port's label map? |

## 10. Next

1. ~~D1a~~, ~~W1a~~ — done, tagged.
2. **W1b** — the WOMaint page: list panel with the four type chips and the two mode chips, the record, the four read-only tabs, `MenuItem_WOMaint` live, `activeKeyFor` gains `/workorders`. Needs the live WOMaint screenshot for the pixel checks, and settles items 53 and 54.
3. **Auth** — a condition of the Redstag install, not an option. Still blocked on Andrew's user list.
4. **W2 / W3** (the five write procs are in the W1a spec §2.4), then **S2b / S2c**, then **D1b**, then deploy.
5. **The morning report** — blocked on which mail the box may send through.
6. The doc set (§8) at the close of this session.

## 11. Changelog

- 1.2.0 (2026-09-19) W1a added: OD-62…OD-71 delegated; commit `797948a` and tag `w1a-api-1.0.0`; 319 / 2; §4c the measured smoke and the trail; §5 the RST facts the audit turned up; mistakes 13–17; items 53–55; the doc queue's W1a lines.
- 1.1.0 (2026-09-19) D1a added: OD-55…OD-61 signed; commit `c7de038` and its tag; 218 / 2; §4b the measured smoke; mistakes 7–12; items 50–52; the doc queue's D1a lines.
- 1.0.0 (2026-09-19) The S1k session: shell built, smoked, committed and tagged; the WOMaint and D1 audits written; four uploads read; items 46–49 raised; the 09-15 doc queue still open and now larger.
