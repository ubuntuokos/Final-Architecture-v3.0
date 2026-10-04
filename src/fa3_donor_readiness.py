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
REJECTION_AUDIT = "canonical/FA3-DONOR-REJECTION-AUDIT-001.json"
LIFECYCLE_DECISION = "canonical/decisions/FA3-DEC-DONOR-LIFECYCLE-APPLICATION-SYNC-2026-09-30.json"
REPO = "ubuntuokos/Final-Architecture-v3.0"
FLAGS = ("authority","automatic_selection","automatic_fetch","automatic_install",
         "automatic_activation","automatic_dependency","automatic_code_import",
         "automatic_provider_admission","automatic_model_selection")
STATES = {"CANDIDATE","ANALYZED","ACCEPTED_REFERENCE","SUPERSEDED"}
DONOR_FILES = {REGISTRY, REJECTION_AUDIT, LIFECYCLE_DECISION,
               "canonical/FA3-APPLICATION-DONOR-LINKS-001.json",
               "docs/donor-reference-registry.md",
               "src/fa3_donor_registry.py", "src/fa3_donor_chat_import.py",
               "src/fa3_donor_chat_inbox.py", "src/fa3_donor_readiness.py",
               "src/fa3_application_donor_index.py",
               ".github/workflows/fa3-donor-serialization.yml",
               '.github/workflows/fa3-permanent-enforcement.yml',
               ".github/workflows/fa3-application-donor-inventory.yml",
               "tests/test_application_donor_index.py"}
EXEMPT_HISTORICAL_PRS = frozenset({24, 31, 52, 70, 71, 125, 180, 181, 245, 252, 392, 427, 434, 438})
# Explicit owner decision: these closed historical PRs require no retrospective donor extraction.
# Exemption is limited to the specified immutable PR heads; new changes are not exempt.
EXEMPT_HISTORICAL_HEADS = {
    24: "d7bc56979023ca9de88b940cfbb188d9fbb99f4c",
    31: "4f84fe805f0a78bac8b92f2ac3a35801b2cf3e32",
    52: "fdc39a619b24d0491ae1ff928d476fe14f143320",
    70: "31fdd4d2ee90ca386cf7d0dedc2c3b125f613360",
    71: "b61fbfbfed7939e788cfbcfc52fbb50c51303c34",
    125: "85d592c74bd10923bcc86eef1453e412b63e1d84",
    180: "3fa35c7b904f6a00ee44fd06ddb5a69da3721b81",
    181: "3fa35c7b904f6a00ee44fd06ddb5a69da3721b81",
    245: "8d63c3a04884563d8b56e7951bffbe7681506895",
    252: "f76f1c1d379dcdd230d0771561be29599f504fda",
    392: "70b0e4cde4412b3c5c26f8435158690869829cbb",
    427: "e6119ce6c8aecd2359c89bf7ee23d7e75a5ee9fa",
    434: "4062b5ed7cd59bb17bf09fabc4e3238a79a4290f",
    438: "da51f27ca8f0c967e7c1e6d791da4fb12b4f768c",
}
DONOR_DELTA_PREFIXES = ("canonical/deltas/FA3-DONOR-",
                        "canonical/deltas/CFA3-DONOR-")
DONOR_PREFIXES = ("docs/donor-repair/", "docs/donor-", "docs/donors-",
                  "bin/fa3-donor-", "tests/test_donor_", "tests/test_donors_",
                  *DONOR_DELTA_PREFIXES)
