# Azztec SaaS — S1g Read-only Chunk Spec (filters · selected card · day dialog · keyboard)

**File:** Azztec_SaaS_S1g_Readonly_Chunk_Spec_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-13 · **Author:** Adriaan
**Status:** Draft — awaiting 🤙 before the build
**Slice:** S1g — `rules.ts` 1.1.0 (the oracle's full filter precedence) · `store.ts` 1.1.0 · `planner.css` 1.1.0 · `range.fixture.ts` 1.1.0 · `FiltersRow` · `SelectedWOCard` · `DayDialog` · `WOCard` 1.0.1 · `DayCell` 1.0.1 · `PlannerGrid` 1.0.1 · `WorkerPanel` 1.1.0 · `PlannerView` 1.1.0 · keyboard `← → T Esc` · the cancellation test · `router.tsx` deleted · their Vitest files
**Sits on:** HEAD `81089ce` (docs, clean), tag `s1f-grid-1.0.1` at `8f742b4` — backend `main.py` 0.3.0 · planner 1.0.1 · 125 green; `web/` at S1f (96 green, 8 files, ESLint 10.10.0, TypeScript 6.0.3)
**Parent spec:** `Azztec_SaaS_Planner_Port_Spec_v1_0_1.md` §3 (contract), §6 (S1g row), §7 (UI plan), §9 (OD-5, OD-27, OD-29) · Architecture 1.0.2 §5, §6 · Ways of Working 1.3.0 §2, §4, §6 · Landmines 1.3.0 §C, §E, §F
**Source:** `Azztec_SaaS_Raw_Log_2026-09-12_v1_1_0.md` §8.18–§8.22, §9 and its seven carry-ins; the S1g audit in chat 2026-09-13 (OD-30…OD-34 signed)
**Oracle:** `Planner_v1_8_1.html` src 399–412 (the `.filters` markup), 536–557 (`teamMembers`, `anySelectedWorker`, `visible`, `visibleWOs`), 561–568 (`capacityWorkers`, `capacityPerWeek`), 600–606 (chip title — unchanged), 715–739 (`showDay`), 771–799 (`renderRail` incl. the row click), 801–836 (`renderSelected`), 839–858 (`renderFilters`), 869 (`select`), 1533–1538 (filter wiring), 1564–1569 (grid click), 1582–1596 (keyboard); CSS 138–148 (filters, worker menu), 194 (`.dlg.wide`), 267–272 (`.dd2 .job`), 282–283 (`.pri`), 328 (`.wk.on`), 336–347 (`.selc`, `.kv`, `.badge`, `.lab`), 361–369 (`.ovl`, `.dlg`, `.btns`)

---

## 1. Scope

Frontend only. **Nothing writes to the database.** No route changes, no schema changes, no backend source delivered. One backend re-run at the end because `web/dist` changes (§7). No new runtime dependency — OD-31.

**In:** the filters row (team · worker menu · priority · unassigned · search · Clear), `visibleWos` and `capacityWorkers` with the oracle's full precedence, the rail filtered by team with click-to-filter, the read-only Selected WO card, the day dialog off the day-head click, keyboard `← → T Esc`, grid-background click clears the selection, priority badge colours by rank (OD-32), the test that pins request cancellation (OD-30), `router.tsx` deleted (open item 20), and one test file per library/component file (pair rule).

**Out, cut at the audit gate (recorded so nothing is re-proposed):**

| Dropped | Why | Goes to |
|---|---|---|
| shadcn/ui, lucide-react, `components.json` | the day dialog and the worker menu are **ports** (`showDay`, `.wsel`); OD-27 decides adoption at the first component that is *not* a port | the first non-port component, whenever that is (OD-31) |
| Hover additions | no list arrived; `chipTitle` stays byte-for-byte with oracle 600–606 | a later OD when a list exists (OD-33) |
| `+ person`, `×` remove, Unpin, Plan hours, the estimate popover, the card orb, dblclick-opens | write affordances and AI; absent, not disabled (OD-34) | S2 (estimate, dblclick), S3 (unpin), S4 (labour), S5b (orb) |
| `Open in WO Maintenance` doing anything | no `/workorders/$id` route (OD-5) | rendered disabled with the OD-5 tooltip; the WO module |
| `initials` with parentheses (`J(`) | `initialsOf` is byte-1:1 in `rules.py`; the oracle does it too; a fix is a backend departure needing an OD | first line of the next backend audit (open item 21) |
| `R` refresh, `Ctrl+Z`, `D` debug, `S` suggest, `A` assistant keys | poll exists; undo/suggest/AI are S2/S5 | their slices |
| A `/planner` link on the CTA welcome page | `routes/index.tsx` is CLI-written and not in project knowledge — re-emitting it unread is the reconstruction rule | S2, with the file pasted first |
| Server-side cancellation of a superseded `/range` | impossible on the sync `def` + pyodbc stack; the query runs to completion; harmless at 70–700 ms (Landmines §F) | recorded, not a defect (OD-30) |
| `placeholderData: keepPreviousData` (old grid stays up during nav) | a UX choice, not a port; the oracle shows LOADING | considered, not taken; revisit if nav feels blank |
| Six-month, `@dnd-kit`, `/move`, `/_diag/client`, `?debug=1`, localStorage prefs, `parity_range.py` | unchanged from S1f §1 | — |

## 2. Decisions

### 2.1 Carried in

| ID | Signed | What it means here |
|----|--------|--------------------|
| D-9 | 2026-09-10 | camelCase JSON keys as the Ignition contract; the UI never renames |
| OD-1 | 2026-09-10 | locked PMs stay locked; the card shows `engine owned`, the dialog shows `· engine owned` |
| OD-5 | 2026-09-10 (interim) | WO details inline on the card; no `/workorders/$id` route |
| OD-23 | 2026-09-11 | `usePlannerRange` unchanged; nothing here widens a window |
| OD-26 | 2026-09-12 | rail toggles and the count line unchanged; the team filter applies **before** them (oracle 778 runs before OD-26's rows) |
| OD-27 | 2026-09-12 | every new surface is the oracle's CSS, scoped under `.wm-planner`, ASCII |
| OD-29 | 2026-09-12 | URL stays `mode` + `anchor`; filters, dialog state and selection live in the store, not persisted |

### 2.2 Signed at this gate (2026-09-13)

**OD-30 — request concurrency and cancellation.** The generated `queryFn` already forwards TanStack's `signal` into the fetch (`react-query.gen.ts` 78/82, pasted 2026-09-13), so when the window changes the previous `/range` query loses its observer and TanStack aborts its fetch in the browser. Nothing is built for it; `PlannerView.test.tsx` pins it (§6). No nav debounce. Pool 5+10 unchanged. Server-side cancellation is impossible on the sync stack and is recorded, not fixed: the dev-server terminal will keep logging `[F] range …` for requests the browser has already dropped — expected, not a leak.

**OD-31 — no shadcn in S1g.** The day dialog is `showDay` and the worker menu is `.wsel`: ports, with the oracle's CSS. Plain components. Tailwind/shadcn adoption stays where OD-27 put it. `lucide-react` not installed. No `pnpm add` in this slice.

**OD-32 — priority colours by rank.** `priorities[]` arrives ordered by `Sort_Sequence` (Port Spec §3). `priRank(wo, priorities)` = 1-based index of `wo.priId` in that list, 0 when absent; `priClass(rank)` = `r1`…`r4`, `''` above 4. CSS `.pri.r1`…`.pri.r4` reuse the oracle's A/B/C/D colours in that order; the A–D letter classes stay for KT. On RST `P1` lights red, `P6` and `N/A` stay base. **Claimed as an RST improvement, not parity** — parity holds only if KT's A–D are ranks 1–4 in `Sort_Sequence`, unverified until the KT copy.

**OD-33 — hover.** Parity. `chipTitle` unchanged. A list, when it exists, is an OD of its own.

**OD-34 — strings that describe absent features.** The filters hint becomes `click = select \u00b7 \u2190 \u2192 = navigate \u00b7 T = today \u00b7 Esc = clear` (oracle 409's drag / undo / double-click text is not true here). The rail row title's trailing line becomes `click = filter the work to this person` (S1f dropped the whole line; the click exists now, the drag half does not). `Open in WO Maintenance` renders `disabled` with `title="arrives with the WO module (OD-5)"` on the card and in the dialog. Write affordances are absent. The actor label renders `actor #<id>` (the envelope carries an `int`; identity is OD-2).

## 3. Environment facts this slice depends on (pasted 2026-09-13 unless marked)

| Thing | Value |
|-------|-------|
| repo | HEAD `81089ce`, `git status` clean; `s1f-grid-1.0.1` at `8f742b4` |
| the box | `max server memory` **8192** in use (`sqlcmd -E -C`, 2026-09-13); `.wslconfig` `[wsl2] memory=8GB swap=2GB` written, `wsl --shutdown` run; Docker Desktop not running. Step 1 re-checks memory before the smoke |
| generated client | `src/api/client/@tanstack/react-query.gen.ts` lines 78/82: `queryFn: async ({ queryKey, signal }) => … signal,` — the OD-30 basis |
| `src/router.tsx` | `Test-Path` True; never imported by `main.tsx` (S1f §3) — deleted in step 2 |
| harness | `vitest.config.ts`: jsdom, **no `setupFiles`, no `globals`** — every component test calls `cleanup()` in `afterEach`, asserts on `className` / `style` / `textContent`, no jest-dom (Landmines §C) |
| `planner.css` 1.0.1 | carries `.pri` + `.pri.A–D` (103–105) and the rail block incl. `.wk.on` (verify in step 1 — oracle 328); does **not** carry filters, wsel/menu, dlg/ovl, selc/kv/badge/lab (header line 13) |
| `rules.ts` 1.0.1 exports | `visibleWos(wos, cats)`, `capacityWorkers(workers)`, `railRows(workers, load, opts)`, `rowTitle`, `chipTitle`, `fmtLong`, `fmtH`, `fmtNum`, `countText`, `indexWorkers`, `byDay` … (read 2026-09-13) |
| `store.ts` 1.0.0 | `cats`, `selected`, `railOpen`, `contractors`, `loadedOnly` + toggles; `select(id)` toggles |
| `DayCell` 1.0.0 | head already renders `<span class="d" data-day={dateIso}>` (line 88) — the dialog's click target exists; no handler yet |
| `PlannerView` 1.0.0 | composes Header / Grid / WorkerPanel; `visibleWos(data.wos, store.cats)`; banner; foot. Exports `validateSearch`, `PlannerView`, `VERSION` |
| deps | unchanged from S1f §3; **nothing added** |

## 4. Build order

Nine steps. Step 1 is pasted before any S1g file is dropped — Ways of Working §5, and §6's "the box first".

1. **The box, then the baseline.** `Get-Process` top-5 by working set + free memory; `sqlcmd -E -C` readback of `max server memory`; Docker not running. Then `uv run pytest -q | Select-Object -Last 6` (expect 125), `pnpm test` (expect 96 in 8 files), `pnpm lint` silent. Read-before-import: `Select-String types.gen.ts -Pattern "^export type (Team|Priority|Labour|Wo|Worker|RangeData)"` pasted — the exact generated names for `teams[]`, `priorities[]`, `labour[]`; and `Select-String planner.css -Pattern "wk\.on"`.
2. **Delete `router.tsx`**, then `pnpm lint ; pnpm test ; pnpm build` on the otherwise-S1f tree — green and building **before** any new file exists, so the delete is proved harmless on its own.
3. **`rules.ts` 1.1.0 + `rules.test.ts` 1.1.0** (§5.1). Zero network, zero DOM, zero `Date`. The 32 existing cases must still pass unchanged — the new parameters default to "no filter".
4. **`store.ts` 1.1.0, `planner.css` 1.1.0, `range.fixture.ts` 1.1.0** (§5.2–§5.4).
5. **The three new components with their tests** (§5.5–§5.7, §6): `FiltersRow`, `SelectedWOCard`, `DayDialog`.
6. **The four patched components** (§5.8–§5.11): `WOCard` 1.0.1, `DayCell` 1.0.1, `PlannerGrid` 1.0.1, `WorkerPanel` 1.1.0, with their tests re-issued at the same bump.
7. **`PlannerView` 1.1.0 + test 1.1.0** (§5.12, §6) — composition, keyboard, the cancellation case.
8. `pnpm lint ; pnpm test ; pnpm dev` and the browser smoke with screenshots (§8); `pnpm build`, the backend re-run (§7).
9. Commit + tag.

## 5. Source files

### 5.1 `web/src/features/planner/rules.ts` 1.1.0 — filters, capacity precedence, card and dialog rows, priority rank

No `Date`, no DOM, no fetch. 1.0.1's exports unchanged in behaviour; `visibleWos`, `capacityWorkers` and `railRows` gain an optional trailing parameter that defaults to "no filter", so every 1.0.1 call site and test stands.

| Export | Oracle | Notes |
|---|---|---|
| `Filters` type, `DEFAULT_FILTERS` | 1533–1537 | `{ teamId: number; workers: Record<number, boolean>; pri: number; unassigned: boolean; q: string }`; defaults `0 / {} / 0 / false / ''` |
| `anySelectedWorker(f)` | 540 | any `true` in `f.workers` |
| `visibleWos(wos, cats, filters = DEFAULT_FILTERS)` | 541–557 | cats → `pri` (`priId !== pri` hides) → `unassigned` (hides any with `assigned.length`) → selected workers (keep if any `assigned[i]` is selected) → `q` lower-cased against `sid title asset assetTitle loc locTitle` joined with spaces — exactly that order, `indexOf < 0` hides |
| `capacityWorkers(workers, filters = DEFAULT_FILTERS)` | 561–567 | **selected workers > team > internal** — the two missing precedence branches (log §8.22) |
| `railRows(workers, load, opts, teamId = 0)` | 778 + OD-26 | team filter first (`teamId && w.teamId !== teamId` → skip, not counted), then OD-26 as today. The count line's `internal` / `contractors` totals count the **team-filtered** population, so `12 of 12 internal` reads right under a team |
| `rowTitle(...)` | 790 | 1.0.1's text + `\nclick = filter the work to this person` (OD-34) |
| `teamOptions(teams)` | 841–842 | `{ value: id, label: (short \|\| name) + (internal ? '' : ' (contractor)') + ' \u00b7 ' + users }`, preceded by `{0, 'All teams'}` in the component |
| `priorityOptions(priorities)` | 844–845 | `{ value: id, label: short + ' \u00b7 ' + title }`, preceded by `{0, 'Any'}` |
| `workerMenu(workers, teamId)` | 848–851 | copy, sort internal first then `(team + name).localeCompare`, filter by team, group by `team` (`'other'` when empty, `' \u00b7 contractor'` suffix on a contractor group); rows `{ id, name, cap: fmtNum(hrsPerWeek) + '/wk' }` |
| `workerLabel(f, byId)` | 402 | `'any'` when none selected; one name; `'n selected'` beyond one — the oracle sets `#wlbl` elsewhere (not read: kept minimal and pinned by test as ours) |
| `priRank(wo, priorities)`, `priClass(rank)` | OD-32 | 1-based index of `priId`; `'r1'`…`'r4'`, `''` otherwise |
| `dialogTitle(key)` | 717 | `fmtLong(key).toUpperCase()` — `fmtLong` already takes ISO |
| `dialogRows(list, labour, byId)` | 719–727 | per WO: `sid`, `cat`, `pri`, `meta1 = statusTitle + (startTime ? ' \u00b7 ' + startTime : '') + (end && end !== start ? ' \u2192 ' + end : '') + (pinned ? ' \u00b7 pinned' : locked ? ' \u00b7 engine owned' : '')`, `title`, `meta2 = asset line or 'no asset'` + `loc`, `meta3 = hours (src) or 'no hours yet'` + `people.join(', ')` / `'owner ' + resp.name` / `'nobody planned'`; `people = labour rows for the WO → name + ' ' + fmtH(hours)`, `#id` when unknown |
| `cardRows(wo, labour, byId)` | 804–819 | `status = statusTitle + (pinned ? ' \u00b7 pinned' : engineOwned ? ' \u00b7 engine owned' : '') + (hasPO ? ' \u00b7 PO linked' : '')`; `pin` line only when pinned (`since pinnedOn` + `engine date`); `start = fmtLong(start) + (startTime ? ' ' + startTime : '')`; `end` only when `end` (`fmtLong(end)` + `(n days)` with `days + 1` when `days > 0`); `priority = pri \|\| '\u2014'`; `asset` / `location` only when set (`code \u00b7 title`, `title` attr = the long title); `hours = fmtH(hrs) + ' (src)'` or `'no estimate yet'`; `responsible = name + ' (WO owner - not planned hours)'` or `'nobody'`; `labour[]` rows `{ name, skillTitle, hours: fmtH, date }` |
| `HINT`, `actorLabel(actor)` | OD-34 | the hint string above; `'actor #' + actor` |

`fmtLong` is parity surface (`Mon 14 Sep 2026`, 1.1.0 §4.1) — `dialogTitle` uppercases it: `MON 14 SEP 2026`.

### 5.2 `web/src/features/planner/store.ts` 1.1.0

1.0.0 plus: `filters: Filters` (+ `setTeam(id)` which also clears `workers` — oracle 1533; `toggleWorker(id)`; `setPri(id)`; `setUnassigned(b)`; `setQ(s)`), `clearFilters()` = oracle 1537 exactly: filters to defaults, `cats` to `DEFAULT_CATS`, `selected` 0. `dayOpen: string` (`''` = closed) + `openDay(key)`, `closeDay()`. `select(id)` unchanged (toggling); new `clearSelect()` sets `selected` 0 without toggling (the grid-background click and `Esc` call it). Nothing persisted.

### 5.3 `web/src/features/planner/planner.css` 1.1.0

1.0.1 plus, scoped and ASCII: oracle 138–148 (`.filters`, `.filters label/.hint/.who`, `.wsel`, `.wsel .menu`, `.wsel.open .menu`, menu `label/.grp/.cap`), 194 (`.dlg.wide`), 267–272 (`.dd2 .row/.job/.sid/.meta/.acts`), 336–347 (`.selc`, `.selc .empty/.t/.actions`, `.kv`, `.kv .k`, `.badge` + the four cats, `.lab`), 361–369 (`.ovl`, `.ovl.on`, `.dlg`, `.dlg h2`, `.dlg .btns`). New: `.chip .pri.r1{background:var(--red);color:#fff} .r2{background:var(--gold2)} .r3{background:#8fa3b5} .r4{background:#6f7c87;color:#fff}` under a comment naming OD-32. `.lab .x` (188–189) **not** ported — no remove control. Header line 13 rewritten to list what is now ported and what still is not (drag/drop states, popover, toast, suggest, ai).

### 5.4 `web/src/features/planner/range.fixture.ts` 1.1.0

1.0.0 plus what the new surfaces read: `teams` (one internal `{id 1, short 'MECH', name, internal true, users 2}`, one contractor `{id 2, short 'CTR', …}`); `priorities` in the RST shape `P1 Urgent … P4 Low, N/A` with the fixture's WOs re-pointed at them (`priId 1 / pri 'P1'` on the WO, `priId 5 / pri 'N/A'` on the REQ) — OD-32's `r1` and `''`; `labour[]` rows carrying `userId`, `hours`, `skillTitle`, `date` for the WO (two people); `resp` on the PM pointing at the 40 h worker; `hasPO true` on the WO; `teamId` on every worker matching the teams; `end`/`days` on the WO spanning two days. Counts stay 2 WO / 2 PM (1.1.0 §4.2).

### 5.5 `FiltersRow.tsx` 1.0.0

Props `{ teams, priorities, workers, byId, filters, actor, onTeam, onToggleWorker, onPri, onUnassigned, onQ, onClear }`. Renders oracle 399–412 minus nothing but the hint text: `div.filters` > `label` Team `select` (`teamOptions`), `div.wsel[.open]` > `button` `Worker: <span.who>{workerLabel}</span> \u25BE` + `div.menu` (`workerMenu` groups → `div.grp`, rows → `label > input[type=checkbox] name <span.cap>`), `label` Priority `select`, `label > input[type=checkbox]` Unassigned only, `input#q` placeholder `Search WO / title / asset / location`, `button` Clear, `span.hint` = `HINT`, `span.sp`, `span.hint` = `actorLabel`. Menu open/closed is **local** state: the button toggles it, a document `click` outside `.wsel` closes it (oracle 1538 + its document handler), `Escape` inside the row closes it and stops propagation (so the global handler does not also clear the selection). Search: local input state, 150 ms `setTimeout` before `onQ(v.trim())` (oracle 1536), cleared on unmount. Keydown inside inputs/selects does not reach the global handler (§5.12 checks the target tag, as the oracle does at 1590).

### 5.6 `SelectedWOCard.tsx` 1.0.0

Props `{ wo: Wo | null, labour, byId, onClear }`. `div.selc`. Empty: `h3 SELECTED WO` + `div.empty` `Click a work order.` (803). With a WO, oracle 807–827 read-only: `h3 SELECTED WO <span.badge.<cat>>cat</span>` (no orb), `div.t` `sid \u00b7 title`, `div.kv` of `span.k`/`span.v` pairs from `cardRows` — Status · Pin (when pinned) · Start · End (when set) · Priority · Asset (when set) · Location (when set) · Hours · Responsible — then the `PLANNED LABOUR` heading (no `+ person`), `.lab` rows (`name <small>skill</small>` / `hours \u00b7 date`, no `×`) or `div.empty` `nobody planned yet` (no drag hint), then `div.actions` > `button.gold` Open in WO Maintenance **disabled** with the OD-5 title, `button` Clear → `onClear`. No Unpin. `data-wo` on the root for the test.

### 5.7 `DayDialog.tsx` 1.0.0

Props `{ dateIso: string, list: Wo[] (already visible-filtered for that day), labour, byId, onSelect, onClose }`. Renders nothing when `dateIso` is `''`. Otherwise oracle 715–731 read-only: `div.ovl.on > div.dlg.wide.dd2` > `h2` `dialogTitle` + `<span>` `countText(list) || 'nothing scheduled'`, `div.none` `Nothing scheduled that day (with the current filters).` when empty, else one `div.job` per `dialogRows` entry: `div > span.sid.<cat> sid` + `span.pri` (with `priClass`) + `div.meta` meta1 · `div > title + div.meta meta2 + div.meta meta3` · `div.acts > button Select` (closes, `onSelect(id)`) + `button.gold Open` **disabled** (OD-5). No Plan hours. `div.btns > button Close`. Escape is handled by §5.12 (the dialog is store state, so the global handler can see it).

### 5.8 `WOCard.tsx` 1.0.1

Prop `priRank?: number` (default 0). The badge's class becomes `pri ${wo.pri} ${priClass(priRank)}`.trim() — the letter class stays for KT, the rank class lights RST (OD-32). Nothing else changes; `title` is still `chipTitle(wo)` (OD-33).

### 5.9 `DayCell.tsx` 1.0.1

Two handlers: the head `<span.d data-day>` gets `onClick` → `onOpenDay(dateIso)` (oracle 1566–1567, `stopPropagation`); the cell root and its `.list` get `onClick` → `onClearSelect()` when the click target *is* the cell or the list (oracle 1568: `ev.target === grid || classList.contains('cell') || contains('list')`) — a click on a chip is already stopped by `WOCard`. `priorities` prop passed through to `WOCard` as `priRank`.

### 5.10 `PlannerGrid.tsx` 1.0.1

Props gain `priorities`, `onOpenDay`, `onClearSelect`; `capacityPerWeek(capacityWorkers(workers, filters))` — new `filters` prop so the strips follow the oracle's precedence (`capWorkers` was internal-only). `priRank` computed once per WO in `byDay`'s consumer, never per cell (Landmines §D): a `Map<priId, rank>` built once from `priorities`.

### 5.11 `WorkerPanel.tsx` 1.1.0

Props gain `teamId`, `selected: Record<number, boolean>`, `onToggleWorker`. `railRows(workers, load, opts, teamId)`. Each row gets `.on` when `selected[w.id]` (oracle 780, CSS 328) and `onClick` → `onToggleWorker(w.id)` (792, minus the `.cap` guard — no capacity edit). `title = rowTitle(...)` with the OD-34 line. The `h3` count and the count line come from the team-filtered `railRows` result.

### 5.12 `PlannerView.tsx` 1.1.0

Composition: `FiltersRow` between the header and the banner (oracle 399 sits there). `wos = visibleWos(data.wos, cats, filters)`; `PlannerGrid` gets `filters`, `priorities`, `onOpenDay = store.openDay`, `onClearSelect = store.clearSelect` (§5.2 — `select(id)` toggles, so a clear needs its own action). The rail column becomes `WorkerPanel` above `SelectedWOCard` (oracle's rail holds `#workers` then `#selc`; CSS 336 `.selc{flex:none;max-height:44%}`). `DayDialog` rendered last with `list = byDay(wos).get(dayOpen) ?? []`. Keyboard: one `useEffect` document `keydown` (oracle 1582–1596 minus drag/undo/R/D/S/A): `Escape` → if `dayOpen` close it, else `clearSelect()`; ignore when `target.tagName` is `INPUT`, `SELECT` or `TEXTAREA`; `ArrowLeft`/`ArrowRight` → `onSearch({ anchor: navAnchor(mode, anchor, ∓1) })`; `t`/`T` → `onSearch({ anchor: todayIso() })`. Listener removed on unmount. `VERSION` 1.1.0.

## 6. Tests (pair rule — zero network, components fed the fixture; `cleanup()` in `afterEach`, no jest-dom)

| File | Cases |
|---|---|
| `rules.test.ts` 1.1.0 | 1.0.1's 32 unchanged, plus: `visibleWos` with `pri` keeps only that `priId` · `unassigned` hides the assigned WO · a selected worker keeps only WOs assigned to them · `q 'stacker'` matches on `assetTitle`, case-insensitive; `q 'zzz'` empties · order of precedence: cats off beats everything · `capacityWorkers` selected > team > internal on the fixture (three cases) · `railRows(..., teamId 1)` drops the contractor team and counts `2 of 2 internal` · `teamOptions` / `priorityOptions` labels byte-for-byte (`MECH \u00b7 2`, `CTR (contractor) \u00b7 1`, `P1 \u00b7 Urgent`) · `workerMenu` groups internal first, contractor group suffixed · `priRank`: `P1` → 1 → `r1`; `N/A` (5th) → 5 → `''`; unknown `priId` → 0 · `dialogTitle('2026-09-14') === 'MON 14 SEP 2026'` · `dialogRows` on the fixture: the WO's people line `Name 3.5h, Name 1h`, the PM's `owner <resp name>`, the REQ's `nobody planned`, the locked PM's `\u00b7 engine owned` · `cardRows` on the WO: `PO linked` in status, `(2 days)` on end, `(labour)` on hours; on the PM: `no estimate yet`, responsible name + ` (WO owner - not planned hours)`; on the REQ: `nobody` · `HINT` and `actorLabel(1) === 'actor #1'` byte-for-byte · `rowTitle` ends with the OD-34 line · `VERSION === '1.1.0'` |
| `FiltersRow.test.tsx` | renders team/priority options from the fixture with `All teams` / `Any` first · changing team calls `onTeam(1)` · the worker button toggles `.wsel.open`; a menu checkbox calls `onToggleWorker(id)`; Escape in the row closes the menu and does not bubble (spy on a document listener) · typing in `#q` calls `onQ` **once** after 150 ms (`vi.useFakeTimers`), trimmed · Unassigned calls `onUnassigned(true)` · Clear calls `onClear` · hint text equals `HINT`; actor text `actor #1` |
| `SelectedWOCard.test.tsx` | `null` → `Click a work order.` · the WO: badge `.badge.WO`, `.t` = `sid \u00b7 title`, `kv` has Status with `PO linked`, Start, End with `(2 days)`, Priority `P1`, Asset, Location, Hours `3.5h (labour)`, Responsible; two `.lab` rows; **no** `.x`, **no** `+ person`, **no** Unpin · the PM: `engine owned` in Status, `no estimate yet`, `nobody planned yet` · Open button `disabled` with the OD-5 title · Clear calls `onClear` |
| `DayDialog.test.tsx` | `dateIso ''` renders nothing · fixture day: `.ovl.on`, `h2` starts `MON 14 SEP 2026` and carries `countText` · one `.job` per WO with `.sid.<cat>`, `.pri.r1` on the P1 · empty list → the `Nothing scheduled…` text · Select calls `onSelect(id)` then `onClose` · Open `disabled` · Close calls `onClose` · **no** Plan hours button |
| `WOCard.test.tsx` 1.0.1 | 1.0.0's 8, plus: `priRank 1` → class contains `r1` and the letter; `priRank 0` → no `r` class; `title` still equals `chipTitle` (OD-33 pin) |
| `PlannerGrid.test.tsx` 1.0.1 | 1.0.0's 11, plus: clicking `[data-day="2026-09-14"]` calls `onOpenDay('2026-09-14')` · clicking a `.cell` (not a chip) calls `onClearSelect`; clicking a chip does not · strip planned/cap follows `filters` (a selected worker changes the cap to that worker's `hrsPerWeek`) · the P1 chip carries `r1` |
| `WorkerPanel.test.tsx` 1.1.0 | 1.0.0's 8, plus: `teamId 1` → the contractor team's rows and counts drop · row click calls `onToggleWorker(id)`; `selected[id]` → `.on` · `title` ends with the OD-34 line |
| `PlannerView.test.tsx` 1.1.0 | 1.0.0's 5, plus: **cancellation (OD-30):** the `fetch` stub returns a never-resolving promise for the first call and captures `input.signal`; rerender with a new `anchor`; expect a second request with the new `from=`/`to=`, and `firstSignal.aborted === true` · `ArrowRight` on `document` calls `onSearch` with `navAnchor(mode, anchor, 1)`; `t` calls it with `todayIso()`; the same keys on a focused `INPUT` do nothing · `Escape` clears the selection; with the dialog open it closes the dialog and keeps the selection · clicking a day head opens `.ovl.on` |

Count from the run, never from this table. The fixture is the only data any test sees; `PlannerView.test.tsx` remains the only file that stubs `fetch`, and the component files stay zero-fetch by import graph.

## 7. What changes on the backend

No backend file is delivered. `pnpm build` rewrites `web/dist`, so the backend suite and the dev-server request set are re-run with the new `dist/` (Ways of Working §6). New this slice to look for in the dev-server terminal: after a burst of nav clicks, `[F] range …` lines keep arriving for windows the browser has already abandoned — that is OD-30's server half, expected; count them against the browser's Network tab (cancelled requests) in the smoke, record, do not fix.

## 8. Smoke (paste verbatim)

Step 1, before any drop:

```powershell
cd C:\dev\workmate-saas
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 5 Name,@{n='GB';e={[math]::Round($_.WorkingSet64/1GB,2)}}
(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
sqlcmd -S localhost -E -C -Q "SELECT CAST(value_in_use AS int) AS max_server_memory_mb FROM sys.configurations WHERE name = 'max server memory (MB)';"
cd backend; uv run pytest -q | Select-Object -Last 6
cd ..\web; pnpm lint; pnpm test
Select-String -Path src\api\client\types.gen.ts -Pattern "^export type (Team|Priority|Labour|Wo|Worker|RangeData)" | Select-Object Line
Select-String -Path src\features\planner\planner.css -Pattern "wk\.on" | Select-Object LineNumber
```

Step 2:

```powershell
cd C:\dev\workmate-saas\web
git rm src\router.tsx
pnpm lint; pnpm test; pnpm build
git status --short
```

Drop the cards (`Unblock-File`; the block lists every expected filename and `Test-Path`s each — Ways of Working §2), then:

```powershell
cd C:\dev\workmate-saas\web
Select-String -Path src\features\planner\*.ts, src\features\planner\*.tsx, src\features\planner\planner.css -Pattern "VERSION|Version:" | Select-Object Filename, Line
pnpm lint
pnpm test
Start-Process powershell -ArgumentList '-NoExit','-Command','cd C:\dev\workmate-saas\backend; uv run fastapi dev app/main.py'
Start-Process powershell -ArgumentList '-NoExit','-Command','cd C:\dev\workmate-saas\web; pnpm dev'
```

Browser on `:3000`, old tabs closed first, **screenshots, not descriptions**:

1. `http://localhost:3000/planner?mode=month&anchor=2026-06-15`, Done on — the filters row; Team = the internal team; the worker menu open with its groups; priority = `P1` (red `r1` badges only); search `stacker`; the totals line and the strips changing with each.
2. Same window — click a rail row: `.wk.on`, the grid narrows to that person, the strip cap becomes their hours; click again clears. Clear resets everything incl. Done off.
3. `?mode=week&anchor=2026-09-16` — click a chip: the card under the rail with Status / Start / End / Priority / Asset / Location / Hours / Responsible / planned labour, Open greyed, Clear. Escape clears it.
4. Same — click the `Mon 14 Sep` head: the day dialog with 106 PMs **scrolling**, `MON 14 SEP 2026` + the count; Select on one; Escape closes.
5. `← → T` with the URL bar visible — anchor moves; the same keys typed into the search box do not.
6. DevTools Network tab: click `›` six times fast on the month view — the earlier `/range` requests show **(canceled)**; the dev-server terminal shows the same count of `[F] range …` lines completing anyway (§7). Both in the shot.

Then the build, the deep link and the backend:

```powershell
cd C:\dev\workmate-saas\web
pnpm build
Get-ChildItem dist\index.html | Select-Object Name, Length, LastWriteTime
curl.exe -i "http://localhost:8000/planner?mode=week&anchor=2026-09-16" -H "Accept: text/html" | Select-Object -First 8
cd ..\backend
uv run ruff format . ; uv run ruff check .
uv run pytest -q | Select-Object -Last 6
```

**Paste the dev-server terminal** for the browser session — the `[F] range` lines are the evidence for §7 and the 60 s poll.

## 9. Acceptance

- Step 1 shows the box healthy (SQL 8192, Docker down, free memory sane) and 125 + 96 green **before** anything is dropped; step 2 proves the `router.tsx` delete alone leaves lint, tests and build green.
- Every filter behaves per oracle 541–557 with the same precedence; the strips' capacity follows 561–567 (selected > team > internal); the rail follows team + OD-26; click-to-filter works both ways.
- The Selected WO card shows the eleven items from the audit list, read-only, with Open disabled (OD-5) and no write affordances (OD-34).
- The day dialog opens from the day head, scrolls a 106-PM day, Select works, Open disabled, Escape closes.
- `← → T` move the anchor; `Esc` clears; none of them fire from a text input.
- `P1` chips render red on RST (OD-32); `chipTitle` unchanged (OD-33) — pinned by test.
- The cancellation test passes and the Network tab shows cancelled requests (OD-30); the server-side completions are counted and recorded, not treated as a defect.
- `pnpm build` writes `dist/`; the deep link still returns the SPA; the backend suite is green with the new `dist/`.
- No new runtime dependency (OD-31). No backend source touched. `router.tsx` gone. No parity claim beyond S1f's.

## 10. Deliverables (one Download card each, on 🤙)

| # | File | Version | Target | PK |
|---|------|---------|--------|-----|
| 1 | `Azztec_SaaS_S1g_Readonly_Chunk_Spec_v1_0_0.md` | 1.0.0 | `docs/` | add |
| 2 | `Azztec_SaaS_web_planner_rules_v1_1_0.ts` | 1.1.0 | `web/src/features/planner/rules.ts` | replaces 1.0.1 |
| 3 | `Azztec_SaaS_web_planner_rules_test_v1_1_0.ts` | 1.1.0 | `…/rules.test.ts` | replaces 1.0.1 |
| 4 | `Azztec_SaaS_web_planner_store_v1_1_0.ts` | 1.1.0 | `…/store.ts` | replaces 1.0.0 |
| 5 | `Azztec_SaaS_web_planner_css_v1_1_0.css` | 1.1.0 | `…/planner.css` | replaces 1.0.1 |
| 6 | `Azztec_SaaS_web_planner_range_fixture_v1_1_0.ts` | 1.1.0 | `…/range.fixture.ts` | replaces 1.0.0 |
| 7 | `Azztec_SaaS_web_planner_FiltersRow_v1_0_0.tsx` | 1.0.0 | `…/FiltersRow.tsx` | add |
| 8 | `Azztec_SaaS_web_planner_FiltersRow_test_v1_0_0.tsx` | 1.0.0 | `…/FiltersRow.test.tsx` | add |
| 9 | `Azztec_SaaS_web_planner_SelectedWOCard_v1_0_0.tsx` | 1.0.0 | `…/SelectedWOCard.tsx` | add |
| 10 | `Azztec_SaaS_web_planner_SelectedWOCard_test_v1_0_0.tsx` | 1.0.0 | `…/SelectedWOCard.test.tsx` | add |
| 11 | `Azztec_SaaS_web_planner_DayDialog_v1_0_0.tsx` | 1.0.0 | `…/DayDialog.tsx` | add |
| 12 | `Azztec_SaaS_web_planner_DayDialog_test_v1_0_0.tsx` | 1.0.0 | `…/DayDialog.test.tsx` | add |
| 13 | `Azztec_SaaS_web_planner_WOCard_v1_0_1.tsx` | 1.0.1 | `…/WOCard.tsx` | replaces 1.0.0 |
| 14 | `Azztec_SaaS_web_planner_WOCard_test_v1_0_1.tsx` | 1.0.1 | `…/WOCard.test.tsx` | replaces 1.0.0 |
| 15 | `Azztec_SaaS_web_planner_DayCell_v1_0_1.tsx` | 1.0.1 | `…/DayCell.tsx` | replaces 1.0.0 |
| 16 | `Azztec_SaaS_web_planner_PlannerGrid_v1_0_1.tsx` | 1.0.1 | `…/PlannerGrid.tsx` | replaces 1.0.0 |
| 17 | `Azztec_SaaS_web_planner_PlannerGrid_test_v1_0_1.tsx` | 1.0.1 | `…/PlannerGrid.test.tsx` | replaces 1.0.0 |
| 18 | `Azztec_SaaS_web_planner_WorkerPanel_v1_1_0.tsx` | 1.1.0 | `…/WorkerPanel.tsx` | replaces 1.0.0 |
| 19 | `Azztec_SaaS_web_planner_WorkerPanel_test_v1_1_0.tsx` | 1.1.0 | `…/WorkerPanel.test.tsx` | replaces 1.0.0 |
| 20 | `Azztec_SaaS_web_planner_PlannerView_v1_1_0.tsx` | 1.1.0 | `…/PlannerView.tsx` | replaces 1.0.0 |
| 21 | `Azztec_SaaS_web_planner_PlannerView_test_v1_1_0.tsx` | 1.1.0 | `…/PlannerView.test.tsx` | replaces 1.0.0 |

Not a card: `git rm src/router.tsx` (step 2). Untouched: `PlannerHeader`, `CapacityBar`, `routes/planner.tsx`, `main.tsx`, `dates.ts`, `usePlannerRange.ts`, every backend file. `DayCell` stays covered by `PlannerGrid.test.tsx`. Every file carries `VERSION` / a header block. Versions are what ship — a mid-slice patch off the smoke bumps the tag.

Tag the version that ships: `s1g-readonly-<shipped>`. Commit message `planner filters + selected card + day dialog + keyboard, router.tsx removed - S1g`. 21 cards, four of them re-issued at a bump: the drop block lists all 20 targets and `Test-Path`s each.

## 11. Doc corrections this slice queues

- **Port Spec 1.0.1 §6/§7:** S1g row → done with tag and date; §7's S1g bullet becomes past tense; §9 gains OD-30…OD-34.
- **Landmines §C:** new entry — TanStack Query aborts a fetch when its query loses its last observer *only if* the queryFn consumed `signal`; the hey-api plugin's generated queryFn does, so nothing extra is needed (verified by the S1g test, date). New entry if step 2 or the dialog surfaces one.
- **Architecture §5:** `router.tsx` line removed; `FiltersRow.tsx`, `SelectedWOCard.tsx`, `DayDialog.tsx` added to the S1g marker; §6 step 5 (cancellation) closes to "aborted in the browser; runs to completion on the server".
- **Index §3.4b / §3.5:** the S1g tables; §6.1 OD-30…OD-34; open items 16, 17 (once Docker starts clean under the cap), 18, 19, 20 close in the raw log.
- Everything queued in log 2026-09-12 1.1.0 §7's "carried, unapplied" list (Install doc, Bootstrap, `.gitignore`, Scaffold_Repo 1.0.2, `.vscode`) unchanged.

## 12. Changelog

- 1.0.0 (2026-09-13) Initial. OD-30…OD-34 signed at the S1g audit gate. Scope cut: shadcn/lucide (OD-31), hover (OD-33 parity), all write affordances and the WO-module handoff (OD-34/OD-5), `initials` (backend), a welcome-page link (unread CLI file), `keepPreviousData` (not a port). Both memory caps applied before this spec was written (§3).
