# Azztec SaaS — WOMaint Audit Brief

**File:** Azztec_SaaS_WOMaint_Audit_Brief_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-16 · **Author:** Adriaan
**Status:** Audit input — **nothing here is signed.** This is the read-through that precedes the first WOMaint chunk spec; every question in §6 becomes an OD in that spec, signed at its gate. Delivery target (§7) is the customer's, not this document's decision.
**Target path:** `docs/Azztec_SaaS_WOMaint_Audit_Brief_v1_0_0.md` (+ project knowledge)
**Parent:** Port Spec 1.0.6 — OD-5 (`/open` → the WO module) is the planner's oldest open dependency; the S1k shell's `MenuItem_WOMaint` lights on the route this module brings.
**Sources read (2026-09-16, the 13:07 export):** `Workmate/Workorder/WOMaint` view v16.28.3 (588,182 B — census, tree, tables, handlers; not every script line), `workmate.workorder` 1.8.1 (delivered as `workmate_workorder_code_v1_8_1.py`, byte copy), `workmate.wo_activity` 1.7.2 / `wo_resource` 1.0.0 / `attach` 1.6.1 (function lists only), the 52 `Workmate/Workorder*` / `WO Query` / `WO Responsible User` named queries (delivered as `WO_Named_Queries_2026-09-16.md`), the page config (`/WOMaint` docks the shell). **Not yet read:** the WOMaint scripts in full (92,867 characters over 94 handlers), `WOActivityPanel` (47,207 B), the eleven popups it opens, `Components/Workmate/Objects/Symbols/WOProgress` and `WOStatus`, the `AttachmentPanel`, the `wmsp_WO_*` procedure bodies on RST, and any RST row of any table below.

---

## 1. What WOMaint is (the oracle, as read)

The .NET `frmWOMaintenance` rebuilt in Perspective: **a list on the left, a record on the right.** 281 components (110 flex containers, 74 labels, 27 text fields, 19 buttons, 18 dropdowns, 11 embedded views, 10 tables), one 1954 × 950 view, 39 view customs, 94 script handlers. Navigation lands it at `/WOMaint` with the S1k shell docked.

**Left — `WOListPanel`:** a title, a `TypeToggle` (the thumbnail shows **WO · CP · PM · All** chips), `WOListTable` (`WO_ID`, `WO_IdStyled`, `WO_Title`, `Asset_ID`, `Location_Id`), a footer with the record count. Fed by `Workmate/Workorder/Search` v12 — the big one (6,372 B): `includeClosed` / `includeArchive` each 0 / 1 / 2 (hide · include · **only**), capital-project detection by the *location's* `CP` prefix (D-WOID-3), a live arm and an archive arm (`WO_C_*`). Selection → `onSelectionChange` (3,104 chars) loads the record.

**Right — `DetailPanel`:** a `FilterRow` of twenty controls (search by WO id / title / asset / location, the include chips, `btnPurchaseOrder`, `btnCreateLinkedWO`, `btnDeleteWO`, edit / save / cancel via the toolbar messages) over five main tabs:

| Tab | What it draws | Backed by |
|---|---|---|
| **Work Order** | the header card (id, title, asset, location, Request / Planned buttons); `SCHEDULE` (Day · Week · Month · 3-Month · Next shut · Range — the `CompleteWithinSeg` embed; start / end / logged dates, duration, est. cost, downtime, week no); `ASSIGNMENT` (person resp., charge to, responsibility, resp. users → `UserSelector`); `RESOURCES` (plan table + `Manage Plan` → `ResourceManager_popup`); a **sub-tab strip**: Details (WO group, reason, fault, dept, class, charge to, responsibility, WOC1–3, company, Ref 1/2, the audit stamps created / ack / approved / closed / cancelled / last save) · Purchase Orders (`POTable`, double-click opens) · Attachments (`AttachmentPanel` embed) · Procedures (`ProcTable`) · Parts (`PartsTable`) · Labour (`LabourTable`); `NOTES` | `Workorder/Item` (the header + details + six user-name joins), `Workorder Detail/Item`, twelve `*/Dropdown` reference queries, `ResourceCompare`, `GetPODetails`, `WO Responsible User/List` |
| **Activity** | the same header card again (`Act_*` twins) + `WOActivityPanel` embed — labour and parts actuals, comments | `wo_activity` 1.7.2: `saveLabour` / `savePart` / `updateLabour` / `updatePart` / `deleteLabour` / `deletePart` / `reversePartIssue`, all with `dryRun` |
| **Query/Notes** | `QN_QueryTable` (type, date, from, to, description, email sent) | `WO Query/Search` |
| **Linked WO** | `LWO_FamilyTable` (relation, badge, title, parent short id, dates) | `Workorder/LinkedFamily`, `workorder.canCreateLinked` |
| **WO Event History** | `EVT_TimelineTable` (seq, event, detail, date, by/site) + `EVT_AssessmentTable` | `Workorder/Event/Search` |

