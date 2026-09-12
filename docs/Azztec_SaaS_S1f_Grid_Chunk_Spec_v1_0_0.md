# Azztec SaaS — S1f Grid Chunk Spec (the read-only PlannerGrid)

**File:** Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-12 · **Author:** Adriaan
**Status:** Draft — awaiting 🤙 before the build
**Slice:** S1f — `windowFor`/nav into `dates.ts` 1.1.0 · pure `features/planner/rules.ts` · `store.ts` · `planner.css` · `WOCard` · `DayCell` · `CapacityBar` + `WeekStrip` · `PlannerGrid` · `PlannerHeader` · `WorkerPanel` · `routes/planner.tsx` · `main.tsx` patched · their Vitest files
**Sits on:** HEAD `3731e53` (clean), tag `s1e-web-1.0.1` at `963fcca` — backend `main.py` 0.3.0 · planner 1.0.1 · suite 125 green; `web/` at S1e (`dates.ts` 1.0.0, `usePlannerRange` 1.0.0, 15 green)
**Parent spec:** `Azztec_SaaS_Planner_Port_Spec_v1_0_0.md` §3 (contract), §7 (UI) · Architecture D-6, D-9, §5, §6 · Ways of Working §3, §4, §6
**Source:** `Azztec_SaaS_Raw_Log_2026-09-12_v1_0_0.md` §9 and its five carry-ins; the S1f audit in chat 2026-09-12 (OD-26…OD-29 signed)
**Oracle:** `Planner_v1_8_1.html` src 482–578 (constants, date utils, `windowFor`, filters, capacity), 585–616 (`chipEl`), 619–713 (header, month, strip, week, twoweek), 771–799 (rail), 871–877 (`nav`), 1460–1483 (`load`); `:root` tokens at 102–107; grid/chip/strip/bar/rail CSS at 151–297, 320–335

---

## 1. Scope

Frontend only. **Nothing writes to the database.** No route changes, no schema changes, no backend source delivered. One backend re-run at the end because `web/dist` changes (§7).

**In:** the window and navigation twins, the pure rendering rules, the store, the ported stylesheet, six components, the `/planner` route with `mode`/`anchor` search params, the `QueryClientProvider` patch to `main.tsx`, and one test file per library/component file (pair rule). The 2,364 engine-owned PMs on RST render as the `locked` state with the oracle's lock glyph and tooltip line — OD-1 working, never an error.

**Out, cut at the audit gate (recorded so nothing is re-proposed):**

| Dropped | Why | Goes to |
|---|---|---|
| Selected-WO card, the `.filters` row (team / worker / priority / unassigned / search), the day dialog (`showDay`) | never in log §9's S1f list; each is its own drawn surface | **S1g**, still read-only |
| `6M` mode | needs the API summary shape — log §8.5, unsigned | button rendered **disabled** with the tooltip "needs an API summary shape (open item 5)" |
| shadcn/ui, lucide-react, `components.json` | nothing S1f draws is a shadcn primitive; installing a library nothing consumes is the lock-file noise S1e refused (log §6). Lock/pin glyphs are the oracle's 9×11 inline SVGs, two tiny components. **Carry-in 5 leaves S1f.** | the first dialog — S1g's day dialog or S2's confirm |
| `@dnd-kit/*`, `/move`, drag | S2 | — |
| `POST /api/v1/_diag/client`, the `?debug=1` console trail, localStorage prefs (`savePrefs`) | backend route does not exist; the trail and prefs are conveniences, not evidence | later |
| `scripts/parity_range.py` | still blocked on the KT dev copy | unchanged |
| TypeScript 7 | **7.0.2 is published** (the native compiler, `pnpm view typescript version` 2026-09-12); the box is on 6.0.3 | its own slice once `@vitejs/plugin-react`, typescript-eslint and hey-api declare support |

## 2. Decisions

### 2.1 Carried in

| ID | Signed | What it means here |
|----|--------|--------------------|
| D-6 | 2026-09-10 | SPA under `app.frontend()`; dev = Vite 5173 proxying `/api` to 8000 |
| D-9 | 2026-09-10 | camelCase JSON keys as the Ignition contract; the UI layer does not rename either |
| OD-1 | 2026-09-10 | no `WO_N_Plan` on RST → engine-owned PMs are `locked: true, movable: false`; the grid draws that state |
| OD-6 | 2026-09-10 | day math on civil dates; `today` for cell highlighting is the API's `today` (server tz), not the browser's |
| OD-23 | 2026-09-11 | `usePlannerRange` unchanged; every window `windowFor` produces is ≤ 42 days — proved by a test over every month 2025–2030 |
| OD-24 | 2026-09-11 | the rail lists internal workers by default |
| OD-25 | 2026-09-11 | `width: min(100, pct)%`, class from `barClass(pct)`, real pct in the label, no placeholder heuristic |

