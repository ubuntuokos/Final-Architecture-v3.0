#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCANNER_IDS = (
    "modelaudit", "clamav", "yara", "trivy", "bandit", "pip-audit",
    "modelscan", "picklescan", "fickling", "garak", "cosign",
)
ALWAYS = {"modelaudit", "clamav", "yara"}
DANGEROUS_EXTENSIONS = {".pkl", ".pickle", ".pt", ".pth", ".bin", ".ckpt"}
GENERATIVE_CLASSES = {"LLM", "CHAT", "TEXT_GENERATION", "AGENTIC_TEXT_MODEL"}
DEFAULT_HOME = Path("/ai-cache/fa3/model-security")
LOCK_PATH = "canonical/model-artifact-security-runtime-lock.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def runtime_home() -> Path:
    value = os.environ.get("FA3_MODEL_SECURITY_HOME")
    return Path(value).expanduser().resolve() if value else DEFAULT_HOME


def _tool_path(home: Path, scanner_id: str) -> Path:
    static = home / "venv-static" / "bin"
    garak = home / "venv-garak" / "bin"
    mapping = {
        "modelaudit": static / "modelaudit", "modelscan": static / "modelscan",
        "picklescan": static / "picklescan", "fickling": static / "fickling",
        "bandit": static / "bandit", "pip-audit": static / "pip-audit",
        "garak": garak / "garak", "trivy": home / "bin" / "trivy",
        "cosign": home / "bin" / "cosign",
    }
    if scanner_id in mapping:
        return mapping[scanner_id]
    system_name = {"clamav": "clamscan", "yara": "yara"}[scanner_id]
    resolved = shutil.which(system_name)
    return Path(resolved).resolve() if resolved else Path("/__missing__") / system_name


def _version_args(scanner_id: str, tool: Path) -> list[str]:
    return [str(tool), "version"] if scanner_id == "cosign" else [str(tool), "--version"]


def _safe_version(scanner_id: str, tool: Path) -> str:
    if not tool.is_file():
        return "MISSING"
    try:
        p = subprocess.run(
            _version_args(scanner_id, tool), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=20, check=False,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "NO_ANALYTICS": "1", "PROMPTFOO_DISABLE_TELEMETRY": "1"},
        )
        value = (p.stdout or "").strip().splitlines()
        return value[0][:300] if value else f"exit:{p.returncode}"
    except Exception as exc:
        return f"ERROR:{type(exc).__name__}:{exc}"[:300]


def _ruleset_digest(root: Path, home: Path, scanner_id: str) -> tuple[str, str]:
    payload = bytearray(scanner_id.encode("utf-8"))
    for path in (root / LOCK_PATH, home / "rules" / "fa3-model-security.yar", home / "state" / "database-manifest.json"):
        if path.is_file():
            payload.extend(path.read_bytes())
    return (f"FA3-MODEL-SECURITY-RULESET:{scanner_id}", sha256_bytes(bytes(payload)))


def collect_tool_inventory(root: Path, home: Path) -> dict[str, dict[str, Any]]:
    inventory: dict[str, dict[str, Any]] = {}
    for scanner_id in SCANNER_IDS:
        tool = _tool_path(home, scanner_id)
        ruleset_id, ruleset_digest = _ruleset_digest(root, home, scanner_id)
        inventory[scanner_id] = {
            "scanner_id": scanner_id,
            "path": str(tool),
            "present": tool.is_file() and os.access(tool, os.X_OK),
            "version": _safe_version(scanner_id, tool),
            "binary_or_package_digest": sha256_file(tool) if tool.is_file() else None,
            "ruleset_id": ruleset_id,
            "ruleset_digest": ruleset_digest,
        }
    return inventory


def _sandbox_prefix(home: Path) -> list[str]:
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise RuntimeError("bubblewrap is required for fail-closed network/secret isolation")
    user_home = Path.home().resolve()
    return [
        bwrap, "--die-with-parent", "--new-session", "--unshare-net",
        "--ro-bind", "/", "/", "--tmpfs", "/run", "--tmpfs", "/tmp",
        "--tmpfs", str(user_home), "--proc", "/proc", "--dev", "/dev",
        "--chdir", "/tmp", "--clearenv", "--setenv", "HOME", "/nonexistent",
        "--setenv", "PATH", f"{home}/bin:{home}/venv-static/bin:{home}/venv-garak/bin:/usr/bin:/bin",
        "--setenv", "PROMPTFOO_DISABLE_TELEMETRY", "1", "--setenv", "NO_ANALYTICS", "1",
        "--setenv", "CI", "true", "--",
    ]


