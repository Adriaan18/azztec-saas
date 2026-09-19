"""
Azztec_SaaS_app_workorders_sql_v1_0_0.py  ->  backend/app/workorders/sql.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_W1a_WOMaint_Read_Api_Chunk_Spec_v1_0_0.md §3.1 · OD-63, OD-64, OD-65, OD-66, OD-67
Parent:   Azztec_SaaS_Data_Layer_and_RST_DB_v1_0_0.md §4-§5, Architecture D-3
Ported from: the Ignition named queries (docs/reference/WO_Named_Queries_2026-09-16.md and the
             2026-09-19 addendum) Workmate/Workorder/Search v12, Workorder/Item, Workorder Detail/Item,
             WO Responsible User/List, Workorder/ResourceCompare v1.1.1, Workorder/LinkedFamily v1.0.0,
             Workorder/Event/Search 1.1, wmsp_WO_QuerySelectDynamic (its body, read on RST 2026-09-19),
             Workorder/GetPODetails, Progress/Get; the label joins from the thirteen */Dropdown reads.
Pair:     backend/app/workorders/repo.py 1.0.0

Every statement the WOMaint READ path runs, as dialect-portable text() source. No Python logic beyond
assembling the three search variants - repo.py binds the params and maps the rows.

The five habits (Data Layer §5) applied on the way in:
  the MSSQL null-default function -> COALESCE                    every null default
  string joining with +           -> CONCAT                       the LIKE pattern, the resource label
  row-limiting by TOP             -> OFFSET / FETCH NEXT           the list and the event page
  ? positional params             -> :q, :closed, :wo_type, :offset, :take, :wo_id named binds
  dbo. prefix                     -> on every table
The CI dialect gate greps this WHOLE FILE, so the four banned tokens are described, never spelled.

NO COLONS IN SQL COMMENTS. SQLAlchemy text() reads :name inside a comment as a bind parameter
(Landmines §B). There are no comments inside the statements at all - the notes are Python comments,
outside the strings.

Departures from the oracle, each recorded in the spec:
  - Search v12's in-SQL includeArchive tests fold into the CHOICE of statement (live / archive / both):
    each arm is plannable on its own and the rows are the same. The archive arm has no closed predicate,
    exactly as the NQ (trap 3).
  - ORDER BY Entry_date DESC gains the WO_ID DESC tie-break the NQ lacks (Landmines §B), and paging.
  - Item's INNER JOIN on WO_N_Details becomes LEFT JOIN (OD-65) and carries the label joins (OD-66).
  - ResourceCompare's tick nonce and LinkedFamily's Badge column are not ported - the nonce has no API
    meaning, and the badge composite is rules.badge() for every row that carries one (one function,
    tested once).
  - Progress/Get orders by title; PROGRESS_ALL orders by id (OD-67 - the picture row is id-ordered).

Changelog:
  1.0.0  Initial W1a.
"""

from __future__ import annotations

__version__ = "1.0.0"


# ---------------------------------------------------------------------------
# name:    workorders.search  (three variants)
# dialect: portable
# params:  q (str, '' = no term), closed (0 open only / 1 all / 2 closed+cancelled only - live arm only),
#          wo_type ('' all / N / CP / M), offset, take (limit + 1, repo.py reads the extra row as `more`)
# order:   Entry_date DESC, WO_ID DESC
# ---------------------------------------------------------------------------

_SEARCH_COLS = """
SELECT {t}.WO_ID,
       RTRIM(COALESCE({t}.Short_WO_Id, '')) AS Short_WO_Id,
       RTRIM(COALESCE({t}.WO_Title, '')) AS WO_Title,
       RTRIM(COALESCE(a.Short_asset_Id, '')) AS Asset_ID,
       RTRIM(COALESCE(l.Short_Location_ID, '')) AS Location_Id,
       RTRIM(COALESCE({t}.Status, '')) AS Status,
       COALESCE(d.Progress_Id, 0) AS Progress_Id,
       CASE WHEN EXISTS (SELECT 1 FROM dbo.PO_Header ph WHERE ph.WO_Id = {t}.WO_ID)
              OR EXISTS (SELECT 1 FROM dbo.PO_Details pd WHERE pd.WO_Id = {t}.WO_ID)
            THEN 1 ELSE 0 END AS HasPO,
       {t}.Entry_date
"""

