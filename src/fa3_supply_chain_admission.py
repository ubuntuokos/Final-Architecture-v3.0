#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt, hashlib, json, os, re
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

def evaluate_license_policy(declared:str,detected:list[str],policy:dict[str,Any])->dict[str,Any]:
    allow={str(x).casefold():str(x) for x in policy.get("admitted_exact_spdx",[])}
    declared_norm=str(declared).strip().casefold()
    detected_norm={str(x).strip().casefold() for x in detected if str(x).strip()}
    exact_single=bool(re.fullmatch(r"[A-Za-z0-9.+-]+",str(declared).strip()))
    declaration_matches=declared_norm in detected_norm
    admitted=exact_single and declared_norm in allow and bool(detected_norm) and all(x in allow for x in detected_norm) and declaration_matches
    reasons=[]
    if not exact_single: reasons.append("declared license is compound or non-SPDX-simple")
    if declared_norm not in allow: reasons.append("declared license not auto-admit allowlisted")
    if not detected_norm: reasons.append("scanner detected no license")
    if any(x not in allow for x in detected_norm): reasons.append("detected license requires review or is denied")
    if not declaration_matches: reasons.append("declared license not confirmed by scanner detection")
    return {"result":"PASS" if admitted else "FAIL","commercial_compatible":admitted,"redistribution_compatible":admitted,"declaration_matches_detection":declaration_matches,"reasons":reasons}

def evaluate_receipt(receipt: dict[str,Any]) -> dict[str,Any]:
    findings=[]
    if receipt.get("schema")!=RECEIPT_SCHEMA: findings.append("schema mismatch")
    src=receipt.get("source",{})
    if not _nonempty(src.get("repository")) or not COMMIT.fullmatch(str(src.get("commit","")).lower()):
        findings.append("immutable source identity missing")
    artifact=receipt.get("artifact",{})
    if not _digest(artifact.get("sha256")): findings.append("artifact sha256 missing")
    kind=artifact.get("kind")
    if kind not in {"SOURCE_BUILD","OCI_IMAGE_EXPORT","PREBUILT_BINARY"}: findings.append("artifact kind invalid")
    lock=receipt.get("dependency_lock",{})
    expected_lock_required=kind in {"SOURCE_BUILD","OCI_IMAGE_EXPORT"}
    if lock.get("required") is not expected_lock_required: findings.append("dependency lock requirement inconsistent with artifact kind")
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
    if lic.get("declaration_matches_detection") is not True:
        findings.append("declared license not confirmed by scanner detection")
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
            if sev in BLOCKING_SEVERITIES:
                if disposition in {"FIXED","NOT_AFFECTED"}: continue
                if disposition=="ACCEPTED_WITH_EXPIRY":
                    try:
                        expiry=dt.date.fromisoformat(str(row.get("waiver_expires_on","")))
                        if expiry < dt.date.today(): findings.append(f"expired vulnerability waiver: {row.get('id','UNKNOWN')}")
                        if not _nonempty(row.get("waiver_authority")): findings.append(f"vulnerability waiver authority missing: {row.get('id','UNKNOWN')}")
                    except Exception: findings.append(f"invalid vulnerability waiver expiry: {row.get('id','UNKNOWN')}")
                else:
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

def sha256_tree(path: Path) -> str:
    root=Path(path).resolve()
    if root.is_file(): return sha256_file(root)
    if not root.is_dir(): raise FileNotFoundError(root)
    h=hashlib.sha256()
    for item in sorted(root.rglob("*"),key=lambda p:p.relative_to(root).as_posix()):
        if not (item.is_file() or item.is_symlink()): continue
        rel=item.relative_to(root).as_posix().encode("utf-8")
        h.update(len(rel).to_bytes(4,"big"));h.update(rel)
        if item.is_symlink():
            target=os.readlink(item).encode("utf-8")
            h.update(b"L");h.update(len(target).to_bytes(4,"big"));h.update(target)
        else:
            h.update(b"F");h.update(bytes.fromhex(sha256_file(item)))
    return h.hexdigest()
