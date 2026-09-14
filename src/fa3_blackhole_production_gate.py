#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

GATE_ID = "FA3-BLACKHOLE-PRODUCTION-GATESET-001"
ADMISSION_ID = "FA3-BLACKHOLE-PRODUCTION-ADMISSION-001"

REQUIRED_FILES = (
    "canonical/profiles/FA3-BLACKHOLE-CONTAINER-FABRIC-001.json",
    "canonical/profiles/FA3-CRYPTO-AUDIT-001.json",
    "canonical/contracts/FA3-BLACKHOLE-PRODUCTION-CONTRACTS-001.json",
    "canonical/FA3-BLACKHOLE-PRODUCTION-ADMISSION-001.json",
    "canonical/blackhole-egress-policy.json",
    "src/fa3_audit_logger.py",
    "src/fa3_hrb_cdi.py",
    "src/fa3_consent_vault.py",
    "deployment/blackhole/podman-compose.yaml",
    "deployment/blackhole/README.md",
    "deployment/blackhole/quadlet/fa3-internal.network",
    "deployment/blackhole/quadlet/fa3-egress.network",
    "deployment/blackhole/quadlet/fa3-blackhole-api.container.in",
    "deployment/blackhole/quadlet/fa3-litellm.container.in",
    "deployment/blackhole/quadlet/fa3-comfyui-worker.container.in",
    "deployment/blackhole/quadlet/fa3-egress-gateway.container.in",
    "deployment/blackhole/containers/comfyui.Containerfile",
    "deployment/blackhole/containers/egress-gateway.Containerfile",
    "deployment/blackhole/egress/squid.conf",
    "tests/test_fa3_audit_logger.py",
    "tests/test_fa3_hrb_cdi.py",
    "tests/test_fa3_consent_vault.py",
    "tests/test_fa3_blackhole_production_gate.py",
    "evidence/collect-blackhole-production-current-host.py",
    ".github/workflows/fa3-blackhole-production-static.yml",
    ".github/workflows/fa3-blackhole-production-current-host.yml",
)

