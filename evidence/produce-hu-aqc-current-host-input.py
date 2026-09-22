#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_hu_aqc_input import produce_bundle, validate_bundle
from fa3_runtime_hardening_current_host import write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Produce a fail-closed HU-AQC current-host input bundle from real scorer receipts")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--audio", required=True)
    parser.add_argument("--reference-text-file", required=True)
    parser.add_argument("--host-attestation", required=True)
    parser.add_argument("--asr-receipt", required=True)
    parser.add_argument("--language-receipt", required=True)
    parser.add_argument("--grammar-receipt", required=True)
    parser.add_argument("--toxicity-receipt", required=True)
    parser.add_argument("--perceptual-receipt", required=True)
    parser.add_argument("--speaker-receipt")
    parser.add_argument("--cloning", action="store_true")
    parser.add_argument("--output", default=".fa3-current-host/input/hu-aqc-metrics.json")
    args = parser.parse_args()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise SystemExit("HU-AQC input producer must run rootless")
    root = Path(args.root).resolve()
    receipts = {
        "asr": Path(args.asr_receipt).expanduser(),
        "language": Path(args.language_receipt).expanduser(),
        "grammar": Path(args.grammar_receipt).expanduser(),
        "toxicity": Path(args.toxicity_receipt).expanduser(),
        "perceptual": Path(args.perceptual_receipt).expanduser(),
    }
    if args.speaker_receipt:
        receipts["speaker"] = Path(args.speaker_receipt).expanduser()
    bundle = produce_bundle(
        root,
        audio=Path(args.audio).expanduser(),
        reference_text_file=Path(args.reference_text_file).expanduser(),
        host_attestation=Path(args.host_attestation).expanduser(),
        scorer_receipts=receipts,
        cloning=bool(args.cloning),
    )
    findings = validate_bundle(root, audio=Path(args.audio).expanduser().resolve(), bundle=bundle)
    if findings:
        raise SystemExit("; ".join(findings))
    output = Path(args.output).expanduser()
    if not output.is_absolute():
        output = root / output
    write_json(output, bundle)
    print(json.dumps({
        "status": "PASS",
        "schema": bundle["schema"],
        "host_attestation_ref": bundle["host_attestation_ref"],
        "source_scorers": sorted(bundle["source_receipts"]),
        "output": str(output),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
