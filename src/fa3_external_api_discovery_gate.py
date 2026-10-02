#!/usr/bin/env python3
from __future__ import annotations
from fa3_release_baseline import load_active_release_baseline, module_active_capability_count
from fa3_api_mega_list_adapter import (
    OPENCLAW_SOURCE_ID,
    OPENCLAW_SOURCE_REPOSITORY,
    sanitize_locator,
)

import csv
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

PROFILE_ID = "FA3-EXTERNAL-API-DISCOVERY-001"
CONTRACT_ID = "FA3-EXTERNAL-API-DISCOVERY-CONTRACTS-001"
DECISION_ID = "FA3-DEC-EXTERNAL-API-DISCOVERY-2026-08-30"
GATE_ID = "FA3-EXTERNAL-API-DISCOVERY-GATESET-001"
STORE_POLICY_ID = "FA3-EXTERNAL-DISCOVERY-CANDIDATE-STORE-001"
INGESTION_DECISION_ID = "FA3-DEC-API-MEGA-LIST-INGESTION-CORE-2026-10-01"
CAPABILITY_COUNT = module_active_capability_count(__file__)
REGRESSION_CASE_COUNT = 17

SOURCE_IDS = {
    "FA3-SOURCE-PUBLIC-APIS-001",
    "FA3-SOURCE-PUBLIC-API-LISTS-001",
    "FA3-SOURCE-API-MEGA-LIST-001",
    OPENCLAW_SOURCE_ID,
    "FA3-PATTERN-MEGALIST-001",
}

REFERENCES = {
    "FA3-SOURCE-PUBLIC-APIS-001": (
        "canonical/references/FA3-PUBLIC-APIS-UPSTREAM-REFERENCE-2026-08-30.json",
        "public-apis/public-apis",
        "9dfcbcaab75aecf1f7081e98dd968800fb5bd912",
    ),
    "FA3-SOURCE-PUBLIC-API-LISTS-001": (
        "canonical/references/FA3-PUBLIC-API-LISTS-UPSTREAM-REFERENCE-2026-08-30.json",
        "public-api-lists/public-api-lists",
        "1026cf8fb5a6824c308285d7f449ea795f357831",
    ),
    "FA3-SOURCE-API-MEGA-LIST-001": (
        "canonical/references/FA3-API-MEGA-LIST-UPSTREAM-REFERENCE-2026-08-30.json",
        "cporter202/API-mega-list",
        "be78c4e79b5f31f6969ebdb94396942d64c6cf95",
    ),
    OPENCLAW_SOURCE_ID: (
        "canonical/references/FA3-OPENCLAW-API-LIST-UPSTREAM-REFERENCE-2026-10-02.json",
        OPENCLAW_SOURCE_REPOSITORY,
        "3afa19dd12f3cdc6bc2e297e9b6945059ada0cae",
    ),
    "FA3-PATTERN-MEGALIST-001": (
        "canonical/references/FA3-MEGALIST-UPSTREAM-REFERENCE-2026-08-30.json",
        "meganz/megalist",
        "3da8f3694fea7d92b7e1fdfa1357fa1419264de2",
    ),
}

