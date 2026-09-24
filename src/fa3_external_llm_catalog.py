#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "fa3.external-llm-runtime-catalog.v1"
REFERENCE_ID = "FA3-FREELLM-UPSTREAM-REFERENCE-2026-09-24"
STATES = ("DISCOVERED", "OBSERVED", "VERIFIED", "ADMITTED", "ENABLED")
FORBIDDEN_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "secret_value",
    "token_value",
    "bearer_token",
    "authorization_header",
    "password",
)


def _strip_markup(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = value.replace(chr(96), "")
    return html.unescape(value).strip()


def _split_row(line: str) -> list[str]:
    body = line.strip().strip("|")
    return [_strip_markup(cell) for cell in body.split("|")]


def _section(text: str, begin: str, end: str) -> str:
    marker_begin = f"<!-- {begin} -->"
    marker_end = f"<!-- {end} -->"
    start = text.find(marker_begin)
    finish = text.find(marker_end)
    if start < 0 or finish < 0 or finish <= start:
        return ""
    return text[start + len(marker_begin):finish]


def _parse_table(section: str) -> list[dict[str, str]]:
    lines = [line for line in section.splitlines() if line.lstrip().startswith("|")]
    if len(lines) < 3:
        return []
    headers = _split_row(lines[0])
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        values = _split_row(line)
        if len(values) != len(headers):
            continue
        rows.append(dict(zip(headers, values)))
    return rows


def _slug(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def _int_or_none(value: str) -> int | None:
    try:
        return int(value.replace(",", "").strip())
    except Exception:
        return None


def _modalities(value: str) -> list[str]:
    return sorted({item.strip().lower() for item in value.split(",") if item.strip()})


def normalize_markdown(
    text: str,
    *,
    source_commit: str,
    observed_at: str,
    source_reference_id: str = REFERENCE_ID,
) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("source_commit must be an immutable 40-hex commit")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", observed_at):
        raise ValueError("observed_at must be YYYY-MM-DD")

    permanent = _parse_table(_section(text, "BEGIN_PERMANENT_FREE", "END_PERMANENT_FREE"))
    renewable = _parse_table(_section(text, "BEGIN_RENEWABLE", "END_RENEWABLE"))
    quick_ref = _parse_table(_section(text, "BEGIN_QUICK_REF", "END_QUICK_REF"))

    base_urls: dict[str, str] = {}
    quick_auth: dict[str, str] = {}
    for row in quick_ref:
        name = row.get("Provider", "").strip()
        if not name:
            continue
        base_urls[name] = row.get("Base URL", "").strip()
        quick_auth[name] = row.get("Credit Card?", "").strip()

    providers: list[dict[str, Any]] = []
    for tier, rows in (("PERMANENT_FREE", permanent), ("RENEWABLE_CREDITS", renewable)):
        for row in rows:
            name = row.get("Provider", "").strip()
            if not name:
                continue
            registration = (
                row.get("Credit Card?", "").strip()
                or row.get("Credit Model", "").strip()
                or quick_auth.get(name, "")
            )
            providers.append(
                {
                    "external_provider_key": _slug(name),
                    "provider_name": name,
                    "discovery_state": "DISCOVERED",
                    "free_tier_kind": tier,
                    "free_models": _int_or_none(row.get("Free Models", "")),
                    "max_context": row.get("Max Context", "").strip(),
                    "modalities": _modalities(row.get("Modalities", "")),
                    "registration_requirement": registration,
                    "base_url": base_urls.get(name, ""),
                    "source_attribution": {
                        "reference_id": source_reference_id,
                        "source_commit": source_commit,
                        "observed_at": observed_at,
                    },
                    "admission": {
                        "fa3_provider_id": None,
                        "admission_receipt": None,
                        "explicit_external_policy": False,
                        "credential_handle_present": False,
                        "live_capability_probe": False,
                    },
                }
            )

    providers.sort(key=lambda row: (row["provider_name"].lower(), row["external_provider_key"]))
    catalog = {
        "schema": SCHEMA,
        "source": {
            "reference_id": source_reference_id,
            "commit": source_commit,
            "observed_at": observed_at,
            "bytes_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        },
        "generated_runtime_state": True,
        "canonical_policy": False,
        "contains_secret_values": False,
        "providers": providers,
    }
    errors = validate_runtime_catalog(catalog)
    if errors:
        raise ValueError("normalized catalog failed validation: " + "; ".join(errors))
    return catalog


def _walk_forbidden(obj: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            lower = str(key).lower()
            if any(fragment in lower for fragment in FORBIDDEN_KEY_FRAGMENTS):
                findings.append(f"{path}.{key}: forbidden credential-value field")
            findings.extend(_walk_forbidden(value, f"{path}.{key}"))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            findings.extend(_walk_forbidden(value, f"{path}[{index}]"))
    return findings


def validate_runtime_catalog(catalog: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if catalog.get("schema") != SCHEMA:
        findings.append("schema mismatch")
    if catalog.get("canonical_policy") is not False:
        findings.append("runtime catalog must not be canonical policy")
    if catalog.get("contains_secret_values") is not False:
        findings.append("catalog must declare contains_secret_values=false")
    source = catalog.get("source")
    if not isinstance(source, dict):
        findings.append("missing source")
    else:
        if not re.fullmatch(r"[0-9a-f]{40}", str(source.get("commit", ""))):
            findings.append("source commit is not immutable 40-hex")
        if not re.fullmatch(r"[0-9a-f]{64}", str(source.get("bytes_sha256", ""))):
            findings.append("source bytes sha256 missing or malformed")

    providers = catalog.get("providers")
    if not isinstance(providers, list):
        findings.append("providers must be a list")
        providers = []
    seen: set[str] = set()
    for index, row in enumerate(providers):
        if not isinstance(row, dict):
            findings.append(f"provider[{index}] is not an object")
            continue
        key = str(row.get("external_provider_key", ""))
        if not key or key in seen:
            findings.append(f"provider[{index}] key missing or duplicate")
        seen.add(key)
        state = row.get("discovery_state")
        if state not in STATES:
            findings.append(f"provider[{index}] invalid discovery_state")
        if not isinstance(row.get("provider_name"), str) or not row["provider_name"].strip():
            findings.append(f"provider[{index}] provider_name missing")
        admission = row.get("admission")
        if not isinstance(admission, dict):
            findings.append(f"provider[{index}] admission object missing")
    findings.extend(_walk_forbidden(catalog))
    return findings


def transition_allowed(current: str, target: str) -> bool:
    if current not in STATES or target not in STATES:
        return False
    if current == target:
        return True
    return STATES.index(target) == STATES.index(current) + 1


def runtime_eligible(
    row: dict[str, Any],
    *,
    security_privacy_admitted: bool,
    egress_policy_admitted: bool,
    credential_required: bool,
) -> bool:
    if row.get("discovery_state") not in {"ADMITTED", "ENABLED"}:
        return False
    admission = row.get("admission")
    if not isinstance(admission, dict):
        return False
    if not str(admission.get("fa3_provider_id") or "").startswith("FA3-PROVIDER-"):
        return False
    if not str(admission.get("admission_receipt") or "").strip():
        return False
    if admission.get("explicit_external_policy") is not True:
        return False
    if admission.get("live_capability_probe") is not True:
        return False
    if credential_required and admission.get("credential_handle_present") is not True:
        return False
    if not security_privacy_admitted or not egress_policy_admitted:
        return False
    return True


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    path.chmod(0o600)


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 external LLM catalog normalizer")
    sub = parser.add_subparsers(dest="command", required=True)

    normalize = sub.add_parser("normalize")
    normalize.add_argument("--input", required=True)
    normalize.add_argument("--output", required=True)
    normalize.add_argument("--source-commit", required=True)
    normalize.add_argument("--observed-at", required=True)
    normalize.add_argument("--source-reference-id", default=REFERENCE_ID)

    validate = sub.add_parser("validate")
    validate.add_argument("--catalog", required=True)

    args = parser.parse_args()
    if args.command == "normalize":
        text = Path(args.input).read_text(encoding="utf-8")
        catalog = normalize_markdown(
            text,
            source_commit=args.source_commit,
            observed_at=args.observed_at,
            source_reference_id=args.source_reference_id,
        )
        _write_json(Path(args.output).expanduser(), catalog)
        print(json.dumps({"result": "PASS", "providers": len(catalog["providers"]), "output": args.output}))
        return 0

    catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    findings = validate_runtime_catalog(catalog)
    print(json.dumps({"result": "PASS" if not findings else "FAIL", "findings": findings}, indent=2))
    return 0 if not findings else 2


if __name__ == "__main__":
    raise SystemExit(main())
