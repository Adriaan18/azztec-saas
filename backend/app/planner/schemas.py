"""
Azztec_SaaS_app_planner_schemas_v1_1_0.py  ->  backend/app/planner/schemas.py
Version:  1.1.0
Author:   Adriaan
Spec:     Azztec_SaaS_S1h_Priority_Initials_Chunk_Spec_v1_0_0.md §3.3 · Planner Port Spec §3 · Architecture D-9

The /range JSON contract as Pydantic v2 models. Field names are the Ignition rangeData keys, camelCase,
declared in src order (cosmetic - Jython dicts were unordered, so order was never contract).

Two things to know:
  - `from` is a Python keyword. RangeData.from_ carries Field(alias="from"); FastAPI serialises by alias,
    so the wire key is `from`. Same trap on the router's query parameter.
  - every model is extra="forbid". The router runs RangeData.model_validate() on the service dict, so a
    key the service adds or drops raises loudly instead of being swallowed by response_model.

Changelog:
  1.1.0  S1h. Priority gains colour (open item 29). Ships with repo.py 1.1.0
         or not at all - extra="forbid" makes the two halves one change.
  1.0.0  Initial S1c.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__version__ = "1.1.0"


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
