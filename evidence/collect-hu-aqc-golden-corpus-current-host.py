#!/usr/bin/env python3
from __future__ import annotations
import argparse,importlib.util,json
from pathlib import Path
from typing import Any
from fa3_release_baseline import module_active_capability_count

def loadj(p:Path)->dict[str,Any]:return json.loads(p.read_text(encoding="utf-8"))
def writej(p:Path,o:dict[str,Any])->None:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def load_single(root:Path):
    path=root/"evidence/collect-hu-aqc-current-host.py"
    spec=importlib.util.spec_from_file_location("fa3_hu_aqc_single",path)
    if spec is None or spec.loader is None:raise RuntimeError("cannot load HU-AQC single-sample collector")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def collect(root:Path,manifest_path:Path,output:Path)->dict[str,Any]:
    profile=loadj(root/"canonical/profiles/FA3-HU-AQC-001.json")
    required=set(profile.get("golden_corpus",{}).get("categories",[]))
    receipt={"schema":"fa3.hu-aqc-golden-corpus-current-host-receipt.v1","surface":"HU_AQC_GOLDEN_CORPUS","locale":"hu-HU","synthetic":False,"global_promotion_claim":False,"capability_count":module_active_capability_count(__file__)}
    try:
        manifest=loadj(manifest_path)
        if manifest.get("schema")!="fa3.hu-aqc-golden-corpus-manifest.v1" or manifest.get("locale")!="hu-HU":raise RuntimeError("golden corpus manifest schema/locale mismatch")
        entries=manifest.get("entries",[])
        if not isinstance(entries,list) or not entries:raise RuntimeError("golden corpus entries missing")
        categories={str(e.get("category")) for e in entries}
        missing=sorted(required-categories)
        if missing:raise RuntimeError("golden corpus category coverage missing: "+",".join(missing))
        single=load_single(root);results=[]
        tmp=root/".fa3-current-host/hu-aqc-golden";tmp.mkdir(parents=True,exist_ok=True)
        for i,e in enumerate(entries):
            category=str(e.get("category",""));eid=str(e.get("id") or f"entry-{i}")
            audio=Path(str(e.get("audio","")));audio=audio if audio.is_absolute() else root/audio
            metrics=Path(str(e.get("metrics_json","")));metrics=metrics if metrics.is_absolute() else root/metrics
            provenance_ref=str(e.get("provenance_ref","")).strip()
            if not provenance_ref:raise RuntimeError("golden sample provenance_ref missing")
            bundle=loadj(metrics)
            cloning=bool(bundle.get("cloning",False))
            if category=="VOICE_CLONING_WITH_CONSENT_WHEN_APPLICABLE" and not cloning:raise RuntimeError("voice-cloning category requires cloning=true scorer bundle")
            if cloning and (e.get("consent_status")!="GRANTED" or not str(e.get("consent_ref","")).strip()):raise RuntimeError("cloning sample lacks GRANTED consent and consent_ref")
            child_out=tmp/(eid+".json")
            row=single.collect(root,audio=audio.resolve(),metrics_path=metrics.resolve(),output=child_out)
            results.append({"id":eid,"category":category,"provenance_ref":provenance_ref,"consent_ref":e.get("consent_ref") if cloning else None,"result":row.get("result"),"status":row.get("status"),"asr_metrics":row.get("asr_metrics"),"aqc":row.get("aqc"),"audio_sha256":row.get("audio_sha256"),"metrics_input_sha256":row.get("metrics_input_sha256")})
        failed=[x for x in results if x["result"]!="PASS"]
        if failed:raise RuntimeError("one or more golden-corpus samples failed")
        wers=[float(x["asr_metrics"]["wer"]) for x in results];cers=[float(x["asr_metrics"]["cer"]) for x in results]
        receipt.update({"result":"PASS","status":"CURRENT_HOST_PASS","required_categories":sorted(required),"observed_categories":sorted(categories),"sample_count":len(results),"worst_asr_wer":max(wers),"worst_asr_cer":max(cers),"samples":results,"thresholds":profile.get("default_thresholds",{}),"threshold_relaxation_performed":False})
    except Exception as exc:
        receipt.update({"result":"PENDING","status":"PENDING_CURRENT_HOST","error_type":type(exc).__name__,"error":str(exc)})
    writej(output,receipt);return receipt

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));p.add_argument("--manifest",required=True);p.add_argument("--output",default="evidence/receipts/hu-aqc-golden-corpus-current-host.json");a=p.parse_args()
    root=Path(a.root).resolve();out=Path(a.output);out=out if out.is_absolute() else root/out
    r=collect(root,Path(a.manifest).resolve(),out);print(json.dumps(r,indent=2,ensure_ascii=False));return 0 if r["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