RULES = [
    "EXTERNAL_DISCOVERY_IS_NOT_AUTHORIZATION",
    "UPSTREAM_CATALOG_METADATA_IS_UNTRUSTED_INPUT",
    "IMMUTABLE_SOURCE_SNAPSHOT_REQUIRED",
    "MULTI_SOURCE_NORMALIZATION_AND_DEDUPLICATION_REQUIRED",
    "LICENSE_AND_TERMS_ADMISSION_REQUIRED_BEFORE_RUNTIME_USE",
    "ENDPOINT_PROTOCOL_AND_SCHEMA_VERIFICATION_REQUIRED",
    "SECRET_REQUIREMENTS_DECLARED_BUT_SECRET_VALUES_NOT_INGESTED",
    "CANONICAL_EGRESS_AUTHORIZATION_WITH_SSRF_AND_DNS_REBINDING_CONTROLS_REQUIRED",
    "PROVIDER_NEUTRAL_CAPABILITY_MAPPING_REQUIRED",
    "SANDBOX_PROBE_AND_CONFORMANCE_EVIDENCE_REQUIRED_BEFORE_REGISTRY_ADMISSION",
    "MCP_CATALOG_ENTRY_MUST_NOT_AUTO_REGISTER_OR_AUTO_EXECUTE",
    "SOURCE_FAILURE_OR_DRIFT_MUST_NOT_REPLACE_CANONICAL_STATE",
    "DISCOVERY_SOURCE_CANNOT_BECOME_ARCHITECTURAL_AUTHORITY",
    "DISCOVERY_INGESTION_IS_OFFLINE_FROM_PINNED_SNAPSHOT",
    "AFFILIATE_AND_SPONSORSHIP_METADATA_CANNOT_CHANGE_IDENTITY_RANKING_OR_AUTHORIZATION",
    "DISCOVERY_CANDIDATE_STORE_IS_REBUILDABLE_NON_AUTHORITY",
]

