#!/usr/bin/env bash
set -Eeuo pipefail

WORKSPACE_DIR="${FA3_FFMPEG_WORKSPACE:-/tmp/fa3-ffmpeg-onnx-cuda}"
PREFIX_DIR="${FA3_FFMPEG_PREFIX:-$PWD/bin/ffmpeg-custom}"
CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
ORT_PREFIX="${ONNXRUNTIME_PREFIX:-}"
EVIDENCE_DIR="${FA3_EVIDENCE_DIR:-evidence/receipts}"

FFMPEG_REF="bf1b838f2ab88b4f8fd83443325c782ea0e0f7fa"
NV_CODEC_REF="1889e62e2d35ff7aa9baca2bceb14f053785e6f1"

die(){ echo "[FAIL-CLOSED] $*" >&2; exit 1; }
need(){ command -v "$1" >/dev/null 2>&1 || die "required command missing: $1"; }
for command in git make pkg-config python3 nvidia-smi; do need "$command"; done
[[ -x "${CUDA_HOME}/bin/nvcc" ]] || die "nvcc not found under CUDA_HOME=${CUDA_HOME}"
mkdir -p "$WORKSPACE_DIR" "$PREFIX_DIR" "$EVIDENCE_DIR"

if [[ -n "$ORT_PREFIX" ]]; then
  export PKG_CONFIG_PATH="${ORT_PREFIX}/lib/pkgconfig:${ORT_PREFIX}/lib64/pkgconfig:${PREFIX_DIR}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
  ORT_CFLAGS="-I${ORT_PREFIX}/include"; ORT_LDFLAGS="-L${ORT_PREFIX}/lib -L${ORT_PREFIX}/lib64"
else
  export PKG_CONFIG_PATH="${PREFIX_DIR}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
  ORT_CFLAGS=""; ORT_LDFLAGS=""
fi
pkg-config --exists libonnxruntime || die "libonnxruntime pkg-config metadata required"

checkout_exact(){
  local url="$1" dir="$2" ref="$3"
  [[ -d "$dir/.git" ]] || git clone --filter=blob:none "$url" "$dir"
  git -C "$dir" fetch --tags --force origin
  git -C "$dir" checkout --detach "$ref"
  [[ "$(git -C "$dir" rev-parse HEAD)" == "$ref" ]] || die "immutable source pin mismatch: $dir"
}
checkout_exact https://github.com/FFmpeg/nv-codec-headers.git "$WORKSPACE_DIR/nv-codec-headers" "$NV_CODEC_REF"
make -C "$WORKSPACE_DIR/nv-codec-headers" PREFIX="$PREFIX_DIR"
make -C "$WORKSPACE_DIR/nv-codec-headers" install PREFIX="$PREFIX_DIR"
checkout_exact https://github.com/FFmpeg/FFmpeg.git "$WORKSPACE_DIR/ffmpeg" "$FFMPEG_REF"

normalize_arch(){ local value="${1//./}"; [[ "$value" =~ ^[0-9]{2,3}$ ]] || die "invalid CUDA architecture: $1"; printf '%s\n' "$value"; }
declare -a CUDA_ARCHES=()
if [[ -n "${FA3_CUDA_ARCH_LIST:-}" ]]; then
  read -r -a requested <<< "${FA3_CUDA_ARCH_LIST//,/ }"
  for arch in "${requested[@]}"; do CUDA_ARCHES+=("$(normalize_arch "$arch")"); done
else
  while IFS= read -r capability; do capability="${capability//[[:space:]]/}"; [[ -z "$capability" ]] || CUDA_ARCHES+=("$(normalize_arch "$capability")"); done < <(nvidia-smi --query-gpu=compute_cap --format=csv,noheader,nounits)
fi
[[ ${#CUDA_ARCHES[@]} -gt 0 ]] || die "no CUDA architecture detected or declared"
mapfile -t CUDA_ARCHES < <(printf '%s\n' "${CUDA_ARCHES[@]}" | sort -uV)
NVCC_FLAGS=()
for arch in "${CUDA_ARCHES[@]}"; do NVCC_FLAGS+=("-gencode" "arch=compute_${arch},code=sm_${arch}"); done
highest="${CUDA_ARCHES[${#CUDA_ARCHES[@]}-1]}"
NVCC_FLAGS+=("-gencode" "arch=compute_${highest},code=compute_${highest}")

LICENSE_FLAGS=()
case "${FA3_FFMPEG_LICENSE_PROFILE:-lgpl}" in
  lgpl) ;;
  gpl) LICENSE_FLAGS+=(--enable-gpl) ;;
  nonfree) [[ "${FA3_ALLOW_NONFREE:-NO}" == YES ]] || die "nonfree requires FA3_ALLOW_NONFREE=YES"; LICENSE_FLAGS+=(--enable-gpl --enable-nonfree) ;;
  *) die "FA3_FFMPEG_LICENSE_PROFILE must be lgpl, gpl, or nonfree" ;;
