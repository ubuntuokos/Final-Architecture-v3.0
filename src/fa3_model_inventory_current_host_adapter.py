#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from fa3_model_manager_provider_adapter import find_binary, safe_child_env, sha256_bytes, sha256_file, valid_revision

STABILITY_MATRIX_PROVIDER_ID = "FA3-PROVIDER-STABILITY-MATRIX-MODEL-STORE-001"
HF_PROVIDER_ID = "FA3-PROVIDER-HF-MODEL-STORE-001"
LM_STUDIO_PROVIDER_ID = "FA3-PROVIDER-LM-STUDIO-MODEL-001"
OLLAMA_PROVIDER_ID = "FA3-PROVIDER-OLLAMA-MODEL-001"
PROVIDER_IDS = [STABILITY_MATRIX_PROVIDER_ID, HF_PROVIDER_ID, LM_STUDIO_PROVIDER_ID, OLLAMA_PROVIDER_ID]
CONFORMANCE_ID = "FA3-MODEL-INVENTORY-CURRENT-HOST-CONFORMANCE-001"
GATE_ID = "FA3-GATE-MODEL-INVENTORY-CURRENT-HOST-001"
EVIDENCE_LEVEL = "CURRENT_HOST_READ_ONLY_CROSS_PROVIDER_MODEL_INVENTORY_PASS"

MODEL_SUFFIXES = {
    ".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf", ".onnx",
    ".engine", ".plan", ".tflite", ".pb", ".model", ".npz", ".vae",
}
MAX_REPRESENTATIVE_HASH_BYTES = 512 * 1024 * 1024
MAX_RUNTIME_INVENTORY_ENTRIES = 20000


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(payload)


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_key_ci(value: Any, wanted: str) -> Any:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() == wanted.lower():
                return item
        for item in value.values():
            hit = _find_key_ci(item, wanted)
            if hit is not None:
                return hit
    elif isinstance(value, list):
        for item in value:
            hit = _find_key_ci(item, wanted)
            if hit is not None:
                return hit
    return None


def stability_matrix_library_candidates() -> list[Path]:
    out: list[Path] = []
    for key in ("STABILITY_MATRIX_LIBRARY_DIR", "STABILITY_MATRIX_HOME", "STABILITY_MATRIX_DATA_DIR"):
        if os.environ.get(key):
            out.append(Path(os.environ[key]))
    out.extend([
        Path("/AI-modells/StabilityMatrix"),
        Path("/AI-models/StabilityMatrix"),
        Path.home() / "StabilityMatrix",
        Path.home() / ".local/share/StabilityMatrix",
    ])
    expanded: list[Path] = []
    for base in out:
        expanded.extend([base, base / "Data", base / "Library"])
    unique: list[Path] = []
    seen: set[str] = set()
    for path in expanded:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            continue
        if str(resolved) in seen:
            continue
        seen.add(str(resolved))
        unique.append(resolved)
    return unique


def detect_stability_matrix_library() -> tuple[Path, Path, dict[str, Any]]:
    direct_models = os.environ.get("STABILITY_MATRIX_MODELS_DIR")
    if direct_models:
        models = Path(direct_models).expanduser().resolve()
        if models.is_dir():
            return models.parent, models, {"source": "STABILITY_MATRIX_MODELS_DIR", "settings_present": False, "override_used": True}

    for library in stability_matrix_library_candidates():
        settings_path = library / "settings.json"
        settings: Any = None
        if settings_path.is_file():
            try:
                settings = _json(settings_path)
            except Exception:
                settings = None
        override = _find_key_ci(settings, "ModelDirectoryOverride") if settings is not None else None
        if isinstance(override, str) and override.strip():
            try:
                candidate = Path(override).expanduser()
                if not candidate.is_absolute():
                    candidate = library / candidate
                candidate = candidate.resolve()
            except OSError:
                candidate = Path("/__fa3_invalid_stability_matrix_override__")
            if candidate.is_dir():
                return library, candidate, {
                    "source": "settings.json:ModelDirectoryOverride",
                    "settings_present": True,
                    "override_used": True,
                }
        models = library / "Models"
        if models.is_dir():
            return library, models.resolve(), {
                "source": "LibraryDir/Models",
                "settings_present": settings_path.is_file(),
                "override_used": False,
            }
    raise RuntimeError("StabilityMatrix library/Models directory not found in approved current-host candidates")


