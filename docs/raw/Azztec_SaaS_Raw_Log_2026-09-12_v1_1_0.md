# Azztec SaaS — Raw Log 2026-09-12 (S1f)

**File:** Azztec_SaaS_Raw_Log_2026-09-12_v1_1_0.md · **Version:** 1.1.0 · **Date:** 2026-09-12 · **Author:** Adriaan
**Supersedes:** `Azztec_SaaS_Raw_Log_2026-09-12_v1_0_0.md` §7, §8 and §9 (its §1–§6, the S1e record, stand and are not repeated here)
**Session:** 2026-09-12 afternoon → evening. S1f audit → four decisions signed → spec → three drops → two fix cards → smoke on real RST data → a four-hour detour into a box-level memory incident → build → deep link → backend re-run → commit + tag.
**Status:** append-only ground truth. Corrections go in a later dated log, not by editing this one.
**Goes to:** `docs/raw/` in the repo AND project knowledge.

---

## 1. Decisions signed this session

All four at the S1f audit gate, 2026-09-12, before the spec was written.

| ID | Decision | Why |
|----|----------|-----|
| **OD-26** | Workers rail: rows = `workers` in API order, filtered to `internal` (OD-24). Two client toggles, **contractors** (default off) and **loaded only** (default **on**, `load[id] > 0` in the window). The panel header always carries the count line (`46 of 179 internal · 184 contractors hidden`) so hidden rows are counted, never silent. | Measured on two windows: standing week 46 of 179 internal loaded; June variety week **72 of 179** (§5.2). Either way loaded-only cuts the rail by 60 %+. S1f is read-only so the loaded subset is the useful one; S4 (drag-to-plan) revisits the default with the toggle one click away. |
| **OD-27** | Styling of the port: the oracle's grid / chip / strip / bar / rail CSS ports as `features/planner/planner.css` — same tokens as `wm-ui.css`, same class names, ASCII, scoped under `.wm-planner`. Tailwind and shadcn adoption is decided at the first component that is **not** a port. | Behaviour parity with a screenshot that can be held next to the Ignition planner (§5.7 did exactly that). No theme-mapping exercise inside a slice whose job is to draw the data. |
| **OD-28** | Pins: TypeScript **6.x** stays (box 6.0.3, compiles clean, what the CLI and typescript-eslint resolved). ESLint **10** — `@tanstack/eslint-config@0.4.0` peers `^9.0.0 \|\| ^10.0.0`, 10.10.0 published, bumped before the first `.tsx`, lint silent before and after. **TypeScript 7.0.2 is published** (the native compiler) and deliberately not taken. | Settled as a choice, not a scaffold accident (1.0.0 §8.16 closed). |
| **OD-29** | URL state: `/planner` search params are `mode` (`week \| twoweek \| month`, default `month`) and `anchor` (yyyy-MM-dd, default today), validated by a plain `validateSearch` on `parseIso` — no zod adapter. `from`/`to` never appear in the URL; `windowFor` derives them. Cats, selection, rail open/closed and the two rail toggles live in the Zustand store, not persisted. | A link can only name a window the mode can draw, which is what keeps every request inside OD-23. |

**Scope cut at the audit gate**, recorded so nothing is re-proposed: the **selected-WO card**, the **filters row** (team / worker / priority / unassigned / search) and the **day dialog** → **S1g** (still read-only); **6M** rendered disabled with a tooltip, not hidden; **shadcn/ui and lucide-react not installed** — nothing S1f draws is a shadcn primitive, and the lock/pin glyphs are the oracle's two inline SVGs; `@dnd-kit`, `/move`, `/_diag/client`, the `?debug=1` trail and localStorage prefs → later; `parity_range.py` still blocked on the KT copy.

OD-1, OD-6…OD-25 unchanged. Don't re-litigate.

## 2. Shipped and tagged

Twenty-two cards over three drops plus two fix cards. **Versions are what shipped, not what spec §10 predicted** (§4.12).

