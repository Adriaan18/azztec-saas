"""
Azztec_SaaS_test_diag_persist_v1_0_0.py  ->  backend/tests/test_diag_persist.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_D1a_Persist_Chunk_Spec_v1_0_0.md §5 · pair of app/core/diag.py 1.2.0

ZERO DB. Nothing here opens a connection: the writer thread is never started, so every row a test
"persists" lands in the queue and is read back with diag.take_queued(). That is deliberate - the queue
is the boundary this file owns, and the round trip to the table is test_diag_trail.py's job.

The first case is the one that matters most for everything already shipped: 1.2.0 must not change the
console line. test_diag_wiring.py 1.0.1 pins its shape from the outside; this pins its keys.

Changelog:
  1.0.0  Initial D1a. 14 cases.
"""

from __future__ import annotations

import json
import os

import pytest

from app.core import diag

os.environ.setdefault("WORKMATE_ENV", "test")

TEST_VERSION = "1.0.0"

INSERT_BINDS = {"session_id", "wm_user_id", "site_code", "source", "tier", "msg_level", "message", "detail"}


@pytest.fixture(autouse=True)
def isolate():
    """Every case starts with an empty queue, no de-dupe history and zeroed counters."""
    saved = diag.PERSIST_SQL
    diag.PERSIST_SQL = None
    diag.take_queued()
    diag.clear_dedupe()
    diag.reset_counters()
    diag.configure(level="INFO")
    yield
    diag.PERSIST_SQL = saved
    diag.take_queued()
    diag.clear_dedupe()
    diag.reset_counters()


def _persisting() -> None:
    """Switch persistence on without a database - the queue is as far as a test goes."""
    diag.PERSIST_SQL = "INSERT INTO dbo.Diag_Log (Message) VALUES (:message)"


# 1
def test_version_and_console_line_unchanged(capfd: pytest.CaptureFixture[str]) -> None:
    assert diag.__version__ == "1.2.0"
    diag.log("F", "hello", detail={"a": 1}, actor=21, source="main", request_id="abc123")
    out = capfd.readouterr().out.strip().splitlines()
    assert len(out) == 1
    rec = json.loads(out[0])
    assert set(rec) == {"ts", "tag", "source", "message", "detail", "actor", "rid"}
    assert rec["tag"] == "[F]" and rec["message"] == "hello" and rec["actor"] == 21 and rec["rid"] == "abc123"


# 2
def test_record_maps_tier_and_level() -> None:
    assert [diag.record(t, "m")["tier"] for t in ("F", "G", "E", "S")] == ["F", "G", "E", "S"]
    assert [diag.record(t, "m")["msg_level"] for t in ("F", "G", "E", "S")] == [
        "info",
        "warn",
        "error",
        "info",
    ]
    assert diag.record("?", "m")["tier"] == "F"  # an unknown tag is forensic, never a failed row


# 3
def test_record_cuts_every_field_to_its_column() -> None:
    row = diag.record("F", "m" * 5000, source="s" * 200, request_id="r" * 200)
    assert len(row["message"]) == diag.MSG_MAX == 1000  # nvarchar(1000), not the 2000 BYTES sys.columns says
    assert len(row["source"]) == 64
    assert len(row["session_id"]) == 64
    assert set(row) == INSERT_BINDS


# 4
def test_actor_zero_is_null_and_a_real_id_survives() -> None:
    assert diag.record("F", "m", actor=0)["wm_user_id"] is None  # 0 is not a Users.User_Id
    assert diag.record("F", "m", actor=21)["wm_user_id"] == 21
    assert diag.record("F", "m")["site_code"] is None


# 5
def test_detail_is_json_and_capped() -> None:
    row = diag.record("E", "boom", detail={"trace": "x" * 20000})
    assert isinstance(row["detail"], str)
    assert len(row["detail"]) <= diag.DETAIL_MAX
    assert diag.record("F", "m", detail=None)["detail"] is None


