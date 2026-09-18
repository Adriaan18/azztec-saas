"""
Azztec_SaaS_app_core_diag_v1_2_0.py  ->  backend/app/core/diag.py
Version:  1.2.0
Author:   Adriaan
Spec:     Azztec_SaaS_D1a_Persist_Chunk_Spec_v1_0_0.md §3.1 · OD-55, OD-57, OD-58, OD-59 (signed 2026-09-19)
Ported from: workmate.diag 1.3.0 (log / forensic / guard / error, async persist, NULL user when none)
Pair:     backend/tests/test_diag_persist.py 1.0.0

1.1.1's console behaviour is untouched: every call still prints exactly one JSON line to stdout, in the
same shape, and test_diag_wiring 1.0.1 pins it. What 1.2.0 adds is the other half - the line reaching
dbo.Diag_Log with the person on it.

PERSIST_SQL is set at boot by app.main from app.diag.sql.INSERT when WORKMATE_DIAG_PERSIST is true. Core
does not import the feature package; the wiring is explicit and visible in one place.

The row (OD-55), measured against the real DDL on RST 2026-09-19:
  Tier       the tag                      char(1)       NOT NULL
  Msg_Level  F/S -> info, G -> warn, E -> error  varchar(8)    NOT NULL
  Source     the caller's source          varchar(64)   NOT NULL
  Session_Id the request id, '' at boot   varchar(64)   NOT NULL
  Message    cut to 1000 CHARACTERS       nvarchar(1000) NOT NULL   (sys.columns says 2000 BYTES)
  Wm_User_Id the actor, NULL when 0       int           NULL        (0 is not a Users.User_Id)
  Site_Code  NULL until a site model      varchar(8)    NULL
  Detail     redacted JSON, cut to 8000   nvarchar(max) NULL
  Logged_At  CURRENT_TIMESTAMP in the statement - the DATABASE clock stamps it, as at KT. The `ts` in the
             stdout line is the app clock; on one box they agree, and the viewer shows the database's.
Every field is cut to its column BEFORE it is queued, so one long value cannot fail a whole batch.

The writer (OD-57): one daemon thread, one bounded queue, batches of BATCH_MAX rows or BATCH_SECONDS,
its own engine connection - never a request's. Overflow drops the newest row and counts it, and the next
batch's first row carries the count. A failed batch is retried once, then counted and dropped, and the
first failure (then every hundredth) prints one stdout [E] - never through the queue that just failed.
This is the KT lesson: a persist path that swallows its errors looks healthy while the table stays empty.

Changelog:
  1.2.0  D1a: PERSIST_SQL wired, record()/redact()/should_persist(), the writer thread, counters(),
         flush(), and two seams the suite uses instead of reaching for privates - take_queued() and
         reset_counters(). log() gains one keyword (dedupe) and keeps its stdout line byte-identical.
  1.1.1  Handler stream resolved at emit time (pytest swaps sys.stdout twice).
  1.1.0  persist_mode()/is_wired() split (OD-20).
  1.0.0  Initial S1d.
"""

from __future__ import annotations

import json
import logging
import queue
import re
import sys
import threading
import time
from collections import OrderedDict
from datetime import datetime
from typing import Any, TextIO

__version__ = "1.2.0"

LOGGER_NAME = "workmate.diag"
HANDLER_NAME = "workmate-diag-stdout"

_log = logging.getLogger(LOGGER_NAME)

# Set at boot by app.main (app.diag.sql.INSERT). None -> stdout only, exactly as 1.1.1.
PERSIST_SQL: str | None = None

# --- OD-55: the columns ----------------------------------------------------
TIER_LEVEL = {"F": "info", "G": "warn", "E": "error", "S": "info"}
MSG_MAX = 1000
DETAIL_MAX = 8000
SOURCE_MAX = 64
SESSION_MAX = 64
LEVEL_MAX = 8

# --- OD-58: what Detail may never carry ------------------------------------
SECRET_HINTS = (
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "authorization",
    "cookie",
    "api_key",
    "apikey",
)
REDACTED = "***"

# --- OD-57: the writer -----------------------------------------------------
QUEUE_MAX = 10_000
BATCH_MAX = 100
BATCH_SECONDS = 1.0
FLUSH_TIMEOUT = 2.0

# --- OD-59: volume ---------------------------------------------------------
DEDUPE_SECONDS = 900.0
DEDUPE_MAX = 512
_TIMING = re.compile(r"\b\d+(?:\.\d+)? ?ms\b")

_QUEUE: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=QUEUE_MAX)
_COUNTS: dict[str, Any] = {"written": 0, "failed": 0, "dropped": 0, "lastOkAt": "", "lastError": ""}
_COUNTS_LOCK = threading.Lock()
_DEDUPE: OrderedDict[str, float] = OrderedDict()
_DEDUPE_LOCK = threading.Lock()
_WRITER: threading.Thread | None = None
_WRITER_LOCK = threading.Lock()
_PENDING_DROPPED = 0
_FAILED_BATCHES = 0