| File | Version | Path |
|------|---------|------|
| `Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md` | 1.0.0 | `docs/` |
| `Azztec_SaaS_web_lib_dates_v1_1_0.ts` | **1.1.0** | `web/src/lib/dates.ts` — `Mode`/`MODES`/`isMode`, `Window`/`windowFor`, `navAnchor`, `todayIso`, `dowOf`, `daysInMonthOf`, `monthStart`, `isIso` |
| `Azztec_SaaS_web_lib_dates_test_v1_1_0.ts` | 1.1.0 | `web/src/lib/dates.test.ts` |
| `Azztec_SaaS_web_planner_rules_v1_0_1.ts` | **1.0.1** | `web/src/features/planner/rules.ts` (1.0.1 = one doc comment, §4.1) |
| `Azztec_SaaS_web_planner_rules_test_v1_0_1.ts` | 1.0.1 | `…/rules.test.ts` |
| `Azztec_SaaS_web_planner_range_fixture_v1_0_0.ts` | 1.0.0 | `…/range.fixture.ts` |
| `Azztec_SaaS_web_planner_store_v1_0_0.ts` | 1.0.0 | `…/store.ts` |
| `Azztec_SaaS_web_planner_css_v1_0_1.css` | **1.0.1** | `…/planner.css` (1.0.1 = `.chip{flex:none}`, §4.3) |
| `Azztec_SaaS_web_planner_WOCard_v1_0_0.tsx` (+ test) | 1.0.0 | `…/WOCard.tsx`, `…/WOCard.test.tsx` |
| `Azztec_SaaS_web_planner_DayCell_v1_0_0.tsx` | 1.0.0 | `…/DayCell.tsx` (covered by `PlannerGrid.test.tsx`) |
| `Azztec_SaaS_web_planner_CapacityBar_v1_0_0.tsx` (+ test) | 1.0.0 | `…/CapacityBar.tsx` (also exports `WeekStrip`), `…/CapacityBar.test.tsx` |
| `Azztec_SaaS_web_planner_PlannerGrid_v1_0_0.tsx` (+ test) | 1.0.0 | `…/PlannerGrid.tsx`, `…/PlannerGrid.test.tsx` |
| `Azztec_SaaS_web_planner_PlannerHeader_v1_0_0.tsx` | 1.0.0 | `…/PlannerHeader.tsx` (covered by `PlannerView.test.tsx` and the smoke) |
| `Azztec_SaaS_web_planner_WorkerPanel_v1_0_0.tsx` (+ test) | 1.0.0 | `…/WorkerPanel.tsx`, `…/WorkerPanel.test.tsx` |
| `Azztec_SaaS_web_planner_PlannerView_v1_0_0.tsx` (+ test) | 1.0.0 | `…/PlannerView.tsx`, `…/PlannerView.test.tsx` — **not in spec §10** (§4.12) |
| `Azztec_SaaS_web_routes_planner_v1_0_1.tsx` | **1.0.1** | `web/src/routes/planner.tsx` (1.0.1 = no default export, §4.4) |
| `Azztec_SaaS_web_main_v1_0_0.tsx` | 1.0.0 | `web/src/main.tsx` — the CLI's file + `QueryClientProvider` + Query devtools |

Regenerated on the box and committed, never a card: `web/src/routeTree.gen.ts` (17 `planner` lines), `web/package.json` + `web/pnpm-lock.yaml` (ESLint 10). `web/dist/` is gitignored — `git status` never showed it.

Commit **`8f742b4`**, tag **`s1f-grid-1.0.1`**, message `planner grid read-only + eslint 10 - S1f`. Tag carries 1.0.1: three files were patched mid-slice off the smoke (§4.1, §4.3, §4.4), same convention as `s1e-web-1.0.1`.

No backend source touched. Backend stays at `main.py` 0.3.0 / `diag.py` 1.1.1 / `config.py` 1.1.0 / planner 1.0.1.

## 3. Suite state

