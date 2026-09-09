#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

from fa3_lavasr_provider import (
    OUTPUT_SAMPLE_RATE_HZ,
    AdmissionError,
    select_execution_provider,
    sha256_file,
    validate_audio_contract,
    validate_denoise_policy,
    validate_model_bundle,
    validate_output_integrity,
    validate_runtime_checkout,
    validate_session_provider,
)


def load_runtime_module(runtime_dir: Path):
    module_path = runtime_dir / "lavasr_core.py"
    spec = importlib.util.spec_from_file_location("fa3_pinned_lavasr_runtime", module_path)
    if spec is None or spec.loader is None:
        raise AdmissionError("cannot load pinned LavaSR ONNX runtime module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect real current-host LavaSR ONNX runtime evidence")
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--receipt", default="evidence/receipts/lavasr-current-host.json")
    parser.add_argument("--execution-provider", default="CPUExecutionProvider")
    parser.add_argument("--hrb-receipt")
    parser.add_argument("--allow-resample-projection", action="store_true")
    parser.add_argument("--allow-channel-projection", action="store_true")
    parser.add_argument("--denoise", action="store_true")
    parser.add_argument("--input-already-denoised", action="store_true")
    parser.add_argument("--allow-cascaded-denoise", action="store_true")
    args = parser.parse_args()

    runtime_dir = Path(args.runtime_dir).resolve()
    model_dir = Path(args.model_dir).resolve()
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    receipt_path = Path(args.receipt)

    if not input_path.is_file():
        raise AdmissionError("input audio artifact missing")

    runtime_identity = validate_runtime_checkout(runtime_dir)
    verified_assets = validate_model_bundle(model_dir)
    validate_denoise_policy(args.denoise, args.input_already_denoised, args.allow_cascaded_denoise)

    try:
        import numpy as np
        import onnxruntime as ort
        import soundfile as sf
    except Exception as exc:
        raise AdmissionError("current-host LavaSR runtime dependencies are unavailable") from exc

    info = sf.info(str(input_path))
    validate_audio_contract(
        info.samplerate,
        info.channels,
        explicit_resample_projection=args.allow_resample_projection,
        explicit_channel_projection=args.allow_channel_projection,
    )
    input_duration = float(info.frames) / float(info.samplerate)

    selection = select_execution_provider(args.execution_provider, ort.get_available_providers(), args.hrb_receipt)
    runtime = load_runtime_module(runtime_dir)
    provider_list = [selection.selected]
    model = runtime.LavaSR(
        config=str(runtime_dir / "config.yaml"),
        denoiser_onnx=str(model_dir / "denoiser_core_legacy_fixed63.onnx"),
        enhancer_backbone_onnx=str(model_dir / "enhancer_backbone.onnx"),
        enhancer_spec_head_onnx=str(model_dir / "enhancer_spec_head.onnx"),
        ort_providers=provider_list,
        ort_intra_op_num_threads=1,
        ort_inter_op_num_threads=1,
    )

    session_receipts = {
        "denoiser": validate_session_provider(model.denoiser.session, selection.selected, selection.accelerator),
        "enhancer_backbone": validate_session_provider(model.enhancer.backbone_session, selection.selected, selection.accelerator),
        "enhancer_spec_head": validate_session_provider(model.enhancer.spec_head_session, selection.selected, selection.accelerator),
    }

    waveform = model.load_audio(str(input_path))
    t0 = time.perf_counter()
    enhanced = model.enhance(waveform, apply_denoise=args.denoise)
    elapsed = time.perf_counter() - t0
    integrity = validate_output_integrity(enhanced, input_duration, OUTPUT_SAMPLE_RATE_HZ)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), np.asarray(enhanced, dtype=np.float32), OUTPUT_SAMPLE_RATE_HZ, subtype="FLOAT")
    output_info = sf.info(str(output_path))
    if output_info.samplerate != OUTPUT_SAMPLE_RATE_HZ or output_info.channels != 1:
        raise AdmissionError("written LavaSR output violates 48 kHz mono contract")

    receipt = {
        "schema": "fa3.lavasr-current-host-receipt.v1",
        "provider_id": "FA3-PROVIDER-LAVASR-001",
        "runtime_conformance_id": "FA3-LAVASR-RUNTIME-CONFORMANCE-001",
        "result": "PASS_RUNTIME_INTEGRITY_ONLY",
        "production_admitted": False,
        "production_promotion_blockers": [
            "clean-speech preservation regression evidence",
            "degraded-speech/BWE quality regression evidence",
            "downstream ASR/TTS quality evidence when those projections are promoted",
            "rollback/bypass evidence"
        ],
        "runtime_identity": runtime_identity,
        "model_assets": verified_assets,
        "execution": {
            "requested_provider": selection.requested,
            "selected_provider": selection.selected,
            "accelerator": selection.accelerator,
            "hrb_receipt": selection.hrb_receipt,
            "session_providers": session_receipts,
            "elapsed_seconds": elapsed,
            "input_audio_seconds": input_duration,
            "rtf": elapsed / max(input_duration, 1e-12)
        },
        "audio_contract": {
            "input_sample_rate_hz": info.samplerate,
            "input_channels": info.channels,
            "provider_native_sample_rate_hz": 16000,
            "output_sample_rate_hz": output_info.samplerate,
            "output_channels": output_info.channels,
            "explicit_resample_projection": args.allow_resample_projection,
            "explicit_channel_projection": args.allow_channel_projection,
            "denoise_applied": args.denoise,
            "input_already_denoised": args.input_already_denoised,
            "cascaded_denoise_explicitly_allowed": args.allow_cascaded_denoise,
            "integrity": integrity
        },
        "artifact_lineage": {
            "input_path": str(input_path),
            "input_sha256": sha256_file(input_path),
            "output_path": str(output_path),
            "output_sha256": sha256_file(output_path)
        }
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AdmissionError as exc:
        print(json.dumps({"schema": "fa3.lavasr-current-host-receipt.v1", "result": "FAIL", "error": str(exc)}, indent=2))
        raise SystemExit(2)
