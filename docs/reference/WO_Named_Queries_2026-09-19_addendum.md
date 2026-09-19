# Workmate WO named queries - reference bundle addendum (2026-09-19 export)

**File:** WO_Named_Queries_2026-09-19_addendum.md · **Author:** Adriaan (the queries) · assembled by script from the 2026-09-19 Designer resource exports (`Workorder_NQ.zip`, `Workorder_Hub_NQ.zip`) · `ignition/named-query/Workmate/{Workorder/Event, Workorder/Priority, Workorder/Template, Workorder Hub}`

Adds the eight queries the 2026-09-16 bundle (`WO_Named_Queries_2026-09-16.md`, 52 queries) did not carry. The 48 queries both exports share were compared byte-for-byte on 2026-09-19: none changed, so the 09-16 bundle stands and this file only adds. Each block is the `query.sql` byte-for-byte; the `resource.json` line gives the last modification. Reference input for the WOMaint audits (W1 reads `Event/Search` and `Priority/Dropdown`) — never a build source (the SaaS port writes its own `sql.py`, dialect-portable, D-3).

## `Workmate/Workorder/Event/Insert` — 1834 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder/Event/Insert
-- Type:       Update Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Dialect:    portable
-- Version:    1.0
-- ==============================================================================
-- Changelog (newest first):
--   1.0  New. Writes one row to the existing WO_Event_History table -- the
--        same table the .NET app maintains via clsWOeventHistory. Column set
--        and order match the .NET INSERT verbatim (WO_ID, User_Id_Edited_By,
--        Edited_Date, Event_Name, event_details, server_name, Source_Form)
--        so a Perspective-written row is indistinguishable from a .NET one
--        except for provenance (server_name='Perspective', Source_Form set
--        by the caller, e.g. 'WOMaint' or 'AI'). Used by
--        workmate.workorder._logEvent and _logFieldDiffs. Per WO-3 spec v1.2.
-- ==============================================================================
-- Parameters:
--   woId          Int8      required  -- WO_N_Header.WO_ID
--   userId        Int8      required  -- acting user (User_Id_Edited_By)
--   eventName     String    required  -- 'Create' | 'Update' | 'Note' | 'DELETE'
--   eventDetails  String    required  -- human-readable detail text
--   serverName    String    nullable  -- 'Perspective' (provenance)
--   sourceForm    String    required  -- 'WOMaint' | 'AI' | etc.
-- Returns:
--   (nothing -- update query)
-- ==============================================================================

INSERT INTO dbo.WO_Event_History
    (WO_ID, User_Id_Edited_By, Edited_Date, Event_Name,
     event_details, server_name, Source_Form)
VALUES
    (:woId, :userId, CURRENT_TIMESTAMP, :eventName,
     :eventDetails, :serverName, :sourceForm);
