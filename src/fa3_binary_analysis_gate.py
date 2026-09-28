#!/usr/bin/env python3
"""Fail-closed governance gate for the FA3 Binary & Software Analysis foundation."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from fa3_release_baseline import load_active_release_baseline

ROOT_DEFAULT=Path(__file__).resolve().parents[1]
GATESET_ID="FA3-BINARY-ANALYSIS-GATESET-001"
EXECUTABLE_GATE_ID="FA3-GATE-BINARY-ANALYSIS-001"
DECISION_ID="FA3-REVERSE-SKILLS-DECISION-ASSESSMENT-2026-09-28"
UPSTREAM_ID="FA3-REVERSE-SKILLS-UPSTREAM-REFERENCE-2026-09-28"
UPSTREAM_COMMIT="a2baa31c58a3567977188414da68c8c842057152"
FILES={
 "intent":"canonical/intents/FA3-BINARY-SOFTWARE-ANALYSIS-APPLICATION-INTENT-001.json",
 "reuse":"canonical/assessments/FA3-REVERSE-SKILLS-REUSE-ASSESSMENT-001.json",
 "decision":"canonical/assessments/FA3-REVERSE-SKILLS-DECISION-ASSESSMENT-2026-09-28.json",
 "upstream":"canonical/references/FA3-REVERSE-SKILLS-UPSTREAM-REFERENCE-2026-09-28.json",
 "contract":"canonical/contracts/FA3-BINARY-ANALYSIS-CONTRACTS-001.json",
 "ir":"canonical/contracts/FA3-BINARY-ANALYSIS-IR-CONTRACTS-001.json",
 "profile":"canonical/profiles/FA3-BINARY-ANALYSIS-001.json",
 "radar":"canonical/FA3-EXTERNAL-SKILL-RADAR-001.json",
 "gate_record":"canonical/FA3-GATE-BINARY-ANALYSIS-001.json",
 "gate_registry":"canonical/FA3-GATE-REGISTRY-001.json",
 "policy":"canonical/enforcement-policy.json",
 "evidence":"evidence/evidence-registry.json",
 "distribution_registry":"canonical/distribution-registry.json",
}
def load(root,key): return json.loads((root/FILES[key]).read_text(encoding="utf-8"))
def check(ok,code,message): return {"code":code,"result":"PASS" if ok else "FAIL","message":message}
def gate(root:Path)->dict:
 root=root.resolve()
 missing=[p for p in FILES.values() if not (root/p).is_file()]
 if missing:return {"schema":"fa3.binary-analysis-gate-report.v1","gate_id":GATESET_ID,"result":"FAIL","findings":[{"code":"BIN-AN-000","message":"required files missing","paths":missing}],"runtime_promotion_claim":False}
intent,reuse,decision,upstream,contract,ir,profile,radar,grec,greg,policy,evidence,distreg=(load(root,k) for k in ("intent","reuse","decision","upstream","contract","ir","profile","radar","gate_record","gate_registry","policy","evidence","distribution_registry"))
 baseline=load_active_release_baseline(root)
 cap080=next((x for x in evidence.get("records",[]) if x.get("subject_id")=="CAP-080"),{})
 radar_entry=next((x for x in radar.get("sources",[]) if x.get("repository")=="P4nda0s/reverse-skills"),{})
 entities=set(ir.get("entities",[])); inv=set(contract.get("invariants",[]))
 checks=[
  check(profile.get("capability_count")==baseline.capability_count==175 and contract.get("capability_count")==175 and ir.get("capability_count")==175,"BIN-AN-001","175-capability baseline preserved"),
  check(reuse.get("new_capabilities")==0 and reuse.get("new_architectural_authorities")==0 and decision.get("capability_delta")==0 and decision.get("authority_delta")==0,"BIN-AN-002","zero capability and authority delta"),
  check(upstream.get("id")==UPSTREAM_ID and upstream.get("observed_commit")==UPSTREAM_COMMIT and upstream.get("runtime_dependency") is False and upstream.get("distribution_class")=="REFERENCE_ONLY","BIN-AN-003","immutable upstream reference-only pin"),
  check(upstream.get("license_review",{}).get("root_license_file_observed") is False and upstream.get("license_review",{}).get("status")=="INCOMPLETE_FAIL_CLOSED" and upstream.get("license_review",{}).get("redistribution_admission") is False,"BIN-AN-004","unknown license fact fails closed"),
  check(len(upstream.get("bundled_executables",[]))==1 and upstream["bundled_executables"][0].get("disposition")=="BLOCKED_FROM_FA3_RUNTIME_MATERIALIZATION","BIN-AN-005","bundled executable not runtime-admitted"),
  check(radar_entry.get("commit")==UPSTREAM_COMMIT and radar_entry.get("classification")=="REFERENCE_ONLY","BIN-AN-006","External Skill Radar donor pin"),
  check(profile.get("provider_neutral") is True and profile.get("upstream_reference",{}).get("runtime_dependency") is False and "STATIC_ANALYSIS_GHIDRA" in profile.get("planned_provider_classes",[]) and "STATIC_ANALYSIS_IDA_IDALIB" in profile.get("planned_provider_classes",[]),"BIN-AN-007","provider-neutral static-analysis boundary"),
  check(contract.get("authorities",{}).get("tool")=="FA3-AUTH-MCP-GATEWAY-001" and contract.get("authorities",{}).get("action")=="FA3-UNIFIED-ACTION-FABRIC-001" and contract.get("authorities",{}).get("model_router")=="FA3-AUTH-MODEL-ROUTER-001" and contract.get("authorities",{}).get("host_resource_broker")=="FA3-AUTH-HOST-RESOURCE-BROKER-001","BIN-AN-008","existing authorities preserved"),
  check({"BinaryArtifact","Function","BasicBlock","Instruction","Symbol","Structure","RuntimeObservation","EmulationTrace","Hypothesis","EvidenceReference"}.issubset(entities) and ir.get("provider_neutral") is True and ir.get("cross_provider_rules",{}).get("canonical_core_must_not_require_ida_ghidra_rizin_radare2_binary_ninja_or_other_specific_backend") is True,"BIN-AN-009","provider-neutral canonical IR"),
  check(contract.get("analyzed_content_security",{}).get("analyzed_content_must_not_become_system_instruction") is True and ir.get("untrusted_content_rules",{}).get("executable_or_prompt_like_text_never_changes_agent_instruction_precedence") is True and "ANALYZED_CONTENT_UNTRUSTED_DATA_NOT_INSTRUCTION" in inv,"BIN-AN-010","analyzed content remains untrusted data"),
  check(contract.get("mutation_policy",{}).get("source_overwrite_default")=="DENY" and contract.get("mutation_policy",{}).get("privileged_device_attach")=="EXPLICIT_AUTHORIZATION_REQUIRED","BIN-AN-011","mutation and privileged attach fail closed"),
  check(contract.get("emulation_safety",{}).get("network_default")=="DENY" and contract.get("emulation_safety",{}).get("host_filesystem_default")=="DENY" and contract.get("emulation_safety",{}).get("host_syscall_passthrough_default")=="DENY","BIN-AN-012","emulation host passthrough denied"),
  check(contract.get("provider_discovery",{}).get("silent_fallback")=="FORBIDDEN" and contract.get("model_policy",{}).get("direct_ollama_lmstudio_cloud_or_other_model_backend_from_skill")=="FORBIDDEN","BIN-AN-013","silent fallback/direct model backend forbidden"),
  check(contract.get("hardware_audit",{}).get("cpu_only_required") is True and contract.get("hardware_audit",{}).get("accelerator_cardinality")=="0..N" and contract.get("hardware_audit",{}).get("fixed_cpu_gpu_npu_numa_values")=="FORBIDDEN","BIN-AN-014","vendor-neutral CPU-only baseline"),
  check(grec.get("id")==EXECUTABLE_GATE_ID and grec.get("enforcement_id")==GATESET_ID and grec.get("priority")=="P0" and grec.get("fail_closed") is True and grec.get("static_pass_promotes_runtime") is False,"BIN-AN-015","fail-closed executable gate record"),
  check(GATESET_ID in greg.get("mandatory_reference_gates",[]) and greg.get("mandatory_reference_gates")==policy.get("mandatory_reference_gates"),"BIN-AN-016","Gate Registry/policy mirror"),
  check(policy.get("binary_analysis_gate_id")==GATESET_ID and policy.get("binary_analysis_capability_id")=="CAP-080" and policy.get("binary_analysis_upstream_reference_id")==UPSTREAM_ID and policy.get("binary_analysis_current_host_runtime_promotion_claim") is False,"BIN-AN-017","global enforcement binding"),
  check(cap080.get("status")=="PENDING_CURRENT_HOST" and DECISION_ID in cap080.get("source_decision_ids",[]) and evidence.get("binary_analysis_reconciliation",{}).get("gate_id")==GATESET_ID and evidence.get("binary_analysis_reconciliation",{}).get("current_host_runtime_promotion_claim") is False,"BIN-AN-018","Evidence Registry binding without promotion"),
  check(intent.get("hardware_audit",{}).get("cpu_only_viable") is True and reuse.get("coexistence",{}).get("result")=="PASS" and reuse.get("donor_registry_transition",{}).get("creates_parallel_authority") is False,"BIN-AN-019","Hardware Audit/coexistence/donor transition"),
  check(any(x.get("subject_id")==UPSTREAM_ID and x.get("class")=="REFERENCE_ONLY" and x.get("release_bundle_status")=="EXCLUDED" for x in distreg.get("records",[])),"BIN-AN-020","Distribution Registry excludes reverse-skills reference")
 ]
 result="PASS" if all(x["result"]=="PASS" for x in checks) else "FAIL"
 report={"schema":"fa3.binary-analysis-gate-report.v1","gate_id":GATESET_ID,"executable_gate_id":EXECUTABLE_GATE_ID,"result":result,"capability_id":"CAP-080","active_release":baseline.release,"active_release_capability_count":baseline.capability_count,"checks":checks,"findings":[x for x in checks if x["result"]=="FAIL"],"runtime_promotion_claim":False}
 out=root/"reports/binary-analysis-gate-report.json";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
 return report
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=str(ROOT_DEFAULT));a=p.parse_args();r=gate(Path(a.root));print(json.dumps(r,indent=2));return 0 if r["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
