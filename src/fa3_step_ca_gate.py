#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

PROFILE_ID = "FA3-TRUST-PKI-001"
CONTRACT_ID = "FA3-TRUST-PKI-CONTRACTS-001"
PROVIDER_ID = "FA3-PROVIDER-STEP-CA-001"
DECISION_ID = "FA3-DEC-STEP-CA-TRUST-PKI-2026-09-20"
REFERENCE_ID = "FA3-STEP-CA-UPSTREAM-REFERENCE-2026-09-20"
GATE_ID = "FA3-STEP-CA-GATESET-001"
RELEASE = "0.30.2"
COMMIT = "6e8ec61405239cf3f37b2bbf260a587b7d2e4e31"
CAPABILITY_COUNT = module_active_capability_count(__file__)

P0_INVARIANTS = [
    "STEP_CA_PROVIDER_NOT_FA3_SECURITY_POLICY_AUTHORITY",
    "STEP_CA_PROVIDER_NOT_FA3_IDENTITY_OR_AUTHORIZATION_AUTHORITY",
    "OFFLINE_ROOT_PRIVATE_KEY_REQUIRED",
    "ONLINE_ROOT_PRIVATE_KEY_FORBIDDEN",
    "ONLINE_INTERMEDIATE_CA_ONLY",
    "SHORT_LIVED_WORKLOAD_CERTIFICATES_REQUIRED",
    "CERTIFICATE_IDENTITY_IS_NOT_AUTHORIZATION",
    "ACME_V2_INTERNAL_ENROLLMENT_SUPPORTED",
    "SSH_CERTIFICATE_ISSUANCE_POLICY_GATED",
    "PRIVATE_KEY_MATERIAL_FORBIDDEN_IN_CANONICAL_EVIDENCE",
    "PASSWORD_AND_KEY_UNLOCK_MATERIAL_SECRETREF_ONLY",
    "LOOPBACK_DEFAULT_REMOTE_EXPOSURE_EXPLICITLY_GATED",
    "IMMUTABLE_UPSTREAM_RELEASE_AND_COMMIT_PIN_REQUIRED",
    "SIGSTORE_RELEASE_ARTIFACT_VERIFICATION_REQUIRED",
    "APACHE_2_LICENSE_PROVENANCE_REQUIRED",
    "TRUST_BUNDLE_VERSIONING_REQUIRED",
    "ISSUANCE_AUDIT_METADATA_REQUIRED_WITHOUT_SECRET_MATERIAL",
    "SHORT_LIVED_PASSIVE_REVOCATION_DEFAULT_WITH_RENEWAL_DENY",
    "CURRENT_HOST_MTLS_ACME_SSH_E2E_REQUIRED_FOR_RUNTIME_PROMOTION",
    "ROOT_BACKUP_AND_INTERMEDIATE_RECOVERY_EVIDENCE_REQUIRED"
]

PATHS = {
    "profile": "canonical/profiles/FA3-TRUST-PKI-001.json",
    "contract": "canonical/contracts/FA3-TRUST-PKI-CONTRACTS-001.json",
    "provider": "canonical/providers/FA3-PROVIDER-STEP-CA-001.json",
    "decision": "canonical/decisions/FA3-DEC-STEP-CA-TRUST-PKI-2026-09-20.json",
    "reference": "canonical/references/FA3-STEP-CA-UPSTREAM-REFERENCE-2026-09-20.json",
    "enforcement": "canonical/step-ca-enforcement.json",
    "admission": "canonical/step-ca-runtime-admission.json",
    "conformance": "canonical/FA3-STEP-CA-RUNTIME-CONFORMANCE-001.json",
    "gate": "canonical/FA3-GATE-STEP-CA-001.json",
    "release": "canonical/releases/FA3-RELEASE-PROJECTION-STEP-CA-2026-09-20.json",
    "evidence": "evidence/reference/step-ca-reference-pass.json",
    "service": "deployment/step-ca/fa3-step-ca.service",
    "ca_example": "deployment/step-ca/ca.json.example",
    "gui": "apps/fa3-control-center/qml/TrustCertificatesPage.qml",
}

def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def duration_hours(value: str) -> float:
    m = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?", value)
    if not m or (not m.group(1) and not m.group(2)):
        raise ValueError(value)
    return float(m.group(1) or 0) + float(m.group(2) or 0) / 60.0

