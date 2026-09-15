#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
RULES=18; PIN='c64067bd45768b45287cb4ca53f76c9fb5a037e1'
PATHS=['canonical/providers/FA3-PROVIDER-DIFFUSION-STUDIO-001.json','canonical/references/FA3-DIFFUSION-STUDIO-UPSTREAM-REFERENCE-2026-09-05.json','canonical/decisions/FA3-DEC-DIFFUSION-STUDIO-LINUX-DESKTOP-2026-09-05.json','canonical/FA3-GATE-DIFFUSION-STUDIO-001.json','canonical/diffusion-studio-enforcement.json','canonical/diffusion-studio-runtime-admission.json','src/fa3_diffusion_studio_adapter.py','packaging/diffusion-studio/build-fa3-deb.sh']
def gate(root:Path):
 root=Path(root);f=[]
 for p in PATHS:
  if not (root/p).is_file():f.append({'code':'DS-001','path':p})
 if f:return {'result':'FAIL','findings':f}
 provider=json.loads((root/PATHS[0]).read_text());ref=json.loads((root/PATHS[1]).read_text());gr=json.loads((root/PATHS[3]).read_text());enf=json.loads((root/PATHS[4]).read_text());adm=json.loads((root/PATHS[5]).read_text())
 checks=[provider.get('upstream',{}).get('commit')==PIN,ref.get('commit')==PIN,provider.get('new_capability') is False,provider.get('architectural_authority') is False,provider.get('capability_projection')==['CAP-121','CAP-126'],provider.get('linux_desktop',{}).get('session')=='Wayland-first',provider.get('agent_integration',{}).get('central_mcp_gateway_required') is True,provider.get('agent_integration',{}).get('ui_mouse_keyboard_automation_as_primary_boundary') is False,gr.get('fail_closed') is True,gr.get('rule_count')==RULES,len(enf.get('rules',[]))==RULES,adm.get('current_host_runtime_promotion_claimed') is False,adm.get('capability_count_after')==143]
 if not all(checks):f.append({'code':'DS-002','message':'canonical invariant drift'})
 text=(root/'packaging/diffusion-studio/build-fa3-deb.sh').read_text()
 for token in [PIN,'--ozone-platform=wayland','dpkg-deb --build','npm ci','npm run package']:
  if token not in text:f.append({'code':'DS-003','token':token})
 return {'result':'PASS' if not f else 'FAIL','findings':f,'rule_count':RULES}
if __name__=='__main__':
 import sys;r=gate(Path(sys.argv[1] if len(sys.argv)>1 else '.'));print(json.dumps(r,indent=2));raise SystemExit(0 if r['result']=='PASS' else 2)
