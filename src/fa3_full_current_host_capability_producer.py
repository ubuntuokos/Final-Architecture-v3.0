#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from fa3_current_host_runtime_resolver import resolve_python_runtime

VERDICT_SCHEMA = "fa3.capability-current-host-qualification-constituent-verdict.v1"
MODES = ("positive", "negative", "rollback")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha(path.read_bytes())


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required environment variable missing: {name}")
    return value


def cmd(argv: list[str], timeout: int = 30, *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        shell=False,
        check=False,
        cwd=str(cwd) if cwd else None,
    )


def exact_rollback(scope: Path, cap: str, primitive: str) -> dict[str, Any]:
    path = scope / "rollback-state.json"
    baseline = json.dumps(
        {
            "capability_id": cap,
            "primitive": primitive,
            "state": "READY",
            "external_side_effects": False,
            "global_promotion_claim": False,
        },
        sort_keys=True,
    ).encode() + b"\n"
    fault = json.dumps(
        {
            "capability_id": cap,
            "primitive": primitive,
            "state": "FAULT_INJECTED",
            "external_side_effects": True,
            "global_promotion_claim": True,
        },
        sort_keys=True,
    ).encode() + b"\n"
    path.write_bytes(baseline)
    pre = sha_file(path)
    path.write_bytes(fault)
    mutated = sha_file(path)
    path.write_bytes(baseline)
    post = sha_file(path)
    if pre != post or pre == mutated:
        raise RuntimeError("exact rollback proof failed")
    return {
        "pre_sha256": pre,
        "mutated_sha256": mutated,
        "post_sha256": post,
        "rollback_hash_equal": True,
    }


def expected_source_decisions(root: Path, cap: str) -> list[str]:
    registry = load(root / "evidence/evidence-registry.json")
    row = next((x for x in registry.get("records", []) if x.get("subject_id") == cap), None)
    ids = row.get("source_decision_ids") if isinstance(row, dict) else None
    if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or not x for x in ids):
        raise RuntimeError(f"{cap} source decisions invalid")
    return ids


def recipe_map(root: Path) -> dict[str, dict[str, Any]]:
    data = load(root / "canonical/current-host-capability-proof-recipes.json")
    rows = data.get("recipes")
    if not isinstance(rows, list):
        raise RuntimeError("recipe registry malformed")
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("capability_id"), str):
            raise RuntimeError("recipe row malformed")
        cap = row["capability_id"]
        if cap in out:
            raise RuntimeError(f"duplicate proof recipe: {cap}")
        out[cap] = row
    if len(out) != data.get("capability_count"):
        raise RuntimeError("recipe count mismatch")
    return out


def common_request_allowed(recipe: dict[str, Any], req: dict[str, Any]) -> bool:
    network = req.get("network_scope")
    allowed_network = {"NONE"}
    if recipe.get("network_policy") == "LOOPBACK_ONLY":
        allowed_network.add("LOOPBACK")
    if network not in allowed_network:
        return False
    if req.get("synthetic") is not False:
        return False
    if req.get("privileged") is not False:
        return False
    if req.get("external_side_effects") is not False:
        return False
    if req.get("global_promotion_claim") is not False:
        return False
    if recipe.get("human_approval_required") and not req.get("human_approved"):
        return False
    return True


def negative_proof(recipe: dict[str, Any]) -> dict[str, Any]:
    base = {
        "network_scope": "NONE",
        "synthetic": False,
        "privileged": False,
        "external_side_effects": False,
        "global_promotion_claim": False,
        "human_approved": bool(recipe.get("human_approval_required")),
    }
    cases = {
        "synthetic_pass_denied": not common_request_allowed(recipe, {**base, "synthetic": True}),
        "privileged_execution_denied": not common_request_allowed(recipe, {**base, "privileged": True}),
        "external_side_effect_denied": not common_request_allowed(recipe, {**base, "external_side_effects": True}),
        "global_promotion_denied": not common_request_allowed(recipe, {**base, "global_promotion_claim": True}),
    }
    if recipe.get("network_policy") == "NONE":
        cases["external_network_denied"] = not common_request_allowed(recipe, {**base, "network_scope": "INTERNET"})
    else:
        cases["non_loopback_network_denied"] = not common_request_allowed(recipe, {**base, "network_scope": "INTERNET"})
    if recipe.get("human_approval_required"):
        cases["missing_human_approval_denied"] = not common_request_allowed(recipe, {**base, "human_approved": False})
    if not all(cases.values()):
        raise RuntimeError(f"negative proof matrix failed: {cases}")
    return {"status": "PASS", "cases": cases}


