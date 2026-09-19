"""
Azztec_SaaS_app_workorders_repo_v1_0_0.py  ->  backend/app/workorders/repo.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_W1a_WOMaint_Read_Api_Chunk_Spec_v1_0_0.md §3.3 · OD-63…OD-68, OD-71
Ported from: the WOMaint v16.28.3 transforms (WOListTable.props.data, txtWorkOrderId.props.text,
             LWO_FamilyTable / EVT_TimelineTable / QN_QueryTable / POTable .props.data) and
             onSelectionChange's responsible-users read - see rules.py for the pure parts.
Pair:     backend/tests/test_workorders_repo.py 1.0.0

Row fetch and row mapping. Takes a SQLAlchemy Connection, returns PLAIN DICTS in the shapes schemas.py
declares. No Pydantic, no FastAPI, no transactions, no module state: this layer reads, router.py
validates and serialises.

The s_/i_/f_ mappers stay on every field even though db.rows() already strips strings and converts
Decimal - belt and braces, as Landmines §B prescribes for char(n) and numeric. Every reference id is
i_() -> 0 when NULL, exactly the transform's `if row.get(idField) is None: row[idField] = 0`.

Changelog:
  1.0.0  Initial W1a.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.engine import Connection

from app.core import db
from app.core.db import f_, i_, s_
from app.planner.rules import iso, timeOf
from app.workorders import rules
from app.workorders import sql as wsql

__version__ = "1.0.0"

WO_TYPES = ("", "N", "CP", "M")


def _opt_f(v: Any) -> float | None:
    """A money/qty column that must stay NULL on the wire (the 'not used yet' blank)."""
    return None if v is None else f_(v)


def _yes(v: Any) -> bool:
    """1 / '1' / 'Y' / True / 'True' -> True. Email_Sent's type was not read (trap 7); this covers
    int, char and bit."""
    return s_(v).upper() in ("1", "Y", "TRUE")


# ---------------------------------------------------------------------------
# the list
# ---------------------------------------------------------------------------


def _list_row(r: dict[str, Any]) -> dict[str, Any]:
    st = s_(r["Status"])
    sid = s_(r["Short_WO_Id"])
    prog = i_(r["Progress_Id"])
    has_po = i_(r["HasPO"]) == 1
    return {
        "id": i_(r["WO_ID"]),
        "sid": sid,
        "title": s_(r["WO_Title"]),
        "asset": s_(r["Asset_ID"]),
        "loc": s_(r["Location_Id"]),
        "status": st,
        "prog": prog,
        "hasPO": has_po,
        "entry": rules.stamp(r["Entry_date"]),
        "badge": rules.badge(st, sid, prog, has_po),
    }


def search(
    conn: Connection,
    *,
    wo_type: str = "N",
    closed: int = 0,
    archive: int = 0,
    q: str = "",
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], bool]:
    """Search v12, paged. `archive` picks the statement (0 live, 2 archive, 1 both); `closed` binds on
    the live arm only (the archive arm has no closed predicate - parity, trap 3). Fetches limit + 1 and
    reports the extra row as `more` (OD-64). Callers validate the domain - this binds what it is given."""
    take = int(limit) + 1
    params: dict[str, Any] = {"q": s_(q), "wo_type": s_(wo_type), "offset": int(offset), "take": take}
    if archive == 2:
        statement = wsql.SEARCH_ARCHIVE
    else:
        statement = wsql.SEARCH_BOTH if archive == 1 else wsql.SEARCH_LIVE
        params["closed"] = int(closed)
    raw = db.rows(conn, statement, **params)
    rows = [_list_row(r) for r in raw[: int(limit)]]
    return rows, len(raw) > int(limit)


# ---------------------------------------------------------------------------
# the record
# ---------------------------------------------------------------------------


def live_exists(conn: Connection, wo_id: int) -> bool:
    return i_(db.scalar(conn, wsql.LIVE_EXISTS, wo_id=int(wo_id))) > 0


def archived_exists(conn: Connection, wo_id: int) -> bool:
    return i_(db.scalar(conn, wsql.ARCHIVED_EXISTS, wo_id=int(wo_id))) > 0


def fetch_resp_users(conn: Connection, wo_id: int) -> list[dict[str, Any]]:
    return [
        {"userId": i_(r["User_ID"]), "shortId": s_(r["Short_User_Id"]), "name": s_(r["User_Name"])}
        for r in db.rows(conn, wsql.RESP_USERS, wo_id=int(wo_id))
    ]


def fetch_resources(conn: Connection, wo_id: int) -> dict[str, Any]:
    rows = [
        {
            "type": s_(r["Type"]),
            "item": s_(r["Item"]),
            "planQty": _opt_f(r["PlanQty"]),
            "planCost": _opt_f(r["PlanCost"]),
            "actQty": _opt_f(r["ActQty"]),
            "actCost": _opt_f(r["ActCost"]),
            "delta": f_(r["Delta"]),
        }
        for r in db.rows(conn, wsql.RESOURCE_COMPARE, wo_id=int(wo_id))
    ]
    planned, actual, diff = rules.resources_totals(rows)
    return {
        "rows": rows,
        "planned": planned,
        "actual": actual,
        "diff": diff,
        "line": rules.resources_line(planned, actual, diff),
    }


def fetch_progress(conn: Connection) -> list[dict[str, Any]]:
    """dbo.Progress, active, by id (OD-67). Nine rows on RST, six at KT."""
    return [
        {"id": i_(r["Progress_Id"]), "title": s_(r["Progress_Title"]), "short": s_(r["Short_Progress_Id"])}
        for r in db.rows(conn, wsql.PROGRESS_ALL)
    ]


def _record(r: dict[str, Any]) -> dict[str, Any]:
    st = s_(r["Status"])
    tf = s_(r["WO_Type_Flag"]) or "N"
    sd = r["Request_Start_Date"]
    ed = r["Request_End_Date"]
    loc_short = s_(r["Short_Location_ID"])
    hier_raw = s_(r["Parent_Location_Hierarchy"])
    return {
        "id": i_(r["WO_ID"]),
        "sid": s_(r["Short_WO_Id"]),
        "title": s_(r["WO_Title"]),
        "status": st,
        "statusTitle": rules.status_title(st),
        "type": tf,
        "overDue": s_(r["OverDue"]),
        "weekNo": f_(r["Week_No"]),
        "start": iso(sd),
        "startTime": timeOf(sd),
        "end": iso(ed) if ed is not None else "",
        "endTime": timeOf(ed),
        "logged": rules.stamp(r["Entry_date"]),
        "companyId": i_(r["Company_ID"]),
        "companyTitle": s_(r["Company_Title"]),
        "assetId": i_(r["Asset_ID"]),
        "asset": s_(r["Short_asset_Id"]),
        "assetTitle": s_(r["Asset_Title"]),
        "locId": i_(r["Location_Id"]),
        "loc": loc_short,
        "locTitle": s_(r["Location_Title"]),
        "hierarchy": rules.hierarchy(hier_raw),
        "hierarchyRaw": hier_raw,
        "durationHrs": f_(r["Duration_In_Hours"]),
        "estCost": f_(r["Est_Cost"]),
        "downTime": f_(r["Down_Time"]),
        "priId": i_(r["Priority_Id"]),
        "priShort": s_(r["Short_Priority_Id"]),
        "priTitle": s_(r["Priority_Title"]),
        "groupId": i_(r["WO_Group_Id"]),
        "groupShort": s_(r["Short_WO_Group_ID"]),
        "groupTitle": s_(r["WO_Group_Title"]),
        "reasonId": i_(r["Reason_Id"]),
        "reasonTitle": s_(r["Reason_Title"]),
        "faultId": i_(r["Fault_Id"]),
        "faultTitle": s_(r["Fault_Title"]),
        "costCenterId": i_(r["Cost_Center_Id"]),
        "costCenterTitle": s_(r["Cost_Center_Title"]),
        "accountId": i_(r["Account_Id"]),
        "accountTitle": s_(r["Account_Title"]),
        "chargeToId": i_(r["Supplier_ID_charge_To"]),
        "chargeToShort": s_(r["ChargeTo_Short"]),
        "chargeToName": s_(r["ChargeTo_Name"]),
        "respSupplierId": i_(r["Supplier_ID_Responsibility"]),
        "respSupplierShort": s_(r["RespSupplier_Short"]),
        "respSupplierName": s_(r["RespSupplier_Name"]),
        "woc1Id": i_(r["WOC1_ID"]),
        "woc1Title": s_(r["WOC1_Title"]),
        "woc2Id": i_(r["WOC2_ID"]),
        "woc2Title": s_(r["WOC2_Title"]),
        "woc3Id": i_(r["WOC3_ID"]),
        "woc3Title": s_(r["WOC3_Title"]),
        "ref1": s_(r["Entered_By"]),
        "ref2": s_(r["Reference"]),
        "prog": i_(r["Progress_Id"]),
        "progTitle": s_(r["Progress_Title"]),
        "notes": s_(r["Notes"]),
        "requestedById": i_(r["User_ID_Requested_By"]),
        "respUserId": i_(r["User_ID_Responsibility"]),
        "respUserName": s_(r["Resp_User_Name"]),
        "conditionId": i_(r["Condition_Id"]),
        "generatedFrom": s_(r["Generated_From"]),
        "intrusive": s_(r["Intrusive"]),
        "intrusiveComplete": s_(r["Intrusive_Complete"]),
        "intrusiveCompleteDate": rules.stamp(r["IntrusiveComplete_Date"]),
        "firstActivity": rules.stamp(r["first_activity_date"]),
        "lastActivity": rules.stamp(r["last_activity_date"]),
        "meterId": i_(r["Meter_ID"]),
        "meterReading": f_(r["Meter_Reading"]),
        "printed": s_(r["Printed"]),
        "progressDate": rules.stamp(r["Progress_Date"]),
        "createdBy": s_(r["Created_By_Name"]),
        "ackBy": s_(r["Ack_By_Name"]),
        "ackDate": rules.stamp(r["Acknowledgement_date"]),
        "approvedBy": s_(r["Approved_By_Name"]),
        "approvedDate": rules.stamp(r["Approved_Date"]),
        "closedBy": s_(r["Closed_By_Name"]),
        "closedDate": rules.stamp(r["Closed_Date"]),
        "cancelledBy": s_(r["Cancelled_By_Name"]),
        "cancelledDate": rules.stamp(r["Cancelled_Date"]),
        "lastSaveBy": s_(r["Last_Save_Name"]),
        "lastSaveDate": rules.stamp(r["Last_Save_Date"]),
        "completeWithin": rules.complete_within(sd, ed),
        "detailsMissing": r["D_WO_ID"] is None,
        "filtersFor": {
            **rules.filters_for(st, tf, loc_short),
            "search": "",
            "limit": 200,
            "offset": 0,
        },
    }


def fetch_item(conn: Connection, wo_id: int) -> dict[str, Any] | None:
    """The record: one WO_ITEM row (header + details + labels) plus the responsible users, the resources
    compare and the progress rows. None when the id is not in WO_N_Header - the router decides between
    NOT_FOUND and ARCHIVED (OD-68)."""
    raw = db.rows(conn, wsql.WO_ITEM, wo_id=int(wo_id))
    if not raw:
        return None
    rec = _record(raw[0])
    rec["respUsers"] = fetch_resp_users(conn, wo_id)
    rec["resources"] = fetch_resources(conn, wo_id)
    rec["progressAll"] = fetch_progress(conn)
    return rec


# ---------------------------------------------------------------------------
# the tabs
# ---------------------------------------------------------------------------


def fetch_linked(conn: Connection, wo_id: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = ""
    for r in db.rows(conn, wsql.LINKED_FAMILY, wo_id=int(wo_id)):
        st = s_(r["Status"])
        sid = s_(r["Short_WO_Id"])
        prog = i_(r["Progress_Id"])
        has_po = i_(r["HasPO"]) == 1
        level = i_(r["Level"])
        selected = i_(r["IsSelected"]) == 1
        if level == 0:
            root = sid
        rows.append(
            {
                "id": i_(r["WO_ID"]),
                "sid": sid,
                "title": s_(r["WO_Title"]),
                "status": st,
                "prog": prog,
                "hasPO": has_po,
                "badge": rules.badge(st, sid, prog, has_po),
                "level": level,
                "rel": rules.rel_label(level, selected),
                "parentId": i_(r["ParentId"]),
                "parentSid": s_(r["ParentShortId"]),
                "start": iso(r["Request_Start_Date"]),
                "entry": rules.stamp(r["Entry_date"]),
                "selected": selected,
            }
        )
    return {"rows": rows, "count": len(rows), "root": root}


def fetch_events(
    conn: Connection, wo_id: int, *, offset: int = 0, limit: int = 200
) -> tuple[list[dict[str, Any]], bool]:
    """Event/Search 1.1, newest first, paged like the list (limit + 1 -> more)."""
    take = int(limit) + 1
    raw = db.rows(conn, wsql.EVENTS, wo_id=int(wo_id), offset=int(offset), take=take)
    rows = [
        {
            "seq": int(offset) + i + 1,
            "eventId": i_(r["Sys_WO_Event_Id"]),
            "event": s_(r["Event_Name"]),
            "detail": rules.event_detail(r["event_details"]),
            "date": rules.stamp(r["Edited_Date"]),
            "editorId": i_(r["User_Id_Edited_By"]),
            "editor": s_(r["Editor_Name"]),
            "siteCode": s_(r["Site_Code"]),
            "siteName": s_(r["Site_Name"]),
            "source": s_(r["Source_Form"]),
            "server": s_(r["server_name"]),
        }
        for i, r in enumerate(raw[: int(limit)])
    ]
    return rows, len(raw) > int(limit)


def fetch_queries(conn: Connection, wo_id: int) -> list[dict[str, Any]]:
    return [
        {
            "id": i_(r["Query_ID"]),
            "type": s_(r["Query_Type"]),
            "typeLabel": rules.query_type_label(r["Query_Type"]),
            "queryFrom": s_(r["Query_From"]),
            "queryTo": s_(r["Query_To"]),
            "desc": s_(r["Query_Desc"]),
            "date": rules.stamp(r["Query_Date"]),
            "pairId": i_(r["Pair_Id"]),
            "emailed": _yes(r["Email_Sent"]),
        }
        for r in db.rows(conn, wsql.QUERIES, wo_id=int(wo_id))
    ]


def fetch_po_lines(conn: Connection, wo_id: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in db.rows(conn, wsql.PO_LINES, wo_id=int(wo_id)):
        st = s_(r["Status"])
        po_sid = s_(r["Short_PO_Id"])
        out.append(
            {
                "poSid": po_sid,
                "status": st,
                "badge": f"{st}|{po_sid}",
                "due": iso(r["Due_Date"]) if r["Due_Date"] is not None else "",
                "supplier": s_(r["Company_Name"]),
                "description": s_(r["PO_Description"]),
                "qty": f_(r["Quantity"]),
                "unitCost": f_(r["Unit_Cost"]),
            }
        )
    return out
