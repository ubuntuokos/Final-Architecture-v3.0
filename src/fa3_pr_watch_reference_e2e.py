#!/usr/bin/env python3
"""Synthetic signed PR event -> existing FA3 isolated workers -> separate checker.

This has no code path accepting outside repositories, user source trees or
runtime tokens, and must not be mistaken for provider/current-host admission.
"""
import argparse
import hashlib
import hmac
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from fa3_pr_watch import ProjectionStore, normalize_webhook
from fa3_developer_agent_coordination import (AgentTask,Coordinator,
    BuiltinDeterministicAdapter,FIXTURE_PROVIDER_ID,_init_fixture_repo,cleanup_state_valid)
from fa3_pr_watch_reference_checker import EXPECTED


def fixture_e2e():
    with tempfile.TemporaryDirectory(prefix="fa3-pr-watch-ci-") as td:
        root=Path(td);repo=root/"synthetic"
        _init_fixture_repo(repo,{p:"baseline\n" for p in EXPECTED})
        def sha():
            return subprocess.run(["git","-C",str(repo),"rev-parse","HEAD"],
                    check=True,capture_output=True,text=True).stdout.strip()
        base=sha()
        body=json.dumps({"action":"opened","repository":{"full_name":"fa3/reference-fixture"},
            "sender":{"login":"reference-only"},
            "pull_request":{"number":1,"updated_at":"2026-09-28T12:00:00Z",
                "head":{"sha":base},"base":{"sha":base},"title":"synthetic fixture"}},
            sort_keys=True).encode()
        ephemeral_secret=b"ci-reference-secret-never-production-000"
        event=normalize_webhook(body,signature="sha256="+hmac.new(
            ephemeral_secret,body,hashlib.sha256).hexdigest(),
            secret=ephemeral_secret,event_type="pull_request",delivery_id="synthetic-0001")
        store=ProjectionStore(root/"local-cache")
        accepted=store.ingest(event)
        item=store.operator_projection()["items"][0]
        if accepted["status"]!="INGESTED" or item["head_sha"]!=base or event["action_authorized"]:
            raise ValueError("UNTRUSTED_OR_STALE_SOURCE")
        tasks=[AgentTask("FIXTURE-"+str(i), "reference-agent-"+str(i),
                FIXTURE_PROVIDER_ID,path,content.decode())
                for i,(path,content) in enumerate(EXPECTED.items())]
        run=Coordinator(repo,root/"existing-agent-control").run(tasks,BuiltinDeterministicAdapter())
        head=sha()
        if run.get("status")!="PASS" or head!=run["integration_commit"] or not cleanup_state_valid(**run["cleanup"]):
            raise ValueError("WORKER_OR_CLEANUP_FAILED")
        checker=Path(__file__).with_name("fa3_pr_watch_reference_checker.py")
        cp=subprocess.run([sys.executable,str(checker),"--repo",str(repo),
            "--base",base,"--head",head,"--event-digest",event["payload_sha256"]],
            text=True,capture_output=True,timeout=30,check=False,
            env={"PATH":os.environ.get("PATH",""),"PYTHONIOENCODING":"utf-8"})
        if cp.returncode:
            raise ValueError("INDEPENDENT_CHECK_FAILED")
        verified=json.loads(cp.stdout)
        if verified["status"]!="PASS" or verified["canonical_evidence_verified"]:
            raise ValueError("INDEPENDENT_CHECK_INCOMPLETE")
        return {"schema":"fa3.pr-watch-synthetic-e2e.v1",
            "status":"CI_REFERENCE_PASS_NOT_PRODUCTION",
            "signed_event_digest":event["payload_sha256"],
            "source_sha":base,"integration_sha":head,"worker_count":run["worker_count"],
            "existing_developer_coordination":True,"separate_checker_process":True,
            "checker":verified,"cleanup":run["cleanup"],
            "external_repository_executed":False,
            "real_provider_or_model_run":False,
            "canonical_evidence_verified":False,
            "current_host_production_admitted":False,
            "global_promotion_claim":False}


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--fixture-only",action="store_true",required=True)
    p.add_argument("--output",type=Path)
    a=p.parse_args(argv)
    try:
        result=fixture_e2e()
        if a.output:
            a.output.parent.mkdir(parents=True,exist_ok=True)
            a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
        else:
            print(json.dumps(result,sort_keys=True))
        return 0
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError):
        print(json.dumps({"status":"FAIL","scope":"CI_REFERENCE_ONLY"}),file=sys.stderr)
        return 2


if __name__=="__main__":raise SystemExit(main())
