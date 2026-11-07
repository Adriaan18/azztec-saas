"""
Azztec_SaaS_test_planner_api_v1_4_0.py  ->  backend/tests/test_planner_api.py
Version:  1.4.0
Author:   Adriaan
Spec:     Azztec_SaaS_S1c_Api_Chunk_Spec_v1_0_0.md §7 · Azztec_SaaS_S1h_Priority_Initials_Chunk_Spec_v1_0_0.md §5.2
          · Azztec_SaaS_S1j_KT_Uplift_Chunk_Spec_v1_0_0.md §3.4 · Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s5
          · Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §5.7 (OD-107, OD-111, OD-112, OD-116)
          Pair of router.py 1.2.0 + service.py 1.1.0 + schemas.py 1.2.0 + deps.py 1.2.0 + main.py 0.7.0.

TestClient over the real app, DB dependency overridden with one RST connection inside a transaction that is
rolled back (D-10), principal dependency overridden (DP2a: deps.get_principal, which get_current_actor and
the router's planner gate both read). Standing window 2026-09-14..2026-09-20 (Raw Log 2026-09-11 §5). Zero
skips - every assertion is written to hold on dbWorkmate as restored (and on dbWorkmate_DP1_Test, the
fresh copy of the same backup).

Twenty tests from spec §7 plus one for the [F] line (§9 acceptance), plus five from S1h §5.2 (priority
colour), plus one DP2a gate. Without the override no cookie reaches the app, so the request is a 401 by
design (§7.4 #19).
Assumes the database after migration 0001 (S1j): #12 asserts pinTable is True. Since DP3 a move can pin a
PM, so #12 no longer asserts an empty pin table - it asserts what every pin row must look like.

DP3a adds the move routes (GET /preview, POST /move, POST /undo). THIS FILE NEVER WRITES (OD-111): an autouse
tripwire replaces every function in repo.WRITERS with one that records the call and raises, and every test
fails if anything reached it. Every move request here is either dryRun:true or one the service refuses
before its first write (404, 409, 422, CONFIRM, 403); the write itself is proven by DP3a's smoke on
dbWorkmate_DP1_Test. The WOs are chosen by query on the rolled-back connection, never by a pinned id, and
the target days come from the configured "today".

Changelog:
  1.4.0  DP3a. The tripwire; nineteen move-route test functions, 24 cases (the tripwire's own reach, dry
         plans for move and undo, the refusals over HTTP, CONFIRM's 200, the RW and CSRF gates, /preview,
         the code -> status map through a fake service, contract drift, the [F] line, a body that carries
         an unknown key). test_range_pin_table_true_after_0001
         keeps pinTable True and every engine-owned PM movable, and swaps "every row unpinned" for what a pin
         row must carry (Pinned implies Prev_Start and Pinned_On) - the edit 1.2.0 said S2 would own.
  1.3.0  DP2a. The fixture overrides deps.get_principal with an RWD principal for actor 1 instead of
         deps.get_current_actor (the planner router now sits behind require('planner', 'RO'), which
         reads the principal). test_range_401_without_actor pops that override - same 401 NO_IDENTITY.
         New: test_range_403_without_the_planner_right. Nothing else changed.
  1.2.0  S1j (OD-44). The OD-1 trip-wire flipped deliberately: test_range_pin_table_false_on_rst
         -> test_range_pin_table_true_after_0001. pinTable is True on RST once WO_N_Plan exists;
         with the table empty every row is still unpinned, and every engine-owned PM now reads
         locked False / movable True unless its status is C or D (repo._wo_dict, rules._LOCKED_STATUSES).
         Header: router.py 1.1.1, main.py 0.4.0. Nothing else changed - still zero skips.
  1.1.0  S1h. Five priority-colour tests (item 29 / OD-36); apiVersion and
         libVersion assertions needed no edit, they read the module constants
         (OD-37). Deliberately NO assertion on the number of priority rows, and
         none on the order being non-alphabetical: seven rows is one database's
         Active state on one day, and KT's A B C D order IS alphabetical, so
         both would fire on correct data. Row order is checked against a control
         query instead.
  1.0.1  S1d instrument migration, assertions unchanged. diag.py 1.1.0 sets propagate=False on
         'workmate.diag' (OD-18), so caplog - whose handler sits on root - no longer sees the record.
         test_range_forensic_line_once reads capfd instead, which is the stronger test anyway: caplog
         proved diag.log() was CALLED, capfd proves the line reached stdout. `import logging` dropped,
         `import json` added.
  1.0.0  Initial S1c.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Connection

os.environ.setdefault("WORKMATE_ENV", "test")

from app.core import db, deps  # noqa: E402 - after env is set
from app.core.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.planner import repo, rules, service  # noqa: E402
from app.planner import router as planner_router  # noqa: E402
from app.planner.schemas import Priority  # noqa: E402 - after env is set

RANGE = "/api/v1/planner/range"
PREVIEW = "/api/v1/planner/preview"
MOVE = "/api/v1/planner/move"
UNDO = "/api/v1/planner/undo"
CSRF = {"X-Azztec-Request": "1"}
FROM, TO = "2026-09-14", "2026-09-20"
ACTOR = 1  # only echoed as `actor` here; nothing in this file writes (OD-111)
PRINCIPAL = deps.Principal(user_id=ACTOR, rights={"planner": "RWD", "womaint": "RWD"})

CONTRACT_KEYS = frozenset(
    {
        "from", "to", "today", "wos", "labour", "workers", "teams", "priorities", "colours", "weeks",
        "load", "counts", "pinTable", "workerWeeks", "uomHours", "libVersion",
        "ok", "apiVersion", "actor", "ms",  # OD-14 envelope, no gate
    }
)  # fmt: skip


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def conn() -> Iterator[Connection]:
    repo.clear_caches()  # test order must not decide what hours_uom_id / pin_table_exists cached
    with db.get_engine().connect() as c:
        tx = c.begin()
        try:
            yield c
        finally:
            tx.rollback()


@pytest.fixture(scope="module")
def client(conn: Connection) -> Iterator[TestClient]:
    def _conn() -> Iterator[Connection]:
        yield conn

    app.dependency_overrides[db.get_conn] = _conn
    app.dependency_overrides[deps.get_principal] = lambda: PRINCIPAL
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def body(client: TestClient) -> dict:
    r = client.get(RANGE, params={"from": FROM, "to": TO})
    assert r.status_code == 200, r.text
    return r.json()


TRIPPED: list[str] = []


@pytest.fixture(autouse=True)
def tripwire(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """OD-111: every repo writer records the call and raises, so nothing is written, and the test that
    reached one fails here even if its own assertions passed."""
    TRIPPED.clear()

    def _make(name: str):
        def _tripped(*args, **kwargs):
            TRIPPED.append(name)
            raise AssertionError(f"tripwire: a test reached repo.{name}")

        return _tripped

    for name in repo.WRITERS:
        monkeypatch.setattr(repo, name, _make(name))
    yield
    assert not TRIPPED, f"a test tried to write: {TRIPPED}"


# An open, non-PM, not-Active work order whose planned labour sits on at most one day: moving it to a
# future day asks nothing (SPAN alone never asks - OD-116), so a dry run comes back ok.
OPEN_PLAIN_WO = """
SELECT h.WO_ID
  FROM dbo.WO_N_Header h
 WHERE RTRIM(COALESCE(h.Status, '')) NOT IN ('C', 'D', 'V')
   AND RTRIM(COALESCE(h.WO_Type_Flag, '')) <> 'M'
   AND h.Request_Start_Date IS NOT NULL
   AND (SELECT COUNT(DISTINCT r.Res_Date) FROM dbo.WO_N_Resource r
         WHERE r.WO_Id = h.WO_ID AND RTRIM(COALESCE(r.Resource_Type, '')) = 'L'
           AND r.Res_Date IS NOT NULL) <= 1
 ORDER BY h.WO_ID DESC
OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY
"""

CLOSED_WO = """
SELECT h.WO_ID
  FROM dbo.WO_N_Header h
 WHERE RTRIM(COALESCE(h.Status, '')) = 'C'
   AND h.Request_Start_Date IS NOT NULL
 ORDER BY h.WO_ID DESC
OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY
"""


@pytest.fixture(scope="module")
def plain(conn: Connection) -> dict:
    wo_id = db.scalar(conn, OPEN_PLAIN_WO)
    assert wo_id, "no open, non-PM, not-Active WO with planned labour on at most one day"
    wo = repo.load_wo(conn, int(wo_id))
    assert wo is not None
    return {"id": wo["id"], "sid": wo["sid"], "start": wo["start"]}


@pytest.fixture(scope="module")
def closed_id(conn: Connection) -> int:
    wo_id = db.scalar(conn, CLOSED_WO)
    assert wo_id, "no closed WO with a start date"
    return int(wo_id)


def _day(offset: int, avoid: str) -> str:
    """today + offset days in the configured zone, one further if that is the WO's own start."""
    d = date.fromisoformat(service.today_iso()) + timedelta(days=offset)
    if rules.iso(d) == avoid:
        d += timedelta(days=1 if offset >= 0 else -1)
    return rules.iso(d)


# ---------------------------------------------------------------------------
# §7.2 contract
# ---------------------------------------------------------------------------