_SEARCH_TERM = """
  AND (:q = ''
       OR {t}.Short_WO_Id LIKE CONCAT('%', :q, '%')
       OR {t}.WO_Title LIKE CONCAT('%', :q, '%'))
"""

_SEARCH_TYPE = """
  AND (:wo_type = ''
       OR (:wo_type = 'N' AND {t}.WO_Type_Flag = 'N'
           AND COALESCE(l.Short_Location_ID, '') NOT LIKE 'CP-%'
           AND RTRIM(COALESCE(l.Short_Location_ID, '')) <> 'CP')
       OR (:wo_type = 'CP' AND {t}.WO_Type_Flag = 'N'
           AND (COALESCE(l.Short_Location_ID, '') LIKE 'CP-%'
                OR RTRIM(COALESCE(l.Short_Location_ID, '')) = 'CP'))
       OR (:wo_type = 'M' AND {t}.WO_Type_Flag = 'M'))
"""

_LIVE_ARM = (
    _SEARCH_COLS.format(t="h")
    + """
FROM dbo.WO_N_Header h
LEFT JOIN dbo.Asset a ON h.Asset_ID = a.Asset_ID
LEFT JOIN dbo.Location l ON h.Location_Id = l.Location_Id
LEFT JOIN dbo.WO_N_Details d ON h.WO_ID = d.WO_ID
WHERE 1 = 1
"""
    + _SEARCH_TERM.format(t="h")
    + """
  AND (:closed = 1
       OR (:closed = 0 AND h.Status NOT IN ('C', 'D'))
       OR (:closed = 2 AND h.Status IN ('C', 'D')))
"""
    + _SEARCH_TYPE.format(t="h")
)

_ARCHIVE_ARM = (
    _SEARCH_COLS.format(t="c")
    + """
FROM dbo.WO_C_header c
LEFT JOIN dbo.Asset a ON c.Asset_ID = a.Asset_ID
LEFT JOIN dbo.Location l ON c.Location_Id = l.Location_Id
LEFT JOIN dbo.WO_C_Details d ON c.WO_ID = d.WO_ID
WHERE 1 = 1
"""
    + _SEARCH_TERM.format(t="c")
    + _SEARCH_TYPE.format(t="c")
)

_SEARCH_WRAP_HEAD = """
SELECT s.WO_ID, s.Short_WO_Id, s.WO_Title, s.Asset_ID, s.Location_Id, s.Status, s.Progress_Id,
       s.HasPO, s.Entry_date
FROM (
"""

_SEARCH_WRAP_TAIL = """
) s
ORDER BY s.Entry_date DESC, s.WO_ID DESC
OFFSET :offset ROWS FETCH NEXT :take ROWS ONLY
"""

SEARCH_LIVE = _SEARCH_WRAP_HEAD + _LIVE_ARM + _SEARCH_WRAP_TAIL
SEARCH_ARCHIVE = _SEARCH_WRAP_HEAD + _ARCHIVE_ARM + _SEARCH_WRAP_TAIL
SEARCH_BOTH = _SEARCH_WRAP_HEAD + _LIVE_ARM + "\nUNION ALL\n" + _ARCHIVE_ARM + _SEARCH_WRAP_TAIL


# ---------------------------------------------------------------------------
# name:    workorders.item
# dialect: portable
# params:  wo_id
# note:    Item + Workorder Detail/Item in one row, LEFT JOIN on the details (OD-65 - D_WO_ID is NULL
#          for the seven RST headers without one), every reference id resolved to its title regardless
#          of the reference row's Active flag (OD-66). Table and column names are the */Dropdown reads'.
# ---------------------------------------------------------------------------

