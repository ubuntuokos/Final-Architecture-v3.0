#!/usr/bin/env python3
"""Read-only FA3 donor integrity and GitHub pending-maintenance preflight."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import urllib.request
from pathlib import Path

REGISTRY = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
REPO = "ubuntuokos/Final-Architecture-v3.0"
FLAGS = ("authority","automatic_selection","automatic_fetch","automatic_install",
         "automatic_activation","automatic_dependency","automatic_code_import",
         "automatic_provider_admission","automatic_model_selection")
STATES = {"CANDIDATE","ANALYZED","ACCEPTED_REFERENCE","REJECTED","SUPERSEDED"}
DONOR_FILES = {REGISTRY,"src/fa3_donor_registry.py","src/fa3_donor_chat_import.py",
               "src/fa3_donor_chat_inbox.py","src/fa3_donor_readiness.py",
               ".github/workflows/fa3-donor-serialization.yml"}
DONOR_PREFIXES = ("docs/donor-repair/","bin/fa3-donor-","tests/test_donor_")

def inspect_registry(root):
    raw = (root / REGISTRY).read_bytes()
    reg = json.loads(raw)
    if not isinstance(reg,dict) or not isinstance(reg.get("entries"),list):
        raise ValueError("REGISTRY_NOT_OBJECT_WITH_ENTRIES")
    rows = reg["entries"]
    problems = []
    if reg.get("id") != "FA3-DONOR-REFERENCE-REGISTRY-001":
        problems.append("REGISTRY_ID_INVALID")
    if reg.get("capability_count") != 175:
        problems.append("CAPABILITY_BASELINE_NOT_175")
    if reg.get("backfill",{}).get("entry_count") != len(rows):
        problems.append("BACKFILL_COUNT_DRIFT")
    ids, keys, aliases = set(), set(), set()
    for i,row in enumerate(rows):
        if not isinstance(row,dict):
            problems.append("NON_OBJECT_ENTRY:"+str(i))
            continue
        did = row.get("donor_id")
        src = row.get("source")
        key = src.get("normalized_key") if isinstance(src,dict) else None
        if not isinstance(did,str) or not did or did in ids:
            problems.append("DONOR_ID_INVALID_OR_DUPLICATE:"+str(i))
        else: ids.add(did)
        if not isinstance(key,str) or not key or key in keys:
            problems.append("SOURCE_KEY_INVALID_OR_DUPLICATE:"+str(i))
        else: keys.add(key)
        if row.get("status") not in STATES:
            problems.append("INVALID_STATUS:"+str(i))
        if any(row.get(flag) is not False for flag in FLAGS):
            problems.append("FORBIDDEN_ADMISSION_FLAG:"+str(i))
        for alias in row.get("legacy_source_keys",[]):
            if not isinstance(alias,str) or not alias or alias==key or alias in aliases:
                problems.append("INVALID_LEGACY_ALIAS:"+str(i))
            else: aliases.add(alias)
    if keys & aliases: problems.append("LEGACY_ALIAS_COLLIDES_WITH_PRIMARY")
    return {"registry":reg,"sha256":hashlib.sha256(raw).hexdigest(),
            "count":len(rows),"findings":sorted(set(problems))}

def git_blob_sha(raw):
    """GitHub's contents API exposes the blob SHA even for files above 1 MiB."""
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\\0" + raw).hexdigest()

def github_get(url,token):
    if not token: raise RuntimeError("GITHUB_TOKEN_REQUIRED")
    req=urllib.request.Request("https://api.github.com"+url,
        headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
                 "X-GitHub-Api-Version":"2022-11-28","User-Agent":"fa3-donor-readiness"})
    with urllib.request.urlopen(req,timeout=20) as r: return json.load(r)

def is_donor_pr(pr,files):
    title=str(pr.get("title","")).lower()
    if "donor" in title: return True
    for f in files:
        name=f.get("filename")
        if not isinstance(name,str): raise ValueError("UNREADABLE_PR_FILE")
        if name in DONOR_FILES or any(name.startswith(p) for p in DONOR_PREFIXES):
            return True
    return False

