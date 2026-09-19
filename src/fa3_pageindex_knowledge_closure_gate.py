#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any
GATE_ID="FA3-PAGEINDEX-KNOWLEDGE-CLOSURE-GATESET-001"
def loadj(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding="utf-8"))
def f(code,msg,**kw): return {"code":code,"severity":"P0","message":msg,**kw}
def gate(root:Path)->dict[str,Any]:
    root=root.resolve(); fs=[]
    try:
        k=loadj(root/"canonical/profiles/FA3-KNOWLEDGE-001.json"); comp=loadj(root/"canonical/profiles/FA3-KNOWLEDGE-COMPILATION-001.json")
        mm=loadj(root/"canonical/profiles/FA3-MULTIMODAL-KNOWLEDGE-REASONING-001.json"); eg=loadj(root/"canonical/profiles/FA3-ASSET-EGRESS-POLICY-001.json")
        cc=loadj(root/"canonical/contracts/FA3-KNOWLEDGE-COMPILATION-CONTRACTS-001.json"); bridge=loadj(root/"canonical/FA3-KNOWLEDGE-DERIVATION-BRIDGE-001.json")
        op=loadj(root/"canonical/providers/FA3-PROVIDER-OPENKB-001.json"); cd=loadj(root/"canonical/providers/FA3-PROVIDER-CONDB-001.json")
        page=loadj(root/"canonical/providers/FA3-PROVIDER-PAGEINDEX-LOCAL-001.json"); mcp=loadj(root/"canonical/providers/FA3-PROVIDER-PAGEINDEX-MCP-001.json")
        enf=loadj(root/"canonical/pageindex-knowledge-closure-enforcement.json")
    except Exception as exc:
        return {"schema":"fa3.pageindex-knowledge-closure-gate.v1","gate_id":GATE_ID,"result":"FAIL","findings":[f("PKC-000","closure materialization unreadable",error=repr(exc))],"global_promotion_claim":False}
    if k.get("id")!="FA3-KNOWLEDGE-001" or k.get("canonical_root") is not True: fs.append(f("PKC-001","Knowledge root drift"))
    if any(x.get("capability_count")!=143 or x.get("new_architectural_authority") is not False for x in (k,comp,mm,eg)): fs.append(f("PKC-002","capability/authority invariant drift"))
    required={"KnowledgeClaim","KnowledgeEntity","KnowledgeRelation","KnowledgeConcept","TemporalAssertion","ContradictionRecord","ProvenanceEdge","CompilationReceipt","DerivedKnowledgeProjection"}
    if not required.issubset(set(cc.get("contracts",{}))): fs.append(f("PKC-003","compilation contracts incomplete"))
    if bridge.get("architectural_authority") is not False or "FA3-JOURNAL-001" not in "_".join(bridge.get("inputs",[])): fs.append(f("PKC-004","derivation bridge authority drift"))
    if op.get("source_authority")!="DENY" or op.get("journal_authority")!="DENY" or op.get("upstream",{}).get("commit")!=UP_OPENKB: fs.append(f("PKC-005","OpenKB provider boundary/pin drift"))
    if cd.get("durable_knowledge_authority")!="DENY" or cd.get("journal_authority")!="DENY" or cd.get("upstream",{}).get("commit")!=UP_CONDB: fs.append(f("PKC-006","ConDB provider boundary/pin drift"))
    if eg.get("capability_binding")!="CAP-140" or eg.get("authority")!="SECURITY_GOVERNANCE_POLICY_PLANE": fs.append(f("PKC-007","CAP-140 egress binding drift"))
    if enf.get("rules",{}).get("cloud_upload_without_egress_decision")!="DENY": fs.append(f("PKC-008","egress default-deny disabled"))
    if page.get("architectural_authority") is not False or mcp.get("architectural_authority") is not False: fs.append(f("PKC-009","PageIndex provider authority escalation"))
    for rel in ["src/fa3_knowledge_compilation.py","src/fa3_multimodal_knowledge.py","src/fa3_asset_egress_policy.py","src/fa3_openkb_provider.py","src/fa3_condb_provider.py"]:
        if not (root/rel).is_file(): fs.append(f("PKC-010","runtime artifact missing",path=rel))
    return {"schema":"fa3.pageindex-knowledge-closure-gate.v1","gate_id":GATE_ID,"result":"PASS" if not fs else "FAIL","findings":fs,"global_promotion_claim":False}
UP_OPENKB="ff54396e575ee6feb0113b631a34caa082b441cc"
UP_CONDB="62da030426b3eee96a77b464e7007cdf8530c42e"
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); a=ap.parse_args(); r=gate(Path(a.root)); print(json.dumps(r,indent=2)); return 0 if r["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
