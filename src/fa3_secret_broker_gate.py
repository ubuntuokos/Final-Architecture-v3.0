#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROFILE="canonical/profiles/FA3-SECRET-BROKER-001.json"
CONTRACT="canonical/contracts/FA3-SECRET-BROKER-CONTRACTS-001.json"
DECISION="canonical/decisions/FA3-DEC-SECRET-BROKER-ENCRYPTED-VAULT-2026-09-20.json"
ENFORCEMENT="canonical/secret-broker-enforcement.json"
CONFORMANCE="canonical/FA3-SECRET-BROKER-RUNTIME-CONFORMANCE-001.json"
GATE="canonical/FA3-GATE-SECRET-BROKER-001.json"
def load(path:str):return json.loads((ROOT/path).read_text())
def check()->dict:
    findings=[]
    def req(ok:bool,code:str):
        if not ok:findings.append(code)
    p,c,d,e,r,g=map(load,[PROFILE,CONTRACT,DECISION,ENFORCEMENT,CONFORMANCE,GATE])
    req(p.get("priority")=="P0" and p.get("requirement")=="MUST" and p.get("parent_profile")=="FA3-SCS-001","SB-001")
    req(p.get("provider_neutral") is True and p.get("architectural_authority") is False and p.get("new_capability") is False and p.get("new_architectural_authority") is False and p.get("capability_count")==143,"SB-002")
    machine=p.get("storage_classes",{}).get("machine_service",{})
    req(machine.get("default_type")=="LUKS2_FILE_IMAGE" and machine.get("default_image")=="/var/lib/fa3/state/fa3-machine-state.img" and machine.get("filesystem_label")=="FA3_MSTATE","SB-003")
    req(set(machine.get("mount_options",[]))=={"nodev","nosuid","noexec"} and machine.get("raw_mount_visible_to_consumers") is False,"SB-004")
    req(p.get("storage_classes",{}).get("user_session",{}).get("profile")=="FA3-SESSION-VAULT-001" and p["storage_classes"]["user_session"]["raw_machine_application_secret_storage"]=="FORBIDDEN","SB-005")
    req(p.get("unlock",{}).get("default")=="SYSTEMD_ENCRYPTED_CREDENTIAL" and p["unlock"]["plaintext_keyfile_persistence"]=="FORBIDDEN" and p["unlock"]["unlock_secret_inside_same_image"]=="FORBIDDEN","SB-006")
    req(p.get("delivery",{}).get("broker_transport")=="LOCAL_UNIX_DOMAIN_SOCKET_WITH_SO_PEERCRED" and p["delivery"]["podman_env_secret"]=="FORBIDDEN_BY_DEFAULT" and p["delivery"]["bulk_export"]=="FORBIDDEN" and p["delivery"]["full_vault_bind_mount"]=="FORBIDDEN","SB-007")
    req(p.get("portability",{}).get("hardware_vendor_neutral") is True and p["portability"]["accelerator_requirement"]=="NONE" and p["portability"]["kde_required"] is False and p["portability"]["x11_supported"] is True,"SB-008")
    req(c.get("id")=="FA3-SECRET-BROKER-CONTRACTS-001" and "SecretReference" in c.get("contracts",[]) and "SecretProjectionLease" in c.get("contracts",[]),"SB-009")
    req("SECRET_VALUE_NEVER_IN_LONG_LIVED_ENVIRONMENT" in c.get("invariants",[]) and "SAME_UID_DESKTOP_PROCESS_ISOLATION_MUST_NOT_BE_OVERCLAIMED" in c.get("invariants",[]),"SB-010")
    req(d.get("status")=="CANONICAL_CLOSED" and d.get("new_capabilities")==0 and d.get("new_architectural_authorities")==0 and d.get("capability_count_after")==143,"SB-011")
    req(e.get("fail_closed") is True and e.get("mandatory_rule_count")==36 and len(e.get("p0_invariants",[]))==36,"SB-012")
    req("PODMAN_SECRET_TYPE_ENV_FORBIDDEN_BY_DEFAULT" in e["p0_invariants"] and "REAL_CURRENT_HOST_E2E_REQUIRED_FOR_RUNTIME_PROMOTION" in e["p0_invariants"],"SB-013")
    req(r.get("status")=="MATERIALIZED_PENDING_REAL_CURRENT_HOST_EXECUTION" and r.get("production_runtime_promoted") is False and r.get("global_promotion_claim") is False,"SB-014")
    req(g.get("priority")=="P0" and g.get("fail_closed") is True and g.get("production_runtime_promoted") is False,"SB-015")
    broker=(ROOT/"src/fa3_secret_broker.py").read_text()
    req("SO_PEERCRED" in broker and "secret_ref_sha256" in broker and "secret_values_collected" in broker and "serve_forever" in broker,"SB-016")
    req('if op=="bulk"' not in broker and "unsupported operation" in broker,"SB-017")
    client=(ROOT/"bin/fa3-secretctl").read_text()
    req("getpass.getpass" in client and "secret_b64" in client and "os.environ" not in client,"SB-018")
    init=(ROOT/"bin/fa3-secret-vault-init").read_text()
    req("systemd-creds encrypt" in init and "--key-file -" in init and "FA3_MSTATE" in init,"SB-019")
    mount=(ROOT/"libexec/fa3-secret-vault-mount.sh").read_text()
    req('CREDENTIALS_DIRECTORY' in mount and "nodev,nosuid,noexec" in mount and "cryptsetup close" in mount,"SB-020")
    vault_unit=(ROOT/"deployment/secrets/fa3-secret-vault.service").read_text()
    broker_unit=(ROOT/"deployment/secrets/fa3-secret-broker.service").read_text()
    target=(ROOT/"deployment/secrets/fa3-secrets.target").read_text()
    req("LoadCredentialEncrypted=fa3-machine-state-key:" in vault_unit and "CapabilityBoundingSet=CAP_SYS_ADMIN" in vault_unit,"SB-021")
    req("User=fa3-secret-broker" in broker_unit and "NoNewPrivileges=true" in broker_unit and "RestrictAddressFamilies=AF_UNIX" in broker_unit and "CapabilityBoundingSet=" in broker_unit,"SB-022")
    req("Requires=fa3-secret-broker.service" in target and "PartOf=fa3-secrets.target" in broker_unit and "PartOf=fa3-secrets.target" in vault_unit,"SB-023")
    sv=load("canonical/profiles/FA3-SESSION-VAULT-001.json")
    req(sv.get("machine_secret_boundary",{}).get("profile")=="FA3-SECRET-BROKER-001" and sv["machine_secret_boundary"].get("raw_machine_application_secret_storage")=="FORBIDDEN","SB-024")
    return {"schema":"fa3.secret-broker-gate-report.v1","gate_id":"FA3-GATE-SECRET-BROKER-001","result":"PASS" if not findings else "FAIL","findings":findings,"production_runtime_promoted":False,"global_promotion_claim":False,"capability_count":143}
def main()->int:
    out=check()
    q=ROOT/"reports/secret-broker-gate-report.json";q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2));return 0 if out["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
