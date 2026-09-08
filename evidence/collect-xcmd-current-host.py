#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYS = ROOT / "src"
sys.path.insert(0, str(SYS))
from fa3_xcmd_current_host import (CAPABILITY, COMMIT, GATE_ID, PASS_STATUS, PROVIDER_ID,
                                   TAG, TREE, RUNNER_LABELS, receipt_valid)

REPO = "https://github.com/x-cmd/x-cmd.git"


def run(args, *, cwd=None, env=None, check=True, timeout=120):
    return subprocess.run(args, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, check=check, timeout=timeout)


def hash_files(paths):
    out = {}
    for p in paths:
        if p.exists() and p.is_file():
            out[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def resident_processes(marker: str) -> list[str]:
    try:
        text = run(["ps", "-eo", "pid=,args="], timeout=10).stdout
    except Exception:
        return []
    return [line.strip() for line in text.splitlines() if marker in line and "collect-xcmd-current-host.py" not in line]


def main() -> int:
    receipt_path = ROOT / "evidence/receipts/xcmd-current-host.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    caller = os.environ.get("FA3_CALLER_IDENTITY", "")
    request_id = os.environ.get("FA3_REQUEST_ID", "")
    workspace_id = os.environ.get("FA3_WORKSPACE_ID", "")
    labels = [x for x in os.environ.get("FA3_RUNNER_LABELS", "").split(",") if x]
    ci_fixture = os.environ.get("FA3_CI_FIXTURE", "false").lower() == "true"

    if os.geteuid() == 0:
        raise SystemExit("FAIL: X-CMD current-host admission refuses root execution")
    if not caller or not request_id or not workspace_id:
        raise SystemExit("FAIL: explicit caller identity, request id and workspace id are required")
    if not RUNNER_LABELS.issubset(set(labels)):
        raise SystemExit(f"FAIL: real current-host runner labels required: {sorted(RUNNER_LABELS)}")
    if ci_fixture:
        raise SystemExit("FAIL: CI fixture cannot collect current-host production PASS")
    for exe in ("git", "bash", "ps"):
        if shutil.which(exe) is None:
            raise SystemExit(f"FAIL: required executable missing: {exe}")

    state = Path(os.environ.get("FA3_XCMD_STATE_DIR", str(Path.home()/".local/share/fa3/xcmd-current-host"))).resolve()
    state.mkdir(parents=True, exist_ok=True)
    if state == Path.home().resolve() or Path.home().resolve() in state.parents and state.name == "":
        raise SystemExit("FAIL: invalid state root")

    startup = [Path.home()/n for n in (".bashrc", ".profile", ".zshrc", ".config/fish/config.fish")]
    startup_before = hash_files(startup)
    work = Path(tempfile.mkdtemp(prefix="run-", dir=state))
    src = work / "source"
    home = work / "home"
    home.mkdir(mode=0o700)

    source = {"repository": REPO, "commit": COMMIT, "tree": TREE, "commit_revalidated": False, "tree_revalidated": False}
    execution = {"root_execution": False, "direct_remote_eval": False, "self_update": False,
                 "host_shell_startup_unchanged": False, "resident_provider_processes_after": -1,
                 "probe":"x version", "probe_network_policy":"NO_XCMD_PACKAGE_FETCH_OR_SELF_UPDATE"}
    probe_output = ""
    error = None
    try:
        run(["git", "init", "-q", str(src)])
        run(["git", "-C", str(src), "remote", "add", "origin", REPO])
        # Exact immutable object fetch: no floating branch/tag is executable identity.
        run(["git", "-C", str(src), "fetch", "-q", "--depth=1", "origin", COMMIT], timeout=300)
        run(["git", "-C", str(src), "checkout", "-q", "--detach", "FETCH_HEAD"])
        head = run(["git", "-C", str(src), "rev-parse", "HEAD"]).stdout.strip()
        tree = run(["git", "-C", str(src), "rev-parse", "HEAD^{tree}"]).stdout.strip()
        if head != COMMIT or tree != TREE:
            raise RuntimeError(f"immutable source mismatch head={head} tree={tree}")
        source["commit_revalidated"] = True
        source["tree_revalidated"] = True

        env = os.environ.copy()
        env.update({
            "HOME": str(home), "XDG_CONFIG_HOME": str(home/".config"), "XDG_DATA_HOME": str(home/".local/share"),
            "XDG_CACHE_HOME": str(home/".cache"), "___X_CMD_ROOT": str(home/".x-cmd.root"),
            "___X_CMD_ROOT_CODE": str(src), "___X_CMD_VERSION": TAG,
            "___X_CMD_ADVISE_DISABLE": "1", "___X_CMD_LTEAM_DISABLE": "1",
        })
        script = 'set -euo pipefail; . "$___X_CMD_ROOT_CODE/X"; type ___x_cmd >/dev/null; ___x_cmd version'
        probe_output = run(["bash", "--noprofile", "--norc", "-c", script], env=env, timeout=120).stdout[-8000:]
        startup_after = hash_files(startup)
        execution["host_shell_startup_unchanged"] = startup_before == startup_after
        lingering = resident_processes(str(work))
        execution["resident_provider_processes_after"] = len(lingering)
        execution["resident_process_details"] = lingering[:10]
        if not execution["host_shell_startup_unchanged"]:
            raise RuntimeError("host shell startup file changed")
        if lingering:
            raise RuntimeError("resident provider process detected after probe")
    except Exception as exc:
        error = str(exc)

    receipt = {
        "schema":"fa3.xcmd-current-host-receipt.v1", "provider_id":PROVIDER_ID, "gate_id":GATE_ID,
        "candidate":{"tag":TAG,"commit":COMMIT,"tree":TREE},
        "source":source,
        "caller":{"identity":caller}, "request_id":request_id, "workspace_id":workspace_id,
        "capability_scope":[CAPABILITY],
        "policy":{"authorization_authority":"FA3-AUTH-SECURITY-GOV-001","tool_mediation_authority":"FA3-AUTH-MCP-GATEWAY-001","admission_decision":"ALLOW_EXACT_PROBE_ONLY"},
        "runner":{"hostname":socket.gethostname(),"user":os.environ.get("USER") or os.environ.get("LOGNAME") or "unknown","uid":os.geteuid(),"labels":labels},
        "execution":execution, "probe_output_tail":probe_output, "ci_fixture":False,
        "result_status": PASS_STATUS if error is None else "FAIL", "error":error,
        "promotion":{"global_promotion_claim":False,"provider_remains_optional":True}
    }
    receipt_path.write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
    ok = receipt_valid(receipt, require_real_runner=True)
    print(json.dumps({"result":"PASS" if ok else "FAIL","receipt":str(receipt_path),"status":receipt["result_status"],"error":error}, indent=2))
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