MAX_ACTIVE_DONOR_INTAKES = 5
MAX_ACTIVE_CANONICAL_REGISTRY_MUTATION_PRS = 1
MAX_GITHUB_PR_FILES = 3000

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

    audit_path = root / REJECTION_AUDIT
    if not audit_path.is_file():
        problems.append("REJECTION_AUDIT_MISSING")
        audit = {"entries": []}
    else:
        try:
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            audit = {"entries": []}
            problems.append("REJECTION_AUDIT_INVALID")
    if audit.get("id") != "FA3-DONOR-REJECTION-AUDIT-001" or not isinstance(audit.get("entries"), list):
        problems.append("REJECTION_AUDIT_SCHEMA_INVALID")
    active_by_key = {
        row.get("source", {}).get("normalized_key"): row
        for row in rows if isinstance(row, dict) and isinstance(row.get("source"), dict)
    }
    audited_keys = set()
    for i, item in enumerate(audit.get("entries", [])):
        donor = item.get("donor") if isinstance(item, dict) else None
        key = donor.get("source", {}).get("normalized_key") if isinstance(donor, dict) else None
        if not isinstance(key, str) or not key or key in audited_keys:
            problems.append("REJECTION_AUDIT_SOURCE_INVALID_OR_DUPLICATE:"+str(i))
            continue
        audited_keys.add(key)
        active = active_by_key.get(key)
        if active is None:
            continue
        proof = active.get("security_reentry_evidence")
        refs = proof.get("evidence_refs") if isinstance(proof, dict) else None
        if (not isinstance(proof, dict) or proof.get("status") != "VERIFIED_SAFE"
                or not isinstance(refs, list) or not refs
                or active.get("code_reuse_policy") == "FORBIDDEN"):
            problems.append("REJECTED_DONOR_REENTRY_WITHOUT_VERIFIED_SAFE_EVIDENCE:"+key)
    return {"registry":reg,"sha256":hashlib.sha256(raw).hexdigest(),
            "count":len(rows),"rejection_audit_count":len(audit.get("entries", [])),
            "findings":sorted(set(problems))}

def git_blob_sha(raw):
    """GitHub's contents API exposes the blob SHA even for files above 1 MiB."""
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

def github_get(url,token):
    if not token: raise RuntimeError("GITHUB_TOKEN_REQUIRED")
    req=urllib.request.Request("https://api.github.com"+url,
        headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
                 "X-GitHub-Api-Version":"2022-11-28","User-Agent":"fa3-donor-readiness"})
    with urllib.request.urlopen(req,timeout=20) as r: return json.load(r)

_OPEN_PRS_QUERY = """query($owner:String!,$name:String!,$after:String){
  repository(owner:$owner,name:$name){
    pullRequests(states:[OPEN],first:100,after:$after){
      pageInfo{hasNextPage endCursor}
      nodes{
        number title headRefOid headRefName
        headRepository{nameWithOwner}
        files(first:100){
          totalCount
          pageInfo{hasNextPage endCursor}
          nodes{path additions deletions}
        }
      }
    }
  }
}"""

_MORE_PR_FILES_QUERY = """query($owner:String!,$name:String!,$number:Int!,$after:String){
  repository(owner:$owner,name:$name){
    pullRequest(number:$number){
      files(first:100,after:$after){
        totalCount
        pageInfo{hasNextPage endCursor}
        nodes{path additions deletions}
      }
    }
  }
}"""

def github_graphql(query,variables,token):
    if not token: raise RuntimeError("GITHUB_TOKEN_REQUIRED")
    payload=json.dumps({"query":query,"variables":variables}).encode("utf-8")
    req=urllib.request.Request("https://api.github.com/graphql",data=payload,method="POST",
        headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
                 "Content-Type":"application/json","User-Agent":"fa3-donor-readiness"})
    with urllib.request.urlopen(req,timeout=30) as r:
        body=json.load(r)
    if not isinstance(body,dict) or body.get("errors"):
        raise RuntimeError("GITHUB_GRAPHQL_PROOF_FAILED")
    data=body.get("data")
    if not isinstance(data,dict):
        raise RuntimeError("GITHUB_GRAPHQL_PROOF_INVALID")
    return data

