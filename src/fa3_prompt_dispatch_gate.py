#!/usr/bin/env python3
"""Fail-closed donor/authority gate for FA3 Prompt Builder & Dispatch."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from fa3_prompt_dispatch import load_admitted_applications

MANIFEST = "canonical/assessments/FA3-PROMPT-DISPATCH-DONOR-CHECK-001.json"
REGISTRY = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"


def gate(root: Path) -> dict:
    declaration = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    registry = json.loads((root / REGISTRY).read_text(encoding="utf-8"))
    assert declaration["schema"] == "fa3.donor-reuse-assessment.v1"
    assert registry["id"] == "FA3-DONOR-REFERENCE-REGISTRY-001"
    assert declaration["registry"] == REGISTRY
    assert declaration["authority"] is False
    assert declaration["code_copied_from_external_donors"] is False
    entries = {entry["donor_id"]: entry for entry in registry["entries"]}
    assert len(entries) == len(registry["entries"])
    assert len(declaration["sources"]) >= 8
    for source in declaration["sources"]:
        row = entries[source["donor_id"]]
        assert row["status"] in ("CANDIDATE", "ANALYZED", "ACCEPTED_REFERENCE")
        assert source["mode"] == "REFERENCE_ONLY"
        assert row["authority"] is False
        assert row["automatic_code_import"] is False
        assert row["automatic_provider_admission"] is False
        assert row["automatic_model_selection"] is False
        assert row["source"]["normalized_key"]
        assert source["use"].strip()
    assert len({x["donor_id"] for x in declaration["sources"]}) == len(declaration["sources"])
    refs = {row["pr"]: row for row in declaration["fa3_integrations"]}
    assert refs[364]["mode"] == "USE_EXISTING_UAF_DECISION_FABRIC_MODEL_ROUTER_HRB"
    assert refs[405]["mode"].startswith("OPTIONAL_FAIL_CLOSED")
    assert refs[425]["mode"].startswith("OPTIONAL_FAIL_CLOSED")
    inv = declaration["invariants"]
    assert inv["new_authorities"] == 0 and inv["auto_admit_donors"] is False
    assert inv["source_copy_requires_separate_review"] is True
    assert inv["vendor_neutral"] is True and inv["cpu_only_planning"] is True
    assert inv["accelerators"] == "0..N"
    assert inv["model_router_exclusive"] and inv["hrb_exclusive"]
    assert inv["mcp_gateway_exclusive"] and inv["temporal_exclusive_durable"]
    assert inv["current_host_promotion_claim"] is False
    apps = load_admitted_applications(root)
    assert {"fa3.video-editor", "fa3.quickclip", "fa3.story-screenplay",
            "reference.krita", "reference.ardour"}.issubset(apps)
    assert "rogue-app" not in apps
    return {
        "result": "PASS", "gate": "FA3-PROMPT-DISPATCH-DONOR-CHECK-001",
        "donors_checked": len(declaration["sources"]), "eligible_applications": len(apps),
        "new_authorities": 0, "current_host_promotion": False,
        "checks": ["registry_provenance", "license_boundaries", "integration_refs",
                   "hardware_audit", "full_admitted_app_inventory"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(gate(args.root), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