def _model_file(path: Path) -> bool:
    name = path.name.lower()
    if name.endswith(".pth.tar"):
        return True
    return path.suffix.lower() in MODEL_SUFFIXES


def scan_model_tree(models_root: Path) -> dict[str, Any]:
    root = models_root.resolve()
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    total_bytes = 0
    symlink_files = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in {".git", ".downloads", "__pycache__"})
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if not _model_file(path):
                continue
            try:
                lst = path.lstat()
                is_link = path.is_symlink()
                target = path.resolve(strict=True) if is_link else path
                st = target.stat()
                if not target.is_file():
                    continue
                rel = path.relative_to(root).as_posix()
                row = {
                    "relative_path": rel,
                    "suffix": ".pth.tar" if name.lower().endswith(".pth.tar") else path.suffix.lower(),
                    "size_bytes": int(st.st_size),
                    "is_symlink": bool(is_link),
                }
                rows.append(row)
                total_bytes += int(st.st_size)
                symlink_files += int(is_link)
                if len(rows) > MAX_RUNTIME_INVENTORY_ENTRIES:
                    raise RuntimeError(f"StabilityMatrix inventory exceeds safe entry ceiling {MAX_RUNTIME_INVENTORY_ENTRIES}")
            except Exception as exc:
                errors.append(f"{path.name}:{type(exc).__name__}")
                if len(errors) >= 20:
                    raise RuntimeError("too many StabilityMatrix model scan errors: " + ",".join(errors))
    rows.sort(key=lambda x: (x["relative_path"], x["size_bytes"]))
    if not rows:
        raise RuntimeError("StabilityMatrix Models directory contains no recognized local model artifacts")
    representative_candidates = [r for r in rows if 0 < int(r["size_bytes"]) <= MAX_REPRESENTATIVE_HASH_BYTES]
    representative_row = min(representative_candidates or rows, key=lambda r: (int(r["size_bytes"]), r["relative_path"]))
    representative_path = root / representative_row["relative_path"]
    representative_sha = sha256_file(representative_path.resolve())
    manifest_basis = [{"relative_path": r["relative_path"], "suffix": r["suffix"], "size_bytes": r["size_bytes"], "is_symlink": r["is_symlink"]} for r in rows]
    return {
        "entry_count": len(rows),
        "total_bytes": total_bytes,
        "symlink_file_count": symlink_files,
        "scan_error_count": len(errors),
        "inventory_manifest_sha256": canonical_json_sha256(manifest_basis),
        "representative": {
            "relative_path": representative_row["relative_path"],
            "size_bytes": representative_row["size_bytes"],
            "sha256": representative_sha,
        },
        "entries": rows,
    }


def collect_stability_matrix_inventory() -> dict[str, Any]:
    library, models, detection = detect_stability_matrix_library()
    scan = scan_model_tree(models)
    return {
        "provider_id": STABILITY_MATRIX_PROVIDER_ID,
        "status": "PASS",
        "evidence_level": "CURRENT_HOST_READ_ONLY_MODEL_STORE_SCAN_PASS",
        "library_root_fingerprint": sha256_bytes(str(library).encode("utf-8")),
        "models_root_fingerprint": sha256_bytes(str(models).encode("utf-8")),
        "path_disclosure": "ABSOLUTE_PATHS_NOT_EMITTED",
        "detection": detection,
        "entry_count": scan["entry_count"],
        "total_bytes": scan["total_bytes"],
        "symlink_file_count": scan["symlink_file_count"],
        "scan_error_count": scan["scan_error_count"],
        "inventory_manifest_sha256": scan["inventory_manifest_sha256"],
        "representative": scan["representative"],
        "inventory_entries": scan["entries"],
        "network_access_performed": False,
        "model_store_mutation_performed": False,
    }


def hf_cache_candidates() -> list[Path]:
    out: list[Path] = []
    if os.environ.get("HF_HUB_CACHE"):
        out.append(Path(os.environ["HF_HUB_CACHE"]))
    if os.environ.get("HF_HOME"):
        out.append(Path(os.environ["HF_HOME"]) / "hub")
    out.extend([
        Path("/ai-cache/huggingface/hub"), Path("/ai-cache/huggingface"),
        Path("/ai-cache/hf/hub"), Path("/ai-cache/hf"), Path("/ai-cache/hub"),
        Path.home() / ".cache/huggingface/hub",
    ])
    unique: list[Path] = []
    seen: set[str] = set()
    for path in out:
        try:
            p = path.expanduser().resolve()
        except OSError:
            continue
        if p.name != "hub" and (p / "hub").is_dir():
            p = (p / "hub").resolve()
        if str(p) not in seen:
            seen.add(str(p)); unique.append(p)
    return unique


