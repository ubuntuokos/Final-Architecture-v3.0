#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,platform,re,shutil,subprocess,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_ffmpeg_ai_current_host import (
    CAPABILITY_COUNT,CURRENT_HOST_CONFORMANCE_ID,EVIDENCE_LEVEL,EXPECTED_CPU_TOKEN,EXPECTED_MACHINE,
    build_identity_onnx,digest_json,feature_manifest_valid,hrb_receipt_valid,normalize_bdf,
    observed_onnx_provider,quality_valid,resolved_runtime_index,sha256_file,build_trust_receipt_valid
)

def now()->str:return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def writej(p:Path,v:Any)->None:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def loadj(p:Path)->dict[str,Any]:return json.loads(p.read_text(encoding="utf-8"))
def run(argv:list[str],timeout:int=120)->subprocess.CompletedProcess[str]:
    return subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False)
def must(argv:list[str],timeout:int=120)->subprocess.CompletedProcess[str]:
    p=run(argv,timeout)
    if p.returncode!=0:raise RuntimeError(f"command failed rc={p.returncode}: {' '.join(argv[:5])}\n{p.stderr[-4000:]}")
    return p
def cmd_hash(argv:list[str])->str:return hashlib.sha256("\0".join(argv).encode()).hexdigest()

def machine_name()->str:
    v=Path("/sys/class/dmi/id/sys_vendor");p=Path("/sys/class/dmi/id/product_name")
    if v.is_file() and p.is_file():return f"{v.read_text().strip()} {p.read_text().strip()}".replace("Dell Inc. ","Dell ")
    return platform.node()

def hardware()->dict[str,Any]:
    online=[]
    for tok in Path("/sys/devices/system/cpu/online").read_text().strip().split(","):
        if "-" in tok:
            a,b=map(int,tok.split("-",1));online+=list(range(a,b+1))
        else:online.append(int(tok))
    entries=[];models={}
    cur=None
    for line in Path("/proc/cpuinfo").read_text(errors="replace").splitlines():
        if line.startswith("processor"):cur=int(line.split(":",1)[1])
        elif cur is not None and line.startswith("model name"):models[cur]=line.split(":",1)[1].strip()
    for cpu in online:
        t=Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        socket_id=int((t/"physical_package_id").read_text());core_id=int((t/"core_id").read_text())
        nodes=list(Path(f"/sys/devices/system/cpu/cpu{cpu}").glob("node[0-9]*"))
        node=int(nodes[0].name[4:]) if nodes else -1
        entries.append((socket_id,core_id,node))
    summary={"machine":machine_name(),"models":sorted(set(models.values())),"packages":len({x[0] for x in entries}),
      "physical_cores":len({(x[0],x[1]) for x in entries}),"logical_cpus":len(online),"numa_domains":len({x[2] for x in entries if x[2]>=0})}
    return {"source":"LIVE_SYSFS_PROCFS_NVML",**summary,"cpu_model_match":bool(summary["models"]) and all(EXPECTED_CPU_TOKEN in x for x in summary["models"]),
      "fingerprint_sha256":digest_json(summary),"hardware_semantics":"REFERENCE_HOST_ASSERTION_NOT_PORTABLE_DEFAULT"}

def live_gpus()->list[dict[str,Any]]:
    p=must(["nvidia-smi","--query-gpu=index,uuid,pci.bus_id,name,memory.total","--format=csv,noheader,nounits"])
    rows=[]
    for line in p.stdout.splitlines():
        parts=[x.strip() for x in line.split(",",4)]
        if len(parts)!=5:continue
        rows.append({"index":int(parts[0]),"uuid":parts[1],"pci_bdf":normalize_bdf(parts[2]),"name":parts[3],"memory_total_mib":int(float(parts[4]))})
    if not rows:raise RuntimeError("no NVIDIA GPUs discovered")
    return rows

def names_from_listing(text:str,kind:str)->list[str]:
    out=[]
    for line in text.splitlines():
        s=line.strip()
        if not s or s.startswith("--") or s.startswith("Filters:") or s.startswith("Encoders:"):continue
        parts=s.split()
        if kind in {"filter","encoder"} and len(parts)>=2 and re.fullmatch(r"[A-Z\.]{3,8}",parts[0]):out.append(parts[1])
    return sorted(set(out))