def deployment_policy_valid(root: Path) -> tuple[bool, list[str]]:
    findings: list[str] = []
    service = (root / PATHS["service"]).read_text(encoding="utf-8")
    ca = loadj(root / PATHS["ca_example"])

    required_service_tokens = [
        "User=fa3-step-ca", "Group=fa3-step-ca", "LoadCredential=step-ca-password:",
        "--password-file=%d/step-ca-password", "NoNewPrivileges=true",
        "ProtectSystem=strict", "CapabilityBoundingSet=", "ReadWritePaths=/var/lib/fa3-step-ca",
    ]
    for token in required_service_tokens:
        if token not in service:
            findings.append(f"service-missing:{token}")

    lower_service = service.lower()
    for token in ["root_ca_key", "root_ca_key.pem", "root_ca.key"]:
        if token in lower_service:
            findings.append(f"online-root-key-reference:{token}")

    if ca.get("address") != "127.0.0.1:9443":
        findings.append("ca-loopback-default")
    if "root_ca.crt" not in str(ca.get("root", "")):
        findings.append("ca-public-root")
    if "intermediate_ca" not in str(ca.get("crt", "")) or "intermediate_ca" not in str(ca.get("key", "")):
        findings.append("ca-intermediate")
    if "root" in Path(str(ca.get("key", ""))).name.lower():
        findings.append("ca-key-must-not-be-root")
    ssh = ca.get("ssh", {})
    if "ssh_host_ca_key" not in str(ssh.get("hostKey", "")):
        findings.append("ssh-host-key")
    if "ssh_user_ca_key" not in str(ssh.get("userKey", "")):
        findings.append("ssh-user-key")

    claims = ca.get("authority", {}).get("claims", {})
    try:
        if duration_hours(str(claims.get("defaultTLSCertDuration"))) > 12:
            findings.append("default-ttl")
        if duration_hours(str(claims.get("maxTLSCertDuration"))) > 24:
            findings.append("max-ttl")
    except Exception:
        findings.append("ttl-parse")

    provs = ca.get("authority", {}).get("provisioners", [])
    if not any(p.get("type") == "ACME" and p.get("name") == "fa3-acme" for p in provs):
        findings.append("acme-provisioner")
    return (not findings, findings)

def provider_policy_valid(provider: dict[str, Any]) -> bool:
    p = provider.get("pki_policy", {})
    return (
        provider.get("id") == PROVIDER_ID
        and provider.get("parent_profile") == PROFILE_ID
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("new_architectural_authority") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
        and provider.get("upstream", {}).get("release") == RELEASE
        and provider.get("upstream", {}).get("release_commit") == COMMIT
        and provider.get("upstream", {}).get("license") == "Apache-2.0"
        and provider.get("upstream", {}).get("release_artifact_sigstore_available") is True
        and p.get("offline_root_private_key_required") is True
        and p.get("online_root_private_key_allowed") is False
        and p.get("online_issuer") == "INTERMEDIATE_ONLY"
        and p.get("default_workload_certificate_ttl") == "12h"
        and p.get("maximum_workload_certificate_ttl") == "24h"
        and p.get("certificate_identity_is_authorization") is False
        and p.get("current_host_e2e_required_for_runtime_promotion") is True
        and provider.get("promotion", {}).get("production_runtime_promoted") is False
    )