def collect_hf_inventory() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    roots: list[str] = []
    for root in hf_cache_candidates():
        if not root.is_dir():
            continue
        roots.append(sha256_bytes(str(root).encode("utf-8")))
        for model_dir in sorted(root.glob("models--*")):
            snap_root = model_dir / "snapshots"
            if not snap_root.is_dir():
                continue
            encoded = model_dir.name[len("models--"):]
            repo_id = encoded.replace("--", "/", 1)
            for snap in sorted(snap_root.iterdir(), key=lambda p: p.name):
                if snap.is_dir() and valid_revision(snap.name):
                    entries.append({"repo_id": repo_id, "immutable_revision": snap.name})
                    if len(entries) >= MAX_RUNTIME_INVENTORY_ENTRIES:
                        raise RuntimeError("Hugging Face inventory exceeds safe entry ceiling")
    entries.sort(key=lambda x: (x["repo_id"], x["immutable_revision"]))
    return {
        "provider_id": HF_PROVIDER_ID,
        "status": "PASS" if entries else "EMPTY_OR_UNAVAILABLE",
        "evidence_level": "CURRENT_HOST_READ_ONLY_SOURCE_CACHE_DISCOVERY",
        "cache_root_fingerprints": roots,
        "entry_count": len(entries),
        "inventory_manifest_sha256": canonical_json_sha256(entries),
        "inventory_entries": entries,
        "network_access_performed": False,
        "mutation_performed": False,
    }


