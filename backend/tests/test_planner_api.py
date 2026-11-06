"""
Azztec_SaaS_test_planner_api_v1_3_0.py  ->  backend/tests/test_planner_api.py
Version:  1.3.0
Author:   Adriaan
Spec:     Azztec_SaaS_S1c_Api_Chunk_Spec_v1_0_0.md §7 · Azztec_SaaS_S1h_Priority_Initials_Chunk_Spec_v1_0_0.md §5.2
          · Azztec_SaaS_S1j_KT_Uplift_Chunk_Spec_v1_0_0.md §3.4 · Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s5
          Pair of router.py 1.1.1 + service.py 1.0.1 + schemas.py 1.1.0 + deps.py 1.2.0 + main.py 0.6.0.

TestClient over the real app, DB dependency overridden with one RST connection inside a transaction that is
rolled back (D-10), principal dependency overridden (DP2a: deps.get_principal, which get_current_actor and
the router's planner gate both read). Standing window 2026-09-14..2026-09-20 (Raw Log 2026-09-11 §5). Zero
skips - every assertion is written to hold on dbWorkmate as restored (and on dbWorkmate_DP1_Test, the
fresh copy of the same backup).

Twenty tests from spec §7 plus one for the [F] line (§9 acceptance), plus five from S1h §5.2 (priority
colour), plus one DP2a gate. Without the override no cookie reaches the app, so the request is a 401 by
design (§7.4 #19).
Assumes the database after migration 0001 (S1j): #12 asserts pinTable is True with the pin table EMPTY - OD-1
in its intended end state. After S2 pins a row the "every row unpinned" half moves (S2 owns that edit).

Changelog:
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
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Connection

os.environ.setdefault("WORKMATE_ENV", "test")

from app.core import db, deps  # noqa: E402 - after env is set
from app.core.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.planner import repo, rules  # noqa: E402
from app.planner import router as planner_router  # noqa: E402
from app.planner.schemas import Priority  # noqa: E402 - after env is set

RANGE = "/api/v1/planner/range"
FROM, TO = "2026-09-14", "2026-09-20"
ACTOR = 1  # only echoed as `actor` here; the write slices stamp real people
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
    """OD-1's end state (OD-44). Assumes dbWorkmate after migration 0001 with WO_N_Plan EMPTY: the table
    exists, so pinTable is True and engine-owned PMs are movable-with-pin; nothing has pinned yet, so
    every row is still unpinned. Red before 0001 by design. S2 edits the second half when it pins."""
    assert body["pinTable"] is True, "WO_N_Plan missing: alembic upgrade head has not run"
    assert all(w["pinned"] is False and w["engineDate"] == "" and w["pinnedOn"] == "" for w in body["wos"])
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
