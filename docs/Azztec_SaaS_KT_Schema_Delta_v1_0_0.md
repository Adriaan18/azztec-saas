# Azztec SaaS — KT Schema Delta (dbWorkmate_KT vs the RST dev DB)

**File:** Azztec_SaaS_KT_Schema_Delta_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-13 · **Author:** Adriaan
**Status:** Evidence complete — input to the **uplift audit**. Nothing here is signed; §8 lists what the audit decides.
**Target path:** `docs/`
**Sources:** `dbWorkmate_KT` (restored read-only on AzztecDev 2026-09-13 from `dbWorkmate_backup_2026_09_12_233033_4351464.bak`) · `dbWorkmate` (RST) · `MainSCADA_Timberlands_2026-09-10_1900.zip` (the Ignition project export) · catalog and reference queries pasted 2026-09-13 (raw log of that date)

---

## 1. Why this exists

RST is the SaaS dev database because it carries twenty years of real CMMS data — but it is the **.NET-era schema**. The Ignition edition at KT added tables and columns on top of that schema for seven months. Every one of those additions is a place the SaaS port can hit "does not exist on RST" (it already has: `pinTable=False`, OD-1). This report is the scope/compare Adriaan asked for on 2026-09-13: what exists at KT that RST lacks, which of it is actually used, and what should cross.

**The database says what exists; the gateway export says what is used.** Both were read. Every object below is classified on both.

## 2. Provenance (from `RESTORE HEADERONLY` / `FILELISTONLY`, 2026-09-13)

| Fact | Value |
|---|---|
| Source server | `KTSQL02`, SQL Server 2022 (16.0.4275), backup by `TMCLIMITED\SQLServiceAccount` |
| Backup | full, uncompressed, 78,731,776 bytes, taken 2026-09-13 00:32:36–38 (2 s) |
| Database | `dbWorkmate`, data `D:\SQLData\dbWorkmate.mdf` 95 MB, log `E:\SQLLogs\dbTLL_log.ldf` 16 MB, compat level **100**, FULL recovery, created 2026-02-13 |
| Restored as | `dbWorkmate_KT` on AzztecDev (17.0), `WITH MOVE` to the instance defaults, physical version upgraded 957 → 998, set **READ_ONLY**, compat left at 100 |
| Consequence | **one-way door**: a database from AzztecDev (2025) can never be restored onto KTSQL02 (2022). The oracle copy stays untouched; `svc_workmate` has no user in it yet (needs a read-write flip to add one — only when `parity_range.py` runs) |
| The other oracle | the project export is dated **2026-09-10**; the DB backup **2026-09-12**. Two days apart; nothing below depends on the gap |

## 3. Headline counts

| | tables | views | procs |
|---|---|---|---|
| `dbWorkmate_KT` | 280 | 24 | 1099 |
| `dbWorkmate` (RST) | 255 | 67 | 1121 |

The delta is **not one-directional in the catalog**, but it is in practice: RST's extra 48 views / 27 procs / 17 functions are RST's own site reporting layer (`vRST_*`, `vw_RST_*`, three generations of `vChristmasShut`, `vTransacitonManager*`, `vProjectActuals`, `vSiteAccessvsTimeSheetvsCMMS` …). The SaaS reads none of them (`sql.py` goes to tables). They are a **constraint, not scope**: adding nullable columns beneath them is safe; renaming or retyping anything they select is not. The 21 RST-only tables are `TEMP_*` staging, `DataCleanLog`, `RST_ErrorLog`, `Xmas_Budget` — site-local, not scope either.

## 4. KT-only tables — 46 found, 21 real

### 4.1 Bucket 1 — the SaaS port needs these (in slice order)

