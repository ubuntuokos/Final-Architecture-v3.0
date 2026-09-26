#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path

CAPABILITY_COUNT=175
POLICY_ID="FA3-COEXISTENCE-POLICY-001"
DECISION_ID="FA3-DEC-SOFTWARE-COEXISTENCE-2026-09-26"

def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def finding(code, message, severity="P0", **details):
    return {"code":code,"severity":severity,"message":message,**details}

def _collect_service_files(root: Path):
    return sorted([p for p in root.rglob("*") if p.is_file() and p.suffix in {".service",".socket",".timer"} and ".git" not in p.parts])

def _declared_footprints(root: Path):
    d=root/"canonical/coexistence/footprints"
    if not d.exists(): return []
    out=[]
    for p in sorted(d.glob("*.json")):
        try: out.append((p,load(p)))
        except Exception as exc: out.append((p,{"_parse_error":str(exc)}))
    return out

def audit(root: Path):
    root=root.resolve()
    findings=[]
    coverage=[]
    policy=load(root/"canonical/FA3-COEXISTENCE-POLICY-001.json")
    decision=load(root/"canonical/decisions/FA3-DEC-SOFTWARE-COEXISTENCE-2026-09-26.json")
    if policy.get("capability_count") != CAPABILITY_COUNT or decision.get("capability_count") != CAPABILITY_COUNT:
        findings.append(finding("COEX-001","capability baseline drift",expected=CAPABILITY_COUNT))
    if policy.get("capability_delta") != 0 or policy.get("authority_delta") != 0:
        findings.append(finding("COEX-002","coexistence policy illegally changes capability/authority baseline"))
    tb=decision.get("truth_boundary",{})
    if tb.get("static_pass_is_current_host_pass") is not False or tb.get("physical_current_host_evidence_required_for_runtime_pass") is not True:
        findings.append(finding("COEX-003","current-host truth boundary weakened"))

    # Existing ApplicationIntent records are already partial coexistence declarations.
    intent_files=sorted((root/"canonical/intents").glob("*.json")) if (root/"canonical/intents").exists() else []
    for p in intent_files:
        try: obj=load(p)
        except Exception as exc:
            findings.append(finding("COEX-010","ApplicationIntent parse failure",path=str(p.relative_to(root)),error=str(exc))); continue
        ns=obj.get("namespace_claims")
        if ns is None:
            coverage.append({"kind":"APPLICATION_INTENT","id":obj.get("id",p.stem),"path":str(p.relative_to(root)),"status":"PENDING_COEXISTENCE_DECLARATION"})
            continue
        bad=[]
        if ns.get("requires_upstream_uninstall") is not False: bad.append("requires_upstream_uninstall")
        if ns.get("global_environment_mutation") is not False: bad.append("global_environment_mutation")
        if ns.get("claims_default_port") is not False: bad.append("claims_default_port")
        if bad: findings.append(finding("COEX-011","ApplicationIntent violates coexistence namespace boundary",path=str(p.relative_to(root)),fields=bad))

    # systemd units in the repository must be FA3 namespaced unless explicitly upstream-owned.
    for p in _collect_service_files(root):
        rel=str(p.relative_to(root))
        name=p.name
        if "/deployment/" not in f"/{rel}" and not rel.startswith("deployment/"):
            continue
        if not name.startswith("fa3-"):
            findings.append(finding("COEX-020","repository-managed systemd unit is not FA3 namespaced",path=rel,unit=name))

    # Machine-readable footprint collision detector.
    seen={k:{} for k in ["executables","services","sockets","desktop_ids","protocol_handlers","databases"]}
    footprints=_declared_footprints(root)
    for p,obj in footprints:
        rel=str(p.relative_to(root))
        if "_parse_error" in obj:
            findings.append(finding("COEX-030","footprint parse failure",path=rel,error=obj["_parse_error"])); continue
        if obj.get("schema")!="fa3.coexistence-footprint.v1":
            findings.append(finding("COEX-031","footprint schema mismatch",path=rel)); continue
        co=obj.get("coexistence",{})
        for flag in ["requires_upstream_uninstall","global_environment_mutation","claims_default_port"]:
            if co.get(flag) is not False:
                findings.append(finding("COEX-032","forbidden coexistence claim",path=rel,field=flag))
        for domain in seen:
            for value in co.get(domain,[]):
                owner=seen[domain].get(value)
                if owner and owner != obj.get("component_id"):
                    findings.append(finding("COEX-033","collision between FA3 footprints",domain=domain,value=value,owners=[owner,obj.get("component_id")]))
                else:
                    seen[domain][value]=obj.get("component_id")
        ev=obj.get("evidence",{})
        if ev.get("runtime_promotion_claim") is not False:
            findings.append(finding("COEX-034","footprint attempts document-only runtime promotion",path=rel))
        if ev.get("current_host_status")=="PASS" and not ev.get("artifacts"):
            findings.append(finding("COEX-035","current-host PASS without evidence artifact",path=rel))

    provider_files=sorted((root/"canonical/providers").glob("*.json")) if (root/"canonical/providers").exists() else []
    footprint_ids={obj.get("component_id") for _,obj in footprints if isinstance(obj,dict)}
    for p in provider_files:
        try: obj=load(p)
        except Exception: continue
        pid=obj.get("id")
        coverage.append({"kind":"PROVIDER_RUNTIME","id":pid or p.stem,"path":str(p.relative_to(root)),"status":"DECLARED" if pid in footprint_ids else "PENDING_FOOTPRINT"})

    pending=sum(1 for r in coverage if r["status"].startswith("PENDING"))
    static_result="PASS" if not findings else "FAIL"
    return {
      "schema":"fa3.coexistence-audit-report.v1",
      "policy_id":POLICY_ID,
      "decision_id":DECISION_ID,
      "capability_id":"CAP-175",
      "capability_count":CAPABILITY_COUNT,
      "capability_delta":0,
      "authority_delta":0,
      "static_result":static_result,
      "coverage_status":"COMPLETE" if pending==0 else "PENDING_RETROACTIVE_INVENTORY",
      "current_host_status":"PENDING_CURRENT_HOST",
      "runtime_promotion_claim":False,
      "finding_count":len(findings),
      "pending_coverage_count":pending,
      "findings":findings,
      "coverage":coverage
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--report")
    ns=ap.parse_args()
    root=Path(ns.root)
    report=audit(root)
    out=Path(ns.report) if ns.report else root/"reports/coexistence-audit-report.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report["static_result"]=="PASS" else 2
if __name__=="__main__":
    raise SystemExit(main())
