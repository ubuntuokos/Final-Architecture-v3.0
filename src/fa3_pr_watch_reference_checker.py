#!/usr/bin/env python3
"""Separate-process checker for synthetic PR Watch CI; never a canonical PASS."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

EXPECTED={"work/feature.txt":b"feature result\n","work/tests.txt":b"independent test result\n"}


def verify_fixture(repo:Path,base:str,head:str,event_digest:str)->dict:
    failures=[]
    if not all(re.fullmatch(r"[0-9a-f]{40}",v or "") for v in (base,head)):
        failures.append("SHA_INVALID")
    if not re.fullmatch(r"[0-9a-f]{64}",event_digest or ""):
        failures.append("EVENT_DIGEST_INVALID")
    if not Path(repo).is_dir() or (Path(repo)/".git").is_symlink():
        failures.append("REPO_INVALID")
    if not failures:
        def git(*args):
            p=subprocess.run(["git","-C",str(repo),*args],text=True,capture_output=True,check=False)
            if p.returncode: raise ValueError("GIT_FAILED")
            return p.stdout.strip()
        try:
            if git("rev-parse","HEAD")!=head or git("rev-parse","HEAD^")!=base:
                failures.append("SOURCE_SHA_DRIFT")
            changed=git("diff","--name-only",base,head).splitlines()
            if len(changed)!=len(EXPECTED) or set(changed)!=set(EXPECTED):
                failures.append("PATH_SCOPE_DRIFT")
            if git("show","-s","--format=%s",head)!="FA3 reference multi-agent integration":
                failures.append("UNTRUSTED_INTEGRATION_AUTHORSHIP")
            for path,expected in EXPECTED.items():
                target=Path(repo)/path
                if target.is_symlink() or not target.is_file() or target.read_bytes()!=expected:
                    failures.append("ARTIFACT_MISMATCH")
            if git("status","--porcelain","--untracked-files=all"):
                failures.append("WORKTREE_NOT_CLEAN")
        except (ValueError,OSError,subprocess.SubprocessError):
            failures.append("GIT_OR_FILE_VERIFICATION_FAILED")
    return {"schema":"fa3.pr-watch-reference-verification.v1",
            "status":"PASS" if not failures else "FAIL","failures":failures,
            "source_sha":base,"integration_sha":head,"signed_event_payload_sha256":event_digest,
            "expected_digests":{p:hashlib.sha256(v).hexdigest() for p,v in EXPECTED.items()},
            "scope":"ISOLATED_CI_SYNTHETIC_REFERENCE_ONLY","canonical_evidence_verified":False,
            "current_host_production_admitted":False}


def main():
    p=argparse.ArgumentParser()
    for name in ("repo","base","head","event-digest"):p.add_argument("--"+name,required=True)
    a=p.parse_args()
    result=verify_fixture(Path(a.repo),a.base,a.head,a.event_digest)
    print(json.dumps(result,sort_keys=True))
    return 0 if result["status"]=="PASS" else 2


if __name__=="__main__": raise SystemExit(main())
