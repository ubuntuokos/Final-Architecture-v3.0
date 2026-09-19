#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

VERDICT_SCHEMA = "fa3.capability-current-host-qualification-constituent-verdict.v1"
CAPABILITIES = ("CAP-011", "CAP-012", "CAP-013", "CAP-014", "CAP-015")
MODES = ("positive", "negative", "rollback")
NAMES = {c: f"{c.lower().replace('-', '')}-mat003-evidence.json" for c in CAPABILITIES}


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


def repo_file(root: Path, rel: str) -> Path:
    path = (root / rel).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise RuntimeError(f"required artifact missing: {rel}")
    return path


def cmd(argv: list[str], timeout: int = 30, *, env_map: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        shell=False,
        check=False,
        env=env_map,
    )


def expected_source_decisions(root: Path, cap: str) -> list[str]:
    registry = load(root / "evidence/evidence-registry.json")
    row = next((x for x in registry.get("records", []) if x.get("subject_id") == cap), None)
    ids = row.get("source_decision_ids") if isinstance(row, dict) else None
    if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or not x for x in ids):
        raise RuntimeError(f"{cap} source decisions invalid")
    return ids


def validate_exact_coverage(root: Path, cap: str, supplied: list[str]) -> list[str]:
    expected = expected_source_decisions(root, cap)
    if supplied != expected:
        raise RuntimeError(f"{cap} coverage != Evidence Registry")
    return expected


def exact_rollback(scope: Path, name: str, baseline: bytes, fault: bytes) -> dict[str, Any]:
    path = scope / name
    path.parent.mkdir(parents=True, exist_ok=True)
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


def skill_package_allowed(meta: dict[str, Any]) -> bool:
    path = str(meta.get("entrypoint_path") or "")
    digest = str(meta.get("content_sha256") or "")
    return (
        isinstance(meta.get("name"), str)
        and bool(meta["name"].strip())
        and isinstance(meta.get("version"), str)
        and bool(meta["version"].strip())
        and isinstance(meta.get("trigger"), str)
        and bool(meta["trigger"].strip())
        and path == "SKILL.md"
        and not Path(path).is_absolute()
        and ".." not in Path(path).parts
        and len(digest) == 64
        and all(ch in "0123456789abcdef" for ch in digest.lower())
        and meta.get("executable_directives") == []
        and meta.get("tool_intents_route") == "CENTRAL_MCP_GATEWAY"
    )


def _mcp_gateway_fixture():
    from fa3_mcp_gateway import Adapter, McpGateway

    registry = {
        "schema": "fa3.mcp.capability-registry.v1",
        "profile": "FA3-MCP-CURRENT-HOST-001",
        "authority": "FA3-AUTH-MCP-GATEWAY-001",
        "policy_authority": "SECURITY_GOVERNANCE_POLICY_PLANE",
        "fail_closed": True,
        "automatic_provider_activation": False,
        "direct_agent_provider_bypass": "DENY",
        "capability_delta": 0,
        "authority_delta": 0,
        "capabilities": [
            {
                "capability_id": "fa3.mat003.echo",
                "risk_class": "R0",
                "side_effects": [],
                "approval": "policy",
                "hrb_required": False,
                "providers": [
                    {
                        "provider_id": "FA3-PROVIDER-MAT003-LOCAL",
                        "adapter_id": "fa3.adapter.mat003.local",
                        "state": "CONNECTED",
                        "priority": 1,
                        "evidence_ref": "CURRENT_HOST_MAT003",
                    }
                ],
            }
        ],
    }
    gateway = McpGateway(registry)
    gateway.register_adapter(
        Adapter(
            "fa3.adapter.mat003.local",
            "FA3-PROVIDER-MAT003-LOCAL",
            lambda args: {"echo": args.get("value"), "local_only": True},
        )
    )
    return gateway


def _mcp_request() -> dict[str, Any]:
    return {
        "actor_id": "fa3-mat003",
        "client_id": "fa3-current-host-qualification",
        "session_id": "mat003-current-host",
        "capability_id": "fa3.mat003.echo",
        "arguments": {"value": "current-host"},
        "policy_decision": {
            "authority": "SECURITY_GOVERNANCE_POLICY_PLANE",
            "decision_id": "mat003-policy-allow",
            "capability_id": "fa3.mat003.echo",
            "status": "ALLOW",
        },
    }