```

## `Workmate/Workorder/Event/Search` — 2151 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder/Event/Search
-- Type:       Select Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Dialect:    portable
-- Version:    1.1
-- ==============================================================================
-- Changelog (newest first):
--   1.1  Multi-site: added Site_Code (Short_Company_Id) and Site_Name
--        (Company_Title), derived at read time from the WO's
--        WO_N_Header.Company_ID -> Company. No schema change to
--        WO_Event_History -- the site is resolved through the WO the event
--        belongs to. Enables the audit timeline to show "{editor} · {site}",
--        the multi-tenant story (KPP / MLD / Sanford ...). Per WO-3 spec v1.3.
--   1.0  New. Reads the persisted audit timeline from WO_Event_History for
--        one WO, newest first, editor User_Id resolved to a name via Users.
-- ==============================================================================
-- Parameters:
--   woId       Int8  required  -- WO_N_Header.WO_ID
--   offsetRows Int8  required  -- paging offset (0 for first page)
--   pageSize   Int8  required  -- rows per page (e.g. 100)
-- Returns:
--   Audit rows newest-first. Columns:
--     WO_ID, User_Id_Edited_By, Editor_Name, Site_Code, Site_Name,
--     Edited_Date, Event_Name, event_details, server_name, Source_Form
-- ==============================================================================

SELECT
    e.WO_ID,
    e.User_Id_Edited_By,
    RTRIM(COALESCE(u.User_Name, u.Short_User_Id, CAST(e.User_Id_Edited_By AS VARCHAR(20)))) AS Editor_Name,
    RTRIM(COALESCE(co.Short_Company_Id, '')) AS Site_Code,
    RTRIM(COALESCE(co.Company_Title, '')) AS Site_Name,
    e.Edited_Date,
    e.Event_Name,
    e.event_details,
    e.server_name,
    e.Source_Form
FROM dbo.WO_Event_History e
LEFT JOIN dbo.Users u ON e.User_Id_Edited_By = u.User_Id
LEFT JOIN dbo.WO_N_Header h ON e.WO_ID = h.WO_ID
LEFT JOIN dbo.Company co ON h.Company_ID = co.Company_Id
WHERE e.WO_ID = :woId
ORDER BY e.Edited_Date DESC
OFFSET :offsetRows ROWS FETCH NEXT :pageSize ROWS ONLY;
```

## `Workmate/Workorder/Priority/Dropdown` — 1223 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder/Priority/Dropdown
-- File:       Workmate_Workorder_Priority_Dropdown_query_v1_0.sql
-- Type:       Select Query
-- Database:   TLSQL01_Workmate   (set to the PRODUCTION connection on the new NQ)
-- Author:     Adriaan
-- Dialect:    portable
-- Version:    1.0
-- ==============================================================================
-- Changelog (newest first):
--   1.0  New. WO Priority reference codes shaped as value/label for the
--        Create-WO (WO-4) Priority dropdown. Reference-table active = Active='1'
--        (per the Workmate reference-table convention). Ordered by the
--        configured Sort_Sequence then title.
-- ==============================================================================
-- Parameters:
--   (none)
-- Returns:
--   value (Priority_Id), label (Priority_Title)   -- active priorities, sorted
-- ==============================================================================

SELECT
    Priority_Id                        AS value,
    RTRIM(ISNULL(Priority_Title, ''))  AS label
FROM dbo.Priority
WHERE Active = '1'
ORDER BY Sort_Sequence ASC, Priority_Title ASC;
```

## `Workmate/Workorder/Template/Get` — 2295 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder/Template/Get
-- Type:       Select Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Dialect:    portable
-- Version:    1.0
-- ==============================================================================
-- Changelog (newest first):
--   1.0  New. Returns one template's default field values from WO_T_Details,
--        for the Create-WO flow to pre-fill the new WO. Includes the Copy_*
--        flags so the wrapper can honour the legacy conditional-copy rules.
--        Per WO-4 spec v1.2.
-- ==============================================================================
-- Parameters:
--   templateId  Int8  required  -- WO_T_Header.WO_ID / WO_T_Details.WO_ID
-- Returns:
--   The template's defaults + Copy_* flags. The wrapper applies:
--     - always    WO_Group_Id, Priority_Id, Reason_Id, Fault_Id, Intrusive,
--                  Supplier_ID_Requested_By, Supplier_ID_charge_To, WOC1/2/3
--     - if Copy_Supplier_Resp = 'Y': Supplier_ID_Responsibility
--     - if Copy_Account = 'Y':       Account_Id, Cost_Center_Id  (usually 'N')
--     - if Copy_Tilte   = 'Y':       WO_Title from template       (usually 'N')
--   (Account/Title default to 'N' across all current templates, so by default
--    the WO takes account from asset/location and the user types the title.)
-- ==============================================================================

SELECT
    d.WO_ID                       AS Template_ID,
    d.WO_Group_Id,
    d.Priority_Id,
    d.Reason_Id,
    d.Fault_Id,
    d.Cost_Center_Id,
    d.Account_Id,
    d.Intrusive,
    d.Duration_In_Hours,
    d.Down_Time,
    d.Notes,
    d.Reference,
    d.Supplier_ID_Requested_By,
    d.User_ID_Requested_By,
    d.Supplier_ID_charge_To,
    d.Supplier_ID_Responsibility,
    d.User_ID_Responsibility,
    d.WOC1_ID,
    d.WOC2_ID,
    d.WOC3_ID,
    RTRIM(ISNULL(d.Copy_Account, 'N'))        AS Copy_Account,
    RTRIM(ISNULL(d.Copy_Supplier_Resp, 'N'))  AS Copy_Supplier_Resp,
    RTRIM(ISNULL(d.Copy_Tilte, 'N'))          AS Copy_Title,
    RTRIM(h.WO_Title)                         AS Template_Title
FROM dbo.WO_T_Details d
JOIN dbo.WO_T_Header h ON d.WO_ID = h.WO_ID
WHERE d.WO_ID = :templateId;
```