**Frontend: 96 tests, 8 files, all green, zero red, zero skips**, `pnpm lint` silent on ESLint 10.10.0. Per file, counted from the run: `rules.test.ts` 32 · `dates.test.ts` 16 · `PlannerGrid.test.tsx` 11 · `WOCard.test.tsx` 8 · `CapacityBar.test.tsx` 8 · `WorkerPanel.test.tsx` 8 · `usePlannerRange.test.tsx` 8 · `PlannerView.test.tsx` 5. All zero-network; the component files are also zero-fetch by import graph; `PlannerView.test.tsx` is the one file that stubs `fetch`, and it asserts the request count and the URL (`from=2026-09-14&to=2026-09-20`, never `from_`) — the fourth occurrence of the `from` alias closed at the wire.

**Backend: green with `web/dist/` present** — exit code 0 gated the commit. The count line was cut by my own `Select-Object -Last 3` trim (§4.6); the morning baseline was 125 dots, and no backend file changed. Ruff: `24 files left unchanged`, `All checks passed!`.

`pnpm build`: 340 ms; `index.html` 0.38 kB; `assets/index-*.js` 378.63 kB (121.31 gzip); `assets/index-*.css` 16.22 kB; **`assets/planner-*.js` 0.23 kB and `assets/routes-*.js` 0.35 kB as their own chunks** — the route file code-splits once it exports only `Route`.

## 4. Mistakes caught this session

### 4.1 I asserted `Monday` from memory; the oracle says `Mon`

`fmtLong` (oracle 514) builds from the **abbreviated** `DOW` — `'MON'.charAt(0) + 'on'`. `rules.ts` 1.0.0 was right; `rules.test.ts` 1.0.0 asserted `'Monday 14 Sep 2026'` in four places. Caught by the run, 2 red of 56. Test → 1.0.1; source → 1.0.1 for one wrong doc comment only. **Lesson:** strings are parity surface — read the oracle line, don't recall it.

### 4.2 The fixture's `counts` said 3 WO / 1 PM; it has 2 / 2

The pinned PM (105) is a PM. Fixed in the fixture before it shipped; the spec §6.0 sentence is wrong and stays wrong (append-only), corrected here.

### 4.3 Chips crushed instead of scrolling — an oracle bug RST exposed

Mon 14 Sep 2026 holds **106 PMs**. `.chip` sets `height:var(--chip-h)` but is a flex item in a column list, so past ~25 chips they squash into a smear. **The oracle carries the same rule** — KT never had a day like that. `planner.css` 1.0.1 adds `flex:none`; the list's `overflow:auto` then does what it was always for. Worth carrying back to Planner 1.8.1.

### 4.4 `export default PlannerRoute` defeated code-splitting

The router plugin warned eleven times: any non-`Route` export in a route file is pulled into the main bundle. 1.0.1 drops the default export and the `VERSION` const. Post-fix build: `planner-*.js` is its own chunk (§3).

### 4.5 Drop typo: `range.fictures.ts`

The one filename typed by hand out of 22. Detected by the import failing, not by the `Length` check — a wrong name has the right length. **Lesson (cheap):** every drop block since then lists the exact expected filenames; the next one should `Test-Path` each.

### 4.6 My `Select-Object -Last 3` ate the pytest count

The warnings block is longer than three lines. Exit code still gated the commit. Trim to `-Last 6` or grep `passed`.

### 4.7 The three-terminal trap

Vite and the backend traded places twice: each time one was started in the window the other was living in. Cost ~20 minutes and three false "it's broken" readings. **Rule now:** backend, Vite and the command shell are three windows, and any block that starts a server does it with `Start-Process powershell -NoExit` so it cannot land in the wrong one.

### 4.8 `Test-NetConnection 127.0.0.1:3000` said False while Vite was up

Node binds `localhost` to `::1` on Windows; the backend binds `127.0.0.1`. A port check has to try both stacks. The corrected check is in §5.6.

### 4.9 A stale tab reported the fix hadn't landed

After `routes/planner.tsx` 1.0.1 was on disk, Vite still printed the `PlannerRoute` code-split warning — with a **`[Client]`** prefix. That was an old tab's cached module logging through the HMR client, not the server transform. **Lesson:** close the old tabs before judging a fix by the console.

### 4.10 `sys.configurations.value_in_use` is `sql_variant`

