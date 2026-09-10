"""
workmate_planner_sql_v1_0_1.py  ->  backend/app/planner/sql.py
Version:  1.0.1
Author:   Adriaan
Spec:     Azztec_SaaS_S1b_Data_Chunk_Spec_v1_0_0.md §3
Parent:   Azztec_SaaS_Data_Layer_and_RST_DB_v1_0_0.md §4-§5, Architecture D-3
Ported from: workmate.planner 1.3.1 lines 539-629 (_woSql, _LABOUR_SQL, _WORKER_SQL,
             _PRIORITY_SQL, hoursUomId probes)
Pair:     backend/app/planner/repo.py 1.0.0

Every statement the planner READ path runs, as dialect-portable text() source.
No Python logic here beyond assembling the two pin variants - repo.py binds
the params and maps the rows.

The five habits (Data Layer §5) applied on the way in:
  the MSSQL null-default function -> COALESCE                    ~40 sites
  row-limiting by TOP             -> OFFSET / FETCH NEXT           5 sites
  ? positional params             -> :from_d / :to_d named binds
  the MSSQL current-time function -> not used in the read path at all
  dbo. prefix                     -> already present throughout
FETCH NEXT is valid on both engines (PostgreSQL treats NEXT and FIRST as
synonyms), so none of the rewritten row limits needs a PG-CONVERT tag.

The CI dialect gate (Data Layer §5) greps this WHOLE FILE, not just the
statements - a banned token in a comment fails it exactly as a banned token
in SQL does. That is why the four are described above rather than spelled
out. 1.0.0 shipped with them spelled out and tripped the gate on its own
documentation; the statements were clean. Keep them unspelled.

NO COLONS IN SQL COMMENTS. SQLAlchemy text() reads :name inside a comment as
a bind parameter (Landmines §B) - the Ignition COLON-IN-COMMENT landmine
survives the port. Header comments below are Python comments, outside the
strings, so they are safe.

Changelog:
  1.0.1  Docstring reworded so the CI dialect gate stops matching this
         module's own documentation. No SQL change - every statement is
         byte-identical to 1.0.0. Caught by the gate on first run.
  1.0.0  Initial. OD-11 signed 2026-09-11 - UOM_MODAL gains the UOM_Id
         tie-break the source lacked.
"""

from __future__ import annotations

__version__ = "1.0.1"


# ---------------------------------------------------------------------------
# name:    planner.wo_range
# dialect: portable
# params:  from_d, to_d   (datetime; to_d is EXCLUSIVE - repo.py adds the +1 day)
# order:   Request_Start_Date, Short_WO_Id  (the contract order)
# note:    Status <> 'D' drops cancelled; closed ('C') stay in, the UI hides
#          them by default (D-9). Two variants, see _PIN_COLS below.
# ---------------------------------------------------------------------------

_WO_SELECT = """
SELECT h.WO_ID, RTRIM(COALESCE(h.Short_WO_Id, '')) AS Short_WO_Id,
       RTRIM(COALESCE(h.WO_Title, '')) AS WO_Title,
       RTRIM(COALESCE(h.Status, '')) AS Status,
       RTRIM(COALESCE(h.WO_Type_Flag, 'N')) AS WO_Type_Flag,
       h.Request_Start_Date,
       h.Request_End_Date,
       COALESCE(h.Week_No, 0) AS Week_No,
       COALESCE(d.Progress_Id, 0) AS Progress_Id,
       COALESCE(d.Priority_Id, 0) AS Priority_Id,
       COALESCE(d.Duration_In_Hours, 0) AS Duration_In_Hours,
       COALESCE(d.User_ID_Responsibility, 0) AS Resp_User_Id,
       RTRIM(COALESCE(a.Short_asset_Id, '')) AS AssetId,
       RTRIM(COALESCE(a.Asset_Title, '')) AS AssetTitle,
       RTRIM(COALESCE(l.Short_Location_ID, '')) AS LocationId,
       RTRIM(COALESCE(l.Location_Title, '')) AS LocationTitle,
       RTRIM(COALESCE(p.Short_Priority_Id, '')) AS PriorityShort,
       CASE WHEN RTRIM(COALESCE(h.Purchase_Order_Flag, '')) = '1'
                 OR EXISTS (SELECT 1 FROM dbo.PO_Header ph WHERE ph.WO_Id = h.WO_ID)
                 OR EXISTS (SELECT 1 FROM dbo.PO_Details pd WHERE pd.WO_Id = h.WO_ID)
            THEN 1 ELSE 0 END AS HasPO,
       """