def _graphql_file_rows(conn,pr_number):
    if not isinstance(conn,dict):
        raise ValueError("INCOMPLETE_PR_FILE_LIST:"+str(pr_number))
    total=conn.get("totalCount")
    if not isinstance(total,int) or total < 0:
        raise ValueError("INCOMPLETE_PR_FILE_LIST:"+str(pr_number))
    if total >= MAX_GITHUB_PR_FILES:
        raise ValueError("PR_FILE_LIST_AT_GITHUB_API_CAP:"+str(pr_number))
    nodes=conn.get("nodes")
    if not isinstance(nodes,list):
        raise ValueError("INCOMPLETE_PR_FILE_LIST:"+str(pr_number))
    rows=[]
    for node in nodes:
        if not isinstance(node,dict) or not isinstance(node.get("path"),str):
            raise ValueError("UNREADABLE_PR_FILE")
        additions=node.get("additions")
        deletions=node.get("deletions")
        if not isinstance(additions,int) or additions < 0 or not isinstance(deletions,int) or deletions < 0:
            raise ValueError("UNREADABLE_PR_FILE")
        rows.append({"filename":node["path"],"additions":additions,
                     "deletions":deletions,"changes":additions+deletions})
    return rows

def pending_prs_graphql(token,repo=REPO,graphql=None,get=None):
    """Batch the live open-PR inventory to avoid REST N+1 rate-limit failures.

    File paths and mutation sizes come from GraphQL in one connection scan.
    Exact head/main blob identity for canonical donor mutations is still proven
    separately through the Contents API, preserving stale-base fail-closed
    semantics without fetching every file page for every open PR.
    """
    if repo!=REPO: raise ValueError("UNEXPECTED_REPOSITORY")
    owner,name=repo.split("/",1)
    gql=graphql if graphql is not None else lambda q,v:github_graphql(q,v,token)
    rest=get if get is not None else lambda p:github_get(p,token)
    found=[]
    after=None
    while True:
        data=gql(_OPEN_PRS_QUERY,{"owner":owner,"name":name,"after":after})
        repository=data.get("repository") if isinstance(data,dict) else None
        conn=repository.get("pullRequests") if isinstance(repository,dict) else None
        if not isinstance(conn,dict) or not isinstance(conn.get("nodes"),list):
            raise ValueError("INCOMPLETE_PR_LIST")
        for node in conn["nodes"]:
            if not isinstance(node,dict) or not isinstance(node.get("number"),int):
                raise ValueError("INCOMPLETE_PR_LIST")
            n=node["number"]
            file_conn=node.get("files")
            files=_graphql_file_rows(file_conn,n)
            page=file_conn.get("pageInfo") if isinstance(file_conn,dict) else None
            if not isinstance(page,dict):
                raise ValueError("INCOMPLETE_PR_FILE_LIST:"+str(n))
            file_after=page.get("endCursor")
            has_more=page.get("hasNextPage") is True
            while has_more:
                more=gql(_MORE_PR_FILES_QUERY,
                         {"owner":owner,"name":name,"number":n,"after":file_after})
                rep=more.get("repository") if isinstance(more,dict) else None
                pr=rep.get("pullRequest") if isinstance(rep,dict) else None
                next_conn=pr.get("files") if isinstance(pr,dict) else None
                files.extend(_graphql_file_rows(next_conn,n))
                if len(files)>=MAX_GITHUB_PR_FILES:
                    raise ValueError("PR_FILE_LIST_AT_GITHUB_API_CAP:"+str(n))
                next_page=next_conn.get("pageInfo") if isinstance(next_conn,dict) else None
                if not isinstance(next_page,dict):
                    raise ValueError("INCOMPLETE_PR_FILE_LIST:"+str(n))
                has_more=next_page.get("hasNextPage") is True
                file_after=next_page.get("endCursor")
            if len(files)!=(file_conn.get("totalCount") if isinstance(file_conn,dict) else -1):
                raise ValueError("INCOMPLETE_PR_FILE_LIST:"+str(n))
            head_repo=node.get("headRepository")
            head_repo_full_name=(head_repo.get("nameWithOwner")
                                 if isinstance(head_repo,dict) else None)
            pr_row={"number":n,"title":node.get("title"),
                    "head":{"sha":node.get("headRefOid"),
                            "ref":node.get("headRefName"),
                            "repo":{"full_name":head_repo_full_name}}}
            if (n in EXEMPT_HISTORICAL_PRS and
                    pr_row["head"].get("sha")==EXEMPT_HISTORICAL_HEADS[n]):
                continue
            if not is_donor_pr(pr_row,files):
                continue
            head_sha=pr_row["head"].get("sha")
            source_repo=head_repo_full_name or repo
            for file_row in files:
                filename=file_row.get("filename")
                if filename!=REGISTRY and not any(str(filename).startswith(prefix) for prefix in DONOR_DELTA_PREFIXES):
                    continue
                if not isinstance(head_sha,str) or len(head_sha)!=40:
                    continue
                try:
                    head_obj=rest(f"/repos/{source_repo}/contents/{filename}?ref={head_sha}")
                    head_blob=head_obj.get("sha") if isinstance(head_obj,dict) else None
                    if isinstance(head_blob,str) and len(head_blob)==40:
                        file_row["sha"]=head_blob
                except Exception:
                    # Missing proof remains live/fail-closed in live_donor_intake_files.
                    pass
            live_intake_files=live_donor_intake_files(files,rest,repo)
            intake=bool(live_intake_files)
            found.append({"number":n,"title":node.get("title"),
                          "head_sha":head_sha,
                          "head_ref":node.get("headRefName"),
                          "head_repo_full_name":head_repo_full_name,
                          "intake":intake,
                          "registry_mutation":any(f.get("filename")==REGISTRY for f in live_intake_files),
                          "batch_manifest":any(str(f.get("filename","")).startswith("canonical/deltas/CFA3-DONOR-") for f in live_intake_files),
                          "workload_units":donor_intake_workload(live_intake_files) if intake else None})
        page=conn.get("pageInfo")
        if not isinstance(page,dict):
            raise ValueError("INCOMPLETE_PR_LIST")
        if page.get("hasNextPage") is not True:
            return sorted(found,key=lambda p:p["number"])
        after=page.get("endCursor")
        if not isinstance(after,str) or not after:
            raise ValueError("INCOMPLETE_PR_LIST")

