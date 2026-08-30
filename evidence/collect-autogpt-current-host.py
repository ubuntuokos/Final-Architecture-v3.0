#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_autogpt_provider import (  # noqa: E402
    AutoGPTProvider,
    CAPABILITY,
    PROVIDER_ID,
    REQUEST_SCHEMA,
    STORE_VALUE_BLOCK_ID,
)

COMMIT = "f49bcca95ed327396d8ebdd0bdf7810de482ac1a"
RELEASE = "autogpt-platform-beta-v0.7.3"
RECEIPT_PATH = ROOT / "evidence/receipts/autogpt-current-host.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(*args: str, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, input=input_text, text=True, capture_output=True, check=False)
    if check and proc.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed: {proc.stderr.strip()}")
    return proc


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def podman_json(*args: str) -> Any:
    return json.loads(run("podman", *args, "--format", "json").stdout)


def seed_api_key(rest: str, user_id: str, email: str) -> str:
    script=r'''
import asyncio,json,sys
from backend.data.db import connect,disconnect,prisma
from backend.data.auth.api_key import create_api_key
from prisma.enums import APIKeyPermission,SubscriptionTier
uid,email=sys.argv[1:3]
async def main():
    await connect()
    await prisma.user.delete_many(where={"id":uid})
    await prisma.user.create(data={"id":uid,"email":email,"timezone":"UTC","subscriptionTier":SubscriptionTier.BASIC})
    info,key=await create_api_key(
        name="FA3 current-host narrow E2E",
        user_id=uid,
        permissions=[APIKeyPermission.IDENTITY,APIKeyPermission.READ_BLOCK,APIKeyPermission.EXECUTE_BLOCK],
        description="Ephemeral FA3 AutoGPT current-host E2E credential",
    )
    print(json.dumps({"api_key_id":info.id,"api_key":key}))
    await disconnect()
asyncio.run(main())
'''
    p=run("podman","exec","-i",rest,"python","-",user_id,email,input_text=script)
    data=json.loads(p.stdout.strip().splitlines()[-1])
    key=str(data["api_key"])
    if not key.startswith("agpt_"):
        raise RuntimeError("seeded API key has unexpected format")
    return key


def cleanup_user(rest: str, user_id: str) -> None:
    script=r'''
import asyncio,sys
from backend.data.db import connect,disconnect,prisma
uid=sys.argv[1]
async def main():
    await connect()
    await prisma.user.delete_many(where={"id":uid})
    await disconnect()
asyncio.run(main())
'''
    run("podman","exec","-i",rest,"python","-",user_id,input_text=script,check=False)


def runtime_checks(state: dict[str, Any]) -> dict[str, bool]:
    rest=state["containers"]["rest"]
    info=run("podman","info","--format","{{.Host.Security.Rootless}}").stdout.strip().lower()
    inspect=json.loads(run("podman","inspect",rest).stdout)[0]
    network=json.loads(run("podman","network","inspect",state["network"]).stdout)[0]
    hostconfig=inspect.get("HostConfig",{})
    ports=(inspect.get("NetworkSettings",{}) or {}).get("Ports",{}) or {}
    bindings=[]
    for value in ports.values():
        if isinstance(value,list):
            bindings.extend(value)
    loopback=bool(bindings) and all(str(x.get("HostIp")) in {"127.0.0.1","::1"} for x in bindings)
    security_opts=[str(x).lower() for x in hostconfig.get("SecurityOpt",[]) or []]
    capeff=run("podman","exec",rest,"sh","-c","awk '/CapEff:/ {print $2}' /proc/1/status").stdout.strip()
    gpu_probe=run("podman","exec",rest,"sh","-c","test ! -e /dev/nvidia0 -a ! -e /dev/nvidiactl",check=False)
    egress_probe=run(
        "podman","exec",rest,"python","-c",
        "import socket; s=socket.socket(); s.settimeout(2); s.connect(('1.1.1.1',443))",
        check=False,
    )
    labels=(inspect.get("Config",{}) or {}).get("Labels",{}) or {}
    return {
        "rootless_podman": info=="true",
        "internal_network": network.get("internal") is True,
        "loopback_only_publish": loopback,
        "not_privileged": hostconfig.get("Privileged") is not True,
        "no_new_privileges": any("no-new-privileges" in x for x in security_opts),
        "effective_capabilities_zero": bool(capeff) and int(capeff,16)==0,
        "no_gpu_device_visible": gpu_probe.returncode==0 and not (hostconfig.get("Devices") or []),
        "external_network_egress_denied": egress_probe.returncode != 0,
        "source_commit_label": labels.get("fa3.autogpt.source_commit")==COMMIT,
        "provider_label": labels.get("fa3.provider_id")==PROVIDER_ID,
        "runtime_profile_label": labels.get("fa3.runtime_profile")=="FA3_AUTOGPT_CONSTRAINED_BLOCK_RUNTIME_V1",
    }


