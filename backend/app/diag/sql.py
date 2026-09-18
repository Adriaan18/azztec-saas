"""
Azztec_SaaS_app_diag_sql_v1_0_0.py  ->  backend/app/diag/sql.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_D1a_Persist_Chunk_Spec_v1_0_0.md §3.2 · OD-55, OD-60, OD-61
Parent:   Architecture D-3 (portable SQL), OD-42 (no routine crosses from KT)
Ported from: Workmate/Diag/Diag_LogInsert and Diag_Trail 1.0.1, and KT's three database routines read on
             2026-09-19 - fn_Diag_UserTrail, vw_Diag_Problems, vw_Diag_WhoIsOn. They stay at KT; their
             logic arrives here as queries, which is what OD-42 requires.
Pair:     backend/app/diag/repo.py 1.0.0, backend/tests/test_diag_trail.py 1.0.0

One deliberate difference from KT: the trail takes a USER ID, not a name. KT's function matches
User_Name or Short_User_Id with a wildcard, so two people with the same surname share a trail; the SaaS
already has the id on every row through the actor seam.

Row limiting is OFFSET / FETCH NEXT on both engines, so no rewrite is needed there. The date arithmetic
is the one dialect split: each statement below is tagged in its Python comment, outside the string.
Tags live in PYTHON comments on purpose - SQLAlchemy text() reads a colon inside a SQL comment as a bind
parameter (Landmines §B), so nothing in these strings may carry one except a real bind.

Changelog:
  1.0.0  Initial D1a.
"""

from __future__ import annotations

__version__ = "1.0.0"

DEFAULT_RETENTION_DAYS = 60
DEFAULT_ROW_LIMIT = 500
PURGE_BATCH_ROWS = 5000


# ---------------------------------------------------------------------------
# name:    diag.insert
# dialect: portable
# params:  session_id, wm_user_id, site_code, source, tier, msg_level, message, detail
# note:    Logged_At is the database clock, as at KT. Executed many rows at a time by the writer.
# ---------------------------------------------------------------------------
INSERT = """
INSERT INTO dbo.Diag_Log
    (Logged_At, Session_Id, Wm_User_Id, Site_Code, Source, Tier, Msg_Level, Message, Detail)
VALUES
    (CURRENT_TIMESTAMP, :session_id, :wm_user_id, :site_code, :source, :tier, :msg_level, :message, :detail)
"""


_SELECT_ROW = """
SELECT
    L.Diag_Id,
    L.Logged_At,
    L.Session_Id,
    L.Wm_User_Id,
    COALESCE(RTRIM(U.User_Name), '')     AS User_Name,
    COALESCE(RTRIM(U.Short_User_Id), '') AS Short_User_Id,
    L.Source,
    L.Tier,
    L.Msg_Level,
    L.Message,
    L.Detail
FROM dbo.Diag_Log L
LEFT JOIN dbo.Users U ON U.User_Id = L.Wm_User_Id
"""

_NEWEST_FIRST = """
ORDER BY L.Logged_At DESC, L.Diag_Id DESC
OFFSET 0 ROWS FETCH NEXT :row_limit ROWS ONLY
"""


# ---------------------------------------------------------------------------
# name:    diag.trail
# dialect: mssql date arithmetic -- PG-CONVERT: Logged_At >= CURRENT_TIMESTAMP - make_interval(mins => :minutes_back)
# params:  user_id (0 = everyone), minutes_back, problems_only (0/1), row_limit
# order:   newest first, capped - the viewer's 500
# ---------------------------------------------------------------------------
TRAIL = (
    _SELECT_ROW
    + """
WHERE (:user_id = 0 OR L.Wm_User_Id = :user_id)
  AND (:problems_only = 0 OR L.Tier IN ('E', 'G'))
  AND L.Logged_At >= DATEADD(minute, -:minutes_back, CURRENT_TIMESTAMP)
"""
    + _NEWEST_FIRST
)


# ---------------------------------------------------------------------------
# name:    diag.problems          (KT vw_Diag_Problems)
# dialect: mssql date arithmetic -- PG-CONVERT: CURRENT_TIMESTAMP - make_interval(hours => :hours_back)
# params:  hours_back, row_limit
# ---------------------------------------------------------------------------
PROBLEMS = (
    _SELECT_ROW
    + """
WHERE L.Tier IN ('E', 'G')
  AND L.Logged_At >= DATEADD(hour, -:hours_back, CURRENT_TIMESTAMP)
"""
    + _NEWEST_FIRST
)


