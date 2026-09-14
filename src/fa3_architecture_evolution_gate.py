#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import load_active_release_baseline

GATESET_ID = "FA3-ARCHITECTURE-EVOLUTION-GATESET-001"
POLICIES = {
    "federated": "canonical/FA3-FEDERATED-CAPABILITY-LIFECYCLE-001.json",
    "satellites": "canonical/FA3-SATELLITE-REGISTRY-001.json",
    "host": "canonical/FA3-HOST-ATTESTATION-001.json",
    "compute": "canonical/FA3-COMPUTE-PROFILE-001.json",
    "envelope": "canonical/FA3-WORKLOAD-RESOURCE-ENVELOPE-001.json",
    "qualification": "canonical/FA3-DEPENDENCY-QUALIFICATION-001.json",
    "promotion": "canonical/FA3-DEPENDENCY-PROMOTION-POLICY-001.json",
    "oci": "canonical/FA3-OCI-EXECUTION-POLICY-001.json",
    "p3d_oci": "canonical/FA3-PYTORCH3D-OCI-EXECUTION-001.json",
    "ffmpeg": "canonical/FA3-FFMPEG-ZEROCOPY-001.json",
    "gate": "canonical/FA3-GATE-ARCHITECTURE-EVOLUTION-001.json",
    "decision": "canonical/decisions/FA3-DEC-ARCHITECTURE-EVOLUTION-2026-09-14.json",
}


def loadj(root: Path, rel: str) -> dict[str, Any]:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    missing = [p for p in list(POLICIES.values()) + [
        "deployment/containers/pytorch3d.Containerfile",
        "deployment/quadlet/fa3-pytorch3d.container.in",
        "deployment/quadlet/fa3-pytorch3d-cache.volume",
        "tools/dependency-gate/simulator.py",
        "tools/render_pytorch3d_quadlet.py",
    ] if not (root / p).is_file()]
    if missing:
        return {"schema":"fa3.architecture-evolution-gate-report.v1","gate_set_id":GATESET_ID,"result":"FAIL","findings":[{"code":"AE-000","path":p} for p in missing]}
    baseline = load_active_release_baseline(root)
    docs = {k: loadj(root, v) for k, v in POLICIES.items()}
    findings: list[dict[str, str]] = []
    def require(code: str, ok: bool, detail: str) -> None:
        if not ok:
            findings.append({"code": code, "severity": "P0", "detail": detail})
    base_path = "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json"
    require("AE-001", all(d.get("capability_count_source") == base_path for d in docs.values()), "all new canonical records must consume release-scoped count source")
    require("AE-002", baseline.document.get("baseline_semantics") == "RELEASE_SCOPED", "active capability baseline must be release-scoped")
    require("AE-003", docs["federated"].get("release_composition", {}).get("fixed_core_capability_count_forbidden") is True and docs["federated"].get("satellite_contract", {}).get("own_trust_root_forbidden") is True, "federated lifecycle must keep central trust root without a magic core count")
    require("AE-004", all(x.get("trust_root") == "CENTRAL" for x in docs["satellites"].get("satellites", [])), "satellites may not own trust roots")
    require("AE-005", docs["compute"].get("aggregate_scores", {}).get("cu_tu_allowed_for_production_admission") is False and docs["compute"].get("profile_semantics", {}).get("multidimensional") is True, "compute admission must be multidimensional")
    require("AE-006", docs["envelope"].get("evaluation", {}).get("cross_metric_compensation") is False and docs["envelope"].get("evaluation", {}).get("missing_metric") == "FAIL", "workload envelope must fail closed without compensation")
    staging = docs["qualification"].get("staging_authority", {})
    require("AE-007", all(staging.get(k) is False for k in ("production_authority","may_claim_current_host","may_promote","production_ssot_write")), "staging must have zero current-host/production authority")
    require("AE-008", docs["qualification"].get("principle") == "RANGE_SELECTS_DIGEST_PROVES", "SemVer range may select but not prove identity")
    require("AE-009", docs["promotion"].get("risk_tiers", {}).get("CRITICAL", {}).get("human_approvals_min", 0) >= 2 and "CURRENT_HOST_QUALIFIED" in docs["promotion"].get("preconditions", []), "critical promotion must require approvals and current-host qualification")
    runtime = docs["oci"].get("runtime", {})
    require("AE-010", runtime.get("rootless_required") is True and runtime.get("image_digest_required") is True and runtime.get("read_only_rootfs_required") is True and runtime.get("network_default") == "NONE" and runtime.get("hrb_accelerator_lease_required") is True, "OCI runtime hardening incomplete")
    p3d_builder = docs["p3d_oci"].get("builder", {})
    require("AE-011", docs["p3d_oci"].get("production_status") == "PENDING_CURRENT_HOST" and docs["p3d_oci"].get("production_promotion_claimed") is False and p3d_builder.get("source_archive_sha256_required") is True and p3d_builder.get("source_revision_digest_binding_required") is True and p3d_builder.get("source_commit_self_assertion_forbidden") is True, "PyTorch3D OCI source identity or production boundary weakened")
    require("AE-012", docs["ffmpeg"].get("upstream_candidate", {}).get("commit") == "09bf8dab5b8f5c9d1c9280af4dec7f84e8c0fe8b" and docs["ffmpeg"].get("scope_boundary", {}).get("end_to_end_gpu_resident_pipeline_claimed") is False and docs["ffmpeg"].get("integration", {}).get("permanent_fork_forbidden") is True, "FFmpeg zero-copy scope/retirement policy drift")
    p3d_gate = (root / "src/fa3_pytorch3d_gate.py").read_text(encoding="utf-8")
    require("AE-013", "module_active_capability_count" in p3d_gate and "== 143" not in p3d_gate, "PyTorch3D executable gate still hardcodes release capability count")
    quadlet = (root / "deployment/quadlet/fa3-pytorch3d.container.in").read_text(encoding="utf-8")
    require("AE-014", all(token in quadlet for token in ("Image=@IMAGE_REF@","Network=none","ReadOnly=true","NoNewPrivileges=true","DropCapability=all")) and "CUDA_VISIBLE_DEVICES=" not in quadlet, "PyTorch3D Quadlet template is not hardened or contains static accelerator assignment")
    containerfile = (root / "deployment/containers/pytorch3d.Containerfile").read_text(encoding="utf-8")
    require("AE-015", all(token in containerfile for token in ("ARG BUILDER_BASE","ARG RUNTIME_BASE","COPY pytorch3d-source.tar","sha256sum -c -","--no-index","0a7d4c1a171e8b768c63f15b17564f9ad495f49b")) and "git rev-parse HEAD 2>/dev/null ||" not in containerfile and "conda" not in containerfile.lower(), "PyTorch3D container source/digest/build policy drift")
    decision = docs["decision"]
    require("AE-016", decision.get("capability_delta") == 0 and decision.get("authority_delta") == 0 and decision.get("runtime_effect", {}).get("new_current_host_pass_claimed") is False, "architecture decision gained capability/authority or fabricated current-host evidence")
    report = {"schema":"fa3.architecture-evolution-gate-report.v1","gate_set_id":GATESET_ID,"result":"PASS" if not findings else "FAIL","active_release":baseline.release,"active_release_capability_count":baseline.capability_count,"checks_total":16,"blocking_findings":len(findings),"findings":findings,"current_host_runtime_promoted":False}
    out = root / "reports/architecture-evolution-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    a = p.parse_args()
    result = gate(Path(a.root))
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
