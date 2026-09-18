# Azztec SaaS — S1k Shell Chunk Spec

**File:** Azztec_SaaS_S1k_Shell_Chunk_Spec_v1_0_1.md · **Version:** 1.0.1 · **Date:** 2026-09-16 · **Author:** Adriaan
**Status:** Built on a delegation — **OD-50…OD-54 taken as proposed on "go" (2026-09-16), recorded as *delegated, not signed* (the OD-35 precedent)**; a 🤙 on this file converts them. **1.0.1 supersedes 1.0.0 the same day:** 1.0.0 numbered its decisions OD-48…OD-52, but OD-48 and OD-49 were signed for weekno on 2026-09-15 (log 09-15 §1) — the numbering hazard, again — and its baseline (169 / 2, HEAD `6968c54`) was the 09-14 state; S2a has shipped since. Every OD here is renumbered +2, the baseline is the 09-15 state, and §2.6 records which evidence arrived. Thirteen of the fourteen cards are cut; **card 11 (`__root.tsx`) is held until the CLI's file is pasted** (E2) — never re-emit a file you have not read.
**Target path:** `docs/Azztec_SaaS_S1k_Shell_Chunk_Spec_v1_0_1.md` (+ project knowledge, replaces 1.0.0)
**Parent:** Index 1.8.0 §6 and log 09-15 §10 — a slice outside the planner line, between S2a and the S2b audit (which stays next); Port Spec 1.0.6 §6/§7 — the planner is the first page the shell carries. **The 09-15 doc set (Index 1.9.0, Landmines 1.9.0, WoW 1.3.6, Port Spec 1.0.7, Architecture 1.0.8) is still unapplied** — carried to this session's close, with §9.1 folded into it
**Source of truth:** the Ignition views `Workmate/Navigation/HeaderToolbar` v16.47 and `Workmate/Navigation/SideMenu` v4.20 — byte copies `docs/reference/HeaderToolbar_2026-09-16_view.json` and `docs/reference/SideMenu_2026-09-16_view.json`, delivered with 1.0.0; `Workmate_Material_Icons_Library_v1_0_0.svg` (E3, as it arrived — §2.6); the full project export `MainSCADA_Timberlands_2026-09-16_1307.zip` (page config, style classes, stylesheet v2.69); the live KT page screenshot (E6). Read from the PK cards, not remembered: `planner.css` 1.1.1, `PlannerView.tsx` 1.1.0, `routes/planner.tsx` 1.0.1, `main.tsx` 1.0.0, `lib/dates.ts` 1.1.0, `dates.test.ts` 1.1.0
**Closes:** nothing. **Writes:** no database, no backend file, no contract change (`openapi_0_4_0.json` untouched, no `pnpm gen:api`), no `pnpm add`.
**Signed decisions in force:** OD-5 (disabled-with-a-title precedent), OD-12 (no sign-in yet), OD-27 / OD-31 (a port ships the oracle's CSS; no shadcn, no lucide, no Tailwind classes in a port), OD-29 (`/planner` search is `mode` + `anchor`), OD-34 (chrome says only what is true), D-6 (the SPA is served by `app.frontend()`); Ways of Working §2 (route files carry the version in the header only); Landmines §C (only `lib/dates.ts` touches `Date`; a route file exports `Route` only; Vitest has no `setupFiles` / `globals`; jsdom reports colours as `rgb()`)

---

## 1. Scope — fourteen cards and two reference copies, then stop

The navigation chrome KT runs on every Workmate page, copied as is: the 50 px header docked top and the 50 px rail docked left, rendered around every route in `web/`. **One control navigates: Plannex → `/planner`.** Everything else draws exactly as the oracle draws it and does nothing (OD-51) — except the clock, and two browser-only controls recommended live (fullscreen, Print).

| # | Deliverable | Target path | Version | Change |
|---|---|---|---|---|
| 1 | `Azztec_SaaS_web_shell_rules_v1_0_0.ts` | `web/src/features/shell/rules.ts` | **new** | the oracle's tables + pure rules (§3.1) |
| 2 | `Azztec_SaaS_web_shell_rules_test_v1_0_0.ts` | `web/src/features/shell/rules.test.ts` | **new** | pair of 1 |
| 3 | `Azztec_SaaS_web_shell_icons_v1_0_0.tsx` | `web/src/features/shell/icons.tsx` | **new** | 22 glyphs verbatim from E3 + `Glyph` + the two image URIs (§3.2) |
| 4 | `Azztec_SaaS_web_shell_HeaderToolbar_v1_0_0.tsx` | `web/src/features/shell/HeaderToolbar.tsx` | **new** | §3.3 |
| 5 | `Azztec_SaaS_web_shell_HeaderToolbar_test_v1_0_0.tsx` | `web/src/features/shell/HeaderToolbar.test.tsx` | **new** | pair of 4 |
| 6 | `Azztec_SaaS_web_shell_SideMenu_v1_0_0.tsx` | `web/src/features/shell/SideMenu.tsx` | **new** | §3.4 |
| 7 | `Azztec_SaaS_web_shell_SideMenu_test_v1_0_0.tsx` | `web/src/features/shell/SideMenu.test.tsx` | **new** | pair of 6 |
| 8 | `Azztec_SaaS_web_shell_AppShell_v1_0_0.tsx` | `web/src/features/shell/AppShell.tsx` | **new** | composition, clock, fullscreen, print (§3.5) |
| 9 | `Azztec_SaaS_web_shell_AppShell_test_v1_0_0.tsx` | `web/src/features/shell/AppShell.test.tsx` | **new** | pair of 8 |
| 10 | `Azztec_SaaS_web_shell_css_v1_0_0.css` | `web/src/features/shell/shell.css` | **new** | the views' inline styles under `.wm-shell` (§3.6) |
| 11 | `Azztec_SaaS_web_routes_root_v1_0_0.tsx` | `web/src/routes/__root.tsx` | CLI → **1.0.0** | wraps `<Outlet />` in the shell — **written against E2's paste** (§3.7) |
| 12 | `Azztec_SaaS_web_planner_css_v1_1_2.css` | `web/src/features/planner/planner.css` | 1.1.1 → **1.1.2** | `height:100vh` → `100%`; the day dialog contained (OD-54, §3.8) |
| 13 | `Azztec_SaaS_web_lib_dates_v1_2_0.ts` | `web/src/lib/dates.ts` | 1.1.0 → **1.2.0** | `headerDate` / `headerTime` / `headerClock` (§3.9) |
| 14 | `Azztec_SaaS_web_lib_dates_test_v1_2_0.ts` | `web/src/lib/dates.test.ts` | 1.1.0 → **1.2.0** | pair of 13 |
| 15 | `HeaderToolbar_2026-09-16_view.json` | `docs/reference/` | reference | byte copy of the export — **delivered with this spec** |
| 16 | `SideMenu_2026-09-16_view.json` | `docs/reference/` | reference | byte copy of the export — **delivered with this spec** |

**Untouched:** every `features/planner/*` module except `planner.css`; `routes/planner.tsx`; `routes/index.tsx`; `main.tsx`; the generated client; the whole backend (194 passed, 2 skipped stays); every database.

**Not in this slice (cut at the audit):** the Application / Utilities / System dropdowns — their popup views (`Workmate/Popups/Menu*Popup`) are not in the export; tips — the prefs load, toggle, dismiss, reset and their four named queries (item 33); rights — `workmate.security.allowed` behind VisualX and the search pill; roles — `hasRole("Administrator", …, "KPP")` behind the Users button (OD-2 / D-5); the brand read — `workmate.brand.get_mode()` from `System_Configuration` (OD-53); the AI navigator bridge `wm-ai-ui-action` (dark at KT); the legacy toolbar-state handlers `updateToolbarState` / `set-history-tab` and the view customs they set (nothing in this view binds to them); `nav-active` messaging (inert since SideMenu v4.20 — the router path replaces it); the Print dispatcher's PO and WO popups and WO Wizard's `CreateWO_popup` (those pages do not exist here); `debug-log` messages (the client diag route is item 28).

## 2. Evidence

### 2.1 The export — read in full 2026-09-16, before this spec

`Workmate_Navigations_-_Header_and_Sidemenu.zip`, 34,893 B, seven files from project `MainSCADA Timberlands`:

| Resource | Bytes | Last modified (`resource.json`) | Root `meta.name` |
|---|---|---|---|
| `HeaderToolbar/view.json` | 72,315 | Adriaan, 2026-09-16T00:06:07Z | `HeaderToolbar_v16_47` |
| `SideMenu/view.json` | 38,363 | Adriaan, 2026-08-30T07:24:19Z | `SideMenu_v4_20` |
| the two thumbnails | 10,522 / 5,119 | — | 876×15 and 15×440 px: the AZZTEC brand showing; the VisualX rail item and the search pill absent |

Both views are delivered byte-for-byte as cards 15/16 (`cmp` clean). Every component's `props`, `position`, `propConfig` bindings, `events` and `scripts.messageHandlers` were read, and both `onStartup` scripts.

### 2.2 HeaderToolbar v16.47 — the oracle values

Root: flex row, `alignItems: center`; `background: linear-gradient(90deg, #242E30 0%, #242E30 55%, #003050 75%, #004063 100%)`, `minHeight` / `maxHeight: 50px`, `paddingLeft: 4px`. Children in order:

| # | Component | What it is |
|---|---|---|
| 1 | `WorkmateLogo` (image) | shown when brand ≠ `AZZTEC`; `/system/images/Workmate_Logo_48_Rev.png`, 48×48, `objectFit: contain`, `marginRight: 10px`, pointer; click → `/Hub` |
| 2 | `AzztecLogo` (image) | shown when brand = `AZZTEC`; `data:image/svg+xml;base64,…` — 16,706 characters, decodes to 12,510 B, its comment `Azztec_Logo_v1_1_0 … Adriaan … 2026-09-16`; 48×48, `objectFit: fill`, `marginRight: 10px`, pointer; click → `/Hub` |
| 3 | `BrandBlock` | `shrink 0`, `alignItems center`, `gap 6px`, `marginLeft 2px`, `marginRight 14px`, `overflow hidden`. `AMMSSpine` (brand ≠ AZZTEC): a 12 px column with vertical `MMS` and `A` — 8 px, `#9AA3A7`, `letterSpacing 1px`, `lineHeight 10px`, `writingMode vertical-rl`, `rotate(180deg)`, weights 700 / 800, `A` carries class `wm-brand-a-glow`. `lblBrandName` "Workmate" (≠ AZZTEC) and `lblBrandNameAzztec` "Azztec" (= AZZTEC, class `wm-brand-azztec-gold`): 26 px / 700, `letterSpacing 0.8px`, `lineHeight 28px`, text clipped to a vertical gold gradient, `drop-shadow(0 2px 3px rgba(0,0,0,0.35))`, a five-layer `textShadow`. The two gradients differ — "Workmate" `#FFFFFF 0% · #FFF3C9 30% · #F5D67E 48% · #B37F2A 51% · #96691F 72% · #F2D68C 100%`; "Azztec" `#FFFFFF 0% · #FFF7D6 26% · #FFE08A 47% · #C8912F 51% · #A87718 70% · #FFE9A8 100%` |
| 4–6 | `MenuApplication` · `MenuUtilities` · `MenuSystem` (labels) | 12 px / 400, `#C0C8CA`, `padding 2px 8px`, `borderRadius 3px`, pointer; underline `2px solid #EBC452` when the active key is in the group's pipe list, else `2px solid transparent`; click → a popup at the click point (the popup views are not in the export) |
| 7 | `SepMenuNav` | `basis 1px`, `shrink 0`, `borderLeft 1px solid rgba(255,255,255,0.15)`, `height 16px`, margin `0 6px` |
| 8–13 | six module buttons | the table below |
| 14 | `Spacer` | `grow 1` |
| 15 | `RightControls` | `shrink 0`, `alignItems center`, `gap 8px`, `paddingRight 8px`: `VXSearchPill`, `TipsToggle`, `ControlStack` — the table below |

The three pipe lists, verbatim — Application lights for `pmx`, `schedulex` and `visualx`, and **not** for `plannex` (its list says `planning`):

```
Application  |asset|part|meter|locationsetup|supplier|team|maintenance|wizard|pmx|timesheet|planning|schedulex|visualx|resetpassword|
Utilities    |pmrelease|rebuildpmwo|archiveworkorders|assetarchive|partarchive|customformsetup|
System       |refcodesetup|usersettings|usermapping|systemsetup|useravailability|securitysetup|
```

The module buttons — flex row, `alignItems center`, `padding 1px 6px`, `borderRadius 3px`, pointer; glyph `basis 15`, `shrink 0`, `marginRight 2px`; label 12 px, `#C0C8CA`, `lineHeight 1`:

| Button | Key | Colour | Glyph | Label basis | Underline when active | onClick at KT |
|---|---|---|---|---|---|---|
| `BtnSchedulex` | `schedulex` | `#9C27B0` | `event_note` | 55 | `2px solid #9C27B0` | `/schedulex` (clears five `schedulex*` session props) |
| `BtnPlannex` | `plannex` | `#4CAF50` | `event_available` | 55 | `2px solid #4CAF50` | `/Workmate/Plannex/Plannex` |
| `BtnProcurex` | `procurex` | `#795548` | `shopping_cart` | 50 | `2px solid #795548` | `/procurex` (clears five `procurex*` session props) |
| `BtnPMx` | `pmx` | `#607D8B` | `build` | 28 | `2px solid #607D8B` | `/Workmate/PMx/PMx` |
| `BtnInvoicex` | `invoicex` | `#00BCD4` | `receipt` | 48 | `2px solid #00BCD4` | **empty script — dead at KT too** |
| `BtnMyReports` | — | `#E91E63` | `assessment` | 45 | **no binding — no border at all** | navigation action `/workmate/home?tab=2` |

The right controls:

| Component | Oracle |
|---|---|
| `VXSearchPill` | shown when `runScript('workmate.security.allowed', …, 'visualx')`; 26 px tall, `rgba(255,255,255,0.10)` fill, `1px solid rgba(255,255,255,0.22)`, radius 13 px, padding `0 12px`, `gap 6px`, a 0.2 s colour transition; glyph `search` `#DEBF7A` at `basis 16px`; "Search parts" 11 px / 500 `#E8E4DB`, `letterSpacing 0.3px`; click → the `VX_QuickSearch` popup |
| `TipsToggle` | a 22×22 circle, `marginRight 4px`, 0.2 s transition; `#00BCD4` with `boxShadow 0 0 6px 2px rgba(0,188,212,0.3)` when `session.custom.showTips`, else `#8E9EA3` / `none`; glyph `help_outline` white; click → the `tips-toggle` message |
| `ControlStack` | column, `basis 160px`, `shrink 0`, `height` / `maxHeight 50px`, margin `0 5px`, `overflow hidden`; two rows at `basis 28px` (they shrink to 25 px), `overflow visible` |
| — `topRow` | `fsCoord` (coord container, percent mode, `aspectRatio 1:1`, `basis 20px`, `shrink 0`, `margin 5`, `overflow visible`) → `fsBtn` (fills it; glyph `fullscreen`; white fill, `1px solid #FFFFFF`, radius 5; action **fullscreen, Toggle, Page**) · `logoutCoord` (the same, `basis 20.0px`) → `logoutBtn` (image `/system/images/material_additional/logout_24dp_1F1F1F.svg` at 14×14, the same styling; action **logout**) · `dateLabel` (`grow 1`, text `dateFormat(now(), "MMM d")`) |
| — `bottomRow` | `userCoord` → `userBtn` (glyph `group`, **visible only when `hasRole("Administrator", user, "KPP")`**, nav `/DisplayUsers`) · `timeLabel` (`grow 1`, text `dateFormat(now(), "HH:mm:ss")`) |
| both clock labels | `textStyle`: class `Text/SubHeader`, `#FFFFFF`, `fontSize 1.7vh`, padding `0 5`, `textAlign right`; `timeLabel` also `overflowWrap normal`, `textOverflow clip` |

`onStartup` seeds `session.custom.activePage`, loads the tips prefs (`Workmate/Tips/GetUserPrefs`; `showTips = true` when there is no row) and sets `session.custom.wmBrandMode = workmate.brand.get_mode()` with a `'WORKMATE'` fallback. **Seven** message handlers: `updateToolbarState`, `set-history-tab`, `tips-dismiss`, `tips-toggle`, `tips-reset`, `nav-active`, `wm-ai-ui-action` (the audit said eight — §4 trap 15).

### 2.3 SideMenu v4.20 — the oracle values

Root: column, `width` / `minWidth` / `maxWidth 50px`. `NavContainer` (`grow 1`, `#242E30`, padding `8px 0`) holds the items; `BottomContainer` (`#242E30`, `paddingBottom 8px`) holds `Divider2` and Print, so Print sits at the foot. An item: column, `alignItems center`, `minHeight 50px`, padding `6px 0`, pointer; left border `4px solid <active colour>` when the active key matches, else `4px solid transparent`; glyph `basis 19`, `marginBottom 4px`; label 7 px `#F3EEE7`, centred. Dividers: `borderBottom 1px solid #333333`, margin `6px 10px`.

| # | Item (`MenuItem_…`) | Key(s) | Glyph | Colour | Active border | onClick at KT |
|---|---|---|---|---|---|---|
| 1 | Home | `home` | `dashboard` | `#DEBF7A` | `#E91E63` | `/home` |
| — | `Divider1` | | | | | |
| 2 | Explorer | `explorer` | `search` | `#2196F3` | `#E91E63` | `/Explorer` |
| 3 | Assets | `assets` | `construction` | `#FF9800` | `#E91E63` | `/assetsetup` |
| 4 | Labour | `labour` | `engineering` | `#FF9800` | `#E91E63` | **empty script — dead at KT too** |
| 5 | WO Maint | `womaint` | `assignment` | `#E91E63` | `#E91E63` | `/WOMaint` |
| 6 | WO Wizard | `wowizard` | `flash_on` | `#9C27B0` | `#E91E63` | the `CreateWO_popup` popup |
| 7 | PM Wizard | `pmwizard` | `handyman` | `#9C27B0` | `#E91E63` | **empty script — dead at KT too** |
| 8 | VisualX | `visualx` | `dashboard` | `#4CAF50` | `#E91E63` | `/Workmate/VisualX/VisualX` — **rights-gated** |
| 9 | Insights | `insights` | `insights` | `#DEBF7A` | **`#DEBF7A`** | `/insights` |
| 10 | Supplier | `supplier` | `local_shipping` | `#00BCD4` | `#E91E63` | `/supplier` |
| 11 | Parts | `parts` | `settings` | `#009688` | `#E91E63` | `/Workmate/Parts/PartSetup` |
| 12 | PO List | `purchaseorder` | `featured_play_list` | `#0B5ED7` | `#E91E63` | `/purchaseorder` |
| 13 | Invoice | `invoicemaint`, `invoicex` | `receipt_long` | `#FFC107` | `#E91E63` | `/InvoiceMaintenance/InvoiceMaint` |
| — | `Divider2`, then `MenuItem_Print` | — | `print` | `#AAAAAA` | **a static `3px solid transparent`**, no binding | dispatcher: `purchaseorder` → `POPrintPopup`; `workorder` / `wo` / `womaint` / `workorders` → `WOPrintPopup`; anything else → `system.perspective.print()` |

The dispatcher reads `view.custom.activePage`, seeded at startup from `session.custom.activePage`, else a 17-row primary-view path map, else `''`; the default saved in the view JSON is a stale `"partsetup"`. On the Plannex page every route gives `plannex` or `''`, so KT prints the browser page. The `nav-active` handler is `pass` — **and its comment credits a "HeaderToolbar v16.43 pathKey watcher"; v16.47 contains no `pathKey` at all** (§9.3).

Glyphs: 22 unique across the two views (`search` and `dashboard` are each used twice). Rendered by this slice: 21 — OD-52 hides `group` with the Users button, while Explorer keeps `search` on screen. All 22 ship so un-gating is a flag, not a new file.

### 2.4 Props Perspective does not map — ported as not applied

`meta.classes` (`psc-menubar-item`, `psc-toolbar-btn`) is not a meta property; classes go through `props.style.classes`, which the two brand labels and the clock use correctly. `justifyContent` on `VXSearchPill` and on every rail item is not a flex-container prop (Perspective's is `justify`) — so, believed, rail content sits at the top of its 50 px item rather than centred. `size` on the header glyphs is not an icon prop, and `style.fontSize` on a glyph is believed not to size it: glyph size comes from the flex basis (15 px header, 19 px rail). **E6 confirms or corrects all four before the tag.** No hover rule exists anywhere in either view; if E4's stylesheet carries one it ports, and if not, none is added.

### 2.5 Collisions in `web/`, read from the PK cards

- `planner.css` 1.1.1 line 51 — `.wm-planner{…height:100vh…}`. The oracle's `#app` was 100vh of an **iframe** inside Perspective's content area; under a 50 px header it overflows the viewport by 50 px.
- `planner.css` 1.1.1 line 207 — `.wm-planner .ovl{position:fixed;inset:0;…z-index:40}` (oracle 361). Inside the iframe the day dialog's dim covered the planner only; here it would cover the header and the rail. Other positioned descendants read so far: `.loading` against `.grid-wrap{position:relative}` (81 / 164) and `.wsel .menu` against `.wsel{position:relative}` (180 / 181).
- `PlannerView.tsx` 1.1.0 53–61 — `PlannerSearch = { mode: Mode; anchor: string }`, both required, so a typed navigation to `/planner` must pass `search`. `validateSearch({})` returns `{ mode: 'month', anchor: todayIso() }` — the planner's own defaults, which is what KT's Plannex opens.
- `routes/planner.tsx` 1.0.1 already imports `validateSearch` from `PlannerView` into its route config, so the root route importing the same binding adds nothing to the main chunk (§4 trap 6 checks it).
- `main.tsx` 1.0.0 imports no stylesheet, so `styles.css` arrives some other way — most likely `__root.tsx`. E2 says.
- `lib/dates.ts` 1.1.0 is the only module that touches `Date`; `todayIso()` (154) is the browser's civil day. Perspective formats `now()` in the session's time zone, which comes from the browser — E6's time against the box clock confirms. `dates.test.ts` 1.1.0 has 16 `it(`.

### 2.6 The owed evidence — what arrived on 2026-09-16, and what it settled

| # | Evidence | Status | Settles |
|---|---|---|---|
| ★ E1 | Block 1: `git log`, `git status`, both suites bare | **not yet pasted** — the baseline is taken from log 09-15 §3 (HEAD `5a4802a`, 194 / 2, 170 in 11) and the smoke's first block re-reads it | the prediction's base |
| ★ E2 | Block 2: `__root.tsx`, `styles.css`, `index.html`, the `src/` list, the scripts | **not yet pasted — card 11 is held on it** | the root route diff; the preflight (trap 13); the `#app` height chain |
| ★ E3 | the icon glyphs | **arrived as `Workmate_Material_Icons_Library_v1_0_0.svg`** — 191 `material/*` icons the KT project references, geometry from Google's Material Icons baseline (react-icons 5.6.0), not the gateway's own `material.svg`; its index says a glyph can differ slightly between versions. All 22 present, every one paths-only, `viewBox 0 0 24 24`; copied into card 3 by script. Byte parity with the gateway's file is therefore *believed*, not measured — the smoke's screenshot check owns it | card 3 |
| ★ E5a | `logout_24dp_1F1F1F.svg` | **did not arrive.** Card 3 carries the Material Icons baseline `logout` path, **typed and flagged** in its header — the one glyph in the slice not copied from a file; a one-constant swap when the gateway file lands | the logout button |
| E5b | `Workmate_Logo_48_Rev.png` | **did not arrive → WORKMATE mode is cut** (OD-53); item raised in the log, never faked with a missing image | — |
| E4 | page config, stylesheet, style classes | **arrived, in the full export.** Page config: every Workmate page docks `HeaderToolbar` top (50, fixed, push, handle hidden) and `SideMenu` left (50, the same), `cornerPriority: top-bottom` — **the header owns the corner**, the grid default in §3.6 stands. `Text/SubHeader` = `Verdana / 12px / bold / var(--textSubHeader)`, so the clock is **Verdana bold** in the view's white at `1.7vh`. Stylesheet v2.69 (141,544 B): **no rule** for `psc-toolbar-btn`, `psc-menubar-item`, `wm-brand-azztec-gold` or `wm-brand-a-glow`, and **no `:hover`** for any of them — nothing is added. Session props seed `wmBrandMode: "AZZTEC"`, `showTips: true`; `brand.get_mode()` (script read) defaults to `'WORKMATE'` when the row is absent — KT's row says AZZTEC. Project locale `en-NZ`, timezone `Gateway Timezone` | §2.4 partly; §3.6; OD-53 |
| E6 | the live Plannex screenshot (1916×1197, 13:08:06) | **arrived.** `Sep 16` — the en-US abbreviation, so `headerDate` is plain date-fns (§3.9). The clock is bold Verdana. The rights-gated pill, VisualX and the admin Users button are all **visible** for Adriaan — a rights holder — which changes nothing here (OD-52: no rights yet). **Plannex is not underlined and Home's rail border is lit**: the session's `activePage` was `home` (the page was reached without `BtnPlannex`'s onClick), which is the oracle's session-state rule working, not a binding this port disagrees with — here `/planner` lights Plannex by the router path (§3.1). The computed font-family / font-size lines were not pasted — **font sizes are deferred by decision ("sort the font sizes later")**; the planner's stack ships and the comparison is recorded in the log | §2.4; §3.9; the smoke's by-eye check |

## 3. The changes, exactly

### 3.1 `features/shell/rules.ts` 1.0.0 — pure (card 1)

No `Date`, no DOM. The oracle's tables as data, keyed by the oracle's own `meta.name`:

```ts
export const VERSION = '1.0.0';
export type BrandMode = 'AZZTEC' | 'WORKMATE';
export const BRAND_MODE: BrandMode = 'AZZTEC';                     // OD-53
export type IconName = 'event_note' | 'event_available' | /* … the 22 of §2.3 */;
export type ModuleButton = { name: string; key: string; label: string; icon: IconName; colour: string;
  labelBasis: number; underline: boolean; live: boolean };
export const MODULE_BUTTONS: ReadonlyArray<ModuleButton>;           // §2.2, six rows; Plannex live
export type MenuGroup = { name: string; label: string; pipes: string };
export const MENU_GROUPS: ReadonlyArray<MenuGroup>;                 // §2.2; the pipe strings byte-equal
export type RailItem = { name: string; label: string; icon: IconName; colour: string; activeColour: string;
  keys: ReadonlyArray<string>; gate: 'visualx' | null; dividerAfter: boolean };
export const RAIL_ITEMS: ReadonlyArray<RailItem>;                   // §2.3, thirteen rows
export const PRINT_ITEM;                                            // MenuItem_Print · Print · print · #AAAAAA
export function menuActive(pipes: string, key: string): boolean;    // oracle: indexOf('|' + key + '|') >= 0
export function menuUnderline(on: boolean): string;                 // '2px solid #EBC452' | '2px solid transparent'
export function underline(colour: string, on: boolean): string;     // '2px solid <c>'     | '2px solid transparent'
export function railBorder(colour: string, on: boolean): string;    // '4px solid <c>'     | '4px solid transparent'
export function gateOpen(gate: RailItem['gate']): boolean;          // false for 'visualx' until rights exist (OD-52)
export function activeKeyFor(pathname: string): string;             // '/planner' (a trailing '/' stripped) -> 'plannex', else ''
export function printTarget(pageKey: string): 'POPrintPopup' | 'WOPrintPopup' | 'browser';  // the dispatcher, trim + lower
export function inertTitle(what: string): string;                   // `arrives with ${what} (OD-51)`
export const LOGOUT_TITLE = 'arrives with sign-in (OD-12)';
export const TIPS_TITLE = 'arrives with tips (item 33)';
```

`inertTitle` is called with the label (`Schedulex`, `WO Maint`, …), with `'the Application menu'` and its two siblings, or with `'the Hub'` for the logo. A later module slice lights its own entry by adding one row to `activeKeyFor`'s table and flipping `live`.

### 3.2 `features/shell/icons.tsx` 1.0.0 (card 3)

`MATERIAL: Readonly<Record<IconName, ReadonlyArray<string>>>` — each glyph's `<path d>` list **copied from E3's library by script, never typed** (all 22 are paths-only, asserted at generation; `handyman`, `insights` and `receipt_long` carry two paths). `Glyph({ paths, colour, px })` renders `<svg viewBox="0 0 24 24" width={px} height={px} fill={colour} aria-hidden="true">` with one `<path>` per string. `AZZTEC_LOGO_URI` is the view's data URI, byte-equal (16,706 characters, §2.2 row 2). `LOGOUT` is the Material baseline `logout` path, **typed** (E5a did not arrive) and flagged in the header — the oracle's `<img>` at 14×14 in `#1F1F1F` becomes a `Glyph` in the same colour and size. The header records that the glyphs are Google's Material Icons (Apache 2.0).

### 3.3 `features/shell/HeaderToolbar.tsx` 1.0.0 (card 4)

Props-driven, no router (the `PlannerView` precedent): `{ activeKey, dateText, timeText, onPlannex, onFullscreen }` — no `brandMode` prop, because WORKMATE mode is cut (OD-53) and a prop that selects an unbuilt branch is a promise. One element per oracle component, in §2.2 order, each carrying `data-name="<meta.name>"` so DevTools, the screenshot and a later Playwright spec map 1:1; the module buttons and rail items also carry `data-active` for the tests and a later Playwright spec. An element whose oracle `display` / `visible` is false on this session is not rendered: `WorkmateLogo`, `AMMSSpine`, `lblBrandName` (the WORKMATE pair); `VXSearchPill` and `userCoord` per OD-52. Plannex: `role="link"`, `tabIndex={0}`, click or Enter → `onPlannex()`. `fsBtn` → `onFullscreen()` (OD-51). Every other clickable: `aria-disabled="true"`, its `title` from §3.1, class `inert` (`cursor: default`), no handler — and **not** the `disabled` attribute, which suppresses the hover title in Chrome. `TipsToggle` draws its no-prefs state (on). The logout square draws the `LOGOUT` glyph at 14 px in `#1F1F1F` on white. Inline `style` only where the oracle binds — the underline strings — and nowhere else.

### 3.4 `features/shell/SideMenu.tsx` 1.0.0 (card 6)

`{ activeKey, onPrint }`. `NavContainer` with `RAIL_ITEMS` filtered by `gateOpen`, `Divider1` after Home; `BottomContainer` with `Divider2` and Print. Inline `borderLeft: railBorder(activeColour, keys.includes(activeKey))`. Print → `onPrint()`; every other item inert as in §3.3.

### 3.5 `features/shell/AppShell.tsx` 1.0.0 (card 8)

`{ pathname, onPlannex, children }`. `activeKey = activeKeyFor(pathname)`. The clock: state from `headerClock()`, a `setInterval` of 1000 ms in an effect **with the clear in its cleanup** — StrictMode mounts twice in dev (Landmines §C). Fullscreen: `document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen()`, the promises voided. Print: when `printTarget(activeKey) === 'browser'`, `window.print()`; the two popup targets do nothing — their pages do not exist here. Markup: `div.wm-shell` → `HeaderToolbar` · `SideMenu` · `main.wm-shell-main` holding the children; imports `./shell.css`.

### 3.6 `features/shell/shell.css` 1.0.0 (card 10)

Everything scoped under `.wm-shell`, so the CTA page and Tailwind's preflight are untouched outside it; ASCII only; every declaration carries its oracle value from §2.2 / §2.3, including both wordmark gradients, the five-layer text shadow and the drop-shadow filter. Layout: `.wm-shell{height:100vh;display:grid;grid-template-rows:50px minmax(0,1fr);grid-template-columns:50px minmax(0,1fr);grid-template-areas:"hdr hdr" "rail main"}` — the header owns the corner, confirmed by the page config's `cornerPriority: top-bottom` and by the screenshot (E4/E6). The header cell gets `overflow:hidden`, so its nowrap row clips at a narrow window instead of scrolling the page. `.wm-shell-main{grid-area:main;min-width:0;min-height:0;overflow:hidden}`. `font-family` is the planner's stack (font sizes deferred by decision); the two clock labels are Verdana bold (`Text/SubHeader`). No brand-class rule and no hover rule exist in the project stylesheet, so none is added (E4).

### 3.7 `routes/__root.tsx` → 1.0.0 (card 11)

The first version we own; the version lives in the header comment, and `Route` stays the only export. **The diff is written against E2's paste.** Its shape: a local `ShellLayout` — `pathname` from `useRouterState({ select: (s) => s.location.pathname })`, `onPlannex = () => void navigate({ to: '/planner', search: validateSearch({}) })` — wrapping `<Outlet />`. Everything the CLI put in the file (the stylesheet import, the devtools) stays where it is.

### 3.8 `features/planner/planner.css` 1.1.1 → 1.1.2 (card 12)

Line 51: `height:100vh` → `height:100%`, and `position:relative` added (OD-54). Line 207: `.ovl` `position:fixed` → `position:absolute` (OD-54). Nothing else. If OD-54 is declined, only line 51's height changes.

### 3.9 `lib/dates.ts` 1.1.0 → 1.2.0 (card 13)

`HEADER_DATE = 'MMM d'` and `HEADER_TIME = 'HH:mm:ss'` — the oracle's own patterns, whose tokens date-fns reads the way Java does. `headerDate(d)`, `headerTime(d)`, and `headerClock(): { date: string; time: string }` built from **one** `new Date()` read, so the pair can never straddle midnight. E6 shows `Sep 16`, so `headerDate` is plain date-fns `en-US` — pinned by `dates.test.ts` 1.2.0.

## 4. Traps

1. Card 11 from memory — no. E2 first; the CLI's file is read before it is replaced.
2. Glyphs from memory, from a CDN, or from lucide — no. E3's file, verbatim; nothing is fetched at runtime (plant networks).
3. jsdom returns colours in `rgb()` form — assert that form, never the hex (Landmines §C, S1i). The tests assert the **longhand** (`style.borderBottomColor`, `style.borderLeftColor`) set through the shorthand; if jsdom 30 reports the longhand differently, that is a test fix mid-slice (the S1g `Monday` precedent), not a component change — `data-active` is the second assertion on every lit element for exactly that reason.
4. jsdom has no Fullscreen API, and `window.print` only logs "not implemented": define `requestFullscreen` / `exitFullscreen` / `fullscreenElement` on the test document, and `vi.spyOn(window, 'print').mockImplementation(() => {})`.
5. Clock tests: `vi.useFakeTimers()` with `vi.setSystemTime(new Date(2026, 8, 16, 14, 3, 9))` — the local-time constructor, never an ISO string (UTC midnight, Landmines §C) — and `vi.useRealTimers()` in `afterEach`.
6. The root route is never code-split. Import only `validateSearch` from `PlannerView` (already in the main chunk through `routes/planner.tsx`); the smoke lists `dist/assets` before and after, and the `planner-*.js` chunk must still exist.
7. `height:100%` needs a definite parent: the grid cell, with `min-height:0`. A page-level scrollbar at the smoke means the chain broke.
8. Positioning `.wm-planner` changes the containing block of every absolutely positioned descendant that has no positioned ancestor. Listed before card 12 was cut: `.loading` (164) sits in `.grid-wrap{position:relative}` (81), `.wsel .menu` (181) in `.wsel{position:relative}` (180) — only `.ovl` (207) moves. Card 12's diff is 20 lines, all in the header comment but the two rules.
9. Keep `2px solid transparent` and `4px solid transparent` when inactive — the oracle reserves the border so nothing shifts when an item lights. Reports has **no** border and sits 2 px shorter; Print's border is 3 px, not 4. Parity — fix neither.
10. Insights lights in `#DEBF7A`, not `#E91E63`; Invoice lights for two keys; Application does not light on the planner.
11. The data URI is one 16,706-character line; Prettier never wraps a string — don't split it.
12. `@tanstack/eslint-config`: `**`, never `Math.pow`; `?? ''`, never `!`; no unnecessary conditions; no shadowing; import order as `PlannerView.tsx`.
13. The preflight in `styles.css` sets `img, svg { display: block }` and zeroes borders — `fsBtn` and `logoutBtn` need their white fill and 1 px border spelled out, and nothing may rely on inline images.
14. `1.7vh` is viewport-relative on purpose; on a tall window the time can overflow its 25 px row — `overflow: visible`, parity.
15. The audit counted eight header message handlers; the view has **seven**. §2.2 is the count.

## 5. Test plan — predicted per file

| File | Cases | What |
|---|---|---|
| `features/shell/rules.test.ts` (card 2) | 12 | the six buttons, the three pipe strings and the thirteen rail items against §2.2 / §2.3 · the `underline` / `menuUnderline` / `railBorder` strings · `menuActive` (Application on `pmx` and `schedulex`, not on `plannex`; `''` lights nothing) · Insights' colour · Invoice's two keys · `activeKeyFor` (`/planner`, `/planner/`, `/`, `/plannerx`) · `printTarget` (PO, the four WO keys, `plannex`, `''`) · `gateOpen` · `BRAND_MODE` · `inertTitle` · every `IconName` in the tables has a glyph |
| `features/shell/HeaderToolbar.test.tsx` (card 5) | 8 | `data-name` order · the AZZTEC brand (logo `src` byte-equal, "Azztec", no Workmate parts) · on `plannex` the Plannex underline reads `rgb(76, 175, 80)`, the others transparent, Reports borderless · click and Enter on Plannex call `onPlannex` once each · inert controls call nothing and carry `aria-disabled` and their titles · no pill, no `userCoord`; tips cyan with its title; logout with its title · the clock texts · `fsBtn` calls `onFullscreen` |
| `features/shell/SideMenu.test.tsx` (card 7) | 6 | twelve items and Print in order, the dividers placed, no VisualX · `plannex` lights nothing · `insights` lights `rgb(222, 191, 122)`, `invoicex` lights Invoice · inert clicks and titles · Print calls `onPrint` · glyph fills (Home, Parts) |
| `features/shell/AppShell.test.tsx` (card 9) | 6 | the header, the rail and the children in `main` · `/planner` lights Plannex · the clock ticks on 1000 ms and no timer is left after unmount · Print calls `window.print` on `/planner` · fullscreen enters and exits · Plannex reaches `onPlannex` |
| `lib/dates.test.ts` 1.2.0 (card 14) | +3 | `headerDate` (`Sep 16`; `Oct 1` unpadded; `Dec 25`) · `headerClock` for now on fake timers · `headerClock` from one read across midnight |

**Predicted: frontend `205 passed` in `15` files** (170 + 12 + 8 + 6 + 6 + 3), exit 0 — read against the cards' own `it()` counts before the run. **Backend `194 passed, 2 skipped`**, exit 0 — unchanged, re-run because `dist/` changes (Ways of Working §6). Both bare, both read from the run; a miss against this table is investigated before the commit, never after.

## 6. Open decisions — 🤙 required

| ID | Question | Proposal |
|---|---|---|
| **OD-50** | What the shell is | **A port, on the oracle's own CSS.** `features/shell/` as §3; `data-name` is the oracle's `meta.name`; styles scoped under `.wm-shell`; mounted in `__root.tsx` so every route carries it — the shared-dock behaviour, which E4 confirms. No shadcn, lucide or Tailwind classes, no `pnpm add` (OD-27 / OD-31 — the first non-port component is still item 33). Glyphs from the gateway's own library, inline (the S1f lock/pin precedent). Both views live in `docs/reference/`. |
| **OD-51** | Controls that cannot work yet | **At rest, pixel parity; on hover, the truth.** Plannex navigates. Every other control draws as the oracle draws it and does nothing: `cursor: default`, `aria-disabled`, `title="arrives with … (OD-51)"` (the OD-5 / OD-34 precedent). **Also live, recommended, because no backend is involved:** the clock; `fsBtn` (the Fullscreen API — KT's "Toggle Page"); rail Print (`window.print()` — exactly what KT's dispatcher does on the planner page). Strike those two for navigation-only. The alternative — keep `cursor: pointer` on dead controls for hover parity — makes the chrome promise what it cannot do. |
| **OD-52** | Gated items, with no identity or rights yet (OD-2 / OD-12) | **Hidden where showing them would invent a grant; drawn inert where the oracle always draws them.** VisualX and the search pill: not rendered — `allowed()` cannot be evaluated, and both thumbnails show them hidden. `userBtn`: not rendered — nobody holds `Administrator` at KPP here. Logout: drawn, inert, `arrives with sign-in (OD-12)`. The tips toggle: drawn in its no-prefs default (on, cyan), inert, `arrives with tips (item 33)` — a click that flipped its colour would claim a saved preference that is not saved. |
| **OD-53** | Brand mode | **A constant, `AZZTEC`** — what the attached design shows and what the product is called. KT's truth is `System_Configuration` read through `workmate.brand.get_mode()` with a `WORKMATE` fallback; porting that read is its own slice, with the script source and both databases' rows pasted first. WORKMATE rendering is **cut** — E5b did not arrive — and carried as an item, never faked with a missing image. |
| **OD-54** | The day dialog inside a shell | **Contained, as the iframe contained it:** `.wm-planner{position:relative}` and `.ovl{position:absolute}` — the dim covers the planner, and the header and rail stay live as they do at KT. Trap 8 is the precondition. The alternative — leave it `fixed` — dims the chrome as well, and is one line shorter. |

## 7. Smoke

Nothing here touches a database or a backend source file. One browser tab. Wait for each prompt before the next block.

**0 — before the drop.** `cd C:\dev\workmate-saas\web; Get-ChildItem dist\assets -Filter *.js | Select-Object Name, Length` — kept for trap 6.

**1 — the drop** (after card 11 exists — it ships once `__root.tsx` is pasted), in the S1j shape: every source `Test-Path`ed in Downloads and printed first; each copied to its §1 target (cards 15/16 into `docs\reference\`, this spec into `docs\`); every target `Test-Path`ed by exact name and `Get-Item … | Format-List Name, Length, LastWriteTime` inside a loop; then, mechanically, the header `Version:` line against the `VERSION` constant on cards 1, 3, 4, 6, 8 and 13 — before anything runs.

**2 — frontend.** `pnpm lint` → silent · `pnpm test` → **205 passed in 15 files**, `$LASTEXITCODE` 0 · `pnpm build` → exit 0 · the `dist\assets` list again: `planner-*.js` still its own chunk. No `pnpm gen:api` — the contract did not move.

**3 — backend with the new `dist/`.** `cd ..\backend; uv run pytest` → **194 passed, 2 skipped**, exit 0.

**4 — boot and look.** The backend in its own window via `Start-Process` (the boot lines; `/health` says `frontend: "built"`); then `http://localhost:8000/planner` and `http://localhost:8000/`:

- the header — gradient, Azztec logo, gold wordmark, three menus, separator, six buttons, **Plannex underlined green on `/planner` and nothing underlined on `/`**, the tips circle, the fullscreen and logout squares, the date, and the time ticking;
- the rail — twelve items, Print at the foot, **nothing lit on the planner** (as at KT);
- the planner fills the rest with **no page scrollbar**, at month / today; `Week`, `‹ ›` and the day dialog behave as before, and the dialog dims only the planner (OD-54);
- from `/`, Plannex lands on `/planner?mode=month&anchor=<today>`; every inert control does nothing and shows its title on hover; fullscreen toggles; Print opens the browser's print dialog;
- **held next to E6 at the same window size:** every difference is either a §2.4 prop confirmed, a patch before the tag (a new version, never a knowingly wrong commit), or recorded in the log with its reason.

**5 — commit.** `git status --short` predicts **17 paths — 13 new, 4 modified** (the ten `features/shell/` files, the two reference views, this spec; `__root.tsx`, `planner.css`, `dates.ts`, `dates.test.ts`) → `git add -A` → `git commit -m "S1k shell - HeaderToolbar v16.47 + SideMenu v4.20 port"` → tag **`s1k-shell-1.0.0`**, or whatever version actually shipped.

## 8. Acceptance

- Fourteen cards and two reference copies; nothing else in the tree changes (17 staged paths).
- The header and the rail match E6 at rest; Plannex navigates; every inert control says why on hover; nothing calls the backend.
- Frontend 205 in 15, backend 194 / 2 — both bare, both read, both exit 0.
- The planner fills the shell with no page scroll; its behaviour and its tests are unchanged; its chunk is still split.
- No `pnpm add`, no contract change, no database touched.

## 9. Consequences

### 9.1 Doc corrections for the next compiled set

- **Architecture §5**: `features/shell/` in the tree; `routes/__root.tsx` owned and versioned (1.0.0, in project knowledge); `planner.css` 1.1.2; `docs/reference/` gains the two views. §3.2 Styling row: the shell is the second port on the oracle's literal CSS (OD-50), and shadcn still waits for item 33. §6 step 0: every page renders inside the shell.
- **Port Spec §6**: the S1k row between S1j and S2; §7: the planner renders in the shell's main cell with its day dialog contained (OD-54); §9: OD-50…OD-54.
- **Landmines §C**: the root route is never code-split; jsdom has no Fullscreen API and no working `window.print`; the Perspective props that map to nothing (§2.4, as E6 settles them).
- **Index**: §1 state, §3.4b the new files, §3.7 the two views, §6 next = the S2 audit.

### 9.2 What this unblocks

Every later module port renders inside a finished shell and lights itself with one table row. S2's move work happens on a page the user already navigates to.

### 9.3 Candidate open items — raised in the log, not here

- WORKMATE mode — cut, E5b did not arrive (OD-53); and the gateway's `logout_24dp_1F1F1F.svg` + its own `material.svg` for a byte-exact glyph pass (E3/E5a).
- The brand read from `System_Configuration` — the `workmate.brand` source and both databases' rows first.
- Rights for VisualX and the search pill (the `workmate.security.allowed` source) and a role for the Users button — alongside D-5 / OD-2.
- The three menu dropdowns — their popup views exported first.
- Into item 34's carry-back list for KT: the unmapped `meta.classes` and `justifyContent` props; the three empty onClick scripts (Invoicex, Labour, PM Wizard); SideMenu v4.20's comment naming a `pathKey` watcher that HeaderToolbar v16.47 does not contain; the stale `"partsetup"` default saved in SideMenu's view custom.

**Numbering:** the OD series moves to **54**; the open-item series is at 45 (log 09-15) until the log raises any. Always carry the `OD-` prefix.

## 10. Changelog

- 1.0.1 (2026-09-16) Reissued the same day, before the build. ODs renumbered OD-48…OD-52 → **OD-50…OD-54** (OD-48/49 were signed for weekno on 09-15 — the numbering hazard); baseline corrected to log 09-15 (HEAD `5a4802a`, 194 / 2); Status records the decisions as taken on "go" — delegated, not signed. §2.6 rewritten from what arrived: the icon library (react-icons geometry, not the gateway file), the page config (header owns the corner), `Text/SubHeader` (Verdana bold), the stylesheet (no hover, no brand classes), the screenshot (`Sep 16`, activePage was `home`), E5a/E5b absent. §3.2 the typed `logout` path flagged; §3.3 no `brandMode` prop, no `disabled` attribute, `data-active`; §3.6 the corner confirmed; §3.9 `Sep` pinned; §4 traps 3 and 8 resolved; §5 the dates cases; §6 OD-53 WORKMATE cut; §9.3 the two missing gateway files.
- 1.0.0 (2026-09-16) Initial. From the shell audit (this session): both views read in full and delivered as byte copies (cards 15/16); the collisions read from the PK cards; OD-48…OD-52 proposed (as then numbered); E1–E6 owed, the ★ ones blocking the build.
