#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from fa3_agent_instructions import (
    META_SCHEMA,
    NON_CANONICAL_AUTHORITY,
    PROFILE_ID,
    parse_metadata,
    resolve_instruction_chain,
)

PROFILE_PATH = "canonical/profiles/FA3-AGENT-INSTRUCTIONS-001.json"
CONTRACT_PATH = "canonical/contracts/FA3-AGENT-INSTRUCTION-CONTRACTS-001.json"
GATE_RECORD_PATH = "canonical/FA3-GATE-AGENT-INSTRUCTIONS-001.json"
HARDWARE_CONTRACT_PATH = "canonical/contracts/FA3-HARDWARE-DISCOVERY-CONTRACTS-001.json"
RELEASE_BASELINE_PATH = "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json"
ENFORCEMENT_POLICY_PATH = "canonical/enforcement-policy.json"
CONTRACT_ID = "FA3-AGENT-INSTRUCTION-CONTRACTS-001"
GATE_ID = "FA3-GATE-AGENT-INSTRUCTIONS-001"
GATESET_ID = "FA3-AGENT-INSTRUCTIONS-GATESET-001"

AUTHORITY_ESCALATION_PATTERNS = (
    re.compile(r"\bAGENTS\.md\s+(?:is|becomes|shall be)\s+(?:the\s+)?(?:canonical|authoritative|source of truth)\b", re.I),
    re.compile(r"\bthis file\s+(?:is|becomes|shall be)\s+(?:the\s+)?(?:canonical|authoritative|source of truth)\b", re.I),
)
HARDWARE_REGRESSION_PATTERNS = (
    re.compile(r"\b(?:NVIDIA|AMD|Intel)\b[^\n]{0,80}\b(?:is|required|mandatory)\b[^\n]{0,40}\b(?:global|baseline|required)\b", re.I),
    re.compile(r"\b(?:CUDA|ROCm|Level Zero|Vulkan|ZLUDA)\b[^\n]{0,60}\b(?:is|required|mandatory)\b[^\n]{0,40}\b(?:global|baseline|required)\b", re.I),
    re.compile(r"\b(?:minimum|at least)\s+(?:of\s+)?1\s+(?:GPU|accelerator)\b", re.I),
    re.compile(r"\blogical\s+CPU(?:s|\s+processors)?\s+(?:are|equal)\s+physical\s+(?:CPU\s+)?cores\b", re.I),
)
BYPASS_PATTERNS = (
    re.compile(r"\b(?:may|can|should)\s+(?:skip|bypass|disable|weaken)\s+(?:the\s+)?(?:test|tests|gate|gates|security|approval|evidence)\b", re.I),
    re.compile(r"\b(?:skip|bypass)\s+(?:required\s+)?(?:tests?|gates?)\s+to\s+(?:pass|merge)\b", re.I),
)
FABRICATION_PATTERNS = (
    re.compile(r"\b(?:may|can|should)\s+(?:fabricate|invent|fake)\s+(?:evidence|receipt|receipts|PASS|output)\b", re.I),
    re.compile(r"\bmark\s+(?:it|the\s+result)\s+(?:PASS|VERIFIED)\s+without\s+(?:running|executing|evidence)\b", re.I),
)
SKIP_DIR_NAMES = {".git","__pycache__",".pytest_cache",".mypy_cache"}
SKIP_TOP_LEVEL = {"reports","acceptance","promotion"}

def loadj(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))

def _check(name: str, ok: bool, detail: str) -> dict[str, str]:
    return {"name":name,"status":"PASS" if ok else "FAIL","detail":detail}

def validate_projection_text(path: str, text: str, *, expected_scope: str | None = None) -> list[str]:
    errors: list[str] = []
    meta, meta_errors = parse_metadata(text)
    errors.extend(meta_errors)
    if meta is None:
        return errors
    required = {"schema","profile","scope","authority"}
    missing = sorted(required - set(meta))
    if missing:
        errors.append("MISSING_METADATA_FIELDS:" + ",".join(missing))
    if meta.get("schema") != META_SCHEMA:
        errors.append("METADATA_SCHEMA_MISMATCH")
    if meta.get("profile") != PROFILE_ID:
        errors.append("PROFILE_ID_MISMATCH")
    if meta.get("authority") != NON_CANONICAL_AUTHORITY:
        errors.append("AUTHORITY_ESCALATION")
    if expected_scope is not None and meta.get("scope") != expected_scope:
        errors.append(f"SCOPE_MISMATCH:{meta.get('scope')}!={expected_scope}")
    for pattern in AUTHORITY_ESCALATION_PATTERNS:
        if pattern.search(text):
            errors.append("AUTHORITY_ESCALATION_TEXT"); break
    for pattern in HARDWARE_REGRESSION_PATTERNS:
        if pattern.search(text):
            errors.append("HARDWARE_BASELINE_REGRESSION"); break
    for pattern in BYPASS_PATTERNS:
        if pattern.search(text):
            errors.append("GATE_TEST_SECURITY_BYPASS_INSTRUCTION"); break
    for pattern in FABRICATION_PATTERNS:
        if pattern.search(text):
            errors.append("FABRICATED_EVIDENCE_INSTRUCTION"); break
    if "Canonical authority: repository canonical records and executable gates." not in text:
        errors.append("MISSING_CANONICAL_AUTHORITY_BOUNDARY")
    if "Projection authority: none." not in text:
        errors.append("MISSING_PROJECTION_AUTHORITY_BOUNDARY")
    return errors

