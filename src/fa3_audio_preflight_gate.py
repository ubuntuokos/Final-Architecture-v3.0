#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

CONTRACT_PATH = Path("canonical/contracts/FA3-AUDIO-PREFLIGHT-CONTRACTS-001.json")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class AudioPreflightDenied(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_request(request: dict[str, Any]) -> dict[str, Any]:
    layers: list[dict[str, Any]] = []

    def layer(name: str, checks: list[tuple[bool, str]]) -> None:
        failures = [message for ok, message in checks if not ok]
        layers.append({"layer": name, "result": "PASS" if not failures else "FAIL", "findings": failures})

    sha = str(request.get("sha256", ""))
    codec = str(request.get("codec", "")).lower()
    sample_rate = int(request.get("sample_rate_hz", 0) or 0)
    channels = int(request.get("channels", 0) or 0)
    supported_codecs = {str(item).lower() for item in request.get("supported_codecs", [])}
    supported_rates = {int(item) for item in request.get("supported_sample_rates_hz", [])}
    supported_channels = {int(item) for item in request.get("supported_channel_counts", [])}

    layer("L1_INPUT_INTEGRITY", [
        (bool(request.get("artifact_id")), "artifact_id missing"),
        (bool(SHA256.match(sha)), "sha256 missing or invalid"),
        (bool(codec), "codec missing"),
        (sample_rate > 0, "sample_rate_hz must be positive"),
        (channels > 0, "channels must be positive"),
    ])

    layer("L2_MEDIA_CONTRACT", [
        (codec in supported_codecs, f"unsupported codec: {codec}"),
        (sample_rate in supported_rates, f"unsupported sample rate: {sample_rate}"),
        (channels in supported_channels, f"unsupported channel count: {channels}"),
    ])

    ram_budget = int(request.get("ram_budget_bytes", 0) or 0)
    vram_budget = int(request.get("vram_budget_bytes", 0) or 0)
    peak_ram = int(request.get("estimated_peak_ram_bytes", 0) or 0)
    peak_vram = int(request.get("estimated_peak_vram_bytes", 0) or 0)
    accelerator = bool(request.get("accelerator"))
    layer("L3_RESOURCE_BUDGET", [
        (bool(request.get("bounded_execution")), "execution is not bounded"),
        (ram_budget > 0 and peak_ram <= ram_budget, "RAM budget exceeded or absent"),
        ((not accelerator) or (vram_budget > 0 and peak_vram <= vram_budget), "VRAM budget exceeded or absent"),
    ])

    layer("L4_HRB_ADMISSION", [
        ((not accelerator) or bool(request.get("hrb_lease_id")), "accelerator execution requires HRB lease"),
        (request.get("provider_self_placed_device") is not True, "provider self-placement is forbidden"),
    ])

    layer("L5_PROVENANCE", [
        (bool(request.get("source_artifact_id")), "source_artifact_id missing"),
        (bool(request.get("provider_id")), "provider_id missing"),
        (bool(request.get("model_or_runtime_lock_ref")), "model/runtime immutable lock reference missing"),
    ])

    layer("L6_OUTPUT_CONTRACT", [
        (bool(request.get("output_artifact_type")), "output_artifact_type missing"),
        (bool(request.get("output_codec")), "output_codec missing"),
        (request.get("output_lineage_required") is True, "output lineage must be required"),
    ])

    failed = [item for item in layers if item["result"] != "PASS"]
    return {
        "schema": "fa3.audio-preflight-gate-report.v1",
        "result": "PASS" if not failed else "FAIL",
        "layers": layers,
        "provider_specific_gate_required": True,
    }


def gate(root: Path, request_path: Path | None = None) -> dict[str, Any]:
    contract = _load(root / CONTRACT_PATH)
    if contract.get("provider_neutral") is not True or contract.get("policy", {}).get("fail_closed") is not True:
        return {"result": "FAIL", "findings": ["audio preflight contract is not provider-neutral fail-closed"]}
    if request_path is None:
        return {"result": "PASS", "contract_id": contract.get("id"), "layer_count": len(contract.get("layers", []))}
    return validate_request(_load(request_path))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--request")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    request = Path(args.request).resolve() if args.request else None
    report = gate(root, request)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("result") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
