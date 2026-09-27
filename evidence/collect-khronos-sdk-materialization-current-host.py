#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,platform,subprocess
from pathlib import Path
EXPECTED={
"Vulkan-Headers":"e3b1eec08173d6b825cd3ac88c885a63b621504a","Vulkan-Loader":"5f157b62e333c63260d05d81bf66faa216ab0fb8",
"Vulkan-ValidationLayers":"f4874eee15c78d7bdb2b7e60659d539f14741500","Vulkan-Profiles":"1f139a2ea3c475eed7e6699d67fc362203a69c41",
"SPIRV-Tools":"b707790a898e44038547df54580022fc1cf89c3d","glslang":"e1b562a8bed273a02f30b59b66a5d499793cede5",
"SPIRV-Cross":"aa217aeb6c9f0ace7a0ab233b28807edf45eb165","KTX-Software":"4d6fc70eaf62ad0558e63e8d97eb9766118327a6",
"glTF-Validator":"434283be08a668a8fb4e437145630ddbf93b0686","OpenXR-SDK":"f2448a8797c85814aa892efc1ab8707900fbcc78",
"OpenCL-Headers":"6fe718c31a45fe25151362a72ef041c3a1047cbd","OpenCL-ICD-Loader":"b7bd2803acc779c03d96588e9ca9e9568a18698a",
"ANARI-SDK":"7534bd263d6ff97764eda93d0e1bd6bd2f108c32","OpenVX-sample-impl":"031f44bdcd6648f0957c9e351f76c3a64a0bfc32",
"NNEF-Tools":"765d27d9095e0c90301165f8933fb325b54ddd17"}
def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=".");ap.add_argument("--sdk-root",required=True);ap.add_argument("--output",required=True);ns=ap.parse_args()
 root=Path(ns.repo_root).resolve();sdk=Path(ns.sdk_root).expanduser().resolve();src=sdk/"src"; rows=[];ok=True
 for name,want in EXPECTED.items():
  p=src/name;got=None
  if (p/".git").is_dir():
   try: got=subprocess.check_output(["git","-C",str(p),"rev-parse","HEAD"],text=True).strip()
   except Exception: got=None
  passed=got==want;ok=ok and passed;rows.append({"project":name,"expected_commit":want,"observed_commit":got,"pass":passed})
 source_commit=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
 host_basis=f"{platform.system()}|{platform.machine()}|{platform.node()}".encode()
 receipt={"schema":"fa3.khronos-sdk-materialization-current-host.v1","status":"PASS" if ok else "FAIL","evidence_level":"CURRENT_HOST_SOURCE_MATERIALIZATION_ONLY",
  "source_commit":source_commit,"host_fingerprint_sha256":hashlib.sha256(host_basis).hexdigest(),"sdk_root_class":"XDG_DATA_HOME_FA3_NAMESPACED",
  "projects":rows,"hardware_parameter_mutation":False,"system_package_replacement":False,"global_environment_mutation":False,
  "runtime_execution_claim":False,"current_host_runtime_promotion_claim":False,"global_promotion_claim":False}
 out=Path(ns.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps(receipt,indent=2,sort_keys=True));return 0 if ok else 2
if __name__=="__main__":raise SystemExit(main())