### 2.2 Signed at this gate (2026-09-12)

**OD-26 — rail default.** Rows = `workers` in API order (internal first, then name — Port Spec §3), filtered to `internal` (OD-24). Two client toggles: **contractors** (default off) and **loaded only** (default **on** — `load[id] > 0` in the window). The panel header always carries the count, `46 of 179 internal · 184 contractors hidden`, so the hidden rows are counted, never silent. Basis: 46 of 179 internal have hours on the standing week (log §5.4); S1f is read-only, so the loaded subset is the useful one; S4 (drag-to-plan) revisits the default with the toggle one click away. Second measurement (June) is §4 step 1 — recorded, not gating.

**OD-27 — styling of the port.** The oracle's grid / chip / strip / bar / rail CSS ports as `features/planner/planner.css`: same tokens as `wm-ui.css` (`--gold #FFC65C` …), same class names, ASCII only, every selector scoped under `.wm-planner`. Tailwind and shadcn adoption is decided at the first component that is **not** a port. The screenshot smoke can be held next to the live Ignition planner.

**OD-28 — pins.** TypeScript **6.x** is the pin (box 6.0.3; compiles clean; it is what the CLI and typescript-eslint resolved). Architecture §3.2/§8 corrected from 5.9. ESLint **10**: `@tanstack/eslint-config@0.4.0` peers `^9.0.0 || ^10.0.0` (pasted 2026-09-12), 10.10.0 published — bumped in §4 step 2, before the first `.tsx`, and the existing 15 tests + lint must stay clean on the bump alone. Fallback if `pnpm add` prints peer warnings naming typescript-eslint or an eslint plugin: stay on 9, revert the two files, record it.

**OD-29 — URL state.** `/planner` search params: `mode` (`week | twoweek | month`, default `month`) and `anchor` (yyyy-MM-dd, default today), validated by a plain `validateSearch` on `parseIso` — no zod adapter. The window derives from them via `windowFor`; `from`/`to` never appear in the URL, so a link can only name a window the mode can draw. Cats, selection, rail open/closed and the two rail toggles live in the Zustand store and are not persisted.

## 3. Environment facts this slice depends on (pasted 2026-09-12)

| Thing | Value |
|-------|-------|
| repo | HEAD `3731e53`, `git status` clean, `s1e-web-1.0.1-1-g3731e53` |
| deps | react 19.3.0 · router 1.170.35 · query 5.102.8 · vite 8.3.0 · tailwindcss 4.3.3 + `@tailwindcss/vite` (no duplicate postcss) · zustand 5.0.15 · zod 4.6.1 · date-fns 4.4.0 · vitest 5.0.0 · jsdom 30.0.1 · RTL 16.3.3 · `@tanstack/router-cli` 1.167.35 · `@tanstack/router-plugin` 1.168.37 · typescript 6.0.3 · eslint 9.39.5 · prettier 3.9.6 |
| `tsconfig.json` | `paths` `@/*` and `#/*` → `./src/*`; `strict`, `noUnusedLocals`, `noUnusedParameters`, `verbatimModuleSyntax`, `allowImportingTsExtensions` |
| `vite.config.ts` | `resolve.tsconfigPaths: true`; plugins devtools · tailwindcss · `tanstackRouter({ target: 'react', autoCodeSplitting: true })` · viteReact; the S1e proxy |
| `src/main.tsx` | CLI-written; builds its own `createRouter({ routeTree, defaultPreload: 'intent', scrollRestoration: true })` and renders `<RouterProvider>` into `#app`. **No `QueryClientProvider`** — S1e's tests brought their own. This is the file that gets patched |
| `src/router.tsx` | CLI-written `getRouter()`; **not imported by `main.tsx`** — dead file, left alone, logged |
| `src/routes/__root.tsx` | imports `../styles.css`, renders `<Outlet/>` + `TanStackDevtools` with the Router panel. Untouched |
| `src/styles.css` | `@import "tailwindcss"` + box-sizing/min-height resets. Untouched; `planner.css` is imported by the route |
| `src/routes/index.tsx` | the CTA welcome page. Untouched in S1f (a link to `/planner` is S1g chrome) |
| imports | S1e files use relative paths (`../../api/client/...`); S1f does the same — one style in the tree |