def is_donor_intake_pr(pr,files):
    """Claim the exclusive intake slot only for actual canonical donor mutation.

    Policy-only PRs, donor documentation, research and reference sets remain
    visible to maintenance reporting but cannot reserve the intake slot.
    """
    for f in files:
        name=f.get("filename") if isinstance(f,dict) else None
        if not isinstance(name,str):
            raise ValueError("UNREADABLE_PR_FILE")
        if (name==REGISTRY or any(name.startswith(prefix) for prefix in DONOR_DELTA_PREFIXES)):
            return True
    return False

def live_donor_intake_files(files,get,repo=REPO):
    """Return canonical donor mutations whose candidate bytes still differ from main.

    GitHub's pull-request file list is relative to the PR's merge base. A long-
    lived PR can therefore retain donor files that were independently published
    to main later. Those byte-identical stale-base files must neither reserve a
    rolling-window slot nor inflate finalization workload. Missing or unreadable
    blob identity fails closed and remains a live mutation.
    """
    live=[]
    for f in files:
        name=f.get("filename") if isinstance(f,dict) else None
        if not isinstance(name,str):
            raise ValueError("UNREADABLE_PR_FILE")
        if name!=REGISTRY and not any(name.startswith(prefix) for prefix in DONOR_DELTA_PREFIXES):
            continue
        head_blob=f.get("sha")
        if not isinstance(head_blob,str) or len(head_blob)!=40:
            live.append(f)
            continue
        try:
            main=get(f"/repos/{repo}/contents/{name}?ref=main")
        except Exception:
            live.append(f)
            continue
        main_blob=main.get("sha") if isinstance(main,dict) else None
        if not isinstance(main_blob,str) or len(main_blob)!=40 or main_blob!=head_blob:
            live.append(f)
    return live

