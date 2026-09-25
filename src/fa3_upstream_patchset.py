#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt, re
from typing import Any

DISPOSITIONS={"DIRECT_PINNED","REFERENCE_ONLY","PATCHED_VENDOR","FA3_NATIVE_REIMPLEMENTATION","REJECTED"}
SHA256=re.compile(r"^[0-9a-f]{64}$")
COMMIT=re.compile(r"^[0-9a-f]{40,64}$")

class PatchSetError(RuntimeError): pass

def evaluate_patchset(record:dict[str,Any],*,today:dt.date|None=None)->dict[str,Any]:
    findings=[]
    if record.get("schema")!="fa3.upstream-patch-set.v1": findings.append("schema mismatch")
    disposition=record.get("disposition")
    if disposition not in DISPOSITIONS: findings.append("invalid disposition")
    if disposition=="PATCHED_VENDOR":
        for key in ("upstream_repository","reason"):
            if not record.get(key): findings.append(f"{key} missing")
        for key in ("upstream_commit","patched_commit"):
            if not COMMIT.fullmatch(str(record.get(key,"")).lower()): findings.append(f"{key} invalid")
        for key in ("patch_series_sha256","patched_tree_sha256","dependency_lock_sha256"):
            if not SHA256.fullmatch(str(record.get(key,"")).lower()): findings.append(f"{key} invalid")
        if not isinstance(record.get("upstream_issue_refs"),list): findings.append("upstream issue refs missing")
        if record.get("security_disposition")!="PASS": findings.append("security disposition not PASS")
        if record.get("supply_chain_receipt_status")!="PASS": findings.append("supply-chain receipt not PASS")
        if not SHA256.fullmatch(str(record.get("supply_chain_receipt_sha256","")).lower()): findings.append("supply-chain receipt digest invalid")
        review=record.get("review_by")
        try:
            review_date=dt.date.fromisoformat(str(review))
            if review_date < (today or dt.date.today()): findings.append("patch review expired")
        except Exception: findings.append("patch review date invalid")
    if disposition=="REFERENCE_ONLY" and record.get("runtime_admission") is True:
        findings.append("reference-only source cannot claim runtime admission")
    lic=record.get("license_disposition",{})
    runtime_ok=not findings and disposition in {"DIRECT_PINNED","PATCHED_VENDOR","FA3_NATIVE_REIMPLEMENTATION"}
    distribution_ok=runtime_ok and lic.get("commercial_compatible") is True and lic.get("redistribution_compatible") is True and not lic.get("conflicts")
    return {"result":"PASS" if not findings else "FAIL","runtime_admitted":runtime_ok,"distribution_admitted":distribution_ok,"findings":findings}