| Table | Rows | Used by (export) | Shape as read | Lands with |
|---|---|---|---|---|
| `dbo.WO_N_Plan` | 4 | `pm_engine`, planner (5 scripts) | `WO_ID numeric(18,0)` PK clustered · `Pinned char(1) NOT NULL DEFAULT 'N'` · `Pinned_By numeric(18,0)` · `Pinned_On datetime` · `Prev_Start datetime` · `Note varchar(255)` · `Server_Name varchar(50)` · `Entry_Date datetime NOT NULL DEFAULT getdate()` · `Last_Save_Date datetime` | **S3** (migration 0002 as already planned — now a transcription). Lifecycle from the rows: one row per WO, persists, `Pinned` flips; all four KT rows are `N` with `Prev_Start` = the engine date and `Note = 'Planner move 2026-09-07 -> 2026-09-08'`; `Server_Name = 'Perspective'` (OD-3 → `'SaaS'`) |
| `dbo.Diag_Log` | 69,656 | 3 NQ, 18 scripts, 1 view | `Diag_Id int identity` PK · `Logged_At datetime2(3) NOT NULL` · `Session_Id varchar(64) NOT NULL` · `Wm_User_Id int` · `Site_Code varchar(8)` · `Source varchar(64) NOT NULL` · `Tier char(1) NOT NULL` · `Msg_Level varchar(8) NOT NULL` · `Message nvarchar(1000) NOT NULL` · `Detail nvarchar(max)` · IX `Logged_At`, IX `(Wm_User_Id, Logged_At)` | **diag persist mode** (D-8 already names this table). Companions: `fn_Diag_UserTrail`, `vw_Diag_Problems`, `vw_Diag_WhoIsOn` (all used). The KT rows are real staff activity incl. email addresses — never copied, never pasted; the SaaS starts empty |
| `dbo.Module_Settings` | 2 | 5 scripts, 1 view | `Module_Code varchar(30)` PK · `Is_Enabled char(1) NOT NULL DEFAULT 'N'` · `Notes varchar(255)` · `Updated_Date` · `Updated_By varchar(30)` · `Run_Token varchar(64)` · `Run_Started datetime` · `Run_Host varchar(80)` | **S5** — the module enable switch plus the scheduled-run lock (`Run_Token`/`Run_Started`/`Run_Host`) D-7's CLI jobs need |
| `dbo.Diag_NightShift` | 140 | 3 scripts | `Sys_Id int identity` PK · `Run_Id int NOT NULL` · `Run_Started datetime NOT NULL` · `Run_Mode varchar(20)` · `Pack varchar(60) NOT NULL` · `Test_Name varchar(120) NOT NULL` · `Ok int` · `Detail varchar(2000)` · `Duration_ms int NOT NULL DEFAULT 0` · `Cleanup_Ok int` · `Lib_Version varchar(20)` · IX `(Run_Id, Pack)` | **S5 / S6** — the Night Shift record |
| `dbo.Diag_PM_Engine_Run` | 219 | 2 scripts | `Run_Id int identity` PK · `Run_Started NOT NULL` · `Run_Ended` · `Actor varchar(60)` · `Host varchar(80)` · `Masters`/`Released`/`Updated`/`Failed int` · `Verdict varchar(24)` · `Detail varchar(500)` · `Lib_Version varchar(20)` · IX `Run_Started` | with the **PM engine** port |

### 4.2 Bucket 2 — identity and tips: the concept ports, the table may not

| Table | Rows | Used by | Shape as read | Note |
|---|---|---|---|---|
| `dbo.Ignition_User_Map` | 11 | `identity` module (`resolve`, `Active='Y'`, self-healing auto-insert), 10 views | `Sys_User_Map_Id int identity` PK · `Ignition_Username nvarchar(100) NOT NULL` UQ · `Workmate_User_ID numeric(18,0) NOT NULL` **FK → `Users.User_Id`** · `Active char(1) NOT NULL DEFAULT 'Y'` · `Notes nvarchar(255)` · `Created_Date DEFAULT getdate()` · `Modified_Date` | **OD-2 / D-5.** This is the login → `Users.User_Id` bridge `App_User` was going to invent. The SaaS keys on its own logins, not Ignition usernames, so `App_User` should *inherit the shape* (name, FK to `Users`, `Active`, stamps) rather than carry this table. `workmate_identity_code_v1_1_1.py` is in PK for the audit |
| `dbo.Ignition_Onboarding_Prefs` | 4 | 4 NQ (`Workmate/Tips/*`) | `Ignition_Username varchar(100)` PK · `ShowTips bit NOT NULL DEFAULT 1` · `DismissedTips varchar(max)` · `LastUpdated datetime NOT NULL DEFAULT getdate()` | tips **state**. `DismissedTips` is a comma-joined list guarded by `',' + x + ','` `LIKE` — fine at KT scale; a port wants a row per dismissal (§7) |

