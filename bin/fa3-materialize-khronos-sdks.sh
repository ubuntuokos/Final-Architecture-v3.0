#!/usr/bin/env bash
set -euo pipefail

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
ROOT="${FA3_KHRONOS_ROOT:-$DATA_HOME/fa3/khronos-sdk}"
SRC="$ROOT/src"
BUILD="$CACHE_HOME/fa3/khronos-sdk/build"
PREFIX="$ROOT/prefix"
RECEIPTS="$ROOT/receipts"
MODE="${1:---source-only}"
JOBS="${FA3_KHRONOS_BUILD_JOBS:-4}"

case "$MODE" in
  --source-only|--build-core) ;;
  *) echo "usage: $0 [--source-only|--build-core]" >&2; exit 2 ;;
esac

for cmd in git python3; do
  command -v "$cmd" >/dev/null || { echo "$cmd is required" >&2; exit 3; }
done
mkdir -p "$SRC" "$BUILD" "$PREFIX" "$RECEIPTS"

# Adopted Khronos SDK / tool sources.
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

# Build-only immutable dependencies. They never become FA3 runtime providers.
build_deps=(
"KhronosGroup/SPIRV-Headers|29981f65241605e08b0ede4cfeb999fe3b723c6a"
"KhronosGroup/Vulkan-Utility-Libraries|c279fa4350059faac3d2365df0538977e7e5b097"
"open-source-parsers/jsoncpp|89e2973c754a9c02a49974d839779b151e95afd6"
"tristanpenman/valijson|0b4771e273a065d437814baf426bcfcafec0f434"
)

materialize_one() {
  local item="$1" repo sha name dir
  repo="${item%%|*}"
  sha="${item##*|}"
  name="${repo##*/}"
  dir="$SRC/$name"
  if [[ ! -d "$dir/.git" ]]; then
    git clone --filter=blob:none --no-checkout "https://github.com/$repo.git" "$dir"
  fi
  git -C "$dir" fetch --depth=1 origin "$sha"
  git -C "$dir" checkout --detach --force "$sha"
  [[ "$(git -C "$dir" rev-parse HEAD)" == "$sha" ]] || {
    echo "immutable pin mismatch: $repo" >&2
    exit 4
  }
}

for item in "${projects[@]}" "${build_deps[@]}"; do
  materialize_one "$item"
done

if [[ "$MODE" == "--source-only" ]]; then
  echo "FA3 Khronos immutable source materialization complete: $ROOT"
  exit 0
fi

for cmd in cmake cc c++; do
  command -v "$cmd" >/dev/null || {
    echo "$cmd is required for --build-core; install the distribution package providing it and retry" >&2
    exit 5
  }
done
[[ "$JOBS" =~ ^[1-9][0-9]*$ ]] || { echo "FA3_KHRONOS_BUILD_JOBS must be a positive integer" >&2; exit 5; }
if (( JOBS > 16 )); then
  echo "FA3_KHRONOS_BUILD_JOBS exceeds the bounded validation maximum of 16" >&2
  exit 5
fi

rm -rf "$BUILD" "$PREFIX"
mkdir -p "$BUILD" "$PREFIX"

build_one() {
  local name="$1"; shift
  local b="$BUILD/$name"
  rm -rf "$b"
  cmake -S "$SRC/$name" -B "$b"     -DCMAKE_BUILD_TYPE=Release     -DCMAKE_INSTALL_PREFIX="$PREFIX"     -DCMAKE_PREFIX_PATH="$PREFIX"     "$@"
  cmake --build "$b" --parallel "$JOBS"
  cmake --install "$b"
}

