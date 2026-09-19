"""
Azztec_SaaS_app_workorders_schemas_v1_0_0.py  ->  backend/app/workorders/schemas.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_W1a_WOMaint_Read_Api_Chunk_Spec_v1_0_0.md §3.4 · OD-70 · Architecture D-9
The /workorders read contract as Pydantic v2 models. Keys are camelCase (D-9, the planner's style); the
legacy column each key comes from is named beside it. Every model is extra="forbid" and the router runs
Model.model_validate() on the repo dict, so a key the repo adds or drops raises loudly.
ApiError is the planner's - one flat error shape app-wide (OD-15).

Changelog:
  1.0.0  Initial W1a.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.planner.schemas import ApiError

__version__ = "1.0.0"

__all__ = [
    "ApiError",
    "EventPage",
    "EventRow",
    "LinkedFamily",
    "LinkedRow",
    "PoLine",
    "PoList",
    "ProgressRow",
    "QueryList",
    "QueryRow",
    "ResourceRow",
    "Resources",
    "RespUser",
    "SearchFilters",
    "WoList",
    "WoListRow",
    "WoRecord",
]

Segment = Literal["day", "week", "month", "3month", "nextshut", "range"]
WoType = Literal["", "N", "CP", "M"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class _Envelope(_Strict):
    """OD-14: ok / apiVersion / actor / ms on every 200, no gate."""

    ok: bool
    apiVersion: str
    actor: int
    ms: int


# ---------------------------------------------------------------------------
# the list (Search v12)
# ---------------------------------------------------------------------------


class SearchFilters(_Strict):
    woType: WoType
    includeClosed: int  # 0 open only, 1 all, 2 closed and cancelled only (live arm only)
    includeArchive: int  # 0 live only, 1 both arms, 2 archive only
    search: str  # one term against Short_WO_Id OR WO_Title
    limit: int
    offset: int


class WoListRow(_Strict):
    id: int  # WO_ID
    sid: str  # Short_WO_Id
    title: str  # WO_Title
    asset: str  # Asset.Short_asset_Id
    loc: str  # Location.Short_Location_ID
    status: str  # Status
    prog: int  # Progress_Id, 0 when NULL
    hasPO: bool
    entry: str  # Entry_date, 'yyyy-MM-dd HH:mm:ss'
    badge: str  # status|sid|prog|hasPO (WONumBadge v1.3.0)


class WoList(_Envelope):
    rows: list[WoListRow]
    count: int
    more: bool  # a row exists beyond offset + limit (OD-64 - no total)
    filters: SearchFilters


# ---------------------------------------------------------------------------
# the record (Item + Workorder Detail/Item + the label joins)
# ---------------------------------------------------------------------------


class RespUser(_Strict):
    userId: int  # WO_Responsible_User.User_ID
    shortId: str  # Users.Short_User_Id
    name: str  # Users.User_Name


class ResourceRow(_Strict):
    type: str  # Part / Labour / Service
    item: str
    planQty: float | None
    planCost: float | None
    actQty: float | None
    actCost: float | None
    delta: float


class Resources(_Strict):
    rows: list[ResourceRow]
    planned: float
    actual: float
    diff: float
    line: str  # lblAllResourcesValue's text


class ProgressRow(_Strict):
    id: int  # Progress_Id
    title: str  # Progress_Title
    short: str  # Short_Progress_Id


class WoRecord(_Envelope):
    id: int  # WO_ID
    sid: str  # Short_WO_Id
    title: str  # WO_Title
    status: str  # Status
    statusTitle: str  # STATUS_TITLES
    type: str  # WO_Type_Flag, N when NULL
    overDue: str  # OverDue
    weekNo: float  # Week_No (numeric 6,2)
    start: str  # Request_Start_Date, 'yyyy-MM-dd'
    startTime: str  # 'HH:mm' or ''
    end: str  # Request_End_Date, 'yyyy-MM-dd'
    endTime: str  # 'HH:mm' or ''
    logged: str  # Entry_date stamp (the view's Logged_Date)
    companyId: int  # Company_ID
    companyTitle: str  # Company.Company_Title
    assetId: int  # Asset_ID
    asset: str  # Asset.Short_asset_Id
    assetTitle: str  # Asset.Asset_Title
    locId: int  # Location_Id
    loc: str  # Location.Short_Location_ID
    locTitle: str  # Location.Location_Title
    hierarchy: str  # the titles of Parent_Location_Hierarchy joined with ' > '
    hierarchyRaw: str  # Parent_Location_Hierarchy as stored
    durationHrs: float  # Duration_In_Hours
    estCost: float  # Est_Cost
    downTime: float  # Down_Time
    priId: int  # Priority_Id
    priShort: str  # Priority.Short_Priority_Id
    priTitle: str  # Priority.Priority_Title
    groupId: int  # WO_Group_Id
    groupShort: str  # WorkOrder_Group.Short_WO_Group_ID
    groupTitle: str  # WorkOrder_Group.WO_Group_Title
    reasonId: int  # Reason_Id
    reasonTitle: str  # Reason.Reason_Title
    faultId: int  # Fault_Id
    faultTitle: str  # Fault.Fault_Title
    costCenterId: int  # Cost_Center_Id
    costCenterTitle: str  # Cost_Center.Cost_Center_Title
    accountId: int  # Account_Id
    accountTitle: str  # Account.Account_Title
    chargeToId: int  # Supplier_ID_charge_To
    chargeToShort: str  # Supplier.Short_Supplier_Id
    chargeToName: str  # Supplier.Company_Name
    respSupplierId: int  # Supplier_ID_Responsibility
    respSupplierShort: str
    respSupplierName: str
    woc1Id: int  # WOC1_ID
    woc1Title: str  # WOC1.WOC1_Title
    woc2Id: int
    woc2Title: str
    woc3Id: int
    woc3Title: str
    ref1: str  # Entered_By (the view's Ref. 1)
    ref2: str  # Reference (Ref. 2)
    prog: int  # Progress_Id, 0 when NULL
    progTitle: str  # Progress.Progress_Title
    notes: str  # Notes
    requestedById: int  # User_ID_Requested_By
    respUserId: int  # User_ID_Responsibility
    respUserName: str  # Users.User_Name
    conditionId: int  # Condition_Id (no title - Condition's columns were not read)
    generatedFrom: str  # Generated_From
    intrusive: str  # Intrusive
    intrusiveComplete: str  # Intrusive_Complete
    intrusiveCompleteDate: str  # IntrusiveComplete_Date stamp
    firstActivity: str  # first_activity_date stamp
    lastActivity: str  # last_activity_date stamp
    meterId: int  # Meter_ID
    meterReading: float  # Meter_Reading
    printed: str  # Printed
    progressDate: str  # Progress_Date stamp
    createdBy: str  # Users.Short_User_Id of User_Id_Created_By
    ackBy: str  # ... of User_Id_Ack_by
    ackDate: str  # Acknowledgement_date stamp
    approvedBy: str
    approvedDate: str
    closedBy: str
    closedDate: str
    cancelledBy: str
    cancelledDate: str
    lastSaveBy: str  # ... of User_id_Last_Save
    lastSaveDate: str  # Last_Save_Date stamp, seconds (W3 reads the raw column for its lock)
    completeWithin: Segment  # reverse-derived from the start/end span
    detailsMissing: bool  # no WO_N_Details row (OD-65)
    respUsers: list[RespUser]
    resources: Resources
    progressAll: list[ProgressRow]  # dbo.Progress, active, by id (OD-67)
    filtersFor: SearchFilters  # the list filters that show this WO (OD-71)


# ---------------------------------------------------------------------------
# the tabs
# ---------------------------------------------------------------------------


class LinkedRow(_Strict):
    id: int
    sid: str
    title: str
    status: str
    prog: int
    hasPO: bool
    badge: str
    level: int  # 0 root, 1 child, 2 grandchild
    rel: str  # Parent / Child / Grandchild (+ ' (this WO)')
    parentId: int
    parentSid: str
    start: str  # Request_Start_Date, 'yyyy-MM-dd'
    entry: str  # Entry_date stamp
    selected: bool


class LinkedFamily(_Envelope):
    rows: list[LinkedRow]
    count: int
    root: str  # the level-0 short id ('' when the WO has no family row)


class EventRow(_Strict):
    seq: int  # 1-based across the page (offset + i + 1)
    eventId: int  # Sys_WO_Event_Id
    event: str  # Event_Name
    detail: str  # event_details with the braces removed
    date: str  # Edited_Date stamp
    editorId: int  # User_Id_Edited_By
    editor: str  # Users.User_Name, else Short_User_Id, else the id
    siteCode: str  # Company.Short_Company_Id
    siteName: str  # Company.Company_Title
    source: str  # Source_Form
    server: str  # server_name


class EventPage(_Envelope):
    rows: list[EventRow]
    count: int
    more: bool
    offset: int


class QueryRow(_Strict):
    id: int  # Query_ID
    type: str  # Query_Type
    typeLabel: str  # Query / Reply / the code
    queryFrom: str  # Query_From (not `from` - a Python keyword and the S1d alias trap, avoided outright)
    queryTo: str  # Query_To
    desc: str  # Query_Desc
    date: str  # Query_Date stamp
    pairId: int  # Pair_Id
    emailed: bool  # Email_Sent


class QueryList(_Envelope):
    rows: list[QueryRow]
    count: int


class PoLine(_Strict):
    poSid: str  # PO_Header.Short_PO_Id
    status: str  # PO_Header.Status
    badge: str  # status|poSid (PONumBadge)
    due: str  # PO_Details.Due_Date, 'yyyy-MM-dd'
    supplier: str  # Supplier.Company_Name
    description: str  # PO_Description
    qty: float  # Quantity
    unitCost: float  # Unit_Cost


class PoList(_Envelope):
    rows: list[PoLine]
    count: int