## `Workmate/Workorder/Template/List` — 1509 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- ==============================================================================
-- Workmate/Workorder/Template/List
-- Type:       Select Query
-- Database:   TLSQL01_Workmate
-- Author:     Adriaan
-- Dialect:    portable
-- Version:    1.1
-- ==============================================================================
-- Changelog (newest first):
--   1.1  Avoid referencing the company param twice in one WHERE (Ignition
--        binds each colon-prefixed token as a separate positional slot).
--        Site + global templates selected via UNION ALL: the site branch
--        binds companyId once, the global branch uses no param.
--   1.0  New. Lists WO templates for the Create-WO picker.
-- ==============================================================================
-- Parameters:
--   companyId  Int8  required  -- site (Company_ID; KPP = 1)
-- Returns:
--   WO_ID, Short_WO_Id, WO_Title, Status, Company_ID
--   (site templates for the company PLUS global templates where Company_ID IS NULL)
-- ==============================================================================

SELECT
    WO_ID,
    RTRIM(Short_WO_Id) AS Short_WO_Id,
    RTRIM(WO_Title)    AS WO_Title,
    RTRIM(Status)      AS Status,
    Company_ID
FROM dbo.WO_T_Header
WHERE Company_ID = :companyId
UNION ALL
SELECT
    WO_ID,
    RTRIM(Short_WO_Id) AS Short_WO_Id,
    RTRIM(WO_Title)    AS WO_Title,
    RTRIM(Status)      AS Status,
    Company_ID
FROM dbo.WO_T_Header
WHERE Company_ID IS NULL
ORDER BY WO_Title ASC;
```

## `Workmate/Workorder Hub/AreaList` — 1516 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
-- ==============================================================================
-- Version: 1.1
-- Changelog (newest first):
--   1.1  PM SEPARATION: added WO_Type_Flag='N' so PMs no longer appear in this
--        WO list/metric (PM Audit v1.0.0). Prior history untracked (no header).
-- ==============================================================================
-- =============================================================================
-- Workmate_WorkorderHub_AreaList_v1_0_0.sql
-- NQ Designer path:  Workmate/Workorder Hub/AreaList
-- -----------------------------------------------------------------------------
-- Slice 3 of the Work Order Hub feature. Distinct areas (locations) that have
-- open work orders, with a per-area open count -- drives the board's area
-- filter chips and the live counts.
--
-- Open = Status NOT IN ('C','D').
-- No params.
--
-- Returns: Location_Id, Area, Open_Count   (areas with most open WOs first)
--
-- NOTE: set Database = TLSQL01_Workmate after import (Perspective Rules sec 6).
-- Author: Adriaan
-- =============================================================================
SELECT
    h.Location_Id,
    RTRIM(ISNULL(h.Parent_Location_Hierarchy, '')) AS Area,
    COUNT(*)                                       AS Open_Count
FROM dbo.WO_N_Header h
WHERE RTRIM(ISNULL(h.Status, '')) NOT IN ('C', 'D')
  AND h.WO_Type_Flag = 'N'
  AND h.Location_Id IS NOT NULL
GROUP BY h.Location_Id, RTRIM(ISNULL(h.Parent_Location_Hierarchy, ''))
ORDER BY COUNT(*) DESC
```

