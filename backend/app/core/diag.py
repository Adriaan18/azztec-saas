"""
Azztec_SaaS_app_core_diag_v1_0_0.py  ->  backend/app/core/diag.py
Version:  1.0.0
Author:   Adriaan
Spec:     Workmate_Forensic_Diagnostics_Standard_v1_1_0.md (tags), Architecture D-8

One seam for every request outcome:
  [F] forensic  what happened      [G] guard  why it was blocked      [E] error  crash / write failure
Writes a JSON line to the app logger (stdout) and, when PERSIST_SQL is set (migration 0004_diag_log, S0),
persists to dbo.Diag_Log on a daemon thread. Never blocks a request, never raises.

Changelog:
  1.0.0  Initial. PERSIST_SQL is None until 0004_diag_log lands - stdout only.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from typing import Any

__version__ = "1.0.0"

_log = logging.getLogger("workmate.diag")

# Set once dbo.Diag_Log exists (S0 migration 0004). Named binds: level, source, message, detail, actor, rid
PERSIST_SQL: str | None = None


def persist_mode() -> str:
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
