#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_model_artifact_security_runtime import admit, collect_tool_inventory, run_scanner, runtime_home, sha256_file
from fa3_model_manager_security_hook import evaluate as model_manager_hook

RECEIPT = ROOT / "evidence/receipts/model-artifact-security-current-host.json"
RUNTIME_ID = "FA3-MODEL-ARTIFACT-SECURITY-RUNTIME-CONFORMANCE-001"


def _candidate_roots() -> list[Path]:
    values = []
    env = os.environ.get("FA3_MODEL_SECURITY_MODEL_ROOTS")
    if env:
        values.extend(Path(x).expanduser() for x in env.split(":") if x)
    values.extend([
        Path("/AI-modells/StabilityMatrix/Models"),
        Path("/AI-modells/StabilityMatrix/Data/Models"),
    ])
    out, seen = [], set()
    for p in values:
        q = p.expanduser().resolve()
        if q not in seen and q.is_dir():
            seen.add(q); out.append(q)
    return out


def _find_real_target() -> Path:
    explicit = os.environ.get("FA3_MODEL_SECURITY_E2E_TARGET")
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.is_file() or p.is_symlink() or p.suffix.lower() not in {".safetensors", ".gguf"}:
            raise RuntimeError("FA3_MODEL_SECURITY_E2E_TARGET must be a real regular .safetensors or .gguf file")
        return p
    max_bytes = int(os.environ.get("FA3_MODEL_SECURITY_E2E_MAX_BYTES", str(8 * 1024**3)))
    best: tuple[int, Path] | None = None
    visited = 0
    for root in _candidate_roots():
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith(".")][:64]
            for name in files:
                visited += 1
                if visited > 50000:
                    break
                p = Path(base) / name
                if p.suffix.lower() not in {".safetensors", ".gguf"} or p.is_symlink():
                    continue
                try: size = p.stat().st_size
                except OSError: continue
                if size < 1024 or size > max_bytes: continue
                if best is None or size < best[0]: best = (size, p.resolve())
            if visited > 50000: break
        if best is not None: break
    if best is None:
        raise RuntimeError("no real local .safetensors/.gguf model artifact found; set FA3_MODEL_SECURITY_E2E_TARGET")
    return best[1]


def _target_model_class(target: Path) -> str:
    explicit = os.environ.get("FA3_MODEL_SECURITY_E2E_MODEL_CLASS")
    if explicit:
        return explicit.strip().upper()
    if "StabilityMatrix" in str(target):
        return "DIFFUSION"
    raise RuntimeError("set FA3_MODEL_SECURITY_E2E_MODEL_CLASS for explicit/custom E2E targets; model class must never be guessed")


def _make_negative_pickle(home: Path) -> Path:
    d = home / "negative-fixtures"; d.mkdir(parents=True, exist_ok=True)
    p = d / "fa3-controlled-malicious-pickle.pkl"
    # Static protocol-0 pickle that references os.system. It is NEVER unpickled/executed.
    p.write_bytes(b"cos\nsystem\n(S'echo FA3_CONTROLLED_MALICIOUS_FIXTURE'\ntR.")
    os.chmod(p, 0o444)
    return p


def _database_manifest(home: Path) -> dict:
    candidates = []
    for base in [home / "cache/clamav", Path("/var/lib/clamav"), home / "cache/trivy"]:
        if base.is_dir():
            for p in sorted(base.rglob("*")):
                if p.is_file() and p.stat().st_size > 0:
                    candidates.append({"path_class": base.name, "name": p.name, "size": p.stat().st_size, "mtime_ns": p.stat().st_mtime_ns})
    payload = json.dumps(candidates, sort_keys=True).encode()
    return {
        "entry_count": len(candidates),
        "manifest_sha256": hashlib.sha256(payload).hexdigest(),
        "clamav_database_present": any(x["name"].endswith((".cvd", ".cld")) for x in candidates),
        "trivy_database_present": any(x["name"] == "trivy.db" for x in candidates),
    }


def main() -> int:
    if os.geteuid() == 0:
        raise SystemExit("refusing root execution")
    home = runtime_home()
    target = _find_real_target()
    target_sha = sha256_file(target)
    model_class = _target_model_class(target)
    production = admit(ROOT, target, f"local-content-sha256:{target_sha}", model_class=model_class)
    hook = model_manager_hook(production, target_sha)
    fixture = _make_negative_pickle(home)
    negative_results = {}
    blocking = []
    for sid in ["modelaudit", "modelscan", "picklescan", "fickling"]:
        row = run_scanner(sid, ROOT, home, fixture)
        negative_results[sid] = {"status": row.get("status"), "execution": row.get("execution", {})}
        if row.get("status") == "FAIL": blocking.append(sid)
    inventory = collect_tool_inventory(ROOT, home)
    db = _database_manifest(home)
    all_tools = all(v.get("present") and v.get("binary_or_package_digest") and v.get("ruleset_digest") for v in inventory.values())
    negative_ok = set(blocking) == {"modelaudit","modelscan","picklescan","fickling"}
    production_ok = production.get("promotion", {}).get("security_state") == "SECURITY_ADMITTED"
    hook_ok = hook.get("model_manager_promotion_eligible") is True
    status = "PASS" if all_tools and negative_ok and production_ok and hook_ok and db["clamav_database_present"] and db["trivy_database_present"] else "FAIL"
    receipt = {
        "schema": "fa3.model-artifact-security-current-host-receipt.v1",
        "runtime_id": RUNTIME_ID,
        "status": status,
        "evidence_level": "CURRENT_HOST_PRODUCTION_E2E_PASS" if status == "PASS" else "CURRENT_HOST_EXECUTION_FAILED",
        "real_tool_execution": True,
        "synthetic_target": False,
        "target_model_class": model_class,
        "synthetic_negative_fixture": True,
        "root_execution": False,
        "scan_network_egress": False,
        "modelaudit_telemetry": False,
        "runtime_promotion_eligible": status == "PASS",
        "host": {"system": platform.system(), "release": platform.release(), "machine": platform.machine(), "python": platform.python_version()},
        "runtime_home": str(home),
        "real_target": {"path": str(target), "sha256": target_sha, "size": target.stat().st_size, "extension": target.suffix.lower()},
        "toolchain": inventory,
        "database_manifest": db,
        "production_admission": production,
        "model_manager_hook": hook,
        "negative_pickle_regression": {"fixture_sha256": sha256_file(fixture), "fixture_executed": False, "blocked": negative_ok, "blocking_scanners": sorted(blocking), "scanner_results": negative_results},
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": 143,
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "target": str(target), "receipt": str(RECEIPT)}, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__": raise SystemExit(main())
