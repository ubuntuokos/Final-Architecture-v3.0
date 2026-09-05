#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
PROVIDER_ID='FA3-PROVIDER-DIFFUSION-STUDIO-001'; DAPI=os.environ.get('FA3_DAPI','dapi')
OPS=['project.create','project.open','project.save','media.import','timeline.inspect','timeline.insert','timeline.move','timeline.trim','timeline.split','timeline.delete','track.create','track.update','transition.apply','effect.apply','audio.adjust','caption.insert','preview.render','render.start','render.status','render.cancel','project.validate','project.export']
MUT=set(OPS[2:4]+OPS[5:16]); CLI={'project.open':'open','timeline.inspect':'context','project.validate':'check','preview.render':'capture','project.export':'export','render.start':'export'}
def digest(b):return hashlib.sha256(b).hexdigest()
def target(root,rel):
 r=Path(root).expanduser().resolve();t=(r/rel).resolve()
 if t==r or r not in t.parents:raise ValueError('target escapes admitted project_root')
 if t.suffix.lower() not in {'.tsx','.ts','.jsx','.js','.json'}:raise ValueError('source suffix not admitted')
 return r,t
def dapi(args,timeout=300):
 p=subprocess.run([DAPI,*args],text=True,capture_output=True,timeout=timeout)
 if p.returncode:raise RuntimeError(p.stderr.strip() or f'dapi failed: {p.returncode}')
 out=p.stdout.strip();rows=[]
 for line in out.splitlines():
  try:rows.append(json.loads(line))
  except json.JSONDecodeError:rows.append(line)
 return rows[0] if len(rows)==1 else rows
def mutate(q):
 a=q.get('args') or {};r,t=target(a['project_root'],a['relative_path']);old=t.read_bytes() if t.exists() else b'';new=(a.get('content') or '').encode();pre=digest(old);post=digest(new)
 if a.get('expected_sha256') and a['expected_sha256']!=pre:raise ValueError('precondition sha256 mismatch')
 if not q.get('idempotency_key'):raise ValueError('idempotency_key required')
 receipt=digest(json.dumps({'op':q['operation'],'path':str(t.relative_to(r)),'pre':pre,'post':post,'key':q['idempotency_key']},sort_keys=True).encode())
 if a.get('dry_run') is True:return {'dry_run':True,'receipt':receipt,'pre_sha256':pre,'post_sha256':post}
 if q['operation']=='timeline.delete':
  for k in ('dry_run_receipt','approval_id','provenance_id','audit_id'):
   if not a.get(k):raise ValueError(k+' required for destructive mutation')
  if a['dry_run_receipt']!=receipt:raise ValueError('dry_run_receipt mismatch')
 t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(new);return {'applied':True,'receipt':receipt,'pre_sha256':pre,'post_sha256':post}
def invoke(q):
 if q.get('schema')!='fa3.provider-request.v1' or q.get('provider_id')!=PROVIDER_ID:raise ValueError('invalid request envelope')
 op=q.get('operation');a=q.get('args') or {}
 if op not in OPS:raise ValueError('unsupported operation')
 if op=='project.create':
  r=Path(a['project_root']).expanduser().resolve();r.mkdir(parents=True,exist_ok=False);return {'project_root':str(r)}
 if op in MUT:return mutate(q)
 if op in {'render.status','render.cancel'}:raise ValueError('v0.204.1 dapi export is synchronous; async lifecycle not admitted')
 extra=a.get('dapi_args') or []
 if op=='project.open':extra=(['-b'] if a.get('headless') else [])+[str(a['project_root']),*extra]
 return {'dapi':dapi([CLI[op],*extra],int(a.get('timeout',300)))}
def main():
 ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='cmd',required=True);sp.add_parser('capabilities');sp.add_parser('health');sp.add_parser('invoke');ns=ap.parse_args()
 try:
  if ns.cmd=='capabilities':o={'schema':'fa3.provider-capabilities.v1','provider_id':PROVIDER_ID,'capability_projection':['CAP-121','CAP-126'],'operations':OPS,'async_render_lifecycle':'NOT_ADMITTED_V0.204.1'}
  elif ns.cmd=='health':o={'schema':'fa3.provider-health.v1','provider_id':PROVIDER_ID,'version':dapi(['--version'],15)}
  else:q=json.loads(sys.stdin.read());o={'schema':'fa3.provider-response.v1','provider_id':PROVIDER_ID,'request_id':q.get('request_id'),'result':invoke(q)}
  print(json.dumps(o,ensure_ascii=False,sort_keys=True));return 0
 except Exception as e:print(json.dumps({'schema':'fa3.provider-response.v1','provider_id':PROVIDER_ID,'ok':False,'error':str(e)},sort_keys=True));return 2
if __name__=='__main__':raise SystemExit(main())
