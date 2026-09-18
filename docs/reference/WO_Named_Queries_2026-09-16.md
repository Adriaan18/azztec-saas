# Workmate WO named queries - reference bundle (2026-09-16 export)

**File:** WO_Named_Queries_2026-09-16.md · **Author:** Adriaan (the queries) · assembled by script from `MainSCADA_Timberlands_2026-09-16_1307.zip` · `ignition/named-query/Workmate/{Workorder, Workorder Detail, Workorder Activity, Workorder Resource, WO Query, WO Responsible User}`

Each block is the `query.sql` byte-for-byte; the `resource.json` line gives the last modification. Reference input for the WOMaint audit — never a build source (the SaaS port writes its own `sql.py`, dialect-portable, D-3).

## `Workmate/Workorder/Create from Template` — 723 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- Work Order → work order GROUP management

-- Workmate/Workorder/Create from Template
-- Parameters: Template_WO_ID (Int8)
--             Request_Start_Date (DateTime), Request_End_Date (DateTime), Entry_Date (DateTime),
--             User_Id_Created_By (Int8), Company_ID (Int8), Asset_ID (Int8), Location_ID (Int8)
EXEC [dbo].[wmsp_CreateWorkOrderFromTemplate]
    @Template_WO_ID = :Template_WO_ID,
    @Short_WO_Id = :Short_WO_Id,
    @WO_Title = :WO_Title,
    @Request_Start_Date = :Request_Start_Date,
    @Request_End_Date = :Request_End_Date,
    @Entry_Date = :Entry_Date,
    @User_Id_Created_By = :User_Id_Created_By,
    @Company_ID = :Company_ID,
    @Asset_ID = :Asset_ID,
    @Location_ID = :Location_ID;
```

## `Workmate/Workorder/Delete` — 153 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- Work Order → work order GROUP management

-- Workmate/Workorder/Delete
-- Parameters: id (Int8)
UPDATE WO_N_Header SET Status = 'X' WHERE WO_ID = :id;
```

## `Workmate/Workorder/Get Comments` — 408 B — modified 2026-08-29T20:21:50Z by Adriaan

```sql
-- Work Order → work order GROUP management

-- Workmate/Workorder/Get Comments
-- Parameters: Workorder_ID (Int8)
SELECT Comments
FROM WO_N_Activity
INNER JOIN WO_N_Activity_Comments ON 
    WO_N_Activity.WO_ID = WO_N_Activity_Comments.WO_Id
    AND WO_N_Activity.WO_Activity_ID = WO_N_Activity_Comments.WO_Activity_ID
WHERE Trx_Type = 'L'
  AND LEN(Comments) > 0
  AND WO_N_Activity.WO_ID = :Workorder_ID;
```

## `Workmate/Workorder/GetByAsset` — 1690 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder/GetByAsset
-- Type:       Select Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Dialect:    portable
-- Version:    1.1
-- ==============================================================================
-- Changelog (newest first):
--   1.1  Stripped leading ':' from parameter names in the doc-header comment
--        (Ignition NQ parser counts colon-prefixed names in comments as positional
--        binds -> JDBC "index N out of range"). No SQL body change.
--   1.0  Rewrite of legacy 'Work Order/GetByAsset' (broken: referenced
--        Actual_End_Date which exists on neither WO_N_Header nor WO_N_Details).
--        Now sources close-date from WO_N_Details.Closed_Date. Header LEFT
--        JOIN Details. OFFSET/FETCH limit 100. Renamed Work Order/ -> Workorder/
--        for naming consolidation (WO-2). Per WO-1 spec v2.0.
-- ==============================================================================
-- Parameters:
--   assetId  Int8  required  -- the WO_N_Header.Asset_ID to filter on
-- Returns:
--   Up to 100 work orders for the asset, most recent first.
--   Columns: WO_ID, Short_WO_Id, WO_Title, Status, Request_Start_Date,
--            Closed_Date, Entry_date
-- ==============================================================================

SELECT
    h.WO_ID,
    h.Short_WO_Id,
    h.WO_Title,
    h.Status,
    h.Request_Start_Date,
    d.Closed_Date,
    h.Entry_date
FROM dbo.WO_N_Header h
LEFT JOIN dbo.WO_N_Details d ON h.WO_ID = d.WO_ID
WHERE h.Asset_ID = :assetId
ORDER BY h.Entry_date DESC
OFFSET 0 ROWS FETCH FIRST 100 ROWS ONLY;
```

## `Workmate/Workorder/GetByLocation` — 1504 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
-- ==============================================================================
-- Version: 1.1
-- Changelog (newest first):
--   1.1  PM SEPARATION: added WO_Type_Flag='N' so PMs no longer appear in this
--        WO list/metric (PM Audit v1.0.0). Prior history untracked (no header).
-- ==============================================================================
-- Work Order -> work order GROUP management

-- Query Path: Workmate/Workorder/GetByLocation
-- Type: Query
-- Parameters: locationId (Int8)
-- ==============================================================================
-- Get work order history for a location with Supplier and Activity Person

SELECT
    h.WO_ID,
    h.Short_WO_Id,
    h.WO_Title,
    h.Asset_ID,
    a.Asset_Title,
    h.Status,
    h.Request_Start_Date,
    h.Entry_Date,
    sup.Company_Name AS Supplier_Name,
    usr.User_Name AS Activity_Person
FROM WO_N_Header h
LEFT JOIN Asset a ON h.Asset_ID = a.Asset_ID
OUTER APPLY (
    SELECT TOP 1 s.Company_Name
    FROM WO_N_Activity act
    INNER JOIN Supplier s ON act.Supplier_ID = s.Supplier_ID
    WHERE act.WO_ID = h.WO_ID AND act.Supplier_ID IS NOT NULL
    ORDER BY act.Activity_Date DESC
) sup
OUTER APPLY (
    SELECT TOP 1 u.User_Name
    FROM WO_N_Activity act
    INNER JOIN Users u ON act.User_ID = u.User_Id
    WHERE act.WO_ID = h.WO_ID AND act.User_ID IS NOT NULL
    ORDER BY act.Activity_Date DESC
) usr
WHERE h.Location_ID = :locationId
  AND h.WO_Type_Flag = 'N'
ORDER BY h.Entry_Date DESC;
```

## `Workmate/Workorder/GetByStatus` — 2042 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder/GetByStatus
-- Type:       Select Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Dialect:    portable
-- Version:    1.2
-- ==============================================================================
-- Changelog (newest first):
-- v1.2  PM SEPARATION: added WO_Type_Flag='N' so PM masters/instances no longer appear in this WO list/metric (see PM Audit v1.0.0). No other change.
--   1.1  Stripped leading ':' from parameter names in the doc-header comment
--        (Ignition NQ parser counts colon-prefixed names in comments as positional
--        binds -> JDBC "index N out of range"). No SQL body change.
--   1.0  Rewrite of legacy 'Work Order/GetByStatus' (broken: Priority_ID and
--        Progress_ID referenced on Header; both live on Details). Now LEFT
--        JOIN Details and source from there. Renamed for consolidation.
--        Per WO-1 spec v2.0.
-- ==============================================================================
-- Parameters:
--   status  String  required  -- WO status code (R/H/P/K/A/V/C/D/F)
-- Returns:
--   Up to 200 work orders at the given status, most recent first.
--   Columns: WO_ID, Short_WO_Id, WO_Title, Location_Id, Location_Title,
--            Asset_ID, Asset_Title, Priority_Id, Progress_Id, Status,
--            Request_Start_Date, Entry_date
-- ==============================================================================

SELECT
    h.WO_ID,
    h.Short_WO_Id,
    h.WO_Title,
    h.Location_Id,
    l.Location_Title,
    h.Asset_ID,
    a.Asset_Title,
    d.Priority_Id,
    d.Progress_Id,
    h.Status,
    h.Request_Start_Date,
    h.Entry_date
FROM dbo.WO_N_Header h
LEFT JOIN dbo.WO_N_Details d ON h.WO_ID = d.WO_ID
LEFT JOIN dbo.Location  l ON h.Location_Id = l.Location_Id
LEFT JOIN dbo.Asset     a ON h.Asset_ID    = a.Asset_ID
WHERE h.Status = :status
  AND h.WO_Type_Flag = 'N'
ORDER BY h.Entry_date DESC
OFFSET 0 ROWS FETCH FIRST 200 ROWS ONLY;
```

## `Workmate/Workorder/GetOpen` — 2314 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder/GetOpen
-- Type:       Select Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Dialect:    portable
-- Version:    1.2
-- ==============================================================================
-- Changelog (newest first):
-- v1.2  PM SEPARATION: added WO_Type_Flag='N' so PM masters/instances no longer appear in this WO list/metric (see PM Audit v1.0.0). No other change.
--   1.1  No functional change (this NQ has no parameters, so the colon-in-
--        comment landmine never applied). Version bumped to keep the Stage C
--        set aligned at v1.1.
--   1.0  Rewrite of legacy 'Work Order/GetOpen' (broken: Priority_ID and
--        Progress_ID on Header; User_Id_Assigned_To doesn't exist at all).
--        Now LEFT JOIN Details for the priority/progress fields and
--        substitute User_ID_Responsibility (Details) for "assigned to".
--        Widened "open" from ('R','A','P','H') to NOT IN ('C','D') so the
--        full documented status flow surfaces (R/H/P/K/A/V/F all open).
--        Renamed for consolidation. Per WO-1 spec v2.0.
-- ==============================================================================
-- Parameters:
--   (none)
-- Returns:
--   Up to 200 open work orders sorted by Priority then most-recent.
--   Columns: WO_ID, Short_WO_Id, WO_Title, Location_Id, Location_Title,
--            Asset_ID, Asset_Title, Priority_Id, Progress_Id, Status,
--            Request_Start_Date, Entry_date, User_Id_Created_By,
--            User_ID_Responsibility
-- ==============================================================================

SELECT
    h.WO_ID,
    h.Short_WO_Id,
    h.WO_Title,
    h.Location_Id,
    l.Location_Title,
    h.Asset_ID,
    a.Asset_Title,
    d.Priority_Id,
    d.Progress_Id,
    h.Status,
    h.Request_Start_Date,
    h.Entry_date,
    h.User_Id_Created_By,
    d.User_ID_Responsibility
FROM dbo.WO_N_Header h
LEFT JOIN dbo.WO_N_Details d ON h.WO_ID = d.WO_ID
LEFT JOIN dbo.Location  l ON h.Location_Id = l.Location_Id
LEFT JOIN dbo.Asset     a ON h.Asset_ID    = a.Asset_ID
WHERE h.Status NOT IN ('C', 'D')
  AND h.WO_Type_Flag = 'N'
ORDER BY d.Priority_Id, h.Entry_date DESC
OFFSET 0 ROWS FETCH FIRST 200 ROWS ONLY;
```

## `Workmate/Workorder/GetOpenForWeek` — 2343 B — modified 2026-08-29T20:21:50Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder/GetOpenForWeek
-- File:       Workmate_Workorder_GetOpenForWeek_v1_1_0.sql
-- Version:    1.1.0
-- Type:       Query
-- Database:   TLSQL01_Workmate
-- Author:     Claude (for Adriaan)
--
-- Changelog (newest first):
--   1.1.0  PM SEPARATION: added WO_Type_Flag='N' so released PMs no longer
--          appear in the weekly open-WO list (PM Audit v1.0.0). Live v1.0.0
--          SQL was never exported, so this cut is authored from the caller
--          contract (workmate.workorder.formatOpenForWeekReply reads
--          Priority_Id, Status, Request_Start_Date, Short_WO_Id, WO_Title,
--          Asset_Title). Diff against the live NQ before pasting - if the
--          live SELECT carries extra columns, keep them and add only the
--          type predicate.
--   1.0.0  Initial (live, unexported). Created alongside workmate.workorder
--          v1.3.0 for the WM_AI weekly-outstanding overlay.
--
-- Parameters:
--   weekStart (DateTime, required)  -- window start, inclusive (Monday 00:00)
--   weekEnd   (DateTime, required)  -- window end, EXCLUSIVE (next Monday 00:00;
--                                      exclusive end avoids the datetime
--                                      full-day-span trap on Request_Start_Date)
--
-- Returns: open work orders (Status NOT IN C,D; WOs only, no PMs) whose
--          Request_Start_Date falls in the window. Priority first, then due
--          date, so the AI card renders Critical work at the top.
-- ==============================================================================

SELECT
    h.WO_ID,
    RTRIM(ISNULL(h.Short_WO_Id, ''))   AS Short_WO_Id,
    RTRIM(ISNULL(h.WO_Title, ''))      AS WO_Title,
    RTRIM(ISNULL(h.Status, ''))        AS Status,
    h.Request_Start_Date,
    ISNULL(d.Priority_Id, 3)           AS Priority_Id,
    h.Asset_ID,
    RTRIM(ISNULL(a.Asset_Title, ''))   AS Asset_Title
FROM dbo.WO_N_Header h
INNER JOIN dbo.WO_N_Details d ON h.WO_ID = d.WO_ID
LEFT  JOIN dbo.Asset a        ON h.Asset_ID = a.Asset_ID
WHERE h.Status NOT IN ('C', 'D')
  AND h.WO_Type_Flag = 'N'
  AND h.Request_Start_Date >= :weekStart
  AND h.Request_Start_Date <  :weekEnd
ORDER BY ISNULL(d.Priority_Id, 3) ASC,
         h.Request_Start_Date ASC,
         h.WO_ID ASC;