def pending_prs(get,repo=REPO):
    if repo!=REPO: raise ValueError("UNEXPECTED_REPOSITORY")
    found=[]
    for page in range(1,21):
        prs=get(f"/repos/{repo}/pulls?state=open&per_page=100&page={page}")
        if not isinstance(prs,list) or len(prs)>100: raise ValueError("INCOMPLETE_PR_LIST")
        for pr in prs:
            n=pr["number"]
            files=[]
            for fp in range(1,101):
                part=get(f"/repos/{repo}/pulls/{n}/files?per_page=100&page={fp}")
                if not isinstance(part,list) or len(part)>100:
                    raise ValueError("INCOMPLETE_PR_FILE_LIST:"+str(n))
                files.extend(part)
                if len(part)<100: break
            else: raise ValueError("TOO_MANY_PR_FILES:"+str(n))
            if is_donor_pr(pr,files):
                found.append({"number":n,"title":pr.get("title"),
                              "head_sha":pr.get("head",{}).get("sha")})
        if len(prs)<100: return sorted(found,key=lambda p:p["number"])
    raise ValueError("TOO_MANY_OPEN_PRS")

def committed(root,rel):
    path=Path(rel)
    if (path.is_absolute() or ".." in path.parts or path.as_posix()!=rel or
            not path.parts or path.parts[0] not in ("canonical","docs")):
        raise ValueError("INVALID_COMMITTED_PATH")
    p=root/path
    if p.is_symlink() or not p.is_file(): raise ValueError("COMMITTED_SOURCE_UNAVAILABLE")
    raw=p.read_bytes()
    result=subprocess.run(["git","-C",str(root),"show","HEAD:"+rel],
                          capture_output=True,check=False)
    if result.returncode or result.stdout!=raw:
        raise ValueError("DIRTY_OR_NONCOMMITTED_SOURCE")
    return raw

def assessment_findings(root,path,sha,reg):
    if not path:return ["DONOR_ASSESSMENT_REQUIRED"]
    row=json.loads(committed(root,path))
    findings=[]
    if (row.get("donor_registry_id")!=reg["id"] or
            row.get("donor_registry_sha256")!=sha):
        findings.append("REUSE_ASSESSMENT_REGISTRY_SNAPSHOT_MISMATCH")
    if row.get("donor_review") not in ("REVIEWED_MATCH","REVIEWED_NO_MATCH"):
        findings.append("DONOR_REVIEW_REQUIRED")
    all_ids={e["donor_id"] for e in reg["entries"]}
    adoptions=row.get("adopted_donors",[])
    if not isinstance(adoptions,list): return findings+["INVALID_DONOR_ADOPTIONS"]
    for a in adoptions:
        ref=a.get("approval_ref") if isinstance(a,dict) else None
        if (not isinstance(a,dict) or a.get("donor_id") not in all_ids or
                a.get("decision")!="EXPLICITLY_APPROVED" or
                a.get("mode") not in ("REFERENCE_ONLY","APPROVED_CAPABILITY_PATTERN") or
                not isinstance(ref,str) or not ref.startswith("canonical/decisions/")):
            findings.append("UNAUTHORIZED_DONOR_ADOPTION")
            continue
        decision=json.loads(committed(root,ref))
        if (decision.get("donor_id")!=a["donor_id"] or decision.get("status")!="APPROVED"
                or decision.get("explicit_user_approval") is not True):
            findings.append("INVALID_DONOR_APPROVAL")
    return findings

def plan_findings(root,plan,approval,pr_number,repo,get):
    if not plan or not approval or not pr_number:
        return ["IMMUTABLE_APPROVED_PLAN_AND_EXACT_HEAD_REVIEW_REQUIRED"]
    raw=committed(root,plan)
    decision=json.loads(committed(root,approval))
    if (not approval.startswith("canonical/decisions/") or
            decision.get("status")!="APPROVED" or
            decision.get("explicit_user_approval") is not True or
            decision.get("approved_plan_sha256")!=hashlib.sha256(raw).hexdigest() or
            not decision.get("user_request_ref")):
        return ["EXPLICIT_APPROVED_PLAN_NOT_PROVEN"]
    remote=get(f"/repos/{repo}/pulls/{pr_number}")
    head=remote["head"]["sha"]
    local=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    if head!=local:return ["APPROVED_PR_HEAD_MISMATCH"]
    reviews=get(f"/repos/{repo}/pulls/{pr_number}/reviews?per_page=100")
    owner=repo.split("/")[0].lower()
    if not isinstance(reviews,list) or len(reviews)>=100 or not any(
            r.get("user",{}).get("login","").lower()==owner and
            r.get("state")=="APPROVED" and r.get("commit_id")==head for r in reviews):
        return ["EXPLICIT_OWNER_APPROVAL_ON_EXACT_HEAD_REQUIRED"]
    return []