### 4.3 Bucket 3 — other Ignition modules, product-grade, cross with their module's port

| Table | Rows | Used by | Shape highlights |
|---|---|---|---|
| `dbo.Action_Header` | 98 | 13 NQ, 2 scripts, 1 view | `Action_ID bigint identity` PK · `Short_Action_Id varchar(20)` UQ · title/description · `Asset_ID`/`Location_ID`/`Priority_ID bigint` (no FKs) · `Status char(1) DEFAULT 'R'` with **`CHECK IN ('R','H','P','K','A','V','C','D','G')`** — the WO status domain plus a `G` · `Progress_ID int DEFAULT 1 CHECK 1..6` · raised/owner/ack/approved/closed/cancelled actor+date pairs · **`Promoted_WO_ID bigint`** + `Promoted_Date` + `User_Id_Promoted_By` · five indexes |
| `dbo.Action_Event` | 597 | 3 NQ, 1 script, 1 view | `Event_ID bigint identity` PK · `Action_ID` **FK → `Action_Header`** · `Event_Date DEFAULT getdate()` · `Event_Type varchar(30)` · `Field_Name`/`Old_Value`/`New_Value` · `User_Id`, `User_Id_Acting_For bigint` · `Comment nvarchar(max)` · IX `(Action_ID, Event_Date)` |
| `dbo.Home_View` | 21 | `homeview` module | `Home_View_Id int identity` PK · `User_ID numeric(18,0)` · `View_Title nvarchar(60)` · `Domain_Code char(1) DEFAULT 'W' CHECK IN ('P','W')` · `Criteria_Json nvarchar(max)` · `Sort_Order`, `Active 'Y'`, `Crt_Date`, `Upd_Date` · IX `(User_ID, Active, Sort_Order)` — the Home page's per-user "My Views" |
| `dbo.Account_WorkCode` | 120 | 2 views (PurchaseOrder, ReferenceCodeSetup) | `Sys_Account_WorkCode_Id numeric identity` PK · `Account_ID` **FK → `Account`** · `WorkCode_ID` **FK → `Work_Code`** · `Default_WorkCode_ID char(1) DEFAULT 'F'` (a flag named like an id — parity keep) · UX `(Account_ID, WorkCode_ID)` |
| `dbo.Email_Automation` | 4 | 1 script, 1 view | `Email_Key varchar(50)` UQ · title · `Schedule_Text` · `Is_Enabled 'Y'` · `Last_Sent` · `Last_Recipient_Count` · `Sort_Order` — the scheduled-email registry |
| `dbo.PO_Email_Log` | 158 | 1 script | `Log_Id numeric identity` PK · `PO_Id` · `Sent_Date` · `Sent_To_Email varchar(255)` · `Sent_To_Name` · `Source char(1)` · `Sent_By_User` · `Batch_Title` · `Is_Urgent 'N'` · **duplicate indexes** `IX_PO_Email_Log_PO_Id` and `IX_PO_Email_Log_PO`, both `(PO_Id, Sent_Date)` — carry back to KT, carry one forward |
| `dbo.External_Contractor` | 7 | 3 NQ, 1 script, 1 view, proc `wmsp_External_ContractorInsertUpdate` | legacy-style `char` columns; PK on `External_Contractor_ID` (not the identity `Sys_…`); `Linked_Supplier_ID` **FK → `Supplier`**; `Server_Name`, `User_id_Created_By`, `Entry_Date` |

### 4.4 Bucket 4 — KT-specific by construction; do not cross as-is

