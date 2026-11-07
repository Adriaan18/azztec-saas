"""
Azztec_SaaS_app_planner_schemas_v1_2_0.py  ->  backend/app/planner/schemas.py
Version:  1.2.0
Author:   Adriaan
Spec:     Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §5.4 (OD-112); earlier:
          Azztec_SaaS_S1h_Priority_Initials_Chunk_Spec_v1_0_0.md §3.3 · Planner Port Spec §3 ·
          Architecture D-9

The planner's JSON contract as Pydantic v2 models. Field names are the Ignition keys, camelCase,
declared in src order (cosmetic - Jython dicts were unordered, so order was never contract): rangeData
for /range, and since DP3 moveWO's plan and movePreview's dict for /move, /undo and /preview.

Two things to know:
  - `from` is a Python keyword. RangeData.from_ and LabourMove.from_ carry Field(alias="from"); FastAPI
    serialises by alias, so the wire key is `from`. Same trap on the router's query parameter.
  - every model is extra="forbid". The router runs model_validate() on every service dict it returns, so
    a key the service adds or drops raises loudly instead of being swallowed by response_model.

Changelog:
  1.2.0  DP3a. MoveRequest / UndoRequest (camelCase bodies, dryRun default false - OD-111), Reason,
         UndoRef, LabourMove, MovePreview, MoveResult, MoveConfirm (CONFIRM is a 200 with ok=false),
         WriteError (ApiError + sid + currentStart). Nothing in the /range models moved.
  1.1.0  S1h. Priority gains colour (open item 29). Ships with repo.py 1.1.0
         or not at all - extra="forbid" makes the two halves one change.
  1.0.0  Initial S1c.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__version__ = "1.2.0"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Wo(_Strict):
    id: int
    sid: str
    title: str
    status: str
    statusTitle: str
    type: str
    cat: str  # DONE | PM | REQ | WO
    start: str  # yyyy-MM-dd
    startTime: str  # HH:mm or ''
    end: str  # yyyy-MM-dd or ''
    days: int
    weekNo: float
    prog: int
    priId: int
    pri: str
    estimate: float
    resp: int
    asset: str
    assetTitle: str
    loc: str
    locTitle: str
    hasPO: bool
    engineOwned: bool
    pinned: bool
    pinnedOn: str
    engineDate: str
    locked: bool
    movable: bool
    hrs: float
    hrsSrc: str  # labour | estimate | ''
    assigned: list[int]


class LabourRow(_Strict):
    resId: int
    woId: int
    userId: int
    hours: float
    rate: float
    note: str
    date: str  # yyyy-MM-dd or ''
    skillId: int
    skillTitle: str
    uomId: int


class Skill(_Strict):
    id: int
    title: str
    sysId: int
    hrsPerWeek: float
    supplierId: int


class Worker(_Strict):
    id: int
    sid: str
    name: str
    initials: str
    skills: list[Skill]
    hrsPerWeek: float
    teamId: int
    team: str
    internal: bool


class Team(_Strict):
    id: int
    short: str
    name: str
    internal: bool
    users: int


class Priority(_Strict):
    id: int
    short: str
    title: str
    # dbo.Priority.Colour, varchar(255) NULL on both databases. Free text - no
    # enum, no hex validator, no backend default (OD-36): a default would be
    # indistinguishable from real data downstream. '' when the column is NULL.
    colour: str


class WeekLoad(_Strict):
    weekStart: str
    planned: float
    unknown: int
    count: int
    capacity: float
    pct: int


class Counts(_Strict):
    wo: int
    pm: int
    done: int
    total: int


class WorkerWeek(_Strict):
    weekStart: str
    planned: float
    capacity: float
    pct: int
    flag: str  # over | ok | under | empty


class RangeData(_Strict):
    """GET /api/v1/planner/range - the Ignition rangeData dict plus the OD-14 envelope. No `gate`."""

    from_: str = Field(alias="from")
    to: str
    today: str
    wos: list[Wo]
    labour: list[LabourRow]
    workers: list[Worker]
    teams: list[Team]
    priorities: list[Priority]
    colours: dict[str, str]
    weeks: list[WeekLoad]
    load: dict[str, float]  # key "0" = unassigned
    counts: Counts
    pinTable: bool
    workerWeeks: dict[str, list[WorkerWeek]]
    uomHours: int
    libVersion: str
    # envelope (OD-14)
    ok: bool
    apiVersion: str
    actor: int
    ms: int


class ApiError(_Strict):
    """Flat error body (OD-15, D-9): the same shape main.py emits for INTERNAL."""

    ok: bool = False
    code: str
    message: str
    rid: str = ""


# ---------------------------------------------------------------------------
# DP3 - the move (OD-112). Keys are the oracle's moveWO plan and movePreview dict.
# ---------------------------------------------------------------------------


class MoveRequest(_Strict):
    """POST /api/v1/planner/move. dryRun defaults to false - the UI's real move; the smoke sends true
    first (OD-111)."""

    woId: int = Field(gt=0)
    toIso: str = Field(description="yyyy-MM-dd - the day the WO should start on")
    expectStartIso: str | None = Field(
        default=None, description="the start the client saw; STALE if it moved"
    )
    confirm: bool = False
    dryRun: bool = False


class UndoRequest(_Strict):
    """POST /api/v1/planner/undo - the `undo` dict a move returned. Confirm is implied."""

    woId: int = Field(gt=0)
    toIso: str
    expectStartIso: str | None = None
    dryRun: bool = False


class Reason(_Strict):
    code: str  # PAST | ACTIVE | SPAN | LABOUR_MULTI
    text: str


class UndoRef(_Strict):
    woId: int
    toIso: str
    expectStartIso: str


class LabourMove(_Strict):
    from_: str = Field(alias="from")
    to: str
    rows: int


class MovePreview(_Strict):
    """GET /preview, and a CONFIRM's preview: movePreview (923-937) when the rules pass. `confirm` is the
    service's decision (OD-116), not moveRules'."""

    ok: bool
    code: str
    message: str
    confirm: bool
    reasons: list[Reason]
    delta: int
    newStart: str
    newEnd: str  # '' when the WO has no end
    willPin: bool
    willUnpin: bool
    pinnedAfter: bool
    woId: int
    sid: str
    title: str
    status: str
    statusTitle: str
    prevStart: str
    prevEnd: str
    subtasks: int
    labourDates: list[tuple[str, int]]  # [yyyy-MM-dd, rows]
    labourMoves: list[LabourMove]


class MoveResult(_Strict):
    """200 ok from /move and /undo: moveWO's plan dict, plus the actor who moved it."""

    ok: bool
    dryRun: bool
    woId: int
    sid: str
    prevStart: str
    prevEnd: str
    newStart: str
    newEnd: str
    delta: int
    weekNo: float
    prevWeekNo: float
    subtasks: int
    labourRows: int
    reasons: list[Reason]
    events: int
    willPin: bool
    willUnpin: bool
    pinned: bool
    engineDate: str
    undo: UndoRef
    actor: int


class MoveConfirm(_Strict):
    """200 with ok=false: the move needs a planner's confirm. The client reads `ok`, never the status."""

    ok: bool = False
    code: str  # CONFIRM
    message: str
    rid: str = ""
    sid: str
    preview: MovePreview


class WriteError(ApiError):
    """404 / 409 / 422 / 500 from the move routes: OD-15's flat body plus the oracle's sid, and the start
    the WO has now on STALE."""

    sid: str = ""
    currentStart: str = ""
