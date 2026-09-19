"""
Azztec_SaaS_test_openapi_contract_v1_1_1.py  ->  backend/tests/test_openapi_contract.py
Version:  1.1.1
Author:   Adriaan
Spec:     Azztec_SaaS_S1d_Diag_Chunk_Spec_v1_0_0.md §6
          Azztec_SaaS_W1a_WOMaint_Read_Api_Chunk_Spec_v1_0_0.md §3.6

Guards the PUBLISHED schema, not the runtime body. `from` is a Python keyword, so the contract key needs
Field(alias="from") on the model AND Query(alias="from") on the route parameter - two independent
declarations. Until this file only the runtime body was asserted (test_range_from_key_is_literal_from), so
a regression on the parameter alias would have surfaced as a 422 out of the generated TS client, one slice
later and a long way from its cause. Raw Log 2026-09-11 1.1.0 §7 calls this the third occurrence of the
trap; this is the second, pinned.

Reads app.openapi(). Never iterates router.routes - FastAPI 0.137 made that a tree of intermediate objects
(Landmines §A). Zero DB: building the schema opens no connection.

Changelog:
  1.1.1  W1a smoke: ruff SIM300 (Yoda condition) on the envelope subset assertion - operands swapped.
         No assertion change.
  1.1.0  W1a. The six /workorders paths: published, their parameters and bounds, the flat error shapes,
         WoRecord's key set and additionalProperties False, info.version 0.5.0, and the S1d `from_` trap
         re-asserted over the whole document. The eight range tests are untouched.
  1.0.0  Initial (S1d).
"""

from __future__ import annotations

import json
import os
from typing import Any

import pytest

os.environ.setdefault("WORKMATE_ENV", "test")

RANGE_PATH = "/api/v1/planner/range"

# Port Spec §3 (16 rangeData keys) + OD-14 envelope (ok, apiVersion, actor, ms) = 20
CONTRACT_KEYS = frozenset(
    {
        "from",
        "to",
        "today",
        "wos",
        "labour",
        "workers",
        "teams",
        "priorities",
        "colours",
        "weeks",
        "load",
        "counts",
        "pinTable",
        "workerWeeks",
        "uomHours",
        "libVersion",
        "ok",
        "apiVersion",
        "actor",
        "ms",
    }
)


@pytest.fixture(scope="module")
def schema() -> dict[str, Any]:
    from app.main import app  # noqa: PLC0415 - after env is set

    return app.openapi()


def _resolve(schema: dict[str, Any], ref: str) -> dict[str, Any]:
    node: Any = schema
    for part in ref.removeprefix("#/").split("/"):
        node = node[part]
    return node


def _range_get(schema: dict[str, Any]) -> dict[str, Any]:
    return schema["paths"][RANGE_PATH]["get"]


def _params(schema: dict[str, Any]) -> list[dict[str, Any]]:
    return _range_get(schema).get("parameters", [])