# The pin columns. WO_N_Plan.WO_ID is the primary key so there is at most one
# row per WO; ORDER BY x.WO_ID is simply the deterministic key OFFSET/FETCH
# requires. Bare NULL (not CAST(NULL AS datetime)) in the no-pin variant -
# `datetime` is not a PostgreSQL type name and MSSQL's `timestamp` is
# rowversion, so any cast here would be dialect-specific for no gain: the
# value is always None and repo.py only ever tests it against None.
_PIN_COLS = """
       COALESCE((SELECT CASE WHEN RTRIM(COALESCE(x.Pinned, 'N')) = 'Y' THEN 1 ELSE 0 END
                   FROM dbo.WO_N_Plan x WHERE x.WO_ID = h.WO_ID
                  ORDER BY x.WO_ID OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY), 0) AS Pinned,
       (SELECT x.Prev_Start FROM dbo.WO_N_Plan x WHERE x.WO_ID = h.WO_ID
         ORDER BY x.WO_ID OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY) AS Prev_Start,
       (SELECT x.Pinned_On FROM dbo.WO_N_Plan x WHERE x.WO_ID = h.WO_ID
         ORDER BY x.WO_ID OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY) AS Pinned_On
"""

_NOPIN_COLS = """
       0 AS Pinned, NULL AS Prev_Start, NULL AS Pinned_On
"""

_WO_FROM = """
  FROM dbo.WO_N_Header h
  LEFT JOIN dbo.WO_N_Details d ON d.WO_ID = h.WO_ID
  LEFT JOIN dbo.Asset a ON a.Asset_ID = h.Asset_ID
  LEFT JOIN dbo.Location l ON l.Location_Id = h.Location_Id
  LEFT JOIN dbo.Priority p ON p.Priority_Id = d.Priority_Id
 WHERE RTRIM(COALESCE(h.Status, '')) <> 'D'
   AND h.Request_Start_Date >= :from_d
   AND h.Request_Start_Date <  :to_d
 ORDER BY h.Request_Start_Date, h.Short_WO_Id
"""

# Concatenated, not .format()ed - a stray brace in the SQL would break format()
# and this text will be edited by hand for years.
WO_RANGE_PINNED = _WO_SELECT + _PIN_COLS + _WO_FROM
WO_RANGE_NOPIN = _WO_SELECT + _NOPIN_COLS + _WO_FROM


# ---------------------------------------------------------------------------
# name:    planner.labour_range
# dialect: portable
# params:  from_d, to_d   (datetime; to_d EXCLUSIVE)
# note:    Scoped by the WO's START DATE, not by Res_Date - a labour row dated
#          outside the window still comes back if its WO starts inside it.
#          Deliberate (workerWeeks buckets by Res_Date afterwards). Do not
#          "fix" it to filter on r.Res_Date without a parity re-run.
# ---------------------------------------------------------------------------

_LABOUR_COLS = """
       r.Res_Id, r.WO_Id,
       COALESCE(r.User_Id, 0) AS User_Id,
       COALESCE(r.Planned_Qty, 0) AS Planned_Qty,
       COALESCE(r.Planned_Unit_Cost, 0) AS Rate,
       RTRIM(COALESCE(r.Resource_Note, '')) AS Note,
       r.Res_Date,
       COALESCE(r.Skill_Id, 0) AS Skill_Id,
       RTRIM(COALESCE(k.Skill_Title, '')) AS Skill_Title,
       COALESCE(r.UOM_Id, 0) AS UOM_Id
"""

LABOUR_RANGE = "SELECT " + _LABOUR_COLS + """
  FROM dbo.WO_N_Resource r
  JOIN dbo.WO_N_Header h ON h.WO_ID = r.WO_Id
  LEFT JOIN dbo.Skill k ON k.Skill_ID = r.Skill_Id
 WHERE RTRIM(COALESCE(r.Resource_Type, '')) = 'L'
   AND RTRIM(COALESCE(h.Status, '')) <> 'D'
   AND h.Request_Start_Date >= :from_d
   AND h.Request_Start_Date <  :to_d
 ORDER BY r.WO_Id, r.Res_Date, r.Res_Id
"""


# ---------------------------------------------------------------------------
# name:    planner.worker_skills
# dialect: portable
# params:  none
# note:    Two different Active domains, both real on RST (raw log 8.2b/8.2c):
#          Users.Active is 'Y'/'N' (443/677), User_Skill.Active is '1'/'0'
#          (668/314). Excluding both '0' and 'N' is the KJ 5.0a rule.
#          An assignable worker = active user with >= 1 active skill row,
#          which is what the JOIN (not LEFT JOIN) on User_Skill enforces.
# ---------------------------------------------------------------------------

