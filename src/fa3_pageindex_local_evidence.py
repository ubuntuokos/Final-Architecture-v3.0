#!/usr/bin/env python3
from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any
from fa3_hybrid_retrieval import build_plan,make_trace,context_passport
TOKEN="ORBITAL-COPPER-7319"
def write_fixture_pdf(path:Path)->str:
    text=f"FA3 PageIndex Local current host evidence. The verification phrase is {TOKEN}. Hierarchical retrieval must preserve this source."
    stream=f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs=[b"<< /Type /Catalog /Pages 2 0 R >>",b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
      b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
      b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
      b"<< /Length "+str(len(stream)).encode()+b" >>\nstream\n"+stream+b"\nendstream"]
    out=bytearray(b"%PDF-1.4\n"); offsets=[0]
    for i,obj in enumerate(objs,1):
        offsets.append(len(out)); out.extend(f"{i} 0 obj\n".encode()+obj+b"\nendobj\n")
    xref=len(out); out.extend(f"xref\n0 {len(objs)+1}\n".encode()+b"0000000000 65535 f \n")
    for off in offsets[1:]: out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(out)
    return hashlib.sha256(out).hexdigest()
def text_of(value:Any)->str:
    if isinstance(value,str): return value
    if isinstance(value,dict): return " ".join(text_of(x) for x in value.values())
    if isinstance(value,list): return " ".join(text_of(x) for x in value)
    return "" if value is None else str(value)
def retrieval_evidence(doc_id:str,receipts:list[dict[str,Any]])->tuple[dict[str,Any],dict[str,Any],dict[str,Any]]:
    reason=receipts[-1]
    plan=build_plan({"query":"What is the verification phrase?","source_scope":{"doc_ids":[doc_id]},"allow_vector":False,"provider_preferences":["FA3-PROVIDER-PAGEINDEX-LOCAL-001"]})
    trace=make_trace(plan,[{"source_id":doc_id,"locator":"page:1","score":1.0,"strategy":"tree_reasoning","evidence_refs":[str(reason.get("request_sha256",""))]}],
      [{"provider_id":x.get("provider_id"),"adapter_id":x.get("adapter_id"),"receipt_id":x.get("request_sha256"),"status":x.get("result_status")} for x in receipts])
    return plan,trace,context_passport(trace)
