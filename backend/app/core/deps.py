"""
Azztec_SaaS_app_core_deps_v1_0_0.py  ->  backend/app/core/deps.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_S1c_Api_Chunk_Spec_v1_0_0.md §5 · OD-7, OD-12 (Raw Log 2026-09-11 §1)

The interim identity seam. get_current_actor() returns .env WORKMATE_DEV_USER_ID when WORKMATE_ENV=dev
and that id is > 0; otherwise [G] and a 401 NO_IDENTITY in the flat OD-15 shape (main.py's HTTPException
handler renders it). Swapped wholesale for the JWT dependency in S2 - routes keep `Depends(get_current_actor)`.

Under pytest WORKMATE_ENV=test, so an un-overridden call is a 401 by design; tests override this dependency.

Changelog:
  1.0.0  Initial S1c.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.core import diag
from app.core.config import get_settings

__version__ = "1.0.0"


def get_current_actor(request: Request) -> int:
    s = get_settings()
    if s.is_dev and s.dev_user_id > 0:
        return int(s.dev_user_id)
    rid = getattr(request.state, "rid", "")
    diag.log("G", "no identity", detail={"env": s.env, "devUserId": s.dev_user_id}, request_id=rid)
    raise HTTPException(
        status_code=401,
        detail={
            "code": "NO_IDENTITY",
            "message": "no identity (dev override needs WORKMATE_ENV=dev and WORKMATE_DEV_USER_ID > 0)",
        },
    )