def _discover_agent_files(root: Path) -> list[str]:
    found = []
    for path in root.rglob("AGENTS.md"):
        rel = path.relative_to(root)
        if not rel.parts:
            continue
        if rel.parts[0] in SKIP_TOP_LEVEL or any(part in SKIP_DIR_NAMES for part in rel.parts):
            continue
        found.append(rel.as_posix())
    return sorted(found)

def evaluate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    checks: list[dict[str, str]] = []
    required_files = [
        PROFILE_PATH,CONTRACT_PATH,GATE_RECORD_PATH,HARDWARE_CONTRACT_PATH,
        RELEASE_BASELINE_PATH,ENFORCEMENT_POLICY_PATH,
    ]
    missing_core = [p for p in required_files if not (root / p).is_file()]
    checks.append(_check("core-records-present",not missing_core,f"missing={missing_core}"))
    if missing_core:
        return {
            "schema":"fa3.agent-instruction-gate-report.v1","gate_id":GATESET_ID,
            "executable_gate_id":GATE_ID,"result":"FAIL","fail_closed":True,
            "current_host_runtime_promotion_claim":False,"checks":checks,
            "findings":[{"code":"MISSING_CORE_RECORD","paths":missing_core}],
        }

    profile = loadj(root,PROFILE_PATH)
    contract = loadj(root,CONTRACT_PATH)
    gate_record = loadj(root,GATE_RECORD_PATH)
    hardware = loadj(root,HARDWARE_CONTRACT_PATH)
    baseline = loadj(root,RELEASE_BASELINE_PATH)
    enforcement = loadj(root,ENFORCEMENT_POLICY_PATH)
    capability_count = baseline.get("current_release_capability_count")

    profile_ok = (
        profile.get("id")==PROFILE_ID and profile.get("status")=="CANONICAL"
        and profile.get("priority")=="P0" and profile.get("requirement")=="MUST"
        and profile.get("parent_profile")=="FA3-AGENT-EXEC-001"
        and profile.get("new_capability") is False and profile.get("new_architectural_authority") is False
        and profile.get("capability_count")==capability_count
        and profile.get("authority_model",{}).get("projection_is_authority") is False
        and profile.get("authority_model",{}).get("project_instructions_are_untrusted_scoped_context") is True
        and profile.get("format_compatibility",{}).get("upstream_code_dependency") is False
        and profile.get("format_compatibility",{}).get("vendored_upstream_code") is False
    )
    checks.append(_check("profile-boundary",profile_ok,"native projection preserves capability and authority boundaries"))

    contract_ok = (
        contract.get("id")==CONTRACT_ID and contract.get("parent_profile")=="FA3-AGENT-EXEC-001"
        and contract.get("projection_profile")==PROFILE_ID
        and contract.get("new_capability") is False and contract.get("new_architectural_authority") is False
        and contract.get("capability_count")==capability_count
        and contract.get("metadata_contract",{}).get("authority_value")==NON_CANONICAL_AUTHORITY
        and contract.get("resolution_semantics",{}).get("projection_may_override_canonical_record") is False
        and contract.get("resolution_semantics",{}).get("projection_may_override_executable_gate") is False
        and contract.get("resolution_semantics",{}).get("sibling_scope_leakage") is False
    )
    checks.append(_check("contract-boundary",contract_ok,"projection cannot override canonical records or executable gates"))

    gate_ok = (
        gate_record.get("id")==GATE_ID and gate_record.get("gateset_id")==GATESET_ID
        and gate_record.get("profile_id")==PROFILE_ID and gate_record.get("contract_id")==CONTRACT_ID
        and gate_record.get("fail_closed") is True and gate_record.get("global_static_enforcement") is True
        and gate_record.get("mandatory_reference_gate") is True
        and gate_record.get("current_host_required") is False
        and gate_record.get("current_host_runtime_promotion_claim") is False
        and gate_record.get("new_capability") is False and gate_record.get("new_architectural_authority") is False
        and gate_record.get("capability_count")==capability_count
    )
    checks.append(_check("gate-record",gate_ok,"P0 static governance gate is fail-closed and non-runtime"))

    enforcement_ok = (
        GATESET_ID in enforcement.get("mandatory_reference_gates",[])
        and enforcement.get("agent_instruction_projection_profile_id")==PROFILE_ID
        and enforcement.get("agent_instruction_projection_gate_id")==GATESET_ID
        and enforcement.get("agent_instruction_projection_authority")==NON_CANONICAL_AUTHORITY
        and enforcement.get("agent_instruction_projection_fail_closed") is True
        and enforcement.get("agent_instruction_projection_current_host_claim") is False
    )
    checks.append(_check("global-enforcement-binding",enforcement_ok,"P0 gate is bound into global static enforcement policy"))

    envelope = hardware.get("portable_minimum_envelope",{})
    discovery = hardware.get("discovery_semantics",{})
    cpu_schema = hardware.get("descriptor_schemas",{}).get("cpu",{})
    hardware_ok = (
        hardware.get("id")=="FA3-HARDWARE-DISCOVERY-CONTRACTS-001"
        and discovery.get("accelerator_enumeration")=="DYNAMIC_0_TO_N"
        and envelope.get("accelerator_devices_min")==0
        and envelope.get("accelerator_vendor_pin")=="FORBIDDEN"
        and envelope.get("global_runtime_api_pin")=="FORBIDDEN"
        and "logical_cpus_total" in cpu_schema.get("required_counts",[])
        and "physical_cores_total" in cpu_schema.get("required_counts",[])
    )
    checks.append(_check("hardware-audit-binding",hardware_ok,"vendor/backend neutral 0..N accelerator baseline and CPU count distinction preserved"))

    expected = {
        item["path"]:item["scope"]
        for item in profile.get("required_projection_files",[])
        if item.get("path") and item.get("scope")
    }
    discovered = set(_discover_agent_files(root))
    expected_paths = set(expected)
    missing = sorted(expected_paths-discovered)
    unmanaged = sorted(discovered-expected_paths)
    checks.append(_check("required-projections-present",not missing,f"missing={missing}"))
    checks.append(_check("no-unmanaged-projections",not unmanaged,f"unmanaged={unmanaged}"))

    projection_errors: dict[str,list[str]] = {}
    for path,scope in sorted(expected.items()):
        full = root/path
        if full.is_file():
            errors = validate_projection_text(path,full.read_text(encoding="utf-8"),expected_scope=scope)
            if errors:
                projection_errors[path]=errors
    checks.append(_check("projection-content-policy",not projection_errors,f"errors={projection_errors}"))

    resolver_ok = True
    resolver_detail = "root and scoped resolution verified"
    try:
        src_chain = [doc.path for doc in resolve_instruction_chain(root,Path("src/fa3_agent_instructions.py"))]
        test_chain = [doc.path for doc in resolve_instruction_chain(root,Path("tests/test_agent_instructions_gate.py"))]
        resolver_ok = (
            src_chain==["AGENTS.md","src/AGENTS.md"]
            and test_chain==["AGENTS.md","tests/AGENTS.md"]
            and "tests/AGENTS.md" not in src_chain
            and "src/AGENTS.md" not in test_chain
        )
        resolver_detail = f"src={src_chain} tests={test_chain}"
    except Exception as exc:
        resolver_ok = False
        resolver_detail = f"{type(exc).__name__}:{exc}"
    checks.append(_check("scope-resolution",resolver_ok,resolver_detail))

    if missing: findings.append({"code":"MISSING_REQUIRED_PROJECTION","paths":missing})
    if unmanaged: findings.append({"code":"UNMANAGED_PROJECTION","paths":unmanaged})
    if projection_errors: findings.append({"code":"PROJECTION_POLICY_VIOLATION","errors":projection_errors})
    if not profile_ok: findings.append({"code":"PROFILE_BOUNDARY_VIOLATION"})
    if not contract_ok: findings.append({"code":"CONTRACT_BOUNDARY_VIOLATION"})
    if not gate_ok: findings.append({"code":"GATE_RECORD_VIOLATION"})
    if not enforcement_ok: findings.append({"code":"GLOBAL_ENFORCEMENT_BINDING_VIOLATION"})
    if not hardware_ok: findings.append({"code":"HARDWARE_AUDIT_BINDING_VIOLATION"})
    if not resolver_ok: findings.append({"code":"SCOPE_RESOLUTION_VIOLATION","detail":resolver_detail})

    passed = all(item["status"]=="PASS" for item in checks)
    return {
        "schema":"fa3.agent-instruction-gate-report.v1",
        "gate_id":GATESET_ID,"executable_gate_id":GATE_ID,
        "profile_id":PROFILE_ID,"contract_id":CONTRACT_ID,
        "capability_count":capability_count,
        "result":"PASS" if passed else "FAIL","fail_closed":True,
        "implementation_origin":"FA3_NATIVE_INDEPENDENT",
        "upstream_code_dependency":False,
        "current_host_runtime_promotion_claim":False,
        "checks":checks,
        "summary":{"passed":sum(item["status"]=="PASS" for item in checks),"total":len(checks)},
        "findings":findings,
    }

def gate(root: Path) -> dict[str, Any]:
    report = evaluate(root)
    out = root/"reports/agent-instructions-gate-report.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report

def main() -> int:
    parser=argparse.ArgumentParser(description="FA3 repository agent-instruction projection gate")
    parser.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    args=parser.parse_args()
    report=gate(Path(args.root))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report["result"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
