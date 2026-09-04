#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
gate=ROOT/"src/fa3_openvid_gate.py"
out=ROOT/"evidence/reference/openvid-ci-2026-09-04.json"
p=subprocess.run([sys.executable,str(gate),"--root",str(ROOT)],capture_output=True,text=True)
report=json.loads(p.stdout)
evidence={
 "schema":"fa3.reference-evidence.v1",
 "evidence_id":"FA3-EVID-OPENVID-CI-2026-09-04",
 "subject_id":"FA3-PROVIDER-OPENVID-001",
 "gate_id":"FA3-OPENVID-GATESET-001",
 "status":report["status"],
 "execution_scope":"CANONICAL_STATIC_AND_EXECUTABLE_REGRESSION",
 "regression_count":report["regression_count"],
 "regressions":report["regressions"],
 "finding_count":report["finding_count"],
 "findings":report["findings"],
 "capability_count_after":143,
 "new_capabilities":0,
 "new_architectural_authorities":0,
 "runtime_activation_status":"DENIED_BASELINE_AND_COMMERCIAL_RUNTIME_BY_LICENSE_POLICY",
 "current_host_runtime_evidence":"NOT_CLAIMED",
 "current_host_runtime_promotion_claimed":False,
 "production_or_commercial_openvid_runtime_admitted":False
}
out.write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8")
print(json.dumps(evidence,indent=2))
raise SystemExit(p.returncode)
