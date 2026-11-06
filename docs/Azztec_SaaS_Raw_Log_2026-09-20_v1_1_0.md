# Azztec SaaS — Raw Log 2026-09-20

**File:** Azztec_SaaS_Raw_Log_2026-09-20_v1_1_0.md · **Version:** 1.1.0 · **Date:** 2026-09-20 · **Author:** Adriaan
**Status:** Session record, append-only. One slice: **W1b — the WOMaint read-only page.** Audited from the PK exports plus two new reference cards, specced, signed, built in five tranches, smoked in four rounds, committed and tagged. The doc set (§8) is **still the thing not cut** — the queue is now three sessions deep.
**Target path:** `docs/Azztec_SaaS_Raw_Log_2026-09-20_v1_1_0.md` (+ project knowledge; replaces 1.0.0 in PK — raw logs keep every version in `docs/`)
**Parent:** log 2026-09-19 1.2.0. Its §8 doc-correction queue is carried forward here, unapplied, with today's additions.

---

## 1. Decisions this session

| ID | What | State |
|---|---|---|
| **OD-72** | The W1 read page ships as **two** slices: W1b = list + the Work Order tab (incl. Details/Notes); **W1c** = Query/Notes, Linked WO, WO Event History, the Purchase Orders sub-tab and `PONumBadge` | 🤙 2026-09-20 |
| **OD-73** | `/workorders` + `/workorders/$id`; the URL carries `type`, `closed`, `archive`, `q`. **`limit`/`offset` stay out** — paging position is not something a shared link should reproduce | 🤙 2026-09-20 |
| **OD-74** | The status row draws the oracle's **eight** cards. An `F` record lights none; `statusTitle` still names it. Becomes a real gap in **W3**, where the row is how status is *set* — raised as an item against that slice | 🤙 2026-09-20 |
| **OD-75** | The progress row draws **one card per `progressAll` row** — the oracle's six symbols for ids 1–6, a plain titled card for 7 and 8 | 🤙 2026-09-20 |
| **OD-76** | The port **drops all five dead classes** and takes the inline styling that actually renders. **Closes item 54.** KT carry-back raised | 🤙 2026-09-20 |
| **OD-77** | Paging: `limit` 200, Load more while `more`, footer `No of Records: 200+`. **No total, ever** | 🤙 2026-09-20 |
| **OD-78** | Search: **300 ms debounce, minimum 2 characters**, the leading-wildcard `LIKE` kept as parity. Item 53's page-side answer | 🤙 2026-09-20 |
| **OD-79** | The write controls **draw inert** (`aria-disabled` + OD-51 title); the Summary toggle, tips, AI embed and toast bar are **not rendered** | 🤙 2026-09-20. **Count wrong in the spec** — see §6 |
| **house** | `docs/` carries the current version of each compiled doc and spec plus the newest handover brief; **raw logs keep every version**; git history keeps the rest | Taken on "should it be like this?", executed as its own commit `44be75d` (42 files) |

## 2. Shipped and committed

- **`44be75d`** — `docs:` 42 superseded doc versions removed. Nine Architectures, nine Indexes, eight Planner Port Specs, seven WoWs, eight Landmines, two old handover briefs. 27 kept.
- **`330c0c7`**, tag **`w1b-page-1.0.0`** — W1b. 30 paths: 19 new in `features/workorders/`, 2 routes, 5 modified (`shell/rules{,.test}`, `planner/SelectedWOCard{,.test}`, `planner/PlannerView.test`), `routeTree.gen.ts`, 3 docs. **No backend file, no contract file, no lock file, no migration.**
- **OD-5 is closed.** `SelectedWOCard` 1.1.0 drops `OPEN_TITLE`; the disabled button is a `<Link to="/workorders/$id">`.
- Reference cards added: `Workmate_Stylesheet_2026-09-20_v2_69.css` (141,544 B, byte copy, md5 verified), `PONumBadge_2026-09-20_view.json`.