WO_ITEM = """
SELECT h.WO_ID,
       d.WO_ID AS D_WO_ID,
       RTRIM(COALESCE(h.Short_WO_Id, '')) AS Short_WO_Id,
       RTRIM(COALESCE(h.WO_Title, '')) AS WO_Title,
       RTRIM(COALESCE(h.Status, '')) AS Status,
       RTRIM(COALESCE(h.WO_Type_Flag, 'N')) AS WO_Type_Flag,
       RTRIM(COALESCE(h.OverDue, '')) AS OverDue,
       h.Week_No,
       h.Request_Start_Date,
       h.Request_End_Date,
       h.Entry_date,
       h.Company_ID,
       RTRIM(COALESCE(co.Company_Title, '')) AS Company_Title,
       h.Asset_ID,
       RTRIM(COALESCE(a.Short_asset_Id, '')) AS Short_asset_Id,
       RTRIM(COALESCE(a.Asset_Title, '')) AS Asset_Title,
       h.Location_Id,
       RTRIM(COALESCE(l.Short_Location_ID, '')) AS Short_Location_ID,
       RTRIM(COALESCE(l.Location_Title, '')) AS Location_Title,
       COALESCE(h.Parent_Location_Hierarchy, '') AS Parent_Location_Hierarchy,
       d.Duration_In_Hours,
       d.Est_Cost,
       d.Down_Time,
       d.Priority_Id,
       RTRIM(COALESCE(pr.Short_Priority_Id, '')) AS Short_Priority_Id,
       RTRIM(COALESCE(pr.Priority_Title, '')) AS Priority_Title,
       d.WO_Group_Id,
       RTRIM(COALESCE(wg.Short_WO_Group_ID, '')) AS Short_WO_Group_ID,
       RTRIM(COALESCE(wg.WO_Group_Title, '')) AS WO_Group_Title,
       d.Reason_Id,
       RTRIM(COALESCE(rs.Reason_Title, '')) AS Reason_Title,
       d.Fault_Id,
       RTRIM(COALESCE(fa.Fault_Title, '')) AS Fault_Title,
       d.Cost_Center_Id,
       RTRIM(COALESCE(cc.Cost_Center_Title, '')) AS Cost_Center_Title,
       d.Account_Id,
       RTRIM(COALESCE(ac.Account_Title, '')) AS Account_Title,
       d.Supplier_ID_charge_To,
       RTRIM(COALESCE(sc.Short_Supplier_Id, '')) AS ChargeTo_Short,
       RTRIM(COALESCE(sc.Company_Name, '')) AS ChargeTo_Name,
       d.Supplier_ID_Responsibility,
       RTRIM(COALESCE(sr.Short_Supplier_Id, '')) AS RespSupplier_Short,
       RTRIM(COALESCE(sr.Company_Name, '')) AS RespSupplier_Name,
       d.WOC1_ID,
       RTRIM(COALESCE(w1.WOC1_Title, '')) AS WOC1_Title,
       d.WOC2_ID,
       RTRIM(COALESCE(w2.WOC2_Title, '')) AS WOC2_Title,
       d.WOC3_ID,
       RTRIM(COALESCE(w3.WOC3_Title, '')) AS WOC3_Title,
       RTRIM(COALESCE(d.Entered_By, '')) AS Entered_By,
       RTRIM(COALESCE(d.Reference, '')) AS Reference,
       d.Progress_Id,
       RTRIM(COALESCE(pg.Progress_Title, '')) AS Progress_Title,
       d.Notes,
       d.User_ID_Requested_By,
       d.User_ID_Responsibility,
       RTRIM(COALESCE(ur.User_Name, '')) AS Resp_User_Name,
       d.Condition_Id,
       RTRIM(COALESCE(d.Generated_From, '')) AS Generated_From,
       RTRIM(COALESCE(d.Intrusive, '')) AS Intrusive,
       RTRIM(COALESCE(d.Intrusive_Complete, '')) AS Intrusive_Complete,
       d.IntrusiveComplete_Date,
       d.first_activity_date,
       d.last_activity_date,
       d.Meter_ID,
       d.Meter_Reading,
       RTRIM(COALESCE(d.Printed, '')) AS Printed,
       d.Progress_Date,
       RTRIM(COALESCE(uc.Short_User_Id, '')) AS Created_By_Name,
       RTRIM(COALESCE(ua.Short_User_Id, '')) AS Ack_By_Name,
       d.Acknowledgement_date,
       RTRIM(COALESCE(uap.Short_User_Id, '')) AS Approved_By_Name,
       d.Approved_Date,
       RTRIM(COALESCE(ucl.Short_User_Id, '')) AS Closed_By_Name,
       d.Closed_Date,
       RTRIM(COALESCE(uca.Short_User_Id, '')) AS Cancelled_By_Name,
       d.Cancelled_Date,
       RTRIM(COALESCE(uls.Short_User_Id, '')) AS Last_Save_Name,
       d.Last_Save_Date
FROM dbo.WO_N_Header h
LEFT JOIN dbo.WO_N_Details d ON d.WO_ID = h.WO_ID
LEFT JOIN dbo.Asset a ON a.Asset_ID = h.Asset_ID
LEFT JOIN dbo.Location l ON l.Location_Id = h.Location_Id
LEFT JOIN dbo.Company co ON co.Company_Id = h.Company_ID
LEFT JOIN dbo.Priority pr ON pr.Priority_Id = d.Priority_Id
LEFT JOIN dbo.WorkOrder_Group wg ON wg.WO_Group_ID = d.WO_Group_Id
LEFT JOIN dbo.Reason rs ON rs.Reason_ID = d.Reason_Id
LEFT JOIN dbo.Fault fa ON fa.Fault_Id = d.Fault_Id
LEFT JOIN dbo.Cost_Center cc ON cc.Cost_Center_ID = d.Cost_Center_Id
LEFT JOIN dbo.Account ac ON ac.Account_ID = d.Account_Id
LEFT JOIN dbo.Supplier sc ON sc.Supplier_ID = d.Supplier_ID_charge_To
LEFT JOIN dbo.Supplier sr ON sr.Supplier_ID = d.Supplier_ID_Responsibility
LEFT JOIN dbo.WOC1 w1 ON w1.WOC1_ID = d.WOC1_ID
LEFT JOIN dbo.WOC2 w2 ON w2.WOC2_ID = d.WOC2_ID
LEFT JOIN dbo.WOC3 w3 ON w3.WOC3_ID = d.WOC3_ID
LEFT JOIN dbo.Progress pg ON pg.Progress_Id = d.Progress_Id
LEFT JOIN dbo.Users ur ON ur.User_Id = d.User_ID_Responsibility
LEFT JOIN dbo.Users uc ON uc.User_Id = h.User_Id_Created_By
LEFT JOIN dbo.Users ua ON ua.User_Id = d.User_Id_Ack_by
LEFT JOIN dbo.Users uap ON uap.User_Id = d.User_Id_Approved_By
LEFT JOIN dbo.Users ucl ON ucl.User_Id = d.User_ID_ClosedBy
LEFT JOIN dbo.Users uca ON uca.User_Id = d.User_ID_CancelledBy
LEFT JOIN dbo.Users uls ON uls.User_Id = d.User_id_Last_Save
WHERE h.WO_ID = :wo_id
"""


