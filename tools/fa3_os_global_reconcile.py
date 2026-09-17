#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import fa3_buzz_global_reconcile as common  # noqa: E402

PROFILE_ID = "FA3-OS-001"
PRIVACY_PROFILE_ID = "FA3-OS-POLICY-001"
EVENT_CONTRACT_ID = "FA3-OS-EVENT-001"
GATESET_ID = "FA3-OS-EVENT-PRIVACY-GATESET-001"
LEDGER_AUTHORITY = "FA3-JOURNAL-001"
JOURNAL_CONTRACT_ID = "FA3-JOURNAL-CONTRACTS-001"
CAPABILITY_COUNT = 143
POLICY = "canonical/enforcement-policy.json"
ENFORCEMENT = "canonical/fa3-os-event-privacy-enforcement.json"
RELEASE = common.RELEASE
FA3_ENFORCE = "src/fa3_enforce.py"
PERMANENT_WORKFLOW = ".github/workflows/fa3-permanent-enforcement.yml"
RECONCILIATION_STATUS = "GLOBAL_RELEASE_INVENTORY_RECONCILED_CANONICAL_GATE_ENFORCED_RUNTIME_PROJECTION_ONLY"


def load(rel: str) -> dict[str, Any]:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def write(rel: str, obj: dict[str, Any]) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def patch_policy() -> None:
    policy = load(POLICY)
    if policy.get("canonical_capability_count") != CAPABILITY_COUNT:
        raise RuntimeError("FA3 capability count must remain exactly 143")
    gates = policy.setdefault("mandatory_reference_gates", [])
    if GATESET_ID not in gates:
        gates.append(GATESET_ID)
    if len(gates) != len(set(gates)):
        raise RuntimeError("mandatory_reference_gates must remain unique")
    enforcement = load(ENFORCEMENT)
    policy["fa3_os_profile_id"] = PROFILE_ID
    policy["fa3_os_privacy_profile_id"] = PRIVACY_PROFILE_ID
    policy["fa3_os_event_contract_id"] = EVENT_CONTRACT_ID
    policy["fa3_os_ledger_authority"] = LEDGER_AUTHORITY
    policy["fa3_os_canonical_event_envelope"] = JOURNAL_CONTRACT_ID
    policy["fa3_os_mandatory_p0_rules"] = list(enforcement.get("p0_invariants", []))
    write(POLICY, policy)


def patch_fa3_enforce() -> None:
    path = ROOT / FA3_ENFORCE
    text = path.read_text(encoding="utf-8")

    import_line = "from fa3_os_event_privacy_gate import gate as fa3_os_event_privacy_gate\n"
    if import_line not in text:
        anchor = "from fa3_openfx_interop_gate import gate as openfx_interop_gate\n"
        if anchor not in text:
            raise RuntimeError("fa3_enforce import anchor missing")
        text = text.replace(anchor, anchor + import_line, 1)

    policy_check = (
        "    if \"FA3-OS-EVENT-PRIVACY-GATESET-001\" not in pol.get(\"mandatory_reference_gates\",[]):\n"
        "        fs.append(finding(\"FA3-STATIC-104\",\"FA3 OS event/privacy gate is not bound into global enforcement policy\"))\n"
    )
    if policy_check not in text:
        anchor = "    if len(rows)!=CAPS or ids!=expected:\n"
        if anchor not in text:
            raise RuntimeError("fa3_enforce static policy anchor missing")
        text = text.replace(anchor, policy_check + "\n" + anchor, 1)

    gate_check = (
        "    fa3_os_ref=fa3_os_event_privacy_gate(root)\n"
        "    if fa3_os_ref[\"result\"]!=\"PASS\":\n"
        "        fs.append(finding(\"FA3-STATIC-105\",\"FA3 OS event/privacy substrate gate failed\",fa3_os_event_privacy_gate=fa3_os_ref))\n"
    )
    if gate_check not in text:
        anchor = "    result=\"PASS\" if not fs else \"FAIL\"\n"
        if anchor not in text:
            raise RuntimeError("fa3_enforce static gate anchor missing")
        text = text.replace(anchor, gate_check + "\n" + anchor, 1)

    command = '"fa3-os-event-privacy"'
    if command not in text:
        anchor = '"presenton-current-host","acceptance"'
        if anchor not in text:
            raise RuntimeError("fa3_enforce command-choice anchor missing")
        text = text.replace(anchor, '"presenton-current-host","fa3-os-event-privacy","acceptance"', 1)

    handler = (
        "        if a.command==\"fa3-os-event-privacy\":\n"
        "            x=fa3_os_event_privacy_gate(root); print(json.dumps(x,indent=2)); return OK if x[\"result\"]==\"PASS\" else BLOCKED\n"
    )
    if handler not in text:
        anchor = "        if a.command==\"acceptance\":\n"
        if anchor not in text:
            raise RuntimeError("fa3_enforce handler anchor missing")
        text = text.replace(anchor, handler + anchor, 1)

    path.write_text(text, encoding="utf-8")