# 6
def test_redact_hides_secrets_at_any_depth_and_leaves_the_rest() -> None:
    src = {
        "user": "azzmax",
        "Password": "hunter2",
        "nested": [{"api_key": "k", "rows": 3}],
        "headers": {"Authorization": "Bearer x", "accept": "json"},
    }
    out = diag.redact(src)
    assert out["Password"] == diag.REDACTED
    assert out["nested"][0]["api_key"] == diag.REDACTED
    assert out["headers"]["Authorization"] == diag.REDACTED
    assert out["user"] == "azzmax" and out["nested"][0]["rows"] == 3 and out["headers"]["accept"] == "json"
    assert "hunter2" not in json.dumps(out)


# 7
def test_blocks_and_crashes_never_dedupe_but_forensic_lines_do() -> None:
    for tier in ("G", "E"):
        assert diag.should_persist(tier, 21, "app", "same line") is True
        assert diag.should_persist(tier, 21, "app", "same line") is True
    assert diag.should_persist("F", 21, "app", "range 2026-09-01") is True
    assert diag.should_persist("F", 21, "app", "range 2026-09-01") is False
    assert diag.should_persist("F", 22, "app", "range 2026-09-01") is True  # a different person is a row
    assert diag.should_persist("F", 21, "planner", "range 2026-09-01") is True  # so is a different source


# 8
def test_dedupe_ignores_timings_but_not_the_window() -> None:
    assert diag.should_persist("F", 21, "app", "range 2026-08-31..2026-10-04 rows=1191 in 509 ms") is True
    assert diag.should_persist("F", 21, "app", "range 2026-08-31..2026-10-04 rows=1191 in 237 ms") is False
    assert diag.should_persist("F", 21, "app", "range 2026-09-07..2026-09-13 rows=200 in 240 ms") is True


# 9
def test_dedupe_false_always_persists() -> None:
    assert diag.should_persist("F", 21, "app", "wo 123 saved", dedupe=False) is True
    assert diag.should_persist("F", 21, "app", "wo 123 saved", dedupe=False) is True


# 10
def test_log_queues_only_when_persistence_is_on() -> None:
    diag.log("F", "off", actor=21)
    assert diag.take_queued() == []
    _persisting()
    diag.log("F", "on", actor=21, request_id="rid1")
    queued = diag.take_queued()
    assert len(queued) == 1
    assert (
        queued[0]["message"] == "on" and queued[0]["wm_user_id"] == 21 and queued[0]["session_id"] == "rid1"
    )


# 11
def test_overflow_drops_and_counts() -> None:
    _persisting()
    diag.configure(level="ERROR")  # the console is not the subject here, and 10k lines is noise
    for i in range(diag.QUEUE_MAX + 5):
        diag.log("F", f"line {i}", actor=21, dedupe=False)
    counts = diag.counters()
    assert counts["dropped"] >= 5
    assert counts["queued"] == diag.QUEUE_MAX
    assert len(diag.take_queued()) == diag.QUEUE_MAX


# 12
def test_the_next_batch_reports_what_the_queue_lost() -> None:
    _persisting()
    diag.configure(level="ERROR")
    for i in range(diag.QUEUE_MAX + 3):
        diag.log("F", f"line {i}", actor=21, dedupe=False)
    batch = diag.take_queued(5)
    diag.stamp_drops(batch)
    assert json.loads(batch[0]["detail"])["dropped"] == 3
    diag.take_queued()


# 13
def test_counters_report_the_shape_health_publishes() -> None:
    assert set(diag.counters()) == {
        "mode",
        "queued",
        "written",
        "failed",
        "dropped",
        "lastOkAt",
        "lastError",
    }
    assert diag.counters()["mode"] == "stdout"
    _persisting()
    assert diag.counters()["mode"] == "diag_log" == diag.persist_mode()


# 14
def test_flush_returns_true_on_an_empty_queue() -> None:
    assert diag.flush(timeout=0.1) is True
    _persisting()
    diag.log("F", "queued", actor=21)
    assert diag.flush(timeout=0.1) is False  # nothing is draining it in the suite
    diag.take_queued()
    assert diag.flush(timeout=0.1) is True
