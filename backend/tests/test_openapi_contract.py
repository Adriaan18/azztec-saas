"""
Azztec_SaaS_test_openapi_contract_v1_0_0.py  ->  backend/tests/test_openapi_contract.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_S1d_Diag_Chunk_Spec_v1_0_0.md §6

Guards the PUBLISHED schema, not the runtime body. `from` is a Python keyword, so the contract key needs
Field(alias="from") on the model AND Query(alias="from") on the route parameter - two independent
declarations. Until this file only the runtime body was asserted (test_range_from_key_is_literal_from), so
a regression on the parameter alias would have surfaced as a 422 out of the generated TS client, one slice
later and a long way from its cause. Raw Log 2026-09-11 1.1.0 §7 calls this the third occurrence of the
trap; this is the second, pinned.

Reads app.openapi(). Never iterates router.routes - FastAPI 0.137 made that a tree of intermediate objects
(Landmines §A). Zero DB: building the schema opens no connection.

Changelog:
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