## `Workmate/Workorder Hub/LiveWOList` — 3371 B — modified 2026-08-29T20:21:52Z by Adriaan

```sql
-- ==============================================================================
-- Version: 1.1
-- Changelog (newest first):
--   1.1  PM SEPARATION: added WO_Type_Flag='N' so PMs no longer appear in this
--        WO list/metric (PM Audit v1.0.0). Prior history untracked (no header).
-- ==============================================================================
-- =============================================================================
-- Workmate_WorkorderHub_LiveWOList_v1_0_0.sql
-- NQ Designer path:  Workmate/Workorder Hub/LiveWOList
-- -----------------------------------------------------------------------------
-- Slice 3 of the Work Order Hub feature. The board's main list: all OPEN work
-- orders with the display fields the touch board needs (area, asset, age,
-- assignee, status). Open = Status NOT IN ('C','D') -- the same rule the
-- existing workmate.workorder.getOpen() / Workmate/Workorder/GetOpen uses
-- (_VALID_STATUS: R Request, H Planned, P Pending, K Acknowledged, A Approved,
--  V Active, C Closed, D Cancelled, F Finished).
--
-- Params:
--   locationId  Int   0 = all areas, else filter to a Location_Id
--
-- Returns (capped 200 rows, oldest-open first so stale WOs surface):
--   WO_ID, Short_WO_Id, WO_Title, Status, Status_Label,
--   Asset_ID, Asset_Number, Asset_Title,
--   Location_Id, Area,                       -- Parent_Location_Hierarchy
--   Request_Start_Date, Age_Days,
--   Assignee, Has_PO
--
-- NOTE: set Database = TLSQL01_Workmate after import (Perspective Rules sec 6).
-- Scale: TOP 200, filtered at the DB (never client-side).
-- Author: Adriaan
-- =============================================================================
SELECT TOP 200
    h.WO_ID,
    RTRIM(ISNULL(h.Short_WO_Id, ''))               AS Short_WO_Id,
    RTRIM(ISNULL(h.WO_Title, ''))                  AS WO_Title,
    RTRIM(ISNULL(h.Status, ''))                    AS Status,
    CASE RTRIM(ISNULL(h.Status, ''))
        WHEN 'R' THEN 'Request'
        WHEN 'H' THEN 'Planned'
        WHEN 'P' THEN 'Pending'
        WHEN 'K' THEN 'Acknowledged'
        WHEN 'A' THEN 'Approved'
        WHEN 'V' THEN 'Active'
        WHEN 'F' THEN 'Finished'
        ELSE RTRIM(ISNULL(h.Status, ''))
    END                                            AS Status_Label,
    h.Asset_ID,
    RTRIM(ISNULL(a.Asset_Number, ''))              AS Asset_Number,
    RTRIM(ISNULL(a.Asset_Title, ''))               AS Asset_Title,
    h.Location_Id,
    RTRIM(ISNULL(h.Parent_Location_Hierarchy, '')) AS Area,
    h.Request_Start_Date,
    DATEDIFF(DAY, h.Request_Start_Date, GETDATE()) AS Age_Days,
    RTRIM(ISNULL(ru.Assignee, ''))                 AS Assignee,
    CASE WHEN ISNULL(h.Purchase_Order_Flag, '0') = '1'
         THEN 1 ELSE 0 END                         AS Has_PO
FROM dbo.WO_N_Header h
LEFT JOIN dbo.Asset a
    ON a.Asset_ID = h.Asset_ID
OUTER APPLY (
    -- first responsible user flagged Select='1' for this WO (the assignee)
    SELECT TOP 1 RTRIM(ISNULL(u.User_Name, '')) AS Assignee
    FROM dbo.WO_Responsible_User r
    JOIN dbo.Users u ON u.User_Id = r.User_ID
    WHERE r.WO_ID = h.WO_ID
      AND RTRIM(ISNULL(r.[Select], '')) = '1'
    ORDER BY u.User_Name
) ru
WHERE RTRIM(ISNULL(h.Status, '')) NOT IN ('C', 'D')
  AND h.WO_Type_Flag = 'N'
  AND (:locationId = 0 OR h.Location_Id = :locationId)
ORDER BY h.Request_Start_Date ASC
```