# ---------------------------------------------------------------------------
# name:    workorders.live_exists / workorders.archived_exists
# dialect: portable
# params:  wo_id
# note:    the record's 404 code (OD-68) and the tab routes' guard
# ---------------------------------------------------------------------------

LIVE_EXISTS = """
SELECT COUNT(*) AS n FROM dbo.WO_N_Header WHERE WO_ID = :wo_id
"""

ARCHIVED_EXISTS = """
SELECT COUNT(*) AS n FROM dbo.WO_C_header WHERE WO_ID = :wo_id
"""


# ---------------------------------------------------------------------------
# name:    workorders.resp_users
# dialect: portable
# params:  wo_id
# note:    WO Responsible User/List with includeRemoved = 0 baked in. Select is a reserved word on both
#          engines and is double-quoted (trap 1).
# ---------------------------------------------------------------------------

RESP_USERS = """
SELECT r.System_WO_Resp_ID,
       r.User_ID,
       RTRIM(COALESCE(u.Short_User_Id, '')) AS Short_User_Id,
       RTRIM(COALESCE(u.User_Name, '')) AS User_Name
FROM dbo.WO_Responsible_User r
LEFT JOIN dbo.Users u ON r.User_ID = u.User_Id
WHERE r.WO_ID = :wo_id
  AND RTRIM(COALESCE(r."Select", '')) = 'Y'
ORDER BY u.Short_User_Id
"""


# ---------------------------------------------------------------------------
# name:    workorders.resource_compare
# dialect: portable
# params:  wo_id
# note:    ResourceCompare v1.1.1 minus the tick nonce. Keys (D-RC-1) Parts -> Part_Id, Labour ->
#          User_Id, Service actuals have no planned counterpart; actual = committed L/P/S activity
#          (D-RC-2); actual-only rows carry ' (unplanned)' (D-RC-3); planned-only rows show NULL actuals.
# ---------------------------------------------------------------------------