| Table | Why |
|---|---|
| `forecast.shift_matrix` (1022), `forecast.month_parameters` (36), `forecast.site_parameters` (4), `forecast.audit_log` (186), `usp_upsert_shift`, `v_shift_grid`, `v_monthly_summary` | the VolumeMatrix module; **`CHECK (site IN ('KPP','MLD'))`** on three tables; a second schema (D-12 says `dbo` only on PG). Product only if the SaaS ships a forecast module, and then with the site domain lifted out of the DDL |
| `dbo.MP_Downtime_Area_Map` (10), `dbo.MP_Downtime_WO_Link` (27) | links WOs to **MainSCADA's** downtime table (`Downtime_Id bigint`); `Created_By int`. RST has no Ignition SCADA to link to |

### 4.5 Orphans — exist, referenced by nothing (gateway 0, DB dependencies 0)

`dbo.Ignition_Tip_Definitions` (19 rows — the tip text lives in view JSON, §7) · column `PO_Header.Status_Pre_Archive` · function `GetWeekNoAndYear` (**keep as a reference for S2, not as a DB object** — read its body via `sys.sql_modules`, pin it in `test_weekno.py` against `pm_engine`'s verbatim port and KT's `Week_No` data) · procs `wmsp_GetNextWOId`, `wmsp_GenerateShortWOId` · view `vw_SchedulexCount`. Possibly called by something outside the export (the .NET client at KT?) — unknowable from here; not the SaaS's.

### 4.6 Junk — 25 tables that never cross

| Set | Count | What |
|---|---|---|
| `sqlth_annotations`, `sqlth_drv`, `sqlth_partitions`, `sqlth_sce`, `sqlth_scinfo`, `sqlth_te` | 6 | Ignition tag-historian plumbing, 0–1 rows |
| `TMCLIMITED\PrinslooA.Trace_*` | 14 | a `SELECT INTO` trace session that landed in a personal schema |
| `TMCLIMITED\PrinslooA.PO_Details_Backup_20260410`, `…PO_Header_Backup_20260410` | 2 | ad-hoc backups, same schema |
| `Action_Event_AuditRepair_Backup_20260525_213712`, `Action_Header_LocBackfill_Backup_20260525_215812`, `Action_Header_TitleMig_Backup_20260525_210917` | 3 | May data-repair backups |
| `sysdiagrams` | — | SSMS artefact |

Cleanup candidates at KT, all of them.

## 5. Columns added at KT on shared tables

Real (all nullable, **no defaults** — T5 empty), used per the export:

| Table | Column | Type | Used by |
|---|---|---|---|
| `WO_N_Header`, `WO_C_header` | `Source_Action_ID` | `bigint` | 2 NQ, 2 scripts — the Action → WO promotion link |
| `Supplier` | `Email_2`, `Email_3` | `varchar(255)` | 2 NQ, 1 script, 2 views |
| `PO_Details` | `Invoice_Ref` | `varchar(30)` | 1 NQ, 1 script, 2 views |
| `WO_Attachment`, `WO_M_Attachment`, `PO_Attachment`, `Part_Attachment`, `Location_Attachment` | `Creation_Date`, `User_id_Created_By` | `datetime`, `numeric(18,0)` | 2 NQ, 2 scripts — one audit-stamp pattern across all five |

Not real: **47 columns on `TEMP_*` staging tables** (`TEMP_WO_N_Details`, `TEMP_WO_N_Header`, `TEMP_WO_M_details`, `TEMP_WO_T_details`, `TEMP_WO_N_Activity*`, `TEMP_Invoice_Details`, `TEMP_WO_M_header`) — .NET import mirrors that KT's newer .NET build extended; not the SaaS's. Orphan: `PO_Header.Status_Pre_Archive`.

**Type note, so nobody "fixes" it in flight:** the Ignition-era tables use `bigint`/`int` for ids that point at legacy `numeric(18,0)` keys, without FKs across that boundary (`Action_Header.Asset_ID`, `Diag_Log.Wm_User_Id`, `MP_Downtime_WO_Link.Created_By` …). Parity keeps the types; the SaaS mapper's `_i()`/`_f()` coercion already absorbs them (Landmines §A).

## 6. What this changes on the existing queue