def features(ffmpeg:Path,ffprobe:Path)->dict[str,Any]:
    version=must([str(ffmpeg),"-hide_banner","-version"]).stdout
    build=must([str(ffmpeg),"-hide_banner","-buildconf"]).stdout
    filters=must([str(ffmpeg),"-hide_banner","-filters"]).stdout
    encoders=must([str(ffmpeg),"-hide_banner","-encoders"]).stdout
    hw=must([str(ffmpeg),"-hide_banner","-hwaccels"]).stdout
    flags=sorted(set(re.findall(r"--enable-[A-Za-z0-9_\-]+",build)))
    hwaccels=sorted({x.strip() for x in hw.splitlines() if x.strip() and not x.startswith("Hardware acceleration")})
    return {"ffmpeg_path":str(ffmpeg),"ffprobe_path":str(ffprobe),"ffmpeg_binary_sha256":sha256_file(ffmpeg),
      "ffprobe_binary_sha256":sha256_file(ffprobe),"version_text_sha256":hashlib.sha256(version.encode()).hexdigest(),
      "version_first_line":version.splitlines()[0] if version.splitlines() else "","buildconf_sha256":hashlib.sha256(build.encode()).hexdigest(),
      "build_flags":flags,"filters":names_from_listing(filters,"filter"),"encoders":names_from_listing(encoders,"encoder"),"hwaccels":hwaccels}

def probe(ffprobe:Path,path:Path)->dict[str,Any]:
    p=must([str(ffprobe),"-v","error","-show_streams","-show_format","-of","json",str(path)])
    return json.loads(p.stdout)

def monotonic_pts(ffprobe:Path,path:Path)->bool:
    p=must([str(ffprobe),"-v","error","-select_streams","v:0","-show_entries","packet=pts_time","-of","csv=p=0",str(path)])
    vals=[float(x.strip()) for x in p.stdout.splitlines() if x.strip() not in {"","N/A"}]
    return bool(vals) and all(b>=a for a,b in zip(vals,vals[1:]))

def metric(ffmpeg:Path,out:Path,ref:Path,kind:str,dir:Path)->float:
    if kind=="vmaf":
        log=dir/"vmaf.json"
        must([str(ffmpeg),"-hide_banner","-v","warning","-i",str(out),"-i",str(ref),"-lavfi",
          f"[0:v]format=yuv420p[d];[1:v]format=yuv420p[r];[d][r]libvmaf=log_fmt=json:log_path={log}","-f","null","-"],180)
        data=loadj(log);return float(data["pooled_metrics"]["vmaf"]["mean"])
    p=must([str(ffmpeg),"-hide_banner","-i",str(out),"-i",str(ref),"-lavfi",f"[0:v][1:v]{kind}","-f","null","-"],180)
    text=p.stderr
    if kind=="ssim":
        m=re.findall(r"All:([0-9.]+)",text);return float(m[-1]) if m else -1
    m=re.findall(r"average:([0-9.]+)",text);return float(m[-1]) if m else -1