```

## `Workmate/Workorder/GetPODetails` — 721 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- Query Path: Workmate/Work Order/GetPODetails
-- Type: Query (FIXED)
-- Database: KTSQLWM_Workmate
-- Parameters: woId (Int8)
-- Purpose: Get all PO detail lines for a given Work Order ID.
--          Used by the Purchase Orders sub-tab table in WOMaint.
--          NOTE: The WO link is on PO_Details.WO_Id (not PO_Header.WO_Id)
-- ==============================================================================
SELECT 
    h.Status,
    h.Short_PO_Id,
    d.Due_Date,
    s.Company_Name,
    d.PO_Description,
    d.Quantity,
    d.Unit_Cost
FROM PO_Details d
INNER JOIN PO_Header h ON d.PO_ID = h.PO_Id
LEFT JOIN Supplier s ON h.Supplier_Id = s.Supplier_ID
WHERE d.WO_Id = :woId
ORDER BY h.Short_PO_Id, d.PO_Detail_ID
```

## `Workmate/Workorder/GetPOs` — 424 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql

--Parameter:** `woId` (Int8)

--This will show the PO lines below Notes in the format:

--PO(1) - K-1677413 - DATACOM - INV1677413
--PO(2) - K-20014949 - WFIVE - INV - 20014949

SELECT 
    h.Short_PO_Id,
    s.Company_Name,
    d.PO_Description
FROM PO_Header h
LEFT JOIN Supplier s ON h.Supplier_Id = s.Supplier_ID
LEFT JOIN PO_Details d ON h.PO_Id = d.PO_ID
WHERE h.WO_Id = :woId
ORDER BY h.Short_PO_Id, d.PO_Detail_ID;
```

## `Workmate/Workorder/Item` — 1867 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
-- Work Order → work order GROUP management

-- Workmate/Workorder/Item
-- Parameters: woId (Int8)
SELECT 
    h.WO_ID,
    h.Short_WO_Id,
    h.WO_Title,
    h.Asset_ID,
    a.Short_asset_Id,
    a.Asset_Title,
    h.Location_Id,
    l.Short_Location_ID,
    l.Location_Title,
    h.Request_Start_Date,
    h.Request_End_Date,
    h.Entry_date AS Logged_Date,
    h.Status,
    h.OverDue,
    h.Week_No,
    h.Company_ID,
    h.Parent_Location_Hierarchy,
    d.Duration_In_Hours,
    d.Est_Cost,
    d.Down_Time,
    d.Priority_Id,
    d.WO_Group_Id,
    d.Reason_Id,
    d.Fault_Id,
    d.Cost_Center_Id,
    d.Account_Id,
    d.Supplier_ID_charge_To,
    d.Supplier_ID_Responsibility,
    d.WOC1_ID,
    d.WOC2_ID,
    d.WOC3_ID,
    d.Reference,
    d.Progress_Id,
    d.Notes,
    d.User_ID_Requested_By,
    d.User_ID_Responsibility,
    d.Entered_By,
    d.User_Id_Ack_by,
    d.Acknowledgement_date,
    d.User_Id_Approved_By,
    d.Approved_Date,
    d.User_ID_ClosedBy,
    d.Closed_Date,
    d.User_ID_CancelledBy,
    d.Cancelled_Date,
    d.User_id_Last_Save,
    d.Last_Save_Date,
    uc.Short_User_Id AS Created_By_Name,
    ua.Short_User_Id AS Ack_By_Name,
    uap.Short_User_Id AS Approved_By_Name,
    ucl.Short_User_Id AS Closed_By_Name,
    uca.Short_User_Id AS Cancelled_By_Name,
    uls.Short_User_Id AS Last_Save_Name
FROM WO_N_Header h
INNER JOIN WO_N_Details d ON h.WO_ID = d.WO_ID
LEFT JOIN Asset a ON h.Asset_ID = a.Asset_ID
LEFT JOIN Location l ON h.Location_Id = l.Location_Id
LEFT JOIN Users uc ON h.User_Id_Created_By = uc.User_Id
LEFT JOIN Users ua ON d.User_Id_Ack_by = ua.User_Id
LEFT JOIN Users uap ON d.User_Id_Approved_By = uap.User_Id
LEFT JOIN Users ucl ON d.User_ID_ClosedBy = ucl.User_Id
LEFT JOIN Users uca ON d.User_ID_CancelledBy = uca.User_Id
LEFT JOIN Users uls ON d.User_id_Last_Save = uls.User_Id
WHERE h.WO_ID = :woId;
```

## `Workmate/Workorder/ItemHeader` — 1901 B — modified 2026-08-29T20:21:49Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder/ItemHeader
-- Type:       Select Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Dialect:    portable
-- Version:    1.1
-- ==============================================================================
-- Changelog (newest first):
--   1.1  Stripped leading ':' from parameter names in the doc-header comment.
--        Ignition's NQ parameter parser scans the full source for ':identifier'
--        patterns including inside SQL comments, then tries to bind them
--        positionally against the prepared SQL (which has comments stripped).
--        Result: phantom extra positions, JDBC "index N out of range".
--        Rule: doc-header parameter refs use plain name, no colon prefix.
--   1.0  Rename of legacy 'Workmate/Workorder/Item' (the header-only variant)
--        to 'Workmate/Workorder/ItemHeader' as part of WO-1 v2.0 collision
--        resolution. Added 'dbo.' prefix and 'Dialect: portable' header
--        per Workmate_PG_Forward_Compat v1.0. SQL body otherwise unchanged.
-- ==============================================================================
-- Parameters:
--   woId  Int8  required  -- WO_N_Header.WO_ID
-- Returns:
--   At most one row with the 25 header-only columns of WO_N_Header.
-- ==============================================================================

SELECT
    Allow_child,
    Asset_ID,
    Company_ID,
    Compliance,
    Entry_date,
    General_Permit_Form,
    JSA_Form,
    Linked_to_WO,
    Location_Id,
    OverDue,
    Purchase_Order_Flag,
    Request_End_Date,
    Request_Start_Date,
    Safety,
    Server_Name,
    Short_WO_Id,
    Status,
    Sys_WO_ID,
    User_Id_Created_By,
    Week_No,
    WO_ID,
    WO_Query_Status,
    WO_Title,
    WO_Type_Flag,
    Work_Permit
FROM dbo.WO_N_Header
WHERE WO_ID = :woId;
```

## `Workmate/Workorder/LinkedFamily` — 3807 B — modified 2026-09-03T04:55:25Z by Adriaan

```sql
-- =============================================================================
-- Workmate_Workorder_LinkedFamily_v1_0_0.sql
-- NQ Designer path:  Workmate/Workorder/LinkedFamily
-- NQ TYPE: Select Query
-- Database: TLSQL01_Workmate   (set after creating; register param woId!)
-- Author: Adriaan
-- -----------------------------------------------------------------------------
-- Changelog (newest first)
--   v1.0.0  Initial. The .NET Linked WO tab (frmWOMaintenance ->
--           Schedulex.ShowLinkedWO) walks UP to the root parent (two hops
--           max: parent -> child 'A' -> grandchild 'A1') and then shows the
--           WHOLE family. This query does the same, keyed on Linked_to_WO
--           rather than the Short_WO_Id prefix (probe 2026-09-03: prefix
--           convention holds today, but the id is the truth). Ships the
--           WONumBadge composite ready-made (data layers assemble it, views
--           never do - Perspective Rules v3.5). Open table only - closed
--           archives (WO_C_header) are out of scope, as in the .NET tab.
--
-- Parameters:
--   woId   Integer   WO_N_Header.WO_ID of the WO on screen   << REGISTER
--
-- Returns (one row per family member, parent first by id):
--   WO_ID, Short_WO_Id, WO_Title, Status, Progress_Id, HasPO, Level (0 root /
--   1 child / 2 grandchild), ParentId, ParentShortId, Request_Start_Date,
--   Entry_date, IsSelected (1 = the woId row), Badge (status|shortId|prog|hasPO)
-- =============================================================================
WITH me AS (
    SELECT h.WO_ID, ISNULL(h.Linked_to_WO, 0) AS Up1
    FROM dbo.WO_N_Header h
    WHERE h.WO_ID = :woId
),
up1 AS (
    SELECT CASE WHEN me.Up1 > 0 THEN me.Up1 ELSE me.WO_ID END AS WO_ID
    FROM me
),
rootq AS (
    SELECT CASE WHEN ISNULL(h.Linked_to_WO, 0) > 0 THEN h.Linked_to_WO ELSE h.WO_ID END AS RootId
    FROM dbo.WO_N_Header h
    INNER JOIN up1 ON h.WO_ID = up1.WO_ID
),
fam AS (
    SELECT h.WO_ID, 0 AS Lvl
    FROM dbo.WO_N_Header h
    INNER JOIN rootq r ON h.WO_ID = r.RootId
    UNION ALL
    SELECT c.WO_ID, 1 AS Lvl
    FROM dbo.WO_N_Header c
    INNER JOIN rootq r ON c.Linked_to_WO = r.RootId
    UNION ALL
    SELECT g.WO_ID, 2 AS Lvl
    FROM dbo.WO_N_Header g
    INNER JOIN dbo.WO_N_Header c ON g.Linked_to_WO = c.WO_ID
    INNER JOIN rootq r ON c.Linked_to_WO = r.RootId
)
SELECT
    h.WO_ID,
    RTRIM(h.Short_WO_Id)                                   AS Short_WO_Id,
    RTRIM(ISNULL(h.WO_Title, ''))                          AS WO_Title,
    RTRIM(ISNULL(h.Status, ''))                            AS Status,
    ISNULL(d.Progress_Id, 0)                               AS Progress_Id,
    CASE WHEN EXISTS (SELECT 1 FROM dbo.PO_Header  ph WHERE ph.WO_Id = h.WO_ID)
           OR EXISTS (SELECT 1 FROM dbo.PO_Details pd WHERE pd.WO_Id = h.WO_ID)
         THEN 1 ELSE 0 END                                 AS HasPO,
    f.Lvl                                                  AS Level,
    ISNULL(h.Linked_to_WO, 0)                              AS ParentId,
    RTRIM(ISNULL(p.Short_WO_Id, ''))                       AS ParentShortId,
    h.Request_Start_Date,
    h.Entry_date,
    CASE WHEN h.WO_ID = :woId THEN 1 ELSE 0 END            AS IsSelected,
    RTRIM(ISNULL(h.Status, '')) + '|' + RTRIM(h.Short_WO_Id) + '|'
        + CAST(ISNULL(d.Progress_Id, 0) AS varchar(10)) + '|'
        + CASE WHEN EXISTS (SELECT 1 FROM dbo.PO_Header  ph2 WHERE ph2.WO_Id = h.WO_ID)
                 OR EXISTS (SELECT 1 FROM dbo.PO_Details pd2 WHERE pd2.WO_Id = h.WO_ID)
               THEN '1' ELSE '0' END                       AS Badge
FROM fam f
INNER JOIN dbo.WO_N_Header h ON h.WO_ID = f.WO_ID
LEFT JOIN dbo.WO_N_Details d ON d.WO_ID = h.WO_ID
LEFT JOIN dbo.WO_N_Header p ON p.WO_ID = h.Linked_to_WO
ORDER BY f.Lvl, h.Short_WO_Id
```

## `Workmate/Workorder/PrintList` — 1735 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
-- ===========================================================================
-- Workmate / Workorder / PrintList               v1.1.0   (read-only)
-- Author: Adriaan
-- ---------------------------------------------------------------------------
-- Purpose : WO list for WOPrintPopup (board #9, multi-select print).
--           Modelled on Purchase Order/PrintList: NQ carries the days
--           window only; search stays CLIENT-SIDE in the popup.
--           No status exclusion in v1.0.0 - the WO status vocabulary is
--           not yet confirmed, so nothing is silently hidden.
--   v1.1.0 - CreatedBy fixed: d.Entered_By is empty on Live; the real
--            source is h.User_Id_Created_By -> Users (per Item NQ).
-- Designer path : Workmate/Workorder/PrintList
-- Query Type    : Select Query
-- Database      : TLSQL01_Workmate
-- Parameters    : daysWindow  (Int4)
-- Cache Time    : 0
-- ===========================================================================

SELECT
    h.WO_ID,
    RTRIM(ISNULL(h.Short_WO_Id, ''))                 AS Short_WO_Id,
    h.Entry_date,
    RTRIM(ISNULL(h.Status, ''))                      AS Status,
    RTRIM(ISNULL(h.WO_Title, ''))                    AS WO_Title,
    RTRIM(ISNULL(a.Short_asset_Id, ''))              AS Short_asset_Id,
    RTRIM(ISNULL(uc.User_Name, ''))                  AS CreatedBy,
    DATEDIFF(day, h.Entry_date, GETDATE())           AS DaysOpen
FROM WO_N_Header h
LEFT JOIN WO_N_Details d ON d.WO_ID    = h.WO_ID
LEFT JOIN Asset        a ON h.Asset_ID           = a.Asset_ID
LEFT JOIN Users        uc ON h.User_Id_Created_By = uc.User_Id
WHERE
    h.Entry_date >= DATEADD(day, -ISNULL(:daysWindow, 90), GETDATE())
ORDER BY h.Entry_date DESC, h.WO_ID DESC
```