Plus a `ToastBar` and the `WM_AI_Assistant` embed (dark). Tips badges on three anchors (item 33's pattern).

## 2. The write paths — what "full CRUD" means here

Every write already goes through **`workmate.workorder` 1.8.1**, the service layer the view calls (`update` ×3, `updateStatus`, `updateProgress`, `updateDetail`, `canCreateLinked`, plus `create` / `createFromTemplate` / `clone` / `delete` / `addNote` from the popups). That module is the port's oracle for the backend, the way `workmate.planner` 1.3.1 was for `rules.py`. What it does, and what the port must therefore do:

| Operation | Oracle path | Portability notes |
|---|---|---|
| **Create** | `create()`: `WO_Short_IDs` insert → `wmsp_WO_StatusInsert` → `wmsp_WO_N_HeaderInsert` → `wmsp_WO_N_DetailsInsert` → optional `Source_Action_ID` back-link; **the next `WO_ID` comes from `WO_Status`, the sequence owner** (1.8.1 — a live PK dup at KT on 2026-07-22 when it came from `MAX(header)+1`); `Short_WO_Id` prefix is `WO` (D-WOID-1), `CP` preserved by location (D-WOID-2), per-prefix `MAX(seq)`; `Week_No` via `_weekNoAndYear` (**S2a's `weekno.py` is that port, already on disk**); `Request_End_Date` from `completeWithin` (`day` / `week` / `month` / `3month` / `nextshut` — `Shutdown/GetNextShut`) | four stored procedures in a transaction. **D-3 question:** call the procs (MSSQL-only, `SET NOCOUNT ON`, Landmines §B) or port their bodies to portable SQL? The procs' bodies must be read on RST before that OD |
| **Read** | `Workorder/Item` (header + details + user names), `Workorder Detail/Item`, `Search` v12, the dropdown set, `ResourceCompare`, `GetPODetails`, `LinkedFamily`, `Event/Search`, `WO Query/Search` | straight ports into `app/workorder/sql.py` with PG-CONVERT tags; `Search` v12's two arms and three-mode params are the parity surface |
| **Update** | `update()` header-only (`Workorder/Update` 1.2 — title, location, asset, dates, company); `updateDetail()` via `wmsp_WO_N_DetailsInsertUpdate` (`Workorder Detail/InsertUpdate`); `_logFieldDiffs` → one `WO_Event_History` row per changed column, `event_details` capped at **990** (varchar(1000)), `Source_Form 'WOMaint'`, `server_name` — OD-3's `'SaaS'`, both sites (item 45) | the audit-diff writer is pure and ports 1:1 (`_sameValue`, `_fmtDiffValue`, `_DIFF_DATE_COLS`) |
| **Status / Progress** | `updateStatus` over `R H P K A V C D F` with the .NET stamps (ack / approved / closed / cancelled user + date); `updateProgress` 1–6 (Progress FK rejects 0 — Landmines §E) | state machine ports as pure rules (`rules.py`), tested at zero DB |
| **Delete** | `canDelete()` (blocked for Closed / Active, PO-linked, linked children, `Part_Adjustment` / `Part_Holding` refs) → `delete()`: `Meter_Reading.FROM_WO_ID` detached, an event-history DELETE row, `wmsp_WO_StatusDelete` **with an in-tx cascade verify** (hard delete, decision D3; admin-only gate on the button, D5) | the cascade verify is the Marker-Law shape already |
| **Clone / Linked / Template** | `clone()` (title, notes, priority, details, `Est_Cost`; status → `P`, progress 1, fresh short id; activities / POs not cloned), `canCreateLinked()` (parent A–Z, child 1–9, depth cap — the .NET suffix rules), `createFromTemplate()` | second-wave — not day-one CRUD |
| **Activity actuals** | `wo_activity` 1.7.2 (labour / part lines, `dryRun` everywhere, the critical-part e-mail, contractor shadows) | **its own module and its own audit** — 70 KB, e-mail side effects, `Part_Holding` stock movement |
| **Attachments** | `attach` 1.6.1 (file-system jail, `Attachment` tables per entity) | its own audit — a file store is not in the SaaS yet |

**`workmate.diag.forensic`** is called 41 times from the view — the `[F]/[G]/[E]` seam the SaaS already has (D-8).

## 3. What already exists on the SaaS side

- `app/core/weekno.py` 1.0.0 — `Week_No` for `create()`, no caller yet (S2a). WOMaint create is its second consumer after `move_wo`.
- `deps.get_current_actor()` (OD-12) — every write's `User_Id`; the JWT swap stays outside (log 09-15 §4.1).
- `diag.py` 1.1.1, the flat error body (OD-15), `WindowError`-by-type (OD-16), `db.insert_returning_id()` (D-3), `Diag_Log` on RST (`0001`).
- The planner's `SelectedWOCard` with `Open in WO Maintenance` **disabled** (OD-5) — the first link into this module is `/workorders/$id` (Port Spec OD-5's named route).
- RST already carries `0001`'s twelve KT tables — none of them is a WO table; the WO schema is legacy on both databases (`WO_N_Header`, `WO_N_Details`, `WO_Status`, `WO_Short_IDs`, `WO_Event_History`, `WO_N_Resource`, `WO_N_Activity`, `WO_C_*`).

## 4. Landmines already known that this module walks into

`char(n)` padding on `Short_WO_Id char(25)` / `Status char(1)` / `WO_Title char(70)` (RTRIM + strip); `Users.User_Id` numeric → `Decimal`; naive `datetime` and the 3.33 ms precision; `Request_Start_Date` carrying a time of day on ~half the rows; `Week_No` is not a function of the start date (OD-49) — `create()` computes it, `update()` never recomputes it; triggers on RST are PO-only (so `OUTPUT INSERTED` is still avoided, D-3); legacy procs return row counts (`SET NOCOUNT ON`); `WO_Status` owns the id sequence and gates the header — companion row first; `:name` in a SQL comment is a bind (the NQ headers already learned this — `Update` 1.1's changelog).

## 5. The slice cut proposed for the spec

Four slices, in the S2 shape (audit → spec per slice, pair rule, `dry_run=True` first — the first slice that writes a **WO** to RST):

| Slice | Backend | Frontend | Writes RST? |
|---|---|---|---|
| **W1 read** | `app/workorder/`: `sql.py` (Item, Detail/Item, Search v12 both arms + modes, the twelve dropdowns, ResourceCompare, GetPODetails, LinkedFamily, Event/Search, WO Query/Search), `repo.py`, `schemas.py`, `service.py`, `router.py` — `GET /api/v1/workorders?…` (search), `GET /workorders/{id}` (the record), `GET /workorders/{id}/events`, `/pos`, `/resources`, `/linked`, `/queries`; `GET /workorders/refs` (the dropdown set in one call) | `features/workorder/`: list panel + type chips + search row, the record's Work Order tab (header card, schedule, assignment, resources plan **read-only**, the Details sub-tab, Notes), the Linked / Event History / Query tabs as tables; `routes/workorders.$id.tsx`; the planner's `Open in WO Maintenance` **enabled** (OD-5 closes); `MenuItem_WOMaint` live (one row in `activeKeyFor`) | no |
| **W2 write core** | `service.create` / `update` / `update_detail` / `set_status` / `set_progress` / `add_note` with the `_logFieldDiffs` audit writer, `weekno.py`'s first caller, `dry_run=True`; the proc-vs-portable OD (§6 Q1) | — | **yes** — first WO written to RST; Marker Law on the smoke's own WO |
| **W3 write routes + edit UI** | `POST /workorders`, `PATCH /workorders/{id}`, `/status`, `/progress`, `/notes`; `409 STALE` on `Last_Save_Date` | edit mode (`wo-edit` / `wo-save` / `wo-cancel-edit` as they are in the view), the `CreateWO_popup` as a dialog, status / progress controls, the toast bar | yes |
| **W4 delete + linked + clone** | `can_delete` / `delete` (the cascade verify), `can_create_linked` / linked create, `clone`; `Delete` and `CloneWOConfirm` dialogs; the admin gate is **OD-2's** problem — until identity exists, delete stays behind the dev actor only | yes |
| later, own audits | Activity actuals (`wo_activity`), Attachments (`attach`), Purchase Orders sub-tab as a writer, Procedures, Templates, the AI embed, tips | | |

## 6. Questions the spec must answer (each an OD, signed at its gate — none signed here)

1. **Procedures or portable SQL** for create / detail upsert / status delete? Read `wmsp_WO_StatusInsert`, `wmsp_WO_N_HeaderInsert`, `wmsp_WO_N_DetailsInsert`, `wmsp_WO_N_DetailsInsertUpdate`, `wmsp_WO_StatusDelete` bodies from RST's `sys.sql_modules` first. The .NET app still writes through them at RST — a portable rewrite must produce byte-identical rows.
2. **`Short_WO_Id` policy on RST.** KT's D-WOID-1 (`WO-` prefix) was a KT decision on 2026-07-14; what prefix does RST's data carry? `SELECT LEFT(RTRIM(Short_WO_Id), …), COUNT(*)` on `WO_N_Header` before deciding.
3. **`Search` v12 parity** — `includeClosed` / `includeArchive` modes and the CP-by-location rule: port as-is, or does RST have no `CP` location?
4. **The `WO_C_*` archive arm** — does RST use it (row counts), and is the archive arm inside W1?
5. **Optimistic lock** — `Last_Save_Date` as the `expect_*` twin of the planner's `expect_start_iso`?
6. **`Server_Name` / `Source_Form`** — OD-3's `'SaaS'` and `'WOMaint'` verbatim (the .NET and Perspective trails share one table).
7. **Delete rights** — hard delete per KT's D3, gated by whom before OD-2?
8. **Route shape** — `/workorders/$id` (Port Spec OD-5) vs the oracle's `/WOMaint` with the id in session state; the SaaS keys the URL (the OD-29 precedent).
9. **What the two-week build cuts** (§7).

**Evidence to paste before any of them:** row counts of the eight WO tables on RST **and** KT (three-part names, `SELECT DB_NAME()` first); `TOP 5` of `WO_N_Header` with `Short_WO_Id` variety; the five proc bodies; `WO_Event_History` columns and lengths; `Users.Active` / `User_Skill.Active` domains as they meet the assignment dropdowns.

## 7. The two-week reality (Redstag test server, first use)

What the ask contains, in slices already on the board: **S1k** shell (built, unsmoked) · **W1–W4** above · **S2b–S2d** (the planner's move / undo / estimate — "a finished Planner as in Workmate" is at least that; the KT planner in today's screenshot also carries Suggest, the orb, 6M and drag-to-plan-hours — S4/S5 work) · an **auth slice** (D-5 / OD-2 — a test server with real users cannot run on `WORKMATE_DEV_USER_ID=1`) · a **deploy slice** (a Windows service or the appliance, `dist/` built, `.env` for the RST server, the DB pointed at Redstag's `dbWorkmate`).

At the cadence of the last six sessions (one slice per session, each with its audit and log) that is **nine to twelve slices**. Two weeks is eight to ten working sessions. The honest cut for a first test-server drop — proposed, not decided:

1. **S1k** smoke + commit (this session's tail).
2. **W1** read-only WOMaint — the module Redstag will look at first, no risk to their data.
3. **Auth minimal** — sign-in against `Users` with `App_User` (D-5) so the actor is real before the first write; OD-2's list from Andrew is the blocker to name to Redstag now.
4. **W2 + W3** — create / edit / status / progress on the test server.
5. **S2b + S2c** — planner moves land on the same server.
6. **Deploy** — before or after 4, depending on whether Redstag wants to watch it grow or receive it once.

Left for after the first drop: **W4** (delete / clone / linked), **S2d** (drag-and-drop — the planner is usable through the day dialog and the WO record until then), activity actuals, attachments, POs, tips, the brand read, rights. Every one of these has an oracle in the export and a named place in this brief.

The rules that do not bend for the date: `dry_run=True` first on every writer, Marker Law on the smoke's own WO, the pair rule, a log per session. What can bend: card count per session (W1's SQL ports are mechanical), and the doc set can lag by one session if the log carries the queue.

## 8. Reference cards delivered with this brief

- `workmate_workorder_code_v1_8_1.py` — byte copy of `workmate.workorder` 1.8.1 (`docs/reference/`). PK: add.
- `WO_Named_Queries_2026-09-16.md` — the 52 `query.sql` files under `Workmate/Workorder*`, `WO Query`, `WO Responsible User`, each byte-for-byte with its last-modified stamp (`docs/reference/`). PK: add.
- Still in the export, extracted when their audit runs: `WOMaint/view.json` (588 KB), `WOActivityPanel/view.json`, `wo_activity` 1.7.2, `wo_resource` 1.0.0, `attach` 1.6.1, the eleven popups.

## 9. Changelog

- 1.0.0 (2026-09-16) Initial. From the 13:07 export and the scripts zip; a read-through, not a spec; nothing signed.
