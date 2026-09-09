#!/usr/bin/env python3
from __future__ import annotations
import argparse, array, hashlib, json, sys, wave
from pathlib import Path
from fa3_gtcrn_provider import create_onnx_session, enhance_waveform, validate_audio_contract

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def read_wav(path: Path):
    with wave.open(str(path), "rb") as w:
        channels = w.getnchannels(); rate = w.getframerate(); width = w.getsampwidth(); n = w.getnframes(); raw = w.readframes(n)
    if width != 2:
        raise RuntimeError("current collector admits 16-bit PCM WAV only")
    validate_audio_contract(rate, channels)
    a = array.array("h"); a.frombytes(raw)
    if sys.byteorder != "little":
        a.byteswap()
    try:
        import numpy as np
    except Exception as e:
        raise RuntimeError("numpy required in isolated GTCRN current-host runtime") from e
    return np.asarray(a, dtype=np.float32) / 32768.0, {"channels": channels, "sample_rate_hz": rate, "sample_width": width, "frames": n}, raw

def write_wav(path: Path, y, rate: int):
    import numpy as np
    z = np.clip(np.asarray(y, dtype=np.float32), -1.0, 0.9999695)
    pcm = (z * 32768.0).astype("<i2").tobytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
    return pcm

def main():
    ap = argparse.ArgumentParser(description="Collect real GTCRN current-host ONNX audio E2E evidence")
    ap.add_argument("--model", required=True); ap.add_argument("--input", required=True); ap.add_argument("--output", required=True); ap.add_argument("--expected-sha256", required=True); ap.add_argument("--provider", default="CPUExecutionProvider"); ap.add_argument("--hrb-receipt")
    a = ap.parse_args(); root = Path(__file__).resolve().parents[1]
    x, meta, raw = read_wav(Path(a.input))
    session, selection, model_sha = create_onnx_session(a.model, a.expected_sha256, a.provider, a.hrb_receipt)
    y, perf = enhance_waveform(session, x, meta["sample_rate_hz"], meta["channels"])
    out_raw = write_wav(Path(a.output), y, meta["sample_rate_hz"])
    receipt = {"schema": "fa3.gtcrn-current-host-receipt.v1", "provider_id": "FA3-PROVIDER-GTCRN-001", "status": "RUNTIME_E2E_PASS_QUALITY_PROMOTION_PENDING", "production_pass": False, "model_sha256": model_sha, "execution_provider": selection.selected, "input_meta": meta, "input_pcm_sha256": sha256_bytes(raw), "output_pcm_sha256": sha256_bytes(out_raw), "performance": perf, "quality_gate": "PENDING_CLEAN_SPEECH_AND_NOISY_SPEECH_GOLDEN_CORPUS", "rollback_bypass_gate": "PENDING_OPERATOR_RECEIPT", "note": "Real ONNX E2E is necessary but not sufficient for production promotion."}
    p = root / "evidence/receipts/gtcrn-current-host.json"; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
