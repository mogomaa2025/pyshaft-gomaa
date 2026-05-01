"""PyShaft API Inspector — I/O manager for saving/loading API workflows."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from pyshaft.recorder.api_inspector.api_models import (
    ApiAssertion,
    ApiEnvironment,
    ApiExtraction,
    ApiFolder,
    ApiRequestStep,
    ApiWorkflow,
    AssertionType,
    AuthType,
    HttpMethod,
    PipelineOp,
    PipelineStep,
)

logger = logging.getLogger("pyshaft.recorder.api_inspector.io")


def save_workflow(workflow: ApiWorkflow, path: str | Path) -> None:
    """Save an API workflow to a JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = _workflow_to_dict(workflow)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    logger.info("Workflow saved: %s", path)


def load_workflow(path: str | Path) -> ApiWorkflow:
    """Load an API workflow from a JSON file."""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return _dict_to_workflow(data)


def _workflow_to_dict(workflow: ApiWorkflow) -> dict[str, Any]:
    """Convert workflow to a serializable dict."""
    return {
        "name": workflow.name,
        "base_url": workflow.base_url,
        "variables": workflow.variables,
        "items": [_item_to_dict(it) for it in workflow.items],
        "environments": [
            {"name": e.name, "variables": e.variables, "base_url": e.base_url}
            for e in workflow.environments
        ],
        "current_environment_index": workflow.current_environment_index,
        "global_headers": workflow.global_headers,
        "use_session": workflow.use_session,
    }


def _item_to_dict(item: ApiFolder | ApiRequestStep) -> dict[str, Any]:
    """Recursively convert item to dict."""
    if isinstance(item, ApiFolder):
        return {
            "type": "folder",
            "name": item.name,
            "items": [_item_to_dict(it) for it in item.items],
        }
    else:
        return {
            "type": "request",
            **_step_to_dict(item),
        }


def _step_to_dict(step: ApiRequestStep) -> dict[str, Any]:
    """Convert a single step to dict, including last run state."""
    return {
        "name": step.name,
        "method": step.method.value,
        "url": step.url,
        "endpoint": step.endpoint,
        "headers": step.headers,
        "payload": step.payload,
        "auth_type": step.auth_type.value,
        "auth_value": step.auth_value,
        "auth_key": step.auth_key,
        "expected_status": step.expected_status,
        "assertions": [
            {"type": a.type.value, "path": a.path, "expected": a.expected, "expected_type": a.expected_type}
            for a in step.assertions
        ],
        "extractions": [
            {"variable_name": e.variable_name, "json_path": e.json_path, "cast_type": e.cast_type}
            for e in step.extractions
        ],
        "pipeline": [
            {"operation": p.operation.value, "path": p.path, "expression": p.expression, "key": p.key}
            for p in step.pipeline
        ],
        "loop_variable": step.loop_variable,
        "loop_payload_key": step.loop_payload_key,
        "query_params": step.query_params,
        "b64_param_name": step.b64_param_name,
        "b64_param_json": step.b64_param_json,
        "b64_param_encoded": step.b64_param_encoded,
        # Persist last run state
        "last_status": step.last_status,
        "last_response": step.last_response,
        "last_duration_ms": step.last_duration_ms,
        "last_error": step.last_error,
    }


def _dict_to_workflow(data: dict[str, Any]) -> ApiWorkflow:
    """Convert dict back to ApiWorkflow."""
    # Handle old format (steps list) vs new format (items list)
    if "steps" in data and "items" not in data:
        items = [_dict_to_step(s) for s in data["steps"]]
    else:
        items = [_dict_to_item(it) for it in data.get("items", [])]

    environments = [
        ApiEnvironment(
            name=e["name"],
            variables=e.get("variables", {}),
            base_url=e.get("base_url", ""),
        )
        for e in data.get("environments", [])
    ]
    
    return ApiWorkflow(
        name=data.get("name", "API Workflow"),
        base_url=data.get("base_url", ""),
        items=items,
        variables=data.get("variables", {}),
        environments=environments,
        current_environment_index=data.get("current_environment_index", -1),
        global_headers=data.get("global_headers", {}),
        use_session=data.get("use_session", True),
    )


def _dict_to_item(data: dict[str, Any]) -> ApiFolder | ApiRequestStep:
    """Recursively convert dict back to item."""
    if data.get("type") == "folder":
        return ApiFolder(
            name=data.get("name", "New Folder"),
            items=[_dict_to_item(it) for it in data.get("items", [])],
        )
    else:
        return _dict_to_step(data)


def _dict_to_step(data: dict[str, Any]) -> ApiRequestStep:
    """Convert dict to ApiRequestStep, restoring last run state."""
    assertions = [
        ApiAssertion(
            type=AssertionType(a["type"]),
            path=a.get("path", ""),
            expected=a.get("expected", ""),
            expected_type=a.get("expected_type", ""),
        )
        for a in data.get("assertions", [])
    ]

    extractions = [
        ApiExtraction(
            variable_name=e["variable_name"],
            json_path=e["json_path"],
            cast_type=e.get("cast_type", "str"),
        )
        for e in data.get("extractions", [])
    ]

    pipeline = [
        PipelineStep(
            operation=PipelineOp(p["operation"]),
            path=p.get("path", ""),
            expression=p.get("expression", ""),
            key=p.get("key", ""),
        )
        for p in data.get("pipeline", [])
    ]

    return ApiRequestStep(
        name=data.get("name", "Request"),
        method=HttpMethod(data.get("method", "GET")),
        url=data.get("url", ""),
        endpoint=data.get("endpoint", ""),
        headers=data.get("headers", {}),
        payload=data.get("payload", ""),
        auth_type=AuthType(data.get("auth_type", "none")),
        auth_value=data.get("auth_value", ""),
        auth_key=data.get("auth_key", ""),
        expected_status=data.get("expected_status", 200),
        assertions=assertions,
        extractions=extractions,
        pipeline=pipeline,
        loop_variable=data.get("loop_variable", ""),
        loop_payload_key=data.get("loop_payload_key", ""),
        query_params=data.get("query_params", {}),
        b64_param_name=data.get("b64_param_name", ""),
        b64_param_json=data.get("b64_param_json", ""),
        b64_param_encoded=data.get("b64_param_encoded", ""),
        # Restore last run state
        last_status=data.get("last_status"),
        last_response=data.get("last_response"),
        last_duration_ms=data.get("last_duration_ms", 0.0),
        last_error=data.get("last_error"),
    )