RESOURCE_COMPARE = """
SELECT
    CASE k.KeyType WHEN 'P' THEN 'Part'
                   WHEN 'L' THEN 'Labour'
                   WHEN 'S' THEN 'Service'
                   ELSE k.KeyType END AS Type,
    CONCAT(
        CASE k.KeyType
            WHEN 'P' THEN CONCAT(RTRIM(COALESCE(p.Short_Part_ID, '')), ' - ',
                                 RTRIM(COALESCE(p.Part_Title, '')))
            WHEN 'L' THEN RTRIM(COALESCE(u.User_Name, ''))
            WHEN 'S' THEN RTRIM(COALESCE(s.Company_Name, 'Service'))
            ELSE ''
        END,
        CASE WHEN pa.PlanQty IS NULL THEN ' (unplanned)' ELSE '' END) AS Item,
    pa.PlanQty AS PlanQty,
    pa.PlanCost AS PlanCost,
    aa.ActQty AS ActQty,
    aa.ActCost AS ActCost,
    COALESCE(aa.ActCost, 0) - COALESCE(pa.PlanCost, 0) AS Delta
FROM (
    SELECT COALESCE(pa2.KeyType, aa2.KeyType) AS KeyType,
           COALESCE(pa2.KeyId, aa2.KeyId) AS KeyId
    FROM (
        SELECT CASE RTRIM(COALESCE(Resource_Type, '')) WHEN 'P' THEN 'P' ELSE 'L' END AS KeyType,
               CASE RTRIM(COALESCE(Resource_Type, '')) WHEN 'P' THEN COALESCE(Part_Id, -1)
                    ELSE COALESCE(User_Id, -1) END AS KeyId
        FROM dbo.WO_N_Resource WHERE WO_Id = :wo_id
        GROUP BY CASE RTRIM(COALESCE(Resource_Type, '')) WHEN 'P' THEN 'P' ELSE 'L' END,
                 CASE RTRIM(COALESCE(Resource_Type, '')) WHEN 'P' THEN COALESCE(Part_Id, -1)
                      ELSE COALESCE(User_Id, -1) END
    ) pa2
    FULL OUTER JOIN (
        SELECT RTRIM(COALESCE(Trx_Type, '')) AS KeyType,
               CASE RTRIM(COALESCE(Trx_Type, ''))
                    WHEN 'P' THEN COALESCE(Part_Id, -1)
                    WHEN 'L' THEN COALESCE(User_ID, -1)
                    ELSE COALESCE(Supplier_ID, -1) END AS KeyId
        FROM dbo.WO_N_Activity
        WHERE WO_ID = :wo_id AND RTRIM(COALESCE(Trx_Type, '')) IN ('L', 'P', 'S')
        GROUP BY RTRIM(COALESCE(Trx_Type, '')),
                 CASE RTRIM(COALESCE(Trx_Type, ''))
                      WHEN 'P' THEN COALESCE(Part_Id, -1)
                      WHEN 'L' THEN COALESCE(User_ID, -1)
                      ELSE COALESCE(Supplier_ID, -1) END
    ) aa2 ON aa2.KeyType = pa2.KeyType AND aa2.KeyId = pa2.KeyId
) k
LEFT JOIN (
    SELECT CASE RTRIM(COALESCE(Resource_Type, '')) WHEN 'P' THEN 'P' ELSE 'L' END AS KeyType,
           CASE RTRIM(COALESCE(Resource_Type, '')) WHEN 'P' THEN COALESCE(Part_Id, -1)
                ELSE COALESCE(User_Id, -1) END AS KeyId,
           SUM(COALESCE(Planned_Qty, 0)) AS PlanQty,
           SUM(COALESCE(Planned_Qty, 0) * COALESCE(Planned_Unit_Cost, 0)) AS PlanCost
    FROM dbo.WO_N_Resource WHERE WO_Id = :wo_id
    GROUP BY CASE RTRIM(COALESCE(Resource_Type, '')) WHEN 'P' THEN 'P' ELSE 'L' END,
             CASE RTRIM(COALESCE(Resource_Type, '')) WHEN 'P' THEN COALESCE(Part_Id, -1)
                  ELSE COALESCE(User_Id, -1) END
) pa ON pa.KeyType = k.KeyType AND pa.KeyId = k.KeyId
LEFT JOIN (
    SELECT RTRIM(COALESCE(Trx_Type, '')) AS KeyType,
           CASE RTRIM(COALESCE(Trx_Type, ''))
                WHEN 'P' THEN COALESCE(Part_Id, -1)
                WHEN 'L' THEN COALESCE(User_ID, -1)
                ELSE COALESCE(Supplier_ID, -1) END AS KeyId,
           SUM(COALESCE(Quantity, 0)) AS ActQty,
           SUM(COALESCE(Quantity, 0) * COALESCE(Unit_Cost, 0)) AS ActCost
    FROM dbo.WO_N_Activity
    WHERE WO_ID = :wo_id AND RTRIM(COALESCE(Trx_Type, '')) IN ('L', 'P', 'S')
    GROUP BY RTRIM(COALESCE(Trx_Type, '')),
             CASE RTRIM(COALESCE(Trx_Type, ''))
                  WHEN 'P' THEN COALESCE(Part_Id, -1)
                  WHEN 'L' THEN COALESCE(User_ID, -1)
                  ELSE COALESCE(Supplier_ID, -1) END
) aa ON aa.KeyType = k.KeyType AND aa.KeyId = k.KeyId
LEFT JOIN dbo.Parts p ON k.KeyType = 'P' AND p.Part_ID = k.KeyId
LEFT JOIN dbo.Users u ON k.KeyType = 'L' AND u.User_Id = k.KeyId
LEFT JOIN dbo.Supplier s ON k.KeyType = 'S' AND s.Supplier_ID = k.KeyId
ORDER BY
    CASE k.KeyType WHEN 'P' THEN 1 WHEN 'L' THEN 2 ELSE 3 END,
    CASE WHEN pa.PlanQty IS NULL THEN 1 ELSE 0 END,
    Item
"""