pyodbc: `ODBC SQL type -16 is not yet supported`. `CAST(value_in_use AS int)`.

### 4.11 `svc_workmate` has `VIEW SERVER STATE` but not `VIEW SERVER PERFORMANCE STATE`

`sys.dm_exec_requests` / `sys.dm_exec_sessions` answered; `sys.dm_os_process_memory` was denied. The memory answer came from Task Manager instead (§6).

### 4.12 Spec §10 predicted 21 cards; 22 shipped, one renamed

The spec's `routes/planner.route.test.tsx` became `features/planner/PlannerView.test.tsx`: the view was split out of the route as a props-driven component so the wire test needs no router, route tree or memory history — the spec's own §6 contingency, taken before it was needed. `main.tsx` shipped as predicted. Tag the version that shipped.

### 4.13 Oracle quirk kept, pinned by a test

`chipTitle` on a **closed** WO carries the "PM – engine owned; run the S3 DDL" line, because `locked` covers status C/D too (Landmines §E) and the oracle's only locked text is the PM one. Parity, not a fix; `rules.test.ts` pins it with a comment.

## 5. Verified this session

### 5.1 Pins (2026-09-12)

`pnpm view eslint version` → **10.10.0**; `pnpm view typescript version` → **7.0.2**; `@tanstack/eslint-config` peers `eslint ^9.0.0 || ^10.0.0`. `pnpm add -D eslint@^10` → `+32 -40`, no peer warnings, `eslint 9.39.5 → 10.10.0`. Lint silent on 9 **and** 10 with the S1f pure layer already on disk (the drop landed before the bump; the pre-bump lint run gave the missing data point by accident).

### 5.2 OD-26 measurements

Standing window: 179 internal, **46** with hours, 184 contractors (1.0.0 §5.4). June 2026-06-01..07: 179 internal, **72** with hours, 184 contractors. June `cat` histogram: **DONE 604 · PM 42 · WO 9 · REQ 3** = 658; `counts.wo` = 12 = WO + REQ, exactly how `countText` lumps them.

### 5.3 RST priorities are `P1`…`P6` and `N/A`, not A–D

The oracle's `.pri.A/B/C/D` colours never fire on RST; every badge renders in the base muted style, three characters wide at most. Parity, not a defect. Colour-by-sort-order is an S1g question (§8.19).

### 5.4 The over-capacity rows

Top five `workerWeeks` by `pct` on the standing window: **80 → 2400 %**, **1036 → 1700 %**, **692 → 1000 %** (10 h against 1 h/week — exactly), 1064 → 700 %, 200 → 400 %. The fixture uses 692 as its 1000 % row.

### 5.5 The box, as read before any file was written

`main.tsx` builds its own `createRouter(...)` and never imports `router.tsx` — the CLI's `getRouter()` is dead code, left in place (§8.20). `tsconfig.json` has `paths` `@/*` and `#/*`; `vite.config.ts` has `resolve.tsconfigPaths: true` and `tanstackRouter({ autoCodeSplitting: true })`. `styles.css` is `@import "tailwindcss"` + resets, untouched; `planner.css` rides on the route. `vitest.config.ts`: jsdom, **no `setupFiles`, no globals** — so RTL's auto-cleanup does not run and jest-dom is not installed; every component test calls `cleanup()` in `afterEach` and asserts on `className` / `style.width` / `textContent`.

### 5.6 Vite is on **port 3000**, not 5173

The scaffold's `dev` script is `vite dev --port 3000`. Every smoke URL and every doc that says 5173 is wrong. Port check that works on this box:

```powershell
$web = (Test-NetConnection -ComputerName ::1 -Port 3000 -InformationLevel Quiet -WarningAction SilentlyContinue) -or (Test-NetConnection -ComputerName 127.0.0.1 -Port 3000 -InformationLevel Quiet -WarningAction SilentlyContinue)
```

### 5.7 Smoke, on real RST data (screenshots taken)