**Cards cut: 25 + 16 smoke-fix revisions = 41.** The fix revisions are why `symbols.tsx` is at 1.0.2 and `wo.css` at 1.0.1 in a slice that shipped today.

## 3. Suite state

| | Before | After |
|---|---|---|
| Frontend | 205 in 15 files | **384 in 23 files** |
| Backend | 319 passed, 2 skipped | **319 passed, 2 skipped** (re-run with `dist/` present) |
| Lint | 0 | 0 |
| ruff check / format | 0 / 0 | 0 / 0 |

Spec 1.0.0 predicted ~331 in 24 files. Actual **384 in 23**: the per-file estimates were low across the board and "24 files" counted cards, not test files. Re-cut owed as spec **1.0.1** (§8).

**Build:** `planner-*.js` survived; `workorders.index-*.js` and `workorders._id-*.js` are siblings; `WoMaintView-*.js` (46 kB) and `WoMaintView-*.css` (8.5 kB) split out as shared chunks.

## 4. Evidence read this session

- `WOMaint_2026-09-19_view.json` v16.28.3 — 281 components, read component by component: panel geometry, the four type chips, the list table, the filter row, the hand-built tab strips, the header/schedule/assignment/resources cards, the Details three-column layout.
- The four symbols in full; `PONumBadge_v1_2_0` new.
- **Stylesheet v2.69** — the nine `--wo-rgb-*` / `--wo-color-*` and ten `--po-rgb-*` tokens, verbatim.
- The generated client on the box: six operations, all types, `…Options()` helpers forwarding `signal`.
- **Icon library v1.1.0** (192 glyphs, paths only) — the 13 missing glyphs extracted **by script and round-tripped byte-identical against the library before shipping**. None opened with a relative command this time; the check ran anyway.

## 4b. W1b — the smoke, measured

Four rounds. Round 1: 11 lint errors, 31 test failures. Round 2: 3 lint, 2 failures. Round 3: 0 lint, 384 green. Round 4: two defects found **on the screen**, invisible to the suite.

| Case | W1a | W1b | server ms |
|---|---|---|---|
| default list | 76 ms | 169 ms wall | **100** |
| search `bin 16` | 851 ms | 292 ms wall | **279** |
| `includeArchive=2` | 1,167 ms | 670 ms wall | **659** |
| record 662704 | 122 ms | 47 ms wall | **39** |

**Trap 17 never fired.** The archive arm came in at roughly half W1a's figure, so nothing crossed the 2,000 ms persist line. Item 53's evidence: the 851 ms was not reproducible on a warm box — **279 ms** — so the debounce (OD-78) is the right answer and a query rewrite is not yet justified.

**Trail:** eight `[F]` planner range rows (the poll, predicted), **zero workorders 200 rows** (OD-69/OD-73 as signed), one `[G]` `wo 143760 has no WO_N_Details row` — correct behaviour, the same OD-65 condition the screen renders as a notice.

**Screen checks, all seven:** rail lights Plannex and WO Maint; the planner's Open navigates; four type chips switch list and title; CP → empty list, footer 0; Closed and Archive mutually exclusive; **662704** renders eight status cards with Active lit, eight progress cards with 100% lit, Week on the segment, the five-title hierarchy, `Planned $0.00  |  Actual $36.52  |  Diff +$36.52`, Week No `2026.35`; **143760** shows the OD-65 notice and no progress row.

**Live proof of two ported oddities.** On `560-MEP-001-0006` (status `A`, progress `7`) the ID pill is `#007BFF` while the Approved card is `#0B5ED7` — two different blues, exactly as `txtWorkOrderId`'s own map says, and correctly *not* "fixed" to the token. Same record lights **Scheduled** as a plain card: OD-75 earning its place on the ~2,750 RST WOs a fixed six would have lit nothing for.

## 5. Facts verified this session

