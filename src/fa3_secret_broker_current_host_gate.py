#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
SCHEMA="fa3.secret-broker-current-host-receipt.v1"
def validate(x:dict)->list[str]:
    f=[]
    def req(ok,code):
        if not ok:f.append(code)
    req(x.get("schema")==SCHEMA,"SBH-001");req(x.get("status")=="PASS" and x.get("real_execution") is True and x.get("synthetic") is False,"SBH-002")
    req(x.get("luks2") is True and x.get("filesystem")=="ext4" and set(x.get("mount_options",[]))=={"nodev","nosuid","noexec"},"SBH-003")
    req(x.get("broker_unprivileged") is True and x.get("broker_user")=="fa3-secret-broker","SBH-004")\n    bridge=str(x.get("bridge_source_commit",""))\n    req(len(bridge)==40 and all(ch in "0123456789abcdef" for ch in bridge),"SBH-004A")
    checks=x.get("checks",{})
    for k in ["current_host_privileged_bridge_source_binding_pass","authorized_single_secret_get","systemd_loadcredential_projection_pass","encrypted_systemd_unlock_runtime_pass","systemd_target_lifecycle_pass","secrets_target_inactive_pass","hardware_neutral_systemd_credential_host_key_mode_pass","luks_unlock_key_rotation_pass","old_unlock_key_rejected_after_rekey","new_unlock_key_accepted_after_rekey","rekey_final_closed_state_pass","systemd_e2e_artifact_cleanup_pass","policy_preflight_pass","policy_install_remove_pass","rotation_pass","revocation_pass","metadata_only_list_pass","unauthorized_consumer_denied","raw_vault_access_denied","bulk_export_absent","credential_scope_enforced","audit_contains_no_raw_secret","secret_absent_from_argv","secret_absent_from_environment","broker_health_pass","explicit_unmount_pass","luks_close_pass","fa3_exit_closed_state_pass","opaque_backup_copy_pass","restore_unlock_pass","restore_mount_pass","restore_broker_health_pass","restore_secret_read_pass"]:
        req(checks.get(k) is True,"SBH-"+k)
    req(x.get("secret_values_collected") is False and x.get("runtime_promotion_eligible") is True and x.get("global_promotion_claim") is False,"SBH-005")
    req(x.get("new_capabilities")==0 and x.get("new_architectural_authorities")==0 and x.get("capability_count_after")==143,"SBH-006")
    return f
def gate(root:Path,receipt:Path|None,require:bool)->dict:
    p=receipt or root/"evidence/receipts/secret-broker-current-host.json"
    if not p.is_file():
        return {"schema":"fa3.secret-broker-current-host-gate-report.v1","gate_id":"FA3-GATE-SECRET-BROKER-CURRENT-HOST-001","result":"FAIL" if require else "PASS","status":"BLOCKED_CURRENT_HOST_EVIDENCE_REQUIRED" if require else "PENDING_CURRENT_HOST","findings":["MISSING_RECEIPT"] if require else [],"global_promotion_claim":False}
    try:x=json.loads(p.read_text());findings=validate(x)
    except Exception as exc:findings=["UNREADABLE:"+type(exc).__name__]
    return {"schema":"fa3.secret-broker-current-host-gate-report.v1","gate_id":"FA3-GATE-SECRET-BROKER-CURRENT-HOST-001","result":"PASS" if not findings else "FAIL","status":"CURRENT_HOST_PASS" if not findings else "BLOCKED_INVALID_EVIDENCE","findings":findings,"global_promotion_claim":False}
def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));ap.add_argument("--receipt");ap.add_argument("--require-evidence",action="store_true");a=ap.parse_args()
    out=gate(Path(a.root).resolve(),Path(a.receipt).resolve() if a.receipt else None,a.require_evidence)
    q=Path(a.root).resolve()/"reports/secret-broker-current-host-gate-report.json";q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2));return 0 if out["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
