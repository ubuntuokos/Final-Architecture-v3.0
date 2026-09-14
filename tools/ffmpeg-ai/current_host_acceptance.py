#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, re, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn


def fail(message: str) -> NoReturn:
    raise SystemExit(f"FAIL-CLOSED: {message}")


def load_json(path: Path) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: fail(f"cannot load JSON {path}: {exc}")


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def require_attestation(path: Path) -> dict[str, Any]:
    doc=load_json(path); digest=str(doc.get('sha256') or doc.get('host_attestation_sha256') or '')
    if doc.get('qualified') is not True or not re.fullmatch(r'[0-9a-f]{64}',digest): fail('qualified immutable host attestation required')
    return {'sha256':digest,'document':doc}


def require_cuda_ep() -> list[str]:
    try: import onnxruntime as ort
    except ImportError: fail('onnxruntime Python package unavailable')
    providers=list(ort.get_available_providers())
    if 'CUDAExecutionProvider' not in providers: fail('ONNX Runtime CUDAExecutionProvider unavailable')
    return providers


def gpu_inventory() -> list[dict[str,str]]:
    c=subprocess.run(['nvidia-smi','--query-gpu=index,uuid,name,compute_cap','--format=csv,noheader,nounits'],check=True,capture_output=True,text=True)
    rows=[]
    for line in c.stdout.splitlines():
        if not line.strip(): continue
        parts=[p.strip() for p in line.split(',',3)]
        if len(parts)!=4: fail('unexpected nvidia-smi inventory format')
        rows.append(dict(zip(('index','uuid','name','compute_capability'),parts)))
    if not rows: fail('no NVIDIA GPU found')
    return rows


def validate_ffmpeg(ffmpeg: Path) -> None:
    if not ffmpeg.is_file(): fail(f'ffmpeg not found: {ffmpeg}')
    build=subprocess.run([str(ffmpeg),'-hide_banner','-buildconf'],check=True,capture_output=True,text=True)
    filters=subprocess.run([str(ffmpeg),'-hide_banner','-filters'],check=True,capture_output=True,text=True)
    hw=subprocess.run([str(ffmpeg),'-hide_banner','-hwaccels'],check=True,capture_output=True,text=True)
    if '--enable-libonnxruntime' not in build.stdout+build.stderr: fail('ffmpeg lacks libonnxruntime')
    if 'dnn_processing' not in filters.stdout+filters.stderr: fail('dnn_processing unavailable')
    if 'cuda' not in hw.stdout+hw.stderr: fail('CUDA hwaccel unavailable')


def validate_command(command: list[str], ffmpeg: Path) -> None:
    if not command or Path(command[0]).resolve()!=ffmpeg.resolve(): fail('command must start with attested ffmpeg')
    joined=' '.join(command)
    if 'dnn_processing' not in joined or 'dnn_backend=onnx' not in joined: fail('command must exercise dnn_processing with dnn_backend=onnx')


def zero_copy_status(path: Path | None, gpus: list[dict[str,str]]) -> tuple[str,dict[str,Any]|None]:
    if path is None: return 'PENDING_PROFILER_EVIDENCE',None
    evidence=load_json(path)
    for key,expected in {'io_binding':True,'cuda_frame_interop':True,'stream_synchronization_validated':True,'host_transfer_bytes':0}.items():
        if evidence.get(key)!=expected: fail(f'profiler does not prove zero-copy: {key}')
    if evidence.get('gpu_uuid') not in {g['uuid'] for g in gpus}: fail('profiler GPU UUID not in current-host inventory')
    return 'EXPERIMENTAL_ZERO_COPY_EVIDENCE_PASS',evidence


def main() -> int:
    p=argparse.ArgumentParser(description='FA3 current-host FFmpeg ONNX/CUDA acceptance')
    p.add_argument('--ffmpeg',required=True,type=Path); p.add_argument('--command-json',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path); p.add_argument('--host-attestation',required=True,type=Path)
    p.add_argument('--profiler-evidence',type=Path); p.add_argument('--evidence-out',type=Path,default=Path('evidence/receipts/ffmpeg-onnx-cuda-current-host.json'))
    args=p.parse_args(); att=require_attestation(args.host_attestation); providers=require_cuda_ep(); gpus=gpu_inventory(); validate_ffmpeg(args.ffmpeg)
    command=load_json(args.command_json)
    if not isinstance(command,list) or not all(isinstance(x,str) for x in command): fail('command JSON must be array of strings')
    validate_command(command,args.ffmpeg)
    result=subprocess.run(command,check=False,capture_output=True,text=True)
    if result.returncode!=0: fail(f'FFmpeg ONNX inference failed: {result.returncode}')
    if not args.output.is_file() or args.output.stat().st_size==0: fail('inference output missing/empty')
    zstatus,prof=zero_copy_status(args.profiler_evidence,gpus)
    evidence={'schema':'fa3.ffmpeg-onnx-cuda-current-host-evidence.v1','profile':'FA3-FFMPEG-ONNX-CUDA-001',
              'timestamp':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'pipeline_status':'CURRENT_HOST_ONNX_CUDA_PASS',
              'zero_copy_profile':'FA3-FFMPEG-ONNX-ZEROCOPY-001','zero_copy_status':zstatus,'ffmpeg_sha256':sha256_file(args.ffmpeg),
              'output_sha256':sha256_file(args.output),'host_attestation_sha256':att['sha256'],'onnxruntime_available_providers':providers,
              'gpu_inventory':gpus,'inference_command':command}
    if prof is not None: evidence['profiler_evidence_sha256']=sha256_file(args.profiler_evidence)
    args.evidence_out.parent.mkdir(parents=True,exist_ok=True); args.evidence_out.write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(evidence,indent=2,sort_keys=True)); return 0


if __name__=='__main__': raise SystemExit(main())