Nothing in `web/` is deleted or regenerated except `src/routeTree.gen.ts`, which the router plugin regenerates when the new route file appears.

## 4. Build order

Ten steps. Steps 1 and 2 are pasted before any S1f file is dropped — Ways of Working §5.

1. **Baseline + measurements.** `uv run pytest -q` (expect 125, counted from the run), boot `fastapi dev app/main.py`, then the OD-26 June count, the June `cat` histogram (expect 12/42/604), RST's priority letters, the top-five `workerWeeks` by `pct` on the standing window (names the row the screenshot shows), and `^export` from `src/api/client/index.ts` (the read-before-import check).
2. **ESLint 10** (OD-28): `pnpm add -D eslint@^10`, then `pnpm lint ; pnpm test` on the S1e tree — 15 green, lint silent, before any new file exists. Fallback in §2.2.
3. **`dates.ts` 1.1.0 + `dates.test.ts` 1.1.0** (§5.1). Zero network, zero DOM.
4. **`rules.ts` + `rules.test.ts`** (§5.2). Zero network, zero DOM, zero `Date`.
5. **`store.ts` + `planner.css`** (§5.3, §5.4).
6. **`range.fixture.ts`** (§6.0), then the components with their tests (§5.5–§5.9, §6).
7. **`routes/planner.tsx` + `main.tsx` 1.0.0** (§5.10, §5.11). `pnpm exec tsr generate` and `Select-String routeTree.gen.ts -Pattern planner` — verify the CLI flag on the box; if `tsr` is not on the path the router plugin regenerates on the first `pnpm dev`/`pnpm test`, and that is recorded instead.
8. **`pnpm lint ; pnpm test ; pnpm dev`** and the browser smoke with screenshots (§8).
9. **`pnpm build`**, the deep link through `app.frontend()`, the backend re-run (§7).
10. Commit + tag.

## 5. Source files

### 5.1 `web/src/lib/dates.ts` 1.1.0 — window and navigation twins

Still the only module in `web/` that touches `Date`. 1.0.0's exports unchanged. Added:

```ts
export type Mode = 'week' | 'twoweek' | 'month';
export const MODES: readonly Mode[] = ['week', 'twoweek', 'month'];
export type Window = { from: string; to: string; days: number };   // ISO strings, inclusive
export function windowFor(mode: Mode, anchor: string): Window
export function navAnchor(mode: Mode, anchor: string, n: number): string
export function todayIso(): string
export function dowOf(d: string): number          // 0 = Monday … 6 = Sunday
export function daysInMonthOf(d: string): number
```