def gate(root,phase="status",token="",assessment=None,plan=None,approval=None,
         pr_number=None,get=None):
    result={"schema":"fa3.donor-readiness.v1","phase":phase,
            "result":"BLOCKED","planning_allowed":False,"execution_allowed":False,
            "finalization_allowed":False,"automatic_donor_adoption":False,
            "pending_prs":None,"findings":[]}
    try:
        inspect=inspect_registry(root)
        result.update({"registry_integrity":"PASS" if not inspect["findings"] else "FAIL",
                       "registry_sha256":inspect["sha256"],"donor_count":inspect["count"],
                       "capability_baseline":inspect["registry"].get("capability_count")})
        result["findings"].extend(inspect["findings"])
        if result["findings"]:return result
        if phase=="maintenance":
            result["result"]="MAINTENANCE_INTEGRITY_PASS"
            result["findings"].append("MAINTENANCE_ONLY_NOT_PLANNING_READY")
            return result
        if not token and get is None:raise RuntimeError("LIVE_GITHUB_TOKEN_REQUIRED")
        getter=get if get is not None else lambda p:github_get(p,token)
        before=getter(f"/repos/{REPO}/branches/main")["commit"]["sha"]
        result["pending_prs"]=pending_prs(getter)
        after=getter(f"/repos/{REPO}/branches/main")["commit"]["sha"]
        if before!=after:result["findings"].append("MAIN_MOVED_DURING_SCAN")
        if result["pending_prs"]:result["findings"].append("PENDING_DONOR_MAINTENANCE")
        if result["findings"]:return result
        # A locally coherent but stale branch must never authorize planning after
        # a newer canonical main registry is published. Fetch the blob identity
        # at the exact main SHA observed during the live pending-PR scan.
        remote=getter(f"/repos/{REPO}/contents/{REGISTRY}?ref={after}")
        if (not isinstance(remote,dict) or not isinstance(remote.get("sha"),str)
                or len(remote["sha"]) != 40):
            raise ValueError("CANONICAL_MAIN_REGISTRY_BLOB_UNAVAILABLE")
        local=git_blob_sha((root / REGISTRY).read_bytes())
        result["main_registry_blob_sha"]=remote["sha"]
        if local != remote["sha"]:
            result["findings"].append("STALE_CANONICAL_DONOR_SNAPSHOT")
            return result
        if phase in ("entry","finalize"):
            result["findings"].extend(assessment_findings(
                root,assessment,inspect["sha256"],inspect["registry"]))
        if phase=="finalize" and not result["findings"]:
            result["findings"].extend(plan_findings(
                root,plan,approval,pr_number,REPO,getter))
        if result["findings"]:return result
        result["result"]="READY_FOR_SEPARATE_FA3_ADMISSION_GATES"
        result["planning_allowed"]=phase in ("entry","finalize")
        result["execution_allowed"]=phase in ("entry","finalize")
        result["finalization_allowed"]=phase=="finalize"
        return result
    except (OSError,ValueError,RuntimeError,KeyError,TypeError,subprocess.CalledProcessError) as e:
        result["findings"].append("PROOF_UNAVAILABLE:"+type(e).__name__)
        return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    p.add_argument("--phase",choices=("maintenance","status","entry","finalize"),default="status")
    p.add_argument("--assessment")
    p.add_argument("--plan")
    p.add_argument("--approval")
    p.add_argument("--pr",type=int)
    a=p.parse_args()
    x=gate(Path(a.root).resolve(),a.phase,os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN",""),
           a.assessment,a.plan,a.approval,a.pr)
    print(json.dumps(x,ensure_ascii=False,indent=2))
    return 0 if x["result"] in ("MAINTENANCE_INTEGRITY_PASS",
                                 "READY_FOR_SEPARATE_FA3_ADMISSION_GATES") else 2
if __name__=="__main__":raise SystemExit(main())