- **Perspective renders `props.style.classes` as `psc-<name>`; a class on `meta.classes` is never reachable by a `.psc-` rule.** Measured across all 281 components: **five of twelve** `wm-*` classes do nothing — `wm-seg-9px` (no rule at all) and `wm-tabs`, `wm-tabs-sub`, `wm-panel-header`, `wm-btn-tertiary` (on `meta.classes`). Costs nothing visually: the real styling is inline.
- `PONumBadge`'s second character is a **flag channel**, not just a separator (`!` `w`/`W` `c`/`C` add a dot and an orange ring). W1a's plain `status|poSid` is correct for a read.
- The 25/50/75 progress symbols print **`1` `2` `3`** — the quarter count, not the percentage.
- **A TanStack route file named `workorders.tsx` beside `workorders.$id.tsx` is a LAYOUT, not a sibling.** See §6.
- `Get-NetTCPConnection` reports the **socket-creating** PID, which can be a dead reload parent whose child inherited the socket. See §6.

## 6. Mistakes caught this session

1. **`wm-*` classes — I got it backwards, then caught it.** First grep was `.wm-`; Perspective emits `psc-wm-`. The W1a log was right and I was wrong. Re-measured before it reached the spec.
2. **`WO_MATERIAL.assignment` was `undefined` — 24 test failures.** I re-exported `assignment`/`search` from the shell rather than duplicating them, then wrote a status-card table naming `assignment` as one of its eight glyphs. **The `as WoIconName` cast I had flagged the turn before is exactly what hid it.** Fix: `GLYPHS` (all fifteen) with `WoGlyphName` as its key type, so a glyph named in a table but absent from the record is now a compile error. The test that "passed" had asserted thirteen things were fine and never asked whether thirteen was the right number.
3. **`<Link>` in `SelectedWOCard` broke two `PlannerView` tests.** A real regression from closing OD-5, not a flake — PlannerView renders the card without a router. Both test files now mock `Link` via `importOriginal`.
4. **`.wo-badge` was never written into `wo.css`.** `symbols.tsx` *said* the static half lived there and nothing did, so `background-size`/`-position`/`-repeat` fell back and the progress underline filled the whole badge at 0.95 alpha — **every WO number in the list rendered as a solid colour block.** Spec trap 5 named this exact failure and I walked into it by asserting the CSS existed instead of checking.
5. **`routes/workorders.tsx` + `workorders.$id.tsx` = layout + child.** `/workorders/662396` matched the child, mounted the parent with `woId={0}`, and rendered nothing else — no `<Outlet/>`. Symptom: "Select a work order from the list." with the id in the URL and **no record request in the log**. Fix is the file name: `workorders.index.tsx`, `createFileRoute('/workorders/')`.
6. **`React.ReactNode` with no React namespace import** in `WoRecordCard` — would have failed the build, not the tests. Caught by a sweep before the card went out.
7. **`import './wo.css'` missing from `WoMaintView`.** The stylesheet would have shipped and never entered the build; every test would still have passed. Caught by checking how `planner.css` actually gets in.
8. **Overstated the trail prediction** — said "not one row from any workorders request" when the spec's claim was "not one workorders **200**". The `[G]` 143760 row is a workorders row and is correct; the looser wording would have called it a failure.
9. **"Stop the server" failed three times.** `Stop-Process -Id 30284` reported success, then "no such process", while the socket kept naming 30284 as owner. The listening socket belonged to a **dead reload parent**; the live child had inherited it.

## 7. Patterns confirmed

- **Defects 4 and 5 both landed exactly where the tests don't look.** No test renders real CSS (jsdom ignores it) and the props-driven view test never exercises the route that supplies the prop. The two deliberate gaps in the test strategy are where both screen defects lived. A green suite is not a smoke.
- **A cast is a place a bug can hide.** Both the glyph failure and the last lint error were assertions silencing a type that was telling the truth.
- **Predicting the number, then reading it off the cards, works.** 384 was the count before the run and the count after.
- A twin-file check that hashes before deleting caught a real duplicate and proved it harmless in one step.

