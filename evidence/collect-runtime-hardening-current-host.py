#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def emit(path,obj):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def quadlet_ok(d):
    return all([
        d.get("signed") is True,
        d.get("rootless") is True,
        d.get("canonical_template_immutable") is True,
        d.get("canonical_template_rewritten") is False,
        d.get("ephemeral_runtime_materialization") is True,
        d.get("hrb_lease_valid") is True,
        d.get("read_only_rootfs") is True,
        d.get("no_new_privileges") is True,
        d.get("drop_all_capabilities") is True,
        d.get("network_mode") == "none",
        d.get("stable_accelerator_identity") is True,
        d.get("runtime_materialization_root") == "$XDG_RUNTIME_DIR/containers/systemd",
    ])

def sandbox_ok(d):
    if d.get("signed") is not True: return False
    if d.get("host_impact") is not True: return d.get("bounded_execution_verified") is True
    return all([
        d.get("runtime") == "runsc",
        d.get("network_mode") == "none",
        d.get("gateway_transport") == "unix",
        d.get("workspace_ephemeral") is True,
        d.get("direct_host_project_write") is False,
        d.get("direct_container_socket") is False,
        d.get("lease_signature_valid") is True,
        d.get("lease_not_expired") is True,
        d.get("task_binding_valid") is True,
        d.get("capability_narrowing_valid") is True,
        d.get("replay_protection_valid") is True,
        d.get("cleanup_complete") is True,
    ])

def residency_ok(d):
    return all([
        d.get("signed") is True,
        d.get("vapoursynth_release") == "R80",
        d.get("source_gpu_resident") is True,
        d.get("neural_output_gpu_resident") is True,
        d.get("encoder_input_gpu_resident") is True,
        d.get("implicit_gpu_uploads") == 0,
        d.get("implicit_gpu_downloads") == 0,
        d.get("host_pixel_materializations") == 0,
        d.get("foreign_device_identity_match") is True,
        d.get("external_memory_interop") is True,
        d.get("device_side_semaphore_sync") is True,
        d.get("backend_residency_verified") is True,
        d.get("current_host_e2e") is True,
        d.get("vspipe_y4m_in_zero_host_round_trip_path") is False,
    ])

def receipt(criterion,kind,src,ok):
    return {
      "schema":"fa3.acceptance-current-host-receipt.v1",
      "criterion":criterion,"kind":kind,
      "status":"PASS" if ok else "FAIL",
      "signed":src.get("signed") is True,
      "source_evidence_id":src.get("evidence_id"),
      "host_fingerprint":src.get("host_fingerprint"),
      "checks":src,
      "current_host_runtime_claim":ok
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--quadlet-evidence",required=True)
    ap.add_argument("--agent-evidence",required=True)
    ap.add_argument("--residency-evidence",required=True)
    ap.add_argument("--output-dir",default="evidence/receipts")
    a=ap.parse_args(); out=Path(a.output_dir)
    q=load(a.quadlet_evidence); s=load(a.agent_evidence); r=load(a.residency_evidence)
    rows=[
      (out/"provider-quadlet-isolation-current-host.json",receipt("CRIT-020","provider_quadlet_isolation",q,quadlet_ok(q))),
      (out/"agent-sandbox-current-host.json",receipt("CRIT-021","bounded_agent_execution",s,sandbox_ok(s))),
      (out/"neural-video-residency-current-host.json",receipt("CRIT-022","accelerator_residency_transfer_integrity",r,residency_ok(r))),
    ]
    for p,o in rows: emit(p,o)
    ok=all(o["status"]=="PASS" for _,o in rows)
    print(json.dumps({"status":"PASS" if ok else "FAIL","receipts":[str(p) for p,_ in rows]},indent=2))
    return 0 if ok else 2
if __name__=="__main__": raise SystemExit(main())
