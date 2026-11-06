"""
Azztec_SaaS_app_auth_service_v1_0_0.py  ->  backend/app/auth/service.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s5 (OD-96..OD-103)

The three things the auth slice does, in one place each:

  sign_in(...)                 OD-99 lockout -> OD-96 lookup + verify -> OD-98 refusals -> a session.
                               One transaction: the event row and the session row commit together.
  sign_out(token, ...)         revokes the session row (idempotent) and writes SIGNOUT.
  principal_from_request(req)  the deps.LOADER main.py installs: cookie -> Auth_Session -> Users.Active
                               (every request) -> rights (cached 60 s per user) -> a Principal, or None.

Times are naive UTC datetimes from utcnow(), bound as parameters - the database clock is never asked.
Nothing here logs, returns or stores a password; diag detail carries the login as typed and the reason.

Changelog:
  1.0.0  Initial DP2a.
"""

from __future__ import annotations

import secrets
import threading
import time
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Request
from sqlalchemy.engine import Connection

from app.auth import repo, rules
from app.core import db, diag
from app.core.config import get_settings
from app.core.deps import Principal

__version__ = "1.0.0"


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _write_conn() -> AbstractContextManager[Connection]:
    """A committing transaction. test_auth_api.py replaces both helpers with a null context."""
    return db.get_engine().begin()


def _read_conn() -> AbstractContextManager[Connection]:
    return db.get_engine().connect()


# ---------------------------------------------------------------------------
# rights cache (OD-100: a change in Workmate.NET bites within a minute; trap 8)
# ---------------------------------------------------------------------------

_CACHE: dict[int, tuple[float, dict[str, Any]]] = {}
_CACHE_LOCK = threading.Lock()


def clear_rights(user_id: int | None = None) -> None:
    with _CACHE_LOCK:
        if user_id is None:
            _CACHE.clear()
        else:
            _CACHE.pop(int(user_id), None)


def _security(conn: Connection, user_id: int) -> dict[str, Any]:
    ttl = get_settings().rights_cache_seconds
    now = time.monotonic()
    with _CACHE_LOCK:
        hit = _CACHE.get(user_id)
        if hit and hit[0] > now:
            return hit[1]
    sec = repo.security(conn, user_id)
    out = {
        "has_group": sec["group_id"] is not None,
        "level": sec["level"],
        "rights": rules.page_rights(sec["level"] if sec["group_id"] is not None else None, sec["tags"]),
        "is_admin": rules.is_admin(sec["level"]) if sec["group_id"] is not None else False,
    }
    with _CACHE_LOCK:
        _CACHE[user_id] = (now + ttl, out)
    return out


# ---------------------------------------------------------------------------
# sign in / out
# ---------------------------------------------------------------------------


@dataclass
class SignInOutcome:
    ok: bool
    code: str = ""  # SIGNIN_FAILED | LOCKED | SYS_USER | DEFAULT_PASSWORD | NO_GROUP | RESET_DUE
    status: int = 200
    message: str = ""
    token: str = ""
    principal: Principal | None = None
    expires_at: datetime | None = None
    detail: dict[str, Any] = field(default_factory=dict)


def _event(conn: Connection, ctx: dict[str, Any], event_type: str, reason: str | None, user_id: int | None):
    repo.insert_event(
        conn,
        at_utc=ctx["now"],
        event_type=event_type,
        reason=reason,
        login_typed=ctx["typed"],
        login_key=ctx["key"],
        user_id=user_id,
        client_ip=ctx["ip"],
        user_agent=ctx["ua"],
        request_id=ctx["rid"],
    )


def _refused(code: str, status: int, **detail: Any) -> SignInOutcome:
    return SignInOutcome(ok=False, code=code, status=status, message=rules.MESSAGES[code], detail=detail)