`windowFor` ports oracle 519–532 minus the six-month branch: week = `weekStart(anchor)` + 6; twoweek = + 13; month = `from = weekStart(first of month)`, `rows = ceil((dowOf(first) + daysInMonth) / 7)`, `to = from + rows*7 - 1`. `navAnchor` ports 871–876: week ±7n days, twoweek ±14n, month → the **first** of the month ±n months (the oracle's `addMonths` lands on the 1st; kept). `todayIso()` is the browser's civil day and is used **only** for the default `anchor` (OD-29); cell highlighting uses the API's `today` (OD-6). Six-month mode is not ported (§1).

### 5.2 `web/src/features/planner/rules.ts` 1.0.0 — the pure rendering rules

No `Date`, no DOM, no fetch. Types imported from the generated client (`Wo`, `Worker`, `WeekLoad`, `WorkerWeek`, `RangeData` — the exact names confirmed by step 1's `^export` paste). Ports, with oracle line numbers:

| Export | Oracle | Notes |
|---|---|---|
| `CAT_ORDER`, `DOW`, `MON`, `MONL`, `Cat`, `Cats`, `DEFAULT_CATS` | 482–485, 492 | `DEFAULT_CATS = {WO, PM, REQ: true, DONE: false}` — the oracle's default; DONE off |
| `visibleWos(wos, cats)` | 541–557 | cats only in S1f; pri / unassigned / worker / search arrive with the S1g filters |
| `byDay(wos): Map<string, Wo[]>` | 558 | keyed by `start` |
| `capacityWorkers(workers)` | 561–567 | internal only in S1f; the selected-worker > team precedence arrives with S1g |
| `capacityPerWeek(workers)` | 568 | `Math.round(c*100)/100` kept |
| `weekStats(weekStart, weekEnd, wos)` | 569–577 | ISO string comparison; both bounds passed in so no `addDays` here |
| `pctOf(planned, capacity)` | 669, 779 | `capacity > 0 ? Math.round(100*planned/capacity) : 0` |
| `barClass(pct)` | 578 | `'over' \| 'ok' \| ''` |
| `countText(list)`, `fmtH(h)`, `fmtNum(h)` | 662–667, 515–516 | byte-for-byte strings |
| `whoFor(wo, byId)` | 590–594 | ≤ 3 initials + `+n`; `#id` when unknown |
| `chipTitle(wo)` | 600–606 | the tooltip, including the OD-1 line `PM - engine owned; run the S3 DDL (WO_N_Plan) to allow planner pins` |
| `stripTitle(...)`, `weekBarTitle(wk)`, `rowTitle(...)` | 674, 785, 790 | rail row title drops the trailing `click = filter … drag …` line (S1g / S4) |
| `weeksIn(days)` | 775 | `Math.max(1, days / 7)` — civil days, **not** `ms / 864e5` |
| `railRows(workers, load, {contractors, loadedOnly})` | 777–778 + OD-26 | returns `{ rows, internal, contractors, loaded }` for the count line |
| `fmtRange(from, to)`, `monthLabel(anchor)` | 510–513, 623 | string slicing on ISO; no `Date` |

### 5.3 `web/src/features/planner/store.ts` 1.0.0

Zustand, not persisted: `cats` (+ `toggleCat`, `setAllCats`), `selected: number` (+ `select(id)` toggling like oracle 869), `railOpen` (+ `toggleRail`), `contractors: false`, `loadedOnly: true` (+ toggles). Nothing else.

### 5.4 `web/src/features/planner/planner.css` 1.0.0

Oracle 102–107 tokens, 108–121 base, 122–137 header/seg/cats, 151–169 grid-wrap/dow/grid/cell, 171–172 chip, 273–297 chip parts/strip/bar, 299–301 week `hh`, 215–221 twoweek, 320–335 rail/wk, 349–354 loading/banner, 374–375 foot — all scoped under `.wm-planner`, ASCII, no drag/drop/dialog/ai/suggest rules. Roughly 120 lines.

### 5.5 `WOCard.tsx` 1.0.0

Props `{ wo, who, selected, onSelect }`. Renders oracle 585–599: `div.chip.cat-<cat>[.locked][.mv][.sel]` with `data-wo`, `data-movable`, `title = chipTitle(wo)`; `.pri.<letter>` badge when `pri` non-empty (letters outside A–D fall to the base `.pri` style — RST's letters are confirmed in step 1); `.sid`; `.hrs[.unk]` = `fmtH`; `.who`; then `PinGlyph` if pinned else `LockGlyph` if locked (the two inline SVGs, `aria-label` kept). Click → `onSelect(wo.id)`. No dblclick (`openWO` is OD-5, S1g). No estimate popover (S2).

### 5.6 `DayCell.tsx` 1.0.0

Props `{ dateIso, mode, col (0–6), list, isPast, isToday, out, byId, selected, onSelect }`. Renders oracle 643–655 (month) and 684–691 / 703–711 (week / twoweek): `div.cell[.past][.today][.out][.x]` with `data-date`; header `.ch` — month: `<span.d data-day>` day number + ` MON` when day is 1 or first cell, `<span.c>` = `countText`; week/twoweek: `DOW[col] d MON`, `.c`, and the `.hh` line `N h planned · n without hours`. Month caps the list at 4 with `.more` (`+n more` / `show less`) on a local `useState` — the oracle's global `S.expanded` becomes per-cell state.

### 5.7 `CapacityBar.tsx` 1.0.0 (also exports `WeekStrip`)

`CapacityBar({ pct })` → `div.bar > i.<barClass(pct)>` with `style={{ width: \`${Math.min(100, pct)}%\` }}` — OD-25, the exact oracle string. `WeekStrip({ weekStart, weekEnd, wos, cap, capWorkers })` → oracle 668–676: `.n` planned `/ cap h`, the bar, `.u` `+n WO no hrs` or `.w` `n WO · pct%`, `title = stripTitle(...)`. The label carries the real pct, whatever it is.

### 5.8 `PlannerGrid.tsx` 1.0.0

Props `{ mode, window, wos (already visible-filtered), today, anchorMonth ('yyyy-MM'), workers, byId, selected, onSelect }`. `byDay` and `capacityPerWeek` memoised once per render (Landmines §D — never per cell). Week: `div.grid.week`, 7 `DayCell`s, no strip (oracle 678–693). Twoweek / month: `.dow` header row (7 DOW + `HOURS / WEEK`), then per week 7 `DayCell`s + one `WeekStrip` (699–713, 638–660). Month marks `out` cells by `dateIso.slice(0,7) !== anchorMonth`, `past` by `dateIso < today`, `today` by equality — string comparisons on ISO.

### 5.9 `PlannerHeader.tsx` 1.0.0

Props for mode / nav / cats / counts / rail. Oracle 381–398 minus Suggest and the AI orb: `PLANNER`, `.range` label (`fmtRange` for week/twoweek, `monthLabel` for month), `.seg` Week / 2W / Month + **6M disabled** with the §1 tooltip, `‹ Today ›`, cats `All WO PM REQ Done` with `.on` from the store, `.totals` `c.wo WO | c.pm PM | c.done done`, the rail `☰` button. Keyboard `← → T` are S1g.

### 5.10 `WorkerPanel.tsx` 1.0.0

Props `{ workers, load, workerWeeks, days, contractors, loadedOnly, onToggleContractors, onToggleLoadedOnly }`. `h3` `WORKERS` + the OD-26 count line + the two toggles. Rows from `railRows(...)`, each per oracle 780–789: `.wk[.contr]` with `data-worker`; `.av` initials; `.nm` name + `<small>` team · first skill; `.wkb` week bars from `workerWeeks[id]` with `i.<flag>` and `weekBarTitle`; `.ld` `<b>ld h</b> · cap/wk`, `CapacityBar(pct)`, `.flags` `n over · n under`. `weeks = weeksIn(days)`, `cap = hrsPerWeek * weeks`, `pct = pctOf(ld, cap)`. No click-to-filter, no capacity edit (S1g / S4). `title = rowTitle(...)`.

### 5.11 `web/src/routes/planner.tsx` 1.0.0

`createFileRoute('/planner')({ validateSearch, component })`. `validateSearch(s)` → `{ mode: MODES.includes(s.mode) ? s.mode : 'month', anchor: isIso(s.anchor) ? s.anchor : todayIso() }` (OD-29). Component: `useSearch`, `useNavigate`; `windowFor(mode, anchor)`; `usePlannerRange(from, to)`; the store; `today = data?.today ?? todayIso()`; `byId = new Map(workers.map(w => [w.id, w]))` memoised on `data`. Layout `div.wm-planner > PlannerHeader, .banner, .body > .grid-wrap(PlannerGrid + .loading) + .rail(WorkerPanel), .foot`. `.loading.on` while no data and fetching; `.banner.on` with `query.error` message or `window.message` when the window is refused; `.foot` = `Planner UI <VERSION> · lib <libVersion> · api <apiVersion> · range <ms> ms · refreshing…` while `isFetching` with data. Nav: `navigate({ search: prev => ({ ...prev, anchor: navAnchor(mode, prev.anchor, n) }) })`; mode change keeps `anchor`. Imports `../features/planner/planner.css`.

### 5.12 `web/src/main.tsx` 1.0.0 — the CLI's file + the provider

Read 2026-09-12 (§3). Unchanged except: `new QueryClient()` at module scope, `<QueryClientProvider client={qc}>` around `<RouterProvider>`, and `<ReactQueryDevtools initialIsOpen={false} />` inside it (already a devDependency from S1e — it shows the 60 s poll firing during the smoke). Delivered as a card with the header block, like `eslint.config.js` was.

## 6. Tests (pair rule — zero network, components fed the fixture)

### 6.0 `range.fixture.ts` (test helper, not a test)

One `RangeData` for `2026-09-14..2026-09-20`, hand-built, contract-shaped (the backend contract test guards the real shape): four WOs — a `WO` (pri `A`, `hrs 3.5 labour`, assigned to two workers), a `PM` (`engineOwned`, `locked`, not `movable`, `hrs 0`), a `REQ` (`hrs 2 estimate`), a `DONE` (`status C`, `locked`) — a pinned WO variant for the glyph test; three workers — internal `hrsPerWeek 1` with `load 10` (the 1000%), internal `hrsPerWeek 40` with `load 0`, one contractor; `workerWeeks` carrying `{planned 10, capacity 1, pct 1000, flag 'over'}`; one `weeks[]` entry consistent with the WOs; `counts`, `colours`, envelope fields.

| File | Cases |
|---|---|
| `dates.test.ts` 1.1.0 | 1.0.0's 7 kept, plus: week window for `2026-09-16` = `2026-09-14..2026-09-20` (7) · twoweek = `..2026-09-27` (14) · **month Sep 2026 = `2026-08-31..2026-10-04` (35, crossing the DST day)** · **month Aug 2026 = `2026-07-27..2026-09-06` = 42** — the OD-23 worst case · every month 2025-01..2030-12 gives `days ≤ 42` and `checkWindow(...).ok` · `navAnchor` month lands on the 1st, week ±7 keeps the weekday · `dowOf('2026-09-14') === 0` · `VERSION === '1.1.0'` |
| `rules.test.ts` | `visibleWos` with `DEFAULT_CATS` hides DONE · `byDay` groups by `start` · `capacityWorkers` internal only · `weekStats` planned/unknown/count on the fixture · `pctOf(74, 0) === 0`, `pctOf(10, 1) === 1000` · `barClass` at 79/80/100/101 · `countText`/`fmtH`/`fmtNum` strings byte-for-byte (`'?'`, `'3.5h'`, `'12h'`) · `whoFor` ≤ 3 + `+n` and `#id` · `chipTitle` on the locked PM contains the OD-1 line · `weeksIn(35) === 5`, `weeksIn(7) === 1` · `railRows` counts on the fixture (loadedOnly → 1 of 2 internal) · `fmtRange` across a year boundary |
| `WOCard.test.tsx` | `cat-PM locked` class set and `data-movable="0"` · `sel` when selected · `unk` hours badge · initials text · lock glyph for locked, pin glyph for pinned, neither otherwise · `title` is `chipTitle` · click calls `onSelect(id)` |
| `CapacityBar.test.tsx` | **pct 1000 → `i.over`, `style.width === '100%'`**; pct 90 → `ok`, `90%`; pct 10 → no class, `10%` — the OD-25 pin · `WeekStrip` on the fixture renders `planned / cap h` and the `+n WO no hrs` branch; capacity 0 renders `? h` |
| `PlannerGrid.test.tsx` | week: 7 cells, the fixture WO is inside `[data-date="<start>"]` · month on `anchor=2026-09-15`: 35 cells + 5 strips, `out` on 31 Aug, `today` on the fixture's `today` · strip planned equals the fixture `weeks[0].planned` with all cats on · month cell with 5 WOs shows 4 + `+1 more`, click shows 5 |
| `WorkerPanel.test.tsx` | default (OD-26): 1 row (the loaded internal), count line `1 of 2 internal · 1 contractors hidden` · `loadedOnly` off → 2 rows · `contractors` on → 3 rows, `.contr` on the contractor · the 1000% row: `.wkb i.over` present, `title` contains `(1000%)` |
| `planner.route.test.tsx` | memory-history router on `/planner?mode=week&anchor=2026-09-16` inside a `QueryClientProvider` with the S1e fetch stub: **one request, URL contains `from=2026-09-14` and `to=2026-09-20`, never `from_`** · `validateSearch({mode:'sixm', anchor:'2026-02-31'})` → `{mode:'month', anchor: todayIso()}` · **Contingency:** if `routeTree.gen.ts` under Vitest does not carry the route or the memory router fights jsdom, the first case reduces to `windowFor` + `plannerQueryOptions(...).queryKey` and the reason is recorded in the raw log — the wire is still pinned by S1e test 6 |

Count from the run, never from this table.

## 7. What changes on the backend

No backend file is delivered. `pnpm build` rewrites `web/dist`, so per Ways of Working §6 the backend suite and the dev-server request set are re-run with the new `dist/`. New this slice: **`GET /planner?mode=week&anchor=2026-09-16` with `Accept: text/html` is the first non-root SPA path ever requested through `app.frontend()`** — expect 200 `index.html` and the grid rendering at `:8000`. Expect **no diag line** for it (middleware scoped to `/api`, Landmines §A, open item 14) — confirm, do not fix. `curl` with `*/*` on the same path: whatever it returns is recorded, not judged.

## 8. Smoke (paste verbatim)

```powershell
cd C:\dev\workmate-saas\web
pnpm add -D eslint@^10
pnpm lint ; pnpm test
```

Drop the cards (`Unblock-File`, then `Length`/`LastWriteTime` on each **target**, wildcard + newest mtime), then:

```powershell
cd C:\dev\workmate-saas\web
Select-String -Path src\lib\dates.ts, src\features\planner\*.ts, src\features\planner\*.tsx, src\routes\planner.tsx, src\main.tsx -Pattern "^export const VERSION"
pnpm exec tsr generate ; Select-String -Path src\routeTree.gen.ts -Pattern "planner"
pnpm lint
pnpm test
pnpm dev
```

Browser (backend up in another terminal — `cd C:\dev\workmate-saas\backend ; uv run fastapi dev app/main.py`), **screenshots, not descriptions**:

1. `http://localhost:5173/planner?mode=month&anchor=2026-06-15` — toggle **Done** on: WO gold, PM cyan, REQ pink, DONE green chips; `+n more` on a busy cell; strips.
2. `http://localhost:5173/planner?mode=week&anchor=2026-09-16` — 273 PM chips with lock glyphs; hover one chip for the OD-1 tooltip line.
3. The rail on 2: the row named by step 1's top-five, showing the full red bar and its tooltip `… (1000%)`; the count line; flip **loaded only** off and screenshot the count line again.
4. `?mode=twoweek&anchor=2026-09-14` — two rows + strips; `6M` visibly disabled; `‹ ›` and Today move the URL.

Then the build and the deep link:

```powershell
cd C:\dev\workmate-saas\web
pnpm build
Get-ChildItem dist\index.html | Select-Object Name, Length, LastWriteTime
curl.exe -i "http://localhost:8000/planner?mode=week&anchor=2026-09-16" -H "Accept: text/html"
curl.exe -i "http://localhost:8000/planner?mode=week&anchor=2026-09-16"
```

Open `http://localhost:8000/planner?mode=week&anchor=2026-09-16` in the browser — screenshot 5. Then the backend:

```powershell
cd C:\dev\workmate-saas\backend
uv run ruff format . ; uv run ruff check .
uv run pytest -q
```

**Paste the dev-server terminal** for the whole browser session — the `[F] range …` lines every 60 s are the poll proving `refetchInterval`, and the absence of any line for `/planner` is open item 14 confirmed.

## 9. Acceptance

- `pnpm lint` silent and `pnpm test` green on ESLint 10 **before** any S1f file lands (OD-28), and again after.
- Every window `windowFor` can produce is ≤ 42 days — proved over 2025–2030, not asserted.
- Week / twoweek / month render from the RST data with the oracle's DOM (`data-date`, `data-wo`, `data-movable`, class names) and the DONE default off.
- The 2,364 locked PMs render as `locked` with the lock glyph and the OD-1 tooltip — no banner, no error.
- The capacity bar at 1000% is a full red bar with `1000%` in its label, **shown in a screenshot** (carry-in 3).
- The rail defaults to loaded internal workers with the count line, and both toggles work (OD-26).
- `/planner?mode=&anchor=` is the only URL state; a bad `anchor` falls back to today, never to a fetch (OD-29).
- `pnpm build` writes `dist/`; the deep link through `app.frontend()` returns the SPA; the backend suite is still green with the new `dist/` (count from the run).
- No new runtime dependency. No backend source touched. No parity claim — Ignition parity still needs the KT copy.

## 10. Deliverables (one Download card each, on 🤙)

| # | File | Version | Target | PK |
|---|------|---------|--------|-----|
| 1 | `Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md` | 1.0.0 | `docs/` | add |
| 2 | `Azztec_SaaS_web_lib_dates_v1_1_0.ts` | 1.1.0 | `web/src/lib/dates.ts` | replaces 1.0.0 |
| 3 | `Azztec_SaaS_web_lib_dates_test_v1_1_0.ts` | 1.1.0 | `web/src/lib/dates.test.ts` | replaces 1.0.0 |
| 4 | `Azztec_SaaS_web_planner_rules_v1_0_0.ts` | 1.0.0 | `web/src/features/planner/rules.ts` | add |
| 5 | `Azztec_SaaS_web_planner_rules_test_v1_0_0.ts` | 1.0.0 | `web/src/features/planner/rules.test.ts` | add |
| 6 | `Azztec_SaaS_web_planner_store_v1_0_0.ts` | 1.0.0 | `web/src/features/planner/store.ts` | add |
| 7 | `Azztec_SaaS_web_planner_css_v1_0_0.css` | 1.0.0 | `web/src/features/planner/planner.css` | add |
| 8 | `Azztec_SaaS_web_planner_range_fixture_v1_0_0.ts` | 1.0.0 | `web/src/features/planner/range.fixture.ts` | add |
| 9 | `Azztec_SaaS_web_planner_WOCard_v1_0_0.tsx` | 1.0.0 | `web/src/features/planner/WOCard.tsx` | add |
| 10 | `Azztec_SaaS_web_planner_WOCard_test_v1_0_0.tsx` | 1.0.0 | `…/WOCard.test.tsx` | add |
| 11 | `Azztec_SaaS_web_planner_DayCell_v1_0_0.tsx` | 1.0.0 | `…/DayCell.tsx` | add |
| 12 | `Azztec_SaaS_web_planner_CapacityBar_v1_0_0.tsx` | 1.0.0 | `…/CapacityBar.tsx` | add |
| 13 | `Azztec_SaaS_web_planner_CapacityBar_test_v1_0_0.tsx` | 1.0.0 | `…/CapacityBar.test.tsx` | add |
| 14 | `Azztec_SaaS_web_planner_PlannerGrid_v1_0_0.tsx` | 1.0.0 | `…/PlannerGrid.tsx` | add |
| 15 | `Azztec_SaaS_web_planner_PlannerGrid_test_v1_0_0.tsx` | 1.0.0 | `…/PlannerGrid.test.tsx` | add |
| 16 | `Azztec_SaaS_web_planner_PlannerHeader_v1_0_0.tsx` | 1.0.0 | `…/PlannerHeader.tsx` | add |
| 17 | `Azztec_SaaS_web_planner_WorkerPanel_v1_0_0.tsx` | 1.0.0 | `…/WorkerPanel.tsx` | add |
| 18 | `Azztec_SaaS_web_planner_WorkerPanel_test_v1_0_0.tsx` | 1.0.0 | `…/WorkerPanel.test.tsx` | add |
| 19 | `Azztec_SaaS_web_routes_planner_v1_0_0.tsx` | 1.0.0 | `web/src/routes/planner.tsx` | add |
| 20 | `Azztec_SaaS_web_routes_planner_test_v1_0_0.tsx` | 1.0.0 | `web/src/routes/planner.route.test.tsx` | add |
| 21 | `Azztec_SaaS_web_main_v1_0_0.tsx` | 1.0.0 | `web/src/main.tsx` | add (CLI file + provider) |

`DayCell` and `PlannerHeader` are covered by `PlannerGrid.test.tsx` and `planner.route.test.tsx` respectively — one drawn surface, one test file each; the pair rule is met per library file, not per leaf. Every TS/TSX/CSS file carries `VERSION` / a header block. `routeTree.gen.ts` and `pnpm-lock.yaml` (ESLint 10) are regenerated on the box and committed, never cards.

Tag the version that ships: `s1f-grid-<shipped>`. Commit message `planner grid read-only + eslint 10 - S1f`. 21 cards is the biggest drop yet — the card-by-card `Length` check is not optional.

## 11. Doc corrections this slice queues

- **Architecture §3.2 / §8:** TypeScript pin 6.x (was 5.9); ESLint 10 (if step 2 lands); note TypeScript 7.0.2 published, not taken. `components.json (shadcn, S1f)` → S1g. §5 layout: `store.ts`, `planner.css`, `range.fixture.ts`, `PlannerHeader.tsx`, `WorkerPanel.tsx` (Port Spec name kept over "rail"); `router.tsx` marked unused.
- **Port Spec §6:** S1 splits S1a–**S1g**; §7 `WorkerPanel` is S1f, `SelectedWOCard` / filters / day dialog S1g.
- **Landmines §C:** new entry — `@tanstack/cli`'s `main.tsx` builds its own router and ignores `router.tsx`; new entry — `routeTree.gen.ts` under Vitest (whichever way step 7 lands); new entry — the first deep-linked SPA path through `app.frontend()` (§7's outcome).
- **Index §3.4b / §3.5:** the S1f tables; §5 eslint / typescript rows.
- Everything queued in log 2026-09-12 §7 unchanged and unapplied.

## 12. Changelog

- 1.0.0 (2026-09-12) Initial. OD-26…OD-29 signed at the S1f audit gate. Scope cut: selected-WO card, filters row, day dialog → S1g; shadcn/ui and lucide-react deferred to the first dialog; 6M disabled; TypeScript 7 noted and not taken. ESLint 10 bump folded in as step 2 on the pasted peer range.