CONTAINER_TEMPLATES = (
    "deployment/blackhole/quadlet/fa3-blackhole-api.container.in",
    "deployment/blackhole/quadlet/fa3-litellm.container.in",
    "deployment/blackhole/quadlet/fa3-comfyui-worker.container.in",
    "deployment/blackhole/quadlet/fa3-egress-gateway.container.in",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def static_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for idx, rel in enumerate(REQUIRED_FILES, 1):
        if not (root / rel).is_file():
            findings.append(_finding(f"BLACKHOLE-PROD-REF-{idx:03d}", f"missing artifact: {rel}"))
    if findings:
        return {"result": "FAIL", "findings": findings}

    profile = _load(root / "canonical/profiles/FA3-BLACKHOLE-CONTAINER-FABRIC-001.json")
    audit = _load(root / "canonical/profiles/FA3-CRYPTO-AUDIT-001.json")
    contract = _load(root / "canonical/contracts/FA3-BLACKHOLE-PRODUCTION-CONTRACTS-001.json")
    admission = _load(root / "canonical/FA3-BLACKHOLE-PRODUCTION-ADMISSION-001.json")
    egress_policy = _load(root / "canonical/blackhole-egress-policy.json")

    if profile.get("id") != "FA3-BLACKHOLE-CONTAINER-FABRIC-001" or profile.get("status") != "CANONICAL":
        findings.append(_finding("BLACKHOLE-PROD-CANON-001", "container fabric identity/status drift"))
    if profile.get("authority_binding") != "FA3-AUTH-HOST-RESOURCE-BROKER-001":
        findings.append(_finding("BLACKHOLE-PROD-CANON-002", "HRB authority binding missing"))
    if profile.get("runtime_model", {}).get("unscoped_gpu_access") is not False:
        findings.append(_finding("BLACKHOLE-PROD-CANON-003", "unscoped GPU access is not explicitly forbidden"))
    if audit.get("id") != "FA3-CRYPTO-AUDIT-001" or audit.get("ledger", {}).get("write_model") != "APPEND_ONLY":
        findings.append(_finding("BLACKHOLE-PROD-CANON-004", "crypto audit append-only invariant missing"))
    if audit.get("checkpoint", {}).get("production_truncation_anchor") != "EXTERNAL_ASYMMETRIC_OR_TPM_REQUIRED":
        findings.append(_finding("BLACKHOLE-PROD-CANON-005", "trusted external/TPM audit anchor is not mandatory"))
    if audit.get("privacy", {}).get("pii_in_immutable_payload_forbidden") is not True:
        findings.append(_finding("BLACKHOLE-PROD-CANON-006", "PII immutable-audit prohibition missing"))
    if audit.get("consent_vault", {}).get("plaintext_persistence_forbidden") is not True:
        findings.append(_finding("BLACKHOLE-PROD-CANON-010", "erasable encrypted consent vault policy missing"))
    invariants = set(contract.get("invariants", []))
    required_invariants = {
        "HRB_REMAINS_EXCLUSIVE_RESOURCE_LEASE_AUTHORITY",
        "PRODUCTION_GPU_ACCESS_MUST_USE_AUTHENTICATED_HRB_RECEIPT_AND_CDI",
        "PRODUCTION_IMAGES_MUST_BE_SHA256_DIGEST_PINNED",
        "LITELLM_EXTERNAL_EGRESS_MUST_TRAVERSE_POLICY_GATEWAY",
        "AUDIT_TRUNCATION_REQUIRES_EXTERNAL_OR_TPM_ANCHOR_DETECTION",
        "CURRENT_HOST_PRODUCTION_PASS_REQUIRES_EXECUTABLE_EVIDENCE",
    }
    if not required_invariants.issubset(invariants):
        findings.append(_finding("BLACKHOLE-PROD-CANON-007", "production contract invariant set incomplete"))
    if admission.get("status") not in {"PENDING_CURRENT_HOST", "PASS"}:
        findings.append(_finding("BLACKHOLE-PROD-CANON-008", "unexpected production admission state"))
    if admission.get("current_host_claim") is not False and admission.get("status") != "PASS":
        findings.append(_finding("BLACKHOLE-PROD-CANON-009", "unproven current-host claim"))
    if egress_policy.get("id") != "FA3-BLACKHOLE-EGRESS-POLICY-001" or egress_policy.get("default_action") != "DENY":
        findings.append(_finding("BLACKHOLE-PROD-EGRESS-004", "egress policy identity/default-deny drift"))
    if egress_policy.get("allow_external_paid_providers") is not False:
        findings.append(_finding("BLACKHOLE-PROD-EGRESS-005", "external paid providers must default disabled"))
    if egress_policy.get("policy_gateway_only") is not True or any(egress_policy.get("direct_egress", {}).values()):
        findings.append(_finding("BLACKHOLE-PROD-EGRESS-006", "workloads must not receive direct external egress"))

    internal = (root / "deployment/blackhole/quadlet/fa3-internal.network").read_text(encoding="utf-8")
    if "Internal=true" not in internal:
        findings.append(_finding("BLACKHOLE-PROD-NET-001", "workload network is not internal-only"))

    for idx, rel in enumerate(CONTAINER_TEMPLATES, 1):
        text = (root / rel).read_text(encoding="utf-8")
        for required in ("ReadOnly=true", "NoNewPrivileges=true", "DropCapability=all"):
            if required not in text:
                findings.append(_finding(f"BLACKHOLE-PROD-HARDEN-{idx:02d}", f"{rel} missing {required}"))
        if ":latest" in text:
            findings.append(_finding(f"BLACKHOLE-PROD-SUPPLY-{idx:02d}", f"{rel} contains mutable latest tag"))

    comfy = (root / "deployment/blackhole/quadlet/fa3-comfyui-worker.container.in").read_text(encoding="utf-8")
    if "AddDevice=@FA3_CDI_DEVICE@" not in comfy or "FA3_HRB_LEASE_ID=@FA3_HRB_LEASE_ID@" not in comfy:
        findings.append(_finding("BLACKHOLE-PROD-GPU-001", "ComfyUI worker is not HRB/CDI materialized"))
    if "NVIDIA_VISIBLE_DEVICES" in comfy or "CUDA_VISIBLE_DEVICES" in comfy:
        findings.append(_finding("BLACKHOLE-PROD-GPU-002", "raw CUDA/NVIDIA environment placement is forbidden"))

    litellm = (root / "deployment/blackhole/quadlet/fa3-litellm.container.in").read_text(encoding="utf-8")
    if "Secret=fa3-litellm-master-key,type=env,target=LITELLM_MASTER_KEY" not in litellm:
        findings.append(_finding("BLACKHOLE-PROD-SECRET-001", "LiteLLM master key is not a Podman secret"))
    if "HTTPS_PROXY=http://fa3-egress-gateway:3128" not in litellm:
        findings.append(_finding("BLACKHOLE-PROD-EGRESS-001", "LiteLLM is not bound to policy egress proxy"))
    if "Network=fa3-egress.network" in litellm:
        findings.append(_finding("BLACKHOLE-PROD-EGRESS-002", "LiteLLM has forbidden direct egress network access"))

    egress = (root / "deployment/blackhole/quadlet/fa3-egress-gateway.container.in").read_text(encoding="utf-8")
    if not all(x in egress for x in ("Network=fa3-internal.network", "Network=fa3-egress.network", "Secret=fa3-egress-allowlist")):
        findings.append(_finding("BLACKHOLE-PROD-EGRESS-003", "egress gateway network boundary incomplete"))

    compose = (root / "deployment/blackhole/podman-compose.yaml").read_text(encoding="utf-8")
    forbidden = (
        "NVIDIA_VISIBLE_DEVICES=all",
        "NVIDIA_VISIBLE_DEVICES: all",
        "CUDA_VISIBLE_DEVICES=0",
        "LITELLM_MASTER_KEY=FA3-",
        "FA3-SUPER-SECRET",
    )
    for token in forbidden:
        if token in compose:
            findings.append(_finding("BLACKHOLE-PROD-COMPOSE-001", f"development compose contains forbidden token: {token}"))
    if "DEVELOPMENT / INTEGRATION ONLY" not in compose:
        findings.append(_finding("BLACKHOLE-PROD-COMPOSE-002", "compose is not explicitly marked non-production"))

    audit_code = (root / "src/fa3_audit_logger.py").read_text(encoding="utf-8")
    for marker in ("fcntl.flock", "os.O_APPEND", "os.fsync", "hmac.compare_digest", "_verify_checkpoint_locked", "PII_KEYS"):
        if marker not in audit_code:
            findings.append(_finding("BLACKHOLE-PROD-AUDIT-001", f"audit implementation missing safety primitive: {marker}"))
    if "open(self.log_path, 'w')" in audit_code or 'open(self.log_path, "w")' in audit_code:
        findings.append(_finding("BLACKHOLE-PROD-AUDIT-002", "audit implementation rewrites the ledger"))

    hrb_code = (root / "src/fa3_hrb_cdi.py").read_text(encoding="utf-8")
    for marker in ("FA3-AUTH-HOST-RESOURCE-BROKER-001", "nvidia.com/gpu=", "verify_receipt_with_hrb", "require_digest_image"):
        if marker not in hrb_code:
            findings.append(_finding("BLACKHOLE-PROD-HRB-001", f"HRB/CDI implementation missing: {marker}"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def evaluate_current_host_receipt(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {
            "result": "PENDING_CURRENT_HOST",
            "reason": "No executable current-host production admission receipt was supplied.",
        }
    receipt = _load(path)
    if receipt.get("schema") != "fa3.blackhole-production-current-host.v1":
        return {"result": "FAIL", "reason": "Unsupported current-host receipt schema"}
    if receipt.get("status") != "PASS":
        return {"result": "FAIL", "reason": "Current-host collector did not report PASS", "receipt": receipt}
    checks = receipt.get("checks", [])
    if not checks or any(c.get("status") != "PASS" for c in checks):
        return {"result": "FAIL", "reason": "One or more current-host checks are not PASS", "receipt": receipt}
    return {"result": "PASS", "receipt": receipt}


def gate(root: Path, current_host_receipt: Path | None = None) -> dict[str, Any]:
    static = static_check(root)
    runtime = evaluate_current_host_receipt(current_host_receipt)
    if static["result"] != "PASS":
        result = "FAIL"
    elif runtime["result"] == "PASS":
        result = "PASS"
    elif runtime["result"] == "PENDING_CURRENT_HOST":
        result = "PENDING_CURRENT_HOST"
    else:
        result = "FAIL"
    report = {
        "schema": "fa3.blackhole-production-gate-report.v1",
        "gate_id": GATE_ID,
        "admission_id": ADMISSION_ID,
        "result": result,
        "static": static,
        "current_host": runtime,
        "document_only_promotion_forbidden": True,
    }
    out = root / "reports/blackhole-production-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Blackhole production admission gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--current-host-receipt")
    parser.add_argument("--static-only", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    static = static_check(root)
    if args.static_only:
        print(json.dumps(static, indent=2))
        return 0 if static["result"] == "PASS" else 2
    receipt = Path(args.current_host_receipt) if args.current_host_receipt else None
    report = gate(root, receipt)
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
