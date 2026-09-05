#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_PACKAGE = "lynxhub"
EXPECTED_VERSION = "3.5.8"
EXPECTED_ARCH = "amd64"
EXPECTED_EXECUTABLE = Path("/opt/LynxHub/lynxhub")
EXPECTED_DEB_SHA256 = "b13882eb5d0443b84bd8c2488c659a149c5b16e15f22fad93aa6ad3c5f33a435"
EXPECTED_CUSTOM_ACTIONS_SHA256 = "125c3382393ef32bde5d1eae415a7a7829493e0d77504f02e6f72fc85bb6ef83"


def run(*command: str) -> tuple[int, str, str]:
    proc = subprocess.run(command, text=True, capture_output=True, check=False)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def check(name: str, passed: bool, **details: Any) -> dict[str, Any]:
    return {"check": name, "result": "PASS" if passed else "FAIL", **details}


def json_receipt(path: Path | None, *, require_human: bool = False) -> tuple[bool, dict[str, Any]]:
    if path is None or not path.is_file():
        return False, {"path": str(path) if path else None, "reason": "receipt missing"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, {"path": str(path), "reason": f"invalid JSON: {exc}"}
    valid = value.get("status") == "PASS"
    if require_human:
        valid = valid and value.get("human_approved") is True
    return valid, {"path": str(path), "sha256": digest(path), "status": value.get("status")}


def collect(args: argparse.Namespace) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    rc, stdout, stderr = run(
        "dpkg-query", "-W", "-f=${Package}\t${Version}\t${Architecture}", EXPECTED_PACKAGE
    )
    identity = stdout.split("\t") if rc == 0 else []
    package_ok = identity == [EXPECTED_PACKAGE, EXPECTED_VERSION, EXPECTED_ARCH]
    checks.append(check("installed_deb_identity", package_ok, observed=stdout, error=stderr))
    checks.append(check("installed_executable", EXPECTED_EXECUTABLE.is_file() and os.access(EXPECTED_EXECUTABLE, os.X_OK), path=str(EXPECTED_EXECUTABLE)))

    deb = Path(args.deb).resolve() if args.deb else None
    deb_sha = digest(deb) if deb and deb.is_file() else None
    checks.append(check("downloaded_deb_digest", deb_sha == EXPECTED_DEB_SHA256, path=str(deb) if deb else None, observed_sha256=deb_sha, expected_sha256=EXPECTED_DEB_SHA256))

    custom_actions = Path(args.custom_actions).resolve() if args.custom_actions else None
    custom_actions_sha = digest(custom_actions) if custom_actions and custom_actions.is_file() else None
    checks.append(check("custom_actions_digest", custom_actions_sha == EXPECTED_CUSTOM_ACTIONS_SHA256, path=str(custom_actions) if custom_actions else None, observed_sha256=custom_actions_sha, expected_sha256=EXPECTED_CUSTOM_ACTIONS_SHA256))

    checks.append(check("wayland_session", os.environ.get("XDG_SESSION_TYPE") == "wayland", observed=os.environ.get("XDG_SESSION_TYPE")))

    home = Path.home()
    desktop = home / ".local/share/applications/ai.kindabrazy.lynxhub.desktop"
    desktop_text = desktop.read_text(encoding="utf-8") if desktop.is_file() else ""
    checks.append(check(
        "effective_desktop_entry_hardened",
        desktop.is_file() and "/.local/libexec/fa3/lynxhub-start" in desktop_text and "--no-sandbox" not in desktop_text,
        path=str(desktop),
    ))

    unit = home / ".config/systemd/user/lynxhub.service"
    unit_text = unit.read_text(encoding="utf-8") if unit.is_file() else ""
    checks.append(check(
        "single_on_demand_user_unit",
        unit.is_file()
        and "PartOf=graphical-session.target ai-creative-ops.target" in unit_text
        and "NoNewPrivileges=yes" in unit_text
        and "[Install]" not in unit_text,
        path=str(unit),
    ))

    action_wrapper = home / ".local/libexec/fa3/lynxhub-action"
    action_text = action_wrapper.read_text(encoding="utf-8") if action_wrapper.is_file() else ""
    forbidden_tokens = ("eval ", "sudo ", "pkexec ", "apt ", "dpkg ", "nft ", "mcp", "11434")
    wrapper_ok = action_wrapper.is_file() and os.access(action_wrapper, os.X_OK) and all(token not in action_text for token in forbidden_tokens)
    checks.append(check("fixed_id_action_wrapper", wrapper_ok, path=str(action_wrapper)))
    if action_wrapper.is_file() and os.access(action_wrapper, os.X_OK):
        rc, stdout, stderr = run(str(action_wrapper), "__fa3_unknown_action__")
        checks.append(check("unknown_action_denied", rc == 77, returncode=rc, stdout=stdout, stderr=stderr))
    else:
        checks.append(check("unknown_action_denied", False, reason="action wrapper unavailable"))

    rc, active, stderr = run("systemctl", "--user", "show", "lynxhub.service", "-p", "ActiveState", "--value")
    checks.append(check("lynxhub_user_service_active", rc == 0 and active == "active", observed=active, error=stderr))

    rc, transient, stderr = run(
        "systemctl", "--user", "list-units", "--state=running", "--plain", "--no-legend", "app-lynxhub@*.service"
    )
    checks.append(check("no_parallel_kde_transient_unit", rc == 0 and not transient, observed=transient, error=stderr))

    autostart_candidates = list((home / ".config/autostart").glob("*lynxhub*.desktop")) if (home / ".config/autostart").is_dir() else []
    checks.append(check("no_duplicate_desktop_autostart", not autostart_candidates, observed=[str(path) for path in autostart_candidates]))

    rc, pids, _ = run("pgrep", "-u", str(os.getuid()), "-f", str(EXPECTED_EXECUTABLE))
    command_lines: list[str] = []
    if rc == 0:
        for item in pids.splitlines():
            cmdline = Path("/proc") / item / "cmdline"
            try:
                command_lines.append(cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace").strip())
            except OSError:
                pass
    process_ok = bool(command_lines) and all("--no-sandbox" not in command for command in command_lines)
    checks.append(check("running_process_is_sandbox_preserving", process_ok, command_lines=command_lines))

    smoke_ok, smoke_details = json_receipt(Path(args.human_smoke_receipt).resolve() if args.human_smoke_receipt else None, require_human=True)
    checks.append(check("human_wayland_action_smoke", smoke_ok, **smoke_details))
    egress_ok, egress_details = json_receipt(Path(args.egress_receipt).resolve() if args.egress_receipt else None)
    checks.append(check("egress_default_deny", egress_ok, **egress_details))
    rollback_ok, rollback_details = json_receipt(Path(args.rollback_receipt).resolve() if args.rollback_receipt else None, require_human=True)
    checks.append(check("rollback_drill", rollback_ok, **rollback_details))

    passed = sum(item["result"] == "PASS" for item in checks)
    return {
        "schema": "fa3.lynxhub-current-host-evidence.v1",
        "evidence_id": "EVID-CAP-057-CURRENT-HOST-LYNXHUB",
        "provider_id": "FA3-PROVIDER-LYNXHUB-001",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "host": os.uname().nodename,
        "result": "PASS" if passed == len(checks) else "FAIL",
        "fail_closed": True,
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks,
        "runtime_promotion_eligible": passed == len(checks),
        "current_host_runtime_promotion_claimed": passed == len(checks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect read-only FA3 LynxHub current-host evidence")
    parser.add_argument("--deb", help="Original pinned LynxHub amd64 .deb")
    parser.add_argument("--custom-actions", help="Original pinned Custom Actions 7z archive")
    parser.add_argument("--human-smoke-receipt", help="Human-approved Wayland/action smoke JSON")
    parser.add_argument("--egress-receipt", help="OpenSnitch/default-deny evidence JSON")
    parser.add_argument("--rollback-receipt", help="Human-approved rollback drill JSON")
    parser.add_argument("--output", default="evidence/current-host/lynxhub-current-host.json")
    args = parser.parse_args()
    result = collect(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
