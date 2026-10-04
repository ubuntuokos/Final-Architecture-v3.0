#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count
from fa3_scale_backend import evaluate_scale_execution_rights, parse_scaleinfo
from fa3_cuda_compat_shared import SHARED_APPLICATION_SCOPE

CAPABILITY_COUNT = module_active_capability_count(__file__)


def loadj(root: Path, rel: str) -> dict[str, Any]:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[str] = []
    required = {
        "provider": "canonical/providers/FA3-PROVIDER-SCALE-CUDA-COMPAT-001.json",
        "contract": "canonical/contracts/FA3-SCALE-CUDA-COMPAT-CONTRACTS-001.json",
        "intent": "canonical/intents/FA3-SCALE-CUDA-COMPAT-APPLICATION-INTENT-2026-10-04.json",
        "reuse": "canonical/assessments/FA3-SCALE-CUDA-COMPAT-REUSE-ASSESSMENT-2026-10-04.json",
        "impact": "canonical/current-host-impact/FA3-CH-IMPACT-SCALE-CUDA-COMPAT-20261004.json",
        "cuda_policy": "canonical/FA3-CUDA-PORTABILITY-SHARED-FUNCTION-POLICY-001.json",
        "rights_policy": "canonical/license-rights-policy.json",
    }
    shared_entrypoint = root / "src/fa3_cuda_compat_shared.py"
    if not shared_entrypoint.is_file():
        findings.append("missing-shared-entrypoint:src/fa3_cuda_compat_shared.py")

    data: dict[str, dict[str, Any]] = {}
    for key, rel in required.items():
        try:
            data[key] = loadj(root, rel)
        except Exception as exc:
            findings.append(f"missing-or-invalid:{rel}:{type(exc).__name__}")

    if not findings:
        provider = data["provider"]
        contract = data["contract"]
        impact = data["impact"]
        reuse = data["reuse"]
        cuda_policy = data["cuda_policy"]
        rights_policy = data["rights_policy"]

        if provider.get("id") != "FA3-PROVIDER-SCALE-CUDA-COMPAT-001":
            findings.append("provider-id")
        if provider.get("capability_count") != CAPABILITY_COUNT:
            findings.append("provider-capability-count")
        if provider.get("new_capability") is not False or provider.get("new_architectural_authority") is not False:
            findings.append("provider-baseline-delta")
        if provider.get("shared_only") is not True or provider.get("application_local_functional_core") != "FORBIDDEN":
            findings.append("shared-only-placement")
        shared_access = provider.get("shared_application_access", {})
        if shared_access.get("scope") != SHARED_APPLICATION_SCOPE or shared_access.get("application_allowlist_required") is not False:
            findings.append("shared-all-application-scope")
        if shared_access.get("central_entrypoint") != "src/fa3_cuda_compat_shared.py:resolve_cuda_compatibility":
            findings.append("shared-central-entrypoint")
        if shared_access.get("application_local_backend_implementation") != "FORBIDDEN":
            findings.append("application-local-backend-not-forbidden")

        backend = provider.get("backend", {})
        if backend.get("name") != "scale-cuda" or backend.get("class") != "translation":
            findings.append("backend-identity")
        if backend.get("target_vendor_materialized") != ["AMD"]:
            findings.append("amd-target-scope")
        if backend.get("intel_support") != "UNAVAILABLE_NOT_CLAIMED":
            findings.append("intel-support-overclaim")
        if backend.get("translation_must_be_explicitly_allowed") is not True:
            findings.append("translation-not-explicit")

        detection = provider.get("detection", {})
        if detection.get("read_only") is not True or detection.get("auto_install") is not False:
            findings.append("discovery-mutation")
        if detection.get("auto_activate_scaleenv") is not False or detection.get("path_mutation") is not False:
            findings.append("environment-mutation")

        rights = provider.get("rights", {})
        if rights.get("authority") != "FA3-AUTH-SECURITY-GOV-001":
            findings.append("rights-authority")
        if rights.get("commercial_context_default") is not True:
            findings.append("commercial-default")
        if rights.get("free_license_observed_2026_10_04") != "NON_COMMERCIAL_ONLY":
            findings.append("free-license-classification")
        if rights_policy.get("fail_closed", {}).get("unknown_commercial_use_right") is not True:
            findings.append("global-rights-fail-closed")

        if contract.get("provider_id") != provider.get("id"):
            findings.append("contract-provider-binding")
        access_contract = contract.get("application_access_contract", {})
        if access_contract.get("consumer_scope") != SHARED_APPLICATION_SCOPE or access_contract.get("per_application_allowlist") is not False:
            findings.append("contract-all-application-scope")
        if access_contract.get("central_entrypoint") != "src/fa3_cuda_compat_shared.py:resolve_cuda_compatibility":
            findings.append("contract-central-entrypoint")
        if access_contract.get("application_may_authorize_execution") is not False or access_contract.get("hrb_lease_required_before_execution") is not True:
            findings.append("contract-hrb-authority")
        if contract.get("backend_contract", {}).get("silent_substitution") is not False:
            findings.append("contract-silent-substitution")
        if contract.get("promotion", {}).get("physical_current_host_pass_claimed") is not False:
            findings.append("false-current-host-pass")

        if impact.get("runtime_change") is not True:
            findings.append("current-host-runtime-impact")
        if impact.get("physical_requalification_required") is not True:
            findings.append("current-host-requalification")
        if impact.get("physical_current_host_pass_claimed") is not False:
            findings.append("current-host-pass-claim")

        if reuse.get("pending_or_unmerged_donors_consumed") is not False:
            findings.append("pending-donor-consumed")
        if reuse.get("donor_usage_edges_created") != 0:
            findings.append("unexpected-donor-usage-edge")
        if cuda_policy.get("shared_placement_policy", {}).get("strongly_cuda_oriented_function_core") != "SHARED_LAYER_ONLY":
            findings.append("cuda-shared-policy")

    no_rights = evaluate_scale_execution_rights(None)
    if no_rights.get("admitted") is not False:
        findings.append("rights-negative-regression")

    admitted = evaluate_scale_execution_rights({
        "schema": "fa3.scale-execution-rights-receipt.v1",
        "authority": "FA3-AUTH-SECURITY-GOV-001",
        "subject_id": "FA3-EXTERNAL-SCALE-TOOLKIT",
        "result": "PASS",
        "execution_allowed": True,
        "commercial_use_allowed": True,
        "entitlement_reference": "secret-broker://license/scale/test",
        "raw_secret_material_present": False,
    })
    if admitted.get("admitted") is not True:
        findings.append("rights-positive-regression")

    parsed = parse_scaleinfo(
        "Device 0 (00:23:00.0): AMD Radeon Pro W6800 - gfx1030 (AMD) "
        "<amdgcn-amd-amdhsa--gfx1030>"
    )
    if parsed.get("0000:23:00.0", {}).get("target") != "gfx1030":
        findings.append("scaleinfo-parser-regression")

    report = {
        "schema": "fa3.scale-backend-gate-report.v1",
        "gate_id": "FA3-GATE-SCALE-CUDA-COMPAT-001",
        "provider_id": "FA3-PROVIDER-SCALE-CUDA-COMPAT-001",
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "capability_count": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "runtime_promotion_claim": False,
        "physical_current_host_pass_claimed": False,
        "physical_requalification_required": True,
    }
    out = root / "reports/scale-cuda-compat-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
