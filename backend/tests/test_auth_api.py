"""
Azztec_SaaS_backend_tests_test_auth_api_v1_0_0.py  ->  backend/tests/test_auth_api.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s5.6, s9 (OD-96..OD-101)
Pair of:  app/auth/router.py, service.py, repo.py 1.0.0 + app/core/deps.py 1.2.0 + app/main.py 0.6.0

TestClient over the real app with ZERO database: repo's functions are swapped for an in-memory Store and
service's two connection helpers for a null context, so nothing here can touch RST. The real SQL is
proven by the DP2 smoke on dbWorkmate_DP1_Test. The client talks https://testserver because the cookie is
Secure (httpx sends a Secure cookie over https only). No lifespan: the client is never entered.

The suite boots against the real backend/.env, so the spec's numbers (cookie, lifetimes, lockout) are
pinned on the cached Settings for every test here - a .env that changes them must not red these tests.

Changelog:
  1.0.0  Initial DP2a. 15 tests, 18 cases once parametrised.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("WORKMATE_ENV", "test")

from app.auth import repo, rules, service  # noqa: E402 - after env is set
from app.core import db, deps, diag  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "Tui-Kereru-42"  # asserted absent from every stored row and every log call
CSRF = {"X-Azztec-Request": "1"}
SIGNIN = "/api/v1/auth/signin"
SIGNOUT = "/api/v1/auth/signout"
ME = "/api/v1/auth/me"
COOKIE = "azztec_session"
SCHEDULEX = rules.PAGE_TAGS["planner"]
WOMAINT = rules.PAGE_TAGS["womaint"]
PINNED = {
    "session_cookie": COOKIE,
    "session_hours": 12,
    "session_idle_minutes": 240,
    "cookie_secure": True,
    "lockout_failures": 5,
    "lockout_ip_failures": 20,
    "lockout_minutes": 15,
    "rights_cache_seconds": 60,
}


def _user(uid, sid, login, pw, active="Y", flag="0"):
    return {
        "User_Id": uid,
        "Short_User_Id": sid,
        "User_Name": f"{sid} name",
        "AD_Login_ID": login,
        "AD_Password": rules.md5_20(pw),
        "Active": active,
        "Reset_Pwd_flag": flag,
        "Last_PW_Reset_Date": None,
    }


class Store:
    def __init__(self) -> None:
        self.users = [
            _user(21, "AZZ", "Azzmax", PASSWORD),
            _user(1, "SYS_USER", "sys_user", "sys_user"),
            _user(30, "WMU", "wmuser", "wm"),
            _user(31, "JS", "jsmith", "jsmith"),
            _user(32, "NG", "nogroup", PASSWORD),
            _user(33, "RO1", "readonly", PASSWORD),
            _user(34, "KE", "Kevin E", PASSWORD),
            _user(35, "OLD", "old", PASSWORD, active="N"),
        ]
        self.groups: dict[int, tuple[int, int]] = {
            21: (1, 1),
            1: (1, 1),
            30: (2, 3),
            31: (2, 3),
            33: (17, 4),
            34: (2, 3),
        }
        self.tags: dict[int, dict[str, str]] = {17: {SCHEDULEX: "RO", WOMAINT: "RO"}}
        self.policy = {"sec_level": 1, "period_months": 0}
        self.sessions: dict[str, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []

    def user(self, uid: int) -> dict[str, Any]:
        return next(u for u in self.users if u["User_Id"] == uid)

    # --- the repo seam -----------------------------------------------------------------------------
    def users_by_login(self, conn, login_key):
        return [
            dict(u)
            for u in self.users
            if u["Active"] == "Y" and u["AD_Login_ID"].strip().lower() == login_key
        ]

    def security(self, conn, user_id):
        if user_id not in self.groups:
            return {"group_id": None, "level": None, "tags": {}}
        gid, level = self.groups[user_id]
        return {"group_id": gid, "level": level, "tags": dict(self.tags.get(gid, {}))}

    def reset_policy(self, conn):
        return dict(self.policy)

    def insert_session(self, conn, session_hash, user_id, now_utc, expires_utc, client_ip, user_agent):
        self.sessions[session_hash] = {
            "Session_Hash": session_hash,
            "User_ID": user_id,
            "Created_Utc": now_utc,
            "Last_Seen_Utc": now_utc,
            "Expires_Utc": expires_utc,
            "Revoked_Utc": None,
            "Client_IP": client_ip,
            "User_Agent": user_agent,
        }

    def session_by_hash(self, conn, session_hash):
        row = self.sessions.get(session_hash)
        if row is None:
            return None
        u = self.user(row["User_ID"])
        return {
            **row,
            "Active": u["Active"],
            "Short_User_Id": u["Short_User_Id"],
            "User_Name": u["User_Name"],
        }

    def touch_session(self, conn, session_hash, now_utc):
        if self.sessions.get(session_hash, {}).get("Revoked_Utc") is None and session_hash in self.sessions:
            self.sessions[session_hash]["Last_Seen_Utc"] = now_utc

    def revoke_session(self, conn, session_hash, now_utc):
        row = self.sessions.get(session_hash)
        if row and row["Revoked_Utc"] is None:
            row["Revoked_Utc"] = now_utc
            return 1
        return 0

    def insert_event(self, conn, **kw):
        self.events.append(kw)

    def login_failures(self, conn, login_key, since_utc):
        oks = [
            e["at_utc"] for e in self.events if e["login_key"] == login_key and e["event_type"] == "SIGNIN_OK"
        ]
        floor = max(oks) if oks else repo.FLOOR_UTC
        return sum(
            1
            for e in self.events
            if e["login_key"] == login_key
            and e["event_type"] == "SIGNIN_FAIL"
            and e["at_utc"] >= since_utc
            and e["at_utc"] > floor
        )

    def ip_failures(self, conn, client_ip, since_utc):
        return sum(
            1
            for e in self.events
            if e["client_ip"] == client_ip and e["event_type"] == "SIGNIN_FAIL" and e["at_utc"] >= since_utc
        )


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> Store:
    st = Store()
    for name in (
        "users_by_login",
        "security",
        "reset_policy",
        "insert_session",
        "session_by_hash",
        "touch_session",
        "revoke_session",
        "insert_event",
        "login_failures",
        "ip_failures",
    ):
        monkeypatch.setattr(repo, name, getattr(st, name))
    settings = get_settings()
    for key, value in PINNED.items():
        monkeypatch.setattr(settings, key, value)
    monkeypatch.setattr(service, "_write_conn", lambda: contextlib.nullcontext(None))
    monkeypatch.setattr(service, "_read_conn", lambda: contextlib.nullcontext(None))
    service.clear_rights()
    return st


@pytest.fixture
def client(store: Store) -> Iterator[TestClient]:
    yield TestClient(app, base_url="https://testserver")
    app.dependency_overrides.clear()
    service.clear_rights()


def _signin(c: TestClient, login: str, pw: str):
    return c.post(SIGNIN, json={"login": login, "password": pw}, headers=CSRF)


# ---------------------------------------------------------------------------
# OD-96 / OD-98: who gets in, and what the screen is told
# ---------------------------------------------------------------------------


def test_signin_needs_the_csrf_header(client: TestClient, store: Store) -> None:
    r = client.post(SIGNIN, json={"login": "Azzmax", "password": PASSWORD})
    assert r.status_code == 403 and r.json()["code"] == "CSRF"
    assert not store.sessions and not store.events


def test_unknown_login_and_wrong_password_look_the_same(client: TestClient, store: Store) -> None:
    a = _signin(client, "nobody-here", PASSWORD)
    b = _signin(client, "Azzmax", "not-it")
    assert a.status_code == b.status_code == 401
    ja, jb = a.json(), b.json()
    assert ja["code"] == jb["code"] == "SIGNIN_FAILED" and ja["message"] == jb["message"]
    assert [e["reason"] for e in store.events] == ["NO_USER", "BAD_PASSWORD"]


def test_an_inactive_user_is_simply_unknown(client: TestClient, store: Store) -> None:
    r = _signin(client, "old", PASSWORD)
    assert r.status_code == 401 and r.json()["code"] == "SIGNIN_FAILED"
    assert store.events[-1]["reason"] == "NO_USER"


def test_signin_ok_sets_a_hardened_cookie_and_stores_only_its_hash(client: TestClient, store: Store) -> None:
    r = _signin(client, "Azzmax", PASSWORD)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"] == {"userId": 21, "shortId": "AZZ", "name": "AZZ name"}
    assert body["rights"] == {"planner": "RWD", "womaint": "RWD"} and body["isAdmin"] is True
    raw = r.headers["set-cookie"].lower()
    for part in ("httponly", "secure", "samesite=strict", "path=/", f"max-age={12 * 3600}"):
        assert part in raw, part
    token = r.cookies[COOKIE]
    assert list(store.sessions) == [rules.token_hash(token)]
    assert token not in repr(store.sessions) and token not in repr(store.events)
    assert store.events[-1]["event_type"] == "SIGNIN_OK" and store.events[-1]["user_id"] == 21


def test_me_with_and_without_a_session(client: TestClient, store: Store) -> None:
    assert _signin(client, "Azzmax", PASSWORD).status_code == 200
    r = client.get(ME)
    assert r.status_code == 200 and r.json()["user"]["userId"] == 21
    bare = TestClient(app, base_url="https://testserver")
    r = bare.get(ME)
    assert r.status_code == 401 and r.json()["code"] == "NO_IDENTITY"


@pytest.mark.parametrize(
    "login,pw,code",
    [
        ("sys_user", "sys_user", "SYS_USER"),
        ("wmuser", "wm", "DEFAULT_PASSWORD"),
        ("jsmith", "jsmith", "DEFAULT_PASSWORD"),
        ("nogroup", PASSWORD, "NO_GROUP"),
    ],
)
def test_refusals_come_only_after_the_password(client: TestClient, store: Store, login, pw, code) -> None:
    wrong = _signin(client, login, pw + "x")
    assert wrong.status_code == 401 and wrong.json()["code"] == "SIGNIN_FAILED"  # no reason leaks
    r = _signin(client, login, pw)
    assert r.status_code == 403 and r.json()["code"] == code
    assert r.json()["message"] == rules.MESSAGES[code]
    assert store.events[-1]["event_type"] == "SIGNIN_REFUSED" and store.events[-1]["reason"] == code
    assert not store.sessions and COOKIE not in r.cookies


def test_reset_due_when_the_client_turns_the_policy_on(client: TestClient, store: Store) -> None:
    store.policy = {"sec_level": 2, "period_months": 0}
    store.user(34)["Reset_Pwd_flag"] = "1"
    r = _signin(client, "kevin e", PASSWORD)
    assert r.status_code == 403 and r.json()["code"] == "RESET_DUE"


def test_an_inner_space_login_signs_in_with_level_rights(client: TestClient, store: Store) -> None:
    r = _signin(client, "  KEVIN E  ", PASSWORD)
    assert r.status_code == 200 and r.json()["rights"] == {"planner": "RW", "womaint": "RW"}
    assert store.events[-1]["login_typed"] == "KEVIN E" and store.events[-1]["login_key"] == "kevin e"


# ---------------------------------------------------------------------------
# OD-99 lockout
# ---------------------------------------------------------------------------


def test_five_failures_lock_the_login_even_for_the_right_password(client: TestClient, store: Store) -> None:
    for _ in range(5):
        assert _signin(client, "Azzmax", "nope").status_code == 401
    r = _signin(client, "AZZMAX", PASSWORD)
    assert r.status_code == 423 and r.json()["code"] == "LOCKED"
    assert store.events[-1]["event_type"] == "LOCKED" and not store.sessions


def test_a_made_up_login_locks_too(client: TestClient, store: Store) -> None:
    for _ in range(5):
        _signin(client, "ghost", "nope")
    assert _signin(client, "ghost", "nope").status_code == 423


# ---------------------------------------------------------------------------
# OD-97 sessions
# ---------------------------------------------------------------------------


def test_signout_revokes_and_clears(client: TestClient, store: Store) -> None:
    token = _signin(client, "Azzmax", PASSWORD).cookies[COOKIE]
    r = client.post(SIGNOUT, headers=CSRF)
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert store.sessions[rules.token_hash(token)]["Revoked_Utc"] is not None
    assert store.events[-1]["event_type"] == "SIGNOUT"
    client.cookies.set(COOKIE, token)  # a stolen copy of the old cookie is worth nothing now
    assert client.get(ME).status_code == 401
    assert TestClient(app, base_url="https://testserver").post(SIGNOUT, headers=CSRF).status_code == 200


def test_idle_and_deactivated_sessions_end(client: TestClient, store: Store) -> None:
    token = _signin(client, "Azzmax", PASSWORD).cookies[COOKIE]
    h = rules.token_hash(token)
    store.sessions[h]["Last_Seen_Utc"] -= timedelta(hours=5)
    assert client.get(ME).status_code == 401
    assert store.events[-1]["event_type"] == "EXPIRED" and store.events[-1]["reason"] == "idle"

    _signin(client, "Azzmax", PASSWORD)
    assert client.get(ME).status_code == 200
    store.user(21)["Active"] = "N"  # turned off in Workmate.NET mid-session
    assert client.get(ME).status_code == 401
    assert store.events[-1]["reason"] == "inactive"


# ---------------------------------------------------------------------------
# OD-100 gates
# ---------------------------------------------------------------------------


def test_routers_refuse_without_the_page_right(client: TestClient, store: Store) -> None:
    def _no_db() -> Iterator[None]:
        yield None

    app.dependency_overrides[db.get_conn] = _no_db
    app.dependency_overrides[deps.get_principal] = lambda: deps.Principal(
        user_id=99, rights={"planner": "NA", "womaint": "NA"}
    )
    r = client.get("/api/v1/planner/range", params={"from": "2026-11-02", "to": "2026-11-08"})
    assert r.status_code == 403 and r.json()["code"] == "NO_RIGHT"
    r = client.get("/api/v1/workorders")
    assert r.status_code == 403 and r.json()["code"] == "NO_RIGHT"
    app.dependency_overrides[deps.get_principal] = lambda: deps.Principal(
        user_id=99, rights={"planner": "RO", "womaint": "NA"}
    )
    assert client.get("/api/v1/workorders").status_code == 403


def test_diag_routes_are_dev_only_then_admin_only(
    client: TestClient, store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.diag import repo as diag_repo  # noqa: PLC0415 - only this test reaches the diag router

    def _no_db() -> Iterator[None]:
        yield None

    app.dependency_overrides[db.get_conn] = _no_db
    monkeypatch.setattr(diag_repo, "users", lambda conn, minutes_back: [])
    full = {"planner": "RWD", "womaint": "RWD"}
    admin = deps.Principal(user_id=21, rights=full, is_admin=True)
    plain = deps.Principal(user_id=30, rights=full)
    app.dependency_overrides[deps.get_principal] = lambda: admin
    r = client.get("/api/v1/_diag/users")
    assert r.status_code == 404 and r.json()["code"] == "NOT_FOUND"  # not dev: 404, even for an administrator
    monkeypatch.setattr(get_settings(), "env", "dev")
    assert client.get("/api/v1/_diag/users").json() == {"ok": True, "count": 0, "rows": []}
    app.dependency_overrides[deps.get_principal] = lambda: plain
    r = client.get("/api/v1/_diag/users")
    assert r.status_code == 403 and r.json()["code"] == "NO_RIGHT"
    del app.dependency_overrides[deps.get_principal]
    r = client.get("/api/v1/_diag/users")
    assert r.status_code == 401 and r.json()["code"] == "NO_IDENTITY"


def test_a_password_is_never_stored_or_logged(
    client: TestClient, store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    real = diag.log

    def spy(*args, **kwargs):
        calls.append(repr((args, kwargs)))
        return real(*args, **kwargs)

    monkeypatch.setattr(diag, "log", spy)
    _signin(client, "Azzmax", PASSWORD + "-wrong")
    _signin(client, "nogroup", PASSWORD)
    _signin(client, "Azzmax", PASSWORD)
    client.post(SIGNOUT, headers=CSRF)
    for blob in ("\n".join(calls), repr(store.events), repr(store.sessions)):
        assert PASSWORD not in blob
    assert calls, "the spy saw nothing - the test proves nothing"
