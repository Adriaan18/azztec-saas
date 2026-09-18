"""
Azztec_SaaS_app_core_deps_v1_1_0.py  ->  backend/app/core/deps.py
Version:  1.1.0
Author:   Adriaan
Spec:     Azztec_SaaS_S1c_Api_Chunk_Spec_v1_0_0.md §5 · OD-7, OD-12;
          Azztec_SaaS_D1a_Persist_Chunk_Spec_v1_0_0.md §3.4 · OD-56

The interim identity seam. get_current_actor() returns .env WORKMATE_DEV_USER_ID when WORKMATE_ENV=dev
and that id is > 0; otherwise [G] and a 401 NO_IDENTITY in the flat OD-15 shape (main.py's HTTPException
handler renders it). Swapped wholesale for the JWT dependency in the auth slice - routes keep
`Depends(get_current_actor)`.

1.1.0 also writes the resolved actor to request.state. The middleware runs before dependencies resolve,
so it can only read the actor AFTER call_next; without this line its outcome rows carried user 0 while
the router's own line carried the real id - measured on the S1k smoke, 2026-09-19. Diag_Log's
Wm_User_Id is NULL for 0 (OD-55), so a per-person query is only as good as this one assignment.

Under pytest WORKMATE_ENV=test, so an un-overridden call is a 401 by design; tests override this
dependency.

Changelog:
  1.1.0  D1a: request.state.actor set on both paths (the id when resolved, 0 when refused).
  1.0.0  Initial S1c.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.core import diag
from app.core.config import get_settings

__version__ = "1.1.0"


def get_current_actor(request: Request) -> int:
    s = get_settings()
    if s.is_dev and s.dev_user_id > 0:
        actor = int(s.dev_user_id)
        request.state.actor = actor
        return actor
    request.state.actor = 0
    rid = getattr(request.state, "rid", "")
    diag.log("G", "no identity", detail={"env": s.env, "devUserId": s.dev_user_id}, request_id=rid)
    raise HTTPException(
        status_code=401,
        detail={
            "code": "NO_IDENTITY",
            "message": "no identity (dev override needs WORKMATE_ENV=dev and WORKMATE_DEV_USER_ID > 0)",
        },
    )