def reference_check(root: Path) -> dict[str, Any]:
    root = Path(root)
    missing = [name for name, rel in PATHS.items() if not (root / rel).is_file()]
    if missing:
        return {"result": "FAIL", "findings": [f"missing:{x}" for x in missing]}

    p = {name: loadj(root / rel) for name, rel in PATHS.items() if rel.endswith(".json")}
    findings: list[str] = []
    profile = p["profile"]
    if not (
        profile.get("id") == PROFILE_ID and profile.get("parent_profile") == "FA3-SCS-001"
        and profile.get("priority") == "P0" and profile.get("requirement") == "MUST"
        and profile.get("provider_neutral") is True and profile.get("new_capability") is False
        and profile.get("new_architectural_authority") is False
        and profile.get("capability_count") == CAPABILITY_COUNT
    ):
        findings.append("profile")
    if not provider_policy_valid(p["provider"]):
        findings.append("provider")
    required_contracts = {
        "TrustBundle","IssuancePolicy","CertificateRequest","CertificateIdentity",
        "CertificateIssuanceReceipt","MachineIdentityBinding","CertificateAuditEvent",
        "PKIBackupEvidence","PKIRestoreEvidence",
    }
    contract = p["contract"]
    if not (
        contract.get("id") == CONTRACT_ID and contract.get("provider_neutral") is True
        and contract.get("capability_count") == CAPABILITY_COUNT
        and required_contracts.issubset(set(contract.get("contracts", [])))
        and "CERTIFICATE_VALIDATION_SUCCESS_IS_NOT_AUTHORIZATION_SUCCESS" in contract.get("invariants", [])
    ):
        findings.append("contract")
    decision = p["decision"]
    if not (
        decision.get("id") == DECISION_ID and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("provider_id") == PROVIDER_ID and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append("decision")
    ref = p["reference"]
    if not (
        ref.get("id") == REFERENCE_ID and ref.get("stable_reference", {}).get("release") == RELEASE
        and ref.get("stable_reference", {}).get("commit_sha") == COMMIT
        and ref.get("release_supply_chain", {}).get("sigstore_bundles_available") is True
        and ref.get("license", {}).get("spdx") == "Apache-2.0"
    ):
        findings.append("reference")
    enf = p["enforcement"]
    if not (
        enf.get("gate_id") == GATE_ID and enf.get("fail_closed") is True
        and enf.get("mandatory_rule_count") == len(P0_INVARIANTS)
        and enf.get("p0_invariants") == P0_INVARIANTS
    ):
        findings.append("enforcement")
    admission = p["admission"]
    if not (
        admission.get("status") == "NOT_ADMITTED"
        and admission.get("current_host_evidence_required") is True
        and admission.get("production_runtime_promoted") is False
    ):
        findings.append("admission")
    conf = p["conformance"]
    if not (
        conf.get("status") == "NOT_EXECUTED"
        and conf.get("synthetic_evidence_allowed_for_promotion") is False
        and conf.get("current_host_receipt") is None
        and conf.get("production_runtime_promoted") is False
    ):
        findings.append("conformance")
    gate = p["gate"]
    if not (
        gate.get("id") == "FA3-GATE-STEP-CA-001" and gate.get("gateset_id") == GATE_ID
        and gate.get("fail_closed") is True and gate.get("rule_count") == len(P0_INVARIANTS)
    ):
        findings.append("gate")
    ev = p["evidence"]
    if not (
        ev.get("status") == "PASS" and ev.get("rules_checked") == len(P0_INVARIANTS)
        and ev.get("current_host_runtime_evidence") is False
        and ev.get("production_runtime_promoted") is False
    ):
        findings.append("evidence")
    ok, deploy_findings = deployment_policy_valid(root)
    if not ok:
        findings.extend(deploy_findings)
    gui = (root / PATHS["gui"]).read_text(encoding="utf-8")
    if "RUNTIME NOT PROMOTED" not in gui or "OFFLINE ONLY" not in gui:
        findings.append("gui-honest-state")
    return {"result":"PASS" if not findings else "FAIL","rules_checked":len(P0_INVARIANTS),"findings":findings}

def run_regressions() -> dict[str, Any]:
    base = {
        "id":PROVIDER_ID, "parent_profile":PROFILE_ID, "architectural_authority":False,
        "new_capability":False, "new_architectural_authority":False, "capability_count":CAPABILITY_COUNT,
        "upstream":{"release":RELEASE,"release_commit":COMMIT,"license":"Apache-2.0","release_artifact_sigstore_available":True},
        "pki_policy":{
            "offline_root_private_key_required":True,"online_root_private_key_allowed":False,
            "online_issuer":"INTERMEDIATE_ONLY","default_workload_certificate_ttl":"12h",
            "maximum_workload_certificate_ttl":"24h","certificate_identity_is_authorization":False,
            "current_host_e2e_required_for_runtime_promotion":True
        },
        "promotion":{"production_runtime_promoted":False},
    }
    cases = [{"case":"baseline","result":"PASS" if provider_policy_valid(base) else "FAIL"}]
    for key,bad_value in [
        ("online_root_private_key_allowed",True),
        ("certificate_identity_is_authorization",True),
        ("maximum_workload_certificate_ttl","168h"),
        ("current_host_e2e_required_for_runtime_promotion",False),
    ]:
        mutated = json.loads(json.dumps(base))
        mutated["pki_policy"][key] = bad_value
        cases.append({"case":key,"result":"PASS" if not provider_policy_valid(mutated) else "FAIL"})
    return {"result":"PASS" if all(c["result"]=="PASS" for c in cases) else "FAIL",
            "passed":sum(c["result"]=="PASS" for c in cases),"total":len(cases),"cases":cases}

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    reference, regressions = reference_check(root), run_regressions()
    result = "PASS" if reference["result"] == regressions["result"] == "PASS" else "FAIL"
    print(json.dumps({"schema":"fa3.step-ca-gate-report.v1","gate_id":GATE_ID,
        "provider_id":PROVIDER_ID,"reference":reference,"regressions":regressions,
        "production_runtime_promoted":False,"result":result}, indent=2, sort_keys=True))
    return 0 if result == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
