#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
from fa3_terax_gate import gate as terax_gate, reference_check as terax_reference_check

OK=0
BLOCKED=2
INPUT=3
RELEASE="2026-08-23/v3.0.11"
CAPS=143
FORBIDDEN={"OPEN","ORPHANED","UNCLASSIFIED"}

RECEIPTS={
  4:["host-fingerprint.json","source-exclusion-receipt.json"],
  5:["provider-runtime-plans.json"],
  6:["host-budget-acceptance.json"],
  7:["survival-plane-acceptance.json"],
  8:["w3-local-inference.json"],
  9:["creative-golden-paths.json"],
  10:["rnnoise-current-host.json"],
  11:["openviking-current-host.json"],
  12:["ace-step-current-host.json"],
  13:["memory-hugepages-current-host.json"],
  14:["conversational-nle-current-host.json"],
  15:["conditional-provider-disposition.json"],
  16:["privileged-action-coverage.json"],
  17:["rollback-expiry-drill.json"],
  18:["release-integrity.json"],
  19:["independent-review.json","human-promotion-receipt.json"],
}
NAMES={
  1:"modular source graph and schema lint PASS",
  2:"authority lint has no duplicate owner",
  3:"143 capability catalog validation PASS",
  4:"current-host fingerprint and source exclusion receipt signed",
  5:"every active provider has current ResolvedRuntimePlan",
  6:"process and CPU/RAM/VRAM/I/O/network envelope fits host budget",
  7:"survival plane boot/security/observability runtime acceptance PASS",
  8:"W3 local inference positive/negative/degraded/rollback PASS",
  9:"creative film/office/audio golden paths human-approved PASS",
  10:"RNNoise current-host conformance PASS",
  11:"OpenViking current-host conformance PASS",
  12:"ACE-Step current-host conformance PASS",
  13:"Host memory-compaction/HugePages acceptance PASS",
  14:"Conversational NLE/editorial conformance PASS",
  15:"conditional providers explicitly dormant or evidence-promoted",
  16:"no orphan MUST and no orphan privileged action",
  17:"evidence expiry/invalidation and rollback drill works",
  18:"generated master digest matches release manifest",
  19:"independent review and human promotion receipt complete",
}

def loadj(p:Path):
    return json.loads(p.read_text(encoding="utf-8"))