# ---------------------------------------------------------------------------
# name:    workorders.linked_family
# dialect: portable
# params:  wo_id
# note:    LinkedFamily v1.0.0 - up to the root (two hops), then the whole family, parent first.
#          Open table only - the archive is out of scope, as in the .NET tab. Badge is rules.badge().
# ---------------------------------------------------------------------------

LINKED_FAMILY = """
WITH me AS (
    SELECT h.WO_ID, COALESCE(h.Linked_to_WO, 0) AS Up1
    FROM dbo.WO_N_Header h
    WHERE h.WO_ID = :wo_id
),
up1 AS (
    SELECT CASE WHEN me.Up1 > 0 THEN me.Up1 ELSE me.WO_ID END AS WO_ID
    FROM me
),
rootq AS (
    SELECT CASE WHEN COALESCE(h.Linked_to_WO, 0) > 0 THEN h.Linked_to_WO ELSE h.WO_ID END AS RootId
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
    RTRIM(COALESCE(h.Short_WO_Id, '')) AS Short_WO_Id,
    RTRIM(COALESCE(h.WO_Title, '')) AS WO_Title,
    RTRIM(COALESCE(h.Status, '')) AS Status,
    COALESCE(d.Progress_Id, 0) AS Progress_Id,
    CASE WHEN EXISTS (SELECT 1 FROM dbo.PO_Header ph WHERE ph.WO_Id = h.WO_ID)
           OR EXISTS (SELECT 1 FROM dbo.PO_Details pd WHERE pd.WO_Id = h.WO_ID)
         THEN 1 ELSE 0 END AS HasPO,
    f.Lvl AS Level,
    COALESCE(h.Linked_to_WO, 0) AS ParentId,
    RTRIM(COALESCE(p.Short_WO_Id, '')) AS ParentShortId,
    h.Request_Start_Date,
    h.Entry_date,
    CASE WHEN h.WO_ID = :wo_id THEN 1 ELSE 0 END AS IsSelected
FROM fam f
INNER JOIN dbo.WO_N_Header h ON h.WO_ID = f.WO_ID
LEFT JOIN dbo.WO_N_Details d ON d.WO_ID = h.WO_ID
LEFT JOIN dbo.WO_N_Header p ON p.WO_ID = h.Linked_to_WO
ORDER BY f.Lvl, h.Short_WO_Id
"""


# ---------------------------------------------------------------------------
# name:    workorders.events
# dialect: portable
# params:  wo_id, offset, take
# order:   Edited_Date DESC, Sys_WO_Event_Id DESC  (the NQ ordered by Edited_Date alone)
# note:    Event/Search 1.1 - the site resolved through the WO's Company_ID, no schema change.
# ---------------------------------------------------------------------------