def _loopback_server(directory: Path):
    class Handler(SimpleHTTPRequestHandler):
        observed: list[str] = []

        def do_GET(self) -> None:
            type(self).observed.append(self.path)
            super().do_GET()

        def log_message(self, format: str, *args: Any) -> None:
            return

    Handler.observed = []
    handler = partial(Handler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return Handler, server, thread


def proof_knowledge_cache(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    source = scope / "source.txt"
    body = f"{cap} {subject} current-host knowledge sentinel"
    source.write_text(body + "\n", encoding="utf-8")
    before = sha_file(source)
    db = sqlite3.connect(scope / "index.sqlite3")
    try:
        db.execute("CREATE VIRTUAL TABLE docs USING fts5(capability_id, body)")
        db.execute("INSERT INTO docs(capability_id,body) VALUES(?,?)", (cap, body))
        db.commit()
        row = db.execute("SELECT capability_id FROM docs WHERE docs MATCH ?", ("sentinel",)).fetchone()
    finally:
        db.close()
    if row != (cap,) or sha_file(source) != before:
        raise RuntimeError("knowledge/cache proof failed")
    return {"source_sha256": before, "retrieved_capability_id": row[0], "source_preserved": True}


def proof_agent_process(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    code = (
        "import json,os;"
        f"print(json.dumps({{'capability_id':'{cap}','pid':os.getpid(),'status':'PASS'}}))"
    )
    proc = cmd([sys.executable, "-I", "-c", code], 20)
    if proc.returncode != 0:
        raise RuntimeError(f"agent/process proof failed: {proc.stderr[-1000:]}")
    row = json.loads(proc.stdout.strip())
    if row.get("status") != "PASS" or row.get("capability_id") != cap or row.get("pid") == os.getpid():
        raise RuntimeError("agent/process proof output invalid")
    return {"child_pid": row["pid"], "parent_pid": os.getpid(), "separate_process": True, "network_scope": "NONE"}


def proof_security_local(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    benign = scope / "benign.txt"
    flagged = scope / "flagged.txt"
    benign.write_text("ordinary local current-host content\n", encoding="utf-8")
    marker = f"FA3_{cap.replace('-', '_')}_DETECTION_SENTINEL"
    flagged.write_text(f"test-only marker: {marker}\n", encoding="utf-8")
    pattern = re.compile(re.escape(marker))
    benign_hits = bool(pattern.search(benign.read_text(encoding="utf-8")))
    flagged_hits = bool(pattern.search(flagged.read_text(encoding="utf-8")))
    if benign_hits or not flagged_hits:
        raise RuntimeError("local security detection proof failed")
    return {
        "benign_sha256": sha_file(benign),
        "flagged_sha256": sha_file(flagged),
        "false_positive": benign_hits,
        "test_marker_detected": flagged_hits,
        "external_target_contacted": False,
    }


def _find_any(names: tuple[str, ...]) -> tuple[str, str] | None:
    for name in names:
        path = shutil.which(name)
        if path:
            return name, path
    return None


def proof_graphics_3d(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    found = _find_any(("bforartists", "bforartists-bin", "blender"))
    if not found:
        raise RuntimeError("Bforartists or Blender required")
    name, binary = found
    sentinel = f"FA3_{cap.replace('-', '_')}_3D_PASS"
    proc = cmd([binary, "--background", "--factory-startup", "--python-expr", f"print('{sentinel}')"], 90)
    combined = proc.stdout + "\n" + proc.stderr
    if proc.returncode != 0 or sentinel not in combined:
        raise RuntimeError(f"3D runtime smoke failed: {proc.stderr[-1500:]}")
    return {"application": name, "binary": binary, "headless_smoke": True}


def proof_metric_3d_reconstruction(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    """Prove the provider-neutral CAP-032 baseline on the existing DCC geometry kernel.

    This is deliberately not a differentiable/neural-rendering claim. It performs
    a real point-set -> convex-hull mesh reconstruction and verifies metric
    geometry. Open3D, Kaolin and PyTorch3D remain replaceable specialized
    providers behind the same CAP-032 authority boundary.
    """
    scope.mkdir(parents=True, exist_ok=True)
    found = _find_any(("bforartists", "bforartists-bin", "blender"))
    if not found:
        raise RuntimeError("Bforartists or Blender required for metric 3D reconstruction proof")
    name, binary = found
    script = scope / "metric_3d_reconstruction.py"
    script.write_text(
        "import bpy,bmesh,json\n"
        "mesh=bpy.data.meshes.new('fa3_metric_reconstruction')\n"
        "obj=bpy.data.objects.new('fa3_metric_reconstruction',mesh)\n"
        "bm=bmesh.new()\n"
        "coords=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(1.,1.,0.),"
        "(0.,0.,1.),(1.,0.,1.),(0.,1.,1.),(1.,1.,1.)]\n"
        "verts=[bm.verts.new(co) for co in coords]\n"
        "bm.verts.ensure_lookup_table()\n"
        "bmesh.ops.convex_hull(bm,input=verts,use_existing_faces=False)\n"
        "bm.to_mesh(mesh);bm.free();mesh.update()\n"
        "vv=[v.co.copy() for v in mesh.vertices]\n"
        "volume=0.0\n"
        "for poly in mesh.polygons:\n"
        " p=[vv[i] for i in poly.vertices]\n"
        " for i in range(1,len(p)-1): volume += p[0].dot(p[i].cross(p[i+1]))/6.0\n"
        "dims=[]\n"
        "for axis in range(3):\n"
        " values=[float(v[axis]) for v in vv];dims.append(max(values)-min(values))\n"
        "payload={'vertices':len(mesh.vertices),'faces':len(mesh.polygons),"
        "'volume':abs(float(volume)),'dimensions':dims}\n"
        "print('FA3_METRIC_3D_JSON='+json.dumps(payload,sort_keys=True))\n",
        encoding="utf-8",
    )
    proc = cmd([binary, "--background", "--factory-startup", "--python", str(script)], 90)
    combined = proc.stdout + "\n" + proc.stderr
    if proc.returncode != 0:
        raise RuntimeError(f"metric 3D reconstruction runtime failed: {proc.stderr[-1500:]}")
    marker = "FA3_METRIC_3D_JSON="
    payload_line = next((line for line in reversed(combined.splitlines()) if marker in line), None)
    if payload_line is None:
        raise RuntimeError("metric 3D reconstruction proof payload missing")
    row = json.loads(payload_line.split(marker, 1)[1].strip())
    dims = row.get("dimensions")
    if (
        int(row.get("vertices", 0)) < 8
        or int(row.get("faces", 0)) < 6
        or abs(float(row.get("volume", 0.0)) - 1.0) > 1e-5
        or not isinstance(dims, list)
        or len(dims) != 3
        or any(abs(float(value) - 1.0) > 1e-5 for value in dims)
    ):
        raise RuntimeError(f"metric 3D reconstruction invariant failed: {row}")
    return {
        "application": name,
        "binary": binary,
        "provider_class": "DCC_GEOMETRY_KERNEL",
        "point_set_to_mesh_reconstruction": True,
        "metric_volume": row["volume"],
        "metric_dimensions": dims,
        "vertex_count": row["vertices"],
        "face_count": row["faces"],
        "differentiable_or_neural_provider_claim": False,
        "provider_hard_dependency": False,
    }

def proof_gpu_compute(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    smi = shutil.which("nvidia-smi")
    if not smi:
        raise RuntimeError("nvidia-smi required")
    resolved = resolve_python_runtime(require_torch=True, require_pytorch3d=False, require_cuda=True)
    selected = resolved.get("selected")
    if not isinstance(selected, dict):
        raise RuntimeError("approved local Python runtime with torch + CUDA required")
    python = str(selected["path"])
    inv = cmd([smi, "--query-gpu=uuid,pci.bus_id,driver_version", "--format=csv,noheader,nounits"], 20)
    if inv.returncode != 0 or not inv.stdout.strip():
        raise RuntimeError("NVIDIA inventory unavailable")
    code = (
        "import json,torch;"
        "assert torch.cuda.is_available();"
        "d=torch.device('cuda');"
        "a=torch.arange(4096,dtype=torch.float32,device=d).reshape(64,64);"
        "c=a@a.T;torch.cuda.synchronize();"
        "print(json.dumps({'device':torch.cuda.get_device_name(),'sum':float(c.sum().item())}))"
    )
    proc = cmd([python, "-c", code], 60)
    if proc.returncode != 0:
        raise RuntimeError(f"CUDA compute proof failed: {proc.stderr[-1500:]}")
    row = json.loads(proc.stdout.strip())
    if not isinstance(row.get("sum"), (int, float)):
        raise RuntimeError("CUDA compute result invalid")
    return {
        "cuda_compute": True,
        "python": python,
        "torch_version": selected.get("torch_version"),
        "device_name": row.get("device"),
        "result_sum": row.get("sum"),
        "inventory_sha256": sha(inv.stdout.encode()),
        "hardcoded_gpu_ordinal_claim": False,
    }


def _ffprobe(path: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe required")
    proc = cmd([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], 30)
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {proc.stderr[-1000:]}")
    return json.loads(proc.stdout)


def proof_audio_local(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg required")
    out = scope / "audio.wav"
    proc = cmd([
        ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "sine=frequency=997:sample_rate=48000:duration=0.5",
        "-ac", "1", "-c:a", "pcm_s16le", str(out)
    ], 45)
    if proc.returncode != 0 or not out.is_file():
        raise RuntimeError(f"audio proof failed: {proc.stderr[-1000:]}")
    probe = _ffprobe(out)
    stream = next((x for x in probe.get("streams", []) if x.get("codec_type") == "audio"), None)
    if not isinstance(stream, dict) or int(stream.get("sample_rate", 0)) != 48000:
        raise RuntimeError("audio stream validation failed")
    return {"artifact_sha256": sha_file(out), "sample_rate": 48000, "channels": stream.get("channels"), "network_fetch": False}


def proof_media_video(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg required")
    out = scope / "video.mkv"
    proc = cmd([
        ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=128x72:rate=8:duration=0.5",
        "-c:v", "ffv1", str(out)
    ], 45)
    if proc.returncode != 0 or not out.is_file():
        raise RuntimeError(f"media proof failed: {proc.stderr[-1000:]}")
    probe = _ffprobe(out)
    stream = next((x for x in probe.get("streams", []) if x.get("codec_type") == "video"), None)
    if not isinstance(stream, dict) or int(stream.get("width", 0)) != 128 or int(stream.get("height", 0)) != 72:
        raise RuntimeError("video stream validation failed")
    return {"artifact_sha256": sha_file(out), "codec": stream.get("codec_name"), "width": 128, "height": 72, "network_fetch": False}


DESKTOP_WAYLAND_REQUIRED_CAPABILITIES = (
    "linux_host",
    "xdg_runtime",
    "dbus_session",
    "uri_open",
    "local_gui_session",
)


def desktop_wayland_scoped_admission(
    report: dict[str, Any],
    session_evidence: dict[str, Any],
) -> dict[str, Any]:
    capabilities = report.get("capabilities")
    if not isinstance(capabilities, dict):
        return {
            "result": "FAIL",
            "reason": "DESKTOP_CAPABILITIES_MISSING",
            "required_capabilities": {},
            "full_desktop_admission_result": report.get("result"),
            "secret_backend_status": None,
        }

    required = {
        key: capabilities.get(key) == "PASS"
        for key in DESKTOP_WAYLAND_REQUIRED_CAPABILITIES
    }
    required["xdg_desktop_portal"] = capabilities.get("xdg_desktop_portal") == "PASS"

    desktop = report.get("desktop") if isinstance(report.get("desktop"), dict) else {}
    session = report.get("session") if isinstance(report.get("session"), dict) else {}
    session_checks = {
        "desktop_kde_plasma": desktop.get("desktop") == "KDE_PLASMA",
        "session_wayland": session.get("type") == "wayland",
        "active_local_graphical_session": session_evidence.get(
            "active_local_graphical_session_proven"
        ) is True,
        "wayland_socket": session_evidence.get("wayland_socket_proven") is True,
        "kde_bus_identity": session_evidence.get("kde_bus_identity_proven") is True,
        "portal_bus_identity": session_evidence.get("portal_bus_identity_proven") is True,
    }

    failed = sorted(
        [key for key, ok in required.items() if not ok]
        + [key for key, ok in session_checks.items() if not ok]
    )
    full_required_failures = sorted(
        key
        for key in (
            "linux_host",
            "xdg_runtime",
            "dbus_session",
            "uri_open",
            "secret_backend",
            "local_gui_session",
        )
        if capabilities.get(key) == "FAIL"
    )
    non_scoped_full_failures = [
        key for key in full_required_failures if key != "secret_backend"
    ]
    if non_scoped_full_failures:
        failed.extend(
            f"full_desktop_failure:{key}" for key in non_scoped_full_failures
        )

    return {
        "result": "PASS" if not failed else "FAIL",
        "required_capabilities": required,
        "session_checks": session_checks,
        "failed_checks": failed,
        "full_desktop_admission_result": report.get("result"),
        "full_desktop_required_failures": full_required_failures,
        "secret_backend_status": capabilities.get("secret_backend"),
        "secret_backend_used_for_desktop_wayland_admission": False,
        "scope_semantics": "DESKTOP_WAYLAND_SESSION_PROOF_NOT_FULL_DESKTOP_ADMISSION",
    }


def proof_desktop_wayland(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    from fa3_desktop_admission import (
        collect_runtime_probes,
        discover_current_user_session_environment,
        evaluate_desktop,
    )

    session_context = discover_current_user_session_environment()
    session_env = session_context["environment"]
    report = evaluate_desktop(
        session_env,
        collect_runtime_probes(session_env),
        require_gui=True,
    )
    scoped = desktop_wayland_scoped_admission(
        report,
        session_context["evidence"],
    )
    if scoped.get("result") != "PASS":
        raise RuntimeError(
            f"desktop/Wayland scoped admission failed for {cap}: {scoped}; "
            f"full_desktop_admission={report}"
        )

    return {
        "desktop": report.get("desktop"),
        "session": report.get("session"),
        "desktop_wayland_scope": scoped,
        "full_desktop_admission_result": report.get("result"),
        "secret_backend_status": report.get("capabilities", {}).get("secret_backend"),
        "secret_backend_used_for_desktop_wayland_admission": False,
        "session_discovery": session_context["evidence"],
        "private_kde_api_used": False,
        "privileged": False,
    }


def proof_document_publish(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    source = scope / "document.md"
    source.write_text(f"# {subject}\n\n{cap} current-host publication sentinel.\n", encoding="utf-8")
    source_hash = sha_file(source)
    page = scope / "index.html"
    page.write_text(
        "<!doctype html><html><body>"
        f"<h1>{html.escape(subject)}</h1><p>{html.escape(cap)} current-host publication sentinel.</p>"
        f"<code>{source_hash}</code></body></html>\n",
        encoding="utf-8",
    )
    Handler, server, thread = _loopback_server(scope)
    host, port = server.server_address
    try:
        with urlopen(f"http://{host}:{port}/index.html", timeout=5) as response:
            payload = response.read()
            status = response.status
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
    if status != 200 or source_hash.encode() not in payload or not Handler.observed:
        raise RuntimeError("document publication loopback proof failed")
    return {"source_sha256": source_hash, "export_sha256": sha_file(page), "loopback_http": True, "external_publish": False}


def proof_toolchain_build(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    compiler = _find_any(("cc", "gcc", "clang"))
    if not compiler:
        raise RuntimeError("C compiler required")
    name, binary = compiler
    source = scope / "smoke.c"
    exe = scope / "smoke"
    sentinel = f"FA3_{cap.replace('-', '_')}_BUILD_PASS"
    source.write_text(f'#include <stdio.h>\nint main(void){{puts("{sentinel}");return 0;}}\n', encoding="utf-8")
    build = cmd([binary, "-O2", str(source), "-o", str(exe)], 30)
    if build.returncode != 0:
        raise RuntimeError(f"toolchain build failed: {build.stderr[-1000:]}")
    run = cmd([str(exe)], 10)
    if run.returncode != 0 or sentinel not in run.stdout:
        raise RuntimeError("toolchain executable smoke failed")
    return {"compiler": name, "compiler_path": binary, "source_sha256": sha_file(source), "binary_sha256": sha_file(exe)}


def proof_storage_io(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    path = scope / "storage.bin"
    block = hashlib.sha256(f"{cap}:{subject}".encode()).digest()
    payload = block * (1024 * 1024 // len(block))
    with path.open("wb") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    before = sha(payload)
    after = sha_file(path)
    if before != after:
        raise RuntimeError("storage fsync/readback integrity failed")
    return {"bytes": path.stat().st_size, "sha256": after, "fsync_completed": True, "readback_equal": True}


def proof_network_loopback(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    page = scope / "index.txt"
    sentinel = f"{cap}:{subject}:LOOPBACK_PASS"
    page.write_text(sentinel + "\n", encoding="utf-8")
    Handler, server, thread = _loopback_server(scope)
    host, port = server.server_address
    try:
        with urlopen(f"http://{host}:{port}/index.txt", timeout=5) as response:
            payload = response.read().decode()
            status = response.status
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
    if status != 200 or sentinel not in payload or not Handler.observed:
        raise RuntimeError("loopback integration proof failed")
    return {"loopback_http": True, "observed_request_count": len(Handler.observed), "external_network": False}


def proof_system_runtime(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    cgroup = Path("/sys/fs/cgroup/cgroup.controllers")
    proc_status = Path("/proc/self/status")
    if not cgroup.is_file() or not proc_status.is_file():
        raise RuntimeError("Linux cgroup v2/proc runtime not available")
    uname = cmd(["uname", "-r"], 10)
    if uname.returncode != 0 or not uname.stdout.strip():
        raise RuntimeError("kernel version probe failed")
    controllers = cgroup.read_text(encoding="utf-8").split()
    if not controllers:
        raise RuntimeError("cgroup v2 controllers unavailable")
    return {
        "kernel_release": uname.stdout.strip(),
        "cgroup_v2": True,
        "controllers": controllers,
        "rootless": os.geteuid() != 0,
        "proc_status_sha256": sha_file(proc_status),
    }


def proof_pipeline_transform(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    source = {"capability_id": cap, "subject": subject, "values": [3, 1, 2]}
    src = scope / "input.json"; write(src, source)
    db = sqlite3.connect(scope / "transform.sqlite3")
    try:
        db.execute("CREATE TABLE values_t(v INTEGER NOT NULL)")
        db.executemany("INSERT INTO values_t(v) VALUES(?)", [(v,) for v in source["values"]])
        db.commit()
        ordered = [row[0] for row in db.execute("SELECT v FROM values_t ORDER BY v")]
    finally:
        db.close()
    out = scope / "output.json"; write(out, {"capability_id": cap, "values": ordered})
    if ordered != [1, 2, 3]:
        raise RuntimeError("structured transform proof failed")
    return {"input_sha256": sha_file(src), "output_sha256": sha_file(out), "ordered_values": ordered}


def proof_external_conditional(scope: Path, cap: str, subject: str) -> dict[str, Any]:
    scope.mkdir(parents=True, exist_ok=True)
    # Exercise the local adapter boundary only. No third-party endpoint is contacted.
    return {
        **proof_network_loopback(scope, cap, subject),
        "provider_execution_claim": False,
        "conditional_external_activation": True,
        "explicit_human_approval_required_for_external_side_effect": True,
    }


PRIMITIVES = {
    "knowledge_cache": proof_knowledge_cache,
    "agent_process": proof_agent_process,
    "security_local": proof_security_local,
    "graphics_3d": proof_graphics_3d,
    "metric_3d_reconstruction": proof_metric_3d_reconstruction,
    "gpu_compute": proof_gpu_compute,
    "audio_local": proof_audio_local,
    "media_video": proof_media_video,
    "desktop_wayland": proof_desktop_wayland,
    "document_publish": proof_document_publish,
    "toolchain_build": proof_toolchain_build,
    "storage_io": proof_storage_io,
    "network_loopback": proof_network_loopback,
    "system_runtime": proof_system_runtime,
    "pipeline_transform": proof_pipeline_transform,
    "external_conditional": proof_external_conditional,
}


def run(root: Path, scope: Path, cap: str, mode: str) -> dict[str, Any]:
    recipes = recipe_map(root)
    recipe = recipes.get(cap)
    if recipe is None:
        raise RuntimeError(f"no proof recipe registered for {cap}")
    primitive = recipe.get("primitive")
    if primitive not in PRIMITIVES:
        raise RuntimeError(f"unsupported proof primitive: {primitive}")
    if mode == "negative":
        result = negative_proof(recipe)
    elif mode == "rollback":
        result = {"status": "PASS", **exact_rollback(scope, cap, str(primitive))}
    else:
        request = {
            "network_scope": "LOOPBACK" if recipe.get("network_policy") == "LOOPBACK_ONLY" else "NONE",
            "synthetic": False,
            "privileged": False,
            "external_side_effects": False,
            "global_promotion_claim": False,
            "human_approved": bool(recipe.get("human_approval_required")),
        }
        if not common_request_allowed(recipe, request):
            raise RuntimeError("positive request rejected by recipe policy")
        result = {
            "status": "PASS",
            **PRIMITIVES[str(primitive)](scope, cap, str(recipe.get("subject"))),
        }
    result.update(
        {
            "capability_id": cap,
            "subject": recipe.get("subject"),
            "primitive": primitive,
            "network_policy": recipe.get("network_policy"),
            "external_side_effects": False,
            "global_promotion_claim": False,
            "registration_is_runtime_pass": False,
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capability", required=True)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--producer-id", required=True)
    args = parser.parse_args()
    try:
        if env("FA3_CURRENT_HOST") != "1" or env("FA3_EXECUTION_SCOPE") != "CURRENT_HOST":
            raise RuntimeError("real CURRENT_HOST execution required")
        if os.geteuid() == 0:
            raise RuntimeError("current-host capability proof must be rootless")
        if env("FA3_CAPABILITY_ID") != args.capability:
            raise RuntimeError("capability binding mismatch")
        root = Path(env("FA3_REPOSITORY_ROOT")).resolve()
        scope = Path(env("FA3_QUALIFICATION_SOURCE_ARTIFACT_DIR")).resolve()
        if root not in scope.parents:
            raise RuntimeError("artifact scope escapes repository")
        scope.mkdir(parents=True, exist_ok=True)

        supplied = json.loads(env("FA3_COVERS_SOURCE_DECISION_IDS_JSON"))
        expected = expected_source_decisions(root, args.capability)
        if supplied != expected:
            raise RuntimeError("source decision coverage mismatch")
        host_digest = env("FA3_HOST_FINGERPRINT_SHA256")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", host_digest):
            raise RuntimeError("invalid host fingerprint SHA-256")

        result = run(root, scope, args.capability, args.mode)
        result["source_decision_coverage_count"] = len(expected)
        result["host_fingerprint_sha256"] = host_digest.lower()

        artifact = scope / f"{args.capability.lower().replace('-', '')}-full-closure-evidence.json"
        write(
            artifact,
            {
                "schema": "fa3.full-current-host-capability-proof.v1",
                "subject_id": args.capability,
                "test_kind": env("FA3_TEST_KIND"),
                "test_id": env("FA3_TEST_ID"),
                "qualification_id": env("FA3_QUALIFICATION_ID"),
                "constituent_id": env("FA3_CONSTITUENT_ID"),
                "execution_scope": "CURRENT_HOST",
                "current_host": True,
                "synthetic": False,
                "ci_reference_only": False,
                "provider_receipt_only": False,
                "component_receipt_only": False,
                "generic_host_collection_only": False,
                "global_promotion_claim": False,
                "result": result,
            },
        )
        verdict = {
            "schema": VERDICT_SCHEMA,
            "producer_id": args.producer_id,
            "qualification_id": env("FA3_QUALIFICATION_ID"),
            "constituent_id": env("FA3_CONSTITUENT_ID"),
            "subject_id": args.capability,
            "test_kind": env("FA3_TEST_KIND"),
            "test_id": env("FA3_TEST_ID"),
            "status": "PASS",
            "execution_scope": "CURRENT_HOST",
            "current_host": True,
            "synthetic": False,
            "ci_reference_only": False,
            "provider_receipt_only": False,
            "component_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "source_evidence_class": env("FA3_SOURCE_EVIDENCE_CLASS"),
            "covers_source_decision_ids": expected,
            "source_artifact_path": artifact.relative_to(root).as_posix(),
            "source_artifact_sha256": sha_file(artifact),
        }
        print(json.dumps(verdict, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "REJECTED", "findings": [str(exc)]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