# Build order is dependency-explicit. Automatic UPDATE_DEPS network fetching is forbidden.
build_one Vulkan-Headers -DBUILD_TESTING=OFF
build_one Vulkan-Utility-Libraries   -DUPDATE_DEPS=OFF   -DBUILD_TESTING=OFF   -DVULKAN_HEADERS_INSTALL_DIR="$PREFIX"
build_one SPIRV-Headers
build_one SPIRV-Tools   -DSPIRV-Headers_SOURCE_DIR="$SRC/SPIRV-Headers"   -DSPIRV_SKIP_TESTS=ON   -DSPIRV_SKIP_EXECUTABLES=OFF   -DSPIRV_WERROR=OFF
build_one glslang   -DENABLE_GLSLANG_BINARIES=ON   -DENABLE_OPT=OFF   -DBUILD_TESTING=OFF
build_one SPIRV-Cross   -DSPIRV_CROSS_CLI=ON   -DSPIRV_CROSS_ENABLE_TESTS=OFF
build_one jsoncpp   -DJSONCPP_WITH_TESTS=OFF   -DJSONCPP_WITH_POST_BUILD_UNITTEST=OFF   -DJSONCPP_WITH_WARNING_AS_ERROR=OFF   -DJSONCPP_WITH_PKGCONFIG_SUPPORT=OFF   -DBUILD_SHARED_LIBS=OFF   -DBUILD_STATIC_LIBS=ON   -DBUILD_OBJECT_LIBS=OFF
build_one valijson
build_one Vulkan-Loader   -DUPDATE_DEPS=OFF   -DBUILD_TESTS=OFF   -DVULKAN_HEADERS_INSTALL_DIR="$PREFIX"   -DBUILD_WSI_XCB_SUPPORT=OFF   -DBUILD_WSI_XLIB_SUPPORT=OFF   -DBUILD_WSI_WAYLAND_SUPPORT=OFF
build_one Vulkan-Profiles   -DUPDATE_DEPS=OFF   -DBUILD_TESTS=OFF   -DVULKAN_HEADERS_INSTALL_DIR="$PREFIX"   -DVULKAN_UTILITY_LIBRARIES_INSTALL_DIR="$PREFIX"   -DVULKAN_LOADER_INSTALL_DIR="$PREFIX"   -DJSONCPP_INSTALL_DIR="$PREFIX"   -DVALIJSON_INSTALL_DIR="$PREFIX"
build_one Vulkan-ValidationLayers   -DUPDATE_DEPS=OFF   -DBUILD_TESTS=OFF   -DVULKAN_HEADERS_INSTALL_DIR="$PREFIX"   -DVULKAN_UTILITY_LIBRARIES_INSTALL_DIR="$PREFIX"   -DSPIRV_HEADERS_INSTALL_DIR="$PREFIX"   -DSPIRV_TOOLS_INSTALL_DIR="$PREFIX"   -DBUILD_WSI_XCB_SUPPORT=OFF   -DBUILD_WSI_XLIB_SUPPORT=OFF   -DBUILD_WSI_WAYLAND_SUPPORT=OFF
build_one KTX-Software   -DKTX_FEATURE_TESTS=OFF   -DKTX_FEATURE_TOOLS=ON   -DKTX_FEATURE_TOOLS_CTS=OFF   -DKTX_FEATURE_LOADTEST_APPS=OFF   -DKTX_FEATURE_DOC=OFF   -DKTX_FEATURE_JNI=OFF   -DKTX_FEATURE_PY=OFF
build_one OpenXR-SDK -DBUILD_TESTS=OFF
build_one OpenCL-Headers
build_one OpenCL-ICD-Loader -DOPENCL_ICD_LOADER_BUILD_TESTING=OFF
build_one ANARI-SDK   -DBUILD_TESTING=OFF   -DBUILD_CTS=OFF   -DBUILD_EXAMPLES=OFF   -DBUILD_VIEWER=OFF   -DBUILD_HELIDE_DEVICE=OFF   -DBUILD_HELIDE_GPU_DEVICE=OFF   -DBUILD_REMOTE_DEVICE=OFF   -DBUILD_CAT=OFF

python3 - "$RECEIPTS/core-build.json" "$PREFIX" "$(git rev-parse HEAD)" <<'PY'
import json,sys
from pathlib import Path
out=Path(sys.argv[1]); prefix=Path(sys.argv[2]); source_commit=sys.argv[3]
components=[
 "Vulkan-Headers","Vulkan-Utility-Libraries","SPIRV-Headers","SPIRV-Tools","glslang","SPIRV-Cross",
 "jsoncpp","valijson","Vulkan-Loader","Vulkan-Profiles","Vulkan-ValidationLayers","KTX-Software",
 "OpenXR-SDK","OpenCL-Headers","OpenCL-ICD-Loader","ANARI-SDK"
]
required_bins=["glslangValidator","spirv-val","spirv-opt","spirv-cross"]
missing=[name for name in required_bins if not (prefix/"bin"/name).is_file()]
row={
 "schema":"fa3.khronos-core-build-receipt.v1",
 "status":"PASS" if not missing else "FAIL",
 "source_commit":source_commit,
 "prefix_class":"XDG_DATA_HOME_FA3_NAMESPACED",
 "components":components,
 "required_binaries":required_bins,
 "missing_required_binaries":missing,
 "automatic_update_deps":False,
 "system_package_replacement":False,
 "global_environment_mutation":False,
 "hardware_parameter_mutation":False,
 "runtime_promotion_claim":False,
}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(row,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(row,indent=2,sort_keys=True))
if missing: raise SystemExit(6)
PY

echo "FA3 Khronos core build complete: $PREFIX"