EVENTS = """
SELECT
    e.Sys_WO_Event_Id,
    e.WO_ID,
    e.User_Id_Edited_By,
    RTRIM(COALESCE(u.User_Name, u.Short_User_Id, CAST(e.User_Id_Edited_By AS varchar(20)))) AS Editor_Name,
    RTRIM(COALESCE(co.Short_Company_Id, '')) AS Site_Code,
    RTRIM(COALESCE(co.Company_Title, '')) AS Site_Name,
    e.Edited_Date,
    RTRIM(COALESCE(e.Event_Name, '')) AS Event_Name,
    e.event_details,
    RTRIM(COALESCE(e.server_name, '')) AS server_name,
    RTRIM(COALESCE(e.Source_Form, '')) AS Source_Form
FROM dbo.WO_Event_History e
LEFT JOIN dbo.Users u ON e.User_Id_Edited_By = u.User_Id
LEFT JOIN dbo.WO_N_Header h ON e.WO_ID = h.WO_ID
LEFT JOIN dbo.Company co ON h.Company_ID = co.Company_Id
WHERE e.WO_ID = :wo_id
ORDER BY e.Edited_Date DESC, e.Sys_WO_Event_Id DESC
OFFSET :offset ROWS FETCH NEXT :take ROWS ONLY
"""


# ---------------------------------------------------------------------------
# name:    workorders.queries
# dialect: portable
# params:  wo_id
# note:    wmsp_WO_QuerySelectDynamic's nine columns with the view's WHERE and ORDER BY made static.
#          Query_Desc is selected raw - its type was not read (a text column rejects COALESCE).
# ---------------------------------------------------------------------------

QUERIES = """
SELECT WO_Id,
       Query_ID,
       RTRIM(COALESCE(Query_Type, '')) AS Query_Type,
       RTRIM(COALESCE(Query_From, '')) AS Query_From,
       Query_Date,
       RTRIM(COALESCE(Query_To, '')) AS Query_To,
       Query_Desc,
       Pair_Id,
       Email_Sent
FROM dbo.WO_Query
WHERE WO_Id = :wo_id
ORDER BY Query_Date DESC, Query_ID DESC
"""


# ---------------------------------------------------------------------------
# name:    workorders.po_lines
# dialect: portable
# params:  wo_id
# note:    GetPODetails - the WO link is on PO_Details.WO_Id, not PO_Header.
# ---------------------------------------------------------------------------

PO_LINES = """
SELECT RTRIM(COALESCE(h.Status, '')) AS Status,
       RTRIM(COALESCE(h.Short_PO_Id, '')) AS Short_PO_Id,
       d.Due_Date,
       RTRIM(COALESCE(s.Company_Name, '')) AS Company_Name,
       d.PO_Description,
       d.Quantity,
       d.Unit_Cost
FROM dbo.PO_Details d
INNER JOIN dbo.PO_Header h ON d.PO_ID = h.PO_Id
LEFT JOIN dbo.Supplier s ON h.Supplier_Id = s.Supplier_ID
WHERE d.WO_Id = :wo_id
ORDER BY h.Short_PO_Id, d.PO_Detail_ID
"""


# ---------------------------------------------------------------------------
# name:    workorders.progress_all
# dialect: portable
# params:  none
# order:   Progress_Id  (OD-67 - the picture row is id-ordered; Progress/Get ordered by title)
# ---------------------------------------------------------------------------

PROGRESS_ALL = """
SELECT Progress_Id,
       RTRIM(COALESCE(Progress_Title, '')) AS Progress_Title,
       RTRIM(COALESCE(Short_Progress_Id, '')) AS Short_Progress_Id
FROM dbo.Progress
WHERE COALESCE(Active, '1') = '1'
ORDER BY Progress_Id
"""


ALL_STATEMENTS = {
    "search_live": SEARCH_LIVE,
    "search_archive": SEARCH_ARCHIVE,
    "search_both": SEARCH_BOTH,
    "wo_item": WO_ITEM,
    "live_exists": LIVE_EXISTS,
    "archived_exists": ARCHIVED_EXISTS,
    "resp_users": RESP_USERS,
    "resource_compare": RESOURCE_COMPARE,
    "linked_family": LINKED_FAMILY,
    "events": EVENTS,
    "queries": QUERIES,
    "po_lines": PO_LINES,
    "progress_all": PROGRESS_ALL,
}
