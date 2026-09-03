#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any
from fa3_ffmpeg_ai_current_host import CAPABILITY_COUNT,CURRENT_HOST_CURRENT_HOST_CONFORMANCE_ID,CURRENT_HOST_EXECUTABLE_CURRENT_HOST_EXECUTABLE_GATE_ID,EVIDENCE_LEVEL,validate_current_host_receipt

RECEIPT="evidence/receipts/ffmpeg-ai-current-host.json"

def loadj(p:Path)->dict[str,Any]:return json.loads(p.read_text(encoding="utf-8"))

def gate(root:Path,receipt_path:Path|None=None)->dict[str,Any]:
    path=receipt_path or root/RECEIPT
    try:
        receipt=loadj(path)
        findings=validate_current_host_receipt(receipt)
        if receipt.get("fixture_semantics")=="SYNTHETIC_REFERENCE_FIXTURE_NOT_CURRENT_HOST":
            findings.append({"code":"FFMPEG-AI-HOST-014","severity":"P0","message":"synthetic fixture cannot be current-host evidence"})
    except Exception as exc:
        receipt={}
        findings=[{"code":"FFMPEG-AI-HOST-000","severity":"P0","message":"current-host receipt missing/unreadable","error":repr(exc)}]
    report={"schema":"fa3.ffmpeg-ai-current-host-gate-report.v1","gate_id":CURRENT_HOST_EXECUTABLE_GATE_ID,"conformance_id":CURRENT_HOST_CONFORMANCE_ID,
      "result":"PASS" if not findings else "FAIL","evidence_level":receipt.get("evidence_level"),
      "capability_count":CAPABILITY_COUNT,"findings":findings,
      "promotion_effect":"COMPONENT_CURRENT_HOST_FFMPEG_EVIDENCE_ONLY_GLOBAL_PROMOTION_UNCHANGED"}
    out=root/"reports/ffmpeg-ai-current-host-gate-report.json";out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return report

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));ap.add_argument("--receipt")
    a=ap.parse_args();root=Path(a.root).resolve();rp=Path(a.receipt).resolve() if a.receipt else None
    r=gate(root,rp);print(json.dumps(r,indent=2,ensure_ascii=False));return 0 if r["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
