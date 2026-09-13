"""
Azztec_SaaS_app_planner_router_v1_1_0.py  ->  backend/app/planner/router.py
Version:  1.1.0
Author:   Adriaan
Spec:     Azztec_SaaS_S1c_Api_Chunk_Spec_v1_0_0.md §6 · Planner Port Spec §4 · Architecture D-9
Ported:   workmate.planner_api 1.8.3 _range (src 571-594) - sid/tok gate replaced by Depends(get_current_actor)

S1c: GET /range only. Plain def (D-2). Mounted under /api/v1 by main.py -> /api/v1/planner/range.
  200  RangeData (Ignition keys + ok/apiVersion/actor/ms, no gate - OD-14)
  400  {ok:false, code:BAD_WINDOW, message, rid} on service.WindowError only (OD-16), body flat (OD-15)
  401  from the actor dependency · 405 from Starlette · 422 FastAPI's own for missing params
One [F] line per request in the Ignition text; the service is silent; the middleware line is separate.

Changelog:
  1.1.0  S1h, OD-37. VERSION LINE ONLY - no logic, no route, no response
         change in this file. Priority gained a colour field (schemas 1.1.0)
         and apiVersion, set from __version__ below, is the only signal a
         generated client gets that the payload shape moved. A client pinned
         to apiVersion 1.0.1 must not be able to receive two shapes.
  1.0.1  Ruff UP031: diag lines to f-strings. Ignition message text unchanged. No behaviour change.
  1.0.0  Initial S1c.
"""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Connection

from app.core import db, diag
from app.core.deps import get_current_actor
from app.planner import service
from app.planner.schemas import ApiError, RangeData

__version__ = "1.1.0"

router = APIRouter(prefix="/planner", tags=["planner"])


@router.get("/range", response_model=RangeData, responses={400: {"model": ApiError}, 401: {"model": ApiError}})
def get_range(
    request: Request,
    from_: Annotated[str, Query(alias="from", description="yyyy-MM-dd, inclusive")],
    to: Annotated[str, Query(description="yyyy-MM-dd, inclusive; max 400 days from `from`")],
    conn: Annotated[Connection, Depends(db.get_conn)],
    actor: Annotated[int, Depends(get_current_actor)],
) -> RangeData:
    rid = getattr(request.state, "rid", "")
    t0 = time.perf_counter()
    try:
        data = service.range_data(conn, from_, to)
    except service.WindowError as e:
        diag.log("G", f"range refused: {e}", request_id=rid, actor=actor)
        return JSONResponse(
            {"ok": False, "code": e.code, "message": str(e), "rid": rid},
            status_code=400,
        )
    ms = int((time.perf_counter() - t0) * 1000)
    data["ok"] = True
    data["apiVersion"] = __version__
    data["actor"] = actor
    data["ms"] = ms
    diag.log(
        "F",
        f"range {data['from']}..{data['to']} rows={len(data['wos'])} labour={len(data['labour'])} "
        f"workers={len(data['workers'])} pinTable={data['pinTable']} in {ms} ms",
        request_id=rid,
        actor=actor,
    )
    return RangeData.model_validate(data)  # extra="forbid": contract drift raises here, loudly