1. **Twoweek 14–27 Sep, pre-fix** — 14 cells, dow row, strips (`426.3 / 547 h · +3 WO no hrs`), lock glyphs on every PM, `0 WO | 473 PM | 0 done` = `rows=473`, rail `WORKERS (49)`, `49 of 179 internal · 184 contractors hidden`, Henry Harris `45 h · 1/wk` full red bar with `2 over`, 6M greyed, footer `lib 1.0.0 · api 1.0.1 · range 219 ms`. Mon 14 Sep (106 PMs) smeared → §4.3.
2. **Month Sep 2026 via Today** — 35 cells, 5 strips, 31 Aug and 1–4 Oct dashed, 12 Sep highlighted, `+105 more` caps, `6 WO | 1175 PM | 10 done` = `rows=1191`, strip `879.5 / 547 h` red with `+28 WO no hrs`, rail with both toggles flipped: `179 of 179 internal · 184 contractors`, `WORKERS (363)`.
3. **The OD-1 tooltip on an RST chip**, byte for byte: `3PL-MEG-003-0019 · [1W] PLANER MILL – G2 Stacker Weekly Greasing MARCO / Approved · priority P3 / 3PL-090 - 090 COMACT G2 Stacker / 1h (labour) / PM - engine owned; run the S3 DDL (WO_N_Plan) to allow planner pins`.
4. **Week 3–9 Aug at `:8000`, no Vite, Done on** — `48 WO | 76 PM | 629 done`, green DONE chips, Mon 3 Aug (181 done) **scrolling** with a visible scrollbar (§4.3 fixed), rail `64 of 179 internal`, `range 133 ms`.
5. **The no-data state**, by accident (backend down mid-smoke): red banner `request failed · TypeError: Failed to fetch`, empty cells, strips `0 / ? h · 0 WO`, rail `0 of 0 internal · nobody matches these toggles`. Renders cleanly.

Not taken: the June month with Done on (the September month covered category variety once Done was on), and a hover on 692 specifically — OD-25's "show the rendered over-capacity bar" is satisfied by shot 1 (4500 % row, full red, number in the flags) and by `CapacityBar.test.tsx` / `WorkerPanel.test.tsx` pinning 1000 % → `over` at `100%`.

### 5.8 The deep link through `app.frontend()`

First non-root SPA path ever requested. `GET /planner?mode=week&anchor=2026-09-16`: **`Accept: text/html` → 200 `text/html; charset=utf-8`**; **`Accept: */*` → 404 `application/json`** — the HTML fallback is Accept-gated, an API-style client gets a real miss. The browser then fetched `index-*.js`, `index-*.css`, **`planner-*.js`** and 404'd `favicon.ico`. **No `[F]`/`[G]` diag line for `/planner`** — 1.0.0 §8.14 confirmed as designed, still undocumented in `main.py`.

### 5.9 The 60 s poll, observed

17:43–17:50: two open tabs (twoweek Sep, month Aug 42-day) each refetching on a clean one-minute cadence, 140–670 ms per call. `refetchInterval` works; `refetchIntervalInBackground: false` was not tested (both tabs were visible).

### 5.10 SQL Server on this box

`@@SERVERNAME` **AzztecDev**, **Standard Developer Edition (64-bit) 17.0.1000.7**. `min server memory` 16 MB, **`max server memory` 2147483647 — uncapped**. Login `svc_workmate` from `AZZTECDEV`, program `Python`.

### 5.11 API `initials` for names with parentheses

`JP Paalvast (TS)` → `J(`; also `T(`, `M(`, `C(` on the chips and the rail. Backend `initials` computation, not S1f. §8.18.

## 6. The Docker incident — four hours, one process

Timeline, all 2026-09-12:

| Time | What | Number |
|------|------|--------|
| 10:53, 16:37 | `/range` standing window on a fresh backend | 368 ms, 757 ms |
| 16:39:58 | after a dozen nav clicks: **500** `QueuePool limit of size 5 overflow 10 reached, connection timed out, timeout 30.00`; the pile behind it took 45–110 s each | first symptom |
| 17:07–17:17 | backend restarted twice; every `/range` waits then all release together | 146–236 s |
| 17:25 | **one isolated request, nothing else running** | **126 s** |
| 17:29 | DMV while a request was in flight: `connected in 100 510 ms`; **no running requests, no open transactions**, one session | not blocking |
| 17:31 | `sqlservr` working set **0.1 GB** (private 0.8 GB) — the DB had been squeezed out | victim, not hog |
| 17:33 | Task Manager: **30.7 / 31.4 GB used, 72.5 GB committed** on a 32 GB box | paging |
| 17:34 | `Get-Process` by working set: **`com.docker.backend` 19.27 GB resident, 45.35 GB committed** | the hog |
| 17:35 | Docker Desktop + service killed, `wsl --shutdown`; memory fell from 29.6 GB to **9.5 GB** over ~60 s | |
| 17:38 | first request after, SQL re-warming from the page file | 41 s |
| 17:39 | second, third | **314 ms, 113 ms** |
| 17:41–18:10 | thirty-odd windows from nav clicks incl. the 42-day August (3784 rows) | 77–700 ms; two outliers at 5 s and 15 s around 18:06 on the Apr–May month (3257 rows), then 0.3 s again |

**What it was:** Docker Desktop's VM had ballooned to 45 GB committed and would not give it back. SQL Server (local, uncapped, default "take everything") lost the fight and ran from the page file; every query paid two minutes of disk. The 16:40 "pool storm" was the first visible symptom, not a cause: twelve concurrent queries at two minutes each is exactly what exhausts a 15-connection pool.

**What it was not:** the planner UI, the backend, the SQL, the DB — no file changed, no blocking session, no lock.

**Lessons, in order of cost:**

1. **Check the box before the code.** Task Manager's memory tab would have ended this at 16:41. Two hours went into DMVs and request timing while the answer was one screenshot away. New rule for any "it's slow" report: free memory and top-5 processes by working set first, verbatim, before a single hypothesis.
2. **`max server memory` is uncapped** on a dev box that shares 32 GB with Docker, Node, Edge and a human. Capping it (8 GB is the sensible number for this copy) is one `sp_configure`, but `svc_workmate` cannot do it — SSMS under Adriaan's own login. §8.16.
3. **Docker Desktop needs a memory cap** in its settings or `.wslconfig` before it runs alongside SQL Server again. §8.17.
4. The diagnostic scripts (`dbdiag.py` — requests / open transactions / sessions by program; `sqlmem.py` — configured limits + DMVs) live in `%TEMP%`, not the repo. They are read-only and use the backend's own `build_url`; worth a `scripts/` home with a version header if they are needed a second time.

## 7. Doc-correction queue

Applied this session: **none of the compiled set** — the incident ate the time. Everything below is queued for the next docs commit, which should be the first thing next session does, from this log:

- **Index → 1.3.0:** §3.4b/§3.5 the S1f tables (§2 above); §5 eslint 10 / typescript 6.x / TS 7 noted; §6 HEAD `8f742b4`, tag `s1f-grid-1.0.1`, 96 + 125.
- **Landmines → 1.3.0, §C:** (a) `@tanstack/cli`'s `main.tsx` builds its own router and ignores `router.tsx`; (b) a route file exports `Route` only, or the plugin cannot code-split it; (c) `vitest.config.ts` has no setupFiles/globals — explicit `cleanup()`, no jest-dom; (d) Vite is on 3000, Node binds `::1`, port checks try both stacks; (e) `.chip` needs `flex:none` in a column flex list — the oracle's latent bug; (f) the `[Client]` prefix on a Vite warning means a browser tab said it, not the server. **§E:** RST priorities `P1–P6`/`N/A`; `initials` with parentheses; 106 PMs on one day is normal. **New §F — the box:** Docker Desktop memory, SQL `max server memory`, Task Manager first.
- **Ways of Working → 1.3.0:** §5 verify-before-relying gains "check free memory and the top processes before diagnosing latency"; §6 smoke: three windows, servers via `Start-Process`, `Test-Path` every dropped filename, `-Last 6` on pytest; the pytest count line rule.
- **Architecture → 1.0.2:** §3.2/§8 TypeScript 6.x (was 5.9), ESLint 10, TS 7.0.2 published not taken; `components.json (shadcn)` → S1g; §5 layout adds `store.ts`, `planner.css`, `range.fixture.ts`, `PlannerView.tsx`, `PlannerHeader.tsx`, `WorkerPanel.tsx`, `DayCell.tsx`; `router.tsx` marked unused; dev port 3000.
- **Port Spec → 1.0.1:** §6 S1 splits S1a–**S1g**; §7 `WorkerPanel` and `PlannerGrid` are S1f, `SelectedWOCard` / filters / day dialog are S1g; plus everything carried from 1.0.0 §7 (§2 dev user, §3 envelope, §8 actor, §9 OD dates). **Still not read in full** — same caveat as before.
- **S1f spec** stays 1.0.0 (append-only): §6.0 counts are 2 WO / 2 PM; §10 is 22 cards with `PlannerView(.test).tsx` and no `planner.route.test.tsx`; §8 URLs are `:3000`.
- **Handover brief → regenerate** from this log (`Azztec_SaaS_Handover_Brief_2026-09-12_v1_1_0.md`).
- Carried from 1.0.0 §7, unapplied: Landmines §E `Priority.Colour`, `WO_C_Activity`, triggers; Install doc / Bootstrap; `.gitignore` symlinks; Scaffold_Repo 1.0.1 → PK then 1.0.2; `web/.vscode/settings.json` vs root.

## 8. Open list

Carried from 1.0.0 §8 with closures; numbering restarts.

1. **KT dev copy** for genuine Ignition parity. `parity_range.py` blocked on it. S1f claims wire-level contract correctness and screenshot-level behaviour parity on RST, not Ignition parity.
2. **OD-2 open:** which `Users` rows map to logins. Dev actor `1`.
3. **Unexplained:** `workmate.diag` records reach a root handler under pytest despite `propagate=False`. Blocks nothing.
4. **Six-month view** — needs the API summary shape. 6M is a disabled button with a tooltip until then.
5. **SPA html-fallback under `/api/`** — the instrument still logs an API miss as a hit (1.0.0 §8.6). S7. New this session: the fallback is Accept-gated (§5.8), so the fix is narrower than it looked.
6. **Double boot lines** under `fastapi dev` — carried.
7. **Cosmetic:** `[F] diag self-test` logs `actor: 0`. S2.
8. **Parity oracle, not to fix:** `capacity 0.0` → `pct 0, flag ok`. OD-25 renders `? h`. Carried.
9. `httpx2` / anyio `BlockingPortal` deprecations. Next dependency bump.
10. `.gitignore` symlink fix — carried.
11. **Project-knowledge gaps** (1.0.0 §8.12) — carried, unchanged; still blocks the next backend audit, not S1g.
12. **The mount branch emits nothing** — carried; one `[F] frontend mounted dist=…` line in the next `main.py` patch.
13. **Diag middleware scoped to `/api`** — **confirmed** by §5.8; write it into `main.py`'s docstring and close.
14. **operationId cosmetic** — carried.
15. ~~TypeScript 6.0.3 vs 5.9 / ESLint 9 vs 10~~ **Closed — OD-28.**
16. **NEW — `max server memory` uncapped** on AzztecDev (§5.10, §6). Cap at 8 GB via SSMS under a sysadmin login; `svc_workmate` cannot. Do it before the next smoke.
17. **NEW — Docker Desktop memory cap.** 45 GB committed on a 32 GB box (§6). Settings → Resources, or `.wslconfig` `memory=`. Do it before Docker runs again; the compose file exists and will be wanted.
18. **NEW — request concurrency and cancellation.** A dozen nav clicks = a dozen in-flight `/range` queries; TanStack Query does not cancel the previous one and the server would keep running it if it did. Harmless at 100–500 ms (§5.9), catastrophic at 2 min (§6). Options for the S1g audit: pass the query `signal` through the generated client (hey-api supports it), a nav debounce, pool sizing. **First line of the S1g audit** — decide, don't drift.
19. **NEW — priority badge colours for RST.** `P1–P6` all render base grey (§5.3). Colour by `Priority.sortOrder` / id rather than by letter is the obvious port; needs an OD because it departs from the oracle.
20. **NEW — `web/src/router.tsx` is dead** (§5.5). Delete in S1g or wire `main.tsx` to it; not both.
21. **NEW — `initials` for names with parentheses** (§5.11). Backend `planner/rules.py` or wherever initials are computed; needs its own test. Not S1g scope unless S1g touches the backend anyway.
22. **NEW — Adriaan's asks off the Ignition screenshots:** the right-hand **Selected WO card** (Status · Start · End · Priority · Asset · Location · Hours · Responsible · Planned labour · Open in WO Maintenance · Clear) and **more on the hover**. Both are S1g. The hover list is an audit input — Adriaan to say what is missing from the hover versus what belongs on the card.
23. **NEW — the 5 s / 15 s outliers** at 18:06–18:07 on the Apr–May month (3257 rows) with everything else at 0.3–1.3 s. Probably the box still re-warming after §6. Watch, don't chase; if it recurs with Docker down, it's real.
24. **NEW — `refetchIntervalInBackground: false` untested** (§5.9). One hidden-tab check next smoke.
25. **NEW — `prettier --check` is not in the smoke.** `pnpm lint` is eslint only; the CLI's `check` script exists. Add it to the frontend order or say why not.
26. **web/.vscode/settings.json** vs root; **Scaffold_Repo 1.0.1 → PK then 1.0.2** — carried (§7).

