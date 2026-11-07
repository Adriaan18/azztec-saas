"""
Azztec_SaaS_app_planner_sql_v1_2_0.py  ->  backend/app/planner/sql.py
Version:  1.2.0
Author:   Adriaan
Spec:     Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §5.1 (OD-110, OD-114);
          earlier: Azztec_SaaS_S1h_Priority_Initials_Chunk_Spec_v1_0_0.md §3.1
Parent:   Azztec_SaaS_Data_Layer_and_RST_DB_v1_0_0.md §4-§5, Architecture D-3
Ported from: workmate.planner 1.3.1 lines 539-629 (_woSql, _LABOUR_SQL, _WORKER_SQL,
             _PRIORITY_SQL, hoursUomId probes); DP3 adds 783-817 (_eventRow,
             _loadSql, _SUBTASK_SQL, _LABOUR_DATES_SQL), 993-1014 (moveWO's
             writes) and 1120-1130 (_upsertPin)
Pair:     backend/app/planner/repo.py 1.2.0

Every statement the planner runs, as dialect-portable text() source. No Python
logic here beyond assembling the two pin variants - repo.py binds the params
and maps the rows. Since DP3 that is the read path AND the move: one header
update, the subtask and planned-labour shifts, the pin row, the audit row.

The five habits (Data Layer §5) applied on the way in:
  the MSSQL null-default function -> COALESCE                    ~45 sites
  row-limiting by TOP             -> OFFSET / FETCH NEXT           5 sites
  ? positional params             -> :named binds
  the MSSQL current-time function -> CURRENT_TIMESTAMP (the pin and audit
                                     writes, DP3)
  dbo. prefix                     -> already present throughout
FETCH NEXT is valid on both engines (PostgreSQL treats NEXT and FIRST as
synonyms), so none of the rewritten row limits needs a PG-CONVERT tag. The
two date shifts DO need one - DATEADD is MSSQL date arithmetic - and carry it
in their Python header (the D1a diag/sql.py precedent, OD-60).

Datetimes are never compared by equality here (DP3 spec §3.3): RST runs at
compatibility level 160 and dev at 170, where a datetime column compared with
a bound datetime2 is converted exactly, so a value read back and bound again
does not match. Every date predicate is a half-open day range.

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
  1.2.0  DP3a. Ten statements for the move (OD-110, OD-114): LOAD_WO_PINNED /
         LOAD_WO_NOPIN (the oracle's _loadSql, reusing the /range pin
         columns), SUBTASK_DATES, LABOUR_DATES, MOVE_HEADER (with the start-day
         guard the oracle lacked - a raced move touches 0 rows), SHIFT_SUBTASKS
         and SHIFT_LABOUR (DATEADD with CAST(:delta AS int), PG-CONVERT in the
         header), PIN_UPDATE / PIN_INSERT / PIN_CLEAR, EVENT_INSERT - eleven
         entries in ALL_STATEMENTS (the load has two pin variants), so both
         gates in test_planner_repo.py cover them. No read statement changed.
  1.1.0  S1h. PRIORITIES gains Colour (open item 29). One column added to one
         SELECT list - no other statement touched, ORDER BY unchanged.
  1.0.1  Docstring reworded so the CI dialect gate stops matching this
         module's own documentation. No SQL change - every statement is
         byte-identical to 1.0.0. Caught by the gate on first run.
  1.0.0  Initial. OD-11 signed 2026-09-11 - UOM_MODAL gains the UOM_Id
         tie-break the source lacked.
"""

from __future__ import annotations

__version__ = "1.2.0"


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

LABOUR_RANGE = (
    "SELECT "
    + _LABOUR_COLS
    + """
  FROM dbo.WO_N_Resource r
  JOIN dbo.WO_N_Header h ON h.WO_ID = r.WO_Id
  LEFT JOIN dbo.Skill k ON k.Skill_ID = r.Skill_Id
 WHERE RTRIM(COALESCE(r.Resource_Type, '')) = 'L'
   AND RTRIM(COALESCE(h.Status, '')) <> 'D'
   AND h.Request_Start_Date >= :from_d
   AND h.Request_Start_Date <  :to_d
 ORDER BY r.WO_Id, r.Res_Date, r.Res_Id
"""
)


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
#
#          The Active filter drops HALF the RST table. Fourteen rows exist,
#          Active is 1 or 0 there, and seven reach the payload - P2 P1 P3 P5
#          P6 P4 and N/A (read 2026-09-13, and dm_exec_query_stats reports
#          max_rows 7 on this statement, so two oracles agree). Ties survive
#          the filter (P2 and P1 at 1, P5 and P6 at 3), which is why OD-11
#          above still matters and why OD-32 stays withdrawn.
#
#          Colour is varchar(255) NULL on BOTH databases - free text, no
#          constraint, no guarantee of a hex triplet. COALESCE gives '' for
#          NULL and the API ships whatever is stored (OD-36); deciding
#          whether the value is paintable belongs to the renderer, not here.
#          Among RST's seven active rows every colour is distinct; KT carries
#          the same colour on all four of its rows, so there the letter class
#          is what paints. Both are real data, neither is the right one.
# ---------------------------------------------------------------------------