def test_range_200_shape_on_standing_window(body: dict) -> None:
    assert body["from"] == FROM and body["to"] == TO
    assert body["counts"]["total"] > 0, "standing window is dense (Raw Log 2026-09-11 §5)"
    assert isinstance(body["wos"], list) and isinstance(body["labour"], list)
    assert isinstance(body["workers"], list) and isinstance(body["teams"], list)
    assert body["colours"] == {"DONE": "#81C784", "PM": "#4DD0E1", "REQ": "#F48FB1", "WO": "#FFC65C"}


def test_range_keys_match_contract(body: dict) -> None:
    assert set(body.keys()) == CONTRACT_KEYS, sorted(set(body.keys()) ^ CONTRACT_KEYS)
    assert "gate" not in body


def test_range_from_key_is_literal_from(body: dict) -> None:
    assert "from" in body
    assert "from_" not in body


def test_range_lib_version_is_rules_version(body: dict) -> None:
    assert body["libVersion"] == rules.__version__
    assert rules.PORTED_FROM == "workmate.planner 1.3.1"


def test_range_envelope(body: dict) -> None:
    assert body["ok"] is True
    assert body["apiVersion"] == planner_router.__version__
    assert body["actor"] == ACTOR
    assert isinstance(body["ms"], int) and body["ms"] >= 0


# ---------------------------------------------------------------------------
# §7.3 data behaviour
# ---------------------------------------------------------------------------


def test_range_counts_are_consistent(body: dict) -> None:
    c = body["counts"]
    cats = [w["cat"] for w in body["wos"]]
    assert c["total"] == len(body["wos"])
    assert c["wo"] == sum(1 for x in cats if x in ("WO", "REQ"))
    assert c["pm"] == sum(1 for x in cats if x == "PM")
    assert c["done"] == sum(1 for x in cats if x == "DONE")
    assert c["wo"] + c["pm"] + c["done"] == c["total"]


def test_range_today_is_configured_tz(body: dict) -> None:
    expect = datetime.now(ZoneInfo(get_settings().tz)).date().isoformat()
    assert body["today"] == expect


def test_range_load_keys_are_strings(body: dict) -> None:
    assert body["load"], "window has labour or estimates"
    assert all(isinstance(k, str) for k in body["load"])
    assert all(isinstance(v, int | float) for v in body["load"].values())