def collect(state_path: Path) -> dict[str, Any]:
    if os.environ.get("FA3_CURRENT_HOST_ASSERTION") != "1":
        raise RuntimeError("real current-host assertion is required")
    state=load(state_path)
    if state.get("source_commit") != COMMIT:
        raise RuntimeError("runtime source commit mismatch")
    source=Path(state["source_dir"])
    actual=run("git","-C",str(source),"rev-parse","HEAD").stdout.strip()
    if actual != COMMIT:
        raise RuntimeError("checked-out AutoGPT source is not the admitted commit")
    if run("git","-C",str(source),"status","--porcelain").stdout.strip():
        raise RuntimeError("AutoGPT source checkout is dirty")

    checks=runtime_checks(state)
    failed=[k for k,v in checks.items() if not v]
    if failed:
        raise RuntimeError(f"runtime isolation checks failed: {failed}")
    if not all(str(v).split("@sha256:",1)[-1] != str(v) for v in state.get("repo_digests",{}).values()):
        raise RuntimeError("a runtime dependency was not resolved to an immutable RepoDigest")

    rest=state["containers"]["rest"]
    user_id="fa3-autogpt-e2e-"+uuid.uuid4().hex
    email=f"{user_id}@invalid.local"
    api_key=seed_api_key(rest,user_id,email)
    try:
        provider=AutoGPTProvider(state["base_url"],api_key)
        if not provider.unauthenticated_denied():
            raise RuntimeError("unauthenticated external API request was not denied")
        if not provider.graph_scope_escalation_denied():
            raise RuntimeError("narrow API key could access EXECUTE_GRAPH")
        blocks=provider.listed_block_ids()
        if STORE_VALUE_BLOCK_ID not in blocks:
            raise RuntimeError("admitted StoreValueBlock is not available in real AutoGPT runtime")

        nonce="fa3-autogpt-current-host-"+uuid.uuid4().hex
        request={
            "schema":REQUEST_SCHEMA,
            "request_id":"req-"+uuid.uuid4().hex,
            "caller_identity":"fa3-current-host-conformance-principal",
            "delegation_id":"delegation-"+uuid.uuid4().hex,
            "workflow_run_id":os.environ.get("GITHUB_RUN_ID") or "local-current-host-"+uuid.uuid4().hex,
            "capability_id":"CAP-028",
            "provider_id":PROVIDER_ID,
            "block_id":STORE_VALUE_BLOCK_ID,
            "authorization_decision":{
                "authority":"FA3-AUTH-SECURITY-GOV-001",
                "decision":"ALLOW",
                "decision_id":"policy-"+uuid.uuid4().hex,
                "capabilities":[CAPABILITY],
                "evidence_scope":"CURRENT_HOST_CONFORMANCE_HARNESS",
            },
            "mcp_admission":{
                "authority":"FA3-AUTH-MCP-GATEWAY-001",
                "decision":"ALLOW",
                "admission_id":"mcp-"+uuid.uuid4().hex,
                "capability":CAPABILITY,
                "evidence_scope":"FA3_ADAPTER_ENFORCED_EXTERNAL_ADMISSION_CONTEXT",
            },
            "host_resource_admission":{
                "authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001",
                "decision":"ALLOW",
                "admission_id":"hrb-"+uuid.uuid4().hex,
                "resource_class":"CPU_RAM_ONLY",
                "accelerator_lease_id":"NONE_REQUIRED",
                "bounded_runtime":{"cpus":8,"memory_bytes":12884901888,"pids_limit":2048},
                "evidence_scope":"FA3_ADAPTER_ENFORCED_CPU_RAM_ADMISSION_CONTEXT",
            },
            "input":{"input":nonce},
            "timeout_seconds":20,
            "network_egress_allowed":False,
        }
        result=provider.execute(request)
        if result.get("output",{}).get("output") != [nonce]:
            raise RuntimeError("real AutoGPT output mismatch")
    finally:
        cleanup_user(rest,user_id)

    run_id=f"autogpt-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    runtime_dir=ROOT/"evidence/runtime/autogpt-current-host"/run_id
    runtime_dir.mkdir(parents=True,exist_ok=False)
    sanitized_state={k:v for k,v in state.items() if k not in {"source_dir"}}
    write(runtime_dir/"runtime-state.json",sanitized_state)
    write(runtime_dir/"provider-result.json",result)
    receipt={
        "schema":"fa3.autogpt-current-host-receipt.v1",
        "provider_id":PROVIDER_ID,
        "capability_id":"CAP-028",
        "contract_id":"FA3-AUTOGPT-CONTRACTS-001",
        "runtime_conformance_id":"FA3-AUTOGPT-RUNTIME-CONFORMANCE-001",
        "status":"PROVISIONAL_RUNTIME_PASS",
        "evidence_level":"CURRENT_HOST_RUNTIME_ACTIVE_E2E_PASS_PENDING_CLEANUP",
        "synthetic":False,
        "collector_mode":"REAL_CURRENT_HOST_ROOTLESS_AUTOGPT_SERVICE",
        "run_id":run_id,
        "started_at":state.get("started_at"),
        "active_e2e_completed_at":now(),
        "host":{
            "hostname":socket.gethostname(),
            "platform":platform.platform(),
            "machine":platform.machine(),
            "effective_uid":os.geteuid(),
            "github_run_id":os.environ.get("GITHUB_RUN_ID"),
            "github_runner_name":os.environ.get("RUNNER_NAME"),
        },
        "upstream":{"release":RELEASE,"source_commit":COMMIT,"poetry_lock_sha256":state.get("poetry_lock_sha256")},
        "runtime_identity":{
            "repo_digests":state.get("repo_digests"),
            "image_ids":state.get("image_ids"),
            "server_tag":state.get("server_tag"),
        },
        "isolation":checks,
        "authorization":{
            "autogpt_api_key_permissions":["IDENTITY","READ_BLOCK","EXECUTE_BLOCK"],
            "execute_graph_permission_absent":True,
            "unauthenticated_request_denied":True,
            "scope_escalation_denied":True,
            "api_key_redacted":True,
            "fa3_security_context_enforced_by_adapter":True,
            "central_mcp_context_enforced_by_adapter":True,
            "host_resource_context_enforced_by_adapter":True,
            "actual_central_gateway_network_hop_claimed":False,
        },
        "execution":{
            "block_id":STORE_VALUE_BLOCK_ID,
            "block_type":"StoreValueBlock",
            "real_autogpt_external_api":True,
            "deterministic_result":"PASS",
            "input_digest":result["input_digest"],
            "output_digest":result["output_digest"],
            "provider_http_status":result["provider_http_status"],
            "caller_identity":result["caller_identity"],
            "delegation_id":result["delegation_id"],
            "workflow_run_id":result["workflow_run_id"],
            "authorization_decision_id":result["authorization_decision_id"],
            "mcp_admission_id":result["mcp_admission_id"],
            "host_resource_admission_id":result["host_resource_admission_id"],
        },
        "cleanup":{"verified":False,"status":"PENDING"},
        "current_host_production_e2e":"PENDING_CLEANUP",
        "global_promotion_claim":False,
        "new_capabilities":0,
        "new_architectural_authorities":0,
        "capability_count_after":143,
    }
    write(RECEIPT_PATH,receipt)
    print(json.dumps(receipt,ensure_ascii=False,indent=2))
    return receipt