def run_isolated(home: Path, argv: list[str], timeout: int = 300) -> dict[str, Any]:
    started = time.time()
    p = subprocess.run(_sandbox_prefix(home) + argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout, check=False)
    stdout, stderr = p.stdout or "", p.stderr or ""
    return {
        "argv": argv, "returncode": p.returncode,
        "stdout_sha256": sha256_bytes(stdout.encode()), "stderr_sha256": sha256_bytes(stderr.encode()),
        "stdout_length": len(stdout), "stderr_length": len(stderr),
        "stdout_excerpt": stdout[:1000], "stderr_excerpt": stderr[:1000],
        "duration_ms": int((time.time() - started) * 1000),
        "sandbox": "bubblewrap", "network_egress": False, "secret_access": False, "host_socket_access": False,
    }


def _scanner_command(scanner_id: str, home: Path, target: Path, source_root: Path | None = None, requirements: Path | None = None) -> list[str]:
    tool = _tool_path(home, scanner_id)
    if scanner_id == "modelaudit": return [str(tool), str(target), "--format", "json"]
    if scanner_id == "clamav":
        db = home / "cache" / "clamav"
        if not any(db.glob("*.c?d")):
            db = Path("/var/lib/clamav")
        return [str(tool), "--no-summary", f"--database={db}", str(target)]
    if scanner_id == "yara": return [str(tool), "-w", str(home / "rules" / "fa3-model-security.yar"), str(target)]
    if scanner_id == "modelscan": return [str(tool), "-p", str(target), "-r", "json"]
    if scanner_id == "picklescan": return [str(tool), "--path", str(target)]
    if scanner_id == "fickling": return [str(tool), "--check-safety", "-p", str(target)]
    if scanner_id == "trivy":
        if source_root is None: raise RuntimeError("trivy requires source_root")
        return [str(tool), "fs", "--cache-dir", str(home / "cache" / "trivy"), "--skip-db-update", "--offline-scan", "--scanners", "vuln,secret,misconfig", "--severity", "HIGH,CRITICAL", "--exit-code", "1", "--format", "json", str(source_root)]
    if scanner_id == "bandit":
        if source_root is None: raise RuntimeError("bandit requires source_root")
        return [str(tool), "-q", "-r", str(source_root), "-f", "json"]
    if scanner_id == "pip-audit":
        if requirements is None: raise RuntimeError("pip-audit requires requirements file")
        return [str(tool), "--disable-pip", "--no-deps", "-r", str(requirements), "--cache-dir", str(home / "cache" / "pip-audit"), "-f", "json"]
    raise RuntimeError(f"scanner {scanner_id} requires specialized offline verification input")


def _scan_status(scanner_id: str, result: dict[str, Any]) -> str:
    rc = int(result["returncode"])
    if scanner_id == "yara":
        return "PASS" if rc == 0 and not str(result.get("stdout_excerpt", "")).strip() else ("FAIL" if rc == 0 else "ERROR")
    return "PASS" if rc == 0 else ("FAIL" if rc == 1 else "ERROR")


def run_scanner(scanner_id: str, root: Path, home: Path, target: Path, source_root: Path | None = None, requirements: Path | None = None) -> dict[str, Any]:
    inventory = collect_tool_inventory(root, home)[scanner_id]
    if not inventory["present"]:
        return {**inventory, "status": "ERROR", "execution": {"error": "tool missing", "network_egress": False}}
    try:
        execution = run_isolated(home, _scanner_command(scanner_id, home, target, source_root, requirements))
        return {**inventory, "status": _scan_status(scanner_id, execution), "execution": execution}
    except Exception as exc:
        return {**inventory, "status": "ERROR", "execution": {"error": repr(exc), "network_egress": False}}


