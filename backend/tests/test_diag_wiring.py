"""
Azztec_SaaS_test_diag_wiring_v1_0_1.py  ->  backend/tests/test_diag_wiring.py
Version:  1.0.1
Author:   Adriaan
Spec:     Azztec_SaaS_S1d_Diag_Chunk_Spec_v1_0_0.md §7.1 - pair of app/core/diag.py 1.1.1

Proves the diagnostics seam is actually wired: handler present, level low enough to admit [F]/[G], stream
is stdout, root untouched, no propagation, and a real request round-trip produces a parseable JSON line.

INSTRUMENT LAW - corrected 2026-09-11 after six reds proved the 1.0.0 version of this note wrong.

  caplog is not an instrument for this. Its handler sits on root and it proves diag.log() was CALLED -
  which is exactly how the silent logger looked healthy for three slices. Same class of error as
  /api/v1/_diag/self-test asserting the return value of diag.log() rather than its emission.

  capfd is the right reader, but it is NOT a way around construction-time stream binding, which is what
  1.0.0 of this file claimed. pytest's default --capture=fd does two things: it redirects fd 1 AND its
  SysCapture half replaces sys.stdout. The capfd fixture then replaces sys.stdout a second time when it
  starts - after the autouse fixture below has already run configure(). A handler that bound its stream
  in configure() therefore writes to the previous object: the line lands in the report's "Captured stdout
  call" section and capfd.readouterr() comes back empty. The fix is on the handler (diag.py 1.1.1 resolves
  sys.stdout at emit time, the stdlib _StderrHandler pattern), not on the test.

  These tests still read empty under -s, where there is no capture to read.

ZERO DB. TestClient is built without the `with` block, so the lifespan (and its engine connect) never runs,
and every route exercised here resolves before any DB dependency.

Changelog:
  1.0.1  Docstring only - the instrument-law note above was wrong about why capfd was needed. Tests are
         byte-identical to 1.0.0; all twelve pass against diag.py 1.1.1.
  1.0.0  Initial (S1d).
"""

from __future__ import annotations

import json
import logging
import os
import sys

import pytest
from fastapi.testclient import TestClient

from app.core import diag

os.environ.setdefault("WORKMATE_ENV", "test")


@pytest.fixture(scope="module")
def client() -> TestClient:
    from app.main import app  # noqa: PLC0415 - after env is set

    return TestClient(app)  # no `with`: the lifespan and its DB connect stay out of this file


@pytest.fixture(autouse=True)
def wired() -> None:
    diag.configure(level="INFO")


def _json_lines(text: str) -> list[dict]:
    out: list[dict] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("{"):
            out.append(json.loads(line))
    return out


def test_configure_attaches_exactly_one_handler() -> None:
    log = logging.getLogger(diag.LOGGER_NAME)
    assert len([h for h in log.handlers if h.name == diag.HANDLER_NAME]) == 1
    assert diag.is_wired() is True


def test_configure_is_idempotent() -> None:
    log = logging.getLogger(diag.LOGGER_NAME)
    for _ in range(3):
        diag.configure(level="INFO")
    assert len([h for h in log.handlers if h.name == diag.HANDLER_NAME]) == 1


def test_logger_level_admits_info() -> None:
    # The assertion that fails against diag.py 1.0.0: the effective level was root's WARNING, so every
    # [F] and [G] died at the level check before any handler would have been consulted.
    log = logging.getLogger(diag.LOGGER_NAME)
    assert log.isEnabledFor(logging.INFO) is True
    assert log.getEffectiveLevel() <= logging.INFO


def test_configure_does_not_touch_root() -> None:
    root = logging.getLogger()
    assert not any(h.name == diag.HANDLER_NAME for h in root.handlers)


def test_diag_does_not_propagate() -> None:
    assert logging.getLogger(diag.LOGGER_NAME).propagate is False


def test_handler_stream_is_stdout() -> None:
    log = logging.getLogger(diag.LOGGER_NAME)
    handler = next(h for h in log.handlers if h.name == diag.HANDLER_NAME)
    assert handler.stream is sys.stdout


def test_level_no_falls_back_to_info() -> None:
    assert diag.level_no("debug") == logging.DEBUG
    assert diag.level_no("nonsense") == logging.INFO
    assert diag.level_no("") == logging.INFO


@pytest.mark.parametrize("tag", ["F", "G", "E"])
def test_every_tag_reaches_stdout_not_stderr(capfd: pytest.CaptureFixture[str], tag: str) -> None:
    diag.log(tag, f"s1d wiring probe {tag}", detail={"slice": "S1d"}, persist=False)
    captured = capfd.readouterr()
    lines = _json_lines(captured.out)
    assert len(lines) == 1, captured
    assert lines[0]["tag"] == f"[{tag}]"
    assert "s1d wiring probe" in lines[0]["message"]
    # [E] no longer escapes through logging.lastResort onto stderr (D-8 says stdout)
    assert "s1d wiring probe" not in captured.err


def test_emitted_line_is_one_whole_json_object(capfd: pytest.CaptureFixture[str]) -> None:
    diag.log(
        "F", "s1d json shape", detail={"k": 1}, actor=7, source="test", request_id="rid123", persist=False
    )
    rec = _json_lines(capfd.readouterr().out)[0]
    assert set(rec) == {"ts", "tag", "source", "message", "detail", "actor", "rid"}
    assert rec["actor"] == 7
    assert rec["rid"] == "rid123"
    assert rec["source"] == "test"


def test_api_miss_emits_an_outcome_line(client: TestClient, capfd: pytest.CaptureFixture[str]) -> None:
    # A full request round-trip with no database in the path. The status code itself is asserted in
    # test_smoke.py (OD-19); what this proves is that the middleware's outcome line reached stdout.
    client.get("/api/v1/does-not-exist")
    lines = _json_lines(capfd.readouterr().out)
    hits = [x for x in lines if x["tag"] in ("[G]", "[E]") and "/api/v1/does-not-exist" in x["message"]]
    assert hits, "the middleware outcome line never reached stdout"