def collect_lmstudio_inventory() -> dict[str, Any]:
    lms = find_binary("lms")
    if lms is None:
        return {"provider_id": LM_STUDIO_PROVIDER_ID, "status": "UNAVAILABLE", "entry_count": 0, "inventory_entries": [], "network_access_performed": False, "mutation_performed": False}
    env = safe_child_env()
    proc = subprocess.run([str(lms), "ls", "--json"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180, check=False, env=env)
    if proc.returncode != 0:
        return {"provider_id": LM_STUDIO_PROVIDER_ID, "status": "UNAVAILABLE", "entry_count": 0, "inventory_entries": [], "cli_binary_sha256": sha256_file(lms), "network_access_performed": False, "mutation_performed": False}
    try:
        rows = json.loads(proc.stdout)
    except Exception as exc:
        raise RuntimeError("LM Studio read-only inventory returned invalid JSON") from exc
    entries: list[dict[str, Any]] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = row.get("modelKey")
            if not isinstance(key, str) or not key:
                continue
            try:
                size = int(row.get("sizeBytes") or 0)
            except Exception:
                size = 0
            entries.append({"model_key": key, "type": row.get("type"), "size_bytes": size})
    entries.sort(key=lambda x: (str(x.get("type")), x["model_key"]))
    return {
        "provider_id": LM_STUDIO_PROVIDER_ID,
        "status": "PASS" if entries else "EMPTY",
        "evidence_level": "CURRENT_HOST_READ_ONLY_PROVIDER_CATALOG_DISCOVERY",
        "cli_binary_sha256": sha256_file(lms),
        "entry_count": len(entries),
        "inventory_manifest_sha256": canonical_json_sha256(entries),
        "inventory_entries": entries,
        "network_access_performed": False,
        "mutation_performed": False,
    }


def ollama_manifest_roots() -> list[Path]:
    out: list[Path] = []
    if os.environ.get("OLLAMA_MODELS"):
        out.append(Path(os.environ["OLLAMA_MODELS"]))
    out.extend([Path.home() / ".ollama/models", Path("/AI-modells/Ollama/models"), Path("/AI-modells/ollama/models")])
    unique: list[Path] = []
    seen: set[str] = set()
    for path in out:
        try:
            p = path.expanduser().resolve()
        except OSError:
            continue
        if str(p) not in seen:
            seen.add(str(p)); unique.append(p)
    return unique


def collect_ollama_inventory() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    roots: list[str] = []
    for root in ollama_manifest_roots():
        manifests = root / "manifests"
        if not manifests.is_dir():
            continue
        roots.append(sha256_bytes(str(root).encode("utf-8")))
        for path in sorted(manifests.rglob("*"), key=lambda p: p.as_posix()):
            if not path.is_file():
                continue
            try:
                data = path.read_bytes()
                obj = json.loads(data.decode("utf-8"))
            except Exception:
                continue
            rel = path.relative_to(manifests).as_posix()
            digests: list[str] = []
            if isinstance(obj, dict):
                cfg = obj.get("config")
                if isinstance(cfg, dict) and isinstance(cfg.get("digest"), str):
                    digests.append(cfg["digest"])
                layers = obj.get("layers")
                if isinstance(layers, list):
                    for layer in layers:
                        if isinstance(layer, dict) and isinstance(layer.get("digest"), str):
                            digests.append(layer["digest"])
            digests = sorted(d for d in set(digests) if re.fullmatch(r"sha256:[0-9a-f]{64}", d))
            entries.append({"manifest_id": rel, "manifest_sha256": sha256_bytes(data), "content_digests": digests})
            if len(entries) >= MAX_RUNTIME_INVENTORY_ENTRIES:
                raise RuntimeError("Ollama inventory exceeds safe entry ceiling")
    entries.sort(key=lambda x: x["manifest_id"])
    return {
        "provider_id": OLLAMA_PROVIDER_ID,
        "status": "PASS" if entries else "EMPTY_OR_UNAVAILABLE",
        "evidence_level": "CURRENT_HOST_READ_ONLY_NATIVE_MANIFEST_DISCOVERY",
        "models_root_fingerprints": roots,
        "entry_count": len(entries),
        "inventory_manifest_sha256": canonical_json_sha256(entries),
        "inventory_entries": entries,
        "network_access_performed": False,
        "mutation_performed": False,
    }


def collect_cross_provider_inventory() -> dict[str, Any]:
    stability = collect_stability_matrix_inventory()
    hf = collect_hf_inventory()
    lm = collect_lmstudio_inventory()
    ollama = collect_ollama_inventory()
    providers = {x["provider_id"]: x for x in (stability, hf, lm, ollama)}
    available = [pid for pid, item in providers.items() if item.get("status") == "PASS" and int(item.get("entry_count", 0)) > 0]
    total_entries = sum(int(item.get("entry_count", 0)) for item in providers.values())
    snapshot_basis = {
        pid: {
            "status": item.get("status"),
            "entry_count": item.get("entry_count", 0),
            "inventory_manifest_sha256": item.get("inventory_manifest_sha256"),
        }
        for pid, item in sorted(providers.items())
    }
    return {
        "schema": "fa3.cross-provider-model-inventory.v1",
        "providers": providers,
        "provider_ids": PROVIDER_IDS,
        "available_provider_ids": available,
        "available_provider_count": len(available),
        "total_entries": total_entries,
        "inventory_snapshot_sha256": canonical_json_sha256(snapshot_basis),
        "read_only": True,
        "network_access_performed": False,
        "physical_dedup_mutation_performed": False,
        "canonical_admission_performed": False,
    }


def regression_check() -> dict[str, Any]:
    cases: dict[str, bool] = {}
    cases["suffix_accept"] = _model_file(Path("x.safetensors")) and _model_file(Path("x.gguf"))
    cases["suffix_reject"] = not _model_file(Path("preview.png")) and not _model_file(Path("notes.txt"))
    cases["canonical_inventory_order_stable"] = canonical_json_sha256([{"b": 2, "a": 1}]) == canonical_json_sha256([{"a": 1, "b": 2}])
    cases["provider_set_exact"] = PROVIDER_IDS == [STABILITY_MATRIX_PROVIDER_ID, HF_PROVIDER_ID, LM_STUDIO_PROVIDER_ID, OLLAMA_PROVIDER_ID]
    cases["immutable_revision_guard"] = valid_revision("a" * 40) and not valid_revision("latest")
    cases["evidence_level_read_only"] = "READ_ONLY" in EVIDENCE_LEVEL
    return {"schema": "fa3.model-inventory-current-host-adapter-regression.v1", "result": "PASS" if all(cases.values()) else "FAIL", "passed": sum(cases.values()), "total": len(cases), "cases": cases}


if __name__ == "__main__":
    print(json.dumps(regression_check(), indent=2))