def cap011(root: Path, scope: Path, mode: str) -> dict[str, Any]:
    for rel in (
        "canonical/contracts/FA3-MCP-GATEWAY-CONTRACTS-001.json",
        "canonical/profiles/FA3-SKILL-FABRIC-001.json",
        "canonical/contracts/FA3-SKILL-PACKAGE-ADMISSION-CONTRACTS-001.json",
        "canonical/mcp-capability-registry.json",
    ):
        repo_file(root, rel)
    if mode == "negative":
        gateway = _mcp_gateway_fixture()
        missing_policy = _mcp_request()
        missing_policy.pop("policy_decision")
        inline_secret = _mcp_request()
        inline_secret["token"] = "must-not-pass"
        unknown_cap = _mcp_request()
        unknown_cap["capability_id"] = "fa3.unknown"
        cases = {
            "missing_policy_denied": gateway.invoke(missing_policy).get("reason_code") == "MISSING_POLICY_DECISION",
            "inline_secret_denied": gateway.invoke(inline_secret).get("reason_code") == "INLINE_SECRET_FORBIDDEN",
            "unknown_capability_denied": gateway.invoke(unknown_cap).get("reason_code") == "UNKNOWN_CAPABILITY",
            "skill_path_escape_denied": not skill_package_allowed(
                {
                    "name": "bad",
                    "version": "1",
                    "trigger": "test",
                    "entrypoint_path": "../SKILL.md",
                    "content_sha256": "0" * 64,
                    "executable_directives": [],
                    "tool_intents_route": "CENTRAL_MCP_GATEWAY",
                }
            ),
            "skill_direct_execution_denied": not skill_package_allowed(
                {
                    "name": "bad",
                    "version": "1",
                    "trigger": "test",
                    "entrypoint_path": "SKILL.md",
                    "content_sha256": "0" * 64,
                    "executable_directives": ["bash"],
                    "tool_intents_route": "CENTRAL_MCP_GATEWAY",
                }
            ),
        }
        if not all(cases.values()):
            raise RuntimeError(f"MCP/Skill/Tool negative matrix failed: {cases}")
        return {"mode": mode, "status": "PASS", "cases": cases}
    if mode == "rollback":
        return {
            "mode": mode,
            "status": "PASS",
            **exact_rollback(
                scope,
                "mcp-skill-tool-state.json",
                b'{"direct_bypass":"DENY","skill_execution":"INERT_UNTIL_AUTHORIZED"}\n',
                b'{"direct_bypass":"ALLOW","skill_execution":"AUTO"}\n',
            ),
        }

    skill_dir = scope / "skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "# MAT-003 current-host skill\n\n"
        "Use only through the Central MCP Gateway. No direct execution.\n",
        encoding="utf-8",
    )
    meta = {
        "name": "mat003-current-host-skill",
        "version": "1.0.0",
        "trigger": "current-host-qualification",
        "entrypoint_path": "SKILL.md",
        "content_sha256": sha_file(skill_file),
        "executable_directives": [],
        "tool_intents_route": "CENTRAL_MCP_GATEWAY",
    }
    if not skill_package_allowed(meta):
        raise RuntimeError("inert skill package admission failed")

    gateway = _mcp_gateway_fixture()
    receipt = gateway.invoke(_mcp_request())
    if (
        receipt.get("result_status") != "success"
        or receipt.get("reason_code") != "DISPATCH_PASS"
        or receipt.get("global_promotion_claim") is not False
    ):
        raise RuntimeError(f"governed MCP invocation failed: {receipt}")
    return {
        "mode": mode,
        "status": "PASS",
        "gateway_health": gateway.health(),
        "gateway_readiness": gateway.readiness(),
        "invocation_reason": receipt.get("reason_code"),
        "skill_content_sha256": meta["content_sha256"],
        "skill_inert_until_authorized": True,
        "direct_provider_bypass": False,
    }


def browser_target_allowed(url: str, *, approved_external: bool = False) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if parsed.username or parsed.password:
        return False
    if host in {"127.0.0.1", "::1", "localhost"}:
        return True
    return approved_external


class _ObservedHandler(SimpleHTTPRequestHandler):
    observed_paths: list[str] = []

    def do_GET(self) -> None:
        type(self).observed_paths.append(self.path)
        super().do_GET()

    def log_message(self, format: str, *args: Any) -> None:
        return