def _format_for(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".safetensors": return "safetensors"
    if ext == ".gguf": return "gguf"
    if ext in DANGEROUS_EXTENSIONS: return "pickle_or_framework_serialization"
    return "unknown"


def _copy_to_quarantine(source: Path, home: Path, digest: str) -> Path:
    if source.is_symlink() or not source.is_file(): raise RuntimeError("source must be a regular non-symlink file")
    qdir = home / "quarantine" / digest
    qdir.mkdir(parents=True, exist_ok=True)
    dest = qdir / source.name
    if dest.exists():
        if sha256_file(dest) != digest: raise RuntimeError("quarantine collision")
        return dest
    with source.open("rb") as src, dest.open("xb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024); dst.flush(); os.fsync(dst.fileno())
    os.chmod(dest, 0o444)
    if sha256_file(dest) != digest: dest.unlink(missing_ok=True); raise RuntimeError("quarantine copy digest mismatch")
    return dest


def _first_load_script(target: Path) -> str:
    fmt = _format_for(target)
    if fmt == "safetensors":
        return "import json,struct,sys;p=sys.argv[1];f=open(p,'rb');n=struct.unpack('<Q',f.read(8))[0];assert 1<=n<=16*1024*1024;h=json.loads(f.read(n));size=f.seek(0,2);base=8+n;assert isinstance(h,dict) and h;[(lambda o: (_ for _ in ()).throw(AssertionError()) if not (isinstance(o,list) and len(o)==2 and 0<=o[0]<=o[1]<=size-base) else None)(v['data_offsets']) for k,v in h.items() if k!='__metadata__'];print('SAFETENSORS_HEADER_AND_OFFSETS_OK')"
    if fmt == "gguf":
        return "import sys;f=open(sys.argv[1],'rb');assert f.read(4)==b'GGUF';print('GGUF_MAGIC_OK')"
    raise RuntimeError(f"no isolated first-load adapter for format {fmt}")


def isolated_first_load(home: Path, target: Path) -> dict[str, Any]:
    try:
        execution = run_isolated(home, [sys.executable, "-c", _first_load_script(target), str(target)], timeout=120)
        ok = execution["returncode"] == 0
        return {"status": "PASS" if ok else "FAIL", "unprivileged": os.geteuid() != 0, "network_egress": False, "secret_access": False, "host_socket_access": False, "read_only_model_input": True, "adapter": _format_for(target), "execution": execution}
    except Exception as exc:
        return {"status": "FAIL", "unprivileged": os.geteuid() != 0, "network_egress": False, "secret_access": False, "host_socket_access": False, "read_only_model_input": True, "error": repr(exc)}


def _source_surface(source_root: Path | None) -> tuple[bool, bool, Path | None]:
    if source_root is None: return False, False, None
    python_code = any(source_root.rglob("*.py"))
    requirements = next((p for p in [source_root / "requirements.txt", source_root / "requirements-dev.txt"] if p.is_file()), None)
    return python_code, requirements is not None, requirements


def admit(root: Path, source: Path, immutable_revision: str, model_class: str = "MODEL_ARTIFACT", source_root: Path | None = None, upstream_signature_or_attestation_present: bool = False) -> dict[str, Any]:
    root, source, home = root.resolve(), source.expanduser().resolve(), runtime_home()
    if os.geteuid() == 0: raise RuntimeError("FA3 model-security admission must not run as root")
    if str(home).startswith(str(Path.home().resolve()) + os.sep): raise RuntimeError("production runtime root must be outside HOME so HOME can be masked in sandbox")
    if source_root is not None:
        staged_root = source_root.expanduser().resolve()
        try:
            staged_root.relative_to(home)
        except ValueError as exc:
            raise RuntimeError("source_root must be staged inside FA3_MODEL_SECURITY_HOME before repository scanning") from exc
        source_root = staged_root
    digest = sha256_file(source)
    target = _copy_to_quarantine(source, home, digest)
    fmt = _format_for(target)
    if fmt == "unknown": raise RuntimeError("unknown artifact format is fail-closed")
    dangerous = target.suffix.lower() in DANGEROUS_EXTENSIONS
    python_code, has_requirements, requirements = _source_surface(source_root.resolve() if source_root else None)
    required = set(ALWAYS)
    if source_root is not None: required.add("trivy")
    if python_code: required.add("bandit")
    if has_requirements: required.add("pip-audit")
    if dangerous: required.update({"modelscan", "picklescan", "fickling"})
    if model_class in GENERATIVE_CLASSES: required.add("garak")
    if upstream_signature_or_attestation_present: required.add("cosign")

    inventory = collect_tool_inventory(root, home)
    scanner_rows, blocking = [], []
    for scanner_id in SCANNER_IDS:
        base = inventory[scanner_id]
        if scanner_id not in required:
            scanner_rows.append({**base, "target_sha256": digest, "applicability": "NOT_APPLICABLE", "status": "NOT_APPLICABLE", "policy_reason": "FA3-POLICY:SCANNER_NOT_APPLICABLE_TO_DISCOVERED_SURFACE", "network_egress": False})
            continue
        if scanner_id in {"garak", "cosign"}:
            row = {**base, "target_sha256": digest, "applicability": "APPLICABLE", "status": "ERROR", "policy_reason": None, "network_egress": False, "execution": {"error": f"{scanner_id} requires explicit offline/local verification profile; implicit remote access is forbidden"}}
        else:
            raw = run_scanner(scanner_id, root, home, target, source_root, requirements)
            row = {**{k: raw.get(k) for k in ("scanner_id", "version", "binary_or_package_digest", "ruleset_id", "ruleset_digest")}, "target_sha256": digest, "applicability": "APPLICABLE", "status": raw.get("status"), "policy_reason": None, "network_egress": False, "execution": raw.get("execution", {})}
        scanner_rows.append(row)
        if row["status"] != "PASS": blocking.append(scanner_id)

    first_load = isolated_first_load(home, target) if not blocking else {"status": "FAIL", "unprivileged": os.geteuid() != 0, "network_egress": False, "secret_access": False, "host_socket_access": False, "read_only_model_input": True, "error": "static security gate blocked isolated first load"}
    if first_load["status"] != "PASS": blocking.append("isolated-first-load")
    generative = model_class in GENERATIVE_CLASSES
    behavior = {"applicability": "APPLICABLE", "status": "FAIL", "scanner_id": "garak", "policy_reason": None} if generative else {"applicability": "NOT_APPLICABLE", "status": "NOT_APPLICABLE", "scanner_id": None, "policy_reason": "FA3-POLICY:BEHAVIOR_SCANNER_NOT_APPLICABLE_TO_MODEL_CLASS"}
    admitted = not blocking and not generative
    return {
        "schema": "fa3.model-artifact-security-receipt.v1", "runtime_id": "FA3-MODEL-ARTIFACT-SECURITY-RUNTIME-CONFORMANCE-001",
        "source": {"origin": str(source), "immutable_revision": immutable_revision, "upstream_signature_or_attestation_present": upstream_signature_or_attestation_present},
        "artifact": {"sha256": digest, "extension": target.suffix.lower(), "format": fmt, "format_classified": True, "dangerous_serialization": dangerous, "trusted_because_safe_format": False, "quarantine_path": str(target)},
        "quarantine": {"state": "QUARANTINED_UNTRUSTED", "promoted_store_visible": False},
        "surface": {"repository_surface": source_root is not None, "python_code": python_code, "python_dependency_manifest": has_requirements},
        "model": {"class": model_class}, "remote_code": {"enabled": False},
        "scan_execution": {"network_egress": False, "telemetry": False, "sandbox": "bubblewrap"}, "scanners": scanner_rows,
        "isolated_first_load": first_load, "behavior_security": behavior,
        "findings": {"unresolved_critical": 0 if admitted else len(blocking), "blocking_stages": sorted(set(blocking))},
        "security_attestation": {"status": "PASS" if admitted else "FAIL", "scanner_output_is_authority": False, "security_policy_authority": "FA3-AUTH-SECURITY-GOV-001", "evidence_authority": "FA3-AUTH-OBS-EVIDENCE-001", "evidence_ids": [f"FA3-MODEL-SECURITY:{digest}"]},
        "promotion": {"security_state": "SECURITY_ADMITTED" if admitted else "SECURITY_BLOCKED", "model_manager_promotion_eligible": admitted, "policy_decision_id": "FA3-DEC-MODEL-ARTIFACT-SECURITY-2026-09-07", "security_attestation_id": f"FA3-MODEL-SECURITY:{digest}", "direct_runtime_store_download_bypass": False},
    }


def write_receipt(receipt: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1])); ap.add_argument("--artifact", required=True); ap.add_argument("--immutable-revision", required=True)
    ap.add_argument("--model-class", default="MODEL_ARTIFACT"); ap.add_argument("--source-root"); ap.add_argument("--upstream-attestation-present", action="store_true"); ap.add_argument("--receipt")
    args = ap.parse_args(); root = Path(args.root).resolve()
    receipt = admit(root, Path(args.artifact), args.immutable_revision, args.model_class, Path(args.source_root).resolve() if args.source_root else None, args.upstream_attestation_present)
    out = Path(args.receipt) if args.receipt else runtime_home() / "receipts" / f"{receipt['artifact']['sha256']}.json"
    write_receipt(receipt, out)
    print(json.dumps({"receipt": str(out), "security_state": receipt["promotion"]["security_state"], "sha256": receipt["artifact"]["sha256"]}, indent=2))
    return 0 if receipt["promotion"]["security_state"] == "SECURITY_ADMITTED" else 2


if __name__ == "__main__": raise SystemExit(main())