def _range_data(schema: dict[str, Any]) -> dict[str, Any]:
    ref = _range_get(schema)["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    return _resolve(schema, ref)


def test_range_route_is_published(schema: dict[str, Any]) -> None:
    assert RANGE_PATH in schema["paths"]


def test_query_param_is_literal_from(schema: dict[str, Any]) -> None:
    names = [p["name"] for p in _params(schema)]
    assert "from" in names
    assert "from_" not in names
    assert "to" in names


def test_from_param_is_a_required_query_param(schema: dict[str, Any]) -> None:
    param = next(p for p in _params(schema) if p["name"] == "from")
    assert param["in"] == "query"
    assert param["required"] is True


def test_response_keys_match_the_contract(schema: dict[str, Any]) -> None:
    assert set(_range_data(schema)["properties"]) == CONTRACT_KEYS


def test_response_has_no_gate(schema: dict[str, Any]) -> None:
    # OD-14: retired with the sid gate.
    assert "gate" not in _range_data(schema)["properties"]


def test_response_forbids_extra_keys(schema: dict[str, Any]) -> None:
    # How extra="forbid" (the drift guard) shows up in the published schema.
    assert _range_data(schema).get("additionalProperties") is False


def test_400_is_documented_with_the_flat_error_shape(schema: dict[str, Any]) -> None:
    # OD-15: flat {ok, code, message}. The generated client needs the failure shape, not just the success.
    responses = _range_get(schema)["responses"]
    assert "400" in responses
    ref = responses["400"]["content"]["application/json"]["schema"]["$ref"]
    assert {"ok", "code", "message"} <= set(_resolve(schema, ref)["properties"])


def test_no_from_underscore_survives_anywhere_in_the_operation(schema: dict[str, Any]) -> None:
    assert "from_" not in json.dumps(_range_get(schema))


# ---------------------------------------------------------------------------
# W1a - the six /workorders paths
# ---------------------------------------------------------------------------

WO_BASE = "/api/v1/workorders"
WO_PATHS = (
    WO_BASE,
    WO_BASE + "/{wo_id}",
    WO_BASE + "/{wo_id}/events",
    WO_BASE + "/{wo_id}/linked",
    WO_BASE + "/{wo_id}/queries",
    WO_BASE + "/{wo_id}/pos",
)
ENVELOPE = {"ok", "apiVersion", "actor", "ms"}


def _wo_get(schema: dict[str, Any], path: str) -> dict[str, Any]:
    return schema["paths"][path]["get"]


def _wo_params(schema: dict[str, Any], path: str) -> dict[str, dict[str, Any]]:
    return {p["name"]: p for p in _wo_get(schema, path).get("parameters", [])}


def _wo_200(schema: dict[str, Any], path: str) -> dict[str, Any]:
    ref = _wo_get(schema, path)["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    return _resolve(schema, ref)


def test_workorders_routes_are_published(schema: dict[str, Any]) -> None:
    for path in WO_PATHS:
        assert path in schema["paths"], path
        assert set(schema["paths"][path]) == {"get"}, path  # GET only this slice


def test_workorders_list_params_and_bounds(schema: dict[str, Any]) -> None:
    params = _wo_params(schema, WO_BASE)
    assert set(params) == {"woType", "includeClosed", "includeArchive", "search", "limit", "offset"}
    assert all(p["in"] == "query" and p.get("required", False) is False for p in params.values())
    sch = {name: p["schema"] for name, p in params.items()}
    assert sch["woType"]["default"] == "N"
    for mode in ("includeClosed", "includeArchive"):
        assert (sch[mode]["minimum"], sch[mode]["maximum"], sch[mode]["default"]) == (0, 2, 0), mode
    assert sch["search"]["default"] == ""
    assert (sch["limit"]["minimum"], sch["limit"]["maximum"], sch["limit"]["default"]) == (1, 1000, 200)
    assert (sch["offset"]["minimum"], sch["offset"]["default"]) == (0, 0)


def test_workorders_wo_id_is_a_positive_integer_path_param(schema: dict[str, Any]) -> None:
    for path in WO_PATHS[1:]:
        p = _wo_params(schema, path)["wo_id"]
        assert p["in"] == "path" and p["required"] is True
        assert p["schema"]["type"] == "integer" and p["schema"]["exclusiveMinimum"] == 0


def test_workorders_events_params(schema: dict[str, Any]) -> None:
    params = _wo_params(schema, WO_BASE + "/{wo_id}/events")
    assert set(params) == {"wo_id", "offset", "limit"}
    assert params["limit"]["schema"]["maximum"] == 1000 and params["limit"]["schema"]["default"] == 200


def test_workorders_list_response_shape(schema: dict[str, Any]) -> None:
    body = _wo_200(schema, WO_BASE)
    assert set(body["properties"]) == {"rows", "count", "more", "filters"} | ENVELOPE
    assert body.get("additionalProperties") is False
    assert set(body["required"]) == set(body["properties"])


def test_workorders_record_forbids_extras_and_carries_every_key(schema: dict[str, Any]) -> None:
    from app.workorders.schemas import WoRecord  # noqa: PLC0415 - after env is set

    body = _wo_200(schema, WO_BASE + "/{wo_id}")
    assert body.get("additionalProperties") is False
    assert set(body["properties"]) == set(WoRecord.model_fields)
    assert set(body["required"]) == set(WoRecord.model_fields)  # every key required - no optional drift
    assert set(body["properties"]) >= ENVELOPE


def test_workorders_errors_are_documented_flat(schema: dict[str, Any]) -> None:
    responses = _wo_get(schema, WO_BASE)["responses"]
    assert "400" in responses and "401" in responses
    for path in WO_PATHS[1:]:
        responses = _wo_get(schema, path)["responses"]
        assert "404" in responses and "401" in responses, path
        ref = responses["404"]["content"]["application/json"]["schema"]["$ref"]
        assert {"ok", "code", "message"} <= set(_resolve(schema, ref)["properties"])


def test_workorders_no_from_underscore_anywhere(schema: dict[str, Any]) -> None:
    for path in WO_PATHS:
        assert "from_" not in json.dumps(_wo_get(schema, path)), path
    assert "from_" not in json.dumps(schema["components"])


def test_info_version_is_the_app_version(schema: dict[str, Any]) -> None:
    from app.main import __version__ as app_version  # noqa: PLC0415 - after env is set

    assert schema["info"]["version"] == app_version == "0.5.0"
