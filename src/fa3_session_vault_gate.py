#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def main():
 findings=[]
 p=load("canonical/profiles/FA3-SESSION-VAULT-001.json")
 e=load("canonical/session-vault-enforcement.json")
 d=load("canonical/decisions/FA3-DEC-SESSION-VAULT-2026-09-20.json")
 c=load("canonical/FA3-SESSION-VAULT-RUNTIME-CONFORMANCE-001.json")
 def req(ok,code): 
  if not ok: findings.append(code)
 req(p.get("new_capability") is False and p.get("new_architectural_authority") is False and p.get("capability_count")==143,"SV-001")
 req(p["storage"]["default_type"]=="LUKS2_FILE_IMAGE" and p["storage"]["removable_media_required"] is False,"SV-002")
 req(p["session_semantics"]["separate_fa3_login_required"] is False and p["multi_user"]["default_enabled"] is False,"SV-002A")
 req("FREEDESKTOP_SECRET_SERVICE" in p["unlock_sources"] and "FA3_HUMAN_CREDENTIAL_VAULT_ADAPTER" in p["unlock_sources"],"SV-003")
 req(e.get("fail_closed") is True and "NO_MANDATORY_REMOVABLE_MEDIA" in e["p0_invariants"],"SV-004")
 req("FA3_STEP_CA_SERVICE_MUST_NOT_READ_SESSION_VAULT" in e["p0_invariants"],"SV-005")
 req("REMOVABLE_MEDIA_IS_OPTIONAL" in d["constraints"] and d["new_architectural_authorities"]==0,"SV-006")
 allowed_status={"MATERIALIZED_PENDING_REAL_CURRENT_HOST_EXECUTION","CURRENT_HOST_PASS_RUNTIME_PROMOTION_ELIGIBLE"}
 req(c["status"] in allowed_status and c["production_runtime_promoted"] is False,"SV-007")
 if c["status"]=="CURRENT_HOST_PASS_RUNTIME_PROMOTION_ELIGIBLE":
  req(c.get("current_host_receipt")=="evidence/receipts/session-vault-current-host.json","SV-007A")
  result=c.get("current_host_result") or {}
  req(result.get("result")=="PASS" and result.get("real_execution") is True and result.get("synthetic") is False,"SV-007B")
 for path in ["apps/fa3-control-center/src/SessionVaultService.cpp","apps/fa3-control-center/qml/SessionVaultPage.qml","bin/fa3-session-vault-init"]:
  req((ROOT/path).is_file(),"SV-MISSING:"+path)
 cpp=(ROOT/"apps/fa3-control-center/src/SessionVaultService.cpp").read_text()
 req("org.freedesktop.UDisks2" in cpp and "LoopSetup" in cpp and "Unlock" in cpp and "Mount" in cpp,"SV-008")
 req("secret-tool" in cpp and "application" in cpp and "session-vault" in cpp and "tryAutoUnlock" in cpp,"SV-009")
 init=(ROOT/"bin/fa3-session-vault-init").read_text()
 req("--type luks2" in init and "--pbkdf argon2id" in init and "nodev,nosuid,noexec" in init,"SV-010")
 req(not (ROOT/"apps/fa3-control-center/qml/SessionVaultLogin.qml").exists(),"SV-011")
 out={"schema":"fa3.session-vault-gate-report.v1","gate_id":"FA3-GATE-SESSION-VAULT-001","result":"PASS" if not findings else "FAIL","findings":findings}
 print(json.dumps(out,indent=2))
 return 0 if not findings else 2
if __name__=="__main__": raise SystemExit(main())
