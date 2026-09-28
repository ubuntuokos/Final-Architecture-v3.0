#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fa3_system_one_reflex import ESCALATE, FINISH, GOAL_REACHED, MAX_OPTIONS, NEXT_ACTION

MCP_AUTHORITY = "FA3-AUTH-MCP-GATEWAY-001"
RESERVED = {ESCALATE, FINISH, GOAL_REACHED, NEXT_ACTION}


@dataclass(frozen=True)
class McpCompileResult:
    action_candidates: list[dict[str, Any]]
    unsupported: dict[str, dict[str, str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "fa3.system-one-mcp-action-catalogue.v1",
            "authority": False,
            "execution_performed": False,
            "final_policy_owner": MCP_AUTHORITY,
            "action_candidates": list(self.action_candidates),
            "unsupported": dict(self.unsupported),
        }


def _risk(annotations: dict[str, Any]) -> str:
    if annotations.get("destructiveHint") is True:
        return "destructive"
    if annotations.get("readOnlyHint") is True:
        return "read"
    return "write"


def _parameter(name: str, schema: dict[str, Any], required: bool) -> dict[str, Any] | None:
    instructions = str(schema.get("description") or f"Choose {name}.")
    out: dict[str, Any] = {"instructions": instructions}
    enum = schema.get("enum")
    if isinstance(enum, list) and enum:
        if len(enum) > MAX_OPTIONS:
            return None
        out["kind"] = "choices"
        out["choices"] = {str(value): str(value) for value in enum}
    elif isinstance(schema.get("x-fa3-candidate-source"), str) and schema["x-fa3-candidate-source"]:
        out["kind"] = "candidates"
        out["source"] = schema["x-fa3-candidate-source"]
    elif schema.get("type") == "boolean":
        out["kind"] = "flag"
    elif isinstance(schema.get("x-fa3-levels"), list):
        levels = schema["x-fa3-levels"]
        if not 2 <= len(levels) <= 10 or any(not isinstance(x, str) or not x for x in levels):
            return None
        out["kind"] = "levels"
        out["levels"] = list(levels)
    else:
        return None
    if not required:
        out["optional"] = True
        out["default"] = schema.get("default")
    return out


def compile_mcp_tools(tools: list[dict[str, Any]]) -> McpCompileResult:
    """Compile enumerable MCP tools to bounded Decision Fabric action candidates.

    This function never executes a tool. A tool with any free-text or otherwise
    non-enumerable parameter is reported as unsupported rather than weakened.
    """
    if not isinstance(tools, list):
        raise TypeError("tools must be a list")

    actions: list[dict[str, Any]] = []
    unsupported: dict[str, dict[str, str]] = {}
    seen: set[str] = set()

    for index, tool in enumerate(tools):
        if not isinstance(tool, dict):
            unsupported[f"#{index}"] = {
                "reason_code": "MCP_TOOL_INVALID",
                "message": "tool descriptor must be an object",
            }
            continue
        name = tool.get("name")
        if not isinstance(name, str) or not name:
            unsupported[f"#{index}"] = {
                "reason_code": "MCP_TOOL_NAME_INVALID",
                "message": "non-empty tool name required",
            }
            continue
        if name in seen:
            unsupported[name] = {
                "reason_code": "MCP_TOOL_DUPLICATE",
                "message": "duplicate tool name",
            }
            continue
        seen.add(name)
        if name in RESERVED or "__" in name:
            unsupported[name] = {
                "reason_code": "MCP_TOOL_NAME_RESERVED",
                "message": "tool name conflicts with System One reserved identifiers",
            }
            continue

        schema = tool.get("inputSchema", tool.get("input_schema", {"type": "object", "properties": {}}))
        if not isinstance(schema, dict) or schema.get("type", "object") != "object":
            unsupported[name] = {
                "reason_code": "MCP_INPUT_SCHEMA_UNSUPPORTED",
                "message": "only object input schemas are supported",
            }
            continue
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(properties, dict) or not isinstance(required, list):
            unsupported[name] = {
                "reason_code": "MCP_INPUT_SCHEMA_INVALID",
                "message": "properties must be an object and required must be a list",
            }
            continue
        required_set = {str(x) for x in required}

        parameters: dict[str, dict[str, Any]] = {}
        failure: tuple[str, str] | None = None
        for pname, pschema in properties.items():
            if (
                not isinstance(pname, str)
                or not pname
                or "__" in pname
                or not isinstance(pschema, dict)
            ):
                failure = (
                    "MCP_PARAMETER_SCHEMA_INVALID",
                    f"parameter {pname!r} has an invalid schema or reserved name",
                )
                break
            compiled = _parameter(pname, pschema, pname in required_set)
            if compiled is None:
                failure = (
                    "MCP_PARAMETER_NOT_FINITE",
                    f"parameter {pname!r} is not representable as a finite System One value set",
                )
                break
            parameters[pname] = compiled

        if failure is not None:
            unsupported[name] = {"reason_code": failure[0], "message": failure[1]}
            continue

        annotations = tool.get("annotations") or {}
        if not isinstance(annotations, dict):
            annotations = {}
        actions.append({
            "id": name,
            "description": str(tool.get("description") or name),
            "metadata": {
                "origin": "MCP",
                "mcp_tool_name": name,
                "risk": _risk(annotations),
                "parameters": parameters,
                "execution_authority": MCP_AUTHORITY,
            },
        })

    return McpCompileResult(actions, unsupported)