| Item | Change |
|---|---|
| **26** — Ignition parity blocked on a KT dev copy | **unblocked.** `dbWorkmate_KT` is on the box, read-only. KT's own `Diag_Log` holds the Ignition planner's `[F] range … rows=… labour=… workers=36 pinTable=True in 147 ms` lines — the oracle's actual counts and timings for `parity_range.py`. Needs a `svc_workmate` user in the copy first (read-write flip, create, flip back) |
| **29** — `Priority.Colour` to the badge | **both halves verified against tables.** KT: A/B/C/D at `Sort_Sequence` 1–4, no ties, `#FF8000` ×4 — so the oracle colours by the **letter class in CSS** and `Colour` carries nothing usable there. RST: fourteen rows, ties, `Colour` populated and varied. Design implied: paint from the payload when the colours are varied; when every row matches, leave the existing `.pri.A–D` classes to carry the oracle's colouring. The audit signs it |
| **OD-1 / S3** | `WO_N_Plan` DDL and lifecycle read (§4.1). Pinning is barely used at KT (4 rows) |
| **OD-2 / D-5** | `Ignition_User_Map` + `identity` 1.1.1 are the precedent (§4.2) |
| **OD-3** | `Server_Name = 'Perspective'` confirmed on the pin rows; `'SaaS'` is the swap |
| **S2 `test_weekno.py`** | three references now: `pm_engine` 2.5.0's verbatim `GetWeekNoANDYear` port (in PK), the SQL function body (T8, pending paste), KT's `Week_No` data |
| **D-8 diag persist** | `Diag_Log` DDL is the contract (§4.1); `Session_Id`/`Source`/`Tier`/`Msg_Level` are NOT NULL — the SaaS must decide what fills them |
| **D-12** | a second schema (`forecast`) exists at KT; stays KT-specific unless a forecast module ships |
| **The ⓘ idea** | see §7 |

## 7. The ⓘ tips idea — evidence for its audit

KT built it; the Planner never got one. Design as found in the export: **content in code, state in the DB.** Tip text lives in each view's JSON (`tipTitle`/`tipText` props on Home, Schedulex, Procurex, PMx, Supplier, User Mapping), rendered by two components — `TipBadge` and `TipPopup` (both in PK, dated 2026-09-10). State is `Ignition_Onboarding_Prefs` via four one-line named queries:

- `GetUserPrefs`: `SELECT ISNULL(ShowTips,1), ISNULL(DismissedTips,'') FROM dbo.Ignition_Onboarding_Prefs WHERE Ignition_Username = :username`
- `DismissTip`: a `MERGE` that appends `:tipId` to the comma list unless `',' + DismissedTips + ','` already contains it; inserts the row with `ShowTips = 1` if absent
- `SetShowTips`: `MERGE` setting `ShowTips = :showTips`
- `ResetAllTips`: `UPDATE … SET DismissedTips = '', ShowTips = 1`

The 19-row `Ignition_Tip_Definitions` table is a seed nobody reads. Its rows are still worth a look for **voice**: short imperative titles, one-to-two-sentence text, `SortOrder` mostly 0 with a few 5/10/20/99 — the same tie problem as `Priority`, so ordering is a decision, not a default.

Two things the audit owns: (1) a tips ⓘ is not in the Planner oracle, so it is the **first non-port component** — OD-27/OD-31 put the Tailwind/shadcn decision exactly there; (2) per-view content as a TS registry vs a table, and a row-per-dismissal prefs table keyed on the SaaS user, not an Ignition username.

## 8. The uplift — proposal and the questions the audit signs

**Proposal.** One hand-written, additive migration — call it *KT parity, additive* — scripted **from `dbWorkmate_KT`'s catalog at build time, never typed** (Ways of Working §5): Bucket 1 tables, Bucket 3 tables, the §5 columns, the Diag and External_Contractor companions. Bucket 2 informs `App_User` and the tips prefs rather than crossing verbatim. Bucket 4, the orphans and the junk never cross. `DRY_RUN` first; every statement `IF NOT EXISTS`-guarded; nothing touches an RST view; nothing writes data — RST's copies start empty. Portable DDL per D-3 (`getdate()` → `CURRENT_TIMESTAMP`, `bit` → boolean on PG, lowercase names on PG, `-- PG-CONVERT:` tags). One index for `PO_Email_Log`, not two.

