#!/usr/bin/env bash
set -euo pipefail

ROOT="${FA3_KHRONOS_ROOT:-$HOME/.local/share/fa3/khronos-sdk}"
MODE="source"
case "${1:-}" in
  --build) MODE="build" ;;
  --source-only|"") MODE="source" ;;
  *) echo "usage: $0 [--source-only|--build]" >&2; exit 2 ;;
esac

command -v git >/dev/null || { echo "git required" >&2; exit 3; }
mkdir -p "$ROOT/src" "$ROOT/build" "$ROOT/prefix" "$ROOT/receipts"

projects=(
"KhronosGroup/Vulkan-Headers|e3b1eec08173d6b825cd3ac88c885a63b621504a"
"KhronosGroup/Vulkan-Loader|5f157b62e333c63260d05d81bf66faa216ab0fb8"
"KhronosGroup/Vulkan-ValidationLayers|f4874eee15c78d7bdb2b7e60659d539f14741500"
"KhronosGroup/Vulkan-Profiles|1f139a2ea3c475eed7e6699d67fc362203a69c41"
"KhronosGroup/SPIRV-Tools|b707790a898e44038547df54580022fc1cf89c3d"
"KhronosGroup/glslang|e1b562a8bed273a02f30b59b66a5d499793cede5"
"KhronosGroup/SPIRV-Cross|aa217aeb6c9f0ace7a0ab233b28807edf45eb165"
"KhronosGroup/KTX-Software|4d6fc70eaf62ad0558e63e8d97eb9766118327a6"
"KhronosGroup/glTF-Validator|434283be08a668a8fb4e437145630ddbf93b0686"
"KhronosGroup/OpenXR-SDK|f2448a8797c85814aa892efc1ab8707900fbcc78"
"KhronosGroup/OpenCL-Headers|6fe718c31a45fe25151362a72ef041c3a1047cbd"
"KhronosGroup/OpenCL-ICD-Loader|b7bd2803acc779c03d96588e9ca9e9568a18698a"
"KhronosGroup/ANARI-SDK|7534bd263d6ff97764eda93d0e1bd6bd2f108c32"
"KhronosGroup/OpenVX-sample-impl|031f44bdcd6648f0957c9e351f76c3a64a0bfc32"
"KhronosGroup/NNEF-Tools|765d27d9095e0c90301165f8933fb325b54ddd17"
)

for item in "${projects[@]}"; do
  repo="${item%%|*}"; sha="${item##*|}"; name="${repo##*/}"; dir="$ROOT/src/$name"
  if [[ ! -d "$dir/.git" ]]; then
    git clone --filter=blob:none "https://github.com/$repo.git" "$dir"
  fi
  git -C "$dir" fetch --depth=1 origin "$sha"
  git -C "$dir" checkout --detach "$sha"
  actual="$(git -C "$dir" rev-parse HEAD)"
  [[ "$actual" == "$sha" ]] || { echo "pin mismatch: $repo" >&2; exit 4; }
done

if [[ "$MODE" == "build" ]]; then
  command -v cmake >/dev/null || { echo "cmake required for --build" >&2; exit 5; }
  build_one() {
    local name="$1"; shift
    cmake -S "$ROOT/src/$name" -B "$ROOT/build/$name" -DCMAKE_INSTALL_PREFIX="$ROOT/prefix" "$@"
    cmake --build "$ROOT/build/$name" --parallel
    cmake --install "$ROOT/build/$name"
  }
  build_one Vulkan-Headers
  build_one SPIRV-Tools -DSPIRV_SKIP_TESTS=ON
  build_one glslang -DENABLE_GLSLANG_BINARIES=ON
  build_one SPIRV-Cross -DSPIRV_CROSS_CLI=ON -DSPIRV_CROSS_ENABLE_TESTS=OFF
  build_one Vulkan-Loader -DBUILD_TESTS=OFF
  build_one Vulkan-ValidationLayers -DBUILD_TESTS=OFF
  build_one Vulkan-Profiles -DVULKAN_PROFILES_BUILD_TESTS=OFF
  build_one KTX-Software -DKTX_FEATURE_TESTS=OFF
  build_one OpenXR-SDK -DBUILD_TESTS=OFF
  build_one OpenCL-Headers
  build_one OpenCL-ICD-Loader -DOPENCL_ICD_LOADER_BUILD_TESTING=OFF
  build_one ANARI-SDK -DBUILD_TESTING=OFF
  build_one OpenVX-sample-impl
  echo "glTF-Validator and NNEF-Tools remain isolated source tools; dependency installation is handled by their provider adapters."
fi

python3 - <<'PY' > "$ROOT/receipts/materialization.json"
import json, os, pathlib, subprocess
root=pathlib.Path(os.environ.get("FA3_KHRONOS_ROOT", pathlib.Path.home()/".local/share/fa3/khronos-sdk"))
items=[]
for p in sorted((root/"src").iterdir()):
    if (p/".git").is_dir():
        sha=subprocess.check_output(["git","-C",str(p),"rev-parse","HEAD"],text=True).strip()
        items.append({"project":p.name,"commit":sha})
print(json.dumps({"schema":"fa3.khronos-materialization-receipt.v1","status":"MATERIALIZED_SOURCE","runtime_promotion_claim":False,"projects":items},indent=2))
PY

echo "Khronos SDK materialization complete at $ROOT"