def sign_in(login: str, password: str, client_ip: str, user_agent: str, request_id: str) -> SignInOutcome:
    s = get_settings()
    ctx = {
        "now": utcnow(),
        "typed": rules.clip_login(login),
        "key": rules.normalise_login(login),
        "ip": client_ip or "",
        "ua": user_agent or "",
        "rid": request_id or "",
    }
    since = ctx["now"] - timedelta(minutes=s.lockout_minutes)
    with _write_conn() as conn:
        lock = rules.lockout(
            repo.login_failures(conn, ctx["key"], since),
            repo.ip_failures(conn, ctx["ip"], since),
            s.lockout_failures,
            s.lockout_ip_failures,
        )
        if lock:
            _event(conn, ctx, "LOCKED", lock, None)
            return _refused("LOCKED", 423, lock=lock)

        found = repo.users_by_login(conn, ctx["key"]) if ctx["key"] else []
        user = found[0] if len(found) == 1 else None
        stored = user["AD_Password"] if user else rules.DUMMY_STORED  # same work either way (trap 6)
        matched = rules.password_matches(stored, password)
        if user is None or not matched:
            reason = "BAD_PASSWORD" if user else ("AMBIGUOUS" if found else "NO_USER")
            _event(conn, ctx, "SIGNIN_FAIL", reason, int(user["User_Id"]) if user else None)
            return _refused("SIGNIN_FAILED", 401, reason=reason)

        user_id = int(user["User_Id"])
        sec = _security(conn, user_id)
        policy = repo.reset_policy(conn)
        due = rules.reset_due(
            policy["sec_level"],
            policy["period_months"],
            db.s_(user.get("Reset_Pwd_flag")),
            repo.as_date(user.get("Last_PW_Reset_Date")),
            ctx["now"].date(),
        )
        why = rules.refusal(
            db.s_(user.get("Short_User_Id")), password, db.s_(user.get("AD_Login_ID")), sec["has_group"], due
        )
        if why:
            _event(conn, ctx, "SIGNIN_REFUSED", why, user_id)
            return _refused(why, 403, reason=why, userId=user_id)

        token = secrets.token_urlsafe(32)
        expires = rules.expires_at(ctx["now"], s.session_hours)
        repo.insert_session(conn, rules.token_hash(token), user_id, ctx["now"], expires, ctx["ip"], ctx["ua"])
        _event(conn, ctx, "SIGNIN_OK", None, user_id)
    principal = Principal(
        user_id=user_id,
        short_id=db.s_(user.get("Short_User_Id")),
        name=db.s_(user.get("User_Name")),
        rights=dict(sec["rights"]),
        is_admin=bool(sec["is_admin"]),
        expires_at=expires.isoformat(timespec="seconds") + "Z",
    )
    return SignInOutcome(ok=True, token=token, principal=principal, expires_at=expires)


def sign_out(token: str | None, client_ip: str, user_agent: str, request_id: str) -> int:
    """Revoke the session behind the cookie, if any. Returns the user id it belonged to (0 = none)."""
    if not token:
        return 0
    h = rules.token_hash(token)
    now = utcnow()
    with _write_conn() as conn:
        row = repo.session_by_hash(conn, h)
        if row is None:
            return 0
        user_id = int(row["User_ID"])
        ctx = {"now": now, "typed": None, "key": None, "ip": client_ip, "ua": user_agent, "rid": request_id}
        if repo.revoke_session(conn, h, now):  # one SIGNOUT row per session, however often it is posted
            _event(conn, ctx, "SIGNOUT", None, user_id)
    clear_rights(user_id)
    return user_id


# ---------------------------------------------------------------------------
# the request -> principal loader (deps.LOADER)
# ---------------------------------------------------------------------------


def principal_from_request(request: Request) -> Principal | None:
    s = get_settings()
    token = request.cookies.get(s.session_cookie)
    if not token:
        return None
    h = rules.token_hash(token)
    now = utcnow()
    with _read_conn() as conn:
        row = repo.session_by_hash(conn, h)
        if row is None:
            return None
        user_id = int(row["User_ID"])
        state = rules.session_state(
            now, row["Last_Seen_Utc"], row["Expires_Utc"], row["Revoked_Utc"], s.session_idle_minutes
        )
        active = db.s_(row.get("Active")).upper() == "Y"
        sec = _security(conn, user_id) if state == "ok" and active else None
    rid = getattr(request.state, "rid", "")
    if state != "ok" or not active or sec is None or not sec["has_group"]:
        why = state if state != "ok" else ("inactive" if not active else "no_group")
        if state != "revoked":
            with _write_conn() as conn:
                repo.revoke_session(conn, h, now)
                ctx = {
                    "now": now,
                    "typed": None,
                    "key": None,
                    "ip": _ip(request),
                    "ua": _ua(request),
                    "rid": rid,
                }
                _event(conn, ctx, "EXPIRED", why, user_id)
            clear_rights(user_id)
        diag.log("G", f"session ended reason={why}", actor=user_id, request_id=rid, source="auth")
        return None
    if rules.needs_touch(now, row["Last_Seen_Utc"]):
        with _write_conn() as conn:
            repo.touch_session(conn, h, now)
    return Principal(
        user_id=user_id,
        short_id=db.s_(row.get("Short_User_Id")),
        name=db.s_(row.get("User_Name")),
        rights=dict(sec["rights"]),
        is_admin=bool(sec["is_admin"]),
        expires_at=row["Expires_Utc"].isoformat(timespec="seconds") + "Z",
    )


def _ip(request: Request) -> str:
    return request.client.host if request.client else ""


def _ua(request: Request) -> str:
    return request.headers.get("user-agent", "")[:200]
