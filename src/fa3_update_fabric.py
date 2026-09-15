#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config/fa3-update-policy.json"
STATE_DIR = ROOT / "state/update"
RESTART_STATE = STATE_DIR / "restart-required.json"


def load_policy() -> dict[str, Any]:
    try:
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"FA3 update policy unavailable/invalid: {exc}")


def classify(component: dict[str, Any]) -> dict[str, Any]:
    policy = load_policy()
    source_class = component.get("class", "EXTERNAL_PROVIDER")
    security = bool(component.get("security_update", False))
    host_critical = source_class == "HOST_CRITICAL" or component.get("impact") == "HOST_CRITICAL"
    result = {
        "component": component.get("id", "unknown"),
        "class": source_class,
        "channel": component.get("channel", policy["default_channel"]),
        "security_update": security,
        "host_critical": host_critical,
        "auto_install": False,
        "stage": True,
        "validation_required": True,
        "user_activation_required": False,
        "reason": "NORMAL_VALIDATED_UPDATE",
    }
    if security and source_class == "OS_MANAGED" and not host_critical:
        result.update(auto_install=True, stage=False, validation_required=True, reason="LOW_RISK_OS_SECURITY_BACKGROUND")
    elif security and host_critical:
        result.update(auto_install=False, stage=True, user_activation_required=True, reason="HOST_CRITICAL_SECURITY_STAGE")
    elif security and source_class == "EXTERNAL_PROVIDER":
        result.update(auto_install=False, stage=True, validation_required=True, reason="EXTERNAL_SECURITY_VALIDATE_THEN_PROMOTE")
    elif host_critical:
        result.update(auto_install=False, stage=True, user_activation_required=True, reason="HOST_CRITICAL_MAINTENANCE")
    if component.get("large_model_download"):
        result.update(auto_install=False, user_activation_required=True, reason="MODEL_DOWNLOAD_EXPLICIT_APPROVAL")
    return result


def plan(components: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [classify(c) for c in components]
    return {
        "schema": "fa3.update-plan.v1",
        "blind_update_all": False,
        "check_all": True,
        "generated_unix": int(time.time()),
        "updates": rows,
        "automatic": [r["component"] for r in rows if r["auto_install"]],
        "review_required": [r["component"] for r in rows if r["user_activation_required"]],
    }


def set_restart_required(kind: str, updated_components: list[str], active_workloads: list[str]) -> dict[str, Any]:
    if kind not in {"service", "host"}:
        raise SystemExit("restart kind must be service or host")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        "schema": "fa3.restart-state.v1",
        "state": "RESTART_REQUIRED_SERVICE" if kind == "service" else "REBOOT_REQUIRED_HOST",
        "kind": kind,
        "updated_components": updated_components,
        "active_protected_workloads": active_workloads,
        "recommended_choice": "WHEN_IDLE_SAFE",
        "choices": ["RESTART_NOW", "WHEN_IDLE_SAFE", "SCHEDULE", "LATER"],
        "forced_reboot_allowed": False,
        "resolved": False,
        "created_unix": int(time.time()),
    }
    RESTART_STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


def choose_restart(choice: str, active_workloads: list[str], schedule: str | None) -> dict[str, Any]:
    policy = load_policy()
    if choice not in policy["restart"]["choices"]:
        raise SystemExit(f"unsupported restart choice: {choice}")
    if not RESTART_STATE.exists():
        raise SystemExit("no restart-required state exists")
    state = json.loads(RESTART_STATE.read_text(encoding="utf-8"))
    state["active_protected_workloads"] = active_workloads
    state["choice"] = choice
    if choice == "RESTART_NOW":
        if active_workloads:
            state["state"] = "DEFERRED"
            state["action"] = "POSTPONE_AND_NOTIFY"
        else:
            state["state"] = "READY_TO_RESTART"
            state["action"] = "RESTART_ALLOWED"
    elif choice == "WHEN_IDLE_SAFE":
        state["state"] = "WAITING_FOR_IDLE" if active_workloads else "READY_TO_RESTART"
        state["action"] = "WAIT_FOR_PROTECTED_WORKLOADS" if active_workloads else "RESTART_ALLOWED"
    elif choice == "SCHEDULE":
        if not schedule:
            raise SystemExit("SCHEDULE requires --schedule")
        state["state"] = "SCHEDULED"
        state["scheduled_for"] = schedule
        state["action"] = "POSTPONE_IF_PROTECTED_WORKLOAD_ACTIVE"
    else:
        state["state"] = "DEFERRED"
        state["action"] = "KEEP_VISIBLE_AND_REMIND"
    state["resolved"] = False
    state["updated_unix"] = int(time.time())
    RESTART_STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 update policy engine")
    sub = parser.add_subparsers(dest="command", required=True)
    p_plan = sub.add_parser("plan")
    p_plan.add_argument("--input", required=True, help="JSON file containing an array or {components: [...]} object")
    p_req = sub.add_parser("require-restart")
    p_req.add_argument("--kind", choices=["service", "host"], required=True)
    p_req.add_argument("--component", action="append", default=[])
    p_req.add_argument("--active-workload", action="append", default=[])
    p_choose = sub.add_parser("choose-restart")
    p_choose.add_argument("choice", choices=["RESTART_NOW", "WHEN_IDLE_SAFE", "SCHEDULE", "LATER"])
    p_choose.add_argument("--active-workload", action="append", default=[])
    p_choose.add_argument("--schedule")
    sub.add_parser("restart-status")
    args = parser.parse_args()
    if args.command == "plan":
        raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
        components = raw if isinstance(raw, list) else raw.get("components", [])
        print(json.dumps(plan(components), indent=2))
    elif args.command == "require-restart":
        print(json.dumps(set_restart_required(args.kind, args.component, args.active_workload), indent=2))
    elif args.command == "choose-restart":
        print(json.dumps(choose_restart(args.choice, args.active_workload, args.schedule), indent=2))
    elif args.command == "restart-status":
        if RESTART_STATE.exists():
            print(RESTART_STATE.read_text(encoding="utf-8"), end="")
        else:
            print(json.dumps({"state": "NONE", "resolved": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