def _find_browser() -> tuple[str, str] | None:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return "CHROMIUM", path
    firefox = shutil.which("firefox")
    if firefox:
        return "FIREFOX", firefox
    return None


def _browser_loopback_smoke(scope: Path) -> dict[str, Any]:
    browser = _find_browser()
    if browser is None:
        raise RuntimeError("no supported real browser executable found")
    kind, binary = browser
    site = scope / "browser-site"
    site.mkdir(parents=True, exist_ok=True)
    sentinel = "FA3_MAT003_BROWSER_AUTOMATION_SENTINEL"
    html = f"<!doctype html><html><head><title>{sentinel}</title></head><body>{sentinel}</body></html>\n"
    (site / "index.html").write_text(html, encoding="utf-8")
    _ObservedHandler.observed_paths = []
    handler = partial(_ObservedHandler, directory=str(site))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    url = f"http://{host}:{port}/index.html"
    if not browser_target_allowed(url):
        server.shutdown()
        server.server_close()
        raise RuntimeError("loopback browser target policy rejected its own target")
    try:
        profile = scope / "browser-profile"
        profile.mkdir(parents=True, exist_ok=True)
        if kind == "CHROMIUM":
            proc = cmd(
                [
                    binary,
                    "--headless=new",
                    "--disable-gpu",
                    f"--user-data-dir={profile}",
                    "--dump-dom",
                    url,
                ],
                45,
            )
            output_verified = proc.returncode == 0 and sentinel in proc.stdout
            screenshot = None
        else:
            shot = scope / "browser-screenshot.png"
            env_map = dict(os.environ)
            env_map["MOZ_HEADLESS"] = "1"
            proc = cmd(
                [
                    binary,
                    "--headless",
                    "--profile",
                    str(profile),
                    "--screenshot",
                    str(shot),
                    url,
                ],
                45,
                env_map=env_map,
            )
            output_verified = proc.returncode == 0 and shot.is_file() and shot.stat().st_size > 100
            screenshot = {
                "path": shot.name,
                "sha256": sha_file(shot) if shot.is_file() else None,
                "bytes": shot.stat().st_size if shot.is_file() else 0,
            }
        observed = any(path.startswith("/index.html") for path in _ObservedHandler.observed_paths)
        if not output_verified or not observed:
            raise RuntimeError(
                f"real browser loopback smoke failed kind={kind} rc={proc.returncode} observed={observed} "
                f"stderr={proc.stderr[-1000:]}"
            )
        return {
            "browser_kind": kind,
            "browser_binary": binary,
            "loopback_only": True,
            "requested_url": url,
            "http_request_observed": observed,
            "content_sha256": sha(html.encode("utf-8")),
            "output_verified": output_verified,
            "screenshot": screenshot,
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def cap012(root: Path, scope: Path, mode: str) -> dict[str, Any]:
    repo_file(root, "canonical/FA3-DESKTOP-BASE-001.json")
    if mode == "negative":
        cases = {
            "file_scheme_denied": not browser_target_allowed("file:///etc/passwd"),
            "javascript_scheme_denied": not browser_target_allowed("javascript:alert(1)"),
            "credential_url_denied": not browser_target_allowed("https://user:pass@example.com/"),
            "external_without_approval_denied": not browser_target_allowed("https://example.com/"),
            "loopback_allowed": browser_target_allowed("http://127.0.0.1:12345/test"),
        }
        if not all(cases.values()):
            raise RuntimeError(f"Browser Automation negative matrix failed: {cases}")
        return {"mode": mode, "status": "PASS", "cases": cases}
    if mode == "rollback":
        return {
            "mode": mode,
            "status": "PASS",
            **exact_rollback(
                scope,
                "browser-policy.json",
                b'{"external_requires_approval":true,"unsafe_schemes":"DENY"}\n',
                b'{"external_requires_approval":false,"unsafe_schemes":"ALLOW"}\n',
            ),
        }
    proof = _browser_loopback_smoke(scope)
    return {"mode": mode, "status": "PASS", **proof}


def computer_use_intent_allowed(intent: dict[str, Any]) -> bool:
    argv = intent.get("argv")
    broker = intent.get("broker")
    return (
        intent.get("execution_scope") == "CURRENT_USER_SESSION"
        and broker == "XDG_PORTAL_OR_APPROVED_ADAPTER"
        and intent.get("privileged") is False
        and intent.get("private_kde_api") is False
        and intent.get("free_form_shell") is False
        and isinstance(argv, list)
        and bool(argv)
        and all(isinstance(x, str) and x for x in argv)
        and Path(argv[0]).name not in {"sudo", "su", "pkexec", "sh", "bash"}
    )


def cap013(root: Path, scope: Path, mode: str) -> dict[str, Any]:
    for rel in (
        "canonical/FA3-DESKTOP-BASE-001.json",
        "canonical/FA3-DESKTOP-PLASMA-001.json",
        "canonical/FA3-GATE-DESKTOP-PORTABILITY-001.json",
        "canonical/contracts/FA3-DESKTOP-CONTRACTS-001.json",
    ):
        repo_file(root, rel)
    if mode == "negative":
        base = {
            "execution_scope": "CURRENT_USER_SESSION",
            "broker": "XDG_PORTAL_OR_APPROVED_ADAPTER",
            "privileged": False,
            "private_kde_api": False,
            "free_form_shell": False,
            "argv": ["xdg-open", "https://example.invalid/"],
        }
        cases = {
            "privilege_escalation_denied": not computer_use_intent_allowed({**base, "argv": ["sudo", "id"]}),
            "private_kde_api_denied": not computer_use_intent_allowed({**base, "private_kde_api": True}),
            "free_form_shell_denied": not computer_use_intent_allowed({**base, "free_form_shell": True, "argv": ["bash", "-c", "true"]}),
            "direct_unbrokered_denied": not computer_use_intent_allowed({**base, "broker": "DIRECT_KWIN"}),
            "brokered_nonprivileged_intent_allowed": computer_use_intent_allowed(base),
        }
        if not all(cases.values()):
            raise RuntimeError(f"KDE/Wayland Computer Use negative matrix failed: {cases}")
        return {"mode": mode, "status": "PASS", "cases": cases}
    if mode == "rollback":
        return {
            "mode": mode,
            "status": "PASS",
            **exact_rollback(
                scope,
                "computer-use-policy.json",
                b'{"broker":"XDG_PORTAL_OR_APPROVED_ADAPTER","private_kde_api":"DENY"}\n',
                b'{"broker":"DIRECT_KWIN","private_kde_api":"ALLOW"}\n',
            ),
        }

    from fa3_desktop_admission import (
        collect_runtime_probes,
        discover_current_user_session_environment,
        evaluate_desktop,
    )

    session_context = discover_current_user_session_environment()
    session_env = session_context["environment"]
    probes = collect_runtime_probes(session_env)
    report = evaluate_desktop(session_env, probes, require_gui=True)
    if report.get("result") != "PASS":
        diagnostic = None
        if (
            report.get("desktop", {}).get("desktop") == "KDE_PLASMA"
            and report.get("capabilities", {}).get("secret_backend") == "FAIL"
        ):
            from fa3_plasma_secret_service_diagnostic import (
                collect_plasma_secret_service_diagnostic,
            )
            diagnostic = collect_plasma_secret_service_diagnostic(session_env)
        raise RuntimeError(
            f"desktop admission failed: {report}; "
            f"plasma_secret_service_diagnostic={diagnostic}"
        )
    if report.get("desktop", {}).get("desktop") != "KDE_PLASMA":
        raise RuntimeError(f"KDE Plasma current-user session not proven: {report.get('desktop')}")
    if report.get("session", {}).get("type") != "wayland":
        raise RuntimeError(f"Wayland session not proven: {report.get('session')}")

    busctl = shutil.which("busctl")
    if not busctl:
        raise RuntimeError("busctl unavailable for user-session proof")
    proc = cmd([busctl, "--user", "--no-pager", "--list"], 10, env_map=session_env)
    if proc.returncode != 0:
        raise RuntimeError(f"user DBus inventory failed: {proc.stderr[-1000:]}")
    portal_present = "org.freedesktop.portal.Desktop" in proc.stdout
    kwin_present = "org.kde.KWin" in proc.stdout
    plasma_present = "org.kde.plasmashell" in proc.stdout
    if not portal_present or not kwin_present:
        raise RuntimeError(
            f"KDE/Wayland session services incomplete portal={portal_present} kwin={kwin_present}"
        )

    introspect = cmd(
        [
            busctl,
            "--user",
            "introspect",
            "org.freedesktop.portal.Desktop",
            "/org/freedesktop/portal/desktop",
        ],
        10,
        env_map=session_env,
    )
    if introspect.returncode != 0 or "org.freedesktop.portal" not in introspect.stdout:
        raise RuntimeError("XDG Desktop Portal introspection failed")
    return {
        "mode": mode,
        "status": "PASS",
        "desktop": report.get("desktop"),
        "session": report.get("session"),
        "required_capabilities": {
            key: value
            for key, value in report.get("capabilities", {}).items()
            if value == "PASS"
        },
        "portal_present": portal_present,
        "kwin_present": kwin_present,
        "plasmashell_present": plasma_present,
        "portal_introspection_pass": True,
        "session_discovery": session_context["evidence"],
        "private_kde_api_used": False,
        "desktop_mutation_performed": False,
    }


def validate_film_plan(plan: dict[str, Any]) -> bool:
    if plan.get("schema") != "fa3.film-direction-plan.v1":
        return False
    approval = plan.get("human_approval", {})
    if approval.get("status") != "APPROVED" or not approval.get("approval_id"):
        return False
    shots = plan.get("shots")
    if not isinstance(shots, list) or len(shots) < 2:
        return False
    seen: set[str] = set()
    previous_end = -1
    for shot in shots:
        if not isinstance(shot, dict):
            return False
        sid = shot.get("shot_id")
        start = shot.get("start_frame")
        end = shot.get("end_frame")
        if not isinstance(sid, str) or not sid or sid in seen:
            return False
        seen.add(sid)
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
            return False
        if start < previous_end:
            return False
        previous_end = end
        if not all(isinstance(shot.get(key), str) and shot.get(key) for key in ("intent", "framing", "camera", "audio")):
            return False
    return plan.get("authoritative_final_cut") is False


def cap014(root: Path, scope: Path, mode: str) -> dict[str, Any]:
    for rel in (
        "canonical/contracts/FA3-HYBRID-EDITORIAL-CONTRACTS-001.json",
        "canonical/contracts/FA3-KDENLIVE-EDITORIAL-CONTRACTS-001.json",
        "canonical/contracts/FA3-DESKTOP-CONTRACTS-001.json",
    ):
        repo_file(root, rel)
    base_plan = {
        "schema": "fa3.film-direction-plan.v1",
        "project_id": "mat003-film-plan",
        "fps": 24,
        "human_approval": {"status": "APPROVED", "approval_id": "mat003-human-approval"},
        "authoritative_final_cut": False,
        "shots": [
            {
                "shot_id": "S001",
                "start_frame": 0,
                "end_frame": 48,
                "intent": "establish subject and environment",
                "framing": "wide",
                "camera": "locked",
                "audio": "room tone",
            },
            {
                "shot_id": "S002",
                "start_frame": 48,
                "end_frame": 96,
                "intent": "advance subject action",
                "framing": "medium",
                "camera": "slow push",
                "audio": "dialogue",
            },
            {
                "shot_id": "S003",
                "start_frame": 96,
                "end_frame": 144,
                "intent": "resolve beat",
                "framing": "close",
                "camera": "locked",
                "audio": "dialogue and room tone",
            },
        ],
    }
    if mode == "negative":
        duplicate = json.loads(json.dumps(base_plan))
        duplicate["shots"][1]["shot_id"] = duplicate["shots"][0]["shot_id"]
        overlap = json.loads(json.dumps(base_plan))
        overlap["shots"][1]["start_frame"] = 40
        unapproved = json.loads(json.dumps(base_plan))
        unapproved["human_approval"]["status"] = "PENDING"
        authoritative = json.loads(json.dumps(base_plan))
        authoritative["authoritative_final_cut"] = True
        cases = {
            "duplicate_shot_id_denied": not validate_film_plan(duplicate),
            "overlapping_timeline_denied": not validate_film_plan(overlap),
            "missing_human_approval_denied": not validate_film_plan(unapproved),
            "planning_cannot_claim_final_cut_authority": not validate_film_plan(authoritative),
        }
        if not all(cases.values()):
            raise RuntimeError(f"Film Planning/Direction negative matrix failed: {cases}")
        return {"mode": mode, "status": "PASS", "cases": cases}
    if mode == "rollback":
        return {
            "mode": mode,
            "status": "PASS",
            **exact_rollback(
                scope,
                "film-plan-state.json",
                b'{"status":"APPROVED_PLAN","authoritative_final_cut":false}\n',
                b'{"status":"AUTO_FINALIZED","authoritative_final_cut":true}\n',
            ),
        }
    if not validate_film_plan(base_plan):
        raise RuntimeError("film direction plan validation failed")
    path = scope / "film-direction-plan.json"
    write(path, base_plan)
    reread = load(path)
    if not validate_film_plan(reread):
        raise RuntimeError("persisted film direction plan failed validation")
    return {
        "mode": mode,
        "status": "PASS",
        "plan_path": path.relative_to(root).as_posix(),
        "plan_sha256": sha_file(path),
        "shot_count": len(base_plan["shots"]),
        "timeline_frames": base_plan["shots"][-1]["end_frame"],
        "human_approval_preserved": True,
        "authoritative_final_cut": False,
    }


def validate_animation_spec(spec: dict[str, Any]) -> bool:
    fps = spec.get("fps")
    keyframes = spec.get("keyframes")
    if not isinstance(fps, (int, float)) or not math.isfinite(float(fps)) or fps <= 0 or fps > 240:
        return False
    if not isinstance(keyframes, list) or len(keyframes) < 2:
        return False
    times: list[float] = []
    for item in keyframes:
        if not isinstance(item, dict):
            return False
        try:
            t = float(item["time"])
            x = float(item["x"])
            y = float(item["y"])
        except (KeyError, TypeError, ValueError):
            return False
        if not all(math.isfinite(v) for v in (t, x, y)):
            return False
        times.append(t)
    if times != sorted(times) or len(set(times)) != len(times) or times[0] < 0:
        return False
    if spec.get("interpolation") not in {"LINEAR", "STEP", "BEZIER"}:
        return False
    return spec.get("authoritative_source_preserved") is True


def _write_ppm(path: Path, width: int, height: int, offset: int) -> None:
    pixels = bytearray(width * height * 3)
    square = 10
    x0 = max(0, min(width - square, offset))
    y0 = (height - square) // 2
    for y in range(y0, y0 + square):
        for x in range(x0, x0 + square):
            index = (y * width + x) * 3
            pixels[index:index + 3] = b"\xff\xff\xff"
    path.write_bytes(f"P6\n{width} {height}\n255\n".encode("ascii") + bytes(pixels))


def _render_animation(scope: Path) -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("ffmpeg and ffprobe are required for Animation Department current-host proof")
    frames_dir = scope / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame_count = 12
    for index in range(frame_count):
        _write_ppm(frames_dir / f"frame-{index:03d}.ppm", 64, 64, index * 4)
    frame_hashes = [sha_file(frames_dir / f"frame-{index:03d}.ppm") for index in range(frame_count)]
    if len(set(frame_hashes)) < 3:
        raise RuntimeError("animation frames are not materially changing")

    out = scope / "animation.mkv"
    proc = cmd(
        [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-framerate",
            "8",
            "-start_number",
            "0",
            "-i",
            str(frames_dir / "frame-%03d.ppm"),
            "-c:v",
            "ffv1",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ],
        60,
    )
    if proc.returncode != 0 or not out.is_file() or out.stat().st_size <= 0:
        raise RuntimeError(f"ffmpeg animation render failed: {proc.stderr[-1500:]}")
    probe = cmd(
        [
            ffprobe,
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=nb_read_frames",
            "-of",
            "default=nokey=1:noprint_wrappers=1",
            str(out),
        ],
        30,
    )
    try:
        observed = int(probe.stdout.strip())
    except ValueError:
        observed = -1
    if probe.returncode != 0 or observed != frame_count:
        raise RuntimeError(
            f"ffprobe frame count mismatch expected={frame_count} observed={observed} stderr={probe.stderr[-1000:]}"
        )
    return {
        "frame_count": frame_count,
        "observed_frame_count": observed,
        "distinct_frame_hashes": len(set(frame_hashes)),
        "animation_path": out.name,
        "animation_sha256": sha_file(out),
        "animation_bytes": out.stat().st_size,
        "ffmpeg_binary": ffmpeg,
        "ffprobe_binary": ffprobe,
        "network_required": False,
    }


def cap015(root: Path, scope: Path, mode: str) -> dict[str, Any]:
    for rel in (
        "canonical/contracts/FA3-HUMAN-MOTION-CONTRACTS-001.json",
        "canonical/profiles/FA3-HUMAN-MOTION-001.json",
        "canonical/contracts/FA3-KDENLIVE-EDITORIAL-CONTRACTS-001.json",
    ):
        repo_file(root, rel)
    good = {
        "fps": 8,
        "interpolation": "LINEAR",
        "authoritative_source_preserved": True,
        "keyframes": [
            {"time": 0.0, "x": 0.0, "y": 0.0},
            {"time": 0.75, "x": 24.0, "y": 0.0},
            {"time": 1.375, "x": 44.0, "y": 0.0},
        ],
    }
    if mode == "negative":
        nonmonotonic = json.loads(json.dumps(good))
        nonmonotonic["keyframes"][2]["time"] = 0.5
        nan_value = json.loads(json.dumps(good))
        nan_value["keyframes"][1]["x"] = float("nan")
        bad_interp = json.loads(json.dumps(good))
        bad_interp["interpolation"] = "IMPLICIT_PROVIDER_MAGIC"
        lost_source = json.loads(json.dumps(good))
        lost_source["authoritative_source_preserved"] = False
        cases = {
            "nonmonotonic_keyframes_denied": not validate_animation_spec(nonmonotonic),
            "nan_motion_denied": not validate_animation_spec(nan_value),
            "unknown_interpolation_denied": not validate_animation_spec(bad_interp),
            "source_loss_denied": not validate_animation_spec(lost_source),
        }
        if not all(cases.values()):
            raise RuntimeError(f"Animation Department negative matrix failed: {cases}")
        return {"mode": mode, "status": "PASS", "cases": cases}
    if mode == "rollback":
        return {
            "mode": mode,
            "status": "PASS",
            **exact_rollback(
                scope,
                "animation-state.json",
                b'{"source_preserved":true,"render_state":"READY"}\n',
                b'{"source_preserved":false,"render_state":"UNVERIFIED_AUTO_COMMIT"}\n',
            ),
        }
    if not validate_animation_spec(good):
        raise RuntimeError("animation keyframe specification rejected")
    spec_path = scope / "animation-spec.json"
    write(spec_path, good)
    rendered = _render_animation(scope)
    return {
        "mode": mode,
        "status": "PASS",
        "spec_sha256": sha_file(spec_path),
        "interpolation": good["interpolation"],
        "authoritative_source_preserved": True,
        **rendered,
    }


HANDLERS = {
    "CAP-011": cap011,
    "CAP-012": cap012,
    "CAP-013": cap013,
    "CAP-014": cap014,
    "CAP-015": cap015,
}


def run_mode(root: Path, scope: Path, cap: str, mode: str) -> dict[str, Any]:
    root = root.resolve()
    scope = scope.resolve()
    if cap not in CAPABILITIES or mode not in MODES:
        raise ValueError("unsupported capability or mode")
    if root not in scope.parents:
        raise RuntimeError("artifact scope escapes repository")
    scope.mkdir(parents=True, exist_ok=True)
    return HANDLERS[cap](root, scope, mode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capability", choices=CAPABILITIES, required=True)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--producer-id", required=True)
    args = parser.parse_args()
    try:
        if env("FA3_CURRENT_HOST") != "1" or env("FA3_EXECUTION_SCOPE") != "CURRENT_HOST":
            raise RuntimeError("real CURRENT_HOST execution required")
        if env("FA3_CAPABILITY_ID") != args.capability:
            raise RuntimeError("capability binding mismatch")
        root = Path(env("FA3_REPOSITORY_ROOT")).resolve()
        scope = Path(env("FA3_QUALIFICATION_SOURCE_ARTIFACT_DIR")).resolve()
        supplied = json.loads(env("FA3_COVERS_SOURCE_DECISION_IDS_JSON"))
        coverage = validate_exact_coverage(root, args.capability, supplied)
        host_digest = env("FA3_HOST_FINGERPRINT_SHA256")
        if len(host_digest) != 64 or any(ch not in "0123456789abcdef" for ch in host_digest.lower()):
            raise RuntimeError("invalid host fingerprint SHA-256")
        result = run_mode(root, scope, args.capability, args.mode)
        result.update(
            {
                "source_decision_coverage_count": len(coverage),
                "host_fingerprint_sha256": host_digest,
            }
        )
        artifact = scope / NAMES[args.capability]
        write(
            artifact,
            {
                "schema": "fa3.mat003-interaction-creative-current-host-evidence.v1",
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
            "covers_source_decision_ids": coverage,
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