def test_range_worker_weeks_keys_are_strings(body: dict) -> None:
    for k, rows in body["workerWeeks"].items():
        assert isinstance(k, str)
        assert all(r["flag"] in ("over", "ok", "under", "empty") for r in rows)


def test_range_weeks_cover_window(body: dict) -> None:
    f, t = date.fromisoformat(FROM), date.fromisoformat(TO)
    weeks = body["weeks"]
    assert weeks
    w0 = date.fromisoformat(weeks[0]["weekStart"])
    assert w0.weekday() == 0 and w0 <= f and (f - w0).days < 7
    assert date.fromisoformat(weeks[-1]["weekStart"]) <= t
    assert sum(w["count"] for w in weeks) == body["counts"]["total"]


def test_range_by_wo_index_matches_full_scan(body: dict) -> None:
    """Spec §3.3: the per-WO labour subset must give exactly what the Ignition full-list scan gives."""
    full = body["labour"]
    for wo in body["wos"]:
        h, src = rules.hoursFor(wo, full)
        assert (wo["hrs"], wo["hrsSrc"]) == (h, src), wo["id"]
        assert wo["assigned"] == rules.assignedFor(wo, full), wo["id"]


def test_range_pin_table_true_after_0001(body: dict) -> None:
    """OD-1's end state (OD-44). Assumes the database after migration 0001: the table exists, so pinTable is
    True and engine-owned PMs are movable-with-pin. Red before 0001 by design. Since DP3 a move pins a PM
    (OD-114), so the table need not be empty: a pinned row carries the date it was pinned from and when."""
    assert body["pinTable"] is True, "WO_N_Plan missing: alembic upgrade head has not run"
    for w in body["wos"]:
        if w["pinned"]:
            assert w["engineDate"] and w["pinnedOn"], w["id"]
    pms = [w for w in body["wos"] if w["engineOwned"]]
    assert pms, "standing window carries engine-owned PMs (Raw Log 2026-09-11 §5)"
    for w in pms:
        assert w["locked"] is False, w["id"]
        assert w["movable"] is (w["status"] not in rules._LOCKED_STATUSES), w["id"]


# ---------------------------------------------------------------------------
# §7.4 guards and routing
# ---------------------------------------------------------------------------


def _assert_bad_window(r) -> None:
    assert r.status_code == 400, r.text
    b = r.json()
    assert b["ok"] is False and b["code"] == "BAD_WINDOW"
    assert isinstance(b["message"], str) and b["message"]
    assert "error" not in b  # flat (OD-15), not the nested Ignition shape


def test_range_bad_iso_is_400(client: TestClient) -> None:
    _assert_bad_window(client.get(RANGE, params={"from": "2026-02-31", "to": TO}))


def test_range_reversed_window_is_400(client: TestClient) -> None:
    _assert_bad_window(client.get(RANGE, params={"from": TO, "to": FROM}))


def test_range_exactly_400_days_is_200(client: TestClient) -> None:
    r = client.get(RANGE, params={"from": "2025-09-14", "to": "2026-10-19"})
    assert r.status_code == 200, r.text
    assert r.json()["counts"]["total"] > 0


def test_range_401_days_is_400(client: TestClient) -> None:
    _assert_bad_window(client.get(RANGE, params={"from": "2025-09-14", "to": "2026-10-20"}))


def test_range_missing_params_is_422(client: TestClient) -> None:
    assert client.get(RANGE, params={"from": FROM}).status_code == 422
    assert client.get(RANGE).status_code == 422


def test_range_post_is_405(client: TestClient) -> None:
    r = client.post(RANGE, json={"from": FROM, "to": TO})
    assert r.status_code == 405
    b = r.json()
    assert b["ok"] is False and b["code"] == "METHOD_NOT_ALLOWED"