def writej(p:Path,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def finding(code,msg,**kw):
    return {"code":code,"severity":"P0","message":msg,**kw}

def static_check(root:Path):
    fs=[]
    pol=loadj(root/"canonical/enforcement-policy.json")
    att=loadj(root/"canonical/source-graph-attestation.json")
    geom=loadj(root/"canonical/geometry-closure.json")
    mapping=loadj(root/"canonical/fa3_legacy_gap_to_registry_mapping_2026-08-26.json")
    rows=list(csv.DictReader((root/"canonical/conformance-matrix.csv").open(encoding="utf-8-sig",newline="")))

    if pol.get("architecture_release")!=RELEASE or pol.get("canonical_capability_count")!=CAPS:
        fs.append(finding("FA3-STATIC-001","Enforcement policy release/capability invariant mismatch"))
    if not pol.get("fail_closed") or not pol.get("document_only_promotion_forbidden"):
        fs.append(finding("FA3-STATIC-002","Fail-closed/document-only promotion invariant disabled"))
    if "Linux Recovery/Rebuild Projection" not in pol.get("out_of_scope",[]):
        fs.append(finding("FA3-STATIC-003","Removed Linux Recovery/Rebuild Projection returned to scope"))
    if "FA3-TERAX-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-015","Terax mandatory reference gate is not bound into global enforcement policy"))

    if att.get("release")!=RELEASE or att.get("ci_status")!="PASS" or att.get("design_coverage_status")!="STRUCTURALLY_COMPLETE":
        fs.append(finding("FA3-STATIC-004","Source-graph attestation not current structural PASS"))
    if att.get("sha256")!="0418528b52fd9a29d993fc69c1ea508f57cd527d96e234d738c6b8fc553c4f16":
        fs.append(finding("FA3-STATIC-005","Canonical source-graph attestation digest drift"))
    if att.get("graph_nodes")!=1615 or att.get("graph_edges")!=6144:
        fs.append(finding("FA3-STATIC-006","Canonical source-graph structural-count drift"))
    if any(att.get(k)!=0 for k in ("orphan_must","unmapped_capabilities","missing_evidence_mappings")):
        fs.append(finding("FA3-STATIC-007","Source graph contains unresolved design gaps"))

    expected=[f"CAP-{i:03d}" for i in range(1,144)]
    ids=[r.get("capability_id") for r in rows]
    if len(rows)!=CAPS or ids!=expected:
        fs.append(finding("FA3-STATIC-008","Capability catalog is not exact CAP-001..CAP-143",rows=len(rows)))
    bad=[r.get("capability_id") for r in rows if r.get("design_conformance")!="DESIGN-CONFORMANT"]
    if bad:
        fs.append(finding("FA3-STATIC-009","Non design-conformant capability found",sample=bad[:20]))

    maps=mapping.get("mappings",[])
    if mapping.get("record_id")!="FA3-CGR-2026-08-26" or mapping.get("status")!="CANONICAL_CLOSED":
        fs.append(finding("FA3-STATIC-010","Legacy reconciliation not CANONICAL_CLOSED"))
    if len(maps)!=36:
        fs.append(finding("FA3-STATIC-011","Legacy reconciliation count is not 36",count=len(maps)))
    if mapping.get("capability_count_after")!=CAPS or mapping.get("new_capabilities")!=0 or mapping.get("new_architectural_authorities")!=0:
        fs.append(finding("FA3-STATIC-012","Legacy reconciliation changed capability/authority invariant"))
    openm=[m for m in maps if str(m.get("status","")).upper() in FORBIDDEN or str(m.get("disposition","")).upper() in FORBIDDEN]
    if openm:
        fs.append(finding("FA3-STATIC-013","Unclosed legacy reconciliation records",count=len(openm)))

    if not (
      geom.get("status")=="CANONICAL_CLOSED" and
      geom.get("canonical_root")=="FA3-3D-GEOM-001" and
      geom.get("specialized_child")=="FA3-MESH-GEN-001" and
      geom.get("relationship")=="SUBPROFILE-OF" and
      geom.get("canonical_geometry_root_count")==1 and
      geom.get("open_overlaps")==0 and
      geom.get("canonical_capability_count")==CAPS
    ):
        fs.append(finding("FA3-STATIC-014","Geometry canonical closure invariant failed"))

    terax_ref=terax_reference_check(root)
    if terax_ref["result"]!="PASS":
        fs.extend(terax_ref.get("findings",[]))

    result="PASS" if not fs else "FAIL"
    rep={"schema":"fa3.static-gate-report.v1","architecture_release":RELEASE,"result":result,"blocking_findings":len(fs),"findings":fs,
         "details":{"capabilities":len(rows),"reconciliation_records":len(maps),"geometry_status":geom.get("status"),"source_graph_sha256":att.get("sha256"),"terax_reference_status":terax_ref["result"]}}
    writej(root/"reports/static-gate-report.json",rep)
    return rep

def runtime_check(root:Path):
    fs=[]
    reg=loadj(root/"evidence/evidence-registry.json")
    recs=reg.get("records",[])
    if reg.get("architecture_release")!=RELEASE:
        fs.append(finding("FA3-RUNTIME-001","Evidence Registry release mismatch"))
    expected=[f"CAP-{i:03d}" for i in range(1,144)]
    ids=[r.get("subject_id") for r in recs]
    if len(recs)!=CAPS or ids!=expected:
        fs.append(finding("FA3-RUNTIME-002","Evidence Registry is not exact 143 capability set",records=len(recs)))
    pending=[]
    invalid=[]
    for r in recs:
        s=str(r.get("status","")).upper()
        if s!="PASS":
            pending.append(r.get("subject_id"))
        if not r.get("required_positive_test") or not r.get("required_negative_test") or not r.get("rollback_requirement"):
            invalid.append(r.get("subject_id"))
        if s=="PASS" and not r.get("expires_at"):
            invalid.append(r.get("subject_id"))
    if pending:
        fs.append(finding("FA3-RUNTIME-003","Current-host evidence is not complete",pending_count=len(pending),sample=pending[:20]))
    if invalid:
        fs.append(finding("FA3-RUNTIME-004","Evidence record missing test/rollback/expiry requirement",sample=invalid[:20]))
    result="PASS" if not fs else "FAIL"
    rep={"schema":"fa3.runtime-gate-report.v1","architecture_release":RELEASE,"result":result,"blocking_findings":len(fs),
         "evidence_records":len(recs),"pass_count":sum(str(r.get("status","")).upper()=="PASS" for r in recs),
         "pending_count":sum(str(r.get("status","")).upper()!="PASS" for r in recs),"findings":fs}
    writej(root/"reports/runtime-gate-report.json",rep)
    return rep