class _StdoutHandler(logging.StreamHandler):
    """A StreamHandler whose stream is resolved at EMIT time, not at construction.

    Exactly the shape the stdlib uses for its own logging._StderrHandler, and for the same reason: a
    normal StreamHandler holds the stream object it was handed, which is wrong wherever sys.stdout is
    later reassigned. Under pytest that is not an edge case - the default --capture=fd replaces
    sys.stdout, and the capfd fixture replaces it again on entry."""

    def __init__(self) -> None:
        logging.Handler.__init__(self)  # deliberately not StreamHandler.__init__ - it would bind a stream

    @property
    def stream(self) -> Any:  # type: ignore[override]
        return sys.stdout


def level_no(level: str) -> int:
    """'info' / 'INFO' / 'DEBUG' -> int. Anything unrecognised falls back to INFO rather than raising."""
    value = logging.getLevelName(str(level or "INFO").strip().upper())
    return value if isinstance(value, int) else logging.INFO


def configure(level: str = "INFO", stream: TextIO | None = None) -> logging.Logger:
    """Attach exactly one stdout handler to 'workmate.diag'. Idempotent. Root is never touched."""
    for old in [h for h in _log.handlers if h.name == HANDLER_NAME]:
        _log.removeHandler(old)
        old.close()
    handler: logging.Handler = _StdoutHandler() if stream is None else logging.StreamHandler(stream)
    handler.set_name(HANDLER_NAME)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.setLevel(logging.NOTSET)  # the logger owns the threshold, not the handler
    _log.addHandler(handler)
    _log.setLevel(level_no(level))
    _log.propagate = False
    return _log


def is_wired() -> bool:
    """True when this module's own handler is attached - what /api/v1/health reports as diagWired."""
    return any(h.name == HANDLER_NAME for h in _log.handlers)


def persist_mode() -> str:
    """Where records PERSIST. Says nothing about whether anything is printing - that is is_wired()."""
    return "diag_log" if PERSIST_SQL else "stdout"


# ---------------------------------------------------------------------------
# the row
# ---------------------------------------------------------------------------


def redact(value: Any) -> Any:
    """OD-58. Any key that looks like a secret becomes '***', at any depth, before the row is queued."""
    if isinstance(value, dict):
        return {
            k: (REDACTED if any(h in str(k).lower() for h in SECRET_HINTS) else redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact(v) for v in value]
    return value


def record(
    level: str,
    message: str,
    detail: Any = None,
    actor: int = 0,
    source: str = "app",
    request_id: str = "",
) -> dict[str, Any]:
    """The row as it will be written - binds for app.diag.sql.INSERT, every field cut to its column."""
    tier = level if level in TIER_LEVEL else "F"
    body = None if detail is None else json.dumps(redact(detail), default=str)[:DETAIL_MAX]
    return {
        "session_id": str(request_id or "")[:SESSION_MAX],
        "wm_user_id": int(actor or 0) or None,  # 0 -> NULL
        "site_code": None,
        "source": str(source or "app")[:SOURCE_MAX],
        "tier": tier,
        "msg_level": TIER_LEVEL[tier][:LEVEL_MAX],
        "message": str(message)[:MSG_MAX],
        "detail": body,
    }


def _shape(message: str) -> str:
    """The message with its timings normalised, so a poll of the same window is one shape."""
    return _TIMING.sub("# ms", str(message))


def should_persist(tier: str, actor: int, source: str, message: str, dedupe: bool = True) -> bool:
    """OD-59. Blocks and crashes always persist. A repeated [F] within DEDUPE_SECONDS does not."""
    if tier in ("G", "E") or not dedupe:
        return True
    key = f"{actor}|{source}|{_shape(message)}"
    now = time.monotonic()
    with _DEDUPE_LOCK:
        seen = _DEDUPE.get(key)
        if seen is not None and now - seen < DEDUPE_SECONDS:
            return False
        _DEDUPE[key] = now
        _DEDUPE.move_to_end(key)
        while len(_DEDUPE) > DEDUPE_MAX:
            _DEDUPE.popitem(last=False)
    return True


def clear_dedupe() -> None:
    """Tests and the smoke start from a known state."""
    with _DEDUPE_LOCK:
        _DEDUPE.clear()


# ---------------------------------------------------------------------------
# the line
# ---------------------------------------------------------------------------


def log(
    level: str,
    message: str,
    detail: Any = None,
    actor: int = 0,
    source: str = "app",
    request_id: str = "",
    persist: bool = True,
    dedupe: bool = True,
) -> dict[str, Any]:
    """One JSON line to stdout, always; one row to Diag_Log when persistence is on and OD-59 allows it.

    dedupe=False is for lines that must never be collapsed - every write outcome passes it."""
    rec = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "tag": f"[{level}]",
        "source": source,
        "message": message,
        "detail": detail,
        "actor": int(actor or 0),
        "rid": request_id,
    }
    line = json.dumps(rec, default=str)
    if level == "E":
        _log.error(line)
    else:
        _log.info(line)
    if persist and PERSIST_SQL and should_persist(level, int(actor or 0), source, str(message), dedupe):
        _enqueue(record(level, message, detail, actor, source, request_id))
    return rec


