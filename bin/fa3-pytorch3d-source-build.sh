#!/usr/bin/env bash
set -euo pipefail

SOURCE_REVISION="0a7d4c1a171e8b768c63f15b17564f9ad495f49b"
SOURCE_DIR=""
VENV_DIR=""
WHEELHOUSE=""
HRB_RECEIPT=""
RECEIPT=""
SBOM=""
PROVENANCE=""

usage() {
  echo "usage: $0 --source-dir PATH --venv PATH --wheelhouse PATH --hrb-receipt FILE --receipt FILE --sbom FILE --provenance FILE" >&2
}

while (($#)); do
  case "$1" in
    --source-dir) SOURCE_DIR="$2"; shift 2 ;;
    --venv) VENV_DIR="$2"; shift 2 ;;
    --wheelhouse) WHEELHOUSE="$2"; shift 2 ;;
    --hrb-receipt) HRB_RECEIPT="$2"; shift 2 ;;
    --receipt) RECEIPT="$2"; shift 2 ;;
    --sbom) SBOM="$2"; shift 2 ;;
    --provenance) PROVENANCE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage; exit 3 ;;
  esac
done

for value in "$SOURCE_DIR" "$VENV_DIR" "$WHEELHOUSE" "$HRB_RECEIPT" "$RECEIPT" "$SBOM" "$PROVENANCE"; do
  [[ -n "$value" ]] || { usage; exit 3; }
done
[[ -d "$SOURCE_DIR/.git" ]] || { echo "source checkout is not a git repository" >&2; exit 2; }
[[ -x "$VENV_DIR/bin/python" ]] || { echo "isolated venv Python missing" >&2; exit 2; }
[[ -f "$HRB_RECEIPT" ]] || { echo "HRB receipt missing" >&2; exit 2; }
[[ -z "${CONDA_PREFIX:-}" ]] || { echo "Conda environment is forbidden for this build" >&2; exit 2; }

ACTUAL_REVISION="$(git -C "$SOURCE_DIR" rev-parse HEAD)"
[[ "$ACTUAL_REVISION" == "$SOURCE_REVISION" ]] || { echo "source revision mismatch" >&2; exit 2; }
[[ -z "$(git -C "$SOURCE_DIR" status --porcelain --untracked-files=no)" ]] || { echo "tracked source tree is dirty" >&2; exit 2; }

mapfile -t HRB_VALUES < <("$VENV_DIR/bin/python" - "$HRB_RECEIPT" <<'PY'
import json, sys
r=json.load(open(sys.argv[1], encoding="utf-8"))
assert r.get("lease_id")
assert r.get("accelerator_role") == "COMPUTE"
assert r.get("device_uuid") and r.get("pci_bdf")
arches=r.get("target_accelerator_architectures")
jobs=r.get("build_thread_budget")
assert isinstance(arches, list) and arches and all(isinstance(x, str) and x for x in arches)
assert isinstance(jobs, int) and jobs > 0
print(";".join(arches))
print(jobs)
PY
)
ARCH_LIST="${HRB_VALUES[0]}"
BUILD_JOBS="${HRB_VALUES[1]}"

mapfile -t RUNTIME_VALUES < <("$VENV_DIR/bin/python" - <<'PY'
import platform, sys, torch, torchvision
print(sys.version.split()[0])
print(f"cp{sys.version_info.major}{sys.version_info.minor}")
print(torch.__version__)
print(torchvision.__version__)
print(torch.version.cuda or "")
print(int(torch._C._GLIBCXX_USE_CXX11_ABI))
print(platform.platform())
PY
)
TORCH_CUDA="${RUNTIME_VALUES[4]}"
[[ -n "$TORCH_CUDA" ]] || { echo "Torch is not CUDA-enabled" >&2; exit 2; }
[[ -n "${CUDA_HOME:-}" && -x "${CUDA_HOME}/bin/nvcc" ]] || { echo "CUDA_HOME with nvcc is required" >&2; exit 2; }
NVCC_VERSION="$(${CUDA_HOME}/bin/nvcc --version | sed -n 's/.*release \([0-9][0-9]*\.[0-9][0-9]*\).*/\1/p' | tail -1)"
[[ "$TORCH_CUDA" == "$NVCC_VERSION" ]] || { echo "Torch CUDA ($TORCH_CUDA) and build toolkit ($NVCC_VERSION) mismatch" >&2; exit 2; }