## `Workmate/Workorder/PrintWOHeaders` — 3870 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
-- ===========================================================================
-- Workmate / Workorder / PrintWOHeaders          v1.1.1   (read-only)
-- Author: Adriaan + Claude
-- ---------------------------------------------------------------------------
-- Changelog
--   v1.1.1 - FIX: Entered_By holds the user NAME string, not a Users FK
--            (it is absent from the .NET GetShortID resolver map). The
--            Users join on it forced 'varchar to numeric' - join dropped,
--            CreatedBy read directly from the column.
--   v1.1.0 - full .NET job-card field set for WOPrintable v2.0.0:
--            Reason, Cost Centre, Created By (Entered_By), Progress,
--            Supplier Responsibility, Asset Group/Type, Request_Start_Date,
--            Intrusive flag. v1.0.0 columns kept - drop-in replacement,
--            paste over the existing NQ.
--   v1.0.0 - initial.
-- Designer path : Workmate/Workorder/PrintWOHeaders
-- Query Type    : Select Query
-- Database      : TLSQL01_Workmate
-- Parameters    : woIdsCsv  (String)
-- ===========================================================================

SELECT
    h.WO_ID,
    RTRIM(ISNULL(h.Short_WO_Id, ''))            AS Short_WO_Id,
    RTRIM(ISNULL(h.WO_Title, ''))               AS WO_Title,
    RTRIM(ISNULL(h.Status, ''))                 AS Status,
    h.Entry_date                                AS Logged_Date,
    h.Request_Start_Date,
    h.Request_End_Date,
    RTRIM(ISNULL(a.Short_asset_Id, ''))         AS Short_asset_Id,
    RTRIM(ISNULL(a.Asset_Title, ''))            AS Asset_Title,
    RTRIM(ISNULL(grp.Short_Asset_Group_ID, '')) AS Short_Asset_Group_ID,
    RTRIM(ISNULL(grp.Asset_Group_Title, ''))    AS Asset_Group_Title,
    RTRIM(ISNULL(typ.Short_Asset_Type_id, ''))  AS Short_Asset_Type_id,
    RTRIM(ISNULL(typ.Asset_Type_title, ''))     AS Asset_Type_Title,
    RTRIM(ISNULL(l.Short_Location_ID, ''))      AS Short_Location_ID,
    RTRIM(ISNULL(l.Location_Title, ''))         AS Location_Title,
    ISNULL(d.Duration_In_Hours, 0)              AS Duration_In_Hours,
    RTRIM(ISNULL(CAST(d.Notes AS VARCHAR(2000)), '')) AS Notes,
    RTRIM(ISNULL(CAST(d.Intrusive AS VARCHAR(8)), '')) AS Intrusive,
    RTRIM(ISNULL(pr.Short_Priority_Id, ''))     AS Short_Priority_Id,
    RTRIM(ISNULL(g.Short_WO_Group_ID, ''))      AS Short_WO_Group_ID,
    RTRIM(ISNULL(re.Short_reason_Id, ''))       AS Short_Reason_Id,
    RTRIM(ISNULL(cc.Short_Cost_Center_ID, ''))  AS Short_Cost_Center_ID,
    RTRIM(ISNULL(pg.Short_Progress_Id, ''))     AS Short_Progress_Id,
    RTRIM(ISNULL(sr.Short_Supplier_Id, ''))     AS Supplier_Resp,
    RTRIM(ISNULL(CAST(d.Entered_By AS VARCHAR(64)), '')) AS CreatedBy,
    RTRIM(ISNULL(ur.User_Name, ''))             AS RequestedBy,
    RTRIM(ISNULL(ua.User_Name, ''))             AS AssignedTo
FROM WO_N_Header h
LEFT JOIN WO_N_Details    d   ON d.WO_ID           = h.WO_ID
LEFT JOIN Asset           a   ON h.Asset_ID        = a.Asset_ID
LEFT JOIN Asset_Group     grp ON grp.Asset_Group_ID = a.Asset_Group_ID
LEFT JOIN Asset_Type      typ ON typ.Asset_type_id  = a.Asset_Type_ID
LEFT JOIN Location        l   ON h.Location_Id     = l.Location_Id
LEFT JOIN Priority        pr  ON d.Priority_Id     = pr.Priority_Id
LEFT JOIN WorkOrder_Group g   ON d.WO_Group_Id     = g.WO_Group_Id
LEFT JOIN Reason          re  ON d.Reason_Id       = re.Reason_Id
LEFT JOIN Cost_Center     cc  ON d.Cost_Center_Id  = cc.Cost_Center_Id
LEFT JOIN Progress        pg  ON d.Progress_Id     = pg.Progress_Id
LEFT JOIN Supplier        sr  ON d.Supplier_ID_Responsibility = sr.Supplier_Id
LEFT JOIN Users           ur  ON d.User_ID_Requested_By    = ur.User_Id
LEFT JOIN Users           ua  ON d.User_ID_Responsibility  = ua.User_Id
WHERE
    CHARINDEX(',' + CAST(h.WO_ID AS NVARCHAR(20)) + ',',
              ',' + ISNULL(:woIdsCsv, '') + ',') > 0