PRIORITIES = """
SELECT Priority_Id,
       RTRIM(COALESCE(Short_Priority_Id, '')) AS Short_Priority_Id,
       RTRIM(COALESCE(Priority_Title, '')) AS Priority_Title,
       RTRIM(COALESCE(Colour, '')) AS Colour,
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


# ===========================================================================
# DP3 - the move. Reads first (one WO), then the writes in the order the
# service runs them inside its one transaction.
# ===========================================================================

# ---------------------------------------------------------------------------
# name:    planner.load_wo   (LOAD_WO_PINNED / LOAD_WO_NOPIN)
# dialect: portable
# params:  wo_id
# note:    The oracle's _loadSql (800-810): the header, the estimate, whether a
#          details row exists, and the three pin columns - the same _PIN_COLS /
#          _NOPIN_COLS the range read uses, so one WO reads the same here as
#          on the grid. Both dates come back RAW: the writer shifts them and
#          keeps their time of day (DP3-E P3 - 658 open starts and 2,713 open
#          ends carry one at RST).
# ---------------------------------------------------------------------------

_LOAD_SELECT = """
SELECT h.WO_ID, RTRIM(COALESCE(h.Short_WO_Id, '')) AS Short_WO_Id,
       RTRIM(COALESCE(h.WO_Title, '')) AS WO_Title,
       RTRIM(COALESCE(h.Status, '')) AS Status,
       RTRIM(COALESCE(h.WO_Type_Flag, 'N')) AS WO_Type_Flag,
       h.Request_Start_Date,
       h.Request_End_Date,
       COALESCE(h.Week_No, 0) AS Week_No,
       COALESCE(d.Duration_In_Hours, 0) AS Duration_In_Hours,
       CASE WHEN d.WO_ID IS NULL THEN 0 ELSE 1 END AS HasDetails,
"""

_LOAD_FROM = """
  FROM dbo.WO_N_Header h
  LEFT JOIN dbo.WO_N_Details d ON d.WO_ID = h.WO_ID
 WHERE h.WO_ID = :wo_id
"""

LOAD_WO_PINNED = _LOAD_SELECT + _PIN_COLS + _LOAD_FROM
LOAD_WO_NOPIN = _LOAD_SELECT + _NOPIN_COLS + _LOAD_FROM


# ---------------------------------------------------------------------------
# name:    planner.subtask_dates
# dialect: portable
# params:  wo_id
# note:    _SUBTASK_SQL (812). One row per dated subtask, in date order. At
#          RST no open WO has a subtask row (DP3-E P4 - 80,550 rows, none on
#          an open WO): ported for parity, it returns nothing there.
# ---------------------------------------------------------------------------

SUBTASK_DATES = """
SELECT s.Req_Start_Date
  FROM dbo.WO_N_Subtasks s
 WHERE s.WO_ID = :wo_id
   AND s.Req_Start_Date IS NOT NULL
 ORDER BY s.Req_Start_Date
"""


# ---------------------------------------------------------------------------
# name:    planner.labour_dates
# dialect: portable
# params:  wo_id
# note:    _LABOUR_DATES_SQL (815). Grouped by the exact Res_Date, as the
#          oracle does; at RST that equals grouping by day (DP3-E P4 - no
#          planned-labour row carries a time of day).
# ---------------------------------------------------------------------------

LABOUR_DATES = """
SELECT r.Res_Date, COUNT(*) AS Cnt
  FROM dbo.WO_N_Resource r
 WHERE r.WO_Id = :wo_id
   AND RTRIM(COALESCE(r.Resource_Type, '')) = 'L'
   AND r.Res_Date IS NOT NULL
 GROUP BY r.Res_Date
 ORDER BY r.Res_Date
"""


# ---------------------------------------------------------------------------
# name:    planner.move_header
# dialect: portable
# params:  wo_id, new_start, new_end (None when the WO has no end), week_no
#          (Decimal), day_from / day_to (the loaded start's day, half-open)
# note:    moveWO 993. The start-day guard is OD-110: the oracle loaded the WO
#          outside its transaction and updated by WO_ID alone, so a move that
#          raced it was overwritten. Here a raced move leaves this statement
#          touching 0 rows, which the service turns into STALE and rolls back.
# ---------------------------------------------------------------------------

MOVE_HEADER = """
UPDATE dbo.WO_N_Header
   SET Request_Start_Date = :new_start,
       Request_End_Date = :new_end,
       Week_No = :week_no
 WHERE WO_ID = :wo_id
   AND Request_Start_Date >= :day_from
   AND Request_Start_Date < :day_to
