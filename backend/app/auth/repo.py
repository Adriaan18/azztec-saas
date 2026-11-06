"""
Azztec_SaaS_app_auth_repo_v1_0_0.py  ->  backend/app/auth/repo.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s5 (OD-96..OD-102)

Fetch -> plain dicts (D-4). Every function takes the connection it is given; the service decides which
reads share a transaction and which write commits. test_auth_api.py swaps these functions for an
in-memory store, so their names and return shapes are the seam - change them together with the test.

Changelog:
  1.0.0  Initial DP2a.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.engine import Connection

from app.auth import rules
from app.auth import sql as asql
from app.core import db

__version__ = "1.0.0"

FLOOR_UTC = datetime(1900, 1, 1)


def users_by_login(conn: Connection, login_key: str) -> list[dict[str, Any]]:
    """Every ACTIVE user whose login id matches. The service refuses anything but exactly one."""
    return db.rows(conn, asql.USER_BY_LOGIN, login_key=login_key)


def security(conn: Connection, user_id: int) -> dict[str, Any]:
    """{'group_id': int | None, 'level': int | None, 'tags': {Menu_Tag: Menu_Access_Level}}."""
    grp = db.rows(conn, asql.SECURITY_GROUP, user_id=user_id)
    if not grp:
        return {"group_id": None, "level": None, "tags": {}}
    group_id = db.i_(grp[0]["group_id"])
    level = db.i_(grp[0]["access_level"], -1)
    tags = {
        db.s_(r["tag"]): db.s_(r["access"])
        for r in db.rows(
            conn,
            asql.MENU_RIGHTS,
            group_id=group_id,
            tag_planner=rules.PAGE_TAGS["planner"],
            tag_womaint=rules.PAGE_TAGS["womaint"],
        )
    }
    return {"group_id": group_id, "level": level if level >= 0 else None, "tags": tags}


def reset_policy(conn: Connection) -> dict[str, int]:
    """System_Details' PW_Sec_Level (default 1) and PW_RESET_PERIOD (default 0), as Workmate.NET reads
    them with ISNULL(...). The first row wins; RST has exactly one (P2)."""
    rows = db.rows(conn, asql.RESET_POLICY)
    if not rows:
        return {"sec_level": 1, "period_months": 0}
    return {"sec_level": db.i_(rows[0]["sec_level"], 1), "period_months": db.i_(rows[0]["period_months"], 0)}


def as_date(v: Any) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return None


def insert_session(
    conn: Connection,
    session_hash: str,
    user_id: int,
    now_utc: datetime,
    expires_utc: datetime,
    client_ip: str,
    user_agent: str,
) -> None:
    db.execute(
        conn,
        asql.INSERT_SESSION,
        session_hash=session_hash,
        user_id=user_id,
        now_utc=now_utc,
        expires_utc=expires_utc,
        client_ip=client_ip[:45],
        user_agent=user_agent[:200],
    )


def session_by_hash(conn: Connection, session_hash: str) -> dict[str, Any] | None:
    rows = db.rows(conn, asql.SESSION_BY_HASH, session_hash=session_hash)
    return rows[0] if rows else None


def touch_session(conn: Connection, session_hash: str, now_utc: datetime) -> None:
    db.execute(conn, asql.TOUCH_SESSION, session_hash=session_hash, now_utc=now_utc)


def revoke_session(conn: Connection, session_hash: str, now_utc: datetime) -> int:
    return db.execute(conn, asql.REVOKE_SESSION, session_hash=session_hash, now_utc=now_utc)


def insert_event(
    conn: Connection,
    *,
    at_utc: datetime,
    event_type: str,
    reason: str | None,
    login_typed: str | None,
    login_key: str | None,
    user_id: int | None,
    client_ip: str,
    user_agent: str,
    request_id: str,
) -> None:
    """One Auth_Event row (OD-101). Never a password: there is no parameter that could carry one."""
    db.execute(
        conn,
        asql.INSERT_EVENT,
        at_utc=at_utc,
        event_type=event_type,
        reason=reason,
        login_typed=(login_typed or None) and login_typed[: rules.LOGIN_MAX],
        login_key=(login_key or None) and login_key[: rules.LOGIN_MAX],
        user_id=user_id if user_id else None,
        client_ip=client_ip[:45],
        user_agent=user_agent[:200],
        request_id=request_id[:36],
    )


def login_failures(conn: Connection, login_key: str, since_utc: datetime) -> int:
    return db.i_(
        db.scalar(conn, asql.LOGIN_FAILURES, login_key=login_key, since_utc=since_utc, floor_utc=FLOOR_UTC)
    )


def ip_failures(conn: Connection, client_ip: str, since_utc: datetime) -> int:
    return db.i_(db.scalar(conn, asql.IP_FAILURES, client_ip=client_ip[:45], since_utc=since_utc))
