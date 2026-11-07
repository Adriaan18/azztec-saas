"""
Azztec_SaaS_app_planner_router_v1_2_0.py  ->  backend/app/planner/router.py
Version:  1.2.0
Author:   Adriaan
Spec:     Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §5.5 (OD-107, OD-111, OD-112, OD-116);
          earlier: Azztec_SaaS_S1c_Api_Chunk_Spec_v1_0_0.md §6 · Planner Port Spec §4 · Architecture D-9
Ported:   workmate.planner_api 1.8.3 _range (src 571-594) - sid/tok gate replaced by
          Depends(get_current_actor);
          DP3: _move (724-743), _preview (995-1000), _writeResult (702-710), _CODE_HTTP (659-663),
          _diagWrite (666-699)

Plain def (D-2). Mounted under /api/v1 by main.py behind require('planner', 'RO') -> /api/v1/planner/...

  GET  /range    200 RangeData (Ignition keys + ok/apiVersion/actor/ms, no gate - OD-14)
                 400 {ok:false, code:BAD_WINDOW, message, rid} on service.WindowError only (OD-16),
                 flat (OD-15)
  GET  /preview  200 MovePreview - what a move would do, nothing written; the router's RO gate is enough
                 404 NOT_FOUND · 422 a rule refusal (flat + sid)
  POST /move     require('planner', 'RW') + require_csrf on the route (OD-107)
                 200 MoveResult, or MoveConfirm - CONFIRM is a 200 with ok=false, so a client reads `ok`
                 403 NO_IDENTITY (the service's; never with a session) · NO_RIGHT / CSRF (deps)
                 404 NOT_FOUND · 409 STALE (+ currentStart) · 422 LOCKED_STATUS / ENGINE_OWNED / NO_START /
                 BAD_DATE / NO_CHANGE · 400 BAD_REQUEST · 500 WRITE_FAILED / INTERNAL
  POST /undo     the same gates; 200 MoveResult (confirm is implied, so never CONFIRM)
  Both POST bodies carry dryRun (default false: the UI's real move). The smoke sends true first (OD-111).
  401 from the actor dependency · 405 from Starlette · FastAPI's own 422 for a malformed body or a missing
  query parameter, as /range's. The move routes document 422 as WriteError - the refusal a client acts on.

One diag line per outcome, the oracle's _diagWrite text (CLAUDE.md #10), dedupe off on every write line:
  [F] move <sid> <from> -> <to> (<delta> d)[ PINNED | pin cleared | still pinned] events=<n>
      ("undo ..." for undo, "move (dry run) ..." when nothing was written)
  [F] move <sid> needs confirm: PAST, SPAN      every reason the preview carries, as the oracle listed them
  [G] move <sid> blocked: <code> - <message>    [E] move <sid> FAILED (<code>) with the driver's message
The service is silent; the middleware's own line is separate.

Changelog:
  1.2.0  DP3a. GET /preview, POST /move, POST /undo (OD-107, OD-112); _CODE_HTTP for every code a move
         can produce; the _diagWrite lines. apiVersion 1.2.0 - new routes and models in the contract.
         GET /range untouched.
  1.1.1  S1i. FORMAT ONLY - ruff format wrapped the @router.get decorator, which was 111
         characters against pyproject's line-length = 110. No logic, no route, no response,
         no string change; the token stream is identical. 1.1.0 went into 5443ac1 unformatted
         because S1h's smoke ran `ruff check` on its seven files and no format pass - and
         `ruff check` can never catch this: [tool.ruff.lint] ignore = ["E501"], so a long line
         passes lint indefinitely and only `ruff format` fixes it. Version bumped rather than
         the file left silently differing from its project-knowledge card (the S1h
         test_planner_repo.py 1.0.2 precedent). A patch on apiVersion reads as "fix, no
         contract change", which is exactly what this is - OD-37's signal stays honest.
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
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Connection

from app.core import db, diag
from app.core.deps import get_current_actor, require, require_csrf
from app.planner import service
from app.planner.schemas import (
    ApiError,
    MoveConfirm,
    MovePreview,
    MoveRequest,
    MoveResult,
    RangeData,
    UndoRequest,
    WriteError,
)

__version__ = "1.2.0"

router = APIRouter(prefix="/planner", tags=["planner"])

# The oracle's map (planner_api 659-663), the codes a move or a preview can produce.
_CODE_HTTP = {
    "NOT_FOUND": 404,
    "STALE": 409,
    "NO_IDENTITY": 403,
    "CONFIRM": 200,
    "LOCKED_STATUS": 422,
    "ENGINE_OWNED": 422,
    "NO_START": 422,
    "BAD_DATE": 422,
    "NO_CHANGE": 422,
    "BAD_REQUEST": 400,
    "WRITE_FAILED": 500,
    "INTERNAL": 500,
}
_WRITE_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ApiError},
    **{status: {"model": WriteError} for status in (400, 404, 409, 422, 500)},
}
_PREVIEW_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ApiError},
    **{status: {"model": WriteError} for status in (404, 422)},
}
# OD-107: the router's RO gate (main.py) still runs first; a move needs RW and the CSRF header on top.
_WRITE_GATES = [Depends(require("planner", "RW")), Depends(require_csrf)]


@router.get(
    "/range", response_model=RangeData, responses={400: {"model": ApiError}, 401: {"model": ApiError}}
)
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


# ---------------------------------------------------------------------------
# DP3 - the move
# ---------------------------------------------------------------------------


def _error(res: dict[str, Any], rid: str) -> JSONResponse:
    """_writeResult's refusal half (702-710): the code's status, OD-15's flat body plus sid / currentStart."""
    code = db.s_(res.get("code")) or "INTERNAL"
    body = WriteError(
        code=code,
        message=db.s_(res.get("message")),
        rid=rid,
        sid=db.s_(res.get("sid")),
        currentStart=db.s_(res.get("currentStart")),
    )
    return JSONResponse(body.model_dump(), status_code=_CODE_HTTP.get(code, 500))