"""


# ---------------------------------------------------------------------------
# name:    planner.shift_subtasks
# dialect: MSSQL date arithmetic -- PG-CONVERT: Req_Start_Date + make_interval(days => :delta)
# params:  wo_id, delta, week_no (Decimal, of the NEW day), day_from / day_to
#          (one old day, half-open)
# note:    moveWO 997-1004. One call per distinct old day; the service walks
#          the days latest-first when delta > 0, earliest-first otherwise, so
#          no row is shifted twice. DATEADD on the column keeps each row's
#          time of day; CAST keeps its second argument an int whatever the
#          driver binds.
# ---------------------------------------------------------------------------

SHIFT_SUBTASKS = """
UPDATE dbo.WO_N_Subtasks
   SET Req_Start_Date = DATEADD(day, CAST(:delta AS int), Req_Start_Date),
       Week_No = :week_no
 WHERE WO_ID = :wo_id
   AND Req_Start_Date >= :day_from
   AND Req_Start_Date < :day_to
"""


# ---------------------------------------------------------------------------
# name:    planner.shift_labour
# dialect: MSSQL date arithmetic -- PG-CONVERT: Res_Date + make_interval(days => :delta)
# params:  wo_id, delta
# note:    moveWO 1006 - the legacy "User Planned Date" moves with the WO. One
#          statement over every planned-labour row with a date; parts rows
#          ('P') never move. No index leads with WO_Id (the key is Res_Id,
#          WO_Id - DP3-E P2), so this scans WO_N_Resource, as the range read
#          already does.
# ---------------------------------------------------------------------------

SHIFT_LABOUR = """
UPDATE dbo.WO_N_Resource
   SET Res_Date = DATEADD(day, CAST(:delta AS int), Res_Date)
 WHERE WO_Id = :wo_id
   AND RTRIM(COALESCE(Resource_Type, '')) = 'L'
   AND Res_Date IS NOT NULL
"""


# ---------------------------------------------------------------------------
# name:    planner.pin_update / planner.pin_insert / planner.pin_clear
# dialect: portable
# params:  PIN_UPDATE  wo_id, user_id, engine_date, note
#          PIN_INSERT  wo_id, user_id, engine_date, note, server_name
#          PIN_CLEAR   wo_id
# note:    _upsertPin (1120-1130) and the unpin branch of moveWO (1014).
#          Prev_Start is written on the FIRST pin only - the date the WO had,
#          undo's target - and COALESCE keeps it on every later pin (OD-114).
#          The update runs first; the insert only when it touched nothing. The
#          insert leaves Entry_Date to its default and Last_Save_Date NULL, as
#          the oracle's did (DP3-E P1).
# ---------------------------------------------------------------------------

PIN_UPDATE = """
UPDATE dbo.WO_N_Plan
   SET Pinned = 'Y',
       Pinned_By = :user_id,
       Pinned_On = CURRENT_TIMESTAMP,
       Prev_Start = COALESCE(Prev_Start, :engine_date),
       Note = :note,
       Last_Save_Date = CURRENT_TIMESTAMP
 WHERE WO_ID = :wo_id
"""

PIN_INSERT = """
INSERT INTO dbo.WO_N_Plan (WO_ID, Pinned, Pinned_By, Pinned_On, Prev_Start, Note, Server_Name)
VALUES (:wo_id, 'Y', :user_id, CURRENT_TIMESTAMP, :engine_date, :note, :server_name)
"""

PIN_CLEAR = """
UPDATE dbo.WO_N_Plan
   SET Pinned = 'N',
       Last_Save_Date = CURRENT_TIMESTAMP
 WHERE WO_ID = :wo_id
"""


# ---------------------------------------------------------------------------
# name:    planner.event_insert
# dialect: portable
# params:  wo_id, user_id, event_name, details, server_name, source_form
# note:    _eventRow (783-791). Sys_WO_Event_Id is an identity (DP3-E P1) and
#          nothing reads it back, so this is a plain insert, not
#          db.insert_returning_id(). WO_Event_History is a heap with no index
#          (P2): the insert is cheap. Edited_Date is the database's clock, as
#          the oracle's was.
# ---------------------------------------------------------------------------

EVENT_INSERT = """
INSERT INTO dbo.WO_Event_History
       (WO_ID, User_Id_Edited_By, Edited_Date, Event_Name, event_details, server_name, Source_Form)
VALUES (:wo_id, :user_id, CURRENT_TIMESTAMP, :event_name, :details, :server_name, :source_form)
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
    # DP3
    "LOAD_WO_PINNED": LOAD_WO_PINNED,
    "LOAD_WO_NOPIN": LOAD_WO_NOPIN,
    "SUBTASK_DATES": SUBTASK_DATES,
    "LABOUR_DATES": LABOUR_DATES,
    "MOVE_HEADER": MOVE_HEADER,
    "SHIFT_SUBTASKS": SHIFT_SUBTASKS,
    "SHIFT_LABOUR": SHIFT_LABOUR,
    "PIN_UPDATE": PIN_UPDATE,
    "PIN_INSERT": PIN_INSERT,
    "PIN_CLEAR": PIN_CLEAR,
    "EVENT_INSERT": EVENT_INSERT,
}
