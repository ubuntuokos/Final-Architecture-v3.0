# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def check(root=ROOT):
    profile = load("canonical/profiles/FA3-OFFICE-FABRIC-001.json")
    contract = load("canonical/contracts/FA3-OFFICE-FABRIC-CONTRACTS-001.json")
    reuse = load("canonical/assessments/FA3-OFFICE-FABRIC-REUSE-ASSESSMENT-001.json")
    impact = load("canonical/current-host-impact/FA3-CH-IMPACT-OFFICE-FABRIC-20261001.json")
    failures = []

    rules = [
        (profile["capability_count"] == 175, "baseline-175"),
        (profile["new_capability"] is False, "no-new-capability"),
        (profile["new_architectural_authority"] is False, "no-new-authority"),
        (profile["document_authority"] == "FA3-DOC-001", "document-authority"),
        (profile["engine"]["full_upstream_gui_embedded"] is False, "no-full-upstream-gui"),
        (profile["engine"]["bundled_upstream_binary"] is False, "no-bundled-binary"),
        (profile["format_policy"]["same_type_export_required_for_editable_import"] is True, "format-symmetry"),
        (profile["format_policy"]["silent_format_fallback"] is False, "no-format-fallback"),
        (contract["document_session"]["apply_requires_explicit_human_approval"] is True, "explicit-apply"),
        (contract["document_session"]["undo_required_for_mutation"] is True, "undo"),
        (contract["security"]["macros_disabled_by_default"] is True, "macro-deny"),
        (contract["ai"]["non_ai_authoring_path_required"] is True, "non-ai-path"),
        (reuse["donor_intake_status"]["active_pr"] == 581, "intake-pr"),
        (reuse["donor_intake_status"]["new_donor_records_published"] is False, "no-parallel-intake"),
        (reuse["code_import_authorized"] is False, "no-code-import"),
        (reuse["runtime_admission_authorized"] is False, "runtime-pending"),
        (impact["physical_pass_claimed"] is False, "no-physical-pass-claim"),
        (impact["result"] == "PENDING_PHYSICAL_CURRENT_HOST_REQUALIFICATION", "current-host-pending"),
    ]
    for ok, name in rules:
        if not ok:
            failures.append(name)

    pending = {x["name"]: x["state"] for x in reuse["pending_new_donor_candidates"]}
    if pending != {"Calligra": "PENDING_DONOR_INTAKE", "Collabora Online": "PENDING_DONOR_INTAKE"}:
        failures.append("pending-donor-boundary")
    return failures

def main():
    failures = check()
    if failures:
        print("FA3 OFFICE FABRIC GATE: FAIL")
        for item in failures:
            print(f"- {item}")
        raise SystemExit(1)
    print("FA3 OFFICE FABRIC GATE: PASS (STATIC; RUNTIME/CURRENT-HOST PENDING)")

if __name__ == "__main__":
    main()
