from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fa3_permanent_gate_hardening import (
    canonical_json_bytes,
    explicit_gate_pass,
    scan_workflow_action_pins,
    verify_binding,
    authority_input_snapshot,
    verify_non_interference,
)

ROOT = Path(__file__).resolve().parents[1]


def test_no_implicit_pass_is_exact_string_only():
    assert explicit_gate_pass("PASS")
    for value in [
        None,
        False,
        True,
        0,
        1,
        "",
        "pass",
        "Pass",
        "PENDING",
        "ERROR",
        {},
        [],
    ]:
        assert not explicit_gate_pass(value)


def test_canonical_json_is_order_stable_and_rejects_nan():
    assert canonical_json_bytes({"b": 2, "a": 1}) == canonical_json_bytes(
        {"a": 1, "b": 2}
    )
    try:
        canonical_json_bytes({"x": float("nan")})
    except ValueError:
        pass
    else:
        raise AssertionError("NaN must be rejected")


def test_action_pin_guard_rejects_mutable_tags(tmp_path: Path):
    workflow = tmp_path / ".github/workflows/test.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "steps:\n  - uses: actions/checkout@v4\n",
        encoding="utf-8",
    )
    findings = scan_workflow_action_pins(
        tmp_path, [".github/workflows/test.yml"]
    )
    assert any(row["code"] == "PGH-021" for row in findings)

    workflow.write_text(
        "steps:\n"
        "  - uses: actions/checkout@"
        "3d3c42e5aac5ba805825da76410c181273ba90b1\n",
        encoding="utf-8",
    )
    assert (
        scan_workflow_action_pins(
            tmp_path, [".github/workflows/test.yml"]
        )
        == []
    )


def test_binding_verifier_fails_after_subject_mutation(tmp_path: Path):
    subject = tmp_path / "subject.json"
    subject.write_text('{"a":1}\n', encoding="utf-8")
    digest = hashlib.sha256(subject.read_bytes()).hexdigest()

    binding = {
        "schema": "fa3.permanent-gate-provenance-binding.v1",
        "role": "BINDING_CARRIER",
        "creates_authority": False,
        "run_identity": {"candidate_head_sha": "a" * 40},
        "subjects": [
            {
                "path": "subject.json",
                "role": "TEST",
                "size_bytes": subject.stat().st_size,
                "sha256": digest,
            }
        ],
    }
    binding["binding_hash"] = hashlib.sha256(
        canonical_json_bytes(binding)
    ).hexdigest()
    binding_path = tmp_path / "binding.json"
    binding_path.write_text(json.dumps(binding), encoding="utf-8")

    assert verify_binding(tmp_path, binding_path)["result"] == "PASS"

    subject.write_text('{"a":2}\n', encoding="utf-8")
    assert verify_binding(tmp_path, binding_path)["result"] == "FAIL"


def test_auxiliary_non_interference_snapshot_is_stable(tmp_path: Path):
    before = authority_input_snapshot(ROOT)
    snapshot = tmp_path / "authority-inputs.json"
    snapshot.write_text(
        json.dumps(before, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result = verify_non_interference(ROOT, snapshot)
    assert result["result"] == "PASS"
    assert result["authority_inputs_unchanged"] is True
    assert result["changed_paths"] == []


def test_trusted_workflow_never_executes_candidate_code():
    workflow = (
        ROOT / ".github/workflows/fa3-permanent-control-plane.yml"
    ).read_text(encoding="utf-8")
    assert "pull_request_target:" in workflow
    assert "trusted/src/fa3_trusted_control_plane_gate.py" in workflow
    forbidden = [
        "python candidate/",
        "bash candidate/",
        "sh candidate/",
        "./candidate/",
        "candidate/bin/",
        "candidate/src/",
    ]
    for token in forbidden:
        assert token not in workflow
    config = json.loads(
        (
            ROOT / "canonical/FA3-PERMANENT-GATE-HARDENING-001.json"
        ).read_text(encoding="utf-8")
    )
    assert (
        scan_workflow_action_pins(
            ROOT, config["sha_pinned_workflows"]
        )
        == []
    )
