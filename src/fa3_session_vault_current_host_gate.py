#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def run_gate(root: Path, receipt_rel: Path) -> int:
    path=(root/receipt_rel).resolve()
    findings=[]
    if not path.is_file():
        report={"schema":"fa3.session-vault-current-host-gate-report.v1","gate_id":"FA3-GATE-SESSION-VAULT-CURRENT-HOST-001","result":"FAIL","findings":["MISSING_REAL_CURRENT_HOST_RECEIPT"]}
        print(json.dumps(report,indent=2)); return 2
    try: x=json.loads(path.read_text())
    except Exception as e:
        report={"schema":"fa3.session-vault-current-host-gate-report.v1","gate_id":"FA3-GATE-SESSION-VAULT-CURRENT-HOST-001","result":"FAIL","findings":["INVALID_JSON:"+str(e)]}
        print(json.dumps(report,indent=2)); return 2
    def req(ok,code):
        if not ok: findings.append(code)
    req(x.get("schema")=="fa3.session-vault-current-host-receipt.v1","SVCH-001")
    req(x.get("status")=="PASS" and x.get("real_execution") is True and x.get("synthetic") is False,"SVCH-002")
    req(str(x.get("image_path","")).endswith("/.local/share/fa3/state/fa3-state.img"),"SVCH-003")
    req(x.get("external_storage_name_non_disclosing") is True and x.get("luks2") is True,"SVCH-004")
    for k in ("loop_setup_pass","unlock_pass","mount_pass","service_account_isolation_pass","explicit_unmount_pass","explicit_lock_pass","loop_cleanup_pass","opaque_backup_copy_pass","opaque_backup_restore_unlock_pass","opaque_backup_restore_mount_pass"):
        req(x.get(k) is True,"SVCH-"+k.upper())
    req(x.get("filesystem")=="ext4","SVCH-005")
    req(x.get("luks_label")=="FA3_STATE" and x.get("filesystem_label")=="FA3_STATE","SVCH-006")
    req({"nodev","nosuid","noexec"}.issubset(set(x.get("mount_options") or [])),"SVCH-007")
    ss=x.get("secret_service") or {}
    req(ss.get("configured") is False or ss.get("lookup_pass_if_configured") is True,"SVCH-008")
    req(x.get("secret_values_collected") is False,"SVCH-009")
    req(x.get("runtime_promotion_eligible") is True and x.get("global_promotion_claim") is False,"SVCH-010")
    report={"schema":"fa3.session-vault-current-host-gate-report.v1","gate_id":"FA3-GATE-SESSION-VAULT-CURRENT-HOST-001","result":"PASS" if not findings else "FAIL","findings":findings}
    out=root/"reports/session-vault-current-host-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    return 0 if not findings else 2

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); ap.add_argument("--receipt",default="evidence/receipts/session-vault-current-host.json"); a=ap.parse_args()
    return run_gate(Path(a.root).resolve(),Path(a.receipt))

if __name__=="__main__": raise SystemExit(main())