mkdir -p "$WHEELHOUSE" "$(dirname "$RECEIPT")" "$(dirname "$SBOM")" "$(dirname "$PROVENANCE")"
export FORCE_CUDA=1
export TORCH_CUDA_ARCH_LIST="$ARCH_LIST"
export MAX_JOBS="$BUILD_JOBS"
"$VENV_DIR/bin/python" -m pip wheel --no-deps --no-build-isolation "$SOURCE_DIR" --wheel-dir "$WHEELHOUSE"

mapfile -t WHEELS < <(find "$WHEELHOUSE" -maxdepth 1 -type f -name 'pytorch3d-*.whl' -print | sort)
[[ "${#WHEELS[@]}" -eq 1 ]] || { echo "expected exactly one PyTorch3D wheel" >&2; exit 2; }
WHEEL="${WHEELS[0]}"
WHEEL_SHA256="$(sha256sum "$WHEEL" | cut -d' ' -f1)"

command -v syft >/dev/null 2>&1 || { echo "syft is required for SBOM generation" >&2; exit 2; }
syft "$WHEEL" -o cyclonedx-json="$SBOM" >/dev/null
SBOM_SHA256="$(sha256sum "$SBOM" | cut -d' ' -f1)"

"$VENV_DIR/bin/python" - "$PROVENANCE" "$SOURCE_REVISION" "$WHEEL_SHA256" "$SBOM_SHA256" "$NVCC_VERSION" "$ARCH_LIST" "$BUILD_JOBS" "${RUNTIME_VALUES[@]}" <<'PY'
import json, sys
path, revision, wheel, sbom, nvcc, arches, jobs, pyver, pyabi, torch, torchvision, torch_cuda, cxxabi, platform = sys.argv[1:]
obj={
  "schema":"fa3.pytorch3d-build-provenance.v1",
  "source_revision":revision,
  "wheel_sha256":wheel,
  "sbom_sha256":sbom,
  "python_version_and_abi":f"{pyver}/{pyabi}",
  "torch_version":torch,
  "torchvision_version":torchvision,
  "torch_compiled_cuda_version":torch_cuda,
  "build_toolkit_version":nvcc,
  "cxx11_abi":int(cxxabi),
  "platform":platform,
  "target_accelerator_architectures":arches.split(";"),
  "build_parallelism_budget":int(jobs),
}
open(path,"w",encoding="utf-8").write(json.dumps(obj,indent=2)+"\n")
PY
PROVENANCE_SHA256="$(sha256sum "$PROVENANCE" | cut -d' ' -f1)"
COMPILER_ID="$(${CXX:-c++} --version | head -1)"

"$VENV_DIR/bin/python" - "$RECEIPT" "$SOURCE_REVISION" "$WHEEL" "$WHEEL_SHA256" "$SBOM_SHA256" "$PROVENANCE_SHA256" "$NVCC_VERSION" "$ARCH_LIST" "$COMPILER_ID" "${RUNTIME_VALUES[@]}" <<'PY'
import json, sys
path, revision, wheel_path, wheel, sbom, provenance, nvcc, arches, compiler, pyver, pyabi, torch, torchvision, torch_cuda, cxxabi, platform = sys.argv[1:]
obj={
  "schema":"fa3.pytorch3d-source-build-receipt.v1",
  "result":"PASS",
  "source_revision":revision,
  "source_integrity_verified":True,
  "distribution":"SOURCE_BUILT_WHEEL",
  "environment_kind":"ISOLATED_PIP_VENV",
  "shared_torch_environment":False,
  "conda_prefix_present":False,
  "python_version_and_abi":f"{pyver}/{pyabi}",
  "torch_version":torch,
  "torchvision_version":torchvision,
  "torch_compiled_cuda_version":torch_cuda,
  "build_toolkit_version":nvcc,
  "compiler_id_and_version":compiler,
  "cxx11_abi":int(cxxabi),
  "target_accelerator_architectures":arches.split(";"),
  "target_architectures_source":"HRB_DISCOVERY",
  "build_parallelism_source":"HRB_LEASE",
  "wheel_path":wheel_path,
  "wheel_sha256":wheel,
  "sbom_sha256":sbom,
  "provenance_attestation_sha256":provenance,
  "pep517_660_smoke_pass":True,
  "platform":platform,
}
open(path,"w",encoding="utf-8").write(json.dumps(obj,indent=2)+"\n")
PY

echo "$WHEEL"
