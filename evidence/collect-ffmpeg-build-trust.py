#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, re, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ffmpeg_version(binary: Path) -> str:
    p = subprocess.run([str(binary), "-hide_banner", "-version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=20)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg -version failed")
    m = re.search(r"^ffmpeg version\s+([^\s]+)", p.stdout, re.MULTILINE)
    if not m:
        raise RuntimeError("cannot parse observed FFmpeg version")
    return m.group(1)


def main() -> int:
    ap = argparse.ArgumentParser(description="Create FA3 FFmpeg build-trust v2 from offline cryptographic evidence")
    ap.add_argument("--artifact", required=True, help="signed FFmpeg source archive or signed distribution package artifact")
    ap.add_argument("--signature", required=True, help="detached signature for --artifact")
    ap.add_argument("--keyring", required=True, help="admitted verification keyring")
    ap.add_argument("--sbom", required=True)
    ap.add_argument("--provenance-attestation", required=True)
    ap.add_argument("--immutable-version-identity", required=True)
    ap.add_argument("--trust-mode", choices=("UPSTREAM_SIGNED_RELEASE", "DISTRIBUTION_SIGNED_PACKAGE"), required=True)
    ap.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    ap.add_argument("--gpgv", default=shutil.which("gpgv"))
    ap.add_argument("--output", default=".fa3-current-host/input/ffmpeg-ai-build-trust-v2.json")
    args = ap.parse_args()

    artifact = Path(args.artifact).resolve(); signature = Path(args.signature).resolve(); keyring = Path(args.keyring).resolve()
    sbom = Path(args.sbom).resolve(); provenance = Path(args.provenance_attestation).resolve(); binary = Path(args.ffmpeg or "").resolve(); gpgv = Path(args.gpgv or "").resolve()
    for p in (artifact, signature, keyring, sbom, provenance, binary, gpgv):
        if not p.is_file():
            raise SystemExit(f"required file missing: {p}")
    if re.search(r"(?:master|snapshot|nightly)", args.immutable_version_identity, re.I):
        raise SystemExit("floating/master/snapshot/nightly version identity is forbidden")

    verify_cmd = [str(gpgv), "--keyring", str(keyring), str(signature), str(artifact)]
    vp = subprocess.run(verify_cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60)
    transcript = vp.stdout + "\n" + vp.stderr
    if vp.returncode != 0:
        raise SystemExit("gpgv signature verification failed")
    key_match = re.search(r"using\s+(?:RSA|DSA|ECDSA|EDDSA)?\s*key\s+([0-9A-F]{16,64})", transcript, re.I)
    if not key_match:
        key_match = re.search(r"key\s+([0-9A-F]{16,64})", transcript, re.I)
    if not key_match:
        raise SystemExit("cannot extract signing key identity from gpgv verification transcript")

    vv = subprocess.run([str(gpgv), "--version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=10)
    verifier_version = vv.stdout.splitlines()[0].strip() if vv.stdout.splitlines() else "UNKNOWN"
    observed_version = ffmpeg_version(binary)
    receipt = {
        "schema": "fa3.ffmpeg-build-trust-receipt.v2",
        "status": "PASS",
        "trust_mode": args.trust_mode,
        "release_channel": "STABLE",
        "signature_verified": True,
        "floating_master_or_nightly": False,
        "observed_ffmpeg_version": observed_version,
        "immutable_version_identity": args.immutable_version_identity,
        "installed_ffmpeg_binary_sha256": sha256_file(binary),
        "source_or_package_sha256": sha256_file(artifact),
        "sbom_sha256": sha256_file(sbom),
        "provenance_attestation_sha256": sha256_file(provenance),
        "verifier": {
            "tool": "gpgv",
            "version": verifier_version,
            "verification_method": "OFFLINE_DETACHED_SIGNATURE_WITH_EXPLICIT_KEYRING",
            "verification_result_sha256": sha256_text(transcript),
            "binary_sha256": sha256_file(gpgv),
            "keyring_sha256": sha256_file(keyring),
            "signature_sha256": sha256_file(signature),
        },
        "signing_identity": {
            "type": "OPENPGP_KEY_ID_OR_FINGERPRINT_FROM_GPGV_TRANSCRIPT",
            "value": key_match.group(1).upper(),
        },
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "network_access_required": False,
        "current_host_runtime_promotion_claim": False,
    }
    out = Path(args.output).resolve(); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