esac

cd "$WORKSPACE_DIR/ffmpeg"; make distclean >/dev/null 2>&1 || true
NVCC_FLAGS_STRING="$(printf '%q ' "${NVCC_FLAGS[@]}")"
./configure --prefix="$PREFIX_DIR" --enable-cuda-nvcc --enable-libonnxruntime --enable-shared --disable-static \
  "${LICENSE_FLAGS[@]}" --extra-cflags="-I${PREFIX_DIR}/include -I${CUDA_HOME}/include ${ORT_CFLAGS}" \
  --extra-ldflags="-L${PREFIX_DIR}/lib -L${CUDA_HOME}/lib64 ${ORT_LDFLAGS}" --nvccflags="$NVCC_FLAGS_STRING"
make -j"${FA3_BUILD_JOBS:-$(nproc)}"; make install
FFMPEG="$PREFIX_DIR/bin/ffmpeg"; [[ -x "$FFMPEG" ]] || die "custom ffmpeg not installed"
buildconf="$("$FFMPEG" -hide_banner -buildconf 2>&1)"; filters="$("$FFMPEG" -hide_banner -filters 2>&1)"; hwaccels="$("$FFMPEG" -hide_banner -hwaccels 2>&1)"
grep -q -- --enable-libonnxruntime <<<"$buildconf" || die "libonnxruntime absent from buildconf"
grep -q -- --enable-cuda-nvcc <<<"$buildconf" || die "cuda-nvcc absent from buildconf"
grep -q dnn_processing <<<"$filters" || die "dnn_processing unavailable"
grep -q cuda <<<"$hwaccels" || die "CUDA hwaccel unavailable"

gpu_inventory="$(nvidia-smi --query-gpu=index,uuid,name,compute_cap --format=csv,noheader 2>/dev/null || true)"
evidence_path="$EVIDENCE_DIR/ffmpeg-onnx-cuda-build-$(date -u +%Y%m%dT%H%M%SZ).json"
FA3_FFMPEG="$FFMPEG" FA3_GPU_INVENTORY="$gpu_inventory" FA3_CUDA_ARCHES="$(IFS=,; echo "${CUDA_ARCHES[*]}")" \
FA3_LICENSE_PROFILE="${FA3_FFMPEG_LICENSE_PROFILE:-lgpl}" FA3_EVIDENCE_PATH="$evidence_path" python3 - <<'PY'
import hashlib,json,os
from datetime import datetime,timezone
from pathlib import Path
ffmpeg=Path(os.environ['FA3_FFMPEG'])
payload={
 'schema':'fa3.ffmpeg-onnx-cuda-build-evidence.v1','profile':'FA3-FFMPEG-ONNX-CUDA-001',
 'timestamp':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'ffmpeg_release':'9.0.1',
 'ffmpeg_commit':'bf1b838f2ab88b4f8fd83443325c782ea0e0f7fa','nv_codec_headers_commit':'1889e62e2d35ff7aa9baca2bceb14f053785e6f1',
 'ffmpeg_sha256':hashlib.sha256(ffmpeg.read_bytes()).hexdigest(),'cuda_arches':os.environ['FA3_CUDA_ARCHES'].split(','),
 'license_profile':os.environ['FA3_LICENSE_PROFILE'],'gpu_inventory':[x for x in os.environ.get('FA3_GPU_INVENTORY','').splitlines() if x],
 'build_status':'BUILD_PASS','onnx_cuda_runtime_status':'PENDING_CURRENT_HOST','zero_copy_status':'NOT_CLAIMED',
 'zero_copy_reason':'Build presence does not prove ORT I/O binding, CUDA frame interoperability, stream correctness, or absence of host transfers.'}
Path(os.environ['FA3_EVIDENCE_PATH']).write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
PY
echo "[PASS] FFmpeg/ONNX/CUDA build contract validated"
echo "[PENDING_CURRENT_HOST] Runtime and zero-copy claims require current_host_acceptance.py"
echo "[EVIDENCE] $evidence_path"