def effective_donor_intake_pr(pr,files,get,repo=REPO):
    """Reserve a rolling intake slot only for canonical donor bytes live vs main."""
    return bool(live_donor_intake_files(files,get,repo))

def donor_intake_workload(files):
    """Estimate intake size from canonical donor-mutation diff units.

    Only canonical registry/intake-delta changes count toward the ordering.
    GitHub per-file changes is preferred; additions+deletions are the fallback,
    and unreadable or missing stats fail conservatively to one unit.
    """
    units=0
    found=False
    for f in files:
        name=f.get("filename") if isinstance(f,dict) else None
        if not isinstance(name,str):
            raise ValueError("UNREADABLE_PR_FILE")
        if name==REGISTRY or any(name.startswith(prefix) for prefix in DONOR_DELTA_PREFIXES):
            found=True
            changes=f.get("changes")
            if not isinstance(changes,int) or changes < 0:
                additions=f.get("additions")
                deletions=f.get("deletions")
                if isinstance(additions,int) and additions >= 0 and isinstance(deletions,int) and deletions >= 0:
                    changes=additions+deletions
                else:
                    changes=1
            units += max(1,changes)
    return units if found else 0

def is_donor_pr(pr,files):
    title=str(pr.get("title","")).lower()
    if "donor" in title: return True
    for f in files:
        name=f.get("filename")
        if not isinstance(name,str): raise ValueError("UNREADABLE_PR_FILE")
        if (name in DONOR_FILES or any(name.startswith(p) for p in DONOR_PREFIXES)
                or (name.startswith("canonical/references/")
                    and "DONOR" in name.upper())):
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
                # GitHub caps the PR-files endpoint at 3,000 files. Reaching
                # that boundary is indistinguishable from truncation, so do
                # not derive donor workload or slot priority from partial data.
                if len(files)>=MAX_GITHUB_PR_FILES:
                    raise ValueError("PR_FILE_LIST_AT_GITHUB_API_CAP:"+str(n))
                if len(part)<100: break
            else: raise ValueError("TOO_MANY_PR_FILES:"+str(n))
            if (n in EXEMPT_HISTORICAL_PRS and
                    pr.get("head",{}).get("sha")==EXEMPT_HISTORICAL_HEADS[n]):
                continue
            if is_donor_pr(pr,files):
                live_intake_files=live_donor_intake_files(files,get,repo)
                intake=bool(live_intake_files)
                head=pr.get("head",{}) if isinstance(pr.get("head"),dict) else {}
                head_repo=head.get("repo",{}) if isinstance(head.get("repo"),dict) else {}
                found.append({"number":n,"title":pr.get("title"),
                              "head_sha":head.get("sha"),
                              "head_ref":head.get("ref"),
                              "head_repo_full_name":head_repo.get("full_name"),
                              "intake":intake,
                              "registry_mutation":any(f.get("filename")==REGISTRY for f in live_intake_files),
                              "batch_manifest":any(str(f.get("filename","")).startswith("canonical/deltas/CFA3-DONOR-") for f in live_intake_files),
                              "workload_units":donor_intake_workload(live_intake_files) if intake else None})
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

def planning_snapshot_findings(row,sha,reg,published_main_sha,registry_blob_sha):
    snapshot=row.get("donor_planning_snapshot")
    if not isinstance(snapshot,dict):
        return ["DONOR_PLANNING_SNAPSHOT_REQUIRED"]
    expected={
        "published_main_commit":published_main_sha,
        "donor_registry_id":reg["id"],
        "donor_registry_blob_sha":registry_blob_sha,
        "donor_registry_sha256":sha,
        "donor_registry_entry_count":len(reg.get("entries",[])),
    }
    findings=[]
    for key,value in expected.items():
        if snapshot.get(key)!=value:
            findings.append("DONOR_PLANNING_SNAPSHOT_MISMATCH:"+key)
    return findings

