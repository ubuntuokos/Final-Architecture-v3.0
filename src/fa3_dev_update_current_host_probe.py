#!/usr/bin/env python3
from __future__ import annotations
import json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(cmd):
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    return {"command":cmd,"returncode":p.returncode,"stdout":p.stdout.strip()[:4000],"stderr":p.stderr.strip()[:4000]}
def main():
    outdir=ROOT/"reports/dev-update-current-host";outdir.mkdir(parents=True,exist_ok=True)
    facts={"schema":"fa3.dev-update-current-host-probe.v2","captured_unix":int(time.time()),"claims":[],"non_claims":["CURRENT_HOST_E2E_PASS","GLOBAL_FA3_PROMOTION"],"uid":os.getuid(),"euid":os.geteuid(),"hardware_boundary":{"discovery":"FA3-HARDWARE-DISCOVERY-CONTRACTS-001","accelerator_cardinality":"0..N","cpu_only_valid":True,"global_vendor_pin":None,"provider_specific_probes_optional":True},"tools":{"apt-get":shutil.which("apt-get"),"unattended-upgrade":shutil.which("unattended-upgrade"),"needrestart":shutil.which("needrestart"),"notify-send":shutil.which("notify-send"),"nvidia-smi":shutil.which("nvidia-smi")},"reboot_required":Path("/var/run/reboot-required").exists(),"os_release":{},"checks":{}}
    p=Path("/etc/os-release")
    if p.exists():
      for line in p.read_text(encoding="utf-8",errors="replace").splitlines():
        if "=" in line:
          k,v=line.split("=",1);facts["os_release"][k]=v.strip(chr(34))
    facts["checks"]["canonical_gate"]=run([sys.executable,str(ROOT/"src/fa3_dev_update_gate.py")])
    facts["checks"]["static_gate"]=run([str(ROOT/"bin/fa3-enforce"),"static"])
    if shutil.which("nvidia-smi"): facts["checks"]["optional_provider_specific_accelerator_observation"]=run(["nvidia-smi","--query-compute-apps=pid,process_name,used_memory","--format=csv,noheader,nounits"])
    with tempfile.TemporaryDirectory() as td:
      script="import json,pathlib,fa3_update_fabric as u; u.STATE_DIR=pathlib.Path("+repr(td)+"); u.RESTART_STATE=u.STATE_DIR/\'restart-required.json\'; u.set_restart_required(\'host\',[\'kernel\'],[\'protected-probe-workload\']); print(json.dumps(u.choose_restart(\'RESTART_NOW\',[\'protected-probe-workload\'],None)))"
      facts["checks"]["protected_workload_restart_arbitration"]=run([sys.executable,"-c",script])
    blockers=[n for n in ("canonical_gate","static_gate","protected_workload_restart_arbitration") if facts["checks"].get(n,{}).get("returncode")!=0]
    facts["status"]="REFERENCE_PROBE_PASS_CURRENT_HOST_E2E_PENDING" if not blockers else "FAIL";facts["blocking_findings"]=blockers
    out=outdir/"current-host-probe.json";out.write_text(json.dumps(facts,indent=2,ensure_ascii=False)+"\n",encoding="utf-8");print(json.dumps(facts,indent=2,ensure_ascii=False))
    return 0 if not blockers else 2
if __name__=="__main__":raise SystemExit(main())