**Why additive-all-at-once rather than just-in-time:** the tables are empty and nullable, the risk is near zero, and it closes the gap Adriaan named — the SaaS dev DB stops surprising the port with "does not exist on RST". The one visible behaviour change is the point: `pinTable` flips `True` on RST, which is OD-1's intended end state and makes S2/S3 testable on real data.

**Questions for the audit (not numbered as ODs until signed):**

1. Scope: Buckets 1 + 3 + §5 columns in one migration, or Bucket 1 now and Bucket 3 per module? (Proposal: all additive now.)
2. Migration numbering: this becomes `0001` and S3's `0002_wo_n_plan` collapses into it, or S3 keeps `0002` and the uplift is `0001` without `WO_N_Plan`. (Proposal: one migration, S3 inherits an existing table.)
3. `WO_N_Plan` on RST before S3: accept `pinTable=True` changing the S1 screenshots' `locked`/`movable` state on 2,364 engine-owned PMs? (Proposal: yes — that is OD-1 working.)
4. `Diag_Log` NOT NULL columns: what fills `Session_Id` (request id? JWT `sub`?), `Source`, `Tier`, `Msg_Level` from `diag.py`'s `[F]/[G]/[E]` seam?
5. `App_User` (D-5) inherits `Ignition_User_Map`'s shape — `login → Users.User_Id` FK, `Active`, stamps — yes/no?
6. The `forecast` schema: never, or "when a forecast module ships, with the site domain lifted"?
7. `Action_Header` status `'G'`: what is it, and does the WO status domain (Landmines §E) need it?
8. Type parity: carry `bigint`/`int` ids as-is (proposal) or align to `numeric(18,0)` on the way over?
9. Carry-backs to KT: the duplicate index, the 25 junk tables, the two orphan objects, `Status_Pre_Archive` — a note to KT, not the SaaS's work.

## 9. Landmines harvested on the way (for Landmines 1.5.0)

- `sqlcmd -E` authenticates *you*; the **engine opens the file as `NT Service\MSSQLSERVER`** — a `.bak` under `C:\Users\<you>\Downloads` is unreadable. OS error **2** = path, **5** = ACL. [2026-09-13]
- A **move within a volume keeps the file's old ACL**; a copy inherits the destination's. Granting on the folder after a move does nothing for the file — grant on the file, or `icacls /reset` it. [2026-09-13]
- `OBJECT_DEFINITION()`, `SCHEMA_NAME()`, `OBJECT_NAME()` resolve in the **current database** even when fed an id from a three-part name — `master` here, so `NULL`. Join the remote `sys.*` views instead. [2026-09-13]
- `sqlcmd -W` and `-y 0` are **mutually exclusive**; a long `definition` needs its own call with `-y 0 -h -1`. [2026-09-13]
- PowerShell **formats the second object type with the first one's table** when both go to one output stream — `Select-Object Name, Length` printed only `Name` under a `Name / StartName` header and the verification silently lost its `Length`. `Format-List` the verification line. [2026-09-13]
- Pasting a block **while the previous output is still scrolling** overprints the echo; the file on disk is fine, the paste record is not. Wait for the prompt. [2026-09-13]
- A restore across engine majors upgrades the physical version on the way in (957 → 998 here) — **AzztecDev → KTSQL02 is never possible**. [2026-09-13]

## 10. Changelog

- 1.0.0 (2026-09-13) Initial. Built from the `dbWorkmate_KT` restore, six catalog blocks (counts, table/column/routine deltas both directions, DDL shape, keys/FKs/checks, dependencies) and a reference grep of the 2026-09-10 project export. 46 KT-only tables triaged to 21 real (5 core, 2 identity/tips, 7 module, 6 KT-specific, 1 orphan) and 25 junk; 10 real column additions; 12 routines classified; item 26 unblocked, item 29 evidenced both sides, OD-1/OD-2/OD-3/S2/S3/D-8/D-12 fed; the tips idea documented as found; the uplift proposed with nine audit questions; seven landmines.