def test_range_401_without_actor(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKMATE_ENV", "test")
    get_settings.cache_clear()
    saved = app.dependency_overrides.pop(deps.get_principal)
    try:
        r = client.get(RANGE, params={"from": FROM, "to": TO})
    finally:
        app.dependency_overrides[deps.get_principal] = saved
        get_settings.cache_clear()
    assert r.status_code == 401, r.text
    b = r.json()
    assert b["ok"] is False and b["code"] == "NO_IDENTITY"


def test_range_403_without_the_planner_right(client: TestClient) -> None:
    """DP2a (OD-100): the router-level gate answers before the route runs."""
    saved = app.dependency_overrides[deps.get_principal]
    app.dependency_overrides[deps.get_principal] = lambda: deps.Principal(
        user_id=ACTOR, rights={"planner": "NA", "womaint": "RWD"}
    )
    try:
        r = client.get(RANGE, params={"from": FROM, "to": TO})
    finally:
        app.dependency_overrides[deps.get_principal] = saved
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "NO_RIGHT"


def test_range_response_model_rejects_drift(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """extra="forbid": a key the service adds must be a loud 500, never silently dropped."""
    real = planner_router.service.range_data

    def drifted(conn, f, t):
        d = real(conn, f, t)
        d["gate"] = True
        return d

    monkeypatch.setattr(planner_router.service, "range_data", drifted)
    r = client.get(RANGE, params={"from": FROM, "to": TO})
    assert r.status_code == 500
    assert r.json()["code"] == "INTERNAL"


# ---------------------------------------------------------------------------
# §9 acceptance - one [F] line per request, Ignition text
# ---------------------------------------------------------------------------


def test_range_forensic_line_once(client: TestClient, capfd: pytest.CaptureFixture[str]) -> None:
    """capfd, not caplog (S1d OD-18). diag.py 1.1.0 sets propagate=False, so caplog's root handler sees
    nothing - and caplog only ever proved diag.log() was CALLED. This proves the line reached stdout.
    The middleware's own outcome line is in the same capture but carries no `rows=`, so the count holds."""
    r = client.get(RANGE, params={"from": FROM, "to": TO})
    assert r.status_code == 200
    lines = [x.strip() for x in capfd.readouterr().out.splitlines() if x.strip().startswith("{")]
    hits = [json.loads(x)["message"] for x in lines if f"range {FROM}..{TO} rows=" in x]
    assert len(hits) == 1, hits
    assert "labour=" in hits[0] and "workers=" in hits[0] and "pinTable=" in hits[0] and " ms" in hits[0]


# ---------------------------------------------------------------------------
# S1h - priority colour on the wire (item 29 / OD-36)
# ---------------------------------------------------------------------------


def test_range_priorities_all_carry_a_colour(body: dict) -> None:
    assert body["priorities"], "no active priorities"
    for p in body["priorities"]:
        assert "colour" in p, p
        assert isinstance(p["colour"], str), p


def test_range_priority_colour_is_actually_read(body: dict) -> None:
    """Guards the difference between reading the column and defaulting it. Every
    colour coming back '' would satisfy the type test above and mean the SELECT
    lost the column - as it would on a typo'd alias."""
    assert any(p["colour"] for p in body["priorities"])


def test_range_priority_colour_matches_the_table(body: dict, conn: Connection) -> None:
    """OD-36: the API ships what the column holds, no default, no validation.
    Control query, so it still means something pointed at the KT dev copy -
    where every row legitimately carries the same colour."""
    control = {
        r["Priority_Id"]: (r["Colour"] or "")
        for r in db.rows(
            conn,
            "SELECT Priority_Id, RTRIM(COALESCE(Colour, '')) AS Colour FROM dbo.Priority "
            "WHERE RTRIM(COALESCE(Active, '')) NOT IN ('0', 'N')",
        )
    }
    assert control, "no active priorities in the table"
    for p in body["priorities"]:
        assert p["colour"] == control[p["id"]], p


def test_range_priority_order_survives_the_whole_chain(body: dict, conn: Connection) -> None:
    """Contract order is Sort_Sequence then Priority_Id (OD-11). repo's own test
    asserts that at the mapper; this asserts it at the wire, so the chain
    repo -> service -> schema -> JSON cannot quietly reorder it.

    Control query, not a hard-coded list: on RST the order is P2 P1 P3 P5 P6 P4
    N/A, which is NOT alphabetical, but on the KT copy it is A B C D, which is -
    so an 'order is not alphabetical' trip-wire would fire on correct data
    there. Compare against the table instead."""
    control = [
        r["Priority_Id"]
        for r in db.rows(
            conn,
            "SELECT Priority_Id FROM dbo.Priority "
            "WHERE RTRIM(COALESCE(Active, '')) NOT IN ('0', 'N') "
            "ORDER BY Sort_Sequence, Priority_Id",
        )
    ]
    assert [p["id"] for p in body["priorities"]] == control


def test_priority_model_takes_colour_and_still_forbids_extras() -> None:
    from pydantic import ValidationError  # noqa: PLC0415 - local to the one test that needs it

    ok = Priority(id=1, short="P2", title="Priority 2", colour="#FF9F40")
    assert ok.colour == "#FF9F40"
    assert Priority(id=6, short="N/A", title="Not Applicable", colour="").colour == ""
    with pytest.raises(ValidationError):
        Priority(id=1, short="P2", title="Priority 2", colour="#FF9F40", rank=1)
    with pytest.raises(ValidationError):
        Priority(id=1, short="P2", title="Priority 2")


# ---------------------------------------------------------------------------
# DP3a - the move routes. Nothing here writes: dryRun:true, or refused before the first write.
# ---------------------------------------------------------------------------

MOVE_RESULT_KEYS = frozenset(
    {
        "ok", "dryRun", "woId", "sid", "prevStart", "prevEnd", "newStart", "newEnd", "delta", "weekNo",
        "prevWeekNo", "subtasks", "labourRows", "reasons", "events", "willPin", "willUnpin", "pinned",
        "engineDate", "undo", "actor",
    }
)  # fmt: skip

MOVE_PREVIEW_KEYS = frozenset(
    {
        "ok", "code", "message", "confirm", "reasons", "delta", "newStart", "newEnd", "willPin", "willUnpin",
        "pinnedAfter", "woId", "sid", "title", "status", "statusTitle", "prevStart", "prevEnd", "subtasks",
        "labourDates", "labourMoves",
    }
)  # fmt: skip


def test_tripwire_covers_every_writer() -> None:
    for name in repo.WRITERS:
        assert getattr(repo, name).__name__ == "_tripped", name


def test_move_dry_run_plans_and_writes_nothing(client: TestClient, plain: dict) -> None:
    to = _day(14, plain["start"])
    body = {"woId": plain["id"], "toIso": to, "expectStartIso": plain["start"], "dryRun": True}
    r = client.post(MOVE, json=body, headers=CSRF)
    assert r.status_code == 200, r.text
    b = r.json()
    assert set(b) == MOVE_RESULT_KEYS, sorted(set(b) ^ MOVE_RESULT_KEYS)
    assert b["ok"] is True and b["dryRun"] is True and b["events"] == 0
    assert b["actor"] == ACTOR and b["sid"] == plain["sid"]
    assert b["prevStart"] == plain["start"] and b["newStart"] == to
    assert b["undo"] == {"woId": plain["id"], "toIso": plain["start"], "expectStartIso": to}
    assert "PAST" not in [x["code"] for x in b["reasons"]]


def test_undo_dry_run(client: TestClient, plain: dict) -> None:
    body = {
        "woId": plain["id"],
        "toIso": _day(14, plain["start"]),
        "expectStartIso": plain["start"],
        "dryRun": True,
    }
    r = client.post(UNDO, json=body, headers=CSRF)
    assert r.status_code == 200, r.text
    assert r.json()["dryRun"] is True and set(r.json()) == MOVE_RESULT_KEYS


def test_move_to_a_past_day_is_a_200_confirm_with_a_preview(client: TestClient, plain: dict) -> None:
    """PAST still asks (OD-116); CONFIRM comes back before the first write, so no dryRun is needed."""
    r = client.post(MOVE, json={"woId": plain["id"], "toIso": _day(-30, plain["start"])}, headers=CSRF)
    assert r.status_code == 200, r.text
    b = r.json()
    assert set(b) == {"ok", "code", "message", "rid", "sid", "preview"}
    assert b["ok"] is False and b["code"] == "CONFIRM" and b["sid"] == plain["sid"]
    assert set(b["preview"]) == MOVE_PREVIEW_KEYS
    assert b["preview"]["confirm"] is True
    assert "PAST" in [x["code"] for x in b["preview"]["reasons"]]


def test_move_stale_is_409_with_the_current_start(client: TestClient, plain: dict) -> None:
    body = {"woId": plain["id"], "toIso": _day(14, plain["start"]), "expectStartIso": "1999-01-01"}
    r = client.post(MOVE, json=body, headers=CSRF)
    assert r.status_code == 409, r.text
    b = r.json()
    assert b["ok"] is False and b["code"] == "STALE"
    assert b["currentStart"] == plain["start"] and b["sid"] == plain["sid"] and b["rid"]
    assert "error" not in b  # flat (OD-15), not the nested Ignition shape


def test_move_to_its_own_day_is_422_no_change(client: TestClient, plain: dict) -> None:
    r = client.post(MOVE, json={"woId": plain["id"], "toIso": plain["start"]}, headers=CSRF)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "NO_CHANGE"


def test_move_to_a_calendar_invalid_day_is_422_bad_date(client: TestClient, plain: dict) -> None:
    r = client.post(MOVE, json={"woId": plain["id"], "toIso": "2026-02-31"}, headers=CSRF)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "BAD_DATE"


def test_move_closed_is_422_locked_status(client: TestClient, closed_id: int) -> None:
    r = client.post(MOVE, json={"woId": closed_id, "toIso": "2030-01-07"}, headers=CSRF)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "LOCKED_STATUS"


def test_move_unknown_is_404(client: TestClient) -> None:
    r = client.post(MOVE, json={"woId": 999999999, "toIso": "2030-01-07"}, headers=CSRF)
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "NOT_FOUND"


def test_move_without_the_csrf_header_is_403(client: TestClient, plain: dict) -> None:
    r = client.post(MOVE, json={"woId": plain["id"], "toIso": _day(14, plain["start"]), "dryRun": True})
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "CSRF"


def test_move_and_undo_need_rw_preview_does_not(client: TestClient, plain: dict) -> None:
    """OD-107: the router's RO gate lets a read-only planner in; the two writes need RW on top."""
    saved = app.dependency_overrides[deps.get_principal]
    app.dependency_overrides[deps.get_principal] = lambda: deps.Principal(
        user_id=ACTOR, rights={"planner": "RO", "womaint": "RO"}
    )
    to = _day(14, plain["start"])
    try:
        writes = [
            client.post(path, json={"woId": plain["id"], "toIso": to, "dryRun": True}, headers=CSRF)
            for path in (MOVE, UNDO)
        ]
        read = client.get(PREVIEW, params={"woId": plain["id"], "to": to})
    finally:
        app.dependency_overrides[deps.get_principal] = saved
    for r in writes:
        assert r.status_code == 403, r.text
        assert r.json()["code"] == "NO_RIGHT"
    assert read.status_code == 200, read.text


def test_move_body_with_an_unknown_key_is_refused(client: TestClient, plain: dict) -> None:
    body = {"woId": plain["id"], "toIso": _day(14, plain["start"]), "dryRun": True, "bogus": 1}
    assert client.post(MOVE, json=body, headers=CSRF).status_code == 422  # extra="forbid", FastAPI's own


def test_move_wo_id_must_be_positive(client: TestClient) -> None:
    assert client.post(MOVE, json={"woId": 0, "toIso": "2030-01-07"}, headers=CSRF).status_code == 422


def test_preview_200(client: TestClient, plain: dict) -> None:
    to = _day(14, plain["start"])
    r = client.get(PREVIEW, params={"woId": plain["id"], "to": to})
    assert r.status_code == 200, r.text
    b = r.json()
    assert set(b) == MOVE_PREVIEW_KEYS, sorted(set(b) ^ MOVE_PREVIEW_KEYS)
    assert b["ok"] is True and b["newStart"] == to and b["prevStart"] == plain["start"]
    assert b["confirm"] is False, b["reasons"]  # a future day; SPAN alone never asks (OD-116)
    assert all(set(m) == {"from", "to", "rows"} for m in b["labourMoves"])


def test_preview_refusals_are_flat(client: TestClient, closed_id: int) -> None:
    r = client.get(PREVIEW, params={"woId": 999999999, "to": "2030-01-07"})
    assert r.status_code == 404 and r.json()["code"] == "NOT_FOUND"
    r = client.get(PREVIEW, params={"woId": closed_id, "to": "2030-01-07"})
    assert r.status_code == 422 and r.json()["code"] == "LOCKED_STATUS"
    assert set(r.json()) == {"ok", "code", "message", "rid", "sid", "currentStart"}


def test_preview_missing_params_is_422(client: TestClient) -> None:
    assert client.get(PREVIEW, params={"woId": 1}).status_code == 422
    assert client.get(PREVIEW, params={"to": "2030-01-07"}).status_code == 422


@pytest.mark.parametrize(
    ("code", "status"),
    [
        ("WRITE_FAILED", 500),
        ("INTERNAL", 500),
        ("NO_IDENTITY", 403),
        ("BAD_REQUEST", 400),
        ("ENGINE_OWNED", 422),
        ("NO_START", 422),
    ],
)
def test_move_code_to_status_map(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, code: str, status: int
) -> None:
    """The oracle's _CODE_HTTP for the codes the live database cannot produce on demand."""

    def fake(*args, **kwargs) -> dict:
        return {"ok": False, "code": code, "sid": "X-1", "message": "m"}

    monkeypatch.setattr(planner_router.service, "move_wo", fake)
    r = client.post(MOVE, json={"woId": 1, "toIso": "2030-01-07"}, headers=CSRF)
    assert r.status_code == status, r.text
    b = r.json()
    assert b == {"ok": False, "code": code, "message": "m", "rid": b["rid"], "sid": "X-1", "currentStart": ""}


def test_move_result_drift_is_a_500(client: TestClient, monkeypatch: pytest.MonkeyPatch, plain: dict) -> None:
    """extra="forbid": a key the service adds must be a loud 500, never silently dropped."""
    real = service.move_wo

    def drifted(*args, **kwargs) -> dict:
        d = real(*args, **kwargs)
        d["gate"] = True
        return d

    monkeypatch.setattr(planner_router.service, "move_wo", drifted)
    body = {"woId": plain["id"], "toIso": _day(14, plain["start"]), "dryRun": True}
    r = client.post(MOVE, json=body, headers=CSRF)
    assert r.status_code == 500
    assert r.json()["code"] == "INTERNAL"


def test_move_forensic_line_once(client: TestClient, capfd: pytest.CaptureFixture[str], plain: dict) -> None:
    """The oracle's _diagWrite text, once, with the dry-run label (OD-111). capfd, as the range test."""
    body = {"woId": plain["id"], "toIso": _day(14, plain["start"]), "dryRun": True}
    r = client.post(MOVE, json=body, headers=CSRF)
    assert r.status_code == 200, r.text
    lines = [x.strip() for x in capfd.readouterr().out.splitlines() if x.strip().startswith("{")]
    hits = [json.loads(x)["message"] for x in lines if f"move (dry run) {plain['sid']} " in x]
    assert len(hits) == 1, hits
    assert f"{plain['start']} -> " in hits[0] and hits[0].endswith("events=0")