ORDER BY h.WO_ID
```

## `Workmate/Workorder/PrintWOLines` — 2732 B — modified 2026-08-29T20:21:49Z by Adriaan

```sql
-- ===========================================================================
-- Workmate / Workorder / PrintWOLines            v1.0.0   (read-only)
-- Author: Adriaan + Claude
-- ---------------------------------------------------------------------------
-- Purpose : Activity lines per Work Order for WOPrintable (board #9).
--           Column set and Total CASE cloned from Workorder Activity/Load
--           branch A (stored WO_N_Activity rows, Trx_Type L/P/S/I).
--           The Load NQ's PO-commitment branches (B/C, Trx_Type 'O') are
--           DELIBERATELY out of v1.0.0 - printed card shows stored activity
--           only; add as v1.1.0 if crews need on-order lines on paper.
-- Designer path : Workmate/Workorder/PrintWOLines
-- Query Type    : Select Query
-- Database      : TLSQL01_Workmate
-- Parameters    : woIdsCsv  (String)
-- ===========================================================================

SELECT
    a.WO_ID,
    a.WO_Activity_ID,
    RTRIM(a.Trx_Type)                           AS Trx_Type,
    a.Activity_Date,
    ISNULL(a.Quantity, 0)                       AS Quantity,
    ISNULL(a.Unit_Cost, 0)                      AS Unit_Cost,
    RTRIM(ISNULL(u.User_Name, ''))              AS User_Name,
    RTRIM(ISNULL(sk.Skill_Title, ''))           AS Skill_Title,
    RTRIM(ISNULL(p.Short_Part_ID, ''))          AS Short_Part_ID,
    RTRIM(ISNULL(p.Part_Title, ''))             AS Part_Title,
    RTRIM(ISNULL(w.Warehouse_Title, ''))        AS Warehouse_Title,
    RTRIM(ISNULL(s.Company_Name, ''))           AS Company_Name,
    RTRIM(ISNULL(wc.Work_Code_Title, ''))       AS Work_Code_Title,
    RTRIM(ISNULL(uom.Short_UOM_Id, ''))         AS Short_UOM_Id,
    (CASE WHEN uomf.Factor = -1.0
          THEN ABS(a.Quantity * a.Unit_Cost * ISNULL(uomf.Factor,1)) * (-1)
          ELSE      (a.Quantity * a.Unit_Cost * ISNULL(uomf.Factor,1)) END) AS Total
FROM            WO_N_Activity          a
LEFT OUTER JOIN Users                  u    ON a.User_ID       = u.User_Id
LEFT OUTER JOIN Skill                  sk   ON a.Skill_Id      = sk.Skill_ID
LEFT OUTER JOIN Parts                  p    ON a.Part_Id       = p.Part_ID
LEFT OUTER JOIN Warehouse              w    ON a.Warehouse_ID  = w.Warehouse_ID
LEFT OUTER JOIN Supplier               s    ON a.Supplier_ID   = s.Supplier_ID
LEFT OUTER JOIN Work_Code              wc   ON a.Work_code_Id  = wc.Work_Code_Id
LEFT OUTER JOIN Unit_of_Measure        uom  ON a.UOM_Id        = uom.UOM_Id
LEFT OUTER JOIN Unit_of_Measure_Factor uomf ON a.UOM_Factor_ID = uomf.UOM_Factor_ID
WHERE
    CHARINDEX(',' + CAST(a.WO_ID AS NVARCHAR(20)) + ',',
              ',' + ISNULL(:woIdsCsv, '') + ',') > 0
ORDER BY a.WO_ID, RTRIM(a.Trx_Type), a.WO_Activity_ID
```

## `Workmate/Workorder/RecentByAsset` — 1736 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
/* ============================================================================
   Path:        Workmate/Workorder/RecentByAsset
   File:        Workmate_Workorder_RecentByAsset_v1.0.0.sql
   Version:     1.0.0
   Type:        Query (SELECT)
   Database:    TLSQL01_Workmate          <-- set this on the NQ (default-db trap)
   Author:      Adriaan
   ----------------------------------------------------------------------------
   Changelog (newest first):
     1.0.0  Initial. The 5 most recent work orders for one asset - drives the
            "Recent work orders for this asset" panel on the Create-WO popup
            (populates when a Location + Asset are chosen). WO_IdStyled =
            Status + '|' + Short_WO_Id feeds the WONumBadge render-view column.
   ----------------------------------------------------------------------------
   Parameters:
            assetId  Int8  required  -- WO_N_Header.Asset_ID to filter on
            (no leading colon in this header: Ignition's NQ parser counts
             colon-prefixed names in comments as positional binds)
   Returns: TOP 5 rows - WO_ID, Short_WO_Id, WO_Title, Status, WO_IdStyled,
            Request_Start_Date, Entry_date.  Newest first.
   ============================================================================ */
SELECT TOP 5
       WO_ID,
       RTRIM(ISNULL(Short_WO_Id, ''))                                     AS Short_WO_Id,
       RTRIM(ISNULL(WO_Title, ''))                                        AS WO_Title,
       Status,
       (RTRIM(ISNULL(Status, '')) + '|' + RTRIM(ISNULL(Short_WO_Id, ''))) AS WO_IdStyled,
       Request_Start_Date,
       Entry_date
FROM   dbo.WO_N_Header
WHERE  Asset_ID = :assetId
ORDER BY Entry_date DESC, WO_ID DESC;
```

## `Workmate/Workorder/RecentList` — 1991 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
/* ============================================================================
   Path:        Workmate/Workorder/RecentList
   File:        Workmate_Workorder_RecentList_v1.0.0.sql
   Version:     1.0.1
   Type:        Query (SELECT)
   Database:    TLSQL01_Workmate          <-- set this on the NQ (default-db trap)
   Author:      Adriaan / Claude
   ----------------------------------------------------------------------------
   Changelog (newest first):
     1.0.0  Initial. Last 5 work orders for the KPP Home "Recent Work Orders"
            panel. Ordered by Entry_date (the WO creation timestamp), newest
            first, so a freshly-created WO lands at the top.
            WO_IdStyled = Status + '|' + Short_WO_Id  ->  feeds the WONumBadge
            render-view column (badge colours by the leading status char).
   ----------------------------------------------------------------------------
   Parameters  (none)
   Returns     TOP 5 rows -
                  WO_ID        numeric   (hidden key column, drives row click)
                  Short_WO_Id  varchar
                  WO_Title     varchar
                  Status       char(1)
                  WO_IdStyled  varchar   (Status|Short_WO_Id, for WONumBadge)
                  Asset_ID     numeric
                  Location_Id  numeric
   Notes       Company_ID = 1 (KPP site). Single-site for now; add a
                :companyId parameter when multi-tenant (Sanford etc.).
   ============================================================================ */
SELECT TOP 5
       WO_ID,
       RTRIM(ISNULL(Short_WO_Id, ''))                                     AS Short_WO_Id,
       RTRIM(ISNULL(WO_Title, ''))                                        AS WO_Title,
       Status,
       (RTRIM(ISNULL(Status, '')) + '|' + RTRIM(ISNULL(Short_WO_Id, ''))) AS WO_IdStyled,
       Asset_ID,
       Location_Id
FROM   dbo.WO_N_Header
WHERE  Company_ID = 1
  AND    WO_Type_Flag = 'N'
ORDER BY Entry_date DESC, WO_ID DESC;
```

## `Workmate/Workorder/ResourceCompare` — 5984 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
-- =============================================================================
-- Workmate_Workorder_ResourceCompare_v1_1_1.sql
-- NQ Designer path:  Workmate/Workorder/ResourceCompare
-- NQ TYPE: Select Query
-- Database: TLSQL01_Workmate   (set after creating; register param woId!)
-- Author: Adriaan / Claude
-- -----------------------------------------------------------------------------
-- Changelog (newest first)
--   v1.1.1  FIX: v1.1.0 wrote a colon-prefixed name into this very
--           changelog; the NQ parser counts colon-tokens in comments
--           as binds (journal law). Comments are colon-free forever.
--   v1.1.0  + tick refresh nonce (Integer, REGISTER IT) so the WOMaint
--           card re-queries when wmResourceRefresh bumps view.custom
--           .resTick after Manage Plan edits. ISNULL guard = no-op.
--   v1.0.0  Initial. Resources Compare R1 (spec v1.0.0, gates approved
--           2026-08-30). One row per resource key, planned and actual side
--           by side. Keys (D-RC-1): Parts -> Part_Id; Labour -> User_Id
--           (Kenny plans PEOPLE); Service actuals have no planned
--           counterpart. Actual (D-RC-2) = committed L/P/S activity, the
--           Activity panel's GRAND TOTAL; 'O'/'I' excluded. Actual-only
--           rows carry ' (unplanned)' in Item (D-RC-3); planned-only rows
--           show NULL actuals (render blank = not used yet).
--           Pre-2016 T-SQL: FULL OUTER JOIN on derived aggregates.
--
-- Parameters:
--   woId   Integer      tick   Integer     << REGISTER BOTH
--
-- Returns: Type, Item, PlanQty, PlanCost, ActQty, ActCost, Delta
-- =============================================================================
SELECT
    CASE k.KeyType WHEN 'P' THEN 'Part'
                   WHEN 'L' THEN 'Labour'
                   WHEN 'S' THEN 'Service'
                   ELSE k.KeyType END                       AS Type,
    CASE k.KeyType
        WHEN 'P' THEN RTRIM(ISNULL(p.Short_Part_ID, ''))
                      + ' - ' + RTRIM(ISNULL(p.Part_Title, ''))
        WHEN 'L' THEN RTRIM(ISNULL(u.User_Name, ''))
        WHEN 'S' THEN RTRIM(ISNULL(s.Company_Name, 'Service'))
        ELSE ''
    END + CASE WHEN pa.PlanQty IS NULL THEN ' (unplanned)' ELSE '' END
                                                            AS Item,
    pa.PlanQty                                              AS PlanQty,
    pa.PlanCost                                             AS PlanCost,
    aa.ActQty                                               AS ActQty,
    aa.ActCost                                              AS ActCost,
    ISNULL(aa.ActCost, 0) - ISNULL(pa.PlanCost, 0)          AS Delta
FROM (
    SELECT COALESCE(pa2.KeyType, aa2.KeyType) AS KeyType,
           COALESCE(pa2.KeyId,  aa2.KeyId)  AS KeyId
    FROM (
        SELECT CASE RTRIM(ISNULL(Resource_Type, '')) WHEN 'P' THEN 'P' ELSE 'L' END AS KeyType,
               CASE RTRIM(ISNULL(Resource_Type, '')) WHEN 'P' THEN ISNULL(Part_Id, -1)
                    ELSE ISNULL(User_Id, -1) END AS KeyId
        FROM dbo.WO_N_Resource WHERE WO_Id = :woId
        GROUP BY CASE RTRIM(ISNULL(Resource_Type, '')) WHEN 'P' THEN 'P' ELSE 'L' END,
                 CASE RTRIM(ISNULL(Resource_Type, '')) WHEN 'P' THEN ISNULL(Part_Id, -1)
                      ELSE ISNULL(User_Id, -1) END
    ) pa2
    FULL OUTER JOIN (
        SELECT RTRIM(ISNULL(Trx_Type, '')) AS KeyType,
               CASE RTRIM(ISNULL(Trx_Type, ''))
                    WHEN 'P' THEN ISNULL(Part_Id, -1)
                    WHEN 'L' THEN ISNULL(User_ID, -1)
                    ELSE ISNULL(Supplier_ID, -1) END AS KeyId
        FROM dbo.WO_N_Activity
        WHERE WO_ID = :woId AND RTRIM(ISNULL(Trx_Type, '')) IN ('L', 'P', 'S')
        GROUP BY RTRIM(ISNULL(Trx_Type, '')),
                 CASE RTRIM(ISNULL(Trx_Type, ''))
                      WHEN 'P' THEN ISNULL(Part_Id, -1)
                      WHEN 'L' THEN ISNULL(User_ID, -1)
                      ELSE ISNULL(Supplier_ID, -1) END
    ) aa2 ON aa2.KeyType = pa2.KeyType AND aa2.KeyId = pa2.KeyId
) k
LEFT JOIN (
    SELECT CASE RTRIM(ISNULL(Resource_Type, '')) WHEN 'P' THEN 'P' ELSE 'L' END AS KeyType,
           CASE RTRIM(ISNULL(Resource_Type, '')) WHEN 'P' THEN ISNULL(Part_Id, -1)
                ELSE ISNULL(User_Id, -1) END AS KeyId,
           SUM(ISNULL(Planned_Qty, 0))                          AS PlanQty,
           SUM(ISNULL(Planned_Qty, 0) * ISNULL(Planned_Unit_Cost, 0)) AS PlanCost
    FROM dbo.WO_N_Resource WHERE WO_Id = :woId
    GROUP BY CASE RTRIM(ISNULL(Resource_Type, '')) WHEN 'P' THEN 'P' ELSE 'L' END,
             CASE RTRIM(ISNULL(Resource_Type, '')) WHEN 'P' THEN ISNULL(Part_Id, -1)
                  ELSE ISNULL(User_Id, -1) END
) pa ON pa.KeyType = k.KeyType AND pa.KeyId = k.KeyId
LEFT JOIN (
    SELECT RTRIM(ISNULL(Trx_Type, '')) AS KeyType,
           CASE RTRIM(ISNULL(Trx_Type, ''))
                WHEN 'P' THEN ISNULL(Part_Id, -1)
                WHEN 'L' THEN ISNULL(User_ID, -1)
                ELSE ISNULL(Supplier_ID, -1) END AS KeyId,
           SUM(ISNULL(Quantity, 0))                             AS ActQty,
           SUM(ISNULL(Quantity, 0) * ISNULL(Unit_Cost, 0))      AS ActCost
    FROM dbo.WO_N_Activity
    WHERE WO_ID = :woId AND RTRIM(ISNULL(Trx_Type, '')) IN ('L', 'P', 'S')
    GROUP BY RTRIM(ISNULL(Trx_Type, '')),
             CASE RTRIM(ISNULL(Trx_Type, ''))
                  WHEN 'P' THEN ISNULL(Part_Id, -1)
                  WHEN 'L' THEN ISNULL(User_ID, -1)
                  ELSE ISNULL(Supplier_ID, -1) END
) aa ON aa.KeyType = k.KeyType AND aa.KeyId = k.KeyId
LEFT JOIN dbo.Parts    p ON k.KeyType = 'P' AND p.Part_ID     = k.KeyId
LEFT JOIN dbo.Users    u ON k.KeyType = 'L' AND u.User_Id     = k.KeyId
LEFT JOIN dbo.Supplier s ON k.KeyType = 'S' AND s.Supplier_ID = k.KeyId
WHERE ISNULL(:tick, 0) >= 0
ORDER BY
    CASE k.KeyType WHEN 'P' THEN 1 WHEN 'L' THEN 2 ELSE 3 END,
    CASE WHEN pa.PlanQty IS NULL THEN 1 ELSE 0 END,
    Item
```

## `Workmate/Workorder/ResourceList` — 2760 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- ==============================================================================
-- Query Path: Workmate/Workorder/ResourceList
-- File: Workmate_Workorder_ResourceList_v1_0_0.sql
-- Type: Select Query
-- Database: TLSQL01_Workmate
-- Author: Adriaan
-- Version: 1.0.0
-- ==============================================================================
-- Changelog (newest first):
--   1.0.0  Initial release. Planned resources for the WOMaint AllResourcesCard
--          (WOMaint v16.14.0). Replaces the broken SelectDynamic-style
--          whereCondition bindings, which passed SQL fragments as JDBC bind
--          values and could never return rows in Ignition. Ports the .NET
--          frmWOMaintenance lstvViewResource source: dbo.WO_N_Resource by
--          WO_Id, Resource_Type 'P' (Parts) / 'L' (Labour), Planned_Qty x
--          Planned_Unit_Cost. Returns BOTH the display aliases the table
--          columns use (Type/Part_Code/Description/Qty/Cost/Total) AND the
--          raw Planned_Qty / Planned_Unit_Cost columns the card-total label
--          transform sums. Scope: WO_N only - archived (WO_C_Resource) WOs
--          show an empty card for now.
-- ==============================================================================
-- Parameters:
--   woId (Int4)                          -- WO_N_Header.WO_ID
-- Returns:
--   Type, Part_Code, Description, Qty, Cost, Total,
--   Planned_Qty, Planned_Unit_Cost
-- ==============================================================================

SELECT
    CASE RTRIM(ISNULL(r.Resource_Type, ''))
         WHEN 'P' THEN 'Part'
         WHEN 'L' THEN 'Labour'
         ELSE RTRIM(ISNULL(r.Resource_Type, ''))
    END AS Type,
    CASE WHEN RTRIM(ISNULL(r.Resource_Type, '')) = 'P'
         THEN RTRIM(ISNULL(p.Short_Part_ID, ''))
         ELSE ''
    END AS Part_Code,
    CASE WHEN RTRIM(ISNULL(r.Resource_Type, '')) = 'L'
         THEN CONCAT(RTRIM(ISNULL(u.User_Name, '')),
                     CASE WHEN sk.Skill_Title IS NULL THEN ''
                          ELSE CONCAT(' - ', RTRIM(sk.Skill_Title)) END)
         ELSE RTRIM(ISNULL(r.Resource_Note, ''))
    END AS Description,
    ISNULL(r.Planned_Qty, 0)                                 AS Qty,
    ISNULL(r.Planned_Unit_Cost, 0)                           AS Cost,
    ISNULL(r.Planned_Qty, 0) * ISNULL(r.Planned_Unit_Cost, 0) AS Total,
    ISNULL(r.Planned_Qty, 0)                                 AS Planned_Qty,
    ISNULL(r.Planned_Unit_Cost, 0)                           AS Planned_Unit_Cost
FROM dbo.WO_N_Resource r
LEFT JOIN dbo.Parts p  ON r.Part_Id  = p.Part_ID
LEFT JOIN dbo.Users u  ON r.User_Id  = u.User_Id
LEFT JOIN dbo.Skill sk ON r.Skill_Id = sk.Skill_ID
WHERE r.WO_Id = :woId
ORDER BY r.Resource_Type, r.Res_Id
```

## `Workmate/Workorder/ResourceRows` — 2550 B — modified 2026-08-29T20:21:50Z by Adriaan

```sql
-- =============================================================================
-- Workmate_Workorder_ResourceRows_v1_0_1.sql
-- NQ Designer path:  Workmate/Workorder/ResourceRows
-- NQ TYPE: Select Query
-- Database: TLSQL01_Workmate   (set DB + register BOTH params!)
-- Author: Adriaan / Claude
-- -----------------------------------------------------------------------------
-- Changelog (newest first)
--   v1.0.1  FIX: the changelog itself contained a colon-prefixed param
--           name, and the NQ parser counts EVERY colon-token in the
--           file - comments included - as a bind (journal law, now
--           bitten from the inside). Comments are colon-free forever.
--   v1.0.0  Initial. Resource Editor R2: the RAW planned rows behind the
--           compare card's aggregates - one row per WO_N_Resource record,
--           Res_Id included, for the Manage Plan popup's CRUD table.
--           The tick param is a refresh nonce (bumped by
--           wmResourceRefresh); its ISNULL guard is a no-op.
--
-- Parameters:
--   woId   Integer      tick   Integer     << REGISTER BOTH
--
-- Returns: Res_Id, TypeRaw, Type, Item, Qty, Cost, Total, Note
-- =============================================================================
SELECT
    r.Res_Id,
    RTRIM(ISNULL(r.Resource_Type, ''))                     AS TypeRaw,
    CASE RTRIM(ISNULL(r.Resource_Type, ''))
        WHEN 'P' THEN 'Part' WHEN 'L' THEN 'Labour'
        ELSE RTRIM(ISNULL(r.Resource_Type, '')) END        AS Type,
    CASE RTRIM(ISNULL(r.Resource_Type, ''))
        WHEN 'P' THEN RTRIM(ISNULL(p.Short_Part_ID, ''))
                      + ' - ' + RTRIM(ISNULL(p.Part_Title, ''))
        WHEN 'L' THEN RTRIM(ISNULL(u.User_Name, ''))
                      + CASE WHEN sk.Skill_Title IS NULL THEN ''
                             ELSE ' - ' + RTRIM(sk.Skill_Title) END
        ELSE RTRIM(ISNULL(r.Resource_Note, '')) END        AS Item,
    ISNULL(r.Planned_Qty, 0)                               AS Qty,
    ISNULL(r.Planned_Unit_Cost, 0)                         AS Cost,
    ISNULL(r.Planned_Qty, 0) * ISNULL(r.Planned_Unit_Cost, 0) AS Total,
    RTRIM(ISNULL(r.Resource_Note, ''))                     AS Note
FROM dbo.WO_N_Resource r
LEFT JOIN dbo.Parts p  ON p.Part_ID   = r.Part_Id
LEFT JOIN dbo.Users u  ON u.User_Id   = r.User_Id
LEFT JOIN dbo.Skill sk ON sk.Skill_ID = r.Skill_Id
WHERE r.WO_Id = :woId
  AND ISNULL(:tick, 0) >= 0
ORDER BY
    CASE RTRIM(ISNULL(r.Resource_Type, ''))
        WHEN 'P' THEN 1 WHEN 'L' THEN 2 ELSE 3 END,
    r.Res_Id ASC
```

## `Workmate/Workorder/Search` — 6372 B — modified 2026-08-29T20:21:50Z by Adriaan

```sql
-- ==============================================================================
-- Query Path: Workmate/Workorder/Search
-- File: Workmate_Workorder_Search_v12.sql
-- Type: Select Query
-- Database: TLSQL01_Workmate
-- Author: Adriaan
-- Version: 12 (includeClosed / includeArchive gain ONLY mode, value 2)
-- ==============================================================================
-- Changelog (newest first):
--   12 MODE semantics on the two include params (WOMaint v16.20.0 chips,
--      Adriaan 2026-08-12). includeClosed. 0 = hide C/D (default live view),
--      1 = show everything (unchanged - the PO-B handoff still sends 1),
--      2 = ONLY Closed/Cancelled. includeArchive. 0 = live arm only,
--      1 = live arm + archive arm (unchanged), 2 = ONLY the archive arm
--      (live arm suppressed). Values 0/1 behave byte-identically to v11,
--      so every existing caller is unaffected.
--   11 CP detection moved from the Short_WO_Id prefix to the WO's LOCATION
--      (D-WOID-3 fix, Adriaan 2026-07-14). Capital projects live at the CP
--      location (Short_Location_ID split-on-dash prefix = 'CP', e.g.
--      'CP-00'); code-seeded WOs there can carry a NON-CP id prefix
--      (P0462-002 was minted from its asset id, not the location), so a
--      Short_WO_Id LIKE 'CP-%' test missed them. Now: capital = location
--      prefix 'CP', mirroring the id generator's slid.split('-')[0] logic.
--      NULL-safe via COALESCE (a WO with no location stays in the WO view).
--      'N' = normal WOs at non-CP locations; 'CP' = normal WOs at the CP
--      location; 'M' / '' unchanged.
--   10 woType gains 'CP' (see v11 note). 'N' now means WOs EXCLUDING CP.
--   9  New HasPO column (1/0) on BOTH arms (WONumBadge v1.3.0 PO dot).
--   8  NULL SAFETY: omitted/NULL woType defaults to 'N' in the SQL itself.
--   7  PM SEPARATION v2: woType parameter (N / M / empty = both).
--   6  Hardcoded WO_Type_Flag='N' (never deployed; superseded by v7).
--   5  LEFT JOIN WO_N_Details / WO_C_Details to expose Progress_Id.
--   4  shortWoId searches both ID and Title.
-- ==============================================================================
-- Parameters:
--   shortWoId (String, default "")       -- searches Short_WO_Id AND WO_Title
--   woTitle (String, default "")          -- reserved for future advanced filter
--   shortAssetId (String, default "")
--   shortLocationId (String, default "")
--   includeArchive (Int4, default 0)      -- 0 live only, 1 live+archive, 2 ONLY archive
--   includeClosed (Int4, default 1)       -- 0 hide C/D, 1 show all, 2 ONLY C/D
--   woType (String)                       -- N=normal WOs at non-CP locations
--                                            (also the omitted/NULL default,
--                                            enforced in SQL), CP=normal WOs at
--                                            the CP location, M=PM only,
--                                            empty string=all
-- Returns:
--   WO_ID, Short_WO_Id, WO_Title, Asset_ID, Location_Id, Status, Progress_Id,
--   HasPO (1/0), Entry_date
-- ==============================================================================

SELECT 
    h.WO_ID,
    h.Short_WO_Id,
    h.WO_Title,
    a.Short_asset_Id AS Asset_ID,
    l.Short_Location_ID AS Location_Id,
    h.Status,
    d.Progress_Id,
    CASE WHEN EXISTS (SELECT 1 FROM dbo.PO_Header  ph WHERE ph.WO_Id = h.WO_ID)
           OR EXISTS (SELECT 1 FROM dbo.PO_Details pd WHERE pd.WO_Id = h.WO_ID)
         THEN 1 ELSE 0 END AS HasPO,
    h.Entry_date
FROM WO_N_Header h
LEFT JOIN Asset a ON h.Asset_ID = a.Asset_ID
LEFT JOIN Location l ON h.Location_Id = l.Location_Id
LEFT JOIN WO_N_Details d ON h.WO_ID = d.WO_ID
WHERE COALESCE(:includeArchive, 0) <> 2
  AND (COALESCE(:shortWoId, '') = '' 
       OR h.Short_WO_Id LIKE '%' + :shortWoId + '%'
       OR h.WO_Title LIKE '%' + :shortWoId + '%')
  AND (COALESCE(:woTitle, '') = '' OR h.WO_Title LIKE '%' + :woTitle + '%')
  AND (COALESCE(:shortAssetId, '') = '' OR a.Short_asset_Id LIKE '%' + :shortAssetId + '%')
  AND (COALESCE(:shortLocationId, '') = '' OR l.Short_Location_ID LIKE '%' + :shortLocationId + '%')
  AND (COALESCE(:includeClosed, 1) = 1
       OR (COALESCE(:includeClosed, 1) = 0 AND h.Status NOT IN ('C', 'D'))
       OR (COALESCE(:includeClosed, 1) = 2 AND h.Status IN ('C', 'D')))
  AND (
        COALESCE(:woType, 'N') = ''
     OR (COALESCE(:woType, 'N') = 'N'  AND h.WO_Type_Flag = 'N'
           AND COALESCE(l.Short_Location_ID, '') NOT LIKE 'CP-%'
           AND COALESCE(l.Short_Location_ID, '') <> 'CP')
     OR (COALESCE(:woType, 'N') = 'CP' AND h.WO_Type_Flag = 'N'
           AND (COALESCE(l.Short_Location_ID, '') LIKE 'CP-%'
                OR COALESCE(l.Short_Location_ID, '') = 'CP'))
     OR (COALESCE(:woType, 'N') = 'M'  AND h.WO_Type_Flag = 'M')
      )

UNION ALL

SELECT 
    c.WO_ID,
    c.Short_WO_Id,
    c.WO_Title,
    a.Short_asset_Id AS Asset_ID,
    l.Short_Location_ID AS Location_Id,
    c.Status,
    cd.Progress_Id,
    CASE WHEN EXISTS (SELECT 1 FROM dbo.PO_Header  ph WHERE ph.WO_Id = c.WO_ID)
           OR EXISTS (SELECT 1 FROM dbo.PO_Details pd WHERE pd.WO_Id = c.WO_ID)
         THEN 1 ELSE 0 END AS HasPO,
    c.Entry_date
FROM WO_C_header c
LEFT JOIN Asset a ON c.Asset_ID = a.Asset_ID
LEFT JOIN Location l ON c.Location_Id = l.Location_Id
LEFT JOIN WO_C_Details cd ON c.WO_ID = cd.WO_ID
WHERE COALESCE(:includeArchive, 0) IN (1, 2)
  AND (COALESCE(:shortWoId, '') = '' 
       OR c.Short_WO_Id LIKE '%' + :shortWoId + '%'
       OR c.WO_Title LIKE '%' + :shortWoId + '%')
  AND (COALESCE(:woTitle, '') = '' OR c.WO_Title LIKE '%' + :woTitle + '%')
  AND (COALESCE(:shortAssetId, '') = '' OR a.Short_asset_Id LIKE '%' + :shortAssetId + '%')
  AND (COALESCE(:shortLocationId, '') = '' OR l.Short_Location_ID LIKE '%' + :shortLocationId + '%')
  AND (
        COALESCE(:woType, 'N') = ''
     OR (COALESCE(:woType, 'N') = 'N'  AND c.WO_Type_Flag = 'N'
           AND COALESCE(l.Short_Location_ID, '') NOT LIKE 'CP-%'
           AND COALESCE(l.Short_Location_ID, '') <> 'CP')
     OR (COALESCE(:woType, 'N') = 'CP' AND c.WO_Type_Flag = 'N'
           AND (COALESCE(l.Short_Location_ID, '') LIKE 'CP-%'
                OR COALESCE(l.Short_Location_ID, '') = 'CP'))
     OR (COALESCE(:woType, 'N') = 'M'  AND c.WO_Type_Flag = 'M')
      )

ORDER BY Entry_date DESC
```

## `Workmate/Workorder/SearchDynamic` — 1880 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder/SearchDynamic
-- Type:       Select Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Dialect:    mssql-only
-- Version:    1.1
-- ==============================================================================
-- Changelog (newest first):
--   1.1  Stripped leading ':' from parameter names in the doc-header comment.
--        Ignition's NQ parameter parser scans the full source for ':identifier'
--        patterns including inside SQL comments, then tries to bind them
--        positionally against the prepared SQL (which has comments stripped).
--        Result: phantom extra positions, JDBC "index N out of range".
--        Rule: doc-header parameter refs use plain name, no colon prefix.
--   1.0  Rename of legacy 'Workmate/Workorder/Search' (the dynamic-SQL
--        variant) to 'Workmate/Workorder/SearchDynamic' as part of WO-1
--        v2.0 collision resolution. Added 'Dialect: mssql-only' header
--        to flag that the EXEC of a T-SQL proc is not portable. WO-2.5
--        will parameterize this and retire the proc. SQL body otherwise
--        unchanged.
-- ==============================================================================
-- Parameters:
--   whereCondition     String  required  -- raw SQL WHERE body, no leading WHERE
--   orderByExpression  String  required  -- raw SQL ORDER BY body, no leading ORDER BY
-- Returns:
--   Filtered WO_N_Header rows per dynamic predicate.
-- ==============================================================================
-- PG-CONVERT: rewrite as parameterized SELECT in WO-2.5
-- ==============================================================================

EXEC dbo.wmsp_WO_N_HeaderSelectDynamic
    @WhereCondition    = :whereCondition,
    @OrderByExpression = :orderByExpression;
```

## `Workmate/Workorder/StampClosed` — 1240 B — modified 2026-08-29T20:21:53Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder/StampClosed
-- Type:       Update Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Dialect:    portable
-- Version:    1.0
-- ==============================================================================
-- Changelog (newest first):
--   1.0  New. Sets or clears the Closed stamp (User_ID_ClosedBy + Closed_Date)
--        on WO_N_Details. Matches the .NET frmWOMaintenance rule: on status C
--        set both (only when not already set -- the caller guards that); on
--        reopen the caller passes NULLs to clear. Used by
--        workmate.workorder.updateStatus. Per WO-3 spec v1.2.
-- ==============================================================================
-- Parameters:
--   id         Int8      required  -- WO_N_Details.WO_ID
--   userId     Int8      nullable  -- User_ID_ClosedBy (NULL to clear)
--   closedDate DateTime  nullable  -- Closed_Date (NULL to clear)
-- Returns:
--   (nothing -- update query)
-- ==============================================================================

UPDATE dbo.WO_N_Details
SET User_ID_ClosedBy = :userId,
    Closed_Date      = :closedDate
WHERE WO_ID = :id;
```

## `Workmate/Workorder/Update` — 1925 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder/Update
-- Type:       Update Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Dialect:    portable
-- Version:    1.2
-- ==============================================================================
-- Changelog (newest first):
--   1.2  Added Company_ID to the SET list (header edit was dropping it).
--   1.1  Stripped leading ':' from parameter names in the doc-header comment
--        (Ignition NQ parser counts colon-prefixed names in comments as positional
--        binds -> JDBC "index N out of range"). No SQL body change.
--   1.0  Rewrite of legacy 'Work Order/Update' (broken: tried to update
--        WO_Description, Priority_ID, Progress_ID, User_Id_Assigned_To,
--        Fault_ID, Reason_ID on Header -- none of those live there).
--        Reduced to header-only fields. Details fields stay on
--        wmsp_WO_N_DetailsInsertUpdate via Workorder Detail/InsertUpdate.
--        Renamed for consolidation. Per WO-1 spec v2.0.
-- ==============================================================================
-- Parameters:
--   id            Int8      required  -- WO_N_Header.WO_ID
--   title         String    required  -- new WO_Title
--   locationId    Int8      required  -- new Location_Id
--   assetId       Int8      nullable  -- new Asset_ID (NULL allowed)
--   companyId     Int8      nullable  -- new Company_ID
--   requestStart  DateTime  required
--   requestEnd    DateTime  required
-- Returns:
--   (nothing -- update query)
-- ==============================================================================

UPDATE dbo.WO_N_Header
SET WO_Title           = :title,
    Location_Id        = :locationId,
    Asset_ID           = :assetId,
    Company_ID         = :companyId,
    Request_Start_Date = :requestStart,
    Request_End_Date   = :requestEnd
WHERE WO_ID = :id;
```

## `Workmate/Workorder/UpdateProgress` — 1103 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder/UpdateProgress
-- Type:       Update Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Dialect:    portable
-- Version:    1.0
-- ==============================================================================
-- Changelog (newest first):
--   1.0  New. Sets Progress_Id + Progress_User + Progress_Date on
--        WO_N_Details (progress lives on Details, not Header). Used by
--        workmate.workorder.updateProgress. Per WO-3 spec v1.2.
-- ==============================================================================
-- Parameters:
--   id         Int8  required  -- WO_N_Details.WO_ID
--   progressId Int8  required  -- new Progress_Id (1..6)
--   userId     Int8  required  -- Progress_User (who changed it)
-- Returns:
--   (nothing -- update query)
-- ==============================================================================

UPDATE dbo.WO_N_Details
SET Progress_Id   = :progressId,
    Progress_User = :userId,
    Progress_Date = CURRENT_TIMESTAMP
WHERE WO_ID = :id;
```

## `Workmate/Workorder/UpdateStatus` — 1646 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder/UpdateStatus
-- Type:       Update Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Dialect:    portable
-- Version:    1.1
-- ==============================================================================
-- Changelog (newest first):
--   1.1  Stripped leading ':' from parameter names in the doc-header comment
--        (Ignition NQ parser counts colon-prefixed names in comments as positional
--        binds -> JDBC "index N out of range"). No SQL body change.
--   1.0  Rewrite of legacy 'Work Order/UpdateStatus' (broken: tried to write
--        Actual_Start_Date and Actual_End_Date on Header -- both columns
--        exist on neither table; also used PO-only status code 'X'). Reduced
--        to a pure header status touch. Real lifecycle dates (Closed_Date
--        etc.) live on WO_N_Details and require multi-table coordination;
--        that work lives in WO-3's workmate.workorder.updateStatus()
--        alongside the WO_Status FK row. GETDATE() removed -- date logic
--        moves to the service layer where CURRENT_TIMESTAMP is portable.
--        Renamed for consolidation. Per WO-1 spec v2.0.
-- ==============================================================================
-- Parameters:
--   id      Int8    required  -- WO_N_Header.WO_ID
--   status  String  required  -- WO status code (R/H/P/K/A/V/C/D/F)
-- Returns:
--   (nothing -- update query)
-- ==============================================================================

UPDATE dbo.WO_N_Header
SET Status = :status
WHERE WO_ID = :id;
```

## `Workmate/Workorder Detail/GetCondition` — 732 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder Detail/GetCondition
-- Type:       Select Query   Database: TLSQL01_Workmate   Author: Adriaan   v1.0
-- ==============================================================================
-- Current Condition_Id for one WO, so the Activity-tab Condition dropdown shows
-- the WO's existing condition on load.
-- ==============================================================================
-- Parameters:  woId  Int  required
-- Returns:     conditionId
-- ==============================================================================

SELECT TOP 1 ISNULL(Condition_Id, 0) AS conditionId
FROM dbo.WO_N_Details
WHERE WO_ID = :woId;
```

## `Workmate/Workorder Detail/InsertUpdate` — 3063 B — modified 2026-05-15T07:53:58Z by Adriaan

```sql
-- Workmate/Workorder Detail/InsertUpdate
-- Query Type: Update Query
-- Parameters: woId (Int8), woGroupId (Int8), priorityId (Int8), faultId (Int8), reasonId (Int8), costCenterId (Int8), accountId (Int8), progressId (Int8), intrusive (String), 
--				durationInHours (Int8), generatedFrom (String), downTime (Int8), enteredBy (String), reference (String), notes (String), supplierIdRequestedBy (Int8), 
--			userIdRequestedBy (Int8), supplierIdChargeTo (Int8), supplierIdResponsibility (Int8), userIdResponsibility (Int8), userIdAckBy (Int8), acknowledgementDate (DateTime), 
--			userIdApprovedBy (Int8), approvedDate (DateTime), firstActivityDate (DateTime), lastActivityDate (DateTime), printed (String), conditionId (Int8), 
--			userIdClosedby (Int8), closedDate (DateTime), meterReading (Int8), meterId (Int8), woc1Id (Int8), woc2Id (Int8), woc3Id (Int8), userIdCancelledby (Int8), 
--			cancelledDate (DateTime), serverName (String), intrusiveComplete (String), userIdIntrusivecomplete (Int8), intrusivecompleteDate (DateTime), unlockDate (DateTime), 
--			unlockNotes (String), userIdUnlockBy (Int8), estCost (Int8), progressUser (Int8), progressDate (DateTime), userIdLastSave (Int8), lastSaveDate (DateTime)
EXEC wmsp_WO_N_DetailsInsertUpdate
    @WO_ID = :woId,
    @WO_Group_Id = :woGroupId,
    @Priority_Id = :priorityId,
    @Fault_Id = :faultId,
    @Reason_Id = :reasonId,
    @Cost_Center_Id = :costCenterId,
    @Account_Id = :accountId,
    @Progress_Id = :progressId,
    @Intrusive = :intrusive,
    @Duration_In_Hours = :durationInHours,
    @Generated_From = :generatedFrom,
    @Down_Time = :downTime,
    @Entered_By = :enteredBy,
    @Reference = :reference,
    @Notes = :notes,
    @Supplier_ID_Requested_By = :supplierIdRequestedBy,
    @User_ID_Requested_By = :userIdRequestedBy,
    @Supplier_ID_charge_To = :supplierIdChargeTo,
    @Supplier_ID_Responsibility = :supplierIdResponsibility,
    @User_ID_Responsibility = :userIdResponsibility,
    @User_Id_Ack_by = :userIdAckBy,
    @Acknowledgement_date = :acknowledgementDate,
    @User_Id_Approved_By = :userIdApprovedBy,
    @Approved_Date = :approvedDate,
    @first_activity_date = :firstActivityDate,
    @last_activity_date = :lastActivityDate,
    @Printed = :printed,
    @Condition_Id = :conditionId,
    @User_ID_ClosedBy = :userIdClosedby,
    @Closed_Date = :closedDate,
    @Meter_Reading = :meterReading,
    @Meter_ID = :meterId,
    @WOC1_ID = :woc1Id,
    @WOC2_ID = :woc2Id,
    @WOC3_ID = :woc3Id,
    @User_ID_CancelledBy = :userIdCancelledby,
    @Cancelled_Date = :cancelledDate,
    @Server_Name = :serverName,
    @Intrusive_Complete = :intrusiveComplete,
    @User_ID_IntrusiveComplete = :userIdIntrusivecomplete,
    @IntrusiveComplete_Date = :intrusivecompleteDate,
    @UnLock_Date = :unlockDate,
    @UnLock_Notes = :unlockNotes,
    @User_ID_UnLock_By = :userIdUnlockBy,
    @Est_Cost = :estCost,
    @Progress_User = :progressUser,
    @Progress_Date = :progressDate,
    @User_id_Last_Save = :userIdLastSave,
    @Last_Save_Date = :lastSaveDate;
```

## `Workmate/Workorder Detail/Item` — 600 B — modified 2026-05-15T07:53:58Z by Adriaan

```sql
-- Workmate/Workorder Detail/Item
-- Query Type: Select Query
-- Parameters: woId (Int8)
SELECT
    Account_Id,
    Acknowledgement_date,
    Approved_Date,
    Cancelled_Date,
    Closed_Date,
    Condition_Id,
    Cost_Center_Id,
    Down_Time,
    Duration_In_Hours,
    Entered_By,
    Est_Cost,
    Fault_Id,
    first_activity_date,
    Generated_From,
    Intrusive,
    Intrusive_Complete,
    IntrusiveComplete_Date,
    last_activity_date,
    Last_Save_Date,
    Meter_ID,
    Meter_Reading,
    Notes,
    Printed,
    Priority_Id,
    Progress_Date
FROM WO_N_Details
WHERE WO_ID = :woId;
```

## `Workmate/Workorder Detail/SetCondition` — 913 B — modified 2026-08-29T20:21:50Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder Detail/SetCondition
-- Type:       Update Query   Database: TLSQL01_Workmate   Author: Adriaan   v1.0
-- ==============================================================================
-- Immediate single-field write of the WO's Condition from the Activity tab.
-- WO_N_Details is 1 row per WO (keyed WO_ID), so this UPDATE is exact.
-- The technician completing the WO sets Condition here; it persists at once
-- (no toolbar Save needed), matching the status-pill immediate-write pattern.
-- ==============================================================================
-- Parameters:
--   conditionId  Int  required
--   woId         Int  required
-- ==============================================================================

UPDATE dbo.WO_N_Details
SET Condition_Id = :conditionId
WHERE WO_ID = :woId;
```

## `Workmate/Workorder Activity/AllComments` — 1509 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder Activity/AllComments
-- File:       Workmate_WOActivity_AllComments_query_v1_0.sql
-- Type:       Select Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Version:    1.0
-- ==============================================================================
-- All activity comments for one WO - the "All Comments" viewer (mirrors the
-- .NET Activity Comments popup: Date / User / Comments).
-- WO_N_Activity_Comments holds only the text + keys; Date and User come from the
-- parent WO_N_Activity row (Entry_Date, User_ID_Created_By) joined to Users.
-- ==============================================================================
-- Parameters:
--   woId  Int  required
-- Returns:
--   commentDate, userName, comment, woActivityId  (newest first)
-- ==============================================================================

SELECT
    a.Entry_Date                         AS commentDate,
    RTRIM(ISNULL(u.User_Name, ''))       AS userName,
    RTRIM(ISNULL(c.Comments, ''))        AS comment,
    c.WO_Activity_ID                     AS woActivityId
FROM dbo.WO_N_Activity_Comments c
LEFT OUTER JOIN dbo.WO_N_Activity a
       ON c.WO_Activity_ID = a.WO_Activity_ID
      AND c.WO_Id = a.WO_ID
LEFT OUTER JOIN dbo.Users u
       ON a.User_ID_Created_By = u.User_Id
WHERE c.WO_Id = :woId
  AND LEN(RTRIM(ISNULL(c.Comments, ''))) > 0
ORDER BY a.Entry_Date DESC, c.WO_Activity_ID DESC;
```

## `Workmate/Workorder Activity/Load` — 10613 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
-- ===========================================================================
-- Workmate / Workorder Activity / Load            v1.1.0   (read-only)
-- Author: Adriaan
-- ---------------------------------------------------------------------------
-- Changelog
--   v1.1.0 - folded in the On-Order ('O') rows as UNION ALL of the two
--            PO-derived branches the .NET grid merges:
--              B) received-but-not-invoiced  (PO_Receipt_Detail, status T/R)
--              C) still-on-order             (PO_Details, qty outstanding)
--   v1.0.0 - initial: stored WO_N_Activity rows (Trx_Type L/P/S/I).
--
-- Purpose : One parameterised query returning every activity line for a Work
--           Order - stored activity AND live PO commitment - with all friendly
--           names joined in SQL. Replaces the legacy ActTable approach
--           (7 Dropdown NQs + Jython joins per WO selection).
--
-- Designer path : Workmate/Workorder Activity/Load
-- Query Type    : Select Query
-- Database      : TLSQL01_Workmate
-- Scope         : DG
-- Parameters    : woId  (Integer / sqlType 3)   -- referenced 3x, binds same value
--
-- Branches / Trx_Type
--   A  WO_N_Activity        -> L / P / S / I   (stored activity; has WO_Activity_ID)
--   B  PO_Receipt_Detail    -> O               (received, not yet invoiced)
--   C  PO_Details           -> O               (ordered, not yet received)
--   B & C carry WO_Activity_ID = NULL (no activity row - they are live PO lines).
--
-- Total : Qty x Unit_Cost x ISNULL(UOM_Factor.Factor,1) - factor defaults to 1
--         when NULL (e.g. Part issues have no UOM_Factor_ID), so qty x cost is
--         not nulled to 0, with the Factor=-1 ABS()*-1
--         credit guard. Cost driver is Unit_of_Measure_Factor.Factor, NOT
--         WO_N_Activity.labour_factor.
--
-- Column order is IDENTICAL across all three branches (38 cols) so UNION ALL
-- lines up. Result column NAMES come from branch A only (SQL Server rule).
-- char columns RTRIM'd for clean card text.
--
-- Note: branch C has no PO status gate beyond <> 'D' (matches .NET strQuery2),
--       so it shows outstanding lines on not-yet-issued POs too. Faithful to
--       legacy; revisit if it proves noisy.
-- ===========================================================================

-- ---- Branch A : stored WO activity (L / P / S / I) ------------------------
SELECT
    a.WO_Activity_ID,
    a.WO_ID,
    RTRIM(a.Trx_Type)                       AS Trx_Type,
    a.Activity_Date,
    a.Entry_Date,
    a.Quantity,
    a.Unit_Cost,
    a.labour_factor,
    a.User_ID,      RTRIM(u.Short_User_Id)      AS Short_User_Id,      RTRIM(u.User_Name)       AS User_Name,
    a.Skill_Id,     RTRIM(sk.Short_Skill_Id)    AS Short_Skill_Id,     RTRIM(sk.Skill_Title)    AS Skill_Title,
    a.Asset_Id,     RTRIM(ast.Short_asset_Id)   AS Short_asset_Id,     RTRIM(ast.Asset_Title)   AS Asset_Title,
    a.Part_Id,      RTRIM(p.Short_Part_ID)      AS Short_Part_ID,      RTRIM(p.Part_Title)      AS Part_Title,
    a.Warehouse_ID, RTRIM(w.Short_Warehouse_ID) AS Short_Warehouse_ID, RTRIM(w.Warehouse_Title) AS Warehouse_Title,
    a.Supplier_ID,  RTRIM(s.Short_Supplier_Id)  AS Short_Supplier_Id,  RTRIM(s.Company_Name)    AS Company_Name,
    a.Work_code_Id, RTRIM(wc.Short_Work_Code_Id) AS Short_Work_Code_Id, RTRIM(wc.Work_Code_Title) AS Work_Code_Title,
    a.UOM_Id,       RTRIM(uom.Short_UOM_Id)     AS Short_UOM_Id,       RTRIM(uom.UOM_Title)     AS UOM_Title,
    a.UOM_Factor_ID, uomf.Factor                AS Factor,             RTRIM(uomf.UOM_Factor_Title) AS UOM_Factor_Title,
    (CASE WHEN uomf.Factor = -1.0
          THEN ABS(a.Quantity * a.Unit_Cost * ISNULL(uomf.Factor,1)) * (-1)
          ELSE      (a.Quantity * a.Unit_Cost * ISNULL(uomf.Factor,1)) END)     AS Total,
    CAST((CASE LEN(ISNULL(c.Comments,'')) WHEN 0 THEN 0 ELSE 1 END) AS bit) AS Has_Comment,
    c.Comments                              AS Comments
FROM            WO_N_Activity                  a
LEFT OUTER JOIN Users                          u    ON a.User_ID       = u.User_Id
LEFT OUTER JOIN Skill                          sk   ON a.Skill_Id      = sk.Skill_ID
LEFT OUTER JOIN Asset                          ast  ON a.Asset_Id      = ast.Asset_ID
LEFT OUTER JOIN Parts                          p    ON a.Part_Id       = p.Part_ID
LEFT OUTER JOIN Warehouse                      w    ON a.Warehouse_ID  = w.Warehouse_ID
LEFT OUTER JOIN Supplier                       s    ON a.Supplier_ID   = s.Supplier_ID
LEFT OUTER JOIN Work_Code                      wc   ON a.Work_code_Id  = wc.Work_Code_Id
LEFT OUTER JOIN Unit_of_Measure                uom  ON a.UOM_Id        = uom.UOM_Id
LEFT OUTER JOIN Unit_of_Measure_Factor         uomf ON a.UOM_Factor_ID = uomf.UOM_Factor_ID
LEFT OUTER JOIN WO_N_Activity_Comments         c    ON a.WO_Activity_ID = c.WO_Activity_ID
                                                   AND a.WO_ID          = c.WO_Id
WHERE a.WO_ID = :woId

UNION ALL

-- ---- Branch B : PO received, not yet invoiced  ->  'O' ---------------------
SELECT
    CAST(NULL AS numeric)                   AS WO_Activity_ID,
    wh.WO_ID,
    'O'                                     AS Trx_Type,
    prd.Received_date                       AS Activity_Date,
    CAST(NULL AS datetime)                  AS Entry_Date,
    prd.Recd_Quantity                       AS Quantity,
    prd.Unit_Cost,
    CAST(NULL AS numeric)                   AS labour_factor,
    CAST(NULL AS numeric) AS User_ID, CAST(NULL AS varchar(20)) AS Short_User_Id, CAST(NULL AS varchar(40)) AS User_Name,
    CAST(NULL AS numeric) AS Skill_Id, CAST(NULL AS varchar(20)) AS Short_Skill_Id, CAST(NULL AS varchar(35)) AS Skill_Title,
    ast.Asset_ID  AS Asset_Id, RTRIM(ast.Short_asset_Id) AS Short_asset_Id, RTRIM(ast.Asset_Title) AS Asset_Title,
    prd.Part_id   AS Part_Id, RTRIM(p.Short_Part_ID) AS Short_Part_ID, RTRIM(p.Part_Title) AS Part_Title,
    pd.Warehouse_ID, RTRIM(w.Short_Warehouse_ID) AS Short_Warehouse_ID, RTRIM(w.Warehouse_Title) AS Warehouse_Title,
    ph.Supplier_Id AS Supplier_ID, RTRIM(s.Short_Supplier_Id) AS Short_Supplier_Id, RTRIM(s.Company_Name) AS Company_Name,
    pd.WorkCode_ID AS Work_code_Id, RTRIM(wc.Short_Work_Code_Id) AS Short_Work_Code_Id, RTRIM(wc.Work_Code_Title) AS Work_Code_Title,
    pd.UOM_ID AS UOM_Id, RTRIM(uom.Short_UOM_Id) AS Short_UOM_Id, RTRIM(uom.UOM_Title) AS UOM_Title,
    pd.UOM_Factor_ID, uomf.Factor AS Factor, RTRIM(uomf.UOM_Factor_Title) AS UOM_Factor_Title,
    (CASE WHEN uomf.Factor = -1.0
          THEN ABS(prd.Recd_Quantity * prd.Unit_Cost * ISNULL(uomf.Factor,1)) * (-1)
          ELSE      (prd.Recd_Quantity * prd.Unit_Cost * ISNULL(uomf.Factor,1)) END) AS Total,
    CAST(0 AS bit)                          AS Has_Comment,
    CAST(NULL AS varchar(5000))             AS Comments
FROM            PO_Header              ph
INNER JOIN      PO_Details             pd   ON ph.PO_Id        = pd.PO_ID
INNER JOIN      PO_Receipt_Detail      prd  ON pd.PO_ID        = prd.PO_ID
                                           AND pd.PO_Detail_ID  = prd.PO_Detail_ID
INNER JOIN      WO_N_Header            wh   ON wh.WO_ID        = pd.WO_Id
LEFT OUTER JOIN Asset                  ast  ON wh.Asset_Id     = ast.Asset_ID
INNER JOIN      Parts                  p    ON p.Part_ID       = prd.Part_id
INNER JOIN      Warehouse              w    ON pd.Warehouse_ID = w.Warehouse_ID
LEFT OUTER JOIN Supplier               s    ON s.Supplier_ID   = ph.Supplier_Id
LEFT OUTER JOIN Unit_of_Measure        uom  ON uom.UOM_Id      = pd.UOM_ID
LEFT OUTER JOIN Unit_of_Measure_Factor uomf ON uomf.UOM_Factor_ID = pd.UOM_Factor_ID
LEFT OUTER JOIN Work_Code              wc   ON wc.Work_Code_Id = pd.WorkCode_ID
WHERE wh.WO_ID = :woId
  AND ph.Status IN ('T','R')
  AND (prd.IS_Invoiced <> '1' OR prd.IS_Invoiced IS NULL)

UNION ALL

-- ---- Branch C : PO ordered, not yet received  ->  'O' ----------------------
SELECT
    CAST(NULL AS numeric)                   AS WO_Activity_ID,
    wh.WO_ID,
    'O'                                     AS Trx_Type,
    pd.Due_Date                             AS Activity_Date,
    CAST(NULL AS datetime)                  AS Entry_Date,
    (pd.Quantity - pd.Qty_Received)         AS Quantity,
    pd.Unit_Cost,
    CAST(NULL AS numeric)                   AS labour_factor,
    CAST(NULL AS numeric) AS User_ID, CAST(NULL AS varchar(20)) AS Short_User_Id, CAST(NULL AS varchar(40)) AS User_Name,
    CAST(NULL AS numeric) AS Skill_Id, CAST(NULL AS varchar(20)) AS Short_Skill_Id, CAST(NULL AS varchar(35)) AS Skill_Title,
    ast.Asset_ID  AS Asset_Id, RTRIM(ast.Short_asset_Id) AS Short_asset_Id, RTRIM(ast.Asset_Title) AS Asset_Title,
    pd.Part_ID    AS Part_Id, RTRIM(p.Short_Part_ID) AS Short_Part_ID, RTRIM(p.Part_Title) AS Part_Title,
    pd.Warehouse_ID, RTRIM(w.Short_Warehouse_ID) AS Short_Warehouse_ID, RTRIM(w.Warehouse_Title) AS Warehouse_Title,
    ph.Supplier_Id AS Supplier_ID, RTRIM(s.Short_Supplier_Id) AS Short_Supplier_Id, RTRIM(s.Company_Name) AS Company_Name,
    pd.WorkCode_ID AS Work_code_Id, RTRIM(wc.Short_Work_Code_Id) AS Short_Work_Code_Id, RTRIM(wc.Work_Code_Title) AS Work_Code_Title,
    pd.UOM_ID AS UOM_Id, RTRIM(uom.Short_UOM_Id) AS Short_UOM_Id, RTRIM(uom.UOM_Title) AS UOM_Title,
    pd.UOM_Factor_ID, uomf.Factor AS Factor, RTRIM(uomf.UOM_Factor_Title) AS UOM_Factor_Title,
    (CASE WHEN uomf.Factor = -1.0
          THEN ABS((pd.Quantity - pd.Qty_Received) * pd.Unit_Cost * ISNULL(uomf.Factor,1)) * (-1)
          ELSE      ((pd.Quantity - pd.Qty_Received) * pd.Unit_Cost * ISNULL(uomf.Factor,1)) END) AS Total,
    CAST(0 AS bit)                          AS Has_Comment,
    CAST(NULL AS varchar(5000))             AS Comments
FROM            PO_Header              ph
INNER JOIN      PO_Details             pd   ON ph.PO_Id        = pd.PO_ID
INNER JOIN      WO_N_Header            wh   ON wh.WO_ID        = pd.WO_Id
LEFT OUTER JOIN Asset                  ast  ON wh.Asset_Id     = ast.Asset_ID
INNER JOIN      Parts                  p    ON p.Part_ID       = pd.Part_ID
INNER JOIN      Warehouse              w    ON pd.Warehouse_ID = w.Warehouse_ID
LEFT OUTER JOIN Supplier               s    ON s.Supplier_ID   = ph.Supplier_Id
LEFT OUTER JOIN Unit_of_Measure        uom  ON uom.UOM_Id      = pd.UOM_ID
LEFT OUTER JOIN Unit_of_Measure_Factor uomf ON uomf.UOM_Factor_ID = pd.UOM_Factor_ID
LEFT OUTER JOIN Work_Code              wc   ON wc.Work_Code_Id = pd.WorkCode_ID
WHERE wh.WO_ID = :woId
  AND ph.Status <> 'D'
  AND (pd.Quantity - pd.Qty_Received) > 0

ORDER BY Activity_Date DESC, WO_Activity_ID DESC;
```

## `Workmate/Workorder Activity/PartHolding` — 882 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder Activity/PartHolding
-- Type:       Select Query   Database: TLSQL01_Workmate   Author: Adriaan   v1.0
-- Parameters: partId (Integer / sqlType 3)
-- ==============================================================================
-- Live Part_Holding row for one part (single row, 1:1). Used by savePart to
-- re-read current QOH inside the transaction before the decrement.
-- ==============================================================================

SELECT TOP 1
    ph.Part_ID                          AS partId,
    ph.Warehouse_ID                     AS warehouseId,
    ISNULL(ph.Quantity_On_Hand, 0)      AS qoh,
    ISNULL(ph.Quantity_On_Order, 0)     AS qoo,
    ISNULL(ph.Issue_Cost, 0)            AS issueCost
FROM dbo.Part_Holding ph
WHERE ph.Part_ID = :partId;
```

## `Workmate/Workorder Activity/PartList` — 2002 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder Activity/PartList
-- File:        Workmate_Workorder_Activity_PartList_v1_1_0.sql
-- Version:     1.1.0
-- Type:        Select Query
-- Database:    TLSQL01_Workmate
-- Author:      Adriaan
--
-- Parts stocked somewhere (have a Part_Holding row), joined to their single
-- home warehouse. Confirmed 1:1 (776 parts / 776 holdings / none in >1 wh).
-- Selecting a part in the popup auto-fills warehouseId/QOH/issueCost from THIS
-- row. Non-stock parts (Non_stock_Item='1') included but flagged.
--
-- Changelog:
--   v1.1.0  + manfPart (Manufacture_Part_No) so the ActivityPart popup can
--           build searchable labels that include the manufacturer part number
--           (Ken request - manf search worked in PO but not the WO popup).
--   v1.0    Initial.
--
-- Parameters:
--   None
-- Returns:
--   partId, partShort, partTitle, manfPart, nonStock, warehouseId,
--   warehouseShort, warehouseTitle, qoh, issueCost, lastCost - Part_Title A-Z
-- ==============================================================================

SELECT
    p.Part_ID                                 AS partId,
    RTRIM(p.Short_Part_ID)                    AS partShort,
    RTRIM(p.Part_Title)                       AS partTitle,
    RTRIM(ISNULL(p.Manufacture_Part_No, ''))  AS manfPart,
    RTRIM(ISNULL(p.Non_stock_Item,'0'))       AS nonStock,
    ph.Warehouse_ID                           AS warehouseId,
    RTRIM(w.Short_Warehouse_ID)               AS warehouseShort,
    RTRIM(w.Warehouse_Title)                  AS warehouseTitle,
    ISNULL(ph.Quantity_On_Hand, 0)            AS qoh,
    ISNULL(ph.Issue_Cost, 0)                  AS issueCost,
    ISNULL(ph.Last_Cost, 0)                   AS lastCost
FROM dbo.Part_Holding ph
INNER JOIN dbo.Parts p     ON ph.Part_ID = p.Part_ID
INNER JOIN dbo.Warehouse w ON ph.Warehouse_ID = w.Warehouse_ID
WHERE ISNULL(p.Status, 'Y') <> 'N'
ORDER BY p.Part_Title;
```

## `Workmate/Workorder Activity/ResolveUserId` — 1185 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder Activity/ResolveUserId
-- Type:       Select Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Version:    1.0
-- Parameters: gatewayUser (String / sqlType 7)
-- ==============================================================================
-- Resolves the logged-in Ignition Gateway username to a Workmate User_Id, for
-- writing @User_ID_Created_By on activity rows. Matches AD_Login_ID, the column
-- intended to hold the login identity.
--
-- MAPPING NOTE: AD_Login_ID must equal the Gateway username. Today some rows
-- hold initials (e.g. 'AP') while the Gateway login is 'Adriaan' - a one-time
-- backfill aligns them (see the dry-run backfill script). If no match is found,
-- the popup falls back to SYS_USER (User_Id 1) so a save never blocks.
--
-- Returns 0 or 1 row.
-- ==============================================================================

SELECT TOP 1
    User_Id                             AS userId,
    RTRIM(User_Name)                    AS userName
FROM dbo.Users
WHERE RTRIM(AD_Login_ID) = :gatewayUser
  AND ISNULL(Active, '1') <> '0';
```

## `Workmate/Workorder Activity/Search` — 253 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- Workmate/Workorder Activity/Search
-- Query Type: Select Query
-- Parameters: whereCondition (String), orderByExpression (String)
EXEC wmsp_WO_N_ActivitySelectDynamic
    @WhereCondition = :whereCondition,
    @OrderByExpression = :orderByExpression;
```

## `Workmate/Workorder Activity/UserSkillList` — 2609 B — modified 2026-09-01T21:47:44Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder Activity/UserSkillList
-- File:       Workmate_NQ_Workorder_Activity_UserSkillList_v1_1.sql
-- Type:       Select Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Version:    1.1
-- ==============================================================================
-- Person + skill + rate source for the Labour popup pickers.
--
-- Changelog (newest first)
--   v1.1  2026-09-02  EXT.1. Two changes:
--         (1) ACTIVE-DOMAIN FIX - Users.Active at KPP is 'N'/'Y', but v1.0
--             only excluded '0'. Every deactivated user (all 46 'X ...'
--             rows, Active='N') therefore leaked into the Worker dropdown
--             when their User_Skill line was still Active='1'. Filter now
--             excludes '0' AND 'N'.
--         (2) EXTERNAL SUFFIX - shadow users for external contractors
--             (Short_User_Id 'EXT-' prefix, created by EXT.2) render as
--             "Name (external)" for easy recognition. Harmless before
--             EXT.2 lands - no EXT- rows exist yet.
--   v1.0  Initial (mirrors .NET WMActivityGrid line-1397 query).
--
-- One row per User_Skill line. Popup builds User dropdown from distinct
-- users, Skill dropdown filtered to the chosen user.
-- Parameters:  none
-- Returns:     userId, userName, userShort, skillId, skillShort, skillTitle,
--              supplierId, uomId, uomShort, rate
-- ==============================================================================

SELECT
    us.User_ID                          AS userId,
    CASE WHEN RTRIM(u.Short_User_Id) LIKE 'EXT-%'
         THEN RTRIM(u.User_Name) + ' (external)'
         ELSE RTRIM(u.User_Name) END    AS userName,
    RTRIM(u.Short_User_Id)              AS userShort,
    us.Skill_ID                         AS skillId,
    RTRIM(sk.Short_Skill_Id)            AS skillShort,
    RTRIM(sk.Skill_Title)               AS skillTitle,
    us.Supplier_ID                      AS supplierId,
    us.UOM_ID                           AS uomId,
    RTRIM(uom.Short_UOM_Id)             AS uomShort,
    ISNULL(us.Rate, 0)                  AS rate
FROM dbo.User_Skill us
INNER JOIN dbo.Users u  ON us.User_ID  = u.User_Id
INNER JOIN dbo.Skill sk ON us.Skill_ID = sk.Skill_ID
LEFT OUTER JOIN dbo.Supplier sp        ON us.Supplier_ID = sp.Supplier_ID
LEFT OUTER JOIN dbo.Unit_of_Measure uom ON us.UOM_ID     = uom.UOM_Id
WHERE us.Active = '1'
  AND RTRIM(ISNULL(u.Active, '1')) NOT IN ('0', 'N')
  AND RTRIM(u.Short_User_Id) <> 'SYS_USER'
ORDER BY u.User_Name, sk.Short_Skill_Id;
```

## `Workmate/Workorder Activity/WOContext` — 868 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder Activity/WOContext
-- Type:       Select Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Version:    1.0
-- Parameters: woId (Integer / sqlType 3)
-- ==============================================================================
-- WO header context the Labour popup needs but the user never types:
-- Location_ID, Asset_Id (may be null), and a friendly label for the header.
-- ==============================================================================

SELECT TOP 1
    h.WO_ID                             AS woId,
    h.Location_ID                       AS locationId,
    h.Asset_Id                          AS assetId,
    RTRIM(h.Short_WO_Id) + ' - ' + RTRIM(ISNULL(h.WO_Title,'')) AS woLabel
FROM dbo.WO_N_Header h
WHERE h.WO_ID = :woId;
```

## `Workmate/Workorder Activity/WorkCodeList` — 853 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder Activity/WorkCodeList
-- Type:       Select Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Version:    1.0
-- ==============================================================================
-- Work Code dropdown for the Labour popup (optional field). The .NET default
-- labour Work_code_Id is 40; the popup pre-selects it when present.
-- Work_Code has no reliable Active flag in this schema, so all are returned.
-- ==============================================================================

SELECT
    Work_Code_Id                        AS value,
    RTRIM(Short_Work_Code_Id)           AS short,
    RTRIM(Work_Code_Title)              AS label
FROM dbo.Work_Code
WHERE ISNULL(Active, '1') = '1'
ORDER BY Short_Work_Code_Id;
```

## `Workmate/Workorder Resource/Delete` — 178 B — modified 2026-05-15T07:53:58Z by Adriaan

```sql
-- Workmate/Workorder Resource/Delete
-- Query Type: Update Query
-- Parameters: resId (Int8), woId (Int8)
EXEC wmsp_WO_N_ResourceDelete
    @Res_Id = :resId,
    @WO_Id = :woId;
```

## `Workmate/Workorder Resource/DeleteDynamic` — 187 B — modified 2026-05-15T07:53:58Z by Adriaan

```sql
-- Workmate/Workorder Resource/DeleteDynamic
-- Query Type: Update Query
-- Parameters: whereCondition (String)
EXEC wmsp_WO_N_ResourceDeleteDynamic
    @WhereCondition = :whereCondition;
```

## `Workmate/Workorder Resource/Dropdown` — 181 B — modified 2026-05-15T07:53:58Z by Adriaan

```sql
-- Workmate/Workorder Resource/Dropdown
-- Query Type: Select Query
-- Parameters: None
SELECT
    Res_Id AS value,
    Server_Name AS label
FROM WO_N_Resource
ORDER BY Server_Name;
```

## `Workmate/Workorder Resource/Get` — 444 B — modified 2026-05-15T07:53:58Z by Adriaan

```sql
-- Workmate/Workorder Resource/Get
-- Query Type: Select Query
-- Parameters: None
SELECT
    Account_Id,
    Labour_Facter,
    Part_Id,
    Planned_Qty,
    Planned_Unit_Cost,
    PM_WO_ID,
    Res_Date,
    Res_Id,
    Resource_Note,
    Resource_Type,
    Server_Name,
    Skill_Id,
    Supplier_Id,
    Sys_Res_Id,
    Task_ID,
    UOM_Factor_ID,
    UOM_Id,
    User_Id,
    WO_Id,
    WorkCode_Id
FROM WO_N_Resource
ORDER BY Server_Name;
```

## `Workmate/Workorder Resource/InsertUpdate` — 971 B — modified 2026-05-15T07:53:58Z by Adriaan

```sql
-- Workmate/Workorder Resource/InsertUpdate
-- Query Type: Update Query
-- Parameters: resId (Int8), woId (Int8), resourceType (String), userId (Int8), skillId (Int8), partId (Int8), uomId (Int8), supplierId (Int8), resourceNote (String), plannedUnitCost (Int8), plannedQty (Int8), labourFacter (Int8), accountId (Int8), workcodeId (Int8), uomFactorId (Int8), resDate (DateTime), pmWoId (Int8), taskId (String)
EXEC wmsp_WO_N_ResourceInsertUpdate
    @Res_Id = :resId,
    @WO_Id = :woId,
    @Resource_Type = :resourceType,
    @User_Id = :userId,
    @Skill_Id = :skillId,
    @Part_Id = :partId,
    @UOM_Id = :uomId,
    @Supplier_Id = :supplierId,
    @Resource_Note = :resourceNote,
    @Planned_Unit_Cost = :plannedUnitCost,
    @Planned_Qty = :plannedQty,
    @Labour_Facter = :labourFacter,
    @Account_Id = :accountId,
    @WorkCode_Id = :workcodeId,
    @UOM_Factor_ID = :uomFactorId,
    @Res_Date = :resDate,
    @PM_WO_ID = :pmWoId,
    @Task_ID = :taskId;
```

## `Workmate/Workorder Resource/Item` — 454 B — modified 2026-05-15T07:53:58Z by Adriaan

```sql
-- Workmate/Workorder Resource/Item
-- Query Type: Select Query
-- Parameters: resId (Int8)
SELECT
    Account_Id,
    Labour_Facter,
    Part_Id,
    Planned_Qty,
    Planned_Unit_Cost,
    PM_WO_ID,
    Res_Date,
    Res_Id,
    Resource_Note,
    Resource_Type,
    Server_Name,
    Skill_Id,
    Supplier_Id,
    Sys_Res_Id,
    Task_ID,
    UOM_Factor_ID,
    UOM_Id,
    User_Id,
    WO_Id,
    WorkCode_Id
FROM WO_N_Resource
WHERE Res_Id = :resId;
```

## `Workmate/Workorder Resource/Search` — 253 B — modified 2026-05-15T07:53:58Z by Adriaan

```sql
-- Workmate/Workorder Resource/Search
-- Query Type: Select Query
-- Parameters: whereCondition (String), orderByExpression (String)
EXEC wmsp_WO_N_ResourceSelectDynamic
    @WhereCondition = :whereCondition,
    @OrderByExpression = :orderByExpression;
```

## `Workmate/Workorder Resource/SearchAll` — 323 B — modified 2026-05-15T07:53:58Z by Adriaan

```sql
-- Workmate/Workorder Resource/SearchAll
-- Query Type: Select Query
-- Parameters: selectedFields (String), whereCondition (String), orderByExpression (String)
EXEC wmsp_WO_N_ResourceSelectDynamicAll
    @SelectedFields = :selectedFields,
    @WhereCondition = :whereCondition,
    @OrderByExpression = :orderByExpression;
```

## `Workmate/WO Query/Search` — 238 B — modified 2026-05-15T07:53:56Z by Adriaan

```sql
-- Workmate/WO Query/Search
-- Query Type: Select Query
-- Parameters: whereCondition (String), orderByExpression (String)
EXEC wmsp_WO_QuerySelectDynamic
    @WhereCondition = :whereCondition,
    @OrderByExpression = :orderByExpression;
```

## `Workmate/WO Responsible User/InsertUpdate` — 240 B — modified 2026-05-15T07:53:56Z by Adriaan

```sql
-- Workmate/WO Responsible User/InsertUpdate
-- Query Type: Update Query
-- Parameters: woId (Int8), userId (Int8), select (String)
EXEC wmsp_WO_Responsible_UserInsertUpdate
    @WO_ID = :woId,
    @User_ID = :userId,
    @Select = :select;
```

## `Workmate/WO Responsible User/List` — 1533 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/WO Responsible User/List
-- Type:       Select Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Dialect:    portable
-- Version:    1.0
-- ==============================================================================
-- Lists the responsible users linked to a WO via WO_Responsible_User, resolved
-- to names. By default returns only ACTIVE links ([Select]='Y'); pass
-- includeRemoved=1 to also return soft-removed rows ([Select]<>'Y').
-- Companion to the upsert proc Workmate/WO Responsible User/InsertUpdate
-- (which soft-toggles [Select]).
-- ------------------------------------------------------------------------------
-- Parameters:
--   woId           Int8  required  -- WO_N_Header.WO_ID
--   includeRemoved Int4  required  -- 0 = active only ([Select]='Y'); 1 = all
-- Returns:
--   System_WO_Resp_ID, User_ID, Short_User_Id, User_Name, Sel, Server_Name
-- ==============================================================================

SELECT
    r.System_WO_Resp_ID,
    r.User_ID,
    RTRIM(COALESCE(u.Short_User_Id, '')) AS Short_User_Id,
    RTRIM(COALESCE(u.User_Name, ''))     AS User_Name,
    RTRIM(COALESCE(r.[Select], ''))      AS Sel,
    RTRIM(COALESCE(r.Server_Name, ''))   AS Server_Name
FROM dbo.WO_Responsible_User r
LEFT JOIN dbo.Users u ON r.User_ID = u.User_Id
WHERE r.WO_ID = :woId
  AND (COALESCE(:includeRemoved, 0) = 1 OR RTRIM(COALESCE(r.[Select], '')) = 'Y')
ORDER BY u.Short_User_Id;
```

## `Workmate/WO Responsible User/Picker` — 1741 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/WO Responsible User/Picker
-- Type:       Select Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Dialect:    portable
-- Version:    1.0
-- ==============================================================================
-- Drives the UserSelector popup: every selectable user, each flagged with
-- whether they are CURRENTLY an active responsible user on this WO
-- (Linked=1 when WO_Responsible_User.[Select]='Y' for this WO_ID).
-- Active users only by default (Users.Active='Y'); pass includeInactive=1 for all.
-- ------------------------------------------------------------------------------
-- Parameters:
--   woId            Int8   required  -- WO_N_Header.WO_ID
--   includeInactive Int4   required  -- 0 = Active users only; 1 = all
--   search          String required  -- '' = no filter; matches Short_User_Id/User_Name
-- Returns:
--   User_Id, Short_User_Id, User_Name, Area, Linked (1/0)
-- ==============================================================================

SELECT
    u.User_Id,
    RTRIM(COALESCE(u.Short_User_Id, '')) AS Short_User_Id,
    RTRIM(COALESCE(u.User_Name, ''))     AS User_Name,
    RTRIM(COALESCE(u.Area, ''))          AS Area,
    CASE WHEN r.WO_ID IS NOT NULL THEN 1 ELSE 0 END AS Linked
FROM dbo.Users u
LEFT JOIN dbo.WO_Responsible_User r
       ON r.User_ID = u.User_Id
      AND r.WO_ID = :woId
      AND RTRIM(COALESCE(r.[Select], '')) = 'Y'
WHERE (COALESCE(:includeInactive, 0) = 1 OR RTRIM(COALESCE(u.Active, '')) = 'Y')
  AND (COALESCE(:search, '') = ''
       OR u.Short_User_Id LIKE '%' + :search + '%'
       OR u.User_Name LIKE '%' + :search + '%')
ORDER BY u.Short_User_Id;
```
