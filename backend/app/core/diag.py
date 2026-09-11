"""
Azztec_SaaS_app_core_diag_v1_1_1.py  ->  backend/app/core/diag.py
Version:  1.1.1
Author:   Adriaan
Spec:     Azztec_SaaS_S1d_Diag_Chunk_Spec_v1_0_0.md §3 (OD-18)
          Workmate_Forensic_Diagnostics_Standard_v1_1_0.md (tags) - Architecture D-8

One seam for every request outcome:
  [F] forensic  what happened      [G] guard  why it was blocked      [E] error  crash / write failure
Writes a JSON line to stdout and, when PERSIST_SQL is set (migration 0004_diag_log, S0), persists to
dbo.Diag_Log on a daemon thread. Never blocks a request, never raises.

WIRING - new in 1.1.0.
Up to 1.0.0 nothing attached a handler to 'workmate.diag' and the logger's own level was NOTSET, so its
effective level came from root (WARNING). uvicorn's LOGGING_CONFIG configures the uvicorn* loggers only -
it has no 'root' key - so nothing filled the gap. Two consequences, both observed on the dev server:

  - every [F] and [G] was discarded at the LEVEL CHECK, before any handler would have been consulted.
    Attaching a handler alone would have fixed nothing;
  - [E] escaped through logging.lastResort - a WARNING-level stderr handler with no formatter - so the
    only diagnostics that ever reached an operator were errors, unformatted, on the wrong stream (D-8
    says stdout). That is why Raw Log 2026-09-11 1.0.0 §3 could quote an [E] line verbatim while neither
    log quotes a single [F].

configure() fixes both halves. It is called by create_app(). Any process that does NOT go through
create_app() - the Typer CLI (D-7), the S5 nightly job - must call it itself or it is silent.

Changelog:
  1.1.1  Late-bind the stream (_StdoutHandler). 1.1.0 built a plain StreamHandler(sys.stdout), which binds
         the stream OBJECT at construction. Six reds: capfd.readouterr() came back empty while the same
         line appeared in the report's "Captured stdout call" section. Cause: pytest --capture=fd is not
         only an fd redirect - its SysCapture half replaces sys.stdout as well, and the capfd fixture
         replaces it AGAIN when it starts, after the autouse fixture that called configure(). The handler
         kept writing to the previous object. capfd was never an escape from construction-time binding;
         nothing bound at construction is. Behaviour on a real process is unchanged.
  1.1.0  configure() / is_wired() / level_no(). One stdout handler on 'workmate.diag', level from
         WORKMATE_LOG_LEVEL, bare "%(message)s" formatter (log() already emits one whole JSON object per
         line - a prefix breaks one-line-one-object and the console stops being greppable/jq-able),
         propagate=False so exactly one line is emitted whatever else configures root, idempotent so a
         repeated create_app() cannot stack handlers. Root is never touched.
         log() and _persist() are unchanged: same signature, same record, same persist path.
  1.0.0  Initial. PERSIST_SQL is None until 0004_diag_log lands - stdout only.
"""

from __future__ import annotations

import json
import logging
import sys
import threading
from datetime import datetime
from typing import Any, TextIO

__version__ = "1.1.1"

LOGGER_NAME = "workmate.diag"
HANDLER_NAME = "workmate-diag-stdout"

_log = logging.getLogger(LOGGER_NAME)

# Set once dbo.Diag_Log exists (S0 migration 0004). Named binds: level, source, message, detail, actor, rid
PERSIST_SQL: str | None = None


class _StdoutHandler(logging.StreamHandler):
    """A StreamHandler whose stream is resolved at EMIT time, not at construction.

    Exactly the shape the stdlib uses for its own logging._StderrHandler, and for the same reason: a
    normal StreamHandler holds the stream object it was handed, which is wrong wherever sys.stdout is
    later reassigned. Under pytest that is not an edge case - the default --capture=fd replaces
    sys.stdout, and the capfd fixture replaces it again on entry - so a handler built a moment earlier
    writes somewhere the test cannot read. Resolving late makes the handler honest under any capture
    mode, and costs nothing in production where sys.stdout never moves."""

    def __init__(self) -> None:
        logging.Handler.__init__(self)  # deliberately not StreamHandler.__init__ - it would bind a stream

    @property
    def stream(self) -> Any:  # type: ignore[override]
        return sys.stdout


def level_no(level: str) -> int:
    """'info' / 'INFO' / 'DEBUG' -> int. Anything unrecognised falls back to INFO rather than raising -
    a typo in WORKMATE_LOG_LEVEL must not be able to silence the console again."""
    value = logging.getLevelName(str(level or "INFO").strip().upper())
    return value if isinstance(value, int) else logging.INFO


def configure(level: str = "INFO", stream: TextIO | None = None) -> logging.Logger:
    """Attach exactly one stdout handler to 'workmate.diag'. Idempotent. Root is never touched.

    With stream=None (the normal case) the handler follows sys.stdout wherever it goes. Pass an explicit
    stream only when you want it pinned - a plain StreamHandler is used then, binding included."""
    for old in [h for h in _log.handlers if h.name == HANDLER_NAME]:
        _log.removeHandler(old)
        old.close()
    handler: logging.Handler = _StdoutHandler() if stream is None else logging.StreamHandler(stream)
    handler.set_name(HANDLER_NAME)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.setLevel(logging.NOTSET)  # the logger owns the threshold, not the handler
    _log.addHandler(handler)
    _log.setLevel(level_no(level))
    _log.propagate = False  # exactly one line, whatever a deployment later does to root
    return _log


def is_wired() -> bool:
    """True when this module's own handler is attached - what /api/v1/health reports as diagWired.

    Deliberately NOT logging.Logger.hasHandlers(): that walks ancestors, so pytest's caplog handler on
    root satisfies it and the check passes in the suite while the dev console stays silent. That is
    precisely how the 1.0.0 gap survived three slices."""
    return any(h.name == HANDLER_NAME for h in _log.handlers)


def persist_mode() -> str:
    """Where records PERSIST. Says nothing about whether anything is printing - that is is_wired()."""
    return "diag_log" if PERSIST_SQL else "stdout"


def log(
    level: str,
    message: str,
    detail: Any = None,
    actor: int = 0,
    source: str = "app",
    request_id: str = "",
    persist: bool = True,
) -> dict[str, Any]:
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
    if persist and PERSIST_SQL:
        threading.Thread(target=_persist, args=(rec, level), daemon=True).start()
    return rec


def _persist(rec: dict[str, Any], level: str) -> None:
    try:
        from app.core.db import execute, get_engine  # noqa: PLC0415 - avoid import cycle at module load

        with get_engine().begin() as conn:
            execute(
                conn,
                PERSIST_SQL or "",
                level=level,
                source=rec["source"],
                message=rec["message"][:990],
                detail=(json.dumps(rec["detail"], default=str) if rec["detail"] is not None else None),
                actor=rec["actor"],
                rid=rec["rid"],
            )
    except Exception:  # noqa: BLE001, S110 - diagnostics must never raise
        pass
