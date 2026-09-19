# Azztec SaaS — W1a WOMaint Read API Chunk Spec

**File:** Azztec_SaaS_W1a_WOMaint_Read_Api_Chunk_Spec_v1_0_1.md · **Version:** 1.0.1 · **Date:** 2026-09-19 · **Author:** Adriaan
**Status:** **Built on a delegation — OD-62…OD-71 answered one by one on 2026-09-19 ("ok" on all ten), recorded as *delegated, not signed* (the OD-50…54 precedent); a 🤙 on this file converts them.** 1.0.1 supersedes 1.0.0 the same day: the cards as cut differ from the draft in four countable places (§10) — the statement count, two contract key names, where the linked badge is assembled, and the test counts.
**Target path:** `docs/Azztec_SaaS_W1a_WOMaint_Read_Api_Chunk_Spec_v1_0_1.md` (+ project knowledge: replaces 1.0.0)
**Parent:** Handover Brief 5.0.0 §5 (W1 is next), `Azztec_SaaS_WOMaint_Audit_Brief_v1_0_0.md` §5/§6 (the W1–W4 cut and the evidence it asked for), Index 1.9.0 §6, log 09-19 1.1.0 §9 items 46–52. **Closes OD-5's first half** (a WO record readable on the SaaS); the page that shows it is **W1b**, the next spec (OD-62).
**Source of truth:** the 2026-09-19 Designer exports, read in full before this spec (§2.1): `Workmate/Workorder/WOMaint` v16.28.3 (byte copy `docs/reference/WOMaint_2026-09-19_view.json`), the four symbols (`WOStatus`, `WOProgress`, `WONumBadge`, `CompleteWithinSeg` — byte copies in `docs/reference/`), the 56 + 15 named queries (`WO_Named_Queries_2026-09-16.md`, `WO_Named_Queries_2026-09-19_addendum.md`, and the 15 reference reads in §2.3), `workmate/workorder/code.py` 1.8.1 (byte-equal to the PK card), stylesheet v2.69 (read for W1b; not used here). **RST evidence:** Block W1-E and its two addenda, pasted 2026-09-19, reproduced in §2.4. Read from the PK cards, not remembered: `planner/router.py` 1.1.1, `planner/repo.py` 1.1.0, `planner/sql.py` 1.1.0, `planner/schemas.py` 1.1.0, `planner/rules.py` 1.1.0, `core/db.py` 1.0.0, `core/deps.py` 1.1.0, `core/diag.py` 1.2.0 (`log()`'s `persist` flag), `main.py` card 1.0.6, `test_planner_api.py` 1.2.0, `test_planner_repo.py` 1.0.2, `test_openapi_contract.py` 1.0.0, `openapi-ts.config.ts` 1.0.2.
**Writes:** no database row anywhere — every statement is a SELECT, the suite runs inside a rolled-back transaction (D-10), persistence is off under `WORKMATE_ENV=test`. **Contract change:** yes — six new paths, `main.py` 0.4.0 → **0.5.0**, `docs/api/openapi_0_5_0.json`, `pnpm gen:api` (OD-38 rule, WoW §2).
**Signed decisions in force:** OD-1 (no WO_N_Plan dependency here), OD-14 (envelope `ok/apiVersion/actor/ms`, no gate), OD-15 (flat errors), OD-16 (400 only on a refused input), OD-12 (actor = `Depends(get_current_actor)`), OD-37 (apiVersion from the router's `__version__`), OD-38 (the OpenAPI document is named from `main.__version__`), OD-55/OD-59 (the middleware's persist rule), D-2 (plain `def`), D-3 (portable SQL, `OUTPUT INSERTED` never), D-9 (camelCase contract keys), D-10 (tests roll back); Landmines §B (char(n) strip on every read, `Users.User_Id` numeric → int, no colon in a SQL comment, `Entry_date DESC` needs a tie-break), §E (`WO_Status` owns the sequence — irrelevant to a read, noted).

---

## 1. Scope — eleven cards and one empty `__init__.py`, then stop

The WOMaint **read** side as a versioned API: the list the oracle's `WOListTable` binds (`Search` v12, both arms, all three modes), the record it assembles on selection (`Item` + `Workorder Detail/Item` + the six user names + the responsible users + the resources compare, with the three view-side derivations moved into the data layer), and the four read-only tabs (`LinkedFamily`, `Event/Search`, `WO_Query`, `GetPODetails`). Six `GET` routes under `/api/v1/workorders`. **No page** (W1b), **no write** (W2/W3), **no `refs`** (OD-66), **no Activity / Attachments / Procedures / Parts / Labour** (their own audits).

| # | Deliverable | Target path | Version | Change |
|---|---|---|---|---|
| 1 | `Azztec_SaaS_app_workorders_sql_v1_0_0.py` | `backend/app/workorders/sql.py` | **new** | thirteen portable statements (three search variants) + `ALL_STATEMENTS` (§3.1) |
| 2 | `Azztec_SaaS_app_workorders_rules_v1_0_0.py` | `backend/app/workorders/rules.py` | **new** | pure: the view-side derivations, ported (§3.2) |
| 3 | `Azztec_SaaS_test_workorders_rules_v1_0_0.py` | `backend/tests/test_workorders_rules.py` | **new** | pair of 2 |
| 4 | `Azztec_SaaS_app_workorders_repo_v1_0_0.py` | `backend/app/workorders/repo.py` | **new** | binds, maps rows to contract dicts (§3.3) |
| 5 | `Azztec_SaaS_test_workorders_repo_v1_0_0.py` | `backend/tests/test_workorders_repo.py` | **new** | pair of 4 — the dialect gate for `sql.py`, then RST inside a rolled-back tx |
| 6 | `Azztec_SaaS_app_workorders_schemas_v1_0_0.py` | `backend/app/workorders/schemas.py` | **new** | the contract as `extra="forbid"` models (§3.4) |
| 7 | `Azztec_SaaS_app_workorders_router_v1_0_0.py` | `backend/app/workorders/router.py` | **new** | six routes, one `[F]` line each (§3.5) |
| 8 | `Azztec_SaaS_test_workorders_api_v1_0_0.py` | `backend/tests/test_workorders_api.py` | **new** | pair of 6 + 7 — TestClient over the real app |
| 9 | `Azztec_SaaS_test_openapi_contract_v1_1_0.py` | `backend/tests/test_openapi_contract.py` | 1.0.0 → **1.1.0** | the six paths, their params and error shapes, published (§3.6) |
| 10 | `Azztec_SaaS_app_main_v1_0_7.py` | `backend/app/main.py` | card 1.0.6 → **1.0.7**, app **0.4.0 → 0.5.0** | mounts the router; `/health` `versions.workorders` (§3.7) |
| 11 | `Azztec_SaaS_web_openapi_ts_config_v1_0_3.ts` | `web/openapi-ts.config.ts` | 1.0.2 → **1.0.3** | input → `openapi_0_5_0.json` (§3.8) |
| — | `backend/app/workorders/__init__.py` | — | empty | `New-Item` in the drop block (the D1a `app/diag/` precedent) |

**Generated, committed, never cards:** `docs/api/openapi_0_5_0.json` (exported from `app.main.app`, §7 step 4) and `web/src/api/client/**` (`pnpm gen:api`). `docs/api/openapi_0_4_0.json` is `git rm`-ed in the same commit (WoW §2: never two contract files on disk).

**Untouched:** every `app/planner/*`, `app/diag/*`, `app/core/*` module; `test_planner_*`, `test_diag_*`, `test_smoke.py`, `test_kt_uplift.py`, `test_weekno.py`; every `web/src/**` file except the generated client; every database.

**Not in this slice (cut at the audit):** the page (W1b: list panel, chips, record, tabs, shell wiring — `activeKeyFor` gains `['/workorders','womaint']`, `MenuItem_WOMaint` goes `live`); the edit/save/cancel/create/clone/delete/link/email/PO/print/manage actions (W2–W4, PO, print); `refs` — the thirteen `…/Dropdown` reads for editing (W3, OD-66); the archive **record** (a listed archived WO is a 404 `ARCHIVED` here, OD-68); Activity (`WOActivityPanel`), Attachments, Procedures, Parts, Labour; the `Search` NQ's `woTitle` / `shortAssetId` / `shortLocationId` parameters — the view never sets them (OD-63); `Condition` resolved to a title (its columns were not read; the view shows no condition field); `canCreatePO` and the `User_Settings` rights read (W3 / rights); `nav-active`, `debug-log`, `show-toast`, `wo-*` messaging (view mechanics, no API equivalent).

## 2. Evidence

### 2.1 The exports — read in full 2026-09-19

Eight Designer resource exports (236 files) plus six more for the reference reads and the stylesheet, all exported 13:01–13:05 and later on 2026-09-19. `workmate/workorder/code.py` is byte-identical to `workmate_workorder_code_v1_8_1.py`. The 48 named queries shared with the 09-16 bundle are byte-identical; eight are new (the addendum). `TipBadge` / `TipPopup` are byte-identical to the 09-10 cards.

| Resource | Bytes | Last modified (`resource.json`) | Root `meta.name` |
|---|---|---|---|
| `Workmate/Workorder/WOMaint/view.json` | 588,182 | Adriaan, 2026-09-03T05:44:41Z | `WOMaint_v16_28_3` |
| `Components/Workmate/Objects/Symbols/WOStatus` | 31,969 | 2026-08-29T20:22:15Z | `root` — nine status cards R H P K A V C D F |
| `…/WOProgress` | 35,055 | 2026-08-29T20:22:15Z | `root` — six cards for `Progress_Id` 1–6 |
| `…/WONumBadge` | 6,315 | 2026-08-29T20:22:15Z | `WONumBadge_v1_3_0` — one label, colour from `left(value,1)` |
| `Components/Workmate/Popups/CompleteWithinSeg` | 14,757 | 2026-08-29T20:22:15Z | `CompleteWithinSeg_v1_8_0` — day / week / month / 3-month / next shut / range |

WOMaint by count: 110 flex containers, 74 labels, 27 text fields, 18 dropdowns, 10 tables, 11 embedded views, 19 buttons; **94 scripts, 92,869 characters** (12 message handlers on the root, `onStartup`, 45 event scripts, 36 binding transforms); 18 distinct named queries bound, 4 more called from transforms, 4 raw `runQuery`/`runPrepQuery` statements typed inside scripts.

### 2.2 What the view does on the read path — the port's oracle, script by script

- **The list** (`WOListTable.props.data` ← `Workmate/Workorder/Search`, params `shortWoId`=`searchWoId`, `woTitle`/`shortAssetId`/`shortLocationId` (always `''`), `includeClosed`, `includeArchive`, `woType`). Transform: every column `str().strip()` except `WO_ID`→int; `WO_IdStyled = status|shortId|progressId|hasPO` (`HasPO` defensive → 0 when absent); `woListRecordCount = len(rows)`; the `pendingWoId` auto-select and the selection reconcile (keep the current id if still listed, else row 0). **The search box is one field** (`SearchIcon.onClick`, `SearchField.onActionPerformed`) and writes **only `searchWoId`**; `Search` v12 matches it against `Short_WO_Id` **or** `WO_Title`. `btnClear` / `wo-show-all` clear all four. Chips (v16.20.0): `FilterChip_Closed` toggles `includeClosed` 0 ↔ **2** (only closed/cancelled) and zeroes archive; `FilterChip_Archive` toggles `includeArchive` 0 ↔ **2** and zeroes closed; value **1 = everything** is reserved for the handoff. Type chips set `woTypeFilter` to `'N'` / `'CP'` / `'M'` / `''`; the seed is `'N'`.
- **The record** (`txtWorkOrderId.props.text` ← `Item`, transform 5,731 chars): skip while `selectedWoId` ≤ 0; merge `Item` row with `Workorder Detail/Item` (25 columns); default 22 id fields to 0 when NULL; supplementary `runQuery` for `Location.Short_Location_ID`/`Location_Title`, `Asset.Short_asset_Id`/`Asset_Title` (both already in `Item`) and `Parent_Location_Hierarchy` (already in `Item`); `woProgressId = int(Progress_Id)`; `woStatusCode = Status` when non-empty; **`woCompleteWithin` reverse-derived** from `Request_Start_Date`/`Request_End_Date`: `daysBetween == 1 → day`, `7 → week`, `14 → nextshut`, `monthsBetween == 1 and days ≤ 31 → month`, `monthsBetween == 3 and days ≤ 93 → 3month`, else `range` (`range` when either date is NULL). `onSelectionChange` reads `WO Responsible User/List {woId, includeRemoved: 0}` → `respUsersSummary = ', '.join(Short_User_Id)` or `(none)`.
- **Header labels**: `lblLocHierarchy` parses `Parent_Location_Hierarchy` `{(id)(short)(title)}…` and joins the **titles** with `' > '`; on a parse failure the raw string. `lblChargeToDesc` / `lblRespDesc` ← `Supplier/GetShortId` (the `Short_Supplier_Id` of the two supplier ids). The thirteen dropdowns bind `…/Dropdown` (active rows only, `value`/`label`, WOC1–3 prepend `-- No Selection --` / 0) and select `selectedWoData.<id>`.
- **Resources card**: `ResourceCompare {woId, tick}` for the table; `lblAllResourcesValue` sums `PlanCost` / `ActCost` and prints `Planned $x  |  Actual $y  |  Diff ±$z` (money with thousands separators, sign only on a positive diff).
- **Linked tab**: `LinkedFamily {woId}` → `Rel` = Parent / Child / Grandchild (+ ` (this WO)` when `IsSelected`), `EntryStr = str(Entry_date)[:16]`, `StartStr = str(Request_Start_Date)[:10]`; `linkedFamilyCount = len(rows)`, `linkedFamilyRoot` = the level-0 short id; a lone WO is a family of one.
- **Event History tab**: `Event/Search {woId, offsetRows: 0, pageSize: 200}` → `Seq` 1-based, `Event`, `Detail` = `event_details` with every `{` `}` removed, `Date` = `dd/MM/yyyy HH:mm`, `BySite` = `editor · Site_Name` (else `Site_Code`, else editor). **Assessment card**: raw `SELECT Assessment_Id, Asset_ID, Log_date, Row_Changed, User_Id FROM WO_Assessment_Log WHERE WO_ID = … ORDER BY Log_date DESC`, `DateStr = str(Log_date)[:10]`.
- **Query/Notes tab**: `WO Query/Search {whereCondition: 'WO_Id = <id>', orderByExpression: 'Query_Date DESC'}` — the NQ is `EXEC wmsp_WO_QuerySelectDynamic`, whose body (§2.4) is a nine-column select over `dbo.WO_Query` with the strings pasted in; `TypeLabel` = Query for `Q`, Reply for `R`, else the raw code; `DateStr = str(Query_Date)[:16]`.
- **Purchase Orders sub-tab**: `GetPODetails {woId}` → `PO_NumStyled = Status|Short_PO_Id`, `Due_Date` cut to the date.
- **The handoff** (`onStartup`, v16.18.0): arriving with `session.custom.womaintWoId`, probe `Status`, `WO_Type_Flag`, `Location.Short_Location_ID` for that id and widen only what it needs — `includeClosed = 1` when status ∈ {C, D}; `woTypeFilter = 'M'` when the flag is `M`, else `'CP'` when the location is `CP` or starts `CP-`; both `includeArchive = 1` and `includeClosed = 1` when the id is not in `WO_N_Header`. Then `searchWoId = <short id>` so the list is filtered to it.
- **Progress lookup** (`onStartup`): `Workmate/Progress/Get` once → `progressMap {p<id>: title}` and `progressOptions`.

### 2.3 The fifteen reference reads (exported separately, 2026-09-19)

| Query | Body (bodies only; comments stripped) |
|---|---|
| `Progress/Get` | `SELECT Active, Capture_UserDate_OnSave, Progress_Description, Progress_Id, Progress_Title, Short_Progress_Id, Sys_Progress_Id FROM Progress WHERE ISNULL(Active,'1') = '1' ORDER BY Progress_Title` |
| `Supplier/GetShortId` | `SELECT Short_Supplier_Id FROM Supplier WHERE Supplier_ID = :id` |
| `Account/Dropdown` | `Account_ID, Account_Title FROM Account WHERE ISNULL(Disabled,'N') != 'Y'` |
| `Asset/Dropdown` | `Asset_ID, RTRIM(Short_asset_Id) FROM Asset WHERE ISNULL(Status,'Y') = 'Y'` |
| `Company/Dropdown` | `Company_Id, Company_Title FROM Company WHERE ISNULL(Active,'1') = '1'` |
| `Cost Center/Dropdown` | `Cost_Center_ID, Cost_Center_Title FROM Cost_Center WHERE Active = '1'` |
| `Fault/Dropdown` | `Fault_Id, Fault_Title FROM Fault WHERE ISNULL(Active,'1') = '1'` |
| `Location/Dropdown` | `Location_Id, Location_Title FROM Location WHERE ISNULL(Status,'Y') = 'Y'` |
| `Reason/Dropdown` | `Reason_ID, Reason_Title FROM Reason WHERE ISNULL(Active,'1') = '1'` |
| `Supplier/Dropdown` | `Supplier_ID, Company_Name FROM Supplier` (no active filter) |
| `User/Dropdown` | `User_Id, RTRIM(User_Name) FROM Users WHERE Active = 'Y'` |
| `WOC1/2/3/Dropdown` | `WOC<n>_ID, WOC<n>_Title FROM WOC<n> WHERE ISNULL(Active,'1') = '1'` |
| `WOGroup/Dropdown` | `WO_Group_ID, RTRIM(WO_Group_Title), RTRIM(Short_WO_Group_ID) AS short FROM dbo.WorkOrder_Group WHERE ISNULL(Active,'1') = '1'` |

These give the **table and column names** the record's label joins use (§3.1 `WO_ITEM`). The active filters are **not** applied to a read (OD-66): a WO holding a retired reason still names its reason.

### 2.4 RST, read 2026-09-19 (Block W1-E + two addenda; KT beside it where it matters)

- **Rows** (RST): `WO_N_Header` 169,678 · `WO_N_Details` 184,982 · `WO_Status` 626,467 · `WO_Short_IDs` 6,744 · `WO_Event_History` 247,921 · `WO_N_Resource` 136,702 · `WO_N_Activity` 1,053,820 · `WO_C_header` 453,133 · `WO_C_Details` 453,145 · `WO_C_Activity` 2,290,895. KT: 520 / 520 / 684 / 268 / 4,139 / — / — / 137.
- **`WO_Type_Flag × Status`** (RST live): M — A 2,363 · C 72,501 · D 12,796 · H 1 · V 341; N — A 347 · C 75,925 · D 4,667 · P 2 · R 32 · V 703. **Open: 1,084 N + 2,705 M.** No K, no F on the live table.
- **Short id prefixes** (RST, top): `3CL-` 24,837 · `1BS-` 18,617 · `3RM-` 15,068 · `1SM-` 14,532 · `U-I` 11,709 … ~75 area prefixes, **zero `WO-`**; the shape is `<area>-YYMMDD-NNN` (`3CL-260826-010`). KT: `K-2…` 235 · `WO-` 216 · `K-K` 59 · `CP-` 1.
- **CP rule**: RST `cp_locations` 0, `cp_wos` 0; KT 1 / 1.
- **`Server_Name`**: NULL on all 169,678 headers and all 247,921 event rows. **`Source_Form`**: `WO Maintenance` 190,573 · `WO ScheduleX` 43,288 · `WOW` 14,059 · `WO Timesheet` 1.
- **`WO_Event_History`** columns: `Sys_WO_Event_Id numeric(18,0) NOT NULL`, `WO_ID numeric(18,0) NOT NULL`, `User_Id_Edited_By numeric NULL`, `Edited_Date datetime NULL`, `Event_Name varchar(150)`, **`event_details varchar(max)`**, `server_name varchar(50)`, `Source_Form varchar(50)`. Sample: `{WO_Title} changed from {Illegag bearer placement alarms} to {Illegal bearer placement alarms}`, `{Progress_Id} changed from {0} to {100}`, `{Status} changed from {A} to {V}` — user 113, `Edited_Date` with milliseconds.
- **Newest header**: 662704 `3CL-260826-010` "Check bin 16 level PE" V/N, `Progress_Id` 6, `Priority_Id` 1, start `2026-08-26 19:17:09`, end `2026-09-02 19:17:09` (**exactly 7 days → `week`**), `Week_No` 2026.35, `Last_Save_Date 2026-08-26 19:19:04.057`.
- **`dbo.Progress`** (RST): 1 No Progress · 2 Waiting Parts · 3 25% complete · 4 50% complete · 5 75% complete · 6 100% Complete · **7 Scheduled · 8 Assigned · 9 Machining**. Open WOs by progress: NULL 5 · 1 619 · 2 102 · 3 52 · 4 74 · 5 55 · 6 132 · **7 2,346 · 8 404**.
- **Headers without a details row: 7** (5 of them open). **`WO_Query`** 225 rows: Q 121 (113 emailed) · N 101 · A 3. **`WO_Responsible_User` 0 rows. `WO_Assessment_Log` 0 rows.** `linked_children` 1,894. `wos_with_po_lines` 54,585. `Parent_Location_Hierarchy` empty on 29,138 of 169,678; sample for 662704: `{(1)(RST-00)(Red Stag Timber Waipa)}{(6586)(3-00)(3 Secondary Processing)}{(67)(3CL-00)(08 Coastal)}{(407)(3CL-090)(090 Viking Bins)}{(1963)(3CL-090.170)(170 Bin 16)}`.
- **Objects** exist on RST: `Condition`, `Progress`, `WO_Assessment_Log`, `WO_Query`, `WO_Responsible_User` (tables); `funGetServerName` (scalar function); `wmsp_WO_QuerySelectDynamic`, `wmsp_WO_N_HeaderSelectDynamic` (procedures).
- **`wmsp_WO_QuerySelectDynamic`** body: `SELECT [WO_Id],[Query_ID],[Query_Type],[Query_From],[Query_Date],[Query_To],[Query_Desc],[Pair_Id],[Email_Sent] FROM [dbo].[WO_Query]` + `WHERE <string>` + `ORDER BY <string>` via `sp_executesql`.
- The five write procs (`wmsp_WO_StatusInsert`, `wmsp_WO_N_HeaderInsert`, `wmsp_WO_N_DetailsInsert`, `wmsp_WO_N_DetailsInsertUpdate`, `wmsp_WO_StatusDelete`) were pasted and are **W2's evidence** — CodeSmith inserts; `HeaderInsert` computes `Server_Name` from `funGetServerName(@Location_Id,'L')` and copies it to `WO_Status.SERVER_NAME`.

### 2.5 The SaaS as it stands (from the cards)

`db.rows()` returns dicts with `Decimal` → int/float and strings stripped; `s_` / `i_` / `f_` are belt-and-braces mappers used on every field (Landmines §B). `planner/rules.py` exports `STATUS_TITLES`, `iso()`, `timeOf()`, `civilDays()` — reused, not copied. The router pattern: `Annotated[Connection, Depends(db.get_conn)]`, `Annotated[int, Depends(get_current_actor)]`, `rid` from `request.state`, one `diag.log("F", …)` per request, `Model.model_validate(dict)` so `extra="forbid"` bites in the router. Errors: `HTTPException(status_code, detail={"code","message"})` renders flat through `main.py`'s handler; a `JSONResponse` for the service-level 400 (the planner's `WindowError` shape). `diag.log()` takes `persist=` (1.2.0). `test_openapi_contract.py` reads `app.openapi()` and never walks `router.routes`. The dialect gate in `test_planner_repo.py` scans `ALL_STATEMENTS` and the whole module source for `ISNULL(`, `GETDATE(`, `SELECT TOP`, `[dbo]` without a `PG-CONVERT` tag.

