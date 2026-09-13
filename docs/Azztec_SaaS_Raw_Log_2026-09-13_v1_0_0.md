# Azztec SaaS — Raw session log 2026-09-13 (S1g)

**File:** Azztec_SaaS_Raw_Log_2026-09-13_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-13 · **Author:** Adriaan
**Append-only.** Supersedes §7–§9 of `Azztec_SaaS_Raw_Log_2026-09-12_v1_1_0.md`; that log's §1–§6 (the S1f record) still stand.
**Session:** the compiled doc set from log 1.1.0 §7, then the S1g audit, then S1g built and shipped.
**Ended at:** HEAD `0cb41b8` (docs), slice tag `s1g-readonly-1.1.1` at `449f19d`. Backend 125 green, frontend 155 green in 11 files.

---

## 1. Decisions signed this session

| ID | Term | Where |
|----|------|-------|
| **OD-30** | Request cancellation: the generated `queryFn` already forwards TanStack's `signal` into the fetch (`react-query.gen.ts` 78/82), so a superseded `/range` aborts in the browser when its query loses its last observer. Nothing built; pinned by test. No nav debounce. Pool 5+10 unchanged. **Server-side cancellation is impossible on the sync `def` + pyodbc stack** — the query runs to completion and still logs `[F] range …`; recorded, not a defect | audit, §6 verified on the box |
| **OD-31** | No shadcn/ui, no lucide in S1g. The day dialog (`showDay`) and the worker menu (`.wsel`) are **ports**, and OD-27 puts adoption at the first component that is *not* a port. No `pnpm add` in this slice | audit |
| **OD-32** | ~~Priority badge colour by rank in `priorities[]`~~ — **signed, built, then withdrawn the same day.** See §4.1. The rank classes (`r1`..`r4`) still render and are still tested; they carry no colour. Replacement decision is not yet taken: `Priority.Colour` is a backend slice (§9) | audit, then §4.1 |
| **OD-33** | Hover stays parity: `chipTitle` byte-for-byte with oracle 600-606. No list arrived, so nothing was added. Pinned by a test that asserts `title === chipTitle(wo)` with a rank set | audit |
| **OD-34** | Chrome says only what is true: the hint is `click = select · ← → = navigate · T = today · Esc = clear` (the oracle's drag/undo/double-click text is a lie here); the rail row title ends `click = filter the work to this person`; `Open in WO Maintenance` renders **disabled** with `title="arrives with the WO module (OD-5)"`; write affordances (`+ person`, `×`, Unpin, Plan hours, the orb) are **absent, not disabled**; the actor label is `actor #<id>` until identity (OD-2) | audit |

## 2. Shipped and tagged

**Docs commit `81089ce`** — the compiled set from log 1.1.0 §7, five files, 855 insertions:
Index **1.3.0**, Landmines **1.3.0** (§C +6, §E +3, new §F "the box", changelog → §G), Ways of Working **1.3.0**, Architecture **1.0.2**, Planner Port Spec **1.0.1** (read in full for the first time — the correction queue carried since 2026-09-10 is applied).

**Slice commit `449f19d`**, tag `s1g-readonly-1.1.1`, 21 files, +2084 / −192:

| File | Version | Note |
|---|---|---|
| `features/planner/rules.ts` | 1.1.0 | filters + precedence, `teamOptions`/`priorityOptions`/`workerMenu`/`workerLabel`, `priRank`/`priClass`/`priRankMap`, `dialogTitle`/`dialogRows`, `cardRows`, `HINT`/`actorLabel`, `dowIso`/`fmtLongAny` |
| `features/planner/rules.test.ts` | 1.1.0 | 32 → 55 cases |
| `features/planner/store.ts` | 1.1.0 | `filters` + setters, `clearFilters` (oracle 1537), `dayOpen`, `clearSelect` |
| `features/planner/planner.css` | **1.1.1** | S1g blocks ported; the OD-32 colours removed again before the commit (§4.1) |
| `features/planner/range.fixture.ts` | 1.1.0 | RST-shaped priorities, two labour rows, `hasPO`, a two-day span, `resp` |
| `features/planner/FiltersRow.tsx` + test | 1.0.0 | menu open/close local, 150 ms search settle, Escape scoped to the row |
| `features/planner/SelectedWOCard.tsx` | 1.0.0 | read-only; test **1.0.1** |
| `features/planner/DayDialog.tsx` | 1.0.0 | plain component, oracle CSS; test **1.0.1** |
| `features/planner/WOCard.tsx` + test | 1.0.1 | `priRank` prop; title unchanged |
| `features/planner/DayCell.tsx` | 1.0.1 | day-head click, cell/list click clears |
| `features/planner/PlannerGrid.tsx` + test | 1.0.1 | filters → capacity precedence, rank map, grid background click |
| `features/planner/WorkerPanel.tsx` + test | 1.1.0 | team filter, `.on`, click-to-filter |
| `features/planner/PlannerView.tsx` + test | 1.1.0 | composition, keyboard, the OD-30 abort case |
| `src/router.tsx` | — | **deleted** (open item 20 closes) |

**Docs commit `0cb41b8`** — `Azztec_SaaS_S1g_Readonly_Chunk_Spec_v1_0_0.md`, 289 lines.

## 3. Suite state

Backend **125 passed**, 2 warnings, 6.64 s — unchanged by this slice (no backend file touched), re-run with the new `dist/` present.
Frontend **155 passed in 11 files** (96 → 119 after the library drop → 142 after the three new components → 155 after the patched four).
`pnpm lint` silent. `ruff format` 24 files unchanged, `ruff check` all passed. `pnpm build` 657 ms. Deep link `GET /planner?mode=week&anchor=2026-09-16` → `200 text/html`.

## 4. Mistakes caught this session

### 4.1 OD-32 was signed on an assumption and falsified by the table the same day

The audit proposed colouring the priority badge by **rank in `priorities[]`** (which the API sends in `Sort_Sequence, Priority_Id` order) on the reasoning that RST has no A–D letters and rank ordering would reproduce the oracle's colouring on KT. It was signed, built (`rules.priRank`/`priClass`/`priRankMap`, `planner.css` `.pri.r1..r4`, cases in three test files), and shipped to the box. Adriaan's screenshot then showed **P2 red, P1 not** — and `dbo.Priority` says why:

```
Priority_Id Short   Title                     Sort_Sequence  Colour
1           P2      Priority 2                1              #FF9F40
5           P1      Priority 1                1              #FF0000
9           ST      Stores Items              1              #808000
14          P2S     Small Job <$200 and <2Hrs 1              #FF0000
2           P3      Priority 3                2              #74EE66
10          T       Action Today              2              #808040
3           WK-END  Weekend work              3              #FF0000
11          W       Action Weekend            3              #808040
12          P5      Priority 5                3              #C499C1
13          P6      Priority 6                3              #C0C0C0
4           P4      Priority 4                4              #0080FF
8           SHUT    Shutdown Work             4              #FF0000
6           N/A     Not Applicable            5              #FFFFFF
7           REQUEST Requisition               6              #FFFF80
```

**Fourteen rows, not seven. Four tie at sequence 1, four at 3, two at 2 and 4.** The tie-break is `Priority_Id` (OD-11), so rank 1 is P2 (id 1) and P1 (id 5) is rank 2. Rank is not priority on RST. Withdrawn in `planner.css` **1.1.1** — colour rules deleted, classes left rendering and tested, header states the reason. Cost: one build cycle.

Two lessons, both new:
- **A decision about data is not signable from a screenshot.** The rank scheme was proposed from a chip layout; five minutes of `SELECT` would have killed it at the audit. Rule: any OD whose correctness depends on a table's contents is blocked on reading that table, not on 🤙.
- **Claiming absence from an API shape is not claiming absence from the DB.** In the same reply I said "the colours don't come from the database" — true of `/range`, which sends id/short/title only, and false of RST, whose `Colour` column is populated and varied (KT is the one with #FF8000 on every row — Landmines §E, still correct about KT). The honest sentence was "the API doesn't send it"; what I wrote read as "it isn't there".

### 4.2 The Priority column names were wrong in the query I handed over

`SELECT Priority_Id, Short, Title, …` → two `Msg 207 Invalid column name`. The real names are `Short_Priority_Id` and `Priority_Title`, and they were in `sql.py` 201-204 the whole time — a file already in project knowledge and already read this session. Re-emitting a column list from memory is the same failure as re-emitting a file from memory (Ways of Working §5); it just costs a round trip instead of a build.

### 4.3 `pytest -q` on top of `addopts = "-q"` deletes the count line

Three sessions of "the count line disappeared", blamed on `Select-Object -Last 3`, then `-Last 6`, then `Tee-Object`. The cause was in `pyproject.toml` line 49: `addopts = "-q"`. The command added a second `-q`; two `-q`s suppress the summary entirely. `uv run pytest` with no flag prints `125 passed, 2 warnings in 6.64s` first time. The exit code was always the real gate.

### 4.4 Downloads is not a staging area

The S1g spec card was presented at the audit and only saved to Downloads hours later, so the docs copy in the commit block failed silently-ish and `git add -A` committed the slice **without its spec**. Fixed in `0cb41b8`. Separately, a drop block from earlier in the session was re-run and every copy failed for the same reason (the files had already been moved out of Downloads) — harmless, because `Test-Path` on the targets showed the sizes already on disk, but it proves the rule: **the drop block's verification line is what tells you whether the drop happened**, not the copy's silence.

### 4.5 Two browser tabs during a smoke

14:41:20 in the dev-server log shows two `/range` requests for the same window in the same second with different rids. Two tabs polling doubles the load and makes timing evidence useless. One tab for smokes (Landmines §C already says to close stale tabs; this is the same rule for a different reason).

## 5. Verified this session

- **Both memory caps applied.** `max server memory` 2147483647 → **8192**, in use, via `sqlcmd -S localhost -E -C` under the Windows login (open item 16 closes). `.wslconfig` written fresh (`[wsl2] memory=8GB swap=2GB`) + `wsl --shutdown`; Docker Desktop has stayed down since (item 17 closes on its first clean start under the cap). ODBC 18 needs `-C` for the local self-signed cert — Landmines §B, hit again.
- **SSMS is not needed** and `dbWorkmate` lives at the instance default `…\MSSQL17.MSSQLSERVER\MSSQL\DATA\`; `sqlcmd -E` under `AzztecDev\Azzte` (sysadmin) does everything `svc_workmate` cannot.
- **OD-30, both halves.** Browser: the abort case in `PlannerView.test.tsx` passes (first signal `aborted === true` after a rerender with a new anchor). Server: the 14:41:55–14:42:14 burst in the dev log shows twelve windows completing 0.3–11 s **after** the user had clicked past them — exactly the behaviour recorded as unfixable on this stack.
- **The slice on real RST**, screenshotted: filters row with `actor #1`; team select carrying `MAINT · 107`-style counts and `(contractor)` suffixes over 14 teams; worker menu grouped by team showing `4 selected`; priority filter; the selected card (Status · Start · End · Priority · Location · Hours · Responsible · planned labour · Open greyed · Clear) on `U-IN-00562-0130`; the **14 Sep dialog at 106 PM | 203.8h scrolling**; `← → T` moving the anchor and doing nothing from a text input; the June month view at 77 WO | 123 PM | 3021 done with the rail at `81 of 179 internal · 184 contractors hidden`.
- **`planner.css` 1.1.1 on the box**: 18,348 bytes, ASCII-only, zero `.pri.r*` rules, 155 still green.

## 6. The box, again — and a new open item

Docker down, 15.6 GB free, SQL capped at 8 GB, and the same `/range` window **still alternates fast/slow on a 60 s poll**: 2026-06-01..07-05 (3221 rows) ran 1.2 s, 8.1 s, 1.2 s, 8.1 s, 9.7 s, 1.2 s … for twenty-five minutes straight, and 2026-04-27..05-31 did the same for another twenty. A three-wide burst at 14:41:57 answered in 0.4–0.6 s each; a five-wide burst at 14:42:13 took 9.8–11.7 s each. Healthy singles are 0.12–0.65 s.

So §F's "over 2 s is the box" is **not the whole story**: the box is fine and the pattern persists. The shape (alternating, and degrading under concurrency) points at the four `text()` selects, the pool, or plan reuse — a backend question with a real answer available: `sys.dm_exec_requests` wait types **during** a slow one (`svc_workmate` has `VIEW SERVER STATE`). New open item 30; first line of the next backend audit. Not a frontend defect, and not S1g's to fix.

## 7. Doc-correction queue

**Apply before the next audit** (one docs commit):

- **Port Spec → 1.0.2:** §6 S1g row → done, tag `s1g-readonly-1.1.1`, 2026-09-13; §7's S1g bullet to past tense; §9 gains OD-30…OD-34 with OD-32 marked **withdrawn** and the reason; §9's "raised, unsigned" loses cancellation and priority colours, gains `Priority.Colour` (§9 below) and item 30.
- **Landmines → 1.4.0:** §C — TanStack aborts a fetch when the query loses its last observer *provided the queryFn consumed `signal`*, and hey-api's generated one does (verified by test, 2026-09-13); `pytest -q` on top of `addopts="-q"` kills the summary (§4.3); TS 6 `lib.dom` narrowings that make `as HTMLButtonElement` and `textContent ?? ''` lint errors (§4.4 of the build). §E — the **real `dbo.Priority` table** (14 rows, ties, `Colour` populated on RST and uniform on KT), replacing the "P1..P6/N-A" line's implication that rank ordering is meaningful. §F — the alternating-latency finding (§6): "over 2 s is the box" needs "…unless the box is clean, in which case see item 30".
- **Ways of Working → 1.3.1:** §5 gains "a decision about data is blocked on reading the table, not on 🤙" (§4.1) and "say *the API doesn't send it*, never *it isn't there*"; §6 replaces the pytest trimming rule with plain `uv run pytest` + `Select-String`; §2's drop rule gains "the verification line is the evidence, not the copy's silence" and "Downloads is not a staging area — save the card before the block runs".
- **Architecture → 1.0.3:** §5 drops the `router.tsx` line (deleted); adds `FiltersRow`, `SelectedWOCard`, `DayDialog`; §6 step 5 closes to "aborted in the browser, runs to completion on the server (OD-30)".
- **Index → 1.4.0:** §1 state; §3.2 gains the S1g spec; §3.4b/§3.5 the S1g versions; §6.1 OD-30…OD-34; §6.2 the four superseded files (still to remove by hand) plus this session's supersessions.
- Still carried, still unapplied (fourth session): Install doc, Bootstrap, `.gitignore` symlinks, Scaffold_Repo 1.0.2, the two `.vscode` files.

## 8. Open list

Closed this session: **11** (PK gaps), **16** (SQL memory cap), **17** (Docker cap — pending one clean start), **18** (cancellation → OD-30), **19** (priority colours → OD-32 withdrawn, superseded by 29), **20** (`router.tsx`), **22** (hover → OD-33 parity), **23** (the 5–15 s outliers were real → now item 30).

Carried and new:

1. **4** — six-month summary shape unsigned; 6M stays a disabled button.
2. **21** — `initialsOf` breaks on parentheses (`JP Paalvast (TS)` → `J(`). Backend, byte-1:1 with the oracle, needs an OD to depart. First line of the next backend audit.
3. **24** — `refetchIntervalInBackground: false` (hidden-tab pause) untested.
4. **25** — `prettier --check` not in the smoke; `pnpm lint` is ESLint only.
5. **26** — Ignition parity (`scripts/parity_range.py`) blocked on a KT dev copy.
6. **27** — `WeekStrip` counts internal members of the set it is given, so a selected **contractor** raises the strip's cap but not its `(n workers)`. `CapacityBar` 1.0.1 taking `nWorkers` is the fix; recorded in `PlannerGrid.tsx` 1.0.1's header.
7. **28** — `/api/v1/_diag/client` route and the `?debug=1` trail still not built (D-8, deferred past S1g).
8. **29 (new)** — **`Priority.Colour` to the badge.** RST populates it (§4.1), the API does not send it. Backend slice: `_PRIORITY_SQL` + `schemas.Priority` gain `colour`, regenerate the client, the chip paints from the payload as it already does for category `colours`; then a `DRY_RUN`-first `UPDATE dbo.Priority SET Colour` for the dev copy with the old values printed first. KT's uniform #FF8000 means the UI needs a fallback when every row matches.
9. **30 (new)** — **alternating `/range` latency on a clean box** (§6). Next backend audit's first line; evidence to gather is wait types during a slow request.
10. **31 (new)** — the **Forensics pack** (8 files, ~2,700 lines, `diag` schema, own middleware/SDK/provider, night-replay design) was handed over this session and **set aside by Adriaan** ("forget about Forensics, we have diag"). Not in project knowledge, not audited, no decisions taken. If it comes back it needs its own audit against `diag.py` 1.1.1, D-6/D-8, OD-18…OD-20, the Alembic plan, and the privacy question its own OD-3 raises.

## 9. Next slice

**S2 — move / undo / estimate** is the next *build*, but two audits come first and neither is S2:

1. **Backend audit** — items **30** (latency, with DMV evidence), **29** (`Priority.Colour`), **21** (`initialsOf`). All three are backend, all three are small, and 29 is what makes the planner's priority badges honest. A single backend slice could carry 29 + 21 with their tests.
2. **S2 audit proper** — `loadWO`, `movePreview`, `GET /preview` (OD-13), `service.move_wo`/`undo_move`/`set_estimate`, the weekno port, `@dnd-kit` installed here, the confirm dialog, optimistic drag with rollback, the undo toast, and the actor seam swapped for the JWT dependency (OD-12). `DRY_RUN=True` first — `dbWorkmate` is real RST data, and this is the first slice that writes to it.

Before either: apply §7's doc set. The next audit reads the docs, not this log.

## 10. Changelog

- 1.0.0 (2026-09-13) Initial. The compiled doc set from log 1.1.0 §7 (commit `81089ce`), the S1g audit (OD-30…OD-34), S1g built and shipped (`449f19d`, tag `s1g-readonly-1.1.1`), its spec committed (`0cb41b8`). OD-32 withdrawn the same day against `dbo.Priority`. Both memory caps applied. Items 11, 16, 17, 18, 19, 20, 22, 23 closed; 29, 30, 31 opened.
