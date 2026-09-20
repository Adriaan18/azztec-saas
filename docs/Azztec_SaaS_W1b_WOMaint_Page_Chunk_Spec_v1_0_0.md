# Azztec SaaS — W1b WOMaint Page Chunk Spec

**File:** Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-20 · **Author:** Adriaan
**Status:** **Draft for 🤙.** OD-72…OD-79 in §6 are unsigned. Nothing is built until this file is signed.
**Target path:** `docs/Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md` (+ project knowledge: add)
**Parent:** `Azztec_SaaS_W1a_WOMaint_Read_Api_Chunk_Spec_v1_0_1.md` §1 "Not in this slice" (OD-62) · `Azztec_SaaS_WOMaint_Audit_Brief_v1_0_0.md` §5 (the W1 row) · Handover Brief 6.1.0 §4 · Index 1.10.0 §6 step 5 · log 09-19 1.2.0 §9 items 53, 54. **Closes OD-5 in full** — the planner's `Open in WO Maintenance` goes live on `/workorders/$id`.
**Source of truth:** the 2026-09-19 Designer exports already in PK (`WOMaint_2026-09-19_view.json` v16.28.3, `WOStatus`, `WOProgress`, `WONumBadge`, `CompleteWithinSeg`), read component by component 2026-09-20 (§2.1); **two new reference cards cut with this spec** — `Workmate_Stylesheet_2026-09-20_v2_69.css` (141,544 B, byte copy, `lastModification` Adriaan 2026-09-03T03:58:52Z) and `PONumBadge_2026-09-20_view.json` (`PONumBadge_v1_2_0`). **The live screens:** seven screenshots pasted 2026-09-20 (Work Order/Details, Activity, Linked WO, Event History, Purchase Orders, Attachments, the date-range popup) — the pixel reference, into `docs/reference/` when the slice is cut. Read from the PK cards, not remembered: `shell/rules.ts` 1.0.0, `shell/icons.tsx` 1.0.0, `shell/AppShell.tsx` 1.0.0, `planner/SelectedWOCard.tsx` 1.0.0, `planner/PlannerView.tsx` 1.1.0, `planner/planner.css` 1.1.2, `routes/planner.tsx` 1.0.1, `lib/dates.ts` 1.2.0. **The generated client read on the box 2026-09-20**, not assumed (§2.4).
**Writes:** nothing. No backend file, no database row, no migration, no `pnpm add`, no `uv add`. `web/src` only, plus `docs/reference/`. **Contract change: none** — `openapi_0_5_0.json` and the generated client are untouched; `pnpm gen:api` is not run.
**Signed decisions in force:** OD-5 (the named route `/workorders/$id`), OD-19 (the conditional SPA mount), OD-23 (a window cap belongs in the hook, not the API), OD-27 (a port ships the oracle's CSS), OD-29 (the URL carries what a link must be able to name), OD-30 (`signal` forwarded, the server runs to completion), OD-31 (no shadcn in a port), OD-34 (chrome says only what is true), OD-39/OD-40/OD-41 (the badge paint pattern), OD-50…OD-54 (the shell), OD-63…OD-71 (the read API as shipped, W1a). Landmines §C throughout: TS 6's narrower `lib.dom`, no `setupFiles`/`globals`, a route file exports `Route` only, `.chip{flex:none}`, one browser tab, the `[Client]` prefix.

---

## 1. Scope — the Work Order tab, end to end, and nothing below the sub-tab strip

The oracle's **left list + right record** for the `Work Order` tab only: the list panel with its four type chips and record count, the filter row, the header card with the status and progress rows, the Complete-within segment, Schedule, Assignment, Resources, and the **Details + Notes** sub-tab. The route lands it at `/workorders` and `/workorders/$id`, `MenuItem_WOMaint` lights, and the planner's disabled `Open` button becomes the first link into the module.

**Not in this slice — W1c (OD-72):** the four other main tabs (Activity is not W1c either — its own audit), that is **Query/Notes · Linked WO · WO Event History**, plus the **Purchase Orders** sub-tab and the `PONumBadge` port it needs. Their four routes are live and tagged; W1c is presentational and cheap because of it.
**Not in W1 at all:** every write (W2/W3), delete/clone/link (W4), `refs` (W3, OD-66), Activity (`WOActivityPanel`), Attachments, Procedures, Parts, Labour, the AI embed, tips ⓘ (item 33), the toast bar, the `Summary` toggle, `UserSelector`, `ResourceManager_popup`, `WODateRangePopup` (screenshot 7 — it opens from `rangeSeg` in edit mode, so it is W3's).

| # | Deliverable | Target path | Version | Change |
|---|---|---|---|---|
| 1 | `Azztec_SaaS_web_workorders_rules_v1_0_0.ts` | `web/src/features/workorders/rules.ts` | **new** | pure — the badge parser and paint, the card tables, the labels (§3.2) |
| 2 | `Azztec_SaaS_web_workorders_rules_test_v1_0_0.ts` | `…/rules.test.ts` | **new** | pair of 1, zero DOM |
| 3 | `Azztec_SaaS_web_workorders_css_v1_0_0.css` | `…/wo.css` | **new** | the oracle's CSS scoped `.wm-wo` + the token block (§3.3) |
| 4 | `Azztec_SaaS_web_workorders_icons_v1_0_0.tsx` | `…/icons.tsx` | **new** | the WOMaint glyph set, copied by script (§3.4) |
| 5 | `Azztec_SaaS_web_workorders_symbols_v1_0_0.tsx` | `…/symbols.tsx` | **new** | `WoNumBadge`, `WoStatusRow`, `WoProgressRow`, `CompleteWithinSeg` (§3.5) |
| 6 | `Azztec_SaaS_web_workorders_symbols_test_v1_0_0.tsx` | `…/symbols.test.tsx` | **new** | pair of 5 |
| 7 | `Azztec_SaaS_web_workorders_useWorkorders_v1_0_0.ts` | `…/useWorkorders.ts` | **new** | the two hooks over the generated client (§3.6) |
| 8 | `Azztec_SaaS_web_workorders_useWorkorders_test_v1_0_0.tsx` | `…/useWorkorders.test.tsx` | **new** | pair of 7 — the wire, stubbed `fetch` |
| 9 | `Azztec_SaaS_web_workorders_WoListPanel_v1_0_0.tsx` | `…/WoListPanel.tsx` | **new** | title, type chips, table, footer (§3.7) |
| 10 | `Azztec_SaaS_web_workorders_WoListPanel_test_v1_0_0.tsx` | `…/WoListPanel.test.tsx` | **new** | pair of 9 |
| 11 | `Azztec_SaaS_web_workorders_WoFiltersRow_v1_0_0.tsx` | `…/WoFiltersRow.tsx` | **new** | search, clear, the two mode chips, the inert actions (§3.8) |
| 12 | `Azztec_SaaS_web_workorders_WoFiltersRow_test_v1_0_0.tsx` | `…/WoFiltersRow.test.tsx` | **new** | pair of 11 |
| 13 | `Azztec_SaaS_web_workorders_WoRecordCard_v1_0_0.tsx` | `…/WoRecordCard.tsx` | **new** | header card + Schedule + Assignment + Resources (§3.9) |
| 14 | `Azztec_SaaS_web_workorders_WoRecordCard_test_v1_0_0.tsx` | `…/WoRecordCard.test.tsx` | **new** | pair of 13 |
| 15 | `Azztec_SaaS_web_workorders_WoDetailsTab_v1_0_0.tsx` | `…/WoDetailsTab.tsx` | **new** | the three columns, the six stamp rows, Notes (§3.10) |
| 16 | `Azztec_SaaS_web_workorders_WoDetailsTab_test_v1_0_0.tsx` | `…/WoDetailsTab.test.tsx` | **new** | pair of 15 |
| 17 | `Azztec_SaaS_web_workorders_WoMaintView_v1_0_0.tsx` | `…/WoMaintView.tsx` | **new** | composition, props-driven, the tab strips (§3.11) |
| 18 | `Azztec_SaaS_web_workorders_WoMaintView_test_v1_0_0.tsx` | `…/WoMaintView.test.tsx` | **new** | pair of 17 — the one file that stubs `fetch` end to end |
| 19 | `Azztec_SaaS_web_routes_workorders_v1_0_0.tsx` | `web/src/routes/workorders.tsx` | **new** | list route, search params (§3.12); **header version only** |
| 20 | `Azztec_SaaS_web_routes_workorders_id_v1_0_0.tsx` | `web/src/routes/workorders.$id.tsx` | **new** | record route; **header version only** |
| 21 | `Azztec_SaaS_web_shell_rules_v1_1_0.ts` | `web/src/features/shell/rules.ts` | 1.0.0 → **1.1.0** | `ACTIVE_KEY_BY_PATH` gains the two `/workorders` rows (§3.13) |
| 22 | `Azztec_SaaS_web_shell_rules_test_v1_0_2.ts` | `…/shell/rules.test.ts` | 1.0.1 → **1.0.2** | the new rows |
| 23 | `Azztec_SaaS_web_planner_SelectedWOCard_v1_1_0.tsx` | `web/src/features/planner/SelectedWOCard.tsx` | 1.0.0 → **1.1.0** | `Open` enabled → `/workorders/$id` — **OD-5 closes** |
| 24 | `Azztec_SaaS_web_planner_SelectedWOCard_test_v1_1_0.tsx` | `…/planner/SelectedWOCard.test.tsx` | 1.0.1 → **1.1.0** | the link, not the disabled attribute |
| — | `Workmate_Stylesheet_2026-09-20_v2_69.css` | `docs/reference/` | **new** | byte copy, cut with this spec |
| — | `PONumBadge_2026-09-20_view.json` | `docs/reference/` | **new** | byte copy, cut with this spec (W1c uses it) |
| — | the seven live screenshots | `docs/reference/` | **new** | dropped in the slice commit, named `WOMaint_live_2026-09-20_<n>.png` |

**Twenty-four cards is above the usual slice** (S1k was 17 files, W1a 11). The alternative is a third slice and one more session against a ~09-30 install, with auth, W2, W3, S2b, S2c, D1b and deploy still to come. Called out here so the gate decides it, not the build.

**Untouched:** every backend file, every database, `docs/api/openapi_0_5_0.json`, `web/src/api/client/**`, `routeTree.gen.ts` (regenerated by the plugin, committed), `package.json`, both lock files, every other `features/planner/*` file, `features/shell/{icons,HeaderToolbar,SideMenu,AppShell,shell.css}`.

## 2. Evidence

### 2.1 The oracle, read 2026-09-20 from the PK exports

`WOMaint_v16_28_3` is **281 components**: `MainContent` → `WOListPanel` (basis 400 px, `width`/`minWidth` **450 px**, `1px solid #C8CECE`, `borderRight 2px solid #B0B0B0`, radius 8) + `DetailPanel` (grow 1, gap 10). `MainContent` pads `10px 16px 16px 16px`, gap 10, `overflow: hidden`.

- **`WOListHeader`** — `linear-gradient(180deg,#242E30 0%,#2F3B3D 100%)`, `borderBottom 2px solid #EBC452`, radius `8px 8px 0 0`, minHeight 40, pad `0 12px`. `WOListTitle` is an **expression, not a constant**: `M` → `Planned Maintenance`, `''` → `Work Orders + PM`, else `Work Orders`; white, 13 px bold, letter-spacing 0.5.
- **`TypeToggle`** — four labels, gap 4, `marginLeft:auto`. Each: border `1px solid rgba(222,191,122,0.45)`, radius 10, 11 px/600, pad `2px 9px`; **active `#DEBF7A` on `#1A2224`, inactive `rgba(222,191,122,0.08)` on `#C0C8CA`**. WO → `N` · CP → `CP` · PM → `M` · All → `''`. Seed `'N'`.
- **`WOListTable`** — `wm-compact-table`, cells `fontSize 10, height 42px, padding 6px 10px`, pager `activeOption: 100`. Columns: `WO_ID` hidden · **`WO_IdStyled` 130 px rendered through `WONumBadge`** · `WO_Title` 200 · `Asset_ID` 90 · `Location_Id` 100. Headers 10 px/700.
- **`WOListFooter`** — `'No of Records: ' + woListRecordCount`, white, radius `0 0 8px 8px`, `borderTop 1.5px solid #DEBF7A`, `#5D6E71`, 10 px, line-height 26, pad-left 12.
- **`FilterRow`** — `#F0F0F0`, `borderBottom 1.5px solid #DEBF7A`, gap 4, pad `4px 12px`. `SearchBox` basis 240, `#F7FAFC` on `1px solid #E2E8F0`, radius 8, 28 px tall, placeholder **`Search work orders...`**. `FilterChip_Closed` / `FilterChip_Archive`: radius 4, 10 px, letter-spacing 0.3, pad `3px 7px`, `transition all .3s ease`; **lit** = `rgba(var(--wo-rgb-closed),1.0)` / `rgba(93,110,113,1.0)` with a matching `0 2px 10px …,0.55` glow, **unlit** = the same colour at `0.10` and `boxShadow:none`. Archive's colour is a literal, not a token.
- **`MainTabContainer`** — `#F5F5F5`, `1px solid #C8CECE`, radius 8, and the house gold shadow `0 4px 5px 0 rgba(235,196,82,.14), 0 1px 10px 0 rgba(235,196,82,.12), 0 2px 4px -1px rgba(235,196,82,.20)` — the same shadow on every card in the page. `TabHeaderRow` `#FAFAFA`, `borderBottom 1px solid #C8CECE`, `overflowX:auto`. **The tabs are hand-built `ia.input.button`s, not a tab container**: 12 px/600, pad `6px 14px`; active `borderBottom 2px solid #EBC452` + `#004063`, inactive `2px solid transparent` + `#8A9698`. Tab_0 `Work Order` · 1 `Activity` · 2 `Query/Notes` · 3 **`Linked WO` → `Linked WO (+)` when `linkedFamilyCount > 1`** · 4 `WO Event History`. Sub-tabs are the same at 11 px/600, pad `5px 12px`, **in view order 0 Details · 5 Purchase Orders · 1 Attachments · 2 Procedures · 3 Parts · 4 Labour**. Each tab body is `display:flex|none` on the active index.
- **`WOHeaderCard`** — white, `1px solid #C8CECE`, radius 8, the gold shadow, minHeight 130, pad `14px 18px`. Left: `Work Order ID :` + id + title; `Asset :` + dropdown + title label; `Location :` + dropdown + the hierarchy label. Right (`HeaderSymbolsRight`, gap 3): `embWOProgress` (minWidth **428**) above `embWOStatus` (minWidth **572**), each minHeight 58, each hidden when its value is empty/0.
- **`ScheduleCard`** / **`AssignmentCard`** — `flex: 0.9 0 0px`, white, the same border/radius/shadow, pad `8px 12px`. `AllResourcesCard` `flex: 1`. `ScheduleAssignmentRow` wraps, gap 6. Schedule rows in order: the segment, Start Date, End Date, Logged Date, Duration (hrs), Est. Cost, Down Time, Week No. Assignment: Person Resp., Charge To, Responsibility, Resp. Users + a `Manage` button. `lblAllResourcesValue` basis 538, width 80, 10 px bold `#242E30`, right-aligned, ellipsis.
- **`tblAllResources`** — `wm-compact-table`, pager off. Type 64 · Item 35 · Plan Qty 70 · Plan $ 84 · Act Qty 66 · Act $ 84 · Diff $ 84, the last five right-aligned `render:number`.
- **`DetailsSubTab`** — `ThreeColRow`, wrap, gap 20. **Left:** WO Group, Reason, Fault, Dept. (+desc), Class (+desc), Charge To (+desc), Responsibility (+desc). **Middle:** WOC 1/2/3, Company, Ref. 1, Ref. 2. **Right:** Created By, Ack. By, Approved By, Closed By, Cancelled By, Last Save — each a user field plus a date field. `NotesSection` below, `marginTop 8`, `txtNotes` `1px solid #C8CECE`, radius 4, 11 px, minHeight 60, `width:100%`.

### 2.2 The four symbols, read in full

- **`WOStatus` has EIGHT cards — R H P K A V C D. There is no Deferred card.** Each 68 × 58, radius 8: lit = `var(--wo-color-<name>)` + a 2 px solid accent border, unlit = `transparent` + `1px solid #8A9698`; the icon and label go `#FFF`/bold when lit, `#5D6E71`/normal when not — **except `R`, whose lit text and icon are `#000`** (its `--wo-color-request` `#FFC107` is too light for white). Icons in order: `warning` · `assignment` · `schedule` · `thumb_up` · `check_circle` · `play_circle_filled` · `cancel` · `block`, 20 px. Labels: Request · Planned · Pending · Ack'd · Approved · Active · Closed · Cancel, 10 px, `paddingBottom 4`. Accent borders: `#D4A006 · #11808F · #3A8BBF · #5A349E · #084AAB · #1E8236 · #B02A37 · #565E64`.
  **The W1a spec §2.1 and log 09-19 §4 both say "nine cards R H P K A V C D F". The export says eight.** `WONumBadge` does colour `F` and the stylesheet does carry `--wo-color-deferred` / `--wo-rgb-deferred`, so the badge can paint a status the card row cannot draw. RST's live table has no `F` and no `K` (spec W1a §2.4), so it does not bite today. Doc correction in §9.1; the consequence is OD-74.
- **`WOProgress` has six cards** for `Progress_Id` 1–6, same 68 × 58 geometry: lit `#3D4F52` (**`#16A34A` on the 100 % card**) + `2px solid #242E30`, unlit transparent + `1px solid #8A9698`. Each holds an inline `ia.shapes.svg` at `viewBox 0 0 24 24` — 2 elements (rect + circle) for None, 2 (rect + path) for Wait and 100 %, 3 (rect + rect + text) for 25/50/75. Labels None · Wait · 25% · 50% · 75% · 100%. Copyable by script, the S1k glyph precedent.
- **`WONumBadge_v1_3_0`** takes one pipe string `status|shortId|progressId|hasPO` and renders `parts[1]`. Static: radius 4, 11 px/600, letter-spacing 0.3, pad `3px 7px 5px 7px`, centred, `backgroundPosition 'right 3px top 3px, left bottom'`, `backgroundRepeat no-repeat,no-repeat`, **`backgroundSize '7px 7px, 100% 3px'`**. Background `rgba(var(--wo-rgb-<status>),0.16)` and text `…,0.80`, with `cancelled` at `0.08`/`0.50` as the fallback for an unknown letter. `backgroundImage` is **two layers, always both emitted** so the static two-entry size/position lists stay aligned: layer 1 a `radial-gradient` PO dot, `#0B5ED7` when `hasPO` else `transparent`; layer 2 `linear-gradient(to right, <fill> <p>%, transparent <p>%)` where `p` = `{1:0, 3:25, 4:50, 5:75, 6:100}` by progress id and `fill` = `rgba(var(--wo-rgb-<status>),0.95)`, **except progress 2 (Wait), which is `rgba(100,116,139,0.55)` at 8 %** — a muted nub deliberately unlike real progress.
- **`CompleteWithinSeg_v1_8_0`** — track `#EAECEC`, radius 8, minHeight 34, pad 3, gap 0; six labels Day · Week · Month · 3-Month · Next shut · Range with values `day week month 3month nextshut range` — **exactly `rules.SEGMENTS` from the backend, same order**. Selected: `#FFFFFF`, `boxShadow 0 1px 3px rgba(0,0,0,0.08)`, `#242E30`, weight 500. Unselected: transparent, `#5D6E71`, weight 400. Each segment radius 6, pad `6px 6px`, `transition background-color .15s, box-shadow .15s, color .15s`. `rangeSeg` opens `WODateRangePopup` — a write path, W3's.
- **`PONumBadge_v1_2_0`** (new card, W1c): same geometry as `WONumBadge` minus the background layers. Ten `--po-rgb-*` statuses P W A I R T C X Q D at `0.16`/`0.80`, `cancelled` `0.08`/`0.50` as fallback. `props.text` is `right(value, len-2)` — equivalent to splitting on the first pipe. **The second character is a flag channel, not just a separator:** `w`/`W` adds a `#0B5ED7` dot, `c`/`C` a `rgba(var(--wo-rgb-closed),1.0)` dot, and `!`/`W`/`C` add a `0 0 0 2px #DC7323` ring. W1a's repo ships a plain `status|poSid`, so no dot and no ring — correct for a read, and the flags belong to the PO module.

### 2.3 Stylesheet v2.69 — the tokens, and five classes that do nothing

The nine WO and ten PO palettes, verbatim:

```
--wo-rgb-request 255,193,7      --wo-color-request      #FFC107
--wo-rgb-planned 23,162,184     --wo-color-planned      #17A2B8
--wo-rgb-pending 93,173,226     --wo-color-pending      #5DADE2
--wo-rgb-acknowledged 111,66,193 --wo-color-acknowledged #6F42C1
--wo-rgb-approved 11,94,215     --wo-color-approved     #0B5ED7
--wo-rgb-active 40,167,69       --wo-color-active       #28A745
--wo-rgb-closed 220,53,69       --wo-color-closed       #DC3545
--wo-rgb-cancelled 108,117,125  --wo-color-cancelled    #6C757D
--wo-rgb-deferred 255,152,0     --wo-color-deferred     #FF9800
--po-rgb-pending 93,173,226 · waiting 255,128,192 · approved 111,66,193 · issued 40,167,69 · received 0,0,128
--po-rgb-part-recv 0,128,255 · completed 220,53,69 · exported 0,204,204 · rfq 255,193,7 · cancelled 108,117,125
```

Perspective renders a `props.style.classes` token as the DOM class **`psc-<name>`** — the S1k `psc-toolbar-btn` precedent, and the stylesheet's own comments say so twice ("Add the class on props.style.classes (NOT meta.classes)"). Measured across all 281 components:

| Class | on `props.style.classes` | on `meta.classes` | Live? |
|---|---|---|---|
| `wm-compact-table` | 4 | 0 | **yes** — collapses the header band to 24 px and forces 10 px/700 header text |
| `wm-input-sm` | 2 | 0 | **yes** — 11 px on the inner `<input>` of a date-time input |
| `wm-input-sm-placeholder` | 1 | 0 | **yes** — 12 px `::placeholder`, `opacity 1` |
| `wm-btn-shadow-grey` / `-blue` / `-gold` / `-forest` | 9 / 2 / 1 / 1 | 0 | **yes** — a three-state shadow each, `transition box-shadow 140ms` |
| `wm-seg-9px` | 1 | 0 | **no rule in v2.69** — item 54 |
| `wm-tabs` · `wm-tabs-sub` · `wm-panel-header` · `wm-btn-tertiary` | 0 | 1 each | **no** — `.psc-<name>` can never match a `meta.classes` token |

So **five of the twelve `wm-*` classes WOMaint asks for change nothing.** The W1a log's "eleven of the twelve have rules" is true of the stylesheet and only half the question: a rule that *exists* and a rule that *applies* are different things. It costs nothing visually — `wm-tabs`/`wm-tabs-sub` target `.ia_tabContainer__*` and WOMaint's tabs are hand-built buttons, so they could never have matched; `wm-panel-header` duplicates styling `WOListHeader` already carries inline; `wm-btn-tertiary` sits on one button that also styles itself. Every value the page actually renders is inline and is in §2.1 verbatim. Consequence: OD-76 and a carry-back item.

### 2.4 The SaaS as it stands, read on the box 2026-09-20

`web/src/api/client/` is 17 files. The six W1a operations and their types are on disk exactly as W1b will import them:

```
listWorkordersApiV1WorkordersGet · getWorkorderApiV1WorkordersWoIdGet
getEventsApiV1WorkordersWoIdEventsGet · getLinkedApiV1WorkordersWoIdLinkedGet
getQueriesApiV1WorkordersWoIdQueriesGet · getPoLinesApiV1WorkordersWoIdPosGet
WoList · WoListRow · WoRecord · SearchFilters · RespUser · Resources · ResourceRow
ProgressRow · LinkedFamily · LinkedRow · EventPage · EventRow · QueryList · QueryRow
PoList · PoLine · ApiError
```

`@tanstack/react-query.gen.ts` (14,351 B) carries the `…Options()` helpers whose `queryFn` forwards `signal` (OD-30). `shell/rules.ts` 1.0.0 line ~364: `ACTIVE_KEY_BY_PATH = [['/planner','plannex']]` and `activeKeyFor` strips one trailing slash; `MenuItem_WOMaint` already exists at `RAIL_ITEMS[4]` with `keys: ['womaint']`, `icon: 'assignment'`, `colour`/`activeColour` `#E91E63`, `gate: null`. `printTarget` already routes `workorders` → `WOPrintPopup`. `shell/icons.tsx` 1.0.0 holds 22 glyphs of which WOMaint needs **`assignment` and `search`**; thirteen are missing: `block · cancel · check_circle · clear_all · close · edit · group_add · local_printshop · play_circle_filled · save · schedule · thumb_up · warning`. Backend and frontend suites green at the open: **319 / 2** and **205 in 15 files**, both ruff gates clean, `0001 (head)`, HEAD `7f2b661`.

### 2.5 RST, as W1a measured it (not re-read — no database work in this slice)

The list's default page 76 ms · `includeClosed=2` 352 ms · `includeArchive=1` 627 ms · `includeArchive=2` **1,167 ms** · `search='bin 16'` **851 ms** · the 23-join record **122 ms**. 1,084 open N + 2,705 open M; 453 k archived. `dbo.Progress` eight active rows, **2,346 open WOs at `7 Scheduled` and 404 at `8 Assigned`**. Seven live headers have no details row. RST has no CP location, so the CP chip is a legitimately empty list there.

## 3. The changes, exactly

### 3.1 Shape

One feature folder, the planner's split: **pure `rules.ts` → presentational components → one props-driven view → thin routes.** No `Date` and no DOM in `rules.ts`; `lib/dates.ts` stays the only module touching `Date`; every date the page shows is already a string from the API (`iso()` / `stamp()` server-side), so W1b formats nothing.

### 3.2 `rules.ts` 1.0.0 — pure

`VERSION = '1.0.0'`. No imports but types from `@/api/client`.

- `WO_STATUS_CARDS` — the eight cards as data: `{code, label, icon, token, accent, lightText}`; `R` is the one with `lightText: false` (§2.2).
- `PROGRESS_SYMBOL_IDS = [1,2,3,4,5,6]`; `progressCards(progressAll)` — one card per `ProgressRow` in id order, `symbol` when the id is 1–6 else `null` (OD-75 / OD-67).
- `SEGMENTS` — the six, same order and spelling as the backend's `rules.SEGMENTS`; a test pins the two lists equal through `WoRecord['completeWithin']`.
- `parseBadge(value)` → `{status, sid, prog, hasPO}`; missing parts default exactly as the oracle's transform (`prog '0'`, `hasPO` absent → false).
- `badgeStyle(value)` → `{backgroundColor, color, backgroundImage}` — the §2.2 rules as inline longhands. **Inline, no new CSS rule** (OD-41's precedent); jsdom reports `rgb()`/`rgba()`, so the tests assert that form.
- `poBadgeStyle(value)` (exported now, used by W1c) — the ten PO statuses, the flag channel left unimplemented with a comment naming it.
- `listTitle(woType)` · `typeChips()` → the four `{label, value}` · `chipStyle(active)` · `modeChipStyle(lit, rgb)`.
- `recordCount(count, more)` → `'No of Records: 200+'` when `more`, else `'No of Records: N'` (OD-77).
- `tabs()` / `subTabs()` — the labels and view order; `linkedTabLabel(count)` → `'Linked WO (+)'` above one.
- `fieldRows(record)` — the Details sub-tab's three columns as `[label, value]` pairs, so the component is a map and the test reads one table.

### 3.3 `wo.css` 1.0.0

Scoped `.wm-wo`, OD-27. Carries: the `--wo-rgb-*` / `--wo-color-*` / `--po-rgb-*` custom properties on `.wm-wo` (not `:root` — the planner and shell must not inherit them); the **four live class rules** re-scoped (`.wm-wo .wo-table thead`, the placeholder, the inner input, the four button shadows with their hover/active states); the panel, card, tab, chip and table geometry from §2.1. `height:100%` of the shell's cell and `position:relative`, as `planner.css` 1.1.2 learned (OD-54). No `.psc-*` names — those are Ignition's DOM contract, not ours.

### 3.4 `icons.tsx` 1.0.0

The thirteen missing Material glyphs, **copied from the icon library by script and not typed** (the S1k rule; four glyphs open with a relative `m`, Landmines §C), plus a re-export of `assignment` and `search` from `features/shell/icons.tsx` so there is one copy of each path in the tree. Same `VIEW_BOX` and `Record<IconName, ReadonlyArray<string>>` shape the shell uses, so the two files stay diffable.

### 3.5 `symbols.tsx` 1.0.0

Four presentational components, all driven by `rules.ts` tables, none holding state:
`WoNumBadge({value})` · `WoStatusRow({status})` (eight cards; an unknown or empty code lights none) · `WoProgressRow({prog, progressAll})` · `CompleteWithinSeg({value})` (**read-only in W1b — no click, no popup**; rendered with `aria-disabled` and the OD-51 title, since changing it is a write).

### 3.6 `useWorkorders.ts` 1.0.0

`useWoList({woType, includeClosed, includeArchive, search, limit, offset})` and `useWoRecord(woId)` over the generated `…Options()` helpers, `staleTime` 30 s, **no `refetchInterval`** — a WO record is not a 60-second poll, and the planner's poll is already one row per person per minute against the volume rule (OD-59, Landmines §C). The search term is debounced **300 ms** and only sent at **≥ 2 characters** (OD-78); `enabled: woId > 0` on the record. The hook owns no cap — the API's `limit` is bounded server-side at 1–1000, so OD-23's reason does not arise.

### 3.7–3.11 The components

`WoListPanel` (title, chips, the five-column table with the badge column, the footer) · `WoFiltersRow` (search box + clear + the two mode chips + the nine inert action buttons) · `WoRecordCard` (header card, the two symbol rows, Schedule, Assignment, Resources with `resources.line` printed **byte-for-byte as the API sends it**) · `WoDetailsTab` (three columns + the six stamp rows + Notes, read-only `textarea`) · `WoMaintView` (props-driven composition: the five main tabs and six sub-tabs drawn, **Work Order and Details selectable, the rest inert with the OD-51 title**, the split, the empty state, the loading state, the error state from `ApiError`). Selection: clicking a list row navigates to `/workorders/$id`; the list keeps the current id selected when it is still listed, else row 0 — the oracle's reconcile, ported.

### 3.12 The routes

`routes/workorders.tsx` and `routes/workorders.$id.tsx`, **exporting `Route` and nothing else** (Landmines §C), version in the header comment only. `validateSearch` on plain functions, no zod adapter (the OD-29 precedent): `type` ∈ `'' N CP M` (default `N`), `closed` / `archive` ∈ 0 1 2 (default 0), `q` string (default `''`). `limit` and `offset` are **not** in the URL — they are paging state, not something a link must name.

### 3.13 The shell

`shell/rules.ts` 1.1.0 — one constant changes: `ACTIVE_KEY_BY_PATH` gains `['/workorders','womaint']`. `activeKeyFor('/workorders/662704')` must also return `womaint`, so the lookup gains a **prefix** arm for rows marked as such; the planner row stays an exact match. That is the only behaviour change in the file, and it is why this is a minor bump, not a patch.

## 4. Traps

1. **A route file exports `Route` only** — a `VERSION` const there defeats code-splitting and warns once per import (S1f, eleven times).
2. **`psc-` is Ignition's DOM contract, not ours.** Do not copy `psc-*` selectors into `wo.css`; port what the rule *does*.
3. **Five classes do nothing (§2.3).** If the port looks wrong, the answer is in the inline styles, not in a class we failed to copy.
4. **The status row draws eight.** A `V` record lights Active; an `F` record lights nothing and that is the oracle's behaviour, not a bug (OD-74).
5. **`WONumBadge` always emits both background layers**, even with no PO — drop the transparent one and the two-entry `backgroundSize`/`backgroundPosition` lists misalign and the progress bar renders as a 7 px square.
6. **Progress 2 is not 2 %.** Wait is a muted nub at 8 % in a different colour; only 1/3/4/5/6 map to 0/25/50/75/100.
7. **`prog: 0`** means no card lit (W1a trap 6) — `progressAll` never contains 0, and `Progress` FK rejects it.
8. **jsdom reports colours as `rgb()`/`rgba()`** — assert that form, never the hex (S1i's lesson).
9. **TS 6's `lib.dom` is narrower** — no `as HTMLButtonElement`, no `textContent ?? ''`; pass the generic to `querySelectorAll<T>`.
10. **`cleanup()` in `afterEach`, no jest-dom** — there is no `setupFiles` and adding one is a change to every existing test.
11. **A `disabled` button shows no hover title in Chrome** — every inert control is `aria-disabled` with no handler (S1k).
12. **`.chip{flex:none}`** — a list of 100+ rows in a flex column squashes without it; `wm-compact-table`'s 42 px row height is the same family.
13. **The generated client builds a `Request`** — under Vitest set `client.setConfig({baseUrl:'http://test.local'})` or the first fetch throws on URL parsing.
14. **This slice changes `web/dist`**, so the backend suite and the dev-server request set are re-run with `dist/` present (Landmines §A).
15. **`routeTree.gen.ts` will change** — it is generated and committed; it is part of the predicted staged-path count, not a surprise.
16. **Two new routes mean two new chunks** — the smoke lists `dist/assets` and expects `planner-*.js` to still exist beside them (S1k's rule).
17. **The archive arm can cross the persist line.** `includeArchive=2` measured 1,167 ms on a clean box; a cold read on a loaded one can pass 2,000 ms and land in `Diag_Log` by OD-59. If it does, that is item 53's evidence, not a defect.

## 5. Test plan — predicted per file, **read from the cards before the drop**

| File | Cases | What |
|---|---|---|
| `rules.test.ts` | ~34 | `parseBadge` ×6 (full, no PO part, no prog, status-less, empty, junk) · `badgeStyle` ×9 (each status's rgba pair, the unknown fallback, the Wait nub, hasPO on/off, progress 0/25/50/75/100) · `poBadgeStyle` ×4 · the eight status cards (codes, icons, `R`'s dark text) · `progressCards` ×4 (1–6 symbols, a 7/8 plain card, unknown id, empty) · `SEGMENTS` equals the contract's `completeWithin` union · `listTitle` ×3 · `recordCount` ×2 · `linkedTabLabel` ×3 · `fieldRows` shape |
| `symbols.test.tsx` | ~16 | badge text and inline style; both layers present with no PO; the status row lights exactly one card and none for `F`/`''`; the progress row draws 8 cards on RST-shaped `progressAll` and lights 7; the segment marks one of six and is inert |
| `useWorkorders.test.tsx` | ~8 | the built URL carries `woType`/`includeClosed`/`includeArchive`/`search`/`limit`/`offset` and never `from_`; the debounce holds a 1-char term; `enabled` false at id 0; an `ApiError` body surfaces as an error; `signal` forwarded |
| `WoListPanel.test.tsx` | ~10 | the four chips and which is lit per `woType`; the five columns; the badge column renders a badge; the footer string with and without `more`; row click calls the handler |
| `WoFiltersRow.test.tsx` | ~9 | the two mode chips lit/unlit styles; Closed zeroes Archive and vice versa; the clear button; the placeholder; every inert control carries `aria-disabled` and an OD-51 title and no handler |
| `WoRecordCard.test.tsx` | ~12 | the header three rows; the hierarchy joined with ` > `; the symbol rows wired to `status`/`prog`; the eight Schedule rows; Assignment incl. `(none)` resp users; the resources table's seven columns and `resources.line` printed verbatim; `detailsMissing` renders the empty-record notice |
| `WoDetailsTab.test.tsx` | ~8 | the three columns' labels in view order; the six stamp rows; Notes read-only; a null id renders blank, not `0` |
| `WoMaintView.test.tsx` | ~12 | the split; tab and sub-tab strips with only two selectable; the inert tabs' titles; loading / empty / error; selection reconcile keeps the id when still listed and falls to row 0 when not; the wire (the one file that stubs `fetch`) |
| `shell/rules.test.ts` 1.0.2 | 12 → **14** | `/workorders` and `/workorders/662704` both → `womaint`; `/planner` unchanged; an unknown path still `''` |
| `planner/SelectedWOCard.test.tsx` 1.1.0 | 6 → **7** | `Open` is a link to `/workorders/$id` and is no longer disabled |

**Predicted: frontend `205 + ~126 = ~331 in 24 files`, exit 0; backend `319 passed, 2 skipped`, unchanged and re-run with `dist/` present.** The per-file numbers above are estimates from this spec; per WoW §2 they are **counted from the cards' own `it()` lines before the drop**, and a total that moves is a **1.0.1 of this spec**, not a note in the log.

## 6. Open decisions — 🤙 required

| OD | Proposal | Why |
|---|---|---|
| **OD-72** | **The read page ships as two slices**: W1b = the list + the Work Order tab (incl. Details/Notes); **W1c** = Query/Notes, Linked WO, WO Event History and the Purchase Orders sub-tab, bringing `PONumBadge`. | Twenty-four cards is already above a comfortable slice; all five tabs in one is forty. The seam is the sub-tab strip — the same seam the screenshots show. The four tab routes are live and tagged, so W1c is presentational and cheap. |
| **OD-73** | `/workorders` (list) and `/workorders/$id` (record). The URL carries `type`, `closed`, `archive`, `q`; **`limit`/`offset` stay out**. | OD-5 named `/workorders/$id`; OD-29 is the precedent — the URL names what a link must be able to reproduce, and paging position is not that. |
| **OD-74** | The status row draws the oracle's **eight** cards. An `F` record lights none; the header still names the status through `statusTitle`. | Parity, and RST's live table has no `F` (nor `K`). It becomes a real gap in **W3**, where the row is how a user *sets* status and Deferred would be unreachable — raised as an item against that slice, with `--wo-color-deferred` already in the stylesheet when it is wanted. |
| **OD-75** | The progress row draws **one card per `progressAll` row** — the oracle's six symbols for ids 1–6, a plain card for 7 and 8. | OD-67 as signed at W1a; 2,750 of RST's 3,789 open WOs sit at 7 or 8 and the oracle's fixed six lights nothing for them. |
| **OD-76** | The port **drops all five dead classes** (`wm-seg-9px`, `wm-tabs`, `wm-tabs-sub`, `wm-panel-header`, `wm-btn-tertiary`) and takes the inline styling that actually renders; the seven live ones are ported by what they do. **Closes item 54.** Carry-back to KT raised as an item: move the four `meta.classes` tokens to `props.style.classes` or delete the four unreachable rules. | Porting a rule the oracle never applies would make the SaaS differ from the screen it is copying. The fix at KT is one line per component, and it is a carry-back (item 40's rule), not part of this slice. |
| **OD-77** | Paging: `limit` 200, `offset`, a **Load more** button while `more` is true, and the footer reads `No of Records: 200+` until the last page. **No total**, ever. | OD-64 as signed. The oracle pages client-side at 100 over the whole result set, which is exactly the 620 k-row scan OD-64 refused. `200+` is honest; a number that required a COUNT would not be. |
| **OD-78** | Search: **300 ms debounce, minimum 2 characters**, the leading-wildcard `LIKE` kept as parity. | Item 53. The 851 ms is the query's shape, not the box, and it is what the oracle does — so the page stops *asking* rather than making the query lie. Measured at the smoke with the timings pasted; a prefix match for short-id-shaped terms stays available if 300 ms is not enough. |
| **OD-79** | The filter row's write controls **draw inert** (`aria-disabled`, `cursor:default`, `title="arrives with … (OD-51)"`): Edit, Save, Cancel, Print, Clone, Delete, Link WO, Email WOs, New PO, Manage Plan, Manage (resp. users). **Not rendered**: the `Summary` toggle, the three tips ⓘ anchors, the AI embed, the toast bar. | OD-51 and OD-52 exactly as the shell took them, so the page looks like the oracle and never lies about what it can do (OD-34). |

## 7. Smoke

Predicted before the run; pasted verbatim after; the trail last (WoW §6.1). **The dev server on PID 30284 has been up since the W1a smoke — stop the server child and prove zero listeners before the drop** (WoW §6.2), or the reload is the first smoke.

1. **Drop** — `Test-Path` each of the 24 cards in Downloads (all True or stop), check for a `(1)` twin, copy to targets, `Unblock-File` nothing (no `.ps1`), compare header `Version:` against each file's `VERSION` constant by script, then `git status --short -uall` → **predicted 24 modified/new + `routeTree.gen.ts` + 9 in `docs/reference/`**.
2. **Lint** — `cd web; pnpm lint` → 0. The generated client stays ignored.
3. **Suite** — `pnpm test` bare → **~331 in 24 files**, `$LASTEXITCODE` 0. Read the count against the prediction.
4. **Build** — `pnpm build` → 0; `gci dist\index.html`; list `dist\assets` and confirm `planner-*.js` still exists beside the two new `workorders-*.js` chunks.
5. **Backend with `dist/` present** — `cd ..\backend; uv run ruff check .; uv run ruff format --check .; uv run pytest` → **319 / 2**, both gates 0 (Landmines §A: the mount flips behaviour with no backend file changed).
6. **Server** — `Start-Process` in its own window; **exactly one PID** on 8000.
7. **The screen, one browser tab** — `/planner` still draws and the rail still lights Plannex · the planner's `Open` on a selected WO navigates to `/workorders/$id` (**OD-5 closes, visibly**) · the rail lights **WO Maint** on both `/workorders` and `/workorders/662704` · the four type chips switch the list and the title (`Work Orders` / `Work Orders + PM` / `Planned Maintenance`) · `CP` → an empty list and the footer reads 0 · the Closed chip lights and zeroes Archive · `662704` renders: badge, eight status cards with **Active** lit, the progress row with **eight** cards and 100 % lit, `week` on the segment, the five-title hierarchy, `Planned $0.00 | Actual $36.52 | Diff +$36.52`, Week No 2026.35 · `143760` renders with the detail-less notice · a screenshot of each against the seven live shots.
8. **Timings** — `Measure-Command` on the first paint of the default list, a `bin 16` search, and `includeArchive=2`, against W1a's 76 / 851 / 1,167 ms. Item 53's evidence.
9. **Trail** — wait 2 s, `scripts\Show-DiagTrail.ps1 -UserId 21 -Minutes 15`. **Predicted:** the planner poll's `[F]`s if a planner tab was open, **and not one row from any workorders 200** (OD-69/OD-73 as signed) — unless a read crossed 2,000 ms, in which case it is listed and that is trap 17 firing, a finding for item 53. `Diag_Log` count before and after, every difference accounted for **by name** (WoW §6.1 — the claim is "no row from the page", not "unchanged").
10. **Commit + tag** — `git add -A; git commit -m "W1b WOMaint page - list, record, Work Order tab; shell wiring; OD-5 closed"; git tag w1b-page-1.0.0`; `git log --oneline -2`.

## 8. Acceptance

- Frontend green at the predicted count, backend **319 / 2** with `dist/` present, lint and both ruff gates clean, all exit 0, all pasted.
- The seven screen checks in §7.7 match the live shots; the three timings in §7.8 are recorded in the log whatever they say.
- The trail matches §7.9 and every `Diag_Log` difference is named.
- `MenuItem_WOMaint` lights on both paths; **OD-5 is closed and the planner button proves it**.
- No backend file, no contract file, no database row and no lock file changed — `git status` before the commit is `web/src`, `routeTree.gen.ts`, `docs/reference/` and this spec, nothing else.

## 9. Consequences

### 9.1 Doc corrections for the next compiled set

- **Index §1 / §3.7 and the W1a spec §2.1:** `WOStatus` has **eight** cards (R H P K A V C D), not nine — there is no Deferred card. `WONumBadge` colours nine statuses and the stylesheet carries `--wo-color-deferred`, so the gap is the card row's alone.
- **Landmines §C:** Perspective renders a `props.style.classes` token as `psc-<name>`; a class on **`meta.classes` is never reachable by a `.psc-` rule**. Five of WOMaint's twelve `wm-*` classes do nothing for this reason or for want of a rule. A stylesheet rule that exists is not a stylesheet rule that applies — check which property the class sits on before porting it.
- **Index §3.7 / Architecture §5:** two new `docs/reference/` cards (the v2.69 stylesheet, `PONumBadge`) and the seven live screenshots.
- **Landmines §E:** item 54 is closed by OD-76; item 53's page-side answer is OD-78.

### 9.2 What this unblocks

W1c (the four tabs — every read is a generated hook away and `poBadgeStyle` ships here); the **auth** slice (the page is the first surface a real Redstag user will click, and it currently runs on the dev actor); W2/W3, whose edit mode is this page plus writes — `WoRecordCard` and `WoDetailsTab` become the edit surface, which is why they are one component per card and not one per field.

### 9.3 Candidate open items — raised in the log, not here

The Assessment card (always drawn by the oracle, zero rows on RST, no API behind it — draw empty or drop, a W1c OD); the `WO_Query` `N` and `A` codes (item 55, W1c's to label); the four KT `meta.classes` carry-backs; the `F`-has-no-card gap against W3; whether `Load more` should become windowing at 100 k rows; the `Summary` toggle's meaning (never read).

## 10. Changelog

- 1.0.0 (2026-09-20) Draft for 🤙. Written after reading `WOMaint` v16.28.3 component by component, the four symbols in full, stylesheet v2.69 and `PONumBadge_v1_2_0` (both cut as reference cards with this spec), the generated client on the box, and the seven live screenshots.