## 8. Doc-correction queue — carried forward, now four sessions deep

- **Index §1 / §3.7, W1a spec §2.1:** `WOStatus` has **eight** cards (R H P K A V C D), not nine.
- **Landmines §C:** `psc-` vs `meta.classes` (§5); a stylesheet rule that *exists* is not one that *applies*.
- **Landmines §C (new):** a TanStack route file sharing a name with a `$param` sibling becomes that sibling's **layout**; use `<name>.index.tsx`.
- **Landmines §C (new):** `importOriginal<typeof import('…')>()` is standard Vitest but this repo forbids inline `import()` types — use a type-only namespace import.
- **WoW §6.2 (new):** "stop the server" means **`GET /api/v1/health` failing**, not a listener count of zero. The socket table can name a dead PID.
- **WoW (new):** the `docs/` retention rule from §1.
- **W1b spec → 1.0.1:** real counts (384 in 23), the **25th card** (`record.fixture.ts`), the OD-79 control count (**seven** in the filter row, not eleven — Manage Plan, Link WO, Email WOs and New PO live in the record card and the PO sub-tab), and the smoke-fix revisions.
- Everything still queued from log 2026-09-19 §8.

## 9. Open items

- **54 — closed** by OD-76.
- **53 — answered** on the page side by OD-78; the 851 ms did not reproduce warm (279 ms), so no query rewrite yet.
- **new:** the four KT `meta.classes` carry-backs — move to `props.style.classes` or delete the four unreachable rules.
- **new:** `F` has no status card — flagged against **W3**, where status becomes settable and Deferred would be unreachable.
- **new:** `//workorders/662704` (double slash) resolves. Robustness, not a bug; recorded in case it ever matters.
- **closed:** `S1e_Web_Chunk_Spec_v1_0_0.md` restored to `docs/` 2026-09-20 (byte copy from PK, md5 `ce6e2a04…`). `usePlannerRange.ts`'s header reference now resolves in the repo.
- **eight live reference shots** into `docs/reference/` as `WOMaint_live_2026-09-20_<n>_<screen>.png` — Work Order/Details, Activity, Linked WO, WO Event History, Purchase Orders, Attachments, the date-range popup, and **the WO Wizard (Create WO) popup**. Four are W1c's pixel reference; the date-range popup is W3's.
- **new — the Create WO path has no slice.** The eighth shot is the WO Wizard / Create WO popup. Creating a WO is a write, so it is outside W1, and nothing in the doc set assigns it: not W2, not W3, not W4 (delete/clone/link). `WO Wizard` is also its own rail item, so it may be a module rather than a WOMaint popup. **Unassigned — to be placed at the W2 audit**, not guessed here.
- Carried: the Assessment card (W1c OD candidate), `WO_Query` `N`/`A` codes (item 55), `Summary` toggle meaning, windowing beyond Load more.

## 10. Next

1. The doc set — §8 is now the largest single debt in the project.
2. **Auth** — the one critical-path item, blocked on Andrew's user list. W1b is the first surface a real Redstag user will click and it still runs on dev actor 21.
3. W1c, then W2/W3, S2b/S2c, D1b, deploy. Install target ~2026-09-30.

## 11. Changelog

- 1.1.0 (2026-09-20) After the tag: S1e restored to `docs/`; the reference shots are **eight**, not seven — the eighth is the WO Wizard / Create WO popup, recorded in §9 as a write path with no slice assigned. No decision, count or finding in §1–§8 moved.
- 1.0.0 (2026-09-20) W1b: audit, spec, 🤙 on OD-72…OD-79, 25 cards + 16 fix revisions, four smoke rounds, `330c0c7` / `w1b-page-1.0.0`. Plus the `docs/` retention rule and its commit `44be75d`.