## 3. The changes, exactly

### 3.1 `app/workorders/sql.py` 1.0.0 (card 1)

Header as `planner/sql.py` (the five habits; **no colon in any SQL comment; the four banned tokens never spelled in the docstring**). Statements, all `dbo.`-prefixed, `COALESCE` for every null default, `CONCAT` for every string join, `OFFSET … FETCH NEXT` for every limit, named binds only:

- **`SEARCH_LIVE` / `SEARCH_ARCHIVE` / `SEARCH_BOTH`** — the two arms of `Search` v12 assembled in Python from `_LIVE_ARM` and `_ARCHIVE_ARM`, wrapped as `SELECT … FROM (<arm> [UNION ALL <arm>]) s ORDER BY s.Entry_date DESC, s.WO_ID DESC OFFSET :offset ROWS FETCH NEXT :take ROWS ONLY`. Each arm selects `WO_ID, RTRIM(COALESCE(Short_WO_Id,'')) AS Short_WO_Id, RTRIM(COALESCE(WO_Title,'')) AS WO_Title, RTRIM(COALESCE(a.Short_asset_Id,'')) AS Asset_ID, RTRIM(COALESCE(l.Short_Location_ID,'')) AS Location_Id, RTRIM(COALESCE(Status,'')) AS Status, COALESCE(d.Progress_Id,0) AS Progress_Id, <HasPO CASE as the NQ>, Entry_date` from `WO_N_Header`+`WO_N_Details` (live) or `WO_C_header`+`WO_C_Details` (archive) with the `Asset` / `Location` joins. Predicates as the NQ, verbatim in meaning: the one search term against `Short_WO_Id` **or** `WO_Title` via `LIKE CONCAT('%', :q, '%')` when `:q <> ''`; the three-way `:closed` (0 → `Status NOT IN ('C','D')`, 1 → all, 2 → `Status IN ('C','D')`) on the **live arm only** (the NQ has no closed predicate on the archive arm — parity); the four-way `:wo_type` (`''` all; `N` = flag N and location not CP; `CP` = flag N and location `CP` or `CP-%`; `M` = flag M) on both arms. The mode decides the statement: `includeArchive` 0 → `SEARCH_LIVE`, 2 → `SEARCH_ARCHIVE`, 1 → `SEARCH_BOTH` — the NQ's in-SQL `includeArchive` tests fold into the choice (recorded departure: each arm is plannable on its own; the rows are the same). **`ORDER BY Entry_date DESC, WO_ID DESC`** — the tie-break the NQ lacks (Landmines §B).
- **`WO_ITEM`** — `Item` + `Workorder Detail/Item` in one statement, **`LEFT JOIN dbo.WO_N_Details`** (OD-65; `d.WO_ID AS D_WO_ID` is the sentinel), plus the label joins from §2.3: `dbo.Priority` (`Short_Priority_Id`, `Priority_Title`), `dbo.WorkOrder_Group` (`Short_WO_Group_ID`, `WO_Group_Title`), `dbo.Reason`, `dbo.Fault`, `dbo.Cost_Center`, `dbo.Account`, `dbo.WOC1/2/3`, `dbo.Company` (`Company_Title`), `dbo.Supplier` ×2 (`Short_Supplier_Id`, `Company_Name` for charge-to and responsibility), `dbo.Users` ×7 (the six `Short_User_Id` names of `Item` + `User_Name` for `User_ID_Responsibility`), `dbo.Progress` (`Progress_Title`). No `Condition` join. `WHERE h.WO_ID = :wo_id`. Every char column `RTRIM(COALESCE(…,''))`; `Notes` raw.
- **`ARCHIVED_EXISTS`** — `SELECT COUNT(*) FROM dbo.WO_C_header WHERE WO_ID = :wo_id` (for the 404 code). **`LIVE_EXISTS`** — the same on `WO_N_Header` (the tab routes' guard).
- **`RESP_USERS`** — `WO Responsible User/List` with `includeRemoved = 0` baked in: `r.[Select]` becomes `r."Select"` — a reserved word on both engines, quoted with double quotes, which MSSQL accepts under the default `QUOTED_IDENTIFIER ON` (the repo test proves the statement parses on RST).
- **`RESOURCE_COMPARE`** — `ResourceCompare` v1.1.1 verbatim minus the `:tick` predicate (a refresh nonce with no API meaning), `ISNULL` → `COALESCE`, `+` → `CONCAT` on the `Item` label.
- **`LINKED_FAMILY`** — `LinkedFamily` v1.0.0, `ISNULL` → `COALESCE`; the NQ's `Badge` column is **not selected** — `rules.badge()` assembles the composite for the list, the linked rows and W1b alike (one function, tested once; 1.0.0 had it as a `CONCAT` in the SQL).
- **`EVENTS`** — `Event/Search` 1.1 verbatim (already portable; `OFFSET :offset ROWS FETCH NEXT :take ROWS ONLY`), plus `Edited_Date DESC, Sys_WO_Event_Id DESC` as the deterministic order, and `Sys_WO_Event_Id` selected.
- **`QUERIES`** — the proc's nine columns from `dbo.WO_Query WHERE WO_Id = :wo_id ORDER BY Query_Date DESC, Query_ID DESC`; `Query_Desc` raw (its type was not read; a `text` column rejects `COALESCE`).
- **`PO_LINES`** — `GetPODetails` verbatim with `dbo.` (`ORDER BY h.Short_PO_Id, d.PO_Detail_ID`); `PO_Description` raw.
- **`PROGRESS_ALL`** — `SELECT Progress_Id, RTRIM(COALESCE(Progress_Title,'')) AS Progress_Title, RTRIM(COALESCE(Short_Progress_Id,'')) AS Short_Progress_Id FROM dbo.Progress WHERE COALESCE(Active,'1') = '1' ORDER BY Progress_Id` (OD-67 — by id, not title).
- `ALL_STATEMENTS = {name: sql}` — **thirteen entries**: `search_live`, `search_archive`, `search_both`, `wo_item`, `live_exists`, `archived_exists`, `resp_users`, `resource_compare`, `linked_family`, `events`, `queries`, `po_lines`, `progress_all`. (1.0.0 said eleven; the gate parametrises over thirteen.)

The Assessment card's raw select is **not** ported: `WO_Assessment_Log` is empty on RST, the card is a W1b decision (draw it empty or drop it — a W1b OD), and a statement for an empty table adds a route with nothing to test. Recorded in §9.3.

### 3.2 `app/workorders/rules.py` 1.0.0 (card 2) — pure

No imports beyond `datetime`, `re`, and `app.planner.rules` (`civilDays`, `iso`, `STATUS_TITLES`). Every function is a port of one transform in §2.2, with the source component named in its docstring:

- `complete_within(start, end) -> str` — `range` when either is None; `days = civilDays(iso(start), iso(end))`; `months = (end.year - start.year) * 12 + (end.month - start.month)`, minus 1 when `end.day < start.day` (the calendar-month twin of `system.date.monthsBetween`); then the oracle's ladder: 1 → `day`, 7 → `week`, 14 → `nextshut`, `months == 1 and days <= 31` → `month`, `months == 3 and days <= 93` → `3month`, else `range`. **Civil days, never `(end - start).days` on datetimes** — `daysBetween` is asymmetric across DST; `civilDays` is the fix already in the tree.
- `hierarchy_titles(raw) -> list[str]` / `hierarchy(raw) -> str` — the `{(id)(short)(title)}` parser; `[]` for empty/None/`'None'`; on a malformed string the whole raw string as one item (the oracle's `except: return str(raw)`). The record ships both `hierarchy` (`' > '.join`) and `hierarchyRaw`.
- `badge(status, short_id, progress_id, has_po) -> str` — `status|shortId|prog|hasPO` (status omitted with its pipe when `''`, exactly the list transform's `_base`).
- `resources_totals(rows) -> tuple[float, float, float]` — planned, actual, diff = actual − planned, from `planCost` / `actCost` with None as 0.
- `money(n) -> str` — the `_m()` formatter (`$1,234.56`, `-$…`); `resources_line(planned, actual, diff)` → `Planned $x  |  Actual $y  |  Diff ±$z` (sign `+` only when diff > 0). Served as `resources.line` so W1b shows the oracle's string byte-for-byte.
- `event_detail(raw) -> str` — braces removed, `''` for None.
- `query_type_label(code) -> str` — `Q` → Query, `R` → Reply, else the code.
- `rel_label(level, selected) -> str` — `{0: Parent, 1: Child, 2: Grandchild}` else `str(level)`, `+ ' (this WO)'` when selected.
- `is_cp_location(short_location)` and `filters_for(status, type_flag, short_location) -> dict` — the handoff rule: `includeClosed` 1 when status ∈ {C, D} else 0; `woType` `M` when the flag is `M`, `CP` when the location is `CP` or starts with `CP-`, else `N`; `includeArchive` 0 (an archived id never reaches this — OD-68).
- `stamp(d) -> str` — `'yyyy-MM-dd HH:mm:ss'` for a datetime, `'yyyy-MM-dd 00:00:00'` for a date, `''` for None; milliseconds dropped (a display stamp — W3's optimistic lock reads the raw column itself, §9.3). `status_title(code)` — `STATUS_TITLES`, the code for an unknown one.
- `VERSION = "1.0.0"`; `SEGMENTS = ('day','week','month','3month','nextshut','range')` for the schema's `Literal`; `STATUS_CODES` from `STATUS_TITLES`.

### 3.3 `app/workorders/repo.py` 1.0.0 (card 4)

- `search(conn, *, wo_type, closed, archive, q, limit, offset) -> tuple[list[dict], bool]` — picks the statement by `archive`, binds `take = limit + 1` (and `closed` only on the live / both statements — the archive statement has no such bind), maps rows, returns `(rows[:limit], len(rows) > limit)`. Row dict: `{id, sid, title, asset, loc, status, prog, hasPO, entry, badge}` (`entry` = `stamp(Entry_date)`, `badge` from rules).
- `fetch_item(conn, wo_id) -> dict | None` — one `WO_ITEM` row → the record dict (§3.4 keys); `detailsMissing = r["D_WO_ID"] is None`; ids `i_()` (NULL → 0, the transform's default), strings `s_()`, money/hours `f_()`, dates `iso()` + `timeOf()` for start/end (the planner convention), `stamp()` for every other datetime; `statusTitle`, `completeWithin`, `hierarchy`, `hierarchyRaw`, `filtersFor` from rules; then `respUsers`, `resources`, `progressAll` from their own reads. Returns `None` when no row.
- `archived_exists(conn, wo_id) -> bool` · `live_exists(conn, wo_id) -> bool`.
- `fetch_resp_users(conn, wo_id)` → `[{userId, shortId, name}]`; `fetch_resources(conn, wo_id)` → `{rows: [{type, item, planQty, planCost, actQty, actCost, delta}], planned, actual, diff, line}` (NULL qty/cost stay `None` — the "not used yet" blank; `delta` is the SQL's; totals from rules); `fetch_progress(conn)` → `[{id, title, short}]`.
- `fetch_linked(conn, wo_id)` → `{rows: [{id, sid, title, status, prog, hasPO, badge, level, rel, parentId, parentSid, start, entry, selected}], root, count}`; `fetch_events(conn, wo_id, offset, limit)` → `(rows, more)` with `{seq, eventId, event, detail, date, editorId, editor, siteCode, siteName, source, server}` (`seq` = offset + i + 1); `fetch_queries(conn, wo_id)` → `[{id, type, typeLabel, queryFrom, queryTo, desc, date, pairId, emailed}]` (`emailed` = `Email_Sent` in `1`/`Y`/`True`); `fetch_po_lines(conn, wo_id)` → `[{poSid, status, badge, due, supplier, description, qty, unitCost}]` (`due` = `iso()`; `badge` = `status|poSid`).
- No caches, no module state. `WO_TYPES = ('', 'N', 'CP', 'M')` for the router's check.

### 3.4 `app/workorders/schemas.py` 1.0.0 (card 6)

`_Strict` as the planner's (`extra="forbid"`, `populate_by_name=True`); `_Envelope(_Strict)` carries the OD-14 four. `ApiError` imported from `app.planner.schemas` (one flat error shape app-wide). Models: `SearchFilters` (`woType: Literal['', 'N', 'CP', 'M'], includeClosed, includeArchive, search, limit, offset`), `WoListRow`, `WoList` (`rows, count, more, filters` + envelope), `RespUser`, `ResourceRow`, `Resources`, `ProgressRow`, `WoRecord` (envelope + the keys below), `LinkedRow`, `LinkedFamily` (`rows, count, root`), `EventRow`, `EventPage` (`rows, count, more, offset`), `QueryRow` (`id, type, typeLabel, queryFrom, queryTo, desc, date, pairId, emailed` — **not `from`/`to`**: `from` is the S1d alias trap, avoided outright), `QueryList`, `PoLine`, `PoList`. Every list payload carries `rows` + `count`.

`WoRecord` keys (camelCase, D-9; the column each comes from is in the card's docstring):
`id, sid, title, status, statusTitle, type, overDue, weekNo, start, startTime, end, endTime, logged, companyId, companyTitle, assetId, asset, assetTitle, locId, loc, locTitle, hierarchy, hierarchyRaw, durationHrs, estCost, downTime, priId, priShort, priTitle, groupId, groupShort, groupTitle, reasonId, reasonTitle, faultId, faultTitle, costCenterId, costCenterTitle, accountId, accountTitle, chargeToId, chargeToShort, chargeToName, respSupplierId, respSupplierShort, respSupplierName, woc1Id, woc1Title, woc2Id, woc2Title, woc3Id, woc3Title, ref1, ref2, prog, progTitle, notes, requestedById, respUserId, respUserName, conditionId, generatedFrom, intrusive, intrusiveComplete, intrusiveCompleteDate, firstActivity, lastActivity, meterId, meterReading, printed, progressDate, createdBy, ackBy, ackDate, approvedBy, approvedDate, closedBy, closedDate, cancelledBy, cancelledDate, lastSaveBy, lastSaveDate, completeWithin, detailsMissing, respUsers, resources, progressAll, filtersFor` — **88 keys + the 4 of the envelope = 92**, cross-checked against the repo's dict on 2026-09-19. `ref1` = `Entered_By` (the view's "Ref. 1"), `ref2` = `Reference`. `completeWithin: Literal[...]` from `rules.SEGMENTS`; `filtersFor: SearchFilters` (search `''`, limit 200, offset 0).

### 3.5 `app/workorders/router.py` 1.0.0 (card 7)

`router = APIRouter(prefix="/workorders", tags=["workorders"])`, `__version__ = "1.0.0"` → `apiVersion`. Plain `def`. `WoId = Annotated[int, Path(gt=0)]`. Six routes:

| Route | Query / path | 200 | Errors |
|---|---|---|---|
| `GET /workorders` | `woType` ∈ `''` `N` `CP` `M` (default `N`) · `includeClosed` 0–2 (0) · `includeArchive` 0–2 (0) · `search` str (`''`, trimmed) · `limit` 1–1000 (200) · `offset` ≥ 0 (0) | `WoList` | 400 `BAD_FILTER` on a `woType` outside the four (a `JSONResponse` in the planner's `WindowError` shape); 422 from FastAPI on range violations |
| `GET /workorders/{wo_id}` | `wo_id > 0` | `WoRecord` | 404 `ARCHIVED` when only `WO_C_header` has it, 404 `NOT_FOUND` otherwise (both `HTTPException(detail={code, message})`); `[G]` line on each |
| `GET /workorders/{wo_id}/events` | `offset` ≥ 0 (0), `limit` 1–1000 (200) | `EventPage` | 404 as above when not live |
| `GET /workorders/{wo_id}/linked` | — | `LinkedFamily` | 404 when not live |
| `GET /workorders/{wo_id}/queries` | — | `QueryList` | 404 when not live |
| `GET /workorders/{wo_id}/pos` | — | `PoList` | 404 when not live |

One `[F]` line per 200, **`persist=False`** (OD-69): `wo search type=N closed=0 archive=0 q='' offset=0 rows=200 more=True in 123 ms` · `wo 662704 3CL-260826-010 status=V prog=6 within=week resp=0 res=2 details=ok in 41 ms` (`details=missing` for the seven) · `wo 662704 events offset=0 rows=5 more=False in 9 ms` · `wo 662704 linked rows=1 root=3CL-260826-010 in 7 ms` · `wo 662704 queries rows=0 in 3 ms` · `wo 662704 pos rows=0 in 3 ms`. The record's `detailsMissing` case logs one **`[G]`** (`wo 12345 has no WO_N_Details row`, persisted — a data-quality fact worth a row); the two 404s log a `[G]` each (`wo <id> is archived` / `wo <id> not found`). `WoRecord.model_validate(dict)` etc. in the router, so `extra="forbid"` fires here.

### 3.6 `tests/test_openapi_contract.py` 1.0.0 → 1.1.0 (card 9)

Keeps the eight range tests untouched. Adds nine: the six workorders paths published, GET only; `/workorders` parameters are exactly `woType, includeClosed, includeArchive, search, limit, offset` with the defaults and bounds above; `wo_id` is an integer path param with `exclusiveMinimum 0`; the events params; the list response shape; `WoRecord.additionalProperties is False` and its `properties` and `required` sets equal `WoRecord.model_fields`; 400/401 on the list and 404/401 on the five id routes documented with `ApiError`; no `from_` anywhere in the six operations or `components`; `info.version == main.__version__ == "0.5.0"`.

### 3.7 `app/main.py` card 1.0.6 → 1.0.7, app 0.4.0 → 0.5.0 (card 10)

Three lines: `from app.workorders import router as workorders_router`; `api.include_router(workorders_router.router)` after the planner's; `"workorders": workorders_router.__version__` in `/health` `versions`. `__version__ = "0.5.0"` (minor: new published paths, WoW §2). Header records both numbers as 1.0.6 does.

### 3.8 `web/openapi-ts.config.ts` 1.0.2 → 1.0.3 (card 11)

`input: '../docs/api/openapi_0_5_0.json'`. Nothing else. The generated client gains `listWorkordersApiV1WorkordersGetOptions()` and friends; nothing in `web/src` imports them yet (W1b).

## 4. Traps

1. **`Select` is a reserved word on both engines.** `WO_Responsible_User.[Select]` is written `r."Select"`; if RST's session has `QUOTED_IDENTIFIER OFF` the repo test fails on parse — then the fallback is a `PG-CONVERT`-tagged `[Select]` line, decided at the smoke, not guessed now.
2. **`LIKE CONCAT('%', :q, '%')` on `char(25)`** matches with the padding in place — fine, but a `q` of `'%'` or `'_'` is a wildcard on both engines. Parity with the NQ (which had the same); the router trims, nothing else. Not escaped (recorded).
3. **The archive arm has no closed predicate.** Passing `includeClosed=0` with `includeArchive=2` returns archived rows regardless — that is the NQ's behaviour and the chips can never produce it (Archive zeroes Closed). The API allows it; the repo test pins that `:closed` is absent from `SEARCH_ARCHIVE`.
4. **`OFFSET/FETCH` over a `UNION ALL` of 620 k rows** with two `EXISTS` per row in the select list: MSSQL sorts before projecting, so `SEARCH_BOTH` should be a sort on `Entry_date` (indexed? unknown) plus 201 `EXISTS` pairs, not 620 k. The smoke times `includeArchive=1` cold; if it lands in the trail as slow (≥ 2000 ms, OD-59) that is a finding for W1b's UX, not a fix here.
5. **`Decimal` ids**: `WO_ID` is `numeric(18,0)` — `db._clean` gives an int; `i_()` on top. `Week_No numeric(6,2)` must stay a float (`f_`), as the planner learned.
6. **`Progress_Id` NULL vs 0**: the oracle defaults NULL to 0 and lights nothing; the API ships `prog: 0` — W1b treats 0 as "no card lit", as `WOProgress` does when `progressId` matches none.
7. **`Email_Sent`** — its type was not read (`0`/`1` in the domain query). `emailed = s_(v).upper() in ('1', 'Y', 'TRUE')` handles int, char and bit.
8. **`Query_From` / `Query_To`** may be `char(n)` — `s_()`; **`Query_Desc`** may be `text`/`varchar(max)` — selected raw, shipped whole.
9. **`stamp()` on a `date`** (not datetime): `Due_Date`, `Request_*` are `datetime` on RST, but a future PG column may be `date` — `stamp` handles both.
10. **The dialect gate reads the whole `sql.py`**: the docstring describes the habits without spelling the four tokens (the 1.0.0/1.0.1 lesson in `planner/sql.py`).
11. **`ResourceCompare`'s `FULL OUTER JOIN`** on derived tables parses on PostgreSQL; `CAST(x AS varchar(20))` in `EVENTS` too. No tag needed. `WHERE COALESCE(:tick,0) >= 0` is dropped, not tagged.
12. **The record is one statement with 23 joins.** All `LEFT`; the row count is 1 by the `WO_ID` key. If RST's plan is slow (> 200 ms measured at the smoke), the label joins split into a second statement in a **1.0.1** of card 1 — measured, not assumed.
13. **`test_openapi_contract` builds the schema with `app.openapi()`** — importing `app.main` at test time is fine under `WORKMATE_ENV=test`; the new module imports nothing that opens a connection at import.
14. **Two contract files on disk** for the time between the export and the `git rm` — the drop block does both before the frontend regenerates.
15. **The `search` param name** is `search`, not `q`, on the wire — one name in the schema, the router and the tests; `q` stays a Python variable only.
16. **`ruff format --check`** is in the smoke (the router 1.1.1 lesson). The cards were written black-style (double quotes, magic trailing commas, ≤ 110); a reflow it still wants is a same-session `1.0.1` of that card, never a silent difference between disk and PK.
17. **The dates live on the header, not the details.** A detail-less WO still has a `completeWithin` from its own `Request_*` dates — the test asserts membership in `SEGMENTS`, not `range`.

## 5. Test plan — predicted per file

| File | Cases | What |
|---|---|---|
| `test_workorders_rules.py` (card 3) | **22** | `complete_within`: 7 d → week (662704's real pair), 1 → day, 14 → nextshut, Jan 15 → Feb 15 → month, Jan 31 → Mar 3 → month (31 days, one calendar month — the ladder's boundary holds), Jan 15 → Feb 17 → range (33 days), Apr 1 → Jul 1 → 3month, 100 d → range, None → range, a DST-crossing 7 d pair (NZ, 2026-09-27) → week · `hierarchy_titles`: the RST sample → 5 titles, `''`/`None`/`'None'` → `[]`, malformed → `[raw]` · `badge` with and without status · `money` (`$1,234.50`, `-$0.50`, `$0.00`, rounding) / `resources_totals` / `resources_line` signs · `event_detail` · `query_type_label` Q/R/N/A/None · `rel_label` 0/1/2/9 ± selected · `filters_for` ×8 in one test (V N `3CL-090` → 0/N; C → closed 1; D; M over CP; `CP-01` → CP; `CP` → CP; `CPX` → N; blanks → N) · `stamp` datetime / date / None / ms dropped + `status_title` + `SEGMENTS` + `STATUS_CODES` |
| `test_workorders_repo.py` (card 5) | **46** | **no DB (31):** the gate over thirteen statements (×13 idioms + ×13 colon = 26, module source, named binds) + three structural checks (the search variants and their orders, the LEFT JOIN sentinel, the deterministic event / progress orders); **RST (15):** default search → 200 rows, every status ∉ {C, D}, badge = composite, `more` True, first row 662704; `closed=2` → every row ∈ {C, D}; `archive=2` → every id archived, none live; `closed=1 + archive=1` → 20 + more; `search='3CL-260826-01'` finds 662704 and every row contains the term in sid or title, `'bin 16'` too; paging disjoint + order `(entry, id)` non-increasing; `fetch_item(662704)` (sid, V, prog 6, pri 1, `100% Complete`, start/startTime, `week`, weekNo 2026.35, lastSaveDate to the second, hierarchy, `detailsMissing False`, `respUsers []`, `filtersFor`); `fetch_item` on a detail-less header (control) → `detailsMissing True`, zeros; the exists helpers and the archive split (control); events (≥ 5, seq, newest first, braces gone, `WO Maintenance`, paging); linked (lone family + a real child by control); queries (a Q by control, labels, `emailed` bool, order, `[]` for an unknown); po lines (control, badge, due); resources (keys, line, diff, `(unplanned)` ↔ `planQty None`); progress (ids sorted, ⊇ 1..6, `No Progress`) |
| `test_workorders_api.py` (card 8) | **24** | list 200 + envelope keys exactly `{rows,count,more,filters,ok,apiVersion,actor,ms}`, `filters` echoes the defaults, 200 rows + more; rows open N, badge, first 662704; `woType=X` → 400 `BAD_FILTER` flat; `woType=''`/`CP` (count 0 on RST)/`M`; `includeClosed=3` / `includeArchive=-1` / `limit=1001` / `limit=0` / `offset=-1` → 422; paging disjoint; the search term trimmed; closed / archive modes; record keys == `WoRecord.model_fields`, envelope; record values 662704; 999999999 → 404 `NOT_FOUND` flat; an archive-only id (control) → 404 `ARCHIVED`; `0` / `-1` / `abc` → 422; a detail-less id → 200, `detailsMissing`, one `[G]` on stdout with the actor; `/events` shape + paging + `limit=0` 422; `/linked` root; `/queries`; `/pos`; each tab 404 on 999999999; POST → 405 ×2; 401 without the actor; response-model drift → 500 (monkeypatched `fetch_item`); one `[F]` on stdout per request **and `persist=False`** proven by a spy on `diag.log`; `/health` `version 0.5.0` + `versions.workorders` |
| `test_openapi_contract.py` 1.1.0 (card 9) | **+9** (8 → 17) | §3.6 |

**Predicted: backend `319 passed, 2 skipped`** (218 + 22 + 46 + 24 + 9 — read from the cards' own `def test_` / `parametrize` counts on 2026-09-19; 1.0.0 predicted 307 from a draft count), exit 0. **Frontend `205 passed in 15 files`**, exit 0 — unchanged, re-run because the generated client changes (and `dist/` does, WoW §6). Both bare.

## 6. Open decisions — 🤙 required

| OD | Proposal | Why |
|---|---|---|
| **OD-62** | **W1 ships in two slices**: **W1a** this API (this spec), **W1b** the read-only page (next spec). | Eleven backend cards plus a 20-file page is two S1k's in one gate; the S1c → S1e precedent. |
| **OD-63** | The list takes **one `search` term** (sid **or** title, the NQ's own `OR`), `woType` / `includeClosed` / `includeArchive` with the NQ's 0/1/2 semantics and the view's `N` / 0 / 0 defaults. `woTitle`, `shortAssetId`, `shortLocationId` are **not ported** — the view never sets them. | Port what the oracle uses. Adding them later is one column each. |
| **OD-64** | **Paging**: `limit` 1–1000 (200), `offset`, `more` from a `limit + 1` fetch, **no total**; order `Entry_date DESC, WO_ID DESC`. | 170 k live + 453 k archived on RST; the oracle returns everything (520 at KT). A COUNT over the union costs a full scan per keystroke; `more` is honest and free. |
| **OD-65** | The record **`LEFT JOIN`s `WO_N_Details`** and ships `detailsMissing`; one `[G]` per such read. | Seven live headers have no details row (five open); the oracle's INNER JOIN shows them blank while listing them. |
| **OD-66** | **Labels resolved server-side** in the record, regardless of the reference row's `Active`; **`refs` deferred to W3.** | A read has no dropdowns; the oracle's active-only lists would blank a retired reason. W3's editing needs the active lists — that is when `refs` earns its route. |
| **OD-67** | **`progressAll` on the record from `dbo.Progress`** (active, `ORDER BY Progress_Id`); the picture row (W1b) draws one card per row — the oracle's six icons for 1–6, a plain card beyond. | 2,750 of RST's 3,789 open WOs sit at 7 or 8; the six-card row lights nothing for them. |
| **OD-68** | An id found only in `WO_C_header` is **404 `ARCHIVED`**; the archive record read is a listed item (§9.3), not this slice. | Parity today is a blank record (the oracle's `Item` reads `WO_N_Header` only). A named 404 is more honest than the blank and cheaper than porting `WO_C_*` unread. |
| **OD-69** | The six routes' `[F]` lines **print, don't persist** (`persist=False`); the middleware still persists ≥ 400 / ≥ 2000 ms (OD-59). | The trail is for writes and failures (D1 audit §5); the planner poll's 2 rows/min is item 46's open question — the reads here don't add to it. |
| **OD-70** | Contract keys **camelCase** (D-9, the planner's style), 88 record keys as §3.4; `main` **0.4.0 → 0.5.0**, `openapi_0_5_0.json`, `pnpm gen:api`; `apiVersion` = `workorders/router.__version__` **1.0.0**. | New published paths are a minor bump (WoW §2). |
| **OD-71** | The record carries **`filtersFor`** (the `onStartup` handoff rule, computed server-side). | W1b's `/workorders/$id` needs it to show the list the record belongs to; the rule is one function either side and the data is already in the row. |

**Delegated 2026-09-19:** all ten answered "ok" one by one (OD-64 with the standing priority spelled out: *speed, no lagging like the .NET app* — the smoke's two timings are the check). Recorded as delegated; a 🤙 on this file signs them.

## 7. Smoke

Predicted before the run; pasted verbatim after; the trail read last (WoW §6.1). The server was proven **down** before the drop (zero listeners on 8000, 2026-09-19) and is **started fresh at step 6**.

1. **Drop** — `Test-Path` on the eleven cards in Downloads (all True or stop), copy to targets, `New-Item backend\app\workorders\__init__.py`, `git status --short` shows the new package + the four modified files.
2. **Lint/format** — `cd backend; uv run ruff check .; uv run ruff format --check .; "$LASTEXITCODE"` → 0 (the 1.1.1 lesson: format, not just check).
3. **Suite** — `uv run pytest; "$LASTEXITCODE"` → `319 passed, 2 skipped`, 0. Persist off under test; `Diag_Log` gains nothing (proven at step 9).
4. **Export** — `uv run python -c "import json, pathlib; from app.main import app; pathlib.Path('../docs/api/openapi_0_5_0.json').write_text(json.dumps(app.openapi(), indent=2), encoding='utf-8')"`; `git rm docs/api/openapi_0_4_0.json`; `Select-String '"version"' ..\docs\api\openapi_0_5_0.json | Select -First 1` → `0.5.0`; `(Get-Content ..\docs\api\openapi_0_5_0.json | Select-String '"/api/v1/workorders').Count` → 6.
5. **Frontend** — `cd ..\web; pnpm gen:api; pnpm lint; pnpm test; pnpm build; "$LASTEXITCODE"` → generated files changed under `src/api/client/**`, lint clean, `205 passed in 15 files`, build OK, `gci dist\index.html`.
6. **Server** — `cd ..\backend; Start-Process powershell -ArgumentList '-NoExit','-Command','uv run fastapi dev app/main.py'`; wait; `Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object OwningProcess | Format-Table` → **exactly one PID**.
7. **Request set** (`irm` each; paste the JSON heads; `Measure-Command` on the two marked):
   `/api/v1/health` → `version 0.5.0`, `versions.workorders 1.0.0` · `/api/v1/workorders` → `count 200, more true`, first row `662704`, every status ∉ C/D · `?includeClosed=2&limit=3` · `?includeArchive=2&limit=3` (**time it**) · `?includeArchive=1&limit=3` (**time it** — trap 4) · `?woType=CP` → `count 0` (RST) · `?woType=X` → 400 `BAD_FILTER` · `?search=bin 16` · `/workorders/662704` → the record: `sid`, `completeWithin week`, `hierarchy` five titles, `prog 6`, `progTitle 100% Complete`, `progressAll` nine rows, `filtersFor {0,0,N}` (**time it** — trap 12) · `/workorders/999999999` → 404 `NOT_FOUND` · `/workorders/<archive-only id from the suite's control query>` → 404 `ARCHIVED` · `/workorders/662704/events` → 5 rows, newest `WO_Title changed…` cleaned · `/linked` · `/queries` · `/pos` · a detail-less id → `detailsMissing true`.
8. **Screenshot** — none (no page). `/docs` opened once: the six routes under **workorders**.
9. **Trail** — wait 2 s, `scripts\Show-DiagTrail.ps1 -UserId 21 -Minutes 15`. **Predicted rows:** the three `[G]` outcomes from step 7 (`… 400 …`, two `… 404 …`) plus the router's own `[G]`s (`wo … not found`, `wo … is archived`), the `[G] wo <id> has no WO_N_Details row`, the planner polls if a tab is open — and **no row for any 200 workorders read** unless one crossed 2000 ms (then it is listed, and trap 4 is a finding).
10. **Commit + tag** — `git add -A; git commit -m "W1a WOMaint read API - six routes, search both arms, record with labels, tabs; main 0.5.0, openapi 0.5.0"; git tag w1a-api-1.0.0`; `git log --oneline -2`.

## 8. Acceptance

- Backend `319 passed, 2 skipped`, frontend `205 passed`, ruff (check + format) and eslint clean, all exit 0, all pasted.
- `/health` reports `0.5.0` and `versions.workorders`; `openapi_0_5_0.json` is the only contract file; the generated client compiles and the planner still builds.
- The request set matches its predictions row for row; the trail matches §7.9.
- Every statement in `sql.py` passes the gate; every one parses on RST (the repo test runs each once).
- `Diag_Log` row count before and after the suite is equal (read at step 3 and step 9).
- The raw log records the measured timings of `includeArchive=1`, `includeArchive=2` and the 23-join record.

## 9. Consequences

### 9.1 Doc corrections for the next compiled set

- Landmines §E: `WO_Event_History.event_details` is `varchar(max)` on RST (the 990 cap is the writer's); `Server_Name` is NULL on every RST header and event; RST's `Source_Form` is `WO Maintenance` / `WO ScheduleX` / `WOW`; `dbo.Progress` has nine rows on RST (7 Scheduled, 8 Assigned, 9 Machining), six at KT; `WO_Responsible_User` and `WO_Assessment_Log` are empty on RST; seven live headers have no details row; RST short ids are `<area>-YYMMDD-NNN`, no `WO-`; RST has no CP location.
- Index §2/§3.3: the 09-15 log, the two 09-19 logs, the six reference cards and this spec.
- Ways of Working §2: a new package gets its empty `__init__.py` in the drop block (the D1a precedent, now twice); a spec's test counts are read from the cards before the run, and a draft count that moved is a 1.0.1 of the spec, not a note in the log.

### 9.2 What this unblocks

W1b (the page — every read it needs is one generated hook away); W2's spec (the five procs are in §2.4; `filtersFor` and `badge` are the list's contract already); the auth slice (nothing here assumes an identity beyond `Depends(get_current_actor)`).

### 9.3 Candidate open items — raised in the log, not here

The archive record read (`WO_C_header` + `WO_C_Details`, columns to be read first); the Assessment card (empty on RST — draw or drop, W1b); `Condition` resolved to a title (columns unread); the `search` wildcard escape; W3's optimistic-lock stamp (`Last_Save_Date` with its milliseconds, raw); the `includeArchive=1` timing on RST; `ItemHeader` (unused by the view — no port); `WO_Query` codes `N` and `A` (RST has them, the oracle shows them raw — what are they?).

## 10. Changelog

- 1.0.1 (2026-09-19) After the cards were cut, same day. Four corrections against the draft: `ALL_STATEMENTS` has thirteen entries, not eleven (§1, §3.1); `QueryRow` keys are `queryFrom` / `queryTo`, not `from` / `to` (§3.4); the linked badge is `rules.badge()`, not a SQL `CONCAT` (§3.1); test counts read from the cards — repo 46 (31 + 15), total **319** (§5, §7, §8). Status: built on a delegation. Also §5: `Jan 31 → Mar 3` is `month` by the oracle's ladder (31 days, one calendar month), not `range`; the `range` boundary case is `Jan 15 → Feb 17` (33 days). Traps 16 and 17 added.
- 1.0.0 (2026-09-19) Draft for 🤙. Written after the 09-19 exports and Block W1-E + addenda.