WORKER_SKILLS = """
SELECT u.User_Id,
       RTRIM(COALESCE(u.Short_User_Id, '')) AS Short_User_Id,
       RTRIM(COALESCE(u.User_Name, '')) AS User_Name,
       COALESCE(s.Skill_ID, 0) AS Skill_ID,
       COALESCE(s.Sys_User_Skill_Id, 0) AS Sys_User_Skill_Id,
       COALESCE(s.UOM_ID, 0) AS UOM_ID,
       RTRIM(COALESCE(k.Skill_Title, '')) AS Skill_Title,
       COALESCE(s.Hrs_Per_Week, 0) AS Hrs_Per_Week,
       COALESCE(s.Supplier_ID, 0) AS Supplier_ID,
       RTRIM(COALESCE(sp.Short_Supplier_Id, '')) AS Supplier_Short,
       RTRIM(COALESCE(sp.Company_Name, '')) AS Supplier_Name,
       RTRIM(COALESCE(sp.Internal_Dept, '')) AS Internal_Dept
  FROM dbo.Users u
  JOIN dbo.User_Skill s ON s.User_ID = u.User_Id
                       AND RTRIM(COALESCE(s.Active, '')) NOT IN ('0', 'N')
  LEFT JOIN dbo.Skill k ON k.Skill_ID = s.Skill_ID
  LEFT JOIN dbo.Supplier sp ON sp.Supplier_ID = s.Supplier_ID
 WHERE RTRIM(COALESCE(u.Active, '')) = 'Y'
 ORDER BY u.User_Name, s.Skill_ID
"""


# ---------------------------------------------------------------------------
# name:    planner.priorities
# dialect: portable
# params:  none
# note:    ORDER BY Sort_Sequence, Priority_Id - the second key is LOAD
#          BEARING. RST has four-way ties on Sort_Sequence (raw log 8.2f);
#          without Priority_Id the JSON contract order drifts between runs.
#          Do not drop it.
# ---------------------------------------------------------------------------

PRIORITIES = """
SELECT Priority_Id,
       RTRIM(COALESCE(Short_Priority_Id, '')) AS Short_Priority_Id,
       RTRIM(COALESCE(Priority_Title, '')) AS Priority_Title,
       COALESCE(Sort_Sequence, 0) AS Sort_Sequence
  FROM dbo.Priority
 WHERE RTRIM(COALESCE(Active, '')) NOT IN ('0', 'N')
 ORDER BY Sort_Sequence, Priority_Id
"""


# ---------------------------------------------------------------------------
# name:    planner.uom_lr_std / planner.uom_modal
# dialect: portable
# params:  none
# note:    The labour-hours unit, resolved at runtime - never a hard-coded 9.
#          Primary: the Unit_of_Measure row flagged LRStd. RST has eight such
#          rows, all Active, and ORDER BY UOM_Id resolves to 12 LABOUR HOURS
#          (raw log 8.2d).
#          Fallback: the modal UOM on existing labour rows. OD-11 (signed
#          2026-09-11) adds the UOM_Id tie-break the Ignition source lacked -
#          without it a tie picked an arbitrary unit and cached it for the
#          life of the process. Same fix PRIORITIES already carries.
# ---------------------------------------------------------------------------

UOM_LR_STD = """
SELECT UOM_Id
  FROM dbo.Unit_of_Measure
 WHERE RTRIM(COALESCE(LRStd, '')) IN ('1', 'Y')
   AND RTRIM(COALESCE(Active, '')) NOT IN ('0', 'N')
 ORDER BY UOM_Id
OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY
"""

UOM_MODAL = """
SELECT UOM_Id
  FROM dbo.WO_N_Resource
 WHERE RTRIM(COALESCE(Resource_Type, '')) = 'L'
   AND UOM_Id IS NOT NULL
 GROUP BY UOM_Id
 ORDER BY COUNT(*) DESC, UOM_Id
OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY
"""


# Every statement in this module, for the CI-gate unit test and the
# compile check. Keep in sync when a statement is added.
ALL_STATEMENTS = {
    "WO_RANGE_PINNED": WO_RANGE_PINNED,
    "WO_RANGE_NOPIN": WO_RANGE_NOPIN,
    "LABOUR_RANGE": LABOUR_RANGE,
    "WORKER_SKILLS": WORKER_SKILLS,
    "PRIORITIES": PRIORITIES,
    "UOM_LR_STD": UOM_LR_STD,
    "UOM_MODAL": UOM_MODAL,
}