## `Workmate/Workorder Hub/WOByUser` — 2595 B — modified 2026-08-29T20:21:51Z by Adriaan

```sql
-- ==============================================================================
-- Version: 1.1
-- Changelog (newest first):
--   1.1  PM SEPARATION: added WO_Type_Flag='N' so PMs no longer appear in this
--        WO list/metric (PM Audit v1.0.0). Prior history untracked (no header).
-- ==============================================================================
-- =============================================================================
-- Workmate_WorkorderHub_WOByUser_v1_0_0.sql
-- NQ Designer path:  Workmate/Workorder Hub/WOByUser
-- -----------------------------------------------------------------------------
-- Slice 3 of the Work Order Hub feature. Open work orders a given KT-crew user
-- is responsible for -- drives the Completion flow's "your work orders" list
-- (Slice 7) after the user picks their name.
--
-- Open = Status NOT IN ('C','D') (same rule as LiveWOList / getOpen).
--
-- Params:
--   userId  Int   Users.User_Id of the selected crew member
--
-- Returns (capped 200, oldest-open first):
--   WO_ID, Short_WO_Id, WO_Title, Status, Status_Label,
--   Asset_Number, Asset_Title, Area, Request_Start_Date, Age_Days
--
-- NOTE: set Database = TLSQL01_Workmate after import (Perspective Rules sec 6).
-- Author: Adriaan
-- =============================================================================
SELECT TOP 200
    h.WO_ID,
    RTRIM(ISNULL(h.Short_WO_Id, ''))               AS Short_WO_Id,
    RTRIM(ISNULL(h.WO_Title, ''))                  AS WO_Title,
    RTRIM(ISNULL(h.Status, ''))                    AS Status,
    CASE RTRIM(ISNULL(h.Status, ''))
        WHEN 'R' THEN 'Request'
        WHEN 'H' THEN 'Planned'
        WHEN 'P' THEN 'Pending'
        WHEN 'K' THEN 'Acknowledged'
        WHEN 'A' THEN 'Approved'
        WHEN 'V' THEN 'Active'
        WHEN 'F' THEN 'Finished'
        ELSE RTRIM(ISNULL(h.Status, ''))
    END                                            AS Status_Label,
    RTRIM(ISNULL(a.Asset_Number, ''))              AS Asset_Number,
    RTRIM(ISNULL(a.Asset_Title, ''))               AS Asset_Title,
    RTRIM(ISNULL(h.Parent_Location_Hierarchy, '')) AS Area,
    h.Request_Start_Date,
    DATEDIFF(DAY, h.Request_Start_Date, GETDATE()) AS Age_Days
FROM dbo.WO_N_Header h
LEFT JOIN dbo.Asset a
    ON a.Asset_ID = h.Asset_ID
WHERE RTRIM(ISNULL(h.Status, '')) NOT IN ('C', 'D')
  AND h.WO_Type_Flag = 'N'
  AND EXISTS (
        SELECT 1 FROM dbo.WO_Responsible_User r
        WHERE r.WO_ID = h.WO_ID
          AND r.User_ID = :userId
          AND RTRIM(ISNULL(r.[Select], '')) = '1'
      )
ORDER BY h.Request_Start_Date ASC
```