def receipt_ok(p:Path,signed=False,human=False,independent=False):
    if not p.exists(): return False,"missing"
    try: d=loadj(p)
    except Exception: return False,"unreadable"
    if d.get("status")!="PASS": return False,str(d.get("status","not PASS"))
    if signed and not d.get("signed"): return False,"not signed"
    if human and not d.get("approved"): return False,"not approved"
    if independent and not d.get("independent"): return False,"not independent"
    return True,"PASS"

def acceptance_check(root:Path):
    s=static_check(root)
    r=runtime_check(root)
    t=terax_gate(root,require_current_host=True)
    results=[]
    for i in range(1,20):
        reasons=[]
        if i in (1,2):
            ok=s["result"]=="PASS"
            if not ok: reasons=["static/authority structural gate not PASS"]
        elif i==3:
            ok=s["result"]=="PASS" and s["details"]["capabilities"]==CAPS
            if not ok: reasons=["143 capability validation not PASS"]
        else:
            ok=True
            for fn in RECEIPTS[i]:
                rok,why=receipt_ok(root/"evidence/receipts"/fn,
                                   signed=(i in (4,19)),
                                   human=(fn=="human-promotion-receipt.json"),
                                   independent=(fn=="independent-review.json"))
                if not rok:
                    ok=False
                    reasons.append(f"{fn}: {why}")
        results.append({"id":i,"name":NAMES[i],"status":"PASS" if ok else "PENDING_OR_FAIL","reasons":reasons})
    all_ok=all(x["status"]=="PASS" for x in results) and r["result"]=="PASS" and t["result"]=="PASS"
    rep={"schema":"fa3.acceptance-report.v1","architecture_release":RELEASE,
         "status":"PASS" if all_ok else "DENIED","decision":"ACCEPT" if all_ok else "DENY","fail_closed":True,
         "static_gate":s["result"],"runtime_gate":r["result"],"terax_gate":t["result"],
         "criteria_passed":sum(x["status"]=="PASS" for x in results),"criteria_total":19,"criteria":results}
    writej(root/"acceptance/acceptance-report.json",rep)
    return rep

def promote(root:Path):
    a=acceptance_check(root)
    allowed=a["status"]=="PASS"
    state={"schema":"fa3.runtime-status.v1","architecture_release":RELEASE,"target_state":"PROMOTED",
           "actual_state":"PROMOTED" if allowed else "PROMOTION_BLOCKED","promotion_allowed":allowed,"acceptance":a["status"],
           "reason":None if allowed else "Fail-closed: PROMOTED is forbidden until all current-host evidence, all 19 acceptance criteria, and the mandatory Terax gate are PASS."}
    writej(root/"promotion/runtime-status.json",state)
    return state,OK if allowed else BLOCKED

def main():
    ap=argparse.ArgumentParser(description="FINAL ARCHITECTURE v3.0 permanent enforcement")
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--ci-only",action="store_true",help="For Terax gate: validate immutable reference + executable regressions without claiming current-host evidence")
    ap.add_argument("command",choices=("static","runtime","terax","acceptance","promote","all","status"))
    a=ap.parse_args()
    root=Path(a.root).resolve()
    try:
        if a.command=="static":
            x=static_check(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="runtime":
            x=runtime_check(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="terax":
            x=terax_gate(root,require_current_host=not a.ci_only); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="acceptance":
            x=acceptance_check(root); print(json.dumps(x,indent=2)); return OK if x["status"]=="PASS" else BLOCKED
        if a.command in ("promote","all"):
            x,rc=promote(root); print(json.dumps(x,indent=2)); return rc
        p=root/"promotion/runtime-status.json"
        print(p.read_text() if p.exists() else '{"actual_state":"UNKNOWN"}')
        return OK
    except Exception as e:
        print(f"INPUT ERROR: {e}",file=sys.stderr)
        return INPUT

if __name__=="__main__":
    raise SystemExit(main())
