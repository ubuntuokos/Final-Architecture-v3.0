#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

RECEIPT_PATH = "evidence/receipts/language-gateway-current-host.json"
REPORT_PATH = "reports/language-gateway-current-host-gate-report.json"
EXPECTED_SCHEMA = "fa3.language-gateway-current-host-receipt.v1"
EXPECTED_LEVEL = "CURRENT_HOST_GATEWAY_BRIDGE_E2E_PASS"
COLLECTOR_PATH = "evidence/collect-language-gateway-current-host.py"
LITELLM_CONFIG_PATH = "deployment/litellm/config.yaml"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_loopback_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return False
    if parsed.path not in {"", "/"}:
        return False
    return (parsed.hostname or "").lower() in {"127.0.0.1", "::1", "localhost"}


def validate_receipt(root: Path, require_live: bool = True) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    receipt_path = root / RECEIPT_PATH

    def fail(code: str, message: str, **details: Any) -> None:
        findings.append({"code": code, "severity": "P0", "message": message, **details})

    if not receipt_path.is_file():
        return {
            "result": "FAIL",
            "findings": [{"code": "LANG-HOST-001", "severity": "P0", "message": "Language Gateway current-host receipt is missing"}],
        }
    try:
        receipt = _load(receipt_path)
    except Exception as exc:
        return {
            "result": "FAIL",
            "findings": [{"code": "LANG-HOST-002", "severity": "P0", "message": "Language Gateway current-host receipt is unreadable", "detail": repr(exc)}],
        }

    if receipt.get("schema") != EXPECTED_SCHEMA:
        fail("LANG-HOST-003", "Unexpected current-host receipt schema")
    if receipt.get("status") != "PASS" or receipt.get("evidence_level") != EXPECTED_LEVEL:
        fail("LANG-HOST-004", "Current-host evidence level/status is not a gateway/Bridge E2E PASS")
    if receipt.get("current_host_execution") is not True:
        fail("LANG-HOST-005", "Receipt does not assert real current-host execution")
    if require_live and receipt.get("test_fixture") is not False:
        fail("LANG-HOST-006", "Production current-host gate rejects fixture receipts")
    if receipt.get("production_promotion_claim") is not False or receipt.get("translation_quality_claim") is not False:
        fail("LANG-HOST-007", "Gateway/Bridge transport E2E may not claim production promotion or translation quality")

    languages = receipt.get("languages", {})
    primary = str(languages.get("primary", "")).strip()
    secondary = str(languages.get("secondary", "")).strip()
    if not primary or not secondary or primary.lower() == secondary.lower():
        fail("LANG-HOST-008", "Primary and Secondary languages must be explicit and distinct")

    gateway = receipt.get("gateway", {})
    gateway_url = str(gateway.get("base_url", ""))
    if not _is_loopback_url(gateway_url) or gateway.get("loopback") is not True:
        fail("LANG-HOST-009", "Current-host LiteLLM endpoint must be loopback-scoped")
    if gateway.get("authenticated") is not True or gateway.get("credential_material_logged") is not False:
        fail("LANG-HOST-010", "Authenticated gateway execution without credential disclosure is not proven")
    if gateway.get("models_endpoint_pass") is not True or gateway.get("requested_alias_listed") is not True:
        fail("LANG-HOST-011", "LiteLLM /v1/models did not prove requested logical alias availability")
    if not str(gateway.get("model_alias", "")).strip():
        fail("LANG-HOST-012", "Logical model alias is missing")

    host = receipt.get("host", {})
    if not str(host.get("fingerprint_sha256", "")).startswith("sha256:"):
        fail("LANG-HOST-013", "Hashed current-host fingerprint is missing")
    if host.get("runner_class") != "fa3-current-host":
        fail("LANG-HOST-014", "Receipt is not bound to fa3-current-host runner class")

    integrity = receipt.get("integrity", {})
    collector_path = root / COLLECTOR_PATH
    config_path = root / LITELLM_CONFIG_PATH
    if not collector_path.is_file() or integrity.get("collector_sha256") != _sha256(collector_path):
        fail("LANG-HOST-015", "Collector source digest mismatch")
    if not config_path.is_file() or integrity.get("litellm_config_sha256") != _sha256(config_path):
        fail("LANG-HOST-016", "LiteLLM baseline config digest mismatch")

    runtime_ref = receipt.get("execution_evidence", {})
    runtime_path_value = str(runtime_ref.get("path", ""))
    if not runtime_path_value:
        fail("LANG-HOST-017", "Execution evidence path is missing")
    else:
        runtime_path = Path(runtime_path_value)
        if not runtime_path.is_absolute():
            runtime_path = root / runtime_path
        try:
            runtime_path = runtime_path.resolve()
            runtime_path.relative_to(root)
        except Exception:
            fail("LANG-HOST-018", "Execution evidence path escapes repository root")
        else:
            if not runtime_path.is_file():
                fail("LANG-HOST-019", "Execution evidence file is missing")
            elif runtime_ref.get("sha256") != _sha256(runtime_path):
                fail("LANG-HOST-020", "Execution evidence digest mismatch")
            else:
                try:
                    execution = _load(runtime_path)
                except Exception as exc:
                    fail("LANG-HOST-021", "Execution evidence is unreadable", detail=repr(exc))
                else:
                    if execution.get("status") != "PASS" or execution.get("gateway_calls_real") is not True:
                        fail("LANG-HOST-022", "Execution evidence does not prove real gateway calls")
                    if execution.get("raw_credentials_recorded") is not False or execution.get("raw_samples_recorded") is not False:
                        fail("LANG-HOST-023", "Execution evidence records forbidden raw credentials or language samples")

    directions = receipt.get("directions", [])
    expected_pairs = {(primary, secondary), (secondary, primary)} if primary and secondary else set()
    observed_pairs: set[tuple[str, str]] = set()
    if len(directions) != 2:
        fail("LANG-HOST-024", "Exactly two bidirectional language routes are required")
    for index, direction in enumerate(directions):
        source = str(direction.get("source_language", ""))
        target = str(direction.get("target_language", ""))
        observed_pairs.add((source, target))
        bridge = direction.get("bridge_receipt", {})
        if direction.get("status") != "PASS":
            fail("LANG-HOST-025", "Language direction is not PASS", index=index)
        if not str(direction.get("source_sample_sha256", "")).startswith("sha256:") or not str(direction.get("output_sha256", "")).startswith("sha256:"):
            fail("LANG-HOST-026", "Source/output digest missing", index=index)
        if int(direction.get("source_sample_bytes", 0)) < 8 or int(direction.get("output_bytes", 0)) < 1:
            fail("LANG-HOST-027", "Language sample/output is empty or too small", index=index)
        if bridge.get("native_or_mediated") != "MEDIATED" or bridge.get("provider_locality") != "LOCAL":
            fail("LANG-HOST-028", "Bridge route is not proven as local mediated execution", index=index)
        if bridge.get("protected_token_validation") != "PASS" or int(bridge.get("protected_token_count", 0)) < 3:
            fail("LANG-HOST-029", "Protected-token round-trip is incomplete", index=index)
        if bridge.get("semantic_validation") != "PASS" or bridge.get("authority_expanded_by_mediation") is not False:
            fail("LANG-HOST-030", "Semantic validation or no-authority-expansion proof missing", index=index)
        if bridge.get("current_host_production_claim") is not False:
            fail("LANG-HOST-031", "Bridge receipt overclaims current-host production", index=index)
        if not str(direction.get("translation_response_model", "")).strip() or not str(direction.get("validation_response_model", "")).strip():
            fail("LANG-HOST-032", "Executed translation/validation model identity missing", index=index)
    if observed_pairs != expected_pairs:
        fail("LANG-HOST-033", "Bidirectional Primary/Secondary route set mismatch", expected=sorted(expected_pairs), observed=sorted(observed_pairs))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings, "receipt": receipt}


def gate(root: Path, require_live: bool = True) -> dict[str, Any]:
    checked = validate_receipt(root, require_live=require_live)
    report = {
        "schema": "fa3.language-gateway-current-host-gate-report.v1",
        "gate_id": "FA3-LANGUAGE-GATEWAY-CURRENT-HOST-001",
        "result": checked["result"],
        "findings": checked["findings"],
        "evidence_level": checked.get("receipt", {}).get("evidence_level"),
        "proves": "REAL_CURRENT_HOST_LITELLM_AND_LANGUAGE_BRIDGE_TRANSPORT_E2E_ONLY",
        "does_not_prove": [
            "translation quality promotion",
            "independent semantic validation",
            "underlying model/provider production admission",
            "HRB/model-registry admission for the selected backend",
            "global FA3 production promotion"
        ],
    }
    _write(root.resolve() / REPORT_PATH, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate FA3 Language Gateway/Bridge current-host evidence")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--allow-fixture", action="store_true", help="test-only; never production evidence")
    args = parser.parse_args()
    report = gate(Path(args.root), require_live=not args.allow_fixture)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
