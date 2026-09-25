#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from typing import Any

RECEIPT_SCHEMA="fa3.software-supply-chain-receipt.v1"
SHA256=re.compile(r"^[0-9a-f]{64}$")
COMMIT=re.compile(r"^[0-9a-f]{40,64}$")
SBOM_FORMATS={"SPDX_JSON","CYCLONEDX_JSON"}
BLOCKING_SEVERITIES={"CRITICAL","HIGH"}

class SupplyChainAdmissionError(RuntimeError): pass

def _digest(v: Any) -> bool:
    return isinstance(v,str) and bool(SHA256.fullmatch(v.lower()))

def _nonempty(v: Any) -> bool:
    return isinstance(v,str) and bool(v.strip())

def evaluate_receipt(receipt: dict[str,Any]) -> dict[str,Any]:
    findings=[]
    if receipt.get("schema")!=RECEIPT_SCHEMA: findings.append("schema mismatch")
    src=receipt.get("source",{})
    if not _nonempty(src.get("repository")) or not COMMIT.fullmatch(str(src.get("commit","")).lower()):
        findings.append("immutable source identity missing")
    artifact=receipt.get("artifact",{})
    if not _digest(artifact.get("sha256")): findings.append("artifact sha256 missing")
    lock=receipt.get("dependency_lock",{})
    if lock.get("required") is True and not _digest(lock.get("sha256")):
        findings.append("required dependency lock digest missing")
    sbom=receipt.get("sbom",{})
    if sbom.get("format") not in SBOM_FORMATS or not _digest(sbom.get("sha256")):
        findings.append("valid SPDX/CycloneDX SBOM attestation missing")
    if not _nonempty(sbom.get("scanner")) or not _nonempty(sbom.get("scanner_version")):
        findings.append("SBOM scanner identity/version missing")
    lic=receipt.get("license",{})
    if not _nonempty(lic.get("scanner")) or not _nonempty(lic.get("scanner_version")):
        findings.append("license scanner identity/version missing")
    if not _nonempty(lic.get("declared_expression")):
        findings.append("declared license expression missing")
    detected=lic.get("detected_expressions")
    if not isinstance(detected,list) or not detected:
        findings.append("detected license expressions missing")
    conflicts=lic.get("conflicts",[])
    if not isinstance(conflicts,list): findings.append("license conflicts malformed")
    elif conflicts: findings.append("unresolved license conflict")
    if lic.get("commercial_compatible") is not True:
        findings.append("commercial compatibility not proven")
    if lic.get("redistribution_compatible") is not True:
        findings.append("redistribution compatibility not proven")
    vul=receipt.get("vulnerabilities",{})
    if not _nonempty(vul.get("scanner")) or not _nonempty(vul.get("scanner_version")):
        findings.append("vulnerability scanner identity/version missing")
    matches=vul.get("findings",[])
    if not isinstance(matches,list): findings.append("vulnerability findings malformed")
    else:
        for row in matches:
            if not isinstance(row,dict): findings.append("vulnerability finding malformed"); continue
            sev=str(row.get("severity","UNKNOWN")).upper()
            disposition=str(row.get("disposition","OPEN")).upper()
            if sev in BLOCKING_SEVERITIES and disposition not in {"FIXED","NOT_AFFECTED","ACCEPTED_WITH_EXPIRY"}:
                findings.append(f"blocking vulnerability: {row.get('id','UNKNOWN')}")
    prov=receipt.get("provenance",{})
    if not _nonempty(prov.get("builder")) or not _digest(prov.get("build_recipe_sha256")):
        findings.append("build provenance incomplete")
    admission=not findings
    return {"result":"PASS" if admission else "FAIL","admitted":admission,"findings":findings}

def canonical_json_sha256(obj: Any) -> str:
    raw=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