## 9. Next slice

**S1g — the rest of the read-only planner.** Opens with an audit, not a build. Candidates, from the S1f cut and §8.22: the **selected-WO card** (Ignition screenshot is the reference; OD-5 says details inline, no route), the **filters row** (team / worker / priority / unassigned / search, which also brings `capacityWorkers`'s two missing precedence branches and the `.wk.on` click-to-filter), the **day dialog** (`showDay`), **keyboard nav** (`← → T`), the **hover** additions. **shadcn/ui arrives with the first dialog** — this is the slice. `router.tsx` deleted. Still **no drag** — `@dnd-kit` and `/move` are S2.

**Carry-ins for the S1g audit:**

1. **§8.18 first** — concurrency and cancellation. An unsigned dependency is the audit's first line, not the build's next step.
2. **§8.16 and §8.17 before any smoke** — SQL memory cap and Docker cap. Not code, but the smoke is not trustworthy without them.
3. **Adriaan's hover list** (§8.22) — what goes on the hover, what goes on the card. Measured against the oracle's `showDay` and `renderSelected`, not invented.
4. **Priority colours** (§8.19) as an OD.
5. **The compiled doc set** (§7) is applied **before** the S1g audit starts, so the audit reads Index 1.3.0, not this log.
6. **Test harness facts** (§5.5): no auto-cleanup, no jest-dom — every new component test follows the S1f pattern.
7. Six-month summary shape still unsigned (§8.4); parity still blocked on the KT copy (§8.1).

## 10. Changelog

- 1.1.0 (2026-09-12) S1f shipped and tagged `s1f-grid-1.0.1`, HEAD `8f742b4`. OD-26…OD-29 signed; selected card / filters / day dialog cut to S1g; shadcn and lucide deferred to the first dialog; 6M disabled. The read-only planner renders week / twoweek / month on real RST data with the oracle's DOM, lock glyphs on 2,364 engine-owned PMs, the OD-24/26 rail, OD-25 bars at 1000–4500 %, the OD-1 tooltip byte for byte, and deep-links through `app.frontend()` from a code-split `dist/`. 96 frontend + 125 backend green on ESLint 10. Thirteen mistakes caught, two of them oracle bugs RST exposed. Four hours lost to Docker Desktop holding 45 GB of a 32 GB box — SQL Server starved, every query two minutes; root-caused, killed, recorded, two caps queued. Supersedes 1.0.0 §7–§9.
- 1.0.0 (2026-09-12) The S1e record — see that file; §1–§6 stand.
