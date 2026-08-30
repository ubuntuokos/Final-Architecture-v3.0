#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import socket
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-PRESENTON-001"
OCI_INDEX_DIGEST = "sha256:e6866086f2dbdf9f6c50c8f217123cada2a84f4dd03131ad78f397d6fb11b3d1"
EXPECTED_IMAGE = f"ghcr.io/presenton/presenton@{OCI_INDEX_DIGEST}"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(*args: str) -> str:
    proc = subprocess.run(args, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def request_json(method: str, url: str, token: str | None, payload: dict[str, Any] | None = None,
                 timeout: int = 30) -> tuple[int, dict[str, Any]]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read(2 * 1024 * 1024)
            return response.status, json.loads(body.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read(2 * 1024 * 1024)
        try:
            parsed = json.loads(body.decode("utf-8"))
        except Exception:
            parsed = {"detail": body.decode("utf-8", errors="replace")[:1000]}
        return exc.code, parsed


def safe_artifact_url(base_url: str, path: str) -> str:
    base = urllib.parse.urlparse(base_url)
    candidate = urllib.parse.urlparse(urllib.parse.urljoin(base_url.rstrip("/") + "/", path))
    if candidate.scheme not in {"http", "https"} or candidate.netloc != base.netloc:
        raise RuntimeError("Presenton returned a cross-origin artifact URL")
    return urllib.parse.urlunparse(candidate)


def download(url: str, token: str, destination: Path, limit: int = 512 * 1024 * 1024) -> None:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=120) as response, destination.open("wb") as output:
        total = 0
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            total += len(block)
            if total > limit:
                raise RuntimeError("Presenton artifact exceeds evidence collector limit")
            output.write(block)


def inspect_runtime() -> dict[str, bool]:
    if os.geteuid() == 0:
        raise RuntimeError("Current-host production evidence must run as the rootless service user")
    if run("systemctl", "--user", "is-active", "presenton.service") != "active":
        raise RuntimeError("presenton.service is not active")
    inspect = json.loads(run("podman", "inspect", "fa3-presenton"))[0]
    env = {}
    for entry in inspect.get("Config", {}).get("Env", []):
        key, _, value = entry.partition("=")
        env[key] = value
    image_candidates = {
        str(inspect.get("ImageName", "")),
        str(inspect.get("Config", {}).get("Image", "")),
    }
    serialized = json.dumps(inspect)
    ports = inspect.get("NetworkSettings", {}).get("Ports", {})
    port_bindings = []
    for bindings in ports.values():
        if isinstance(bindings, list):
            port_bindings.extend(bindings)
    loopback = bool(port_bindings) and all(item.get("HostIp") in {"127.0.0.1", "::1"} for item in port_bindings)
    no_gpu = not any(token in serialized for token in ("/dev/nvidia", "NVIDIA_VISIBLE_DEVICES", "--gpus"))
    return {
        "rootless_quadlet_active": True,
        "pinned_oci_digest": EXPECTED_IMAGE in image_candidates,
        "loopback_only_bind": loopback,
        "no_gpu_devices": no_gpu,
        "postgresql_backend": env.get("DATABASE_URL", "").startswith("postgresql://"),
        "litellm_route": env.get("LLM") == "litellm" and env.get("LITELLM_BASE_URL", "").startswith("http://host.containers.internal:4000/"),
        "comfyui_route": env.get("IMAGE_PROVIDER") == "comfyui" and env.get("COMFYUI_URL", "").startswith("http://host.containers.internal:9876"),
        "telemetry_disabled": env.get("DISABLE_ANONYMOUS_TRACKING", "").lower() == "true",
        "web_grounding_disabled": env.get("WEB_GROUNDING", "").lower() == "false",
        "parallel_images_disabled": env.get("ENABLE_PARALLEL_IMAGE_GENERATION", "").lower() == "false",
        "secrets_externalized": all(env.get(key) for key in ("DATABASE_URL", "AUTH_PASSWORD", "LITELLM_API_KEY", "COMFYUI_WORKFLOW")),
    }


def validate_pptx(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as package:
            names = set(package.namelist())
        return "[Content_Types].xml" in names and "ppt/presentation.xml" in names
    except zipfile.BadZipFile:
        return False


def pdf_page_count(path: Path) -> int:
    output = run("pdfinfo", str(path))
    match = re.search(r"^Pages:\s+(\d+)\s*$", output, re.MULTILINE)
    if not match:
        raise RuntimeError("pdfinfo did not report a page count")
    return int(match.group(1))


def render_pdf(path: Path, directory: Path) -> int:
    prefix = directory / "slide"
    run("pdftoppm", "-png", "-r", "110", str(path), str(prefix))
    pages = sorted(directory.glob("slide-*.png"))
    for page in pages:
        data = page.read_bytes()[:24]
        if len(data) != 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError(f"invalid rendered PNG: {page}")
        width, height = struct.unpack(">II", data[16:24])
        if width < 640 or height < 360:
            raise RuntimeError(f"rendered page is unexpectedly small: {page}")
    return len(pages)


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect real FA3 Presenton current-host production evidence")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--base-url", default="http://127.0.0.1:5001")
    ap.add_argument("--access-key-env", default="PRESENTON_ACCESS_KEY")
    ap.add_argument("--access-key-file")
    ap.add_argument("--timeout-seconds", type=int, default=1800)
    ap.add_argument("--slides", type=int, default=3)
    ap.add_argument("--language", default="Hungarian")
    ap.add_argument("--content", default="A Final Architecture v3.0 Presenton current-host conformance rövid bemutatása")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    if args.access_key_file:
        token = Path(args.access_key_file).read_text(encoding="utf-8").strip()
    else:
        token = os.environ.get(args.access_key_env, "").strip()
    if not token.startswith("sk-presenton-"):
        raise RuntimeError("A valid Presenton access key was not supplied")
    if not 1 <= args.slides <= 40 or not 1 <= args.timeout_seconds <= 3600:
        raise RuntimeError("slides or timeout is outside the canonical bounded range")

    started = now()
    run_id = f"presenton-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    output_dir = root / "evidence/runtime/presenton-current-host" / run_id
    render_dir = output_dir / "rendered-pdf"
    render_dir.mkdir(parents=True, exist_ok=False)
    deployment = inspect_runtime()
    if not all(deployment.values()):
        failed = sorted(key for key, value in deployment.items() if not value)
        raise RuntimeError(f"runtime deployment checks failed: {failed}")

    api = args.base_url.rstrip("/") + "/api/v1/ppt/presentation"
    payload = {
        "content": args.content,
        "tone": "default",
        "verbosity": "standard",
        "web_search": False,
        "n_slides": args.slides,
        "language": args.language,
        "template": "general",
        "include_table_of_contents": False,
        "include_title_slide": True,
        "files": None,
        "export_as": "pptx",
        "trigger_webhook": False,
    }
    unauth_status, _ = request_json("POST", api + "/generate/async", None, payload, timeout=20)
    unauth_denied = unauth_status in {401, 403}
    if not unauth_denied:
        raise RuntimeError(f"unauthenticated generation was not denied: HTTP {unauth_status}")

    status, task = request_json("POST", api + "/generate/async", token, payload, timeout=60)
    if status not in {200, 201, 202} or not task.get("id"):
        raise RuntimeError(f"async generation admission failed: HTTP {status}: {task}")
    task_id = task["id"]
    deadline = time.monotonic() + args.timeout_seconds
    while time.monotonic() < deadline:
        status, task = request_json("GET", api + f"/status/{urllib.parse.quote(task_id, safe='')}", token, timeout=30)
        if status != 200:
            raise RuntimeError(f"task polling failed: HTTP {status}: {task}")
        if task.get("status") in {"completed", "error"}:
            break
        time.sleep(5)
    else:
        raise RuntimeError("Presenton generation exceeded the canonical timeout")
    if task.get("status") != "completed":
        raise RuntimeError(f"Presenton generation failed: {task}")
    data = task.get("data") or {}
    presentation_id = data.get("presentation_id")
    pptx_remote = data.get("path")
    if not presentation_id or not pptx_remote:
        raise RuntimeError("completed task did not expose presentation_id and path")

    pptx_path = output_dir / "presenton-current-host.pptx"
    download(safe_artifact_url(args.base_url, pptx_remote), token, pptx_path)
    if not validate_pptx(pptx_path):
        raise RuntimeError("generated PPTX package failed integrity validation")

    status, exported = request_json(
        "POST", api + f"/{urllib.parse.quote(presentation_id, safe='')}/export", token,
        {"export_as": "pdf"}, timeout=600,
    )
    if status != 200 or not exported.get("path"):
        raise RuntimeError(f"PDF export failed: HTTP {status}: {exported}")
    pdf_path = output_dir / "presenton-current-host.pdf"
    download(safe_artifact_url(args.base_url, exported["path"]), token, pdf_path)
    if not pdf_path.read_bytes()[:5] == b"%PDF-":
        raise RuntimeError("generated PDF header failed integrity validation")
    pages = pdf_page_count(pdf_path)
    rendered = render_pdf(pdf_path, render_dir)
    if pages != rendered or pages < 1:
        raise RuntimeError("PDF page count and rendered page count do not match")

    receipt = {
        "schema": "fa3.presenton-current-host-receipt.v1",
        "provider_id": PROVIDER_ID,
        "status": "PASS",
        "evidence_level": "CURRENT_HOST_PRODUCTION_E2E_PASS",
        "collector_mode": "REAL_CURRENT_HOST_SERVICE",
        "synthetic": False,
        "run_id": run_id,
        "started_at": started,
        "completed_at": now(),
        "host": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "effective_uid": os.geteuid(),
        },
        "upstream": {
            "release": "v0.9.8-beta",
            "oci_index_digest": OCI_INDEX_DIGEST,
        },
        "deployment": deployment,
        "authentication": {
            "unauthenticated_request_denied": unauth_denied,
            "authenticated_request_admitted": True,
            "access_key_redacted": True,
        },
        "generation": {
            "workflow": "presentation.generate.v1",
            "task_id": task_id,
            "async_status": task["status"],
            "presentation_id": presentation_id,
            "requested_slides": args.slides,
            "web_search": False,
            "trigger_webhook": False,
        },
        "artifacts": {
            "pptx": {
                "path": str(pptx_path.resolve()),
                "sha256": sha256(pptx_path),
                "size_bytes": pptx_path.stat().st_size,
                "integrity": "PASS",
            },
            "pdf": {
                "path": str(pdf_path.resolve()),
                "sha256": sha256(pdf_path),
                "size_bytes": pdf_path.stat().st_size,
                "integrity": "PASS",
                "page_count": pages,
                "rendered_page_count": rendered,
                "render_qa": "PASS",
            },
        },
        "artifact_lineage": {
            "source_request": "INLINE_CANONICAL_TEST_CONTENT",
            "task_to_presentation": True,
            "presentation_to_pptx": True,
            "same_presentation_reexported_to_pdf": True,
        },
    }
    receipt_path = root / "evidence/receipts/presenton-current-host.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"PRESENTON CURRENT-HOST EVIDENCE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(2)
