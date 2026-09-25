#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil, subprocess, tempfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from fa3_supply_chain_admission import canonical_json_sha256, evaluate_license_policy, evaluate_receipt, sha256_file, sha256_tree

def version(binary:str)->str:
    for arg in ("version","--version"):
        p=subprocess.run([binary,arg],text=True,capture_output=True,timeout=20)
        text=(p.stdout or p.stderr).strip().splitlines()
        if p.returncode==0 and text:return text[0][:200]
    return "UNKNOWN"

def run(cmd:list[str])->str:
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=600)
    if p.returncode: raise RuntimeError(f"{cmd[0]} failed: {(p.stderr or p.stdout)[-2000:]}")
    return p.stdout

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--target",required=True); ap.add_argument("--source-repository",required=True); ap.add_argument("--source-commit",required=True)
    ap.add_argument("--dependency-lock"); ap.add_argument("--declared-license",required=True)
    ap.add_argument("--license-policy",default="canonical/supply-chain-license-policy.json")
    ap.add_argument("--output",default="evidence/receipts/supply-chain-admission.json")
    a=ap.parse_args(); target=Path(a.target).resolve()
    syft=shutil.which("syft"); grype=shutil.which("grype"); scancode=shutil.which("scancode")
    if not all((syft,grype,scancode)): raise SystemExit("syft, grype and scancode must already be installed; network installation is intentionally not performed")
    with tempfile.TemporaryDirectory(prefix="fa3-scs-") as td:
        td=Path(td); sbom=td/"sbom.json"; vul=td/"grype.json"; lic=td/"scancode.json"
        run([syft,str(target),"-o",f"cyclonedx-json={sbom}"])
        vul.write_text(run([grype,f"sbom:{sbom}","-o","json"]),encoding="utf-8")
        run([scancode,"--license","--json",str(lic),str(target)])
        vuldoc=json.loads(vul.read_text()); licdoc=json.loads(lic.read_text())
        findings=[]
        for m in vuldoc.get("matches",[]):
            v=m.get("vulnerability",{}); findings.append({"id":v.get("id"),"severity":v.get("severity","UNKNOWN"),"disposition":"OPEN"})
        detected=set()
        for f in licdoc.get("files",[]):
            for l in f.get("licenses",[]): detected.add(l.get("spdx_license_key") or l.get("key") or "UNKNOWN")
            for d in f.get("license_detections",[]):
                expr=d.get("license_expression_spdx") or d.get("license_expression")
                if expr: detected.add(expr)
        policy_path=Path(a.license_policy)
        if not policy_path.is_absolute(): policy_path=Path.cwd()/policy_path
        policy=json.loads(policy_path.read_text(encoding="utf-8"))
        license_eval=evaluate_license_policy(a.declared_license,sorted(detected),policy)
        receipt={"schema":"fa3.software-supply-chain-receipt.v1","source":{"repository":a.source_repository,"commit":a.source_commit},
          "artifact":{"path":str(target),"sha256":sha256_tree(target),"hash_scope":"FILE_CONTENT" if target.is_file() else "DETERMINISTIC_TREE_CONTENT"},
          "dependency_lock":{"required":bool(a.dependency_lock),"sha256":sha256_file(Path(a.dependency_lock)) if a.dependency_lock else None},
          "sbom":{"format":"CYCLONEDX_JSON","sha256":sha256_file(sbom),"scanner":"syft","scanner_version":version(syft)},
          "license":{"scanner":"scancode","scanner_version":version(scancode),"declared_expression":a.declared_license,
            "detected_expressions":sorted(detected),"conflicts":[],"commercial_compatible":license_eval["commercial_compatible"],"redistribution_compatible":license_eval["redistribution_compatible"],"declaration_matches_detection":license_eval["declaration_matches_detection"],"policy_id":policy.get("id"),"policy_result":license_eval["result"],"policy_reasons":license_eval["reasons"]},
          "vulnerabilities":{"scanner":"grype","scanner_version":version(grype),"findings":findings},
          "provenance":{"builder":"fa3_supply_chain_scan.py","build_recipe_sha256":canonical_json_sha256({"target":str(target),"source":a.source_repository,"commit":a.source_commit})}}
        receipt["admission"]=evaluate_receipt(receipt)
        out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
        print(json.dumps(receipt,indent=2,ensure_ascii=False)); return 0 if receipt["admission"]["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