def patch_permanent_workflow() -> None:
    path = ROOT / PERMANENT_WORKFLOW
    text = path.read_text(encoding="utf-8")
    gate_path = "src/fa3_os_event_privacy_gate.py"
    if gate_path not in text:
        anchor = "src/fa3_openfx_interop.py src/fa3_openfx_interop_gate.py"
        if anchor not in text:
            raise RuntimeError("permanent workflow syntax-check anchor missing")
        text = text.replace(anchor, anchor + " " + gate_path, 1)

    step = (
        "      - name: FA3 OS event/privacy substrate gate\n"
        "        run: ./bin/fa3-enforce fa3-os-event-privacy\n"
    )
    if step not in text:
        anchor = "      - name: Presenton provider/deployment/artifact regression gate\n"
        if anchor not in text:
            raise RuntimeError("permanent workflow gate-step anchor missing")
        text = text.replace(anchor, step + anchor, 1)

    path.write_text(text, encoding="utf-8")


def patch_release_semantics() -> None:
    release = load(RELEASE)
    policy = load(POLICY)
    release["mandatory_reference_gates"] = list(policy.get("mandatory_reference_gates", []))
    release["fa3_os_reconciliation"] = {
        "profile_id": PROFILE_ID,
        "privacy_profile_id": PRIVACY_PROFILE_ID,
        "event_contract_id": EVENT_CONTRACT_ID,
        "gateset_id": GATESET_ID,
        "ledger_authority": LEDGER_AUTHORITY,
        "canonical_event_envelope": JOURNAL_CONTRACT_ID,
        "classification": "P0_MUST_LOCAL_FIRST_PRIVACY_GOVERNED_CONTEXT_ACTIVITY_EPISODIC_MEMORY_OVERLAY",
        "reconciliation_status": RECONCILIATION_STATUS,
        "gate_status": "CI_ENFORCED",
        "runtime_authority": False,
        "historical_truth_authority": False,
        "resume_plan_execution_authority": False,
        "privacy_gate_before_persistence": True,
        "keylogging_default": "DENY",
        "generic_clipboard_default": "DENY",
        "generic_screen_capture_default": "DENY",
        "terminal_capture_default": "METADATA_ONLY",
        "derived_memory_authoritative": False,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": CAPABILITY_COUNT,
    }
    note = (
        "FA3-OS-001 and FA3-OS-POLICY-001 are globally reconciled as a local-first privacy-governed "
        "context/activity/episodic-memory overlay on FA3-JOURNAL-001. The Journal remains the sole "
        "canonical workstation event/history ledger; derived memory remains rebuildable and non-authoritative, "
        "Resume Plan has no execution authority, capability count stays 143 and no architectural authority is added."
    )
    notes = release.setdefault("review_notes", [])
    if note not in notes:
        notes.append(note)
    write(RELEASE, release)


def prepare_only() -> None:
    patch_policy()
    patch_fa3_enforce()
    patch_permanent_workflow()


def projection_only(snapshot_head: str) -> None:
    snapshot = common.git("rev-parse", "--verify", f"{snapshot_head}^{{commit}}")
    current = common.git("rev-parse", "HEAD")
    if snapshot != current:
        raise RuntimeError("projection snapshot must equal clean checked-out HEAD before regeneration")
    dirty = common.dirty_release_surface_paths()
    if dirty:
        raise RuntimeError(f"projection-only requires clean committed release surface: {dirty}")

    patch_release_semantics()
    common.regenerate_release(snapshot)

    release = load(RELEASE)
    verification = release.setdefault("manifest_verification", {})
    verification["fa3_os_reconciliation_generator"] = "tools/fa3_os_global_reconcile.py"
    verification["fa3_os_deterministic_regeneration_pass"] = True
    verification["fa3_os_snapshot_head"] = snapshot
    write(RELEASE, release)

    dirty_after = common.dirty_release_surface_paths()
    if dirty_after != [RELEASE]:
        raise RuntimeError(
            "FA3 OS projection-only mode may modify exactly the unified release projection; observed: "
            + ", ".join(dirty_after)
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FA3 OS deterministic global reconciliation")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--projection-only", action="store_true")
    parser.add_argument("--snapshot-head")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.prepare_only:
        if args.snapshot_head:
            raise RuntimeError("--snapshot-head is projection-only")
        prepare_only()
        print(json.dumps({
            "result": "PASS",
            "mode": "PREPARE_ONLY",
            "profile_id": PROFILE_ID,
            "privacy_profile_id": PRIVACY_PROFILE_ID,
            "gateset_id": GATESET_ID,
        }, indent=2))
        return 0

    snapshot_head = args.snapshot_head or common.git("rev-parse", "HEAD")
    projection_only(snapshot_head)
    print(json.dumps({
        "result": "PASS",
        "mode": "PROJECTION_ONLY",
        "profile_id": PROFILE_ID,
        "snapshot_head": snapshot_head,
        "reconciliation_status": RECONCILIATION_STATUS,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