def _diag_write(what: str, res: dict[str, Any], actor: int, rid: str) -> None:
    """_diagWrite (666-699) for a move or an undo - one line per outcome, never collapsed."""
    sid = db.s_(res.get("sid"))
    if res.get("ok"):
        extra = f" {res.get('prevStart')} -> {res.get('newStart')} ({res.get('delta')} d)"
        if res.get("willPin"):
            extra += " PINNED"
        elif res.get("willUnpin"):
            extra += " pin cleared"
        elif res.get("pinned"):
            extra += " still pinned"
        label = f"{what} (dry run)" if res.get("dryRun") else what
        diag.log(
            "F", f"{label} {sid}{extra} events={res.get('events')}", actor=actor, request_id=rid, dedupe=False
        )
        return
    code = db.s_(res.get("code"))
    if code == "CONFIRM":
        reasons = ", ".join(r.get("code", "") for r in (res.get("preview") or {}).get("reasons", []))
        diag.log("F", f"{what} {sid} needs confirm: {reasons}", actor=actor, request_id=rid, dedupe=False)
    elif code in ("WRITE_FAILED", "INTERNAL"):
        diag.log(
            "E",
            f"{what} {sid} FAILED ({code})",
            detail=res.get("message"),
            actor=actor,
            request_id=rid,
            dedupe=False,
        )
    else:
        message = db.s_(res.get("message"))[:300]
        diag.log("G", f"{what} {sid} blocked: {code} - {message}", actor=actor, request_id=rid, dedupe=False)


def _write_result(
    what: str, res: dict[str, Any], actor: int, rid: str
) -> MoveResult | MoveConfirm | JSONResponse:
    """The library dict -> the response (702-710). extra="forbid" on every model: drift raises, loudly."""
    _diag_write(what, res, actor, rid)
    if res.get("ok"):
        return MoveResult.model_validate({**res, "actor": actor})
    if db.s_(res.get("code")) == "CONFIRM":
        return MoveConfirm.model_validate(
            {
                "ok": False,
                "code": "CONFIRM",
                "message": db.s_(res.get("message")),
                "rid": rid,
                "sid": db.s_(res.get("sid")),
                "preview": res.get("preview"),
            }
        )
    return _error(res, rid)


@router.get("/preview", response_model=MovePreview, responses=_PREVIEW_ERRORS)
def get_preview(
    request: Request,
    wo_id: Annotated[int, Query(alias="woId", gt=0, description="WO_ID of the work order")],
    to: Annotated[str, Query(description="yyyy-MM-dd - the day to preview a move to")],
    conn: Annotated[Connection, Depends(db.get_conn)],
    actor: Annotated[int, Depends(get_current_actor)],
) -> MovePreview:
    rid = getattr(request.state, "rid", "")
    res = service.move_preview(conn, wo_id, to)
    if not res.get("ok"):
        code = db.s_(res.get("code"))
        message = db.s_(res.get("message"))[:300]
        diag.log(
            "G", f"preview {db.s_(res.get('sid'))} blocked: {code} - {message}", request_id=rid, actor=actor
        )
        return _error(res, rid)
    diag.log(
        "F",
        f"preview {res['sid']} {res['prevStart']} -> {res['newStart']} ({res['delta']} d) "
        f"confirm={res['confirm']}",
        request_id=rid,
        actor=actor,
        persist=False,  # a read (OD-69)
    )
    return MovePreview.model_validate(res)


@router.post(
    "/move", response_model=MoveResult | MoveConfirm, responses=_WRITE_ERRORS, dependencies=_WRITE_GATES
)
def post_move(
    request: Request,
    body: MoveRequest,
    actor: Annotated[int, Depends(get_current_actor)],
) -> MoveResult | MoveConfirm | JSONResponse:
    rid = getattr(request.state, "rid", "")
    res = service.move_wo(
        body.woId,
        body.toIso,
        actor,
        expect_start_iso=body.expectStartIso,
        confirm=body.confirm,
        dry_run=body.dryRun,
    )
    return _write_result("move", res, actor, rid)


@router.post("/undo", response_model=MoveResult, responses=_WRITE_ERRORS, dependencies=_WRITE_GATES)
def post_undo(
    request: Request,
    body: UndoRequest,
    actor: Annotated[int, Depends(get_current_actor)],
) -> MoveResult | MoveConfirm | JSONResponse:
    rid = getattr(request.state, "rid", "")
    res = service.undo_move(
        body.woId,
        body.toIso,
        actor,
        expect_start_iso=body.expectStartIso,
        dry_run=body.dryRun,
    )
    return _write_result("undo", res, actor, rid)
