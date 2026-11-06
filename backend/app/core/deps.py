"""
Azztec_SaaS_app_core_deps_v1_2_0.py  ->  backend/app/core/deps.py
Version:  1.2.0
Author:   Adriaan
Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s5 (OD-97, OD-100, OD-103);
          earlier: S1c spec s5 (OD-7, OD-12), D1a spec s3.4 (OD-56)

The identity seam, now a real one. Every gated request resolves ONE Principal:

  get_principal      the session behind the cookie, through LOADER - a callable main.py installs
                     (app.auth.service.principal_from_request). Core never imports the feature package
                     (the OD-55 rule: main.py hands core what it needs, as it hands diag.py its INSERT).
                     No session -> [G] and 401 NO_IDENTITY, the code every client already handles.
  get_current_actor  the principal's User_Id. Routes keep `Depends(get_current_actor)` unchanged.
  require(page, r)   a dependency that answers 403 NO_RIGHT unless the principal's right on `page` is at
                     least `r` (RWD > RW > RO > NA). main.py puts it on whole routers.
  require_admin      403 NO_RIGHT unless the principal is a Workmate administrator (security level 1).
                     main.py puts it on the _diag router, after that router's own dev-only check.
  require_csrf       403 CSRF unless the request carries X-Azztec-Request: 1 (put on every non-GET).

OD-103: WORKMATE_DEV_USER_ID is no longer an identity for any request. Tests override get_principal
(a Principal with the rights the test needs); FastAPI caches a dependency per request, so the principal
is resolved once however many gates ask.

request.state.actor is still set on every path (D1a: the middleware reads it after call_next).

Changelog:
  1.2.0  DP2a: get_principal / Principal / LOADER, require(), require_admin, require_csrf;
         get_current_actor derives from the principal; the dev override is gone from the HTTP path
         (OD-103).
  1.1.0  D1a: request.state.actor set on both paths (the id when resolved, 0 when refused).
  1.0.0  Initial S1c.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app.core import diag

__version__ = "1.2.0"

RANK: dict[str, int] = {"NA": 0, "RO": 1, "RW": 2, "RWD": 3}
CSRF_HEADER = "x-azztec-request"


@dataclass(frozen=True)
class Principal:
    user_id: int
    short_id: str = ""
    name: str = ""
    rights: dict[str, str] = field(default_factory=dict)  # page -> RWD | RW | RO | NA
    is_admin: bool = False
    expires_at: str = ""


# Installed by main.create_app(); None means nobody can be signed in (a 401 for every gated route).
LOADER: Callable[[Request], Principal | None] | None = None


def get_principal(request: Request) -> Principal:
    p = LOADER(request) if LOADER is not None else None
    if p is None:
        request.state.actor = 0
        rid = getattr(request.state, "rid", "")
        diag.log("G", "no identity", detail={"path": request.url.path}, request_id=rid)
        raise HTTPException(status_code=401, detail={"code": "NO_IDENTITY", "message": "not signed in"})
    request.state.actor = p.user_id
    return p


def get_current_actor(request: Request, principal: Annotated[Principal, Depends(get_principal)]) -> int:
    request.state.actor = principal.user_id
    return principal.user_id


def require(page: str, need: str) -> Callable[..., int]:
    """A dependency: 403 NO_RIGHT unless the principal's right on `page` is at least `need`."""
    if need not in RANK:
        raise ValueError(f"unknown right {need!r}")

    def _require(request: Request, principal: Annotated[Principal, Depends(get_principal)]) -> int:
        have = principal.rights.get(page, "NA")
        if RANK.get(have, 0) < RANK[need]:
            rid = getattr(request.state, "rid", "")
            diag.log(
                "G",
                f"no right {page} need={need} have={have}",
                actor=principal.user_id,
                request_id=rid,
                source="auth",
            )
            raise HTTPException(
                status_code=403,
                detail={"code": "NO_RIGHT", "message": f"your Workmate rights do not allow {page} ({need})"},
            )
        return principal.user_id

    _require.__name__ = f"require_{page}_{need}"
    return _require


def require_admin(request: Request, principal: Annotated[Principal, Depends(get_principal)]) -> int:
    """403 NO_RIGHT unless the principal is a Workmate administrator (OD-100: level exactly 1)."""
    if not principal.is_admin:
        rid = getattr(request.state, "rid", "")
        diag.log("G", "no right admin", actor=principal.user_id, request_id=rid, source="auth")
        raise HTTPException(
            status_code=403,
            detail={"code": "NO_RIGHT", "message": "this needs a Workmate administrator"},
        )
    return principal.user_id


def require_csrf(request: Request) -> None:
    if request.headers.get(CSRF_HEADER) != "1":
        rid = getattr(request.state, "rid", "")
        diag.log("G", f"csrf header missing on {request.method} {request.url.path}", request_id=rid)
        raise HTTPException(status_code=403, detail={"code": "CSRF", "message": "missing X-Azztec-Request"})