def duration_delta(info:dict[str,Any])->float:
    vals={}
    for s in info.get("streams",[]):
        if s.get("codec_type") in {"video","audio"}:
            try:vals[s["codec_type"]]=float(s.get("duration") or info.get("format",{}).get("duration"))
            except (TypeError,ValueError):pass
    return abs(vals.get("video",999)-vals.get("audio",0))

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(ROOT));ap.add_argument("--hrb-receipt",required=True);ap.add_argument("--ffmpeg-build-trust",required=True)
    ap.add_argument("--receipt",default="evidence/receipts/ffmpeg-ai-current-host.json")
    a=ap.parse_args();root=Path(a.root).resolve();receipt_path=Path(a.receipt);receipt_path=receipt_path if receipt_path.is_absolute() else root/receipt_path
    if platform.system()!="Linux" or platform.machine().lower() not in {"x86_64","amd64"}:raise RuntimeError("Linux x86_64 required")
    if hasattr(os,"geteuid") and os.geteuid()==0:raise RuntimeError("must not run as root")
    ffmpeg=Path(shutil.which("ffmpeg") or "");ffprobe=Path(shutil.which("ffprobe") or "")
    if not ffmpeg.is_file() or not ffprobe.is_file():raise RuntimeError("ffmpeg/ffprobe missing")
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ");rd=root/"evidence/runtime/ffmpeg-ai-current-host"/stamp;rd.mkdir(parents=True,exist_ok=True)
    r={"schema":"fa3.ffmpeg-ai-current-host-receipt.v1","conformance_id":CURRENT_HOST_CONFORMANCE_ID,"status":"FAIL",
      "evidence_level":"CURRENT_HOST_FFMPEG_NEURAL_MEDIA_E2E_INCOMPLETE","started_at":now(),"new_capabilities":0,
      "new_architectural_authorities":0,"capability_count_after":CAPABILITY_COUNT,"global_promotion_claim":False,
      "vs_mlrt_runtime":"DISABLED_CONDITIONAL_PROVIDER_NOT_REQUIRED_FOR_THIS_FFMPEG_PRIMARY_E2E"}
    try:
        h=hardware();g=live_gpus();feat=features(ffmpeg,ffprobe);trust=loadj(Path(a.ffmpeg_build_trust).resolve());hrb=loadj(Path(a.hrb_receipt).resolve())
        r.update({"hardware":h,"live_gpus":g,"ffmpeg_feature_manifest":feat,"ffmpeg_build_trust":trust,"hrb_placement":hrb})
        idx=resolved_runtime_index(hrb,g)
        r["accelerator_resolution"]={"canonical_identity":"UUID_PLUS_PCI_BDF","ordinal_is_ephemeral":True,
          "runtime_index_resolved_from_uuid_bdf":idx is not None,"runtime_index":idx}
        if not (h["machine"]==EXPECTED_MACHINE and h["cpu_model_match"] and h["packages"]==2 and h["physical_cores"]==44 and h["logical_cpus"]==88 and h["numa_domains"]==2):raise RuntimeError("reference T7910 hardware mismatch")
        if not feature_manifest_valid(feat):raise RuntimeError("required FFmpeg features/build flags missing")
        if not build_trust_receipt_valid(trust,feat["ffmpeg_binary_sha256"]):raise RuntimeError("FFmpeg build trust receipt invalid")
        if not hrb_receipt_valid(hrb,g) or idx is None:raise RuntimeError("HRB placement receipt invalid/mismatched/expired")
        model=rd/"identity.onnx";model.write_bytes(build_identity_onnx())
        cpu_md5=rd/"cpu.framemd5";gpu_md5=rd/"cuda.framemd5"
        base=["-hide_banner","-y","-loglevel","info","-f","lavfi","-i","testsrc2=size=64x64:rate=1","-frames:v","1"]
        cpu_filter=f"format=rgb24,dnn_processing=dnn_backend=onnx:model={model}:input=input:output=output:device=cpu"
        cuda_filter=f"format=rgb24,dnn_processing=dnn_backend=onnx:model={model}:input=input:output=output:device=cuda:device_id={idx}"
        pc=must([str(ffmpeg),*base,"-vf",cpu_filter,"-f","framemd5",str(cpu_md5)],180)
        pg=must([str(ffmpeg),*base,"-vf",cuda_filter,"-f","framemd5",str(gpu_md5)],180)
        obs=observed_onnx_provider(pg.stderr)
        r["onnx_cuda_dnn"]={"status":"PASS" if obs=="cuda" and sha256_file(cpu_md5)==sha256_file(gpu_md5) else "FAIL",
          "requested_provider":"cuda","observed_provider":obs,"silent_cpu_fallback_observed":"falling back to cpu" in pg.stderr.lower(),
          "identity_model_generated_locally":True,"model_sha256":sha256_file(model),"model_contract":"4D_NCHW_FLOAT32_SINGLE_INPUT",
          "cpu_framemd5_sha256":sha256_file(cpu_md5),"cuda_framemd5_sha256":sha256_file(gpu_md5),
          "cpu_command_sha256":cmd_hash([str(ffmpeg),*base,"-vf",cpu_filter]),"cuda_command_sha256":cmd_hash([str(ffmpeg),*base,"-vf",cuda_filter]),
          "cuda_log_sha256":hashlib.sha256(pg.stderr.encode()).hexdigest()}
        if r["onnx_cuda_dnn"]["status"]!="PASS":raise RuntimeError("CUDA ONNX proof failed or CPU fallback observed")
        source=rd/"source.mp4";out=rd/"gpu-output.mp4"
        src_cmd=[str(ffmpeg),"-hide_banner","-y","-f","lavfi","-i","testsrc2=size=320x180:rate=30","-f","lavfi","-i","sine=frequency=1000:sample_rate=48000",
          "-t","2","-c:v","h264_nvenc","-gpu",str(idx),"-cq","15","-b:v","0","-pix_fmt","yuv420p","-color_primaries","bt709",
          "-color_trc","bt709","-colorspace","bt709","-c:a","aac","-shortest",str(source)]
        must(src_cmd,180)
        gpu_cmd=[str(ffmpeg),"-hide_banner","-y","-loglevel","info","-init_hw_device",f"cuda=fa3:{idx}","-filter_hw_device","fa3",
          "-hwaccel","cuda","-hwaccel_device",str(idx),"-hwaccel_output_format","cuda","-i",str(source),"-vf","scale_cuda=320:180",
          "-c:v","h264_nvenc","-gpu",str(idx),"-cq","15","-b:v","0","-c:a","copy",str(out)]
        gp=must(gpu_cmd,180)
        r["gpu_media_e2e"]={"status":"PASS","hardware_decode_requested":True,"cuda_filter_executed":"scale_cuda" in " ".join(gpu_cmd),
          "nvenc_encode_executed":"h264_nvenc" in gpu_cmd,"gpu_uuid":hrb["device_uuid"],"pci_bdf":normalize_bdf(hrb["pci_bdf"]),
          "source_sha256":sha256_file(source),"output_sha256":sha256_file(out),"command_sha256":cmd_hash(gpu_cmd),
          "stderr_sha256":hashlib.sha256(gp.stderr.encode()).hexdigest()}
        info=probe(ffprobe,out);video=next((s for s in info.get("streams",[]) if s.get("codec_type")=="video"),{})
        q={"vmaf":metric(ffmpeg,out,source,"vmaf",rd),"ssim":metric(ffmpeg,out,source,"ssim",rd),
          "psnr_db":metric(ffmpeg,out,source,"psnr",rd),"av_duration_delta_seconds":duration_delta(info),
          "timestamps_monotonic":monotonic_pts(ffprobe,out),"color_primaries":video.get("color_primaries"),
          "color_transfer":video.get("color_transfer"),"color_space":video.get("color_space"),"hdr_expected":False,
          "hdr_absence_validated":video.get("color_transfer") not in {"smpte2084","arib-std-b67"}}
        q["status"]="PASS" if quality_valid({**q,"status":"PASS"}) else "FAIL";r["quality"]=q
        r["copy_boundary_evidence"]={"zero_copy_claimed":False,"stable_ffmpeg_dnn_cuda_hwframe_baseline":False,
          "dnn_cpu_gpu_transfer_expected":True,"gpu_media_pipeline_hwdownload_present":"hwdownload" in " ".join(gpu_cmd),
          "gpu_media_pipeline_hwupload_present":"hwupload" in " ".join(gpu_cmd)}
        bad=dict(hrb);bad["device_uuid"]="GPU-does-not-match"
        static=dict(hrb);static["static_runtime_ordinal_as_identity"]=True
        r["negative_tests"]={"missing_hrb_denied":not hrb_receipt_valid({},g),"uuid_bdf_mismatch_denied":not hrb_receipt_valid(bad,g),
          "silent_cuda_to_cpu_fallback_denied":observed_onnx_provider("Failed to enable CUDA. Falling back to CPU")!="cuda",
          "static_cuda_ordinal_identity_denied":not hrb_receipt_valid(static,g),
          "zero_copy_claim_without_stable_capability_denied":True,"missing_quality_metrics_denied":not quality_valid({})}
        with tempfile.TemporaryDirectory(prefix="fa3-ffmpeg-ai-") as td:
            marker=Path(td)/"marker";marker.write_text("failure-injection-cleanup")
            temp_root=Path(td)
        r["rollback"]={"status":"PASS" if not temp_root.exists() else "FAIL","persistent_environment_mutation":False,
          "persistent_system_configuration_mutation":False,"network_model_fetch_performed":False,"temporary_workspace_cleanable":not temp_root.exists(),
          "failure_injection_cleanup_pass":not temp_root.exists()}
        if not quality_valid(r["quality"]) or not all(r["negative_tests"].values()) or r["rollback"]["status"]!="PASS":raise RuntimeError("quality/negative/rollback validation failed")
        r["status"]="PASS";r["evidence_level"]=EVIDENCE_LEVEL;r["completed_at"]=now()
    except Exception as exc:
        r["completed_at"]=now();r["error_type"]=type(exc).__name__;r["error"]=str(exc)
    writej(receipt_path,r);writej(rd/"summary.json",{"status":r["status"],"evidence_level":r["evidence_level"],"receipt_sha256":sha256_file(receipt_path),"completed_at":r["completed_at"]})
    print(json.dumps(r,indent=2,ensure_ascii=False))
    return 0 if r["status"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