# ---------------------------------------------------------------------------
# the writer
# ---------------------------------------------------------------------------


def _bump(key: str, n: int = 1) -> None:
    with _COUNTS_LOCK:
        _COUNTS[key] = int(_COUNTS[key]) + n


def _enqueue(row: dict[str, Any]) -> None:
    global _PENDING_DROPPED
    try:
        _QUEUE.put_nowait(row)
    except queue.Full:
        _bump("dropped")
        with _COUNTS_LOCK:
            _PENDING_DROPPED += 1


def stamp_drops(batch: list[dict[str, Any]]) -> None:
    """The next batch says how many rows the queue lost, so a gap is never silent."""
    global _PENDING_DROPPED
    with _COUNTS_LOCK:
        n, _PENDING_DROPPED = _PENDING_DROPPED, 0
    if n and batch:
        batch[0]["detail"] = json.dumps({"dropped": n, "detail": batch[0]["detail"]}, default=str)[
            :DETAIL_MAX
        ]


def _write_batch(rows: list[dict[str, Any]]) -> None:
    from sqlalchemy import text  # noqa: PLC0415 - kept out of module import

    from app.core.db import get_engine  # noqa: PLC0415 - avoids an import cycle at module load

    with get_engine().begin() as conn:
        conn.execute(text(PERSIST_SQL or ""), rows)


def _note_failure(e: BaseException) -> None:
    global _FAILED_BATCHES
    _FAILED_BATCHES += 1
    with _COUNTS_LOCK:
        _COUNTS["lastError"] = str(e)[:300]
    if _FAILED_BATCHES == 1 or _FAILED_BATCHES % 100 == 0:
        # stdout only: the path that just failed is the one we would otherwise be reporting through
        log("E", "diag persist failed", detail=str(e)[:300], source="diag", persist=False)


def _drain_one_batch() -> list[dict[str, Any]]:
    batch = [_QUEUE.get()]
    deadline = time.monotonic() + BATCH_SECONDS
    while len(batch) < BATCH_MAX:
        wait = deadline - time.monotonic()
        if wait <= 0:
            break
        try:
            batch.append(_QUEUE.get(timeout=wait))
        except queue.Empty:
            break
    return batch


def _writer_loop() -> None:
    while True:
        batch = _drain_one_batch()
        stamp_drops(batch)
        try:
            _write_batch(batch)
            _bump("written", len(batch))
            with _COUNTS_LOCK:
                _COUNTS["lastOkAt"] = datetime.now().isoformat(timespec="seconds")
        except Exception:  # noqa: BLE001 - one retry, then the batch is counted and dropped
            try:
                _write_batch(batch)
                _bump("written", len(batch))
                with _COUNTS_LOCK:
                    _COUNTS["lastOkAt"] = datetime.now().isoformat(timespec="seconds")
            except Exception as e:  # noqa: BLE001 - diagnostics must never raise into a request
                _bump("failed", len(batch))
                _note_failure(e)
        finally:
            for _ in batch:
                _QUEUE.task_done()


def start_writer() -> bool:
    """Idempotent. False when persistence is off or the thread is already running."""
    global _WRITER
    with _WRITER_LOCK:
        if not PERSIST_SQL:
            return False
        if _WRITER is not None and _WRITER.is_alive():
            return False
        _WRITER = threading.Thread(target=_writer_loop, name="workmate-diag-writer", daemon=True)
        _WRITER.start()
        return True


def flush(timeout: float = FLUSH_TIMEOUT) -> bool:
    """Wait for the queue to drain. True when it did."""
    deadline = time.monotonic() + timeout
    while _QUEUE.unfinished_tasks and time.monotonic() < deadline:
        time.sleep(0.02)
    return not _QUEUE.unfinished_tasks


def take_queued(limit: int = QUEUE_MAX) -> list[dict[str, Any]]:
    """Drain the queue without writing. The writer thread does not run in the suite, so this is how a
    test sees the rows that would have been written - and how the smoke empties a queue it filled."""
    out: list[dict[str, Any]] = []
    while len(out) < limit:
        try:
            out.append(_QUEUE.get_nowait())
        except queue.Empty:
            break
        _QUEUE.task_done()
    return out


def reset_counters() -> None:
    """Tests and the smoke start from a known state; production never calls it."""
    global _PENDING_DROPPED, _FAILED_BATCHES
    with _COUNTS_LOCK:
        _COUNTS.update({"written": 0, "failed": 0, "dropped": 0, "lastOkAt": "", "lastError": ""})
        _PENDING_DROPPED = 0
    _FAILED_BATCHES = 0


def counters() -> dict[str, Any]:
    """What /api/v1/health reports as diagPersist - a dead log must be visible, never inferred."""
    with _COUNTS_LOCK:
        out = dict(_COUNTS)
    out["mode"] = persist_mode()
    out["queued"] = _QUEUE.qsize()
    return out
