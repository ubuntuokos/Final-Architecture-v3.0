#!/usr/bin/env python3
from __future__ import annotations
import re
from typing import Any

RUNTIME_CLASSES={"VENV","OCI","HOST_NATIVE"}
SHA256=re.compile(r"^[0-9a-f]{64}$")
CONDA_TOKENS=("conda","mamba","micromamba","miniconda","anaconda")

class ProviderRuntimeError(RuntimeError): pass

def select_runtime_class(*,reproducible_venv:bool,native_abi_complexity:bool,host_native_required:bool=False)->str:
    if reproducible_venv: return "VENV"
    if native_abi_complexity: return "OCI"
    if host_native_required: return "HOST_NATIVE"
    raise ProviderRuntimeError("runtime class cannot be justified")

def validate_runtime_environment(plan:dict[str,Any])->dict[str,Any]:
    findings=[]
    if plan.get("schema")!="fa3.provider-runtime-environment.v1": findings.append("schema mismatch")
    cls=plan.get("execution_class")
    if cls not in RUNTIME_CLASSES: findings.append("unknown execution class")
    if plan.get("provider_id") in (None,""): findings.append("provider_id missing")
    if plan.get("hrb_admission_required") is not True: findings.append("HRB admission must remain authoritative")
    if plan.get("secret_delivery") not in {"NONE","SECRETREF","CREDENTIAL_LEASE"}: findings.append("secret delivery invalid")
    if plan.get("host_global_reconfiguration") is not False: findings.append("host global reconfiguration forbidden")
    if plan.get("upstream_uninstall_required") is not False: findings.append("upstream uninstall/replacement forbidden")
    if plan.get("supply_chain_receipt_status")!="PASS": findings.append("supply-chain admission missing")
    text=str(plan).lower()
    if any(tok in text for tok in CONDA_TOKENS): findings.append("conda/mamba baseline forbidden")
    if cls=="VENV":
        v=plan.get("venv",{})
        if v.get("manager") not in {"uv","python-venv","pip-venv"}: findings.append("venv manager invalid")
        if not SHA256.fullmatch(str(v.get("dependency_lock_sha256",""))): findings.append("venv dependency lock missing")
        if not SHA256.fullmatch(str(v.get("environment_identity_sha256",""))): findings.append("venv identity missing")
        if v.get("system_site_packages") is not False: findings.append("system-site-packages forbidden")
    elif cls=="OCI":
        o=plan.get("oci",{})
        if o.get("engine")!="podman" or o.get("rootless") is not True: findings.append("OCI must use rootless Podman")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}",str(o.get("image_digest",""))): findings.append("digest-pinned OCI image required")
        if not SHA256.fullmatch(str(o.get("build_recipe_sha256",""))): findings.append("OCI build recipe digest missing")
        if o.get("mutable_tag_only") is not False: findings.append("mutable-tag-only OCI forbidden")
        if o.get("network_default") not in {"DENY","LOOPBACK_ONLY"}: findings.append("OCI network default must be deny/loopback")
        if o.get("explicit_mounts_only") is not True: findings.append("OCI explicit mounts required")
        if o.get("accelerator_device_projection_from_hrb") is not True: findings.append("OCI accelerator projection must come from HRB")
    elif cls=="HOST_NATIVE":
        h=plan.get("host_native",{})
        if not h.get("justification"): findings.append("host-native justification missing")
        if not h.get("package_identity"): findings.append("host-native package identity missing")
        if h.get("namespaced_state") is not True: findings.append("host-native state must be namespaced")
        if h.get("global_environment_mutation") is not False: findings.append("global environment mutation forbidden")
    return {"result":"PASS" if not findings else "FAIL","findings":findings}