def finalize_cleanup(state_path: Path) -> dict[str, Any]:
    if not RECEIPT_PATH.is_file():
        raise RuntimeError("provisional receipt is missing")
    receipt=load(RECEIPT_PATH)
    state=load(state_path)
    names=[state["containers"]["rest"],state["containers"]["rabbitmq"],*state["containers"]["redis"],state["containers"]["db"]]
    alive=[]
    for name in names:
        p=run("podman","container","exists",name,check=False)
        if p.returncode==0:
            alive.append(name)
    network_exists=run("podman","network","exists",state["network"],check=False).returncode==0
    port_probe=run("python3","-c","import socket; s=socket.socket(); s.settimeout(0.5); raise SystemExit(0 if s.connect_ex(('127.0.0.1',58006))!=0 else 1)",check=False)
    cleanup_ok=not alive and not network_exists and port_probe.returncode==0
    receipt["cleanup"]={
        "verified":cleanup_ok,
        "status":"PASS" if cleanup_ok else "FAIL",
        "resident_containers":alive,
        "internal_network_exists":network_exists,
        "loopback_port_closed":port_probe.returncode==0,
        "verified_at":now(),
    }
    if not cleanup_ok:
        receipt["status"]="FAIL"
        receipt["evidence_level"]="CURRENT_HOST_PRODUCTION_E2E_FAIL"
        receipt["current_host_production_e2e"]="FAIL"
        write(RECEIPT_PATH,receipt)
        raise RuntimeError(f"AutoGPT cleanup verification failed: {receipt['cleanup']}")
    receipt["status"]="PASS"
    receipt["evidence_level"]="CURRENT_HOST_PRODUCTION_E2E_PASS"
    receipt["current_host_production_e2e"]="PASS"
    receipt["completed_at"]=now()
    write(RECEIPT_PATH,receipt)
    print(json.dumps(receipt,ensure_ascii=False,indent=2))
    return receipt


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--state-file",required=True)
    ap.add_argument("--finalize-cleanup",action="store_true")
    args=ap.parse_args()
    state=Path(args.state_file).resolve()
    if args.finalize_cleanup:
        finalize_cleanup(state)
    else:
        collect(state)
    return 0


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"AUTOGPT CURRENT-HOST EVIDENCE FAILED: {exc}",file=sys.stderr)
        raise SystemExit(2)