def loadj(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def writej(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def finding(code: str, message: str, **extra):
    return {"code": code, "severity": "P0", "message": message, **extra}

def immutable_commit_valid(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", str(value or "")))

def normalize_endpoint(url: str) -> str:
    p = urlsplit(url.strip())
    scheme = p.scheme.lower()
    host = (p.hostname or "").lower()
    port = p.port
    netloc = host
    if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        netloc = f"{host}:{port}"
    path = p.path.rstrip("/") or "/"
    return urlunsplit((scheme, netloc, path, "", ""))

def dedupe_key(*, provider_name: str, endpoint_url: str, protocol: str) -> str:
    return "|".join((provider_name.strip().casefold(), normalize_endpoint(endpoint_url), protocol.strip().casefold()))

def source_role_valid(*, runtime_provider: bool, canonical_root: bool, architectural_authority: bool, new_capability: bool) -> bool:
    return not any((runtime_provider, canonical_root, architectural_authority, new_capability))

def metadata_boundary_valid(*, catalog_listing_authorizes: bool, catalog_claim_is_canonical_evidence: bool) -> bool:
    return not catalog_listing_authorizes and not catalog_claim_is_canonical_evidence

def secret_boundary_valid(*, auth_requirement_declared: bool, secret_value_present_in_discovery_metadata: bool) -> bool:
    return auth_requirement_declared and not secret_value_present_in_discovery_metadata

def egress_boundary_valid(*, canonical_egress_authorized: bool, ssrf_controls: bool, dns_rebinding_controls: bool) -> bool:
    return canonical_egress_authorized and ssrf_controls and dns_rebinding_controls

def canonical_capability_ids(root: Path) -> frozenset[str]:
    root = Path(root).resolve()
    baseline = load_active_release_baseline(root)
    matrix = root / "canonical/conformance-matrix.csv"
    try:
        with matrix.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, csv.Error) as exc:
        raise ValueError(f"canonical capability matrix unreadable: {exc}") from exc
    ids = [str(row.get("capability_id") or "") for row in rows]
    expected = [f"CAP-{i:03d}" for i in range(1, baseline.capability_count + 1)]
    if ids != expected:
        raise ValueError("canonical capability matrix does not match active release baseline")
    return frozenset(ids)

def capability_mapping_valid(*, capability_id: str, vendor_defined_canonical_capability: bool, root: Path | None = None) -> bool:
    if vendor_defined_canonical_capability:
        return False
    try:
        allowed = canonical_capability_ids(root or Path(__file__).resolve().parents[1])
    except (OSError, ValueError):
        return False
    return capability_id in allowed

def admission_valid(*, discovered: bool, normalized: bool, deduplicated: bool, immutable_source_identity: bool,
                    license_terms_admitted: bool, endpoint_verified: bool, protocol_schema_verified: bool,
                    security_classified: bool, secrets_requirements_declared: bool, egress_authorized: bool,
                    capability_mapped: bool, policy_approved: bool, sandbox_probe_pass: bool,
                    positive_negative_conformance: bool) -> bool:
    return all((
        discovered, normalized, deduplicated, immutable_source_identity, license_terms_admitted,
        endpoint_verified, protocol_schema_verified, security_classified, secrets_requirements_declared,
        egress_authorized, capability_mapped, policy_approved, sandbox_probe_pass, positive_negative_conformance,
    ))

def mcp_registration_allowed(*, admission_pass: bool, central_gateway_mediated: bool, source_self_authorizes: bool) -> bool:
    return admission_pass and central_gateway_mediated and not source_self_authorizes

def source_failure_isolated(*, canonical_registry_unchanged: bool, fail_open_execution: bool, source_state_is_canonical: bool) -> bool:
    return canonical_registry_unchanged and not fail_open_execution and not source_state_is_canonical

def scan_source_authority_assignments(root: Path):
    findings = []
    for path in (root / "canonical").rglob("*.json"):
        try:
            obj = loadj(path)
        except Exception:
            continue

        def walk(node, key_path=""):
            if isinstance(node, dict):
                for key, value in node.items():
                    kp = f"{key_path}.{key}" if key_path else key
                    lk = key.lower()
                    if isinstance(value, str) and value in SOURCE_IDS:
                        if lk == "provider_id" or lk == "authority" or lk.endswith("_authority"):
                            findings.append(finding(
                                "EXTDISC-AUTH-001",
                                "Discovery/pattern source assigned provider or authority role",
                                path=str(path.relative_to(root)),
                                key_path=kp,
                                source_id=value,
                            ))
                    walk(value, kp)
            elif isinstance(node, list):
                for i, value in enumerate(node):
                    walk(value, f"{key_path}[{i}]")
        walk(obj)
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}

def reference_check(root: Path):
    findings = []
    required = {
        "profile": root / "canonical/profiles/FA3-EXTERNAL-API-DISCOVERY-001.json",
        "contracts": root / "canonical/contracts/FA3-EXTERNAL-API-DISCOVERY-CONTRACTS-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-EXTERNAL-API-DISCOVERY-2026-08-30.json",
        "enforcement": root / "canonical/external-api-discovery-enforcement.json",
        "policy": root / "canonical/enforcement-policy.json",
        "candidate_store_policy": root / "canonical/FA3-EXTERNAL-DISCOVERY-CANDIDATE-STORE-001.json",
        "ingestion_decision": root / "canonical/decisions/FA3-DEC-API-MEGA-LIST-INGESTION-CORE-2026-10-01.json",
        "ingestion_adapter": root / "src/fa3_api_mega_list_adapter.py",
        "candidate_store": root / "src/fa3_external_discovery_store.py",
        "ingestion_pipeline": root / "src/fa3_external_api_discovery_pipeline.py",
        "ingestion_cli": root / "bin/fa3-external-api-discovery",
    }
    for sid, (rel, _, _) in REFERENCES.items():
        required[sid] = root / rel
    for name, path in required.items():
        if not path.exists():
            findings.append(finding("EXTDISC-REF-001", "Required canonical discovery artifact missing", item=name, path=str(path.relative_to(root))))
    if findings:
        return {"result":"FAIL","findings":findings}

    profile = loadj(required["profile"])
    contracts = loadj(required["contracts"])
    decision = loadj(required["decision"])
    enforcement = loadj(required["enforcement"])
    policy = loadj(required["policy"])
    candidate_store_policy = loadj(required["candidate_store_policy"])
    ingestion_decision = loadj(required["ingestion_decision"])

    if not (
        profile.get("id") == PROFILE_ID
        and profile.get("status") == "CANONICAL"
        and profile.get("priority") == "P1"
        and profile.get("requirement") == "MUST-IF-EXTERNAL-DISCOVERY-USED"
        and profile.get("new_capability") is False
        and profile.get("new_architectural_authority") is False
        and profile.get("capability_count") == CAPABILITY_COUNT
        and set(profile.get("capabilities", [])) == {"CAP-011","CAP-074","CAP-075"}
        and set(profile.get("discovery_sources", [])) == {
            "FA3-SOURCE-PUBLIC-APIS-001",
            "FA3-SOURCE-PUBLIC-API-LISTS-001",
            "FA3-SOURCE-API-MEGA-LIST-001",
            OPENCLAW_SOURCE_ID,
        }
        and profile.get("candidate_store_policy_id") == STORE_POLICY_ID
        and profile.get("invariants") == RULES
    ):
        findings.append(finding("EXTDISC-REF-002", "External discovery profile invariant mismatch"))

    if not (
        contracts.get("id") == CONTRACT_ID
        and contracts.get("profile_id") == PROFILE_ID
        and contracts.get("capability_count") == CAPABILITY_COUNT
        and {
            "ExternalDiscoverySnapshot",
            "ExternalCapabilityCandidate",
            "ExternalProviderAdmissionDecision",
            "ExternalDiscoveryCandidateStoreManifest",
            "ExternalDiscoveryIngestReceipt",
        }.issubset(set(contracts.get("contracts", [])))
    ):
        findings.append(finding("EXTDISC-REF-003", "External discovery contract-family invariant mismatch"))

    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("profile_id") == PROFILE_ID
        and decision.get("gate_id") == GATE_ID
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append(finding("EXTDISC-REF-004", "External discovery decision invariant mismatch"))

    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("runtime_provider_required_for_global_promotion") is False
        and enforcement.get("mandatory_rule_count") == len(RULES)
        and enforcement.get("p0_invariants") == RULES
        and enforcement.get("regression_case_count") == REGRESSION_CASE_COUNT
    ):
        findings.append(finding("EXTDISC-REF-005", "External discovery enforcement invariant mismatch"))

    if not (
        candidate_store_policy.get("id") == STORE_POLICY_ID
        and candidate_store_policy.get("profile_id") == PROFILE_ID
        and candidate_store_policy.get("authority") is False
        and candidate_store_policy.get("canonical_source_of_truth") is False
        and candidate_store_policy.get("derived_state") is True
        and candidate_store_policy.get("rebuildable") is True
        and candidate_store_policy.get("runtime_provider") is False
        and candidate_store_policy.get("automatic_donor_creation") is False
        and candidate_store_policy.get("automatic_provider_admission") is False
        and candidate_store_policy.get("automatic_mcp_registration") is False
        and candidate_store_policy.get("automatic_activation") is False
        and candidate_store_policy.get("network_fetch_permitted") is False
        and set(candidate_store_policy.get("source_ids", [])) == {
            "FA3-SOURCE-API-MEGA-LIST-001",
            OPENCLAW_SOURCE_ID,
        }
        and candidate_store_policy.get("capacity_policy", {}).get("growth_headroom_fraction") == 0.30
        and candidate_store_policy.get("capacity_policy", {}).get("open_next_volume_at_utilization") == 0.90
        and candidate_store_policy.get("capacity_policy", {}).get("rebalance_at_utilization") == 0.95
        and candidate_store_policy.get("capacity_policy", {}).get("rebalance_target_utilization") == 0.70
        and candidate_store_policy.get("capability_count") == CAPABILITY_COUNT
    ):
        findings.append(finding("EXTDISC-REF-013", "External discovery candidate-store policy invariant mismatch"))

    if not (
        ingestion_decision.get("id") == INGESTION_DECISION_ID
        and ingestion_decision.get("status") == "CANONICAL_CLOSED"
        and ingestion_decision.get("profile_id") == PROFILE_ID
        and ingestion_decision.get("source_id") == "FA3-SOURCE-API-MEGA-LIST-001"
        and ingestion_decision.get("candidate_store_policy_id") == STORE_POLICY_ID
        and ingestion_decision.get("rules", {}).get("network_fetch_by_ingestion_core") is False
        and ingestion_decision.get("rules", {}).get("candidate_store_is_non_authoritative") is True
        and ingestion_decision.get("rules", {}).get("automatic_donor_creation") is False
        and ingestion_decision.get("rules", {}).get("automatic_provider_admission") is False
        and ingestion_decision.get("rules", {}).get("automatic_mcp_registration") is False
        and ingestion_decision.get("current_host_obligation_delta") == 0
        and ingestion_decision.get("new_capabilities") == 0
        and ingestion_decision.get("new_architectural_authorities") == 0
        and ingestion_decision.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append(finding("EXTDISC-REF-014", "API Mega List ingestion decision invariant mismatch"))

    if GATE_ID not in policy.get("mandatory_reference_gates", []):
        findings.append(finding("EXTDISC-REF-006", "External discovery gate not bound into global policy"))
    if policy.get("external_api_discovery_profile_id") != PROFILE_ID:
        findings.append(finding("EXTDISC-REF-007", "External discovery profile policy binding drift"))
    if set(policy.get("external_api_discovery_source_ids", [])) != {
        "FA3-SOURCE-PUBLIC-APIS-001",
        "FA3-SOURCE-PUBLIC-API-LISTS-001",
        "FA3-SOURCE-API-MEGA-LIST-001",
        OPENCLAW_SOURCE_ID,
    }:
        findings.append(finding("EXTDISC-REF-008", "External discovery source policy binding drift"))

    for sid, (rel, repo_name, sha) in REFERENCES.items():
        ref = loadj(root / rel)
        if not (
            ref.get("source_id") == sid
            and ref.get("repository") == repo_name
            and ref.get("immutable_reference_commit") == sha
            and ref.get("observed_default_branch_head") == sha
            and immutable_commit_valid(sha)
        ):
            findings.append(finding("EXTDISC-REF-009", "Pinned upstream reference identity drift", source_id=sid))
        disp = ref.get("fa3_disposition", {})
        if disp.get("runtime_provider") is not False or disp.get("canonical_root") is not False or disp.get("architectural_authority") is not False:
            findings.append(finding("EXTDISC-REF-010", "Upstream source authority/provider escalation", source_id=sid))

    mega = loadj(root / REFERENCES["FA3-SOURCE-API-MEGA-LIST-001"][0])
    if mega.get("license_status") != "NO_REPOSITORY_LICENSE_DETECTED" or mega.get("local_ingestion_policy") != "DISCOVERY_METADATA_ONLY_UNTIL_LICENSE_AND_TERMS_ADMITTED":
        findings.append(finding("EXTDISC-REF-011", "API Mega List licence/terms restriction weakened"))

    openclaw = loadj(root / REFERENCES[OPENCLAW_SOURCE_ID][0])
    if not (
        openclaw.get("license_status") == "NO_REPOSITORY_LICENSE_DETECTED"
        and openclaw.get("local_ingestion_policy") == "DISCOVERY_METADATA_ONLY_UNTIL_LICENSE_AND_TERMS_ADMITTED"
        and openclaw.get("source_signals", {}).get("affiliate_parameter_observed") is True
        and openclaw.get("source_signals", {}).get("upstream_direct_mcp_language_is_admission") is False
        and openclaw.get("fa3_disposition", {}).get("catalog_listing_is_authorization") is False
        and openclaw.get("fa3_disposition", {}).get("affiliate_parameter_is_identity") is False
    ):
        findings.append(finding("EXTDISC-REF-015", "OpenClaw discovery source restriction or identity boundary weakened"))

    ui = loadj(root / REFERENCES["FA3-PATTERN-MEGALIST-001"][0])
    if ui.get("fa3_disposition", {}).get("implementation_dependency") is not False or "EXTERNAL_API_DISCOVERY_SOURCE" not in ui.get("not_classified_as", []):
        findings.append(finding("EXTDISC-REF-012", "MegaList UI pattern source incorrectly promoted to discovery/runtime dependency"))

    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def run_regressions(root: Path):
    cases = []
    def add(name, ok):
        cases.append({"name":name,"status":"PASS" if ok else "FAIL"})

    full = dict(
        discovered=True, normalized=True, deduplicated=True, immutable_source_identity=True,
        license_terms_admitted=True, endpoint_verified=True, protocol_schema_verified=True,
        security_classified=True, secrets_requirements_declared=True, egress_authorized=True,
        capability_mapped=True, policy_approved=True, sandbox_probe_pass=True,
        positive_negative_conformance=True,
    )
    add("catalog listing is not authorization", metadata_boundary_valid(catalog_listing_authorizes=False, catalog_claim_is_canonical_evidence=False))
    add("incomplete admission denied", not admission_valid(**{**full, "license_terms_admitted":False}))
    add("complete controlled admission allowed", admission_valid(**full))
    add("MCP listing cannot auto-register", not mcp_registration_allowed(admission_pass=False, central_gateway_mediated=True, source_self_authorizes=False))
    add("admitted MCP remains gateway-mediated", mcp_registration_allowed(admission_pass=True, central_gateway_mediated=True, source_self_authorizes=False))
    add("egress requires SSRF and DNS rebinding controls", not egress_boundary_valid(canonical_egress_authorized=True, ssrf_controls=False, dns_rebinding_controls=True))
    add("secret values forbidden in discovery metadata", not secret_boundary_valid(auth_requirement_declared=True, secret_value_present_in_discovery_metadata=True))
    add("multi-source endpoint dedupe normalization", dedupe_key(provider_name=" Example ", endpoint_url="HTTPS://API.EXAMPLE.COM:443/v1/", protocol="REST") == dedupe_key(provider_name="example", endpoint_url="https://api.example.com/v1", protocol="rest"))
    add("provider-neutral existing capability mapping", capability_mapping_valid(capability_id="CAP-011", vendor_defined_canonical_capability=False, root=root))
    add("active baseline final capability mapping", capability_mapping_valid(capability_id=f"CAP-{CAPABILITY_COUNT:03d}", vendor_defined_canonical_capability=False, root=root))
    add("capability beyond active baseline denied", not capability_mapping_valid(capability_id=f"CAP-{CAPABILITY_COUNT + 1:03d}", vendor_defined_canonical_capability=False, root=root))
    add("vendor-defined canonical capability denied", not capability_mapping_valid(capability_id="CAP-999", vendor_defined_canonical_capability=True, root=root))
    add("sandbox probe required before admission", not admission_valid(**{**full, "sandbox_probe_pass":False}))
    add("source outage cannot fail open", source_failure_isolated(canonical_registry_unchanged=True, fail_open_execution=False, source_state_is_canonical=False))
    add("source cannot become provider or authority", source_role_valid(runtime_provider=False, canonical_root=False, architectural_authority=False, new_capability=False))
    tracked = sanitize_locator("https://apify.com/example/tool?fpr=partner&utm_source=test")
    clean = sanitize_locator("https://apify.com/example/tool")
    add(
        "affiliate and tracking metadata are identity-neutral",
        tracked["canonical_locator"] == clean["canonical_locator"]
        and tracked["affiliate_or_tracking_present"] is True,
    )
    secret = sanitize_locator("https://api.example.com/v1?api_key=DO_NOT_PERSIST&mode=fast")
    add(
        "secret query values are stripped before persistence",
        secret["canonical_locator"] == "https://api.example.com/v1?mode=fast"
        and secret["secret_parameter_present"] is True
        and "DO_NOT_PERSIST" not in json.dumps(secret),
    )

    passed = sum(x["status"] == "PASS" for x in cases)
    return {"result":"PASS" if passed == len(cases) else "FAIL","passed":passed,"total":len(cases),"cases":cases}

def gate(root: Path):
    root = Path(root).resolve()
    ref = reference_check(root)
    auth = scan_source_authority_assignments(root)
    regressions = run_regressions(root)
    findings = list(ref.get("findings", [])) + list(auth.get("findings", []))
    if regressions["result"] != "PASS":
        findings.append(finding("EXTDISC-REG-001", "Executable external discovery regression matrix failed", regressions=regressions))
    report = {
        "schema":"fa3.external-api-discovery-gate-report.v1",
        "gate_id":GATE_ID,
        "profile_id":PROFILE_ID,
        "capability_count":CAPABILITY_COUNT,
        "result":"PASS" if not findings else "FAIL",
        "findings":findings,
        "reference":ref,
        "authority_scan":auth,
        "regressions":regressions,
        "runtime_provider_required":False,
        "global_runtime_promotion_claimed":False,
    }
    writej(root / "reports/external-api-discovery-gate-report.json", report)
    return report