# ---------------------------------------------------------------------------
# name:    diag.by_rid
# dialect: portable
# params:  session_id, row_limit
# note:    the self-test's read-back - proof the writer reached the table (Marker Law)
# ---------------------------------------------------------------------------
BY_RID = (
    _SELECT_ROW
    + """
WHERE L.Session_Id = :session_id
"""
    + _NEWEST_FIRST
)


# ---------------------------------------------------------------------------
# name:    diag.who_is_on          (KT vw_Diag_WhoIsOn)
# dialect: mssql date arithmetic -- PG-CONVERT: CURRENT_TIMESTAMP - make_interval(mins => :minutes_back)
# params:  minutes_back
# ---------------------------------------------------------------------------
WHOISON = """
SELECT
    L.Wm_User_Id,
    COALESCE(RTRIM(U.User_Name), '') AS User_Name,
    MAX(L.Logged_At)                 AS Last_Seen,
    COUNT(*)                         AS Rows_Window,
    SUM(CASE WHEN L.Tier = 'E' THEN 1 ELSE 0 END) AS Errors,
    SUM(CASE WHEN L.Tier = 'G' THEN 1 ELSE 0 END) AS Blocked
FROM dbo.Diag_Log L
LEFT JOIN dbo.Users U ON U.User_Id = L.Wm_User_Id
WHERE L.Logged_At >= DATEADD(minute, -:minutes_back, CURRENT_TIMESTAMP)
GROUP BY L.Wm_User_Id, COALESCE(RTRIM(U.User_Name), '')
ORDER BY MAX(L.Logged_At) DESC
"""


# ---------------------------------------------------------------------------
# name:    diag.users
# dialect: mssql date arithmetic -- PG-CONVERT: CURRENT_TIMESTAMP - make_interval(mins => :minutes_back)
# params:  minutes_back
# note:    the viewer's user picker; the 'Name (id)' rendering is the client's job
# ---------------------------------------------------------------------------
USERS = """
SELECT
    L.Wm_User_Id,
    COALESCE(RTRIM(U.User_Name), '') AS User_Name,
    COUNT(*)                         AS Rows_Window
FROM dbo.Diag_Log L
LEFT JOIN dbo.Users U ON U.User_Id = L.Wm_User_Id
WHERE L.Wm_User_Id IS NOT NULL
  AND L.Logged_At >= DATEADD(minute, -:minutes_back, CURRENT_TIMESTAMP)
GROUP BY L.Wm_User_Id, COALESCE(RTRIM(U.User_Name), '')
ORDER BY COALESCE(RTRIM(U.User_Name), '')
"""


# ---------------------------------------------------------------------------
# name:    diag.purge_count        (KT Diag_Purge, counted first)
# dialect: mssql date arithmetic -- PG-CONVERT: CURRENT_TIMESTAMP - make_interval(days => :days)
# params:  days
# ---------------------------------------------------------------------------
PURGE_COUNT = """
SELECT COUNT(*) AS n
FROM dbo.Diag_Log
WHERE Logged_At < DATEADD(day, -:days, CURRENT_TIMESTAMP)
"""


# ---------------------------------------------------------------------------
# name:    diag.purge_batch
# dialect: mssql date arithmetic -- PG-CONVERT: CURRENT_TIMESTAMP - make_interval(days => :days)
# params:  days, batch
# note:    batched on purpose - one unbounded DELETE would hold locks on a table everything writes to
# ---------------------------------------------------------------------------
PURGE_BATCH = """
DELETE FROM dbo.Diag_Log
WHERE Diag_Id IN (
    SELECT Diag_Id
    FROM dbo.Diag_Log
    WHERE Logged_At < DATEADD(day, -:days, CURRENT_TIMESTAMP)
    ORDER BY Diag_Id
    OFFSET 0 ROWS FETCH NEXT :batch ROWS ONLY
)
"""


# ---------------------------------------------------------------------------
# name:    diag.delete_by_id
# dialect: portable
# params:  diag_id
# note:    Marker Law - the only delete the tests and the self-test are allowed
# ---------------------------------------------------------------------------
DELETE_BY_ID = """
DELETE FROM dbo.Diag_Log WHERE Diag_Id = :diag_id
"""

STATEMENTS = {
    "INSERT": INSERT,
    "TRAIL": TRAIL,
    "PROBLEMS": PROBLEMS,
    "BY_RID": BY_RID,
    "WHOISON": WHOISON,
    "USERS": USERS,
    "PURGE_COUNT": PURGE_COUNT,
    "PURGE_BATCH": PURGE_BATCH,
    "DELETE_BY_ID": DELETE_BY_ID,
}