def assessment_findings(root,path,sha,reg,published_main_sha,registry_blob_sha):
    if not path:return ["DONOR_ASSESSMENT_REQUIRED"]
    row=json.loads(committed(root,path))
    findings=planning_snapshot_findings(row,sha,reg,published_main_sha,registry_blob_sha)
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

def batch_manifest_coverage(root,pending,pr_number):
    """Return exact-head donor PR coverage declared by a committed CFA3 batch manifest."""
    covered={}
    delta_root=Path(root)/"canonical"/"deltas"
    if delta_root.is_dir():
        for path in sorted(delta_root.glob("CFA3-DONOR-*.json")):
            try:
                row=json.loads(path.read_text(encoding="utf-8"))
            except (OSError,json.JSONDecodeError):
                continue
            source_prs=row.get("source_prs")
            if not isinstance(source_prs,list):
                continue
            for item in source_prs:
                if not isinstance(item,dict):
                    continue
                number=item.get("pr")
                head=item.get("head")
                if isinstance(number,int) and isinstance(head,str) and len(head)==40:
                    covered[number]=head
    required={p["number"]:p.get("head_sha") for p in pending if p["number"]!=pr_number}
    missing=[number for number,head in required.items() if covered.get(number)!=head]
    return covered,sorted(missing)

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
        result["pending_prs"]=(pending_prs_graphql(token) if get is None
                               else pending_prs(getter))
        result["pending_intake_prs"]=[p for p in result["pending_prs"] if p["intake"]]
        after=getter(f"/repos/{REPO}/branches/main")["commit"]["sha"]
        if before!=after:result["findings"].append("MAIN_MOVED_DURING_SCAN")
        if result["findings"]:return result
        if phase=="intake":
            # Owner-approved rolling donor-intake window:
            # - at most five genuine canonical intake PRs are active;
            # - FIFO controls admission into a newly freed slot;
            # - within the active window, the smallest canonical donor-mutation
            #   workload finalizes first, with FIFO as the tie-breaker.
            # Registry publication itself therefore remains single-finalizer
            # even though up to five intake requests may be active.
            pending=result["pending_intake_prs"]
            active=pending[:MAX_ACTIVE_DONOR_INTAKES]
            waiting=pending[MAX_ACTIVE_DONOR_INTAKES:]
            finalization=sorted(
                active,key=lambda p:(p.get("workload_units",1),p["number"]))
            registry_mutators=[p for p in pending if p.get("registry_mutation")]
            result["max_active_donor_intakes"]=MAX_ACTIVE_DONOR_INTAKES
            result["max_active_canonical_registry_mutation_prs"]=MAX_ACTIVE_CANONICAL_REGISTRY_MUTATION_PRS
            result["active_donor_prs"]=[p["number"] for p in active]
            result["waiting_donor_prs"]=[p["number"] for p in waiting]
            result["canonical_registry_mutation_prs"]=[p["number"] for p in registry_mutators]
            result["finalization_order"]=[p["number"] for p in finalization]
            result["available_intake_slots"]=MAX_ACTIVE_DONOR_INTAKES-len(active)
            result["active_donor_pr"]=finalization[0]["number"] if finalization else None

            if pr_number is not None:
                candidate=next((p for p in pending if p["number"]==pr_number),None)
                if candidate is not None and candidate.get("batch_manifest"):
                    covered,missing=batch_manifest_coverage(root,pending,pr_number)
                    if len(pending)>1 and not missing:
                        result["batch_covered_prs"]=sorted(n for n in covered if n!=pr_number)
                        result["batch_coverage_missing"]=[]
                        result["active_donor_pr"]=pr_number
                        result["finalization_order"]=[pr_number]
                        result["result"]="DONOR_INTAKE_READY_TO_FINALIZE"
                        result["intake_workload_units"]=candidate.get("workload_units")
                        result["next_finalizable_donor_pr"]=pr_number
                        return result
                    if missing:
                        result["batch_coverage_missing"]=missing
                        result["findings"].append("BATCH_MANIFEST_DOES_NOT_COVER_ALL_LIVE_INTAKES")
                        return result

            if pr_number is None:
                if len(active) >= MAX_ACTIVE_DONOR_INTAKES:
                    result["findings"].append("DONOR_INTAKE_ACTIVE_WINDOW_FULL_WAIT_FOR_SLOT")
                    return result
                result["result"]="DONOR_INTAKE_SLOT_AVAILABLE"
                return result

            row=next((p for p in pending if p["number"]==pr_number),None)
            if row is None:
                result["findings"].append("INTAKE_PR_NOT_OPEN_OR_NOT_DONOR")
                return result
            if pr_number not in result["active_donor_prs"]:
                result["findings"].append("DONOR_INTAKE_ACTIVE_WINDOW_FULL_WAIT_FOR_SLOT")
                return result
            if finalization and finalization[0]["number"] != pr_number:
                result["findings"].append("DONOR_INTAKE_ACTIVE_WAIT_FOR_SMALLER_FINALIZATION")
                result["next_finalizable_donor_pr"]=finalization[0]["number"]
                return result
            result["result"]="DONOR_INTAKE_READY_TO_FINALIZE"
            result["intake_workload_units"]=row.get("workload_units")
            result["next_finalizable_donor_pr"]=pr_number
            return result
        # Pending intake is deliberately NOT a global planning lock:
        # unmerged donor entries are absent from the published main snapshot.
        # A design must use and hash the exact committed main registry only.
        # A locally coherent but stale branch must never authorize planning after
        # a newer canonical main registry is published. Fetch the blob identity
        # at the exact main SHA observed during the live pending-PR scan.
        remote=getter(f"/repos/{REPO}/contents/{REGISTRY}?ref={after}")
        if (not isinstance(remote,dict) or not isinstance(remote.get("sha"),str)
                or len(remote["sha"]) != 40):
            raise ValueError("CANONICAL_MAIN_REGISTRY_BLOB_UNAVAILABLE")
        local=git_blob_sha((root / REGISTRY).read_bytes())
        result["main_registry_blob_sha"]=remote["sha"]
        result["published_main_sha"]=after
        result["registry_snapshot"]="PUBLISHED_MAIN_ONLY"
        if local != remote["sha"]:
            result["findings"].append("STALE_CANONICAL_DONOR_SNAPSHOT")
            return result
        if phase in ("entry","finalize"):
            result["findings"].extend(assessment_findings(
                root,assessment,inspect["sha256"],inspect["registry"],after,remote["sha"]))
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
    p.add_argument("--phase",choices=("maintenance","intake","status","entry","finalize"),default="status")
    p.add_argument("--assessment")
    p.add_argument("--plan")
    p.add_argument("--approval")
    p.add_argument("--pr",type=int)
    a=p.parse_args()
    x=gate(Path(a.root).resolve(),a.phase,os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN",""),
           a.assessment,a.plan,a.approval,a.pr)
    print(json.dumps(x,ensure_ascii=False,indent=2))
    return 0 if x["result"] in ("MAINTENANCE_INTEGRITY_PASS",
                                 "DONOR_INTAKE_SLOT_AVAILABLE",
                                 "DONOR_INTAKE_READY_TO_FINALIZE",
                                 "READY_FOR_SEPARATE_FA3_ADMISSION_GATES") else 2
if __name__=="__main__":raise SystemExit(main())
