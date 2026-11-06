"""
Azztec_SaaS_app_auth_sql_v1_0_0.py  ->  backend/app/auth/sql.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s5 (OD-96..OD-102)

Statement text only (D-4). Portable SQL (D-3): no TOP, no GETDATE - every time is a UTC value the
service computes and binds, so the window arithmetic needs no dialect function and no PG-CONVERT tag.
Users, Security_Group, User_Security_Group, System_Menu(_Security_Group) and System_Details are READ;
the only writes are to the two tables migration 0002 adds. AD_Password is selected by USER_BY_LOGIN
alone, and only so rules.password_matches can compare it (OD-96).

Changelog:
  1.0.0  Initial DP2a.
"""

from __future__ import annotations

__version__ = "1.0.0"

# Active users whose login id matches, ends trimmed and case-folded (trap 9: inner spaces kept)
USER_BY_LOGIN = """
SELECT User_Id, Short_User_Id, User_Name, AD_Login_ID, AD_Password, Reset_Pwd_flag, Last_PW_Reset_Date
  FROM dbo.Users
 WHERE RTRIM(COALESCE(Active, '')) = 'Y'
   AND LOWER(LTRIM(RTRIM(AD_Login_ID))) = :login_key
"""

# The legacy frmLogin model, as workmate.identity.resolveSecurity: lowest level wins, ties lowest group
SECURITY_GROUP = """
SELECT sg.Sec_Group_ID AS group_id, sg.Sec_Group_Access_Level AS access_level
  FROM dbo.User_Security_Group usg
  JOIN dbo.Security_Group sg ON sg.Sec_Group_ID = usg.Sec_Group_ID
 WHERE usg.User_ID = :user_id
 ORDER BY sg.Sec_Group_Access_Level, sg.Sec_Group_ID
 OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY
"""

MENU_RIGHTS = """
SELECT RTRIM(sm.Menu_Tag) AS tag, RTRIM(smsg.Menu_Access_Level) AS access
  FROM dbo.System_Menu_Security_Group smsg
  JOIN dbo.System_Menu sm ON sm.Menu_ID = smsg.Menu_ID
 WHERE smsg.Sec_Group_Id = :group_id
   AND RTRIM(sm.Menu_Tag) IN (:tag_planner, :tag_womaint)
"""

RESET_POLICY = """
SELECT PW_RESET_PERIOD AS period_months, PW_Sec_Level AS sec_level
  FROM dbo.System_Details
"""

INSERT_SESSION = """
INSERT INTO dbo.Auth_Session
       (Session_Hash, User_ID, Created_Utc, Last_Seen_Utc, Expires_Utc, Revoked_Utc, Client_IP, User_Agent)
VALUES (:session_hash, :user_id, :now_utc, :now_utc, :expires_utc, NULL, :client_ip, :user_agent)
"""

SESSION_BY_HASH = """
SELECT s.Session_Hash, s.User_ID, s.Created_Utc, s.Last_Seen_Utc, s.Expires_Utc, s.Revoked_Utc,
       u.Active, u.Short_User_Id, u.User_Name
  FROM dbo.Auth_Session s
  JOIN dbo.Users u ON u.User_Id = s.User_ID
 WHERE s.Session_Hash = :session_hash
"""

TOUCH_SESSION = """
UPDATE dbo.Auth_Session SET Last_Seen_Utc = :now_utc
 WHERE Session_Hash = :session_hash AND Revoked_Utc IS NULL
"""

REVOKE_SESSION = """
UPDATE dbo.Auth_Session SET Revoked_Utc = :now_utc
 WHERE Session_Hash = :session_hash AND Revoked_Utc IS NULL
"""

INSERT_EVENT = """
INSERT INTO dbo.Auth_Event
       (Event_At_Utc, Event_Type, Reason, Login_Typed, Login_Key, User_ID, Client_IP, User_Agent, Request_Id)
VALUES (:at_utc, :event_type, :reason, :login_typed, :login_key, :user_id, :client_ip, :user_agent, :request_id)
"""

# OD-99: failures for this login inside the window and after its last success
LOGIN_FAILURES = """
SELECT COUNT(*) AS n
  FROM dbo.Auth_Event e
 WHERE e.Login_Key = :login_key
   AND e.Event_Type = 'SIGNIN_FAIL'
   AND e.Event_At_Utc >= :since_utc
   AND e.Event_At_Utc > COALESCE(
         (SELECT MAX(o.Event_At_Utc) FROM dbo.Auth_Event o
           WHERE o.Login_Key = :login_key AND o.Event_Type = 'SIGNIN_OK'),
         :floor_utc)
"""

IP_FAILURES = """
SELECT COUNT(*) AS n
  FROM dbo.Auth_Event
 WHERE Client_IP = :client_ip AND Event_Type = 'SIGNIN_FAIL' AND Event_At_Utc >= :since_utc
"""
