#!/usr/bin/env bash
set -euo pipefail

VERSION="v4.6.0"
COMMIT="e8931cc68001b66ad024fd87ef07394e9e96524a"
ARCHIVE_NAME="AI-Infra-Guard-v4.6.0.tar.gz"
ARCHIVE_SHA256="1523b3e9f54c520b9a602e332a05f846c4e72c02e65a50feadd96533856c0ed4"
URL="https://github.com/Tencent/AI-Infra-Guard/releases/download/v4.6.0/${ARCHIVE_NAME}"
RUNTIME_ROOT="${FA3_AIG_RUNTIME_ROOT:-$HOME/.local/lib/fa3/ai-infra-guard/$VERSION}"
SOURCE_DIR="$RUNTIME_ROOT/source"
TREE="$SOURCE_DIR/tree"
ARCHIVE="$SOURCE_DIR/$ARCHIVE_NAME"
BIN_DIR="$RUNTIME_ROOT/bin"
BINARY="$BIN_DIR/ai-infra-guard"
META="$RUNTIME_ROOT/build-metadata.json"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "AI-Infra-Guard bootstrap refuses root" >&2
  exit 3
fi
for x in curl sha256sum python3 go; do
  command -v "$x" >/dev/null || { echo "missing required command: $x" >&2; exit 3; }
done
mkdir -p "$SOURCE_DIR" "$BIN_DIR"

if [[ -f "$ARCHIVE" ]]; then
  ACTUAL="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
  [[ "$ACTUAL" == "$ARCHIVE_SHA256" ]] || { echo "cached source archive digest mismatch" >&2; exit 2; }
else
  TMP="$ARCHIVE.download"
  rm -f "$TMP"
  curl --fail --location --proto '=https' --tlsv1.2 --output "$TMP" "$URL"
  ACTUAL="$(sha256sum "$TMP" | awk '{print $1}')"
  [[ "$ACTUAL" == "$ARCHIVE_SHA256" ]] || { rm -f "$TMP"; echo "downloaded source archive digest mismatch" >&2; exit 2; }
  mv "$TMP" "$ARCHIVE"
fi

TMPDIR_EXTRACT="$(mktemp -d "$SOURCE_DIR/extract.XXXXXX")"
trap 'rm -rf "$TMPDIR_EXTRACT"' EXIT
EXTRACTED_ROOT="$(python3 - "$ARCHIVE" "$TMPDIR_EXTRACT" <<'PY'
import pathlib, sys, tarfile
archive=pathlib.Path(sys.argv[1]).resolve()
dest=pathlib.Path(sys.argv[2]).resolve()
with tarfile.open(archive, "r:gz") as tf:
    members=tf.getmembers()
    for m in members:
        target=(dest/m.name).resolve(strict=False)
        if target != dest and dest not in target.parents:
            raise SystemExit(f"path traversal denied: {m.name}")
        if m.issym() or m.islnk() or m.isdev():
            raise SystemExit(f"link/device archive member denied: {m.name}")
    tf.extractall(dest)
roots=[]
for main in dest.rglob("cmd/cli/main.go"):
    root=main.parents[2]
    if (root/"go.mod").is_file():
        roots.append(root)
if len(roots) != 1:
    raise SystemExit(f"expected exactly one source root, got {len(roots)}")
print(roots[0])
PY
)"
rm -rf "$TREE"
mkdir -p "$TREE"
cp -a "$EXTRACTED_ROOT/." "$TREE/"

(
  cd "$TREE"
  export CGO_ENABLED=0 GOOS=linux GOARCH=amd64
  go build -trimpath -buildvcs=false -o "$BINARY" ./cmd/cli/main.go
)
chmod 0755 "$BINARY"
"$BINARY" --help | grep -q "scan" || { echo "native scan command missing" >&2; exit 2; }

BINARY_SHA="$(sha256sum "$BINARY" | awk '{print $1}')"
GO_VERSION="$(go version)"
TREE_SHA="$(python3 - "$TREE" <<'PY'
import hashlib,pathlib,sys
root=pathlib.Path(sys.argv[1]).resolve()
h=hashlib.sha256()
for p in sorted(x for x in root.rglob("*") if x.is_file()):
    rel=p.relative_to(root).as_posix().encode()
    h.update(len(rel).to_bytes(4,"big")); h.update(rel)
    f=hashlib.sha256()
    with p.open("rb") as fh:
        for b in iter(lambda:fh.read(1024*1024),b""): f.update(b)
    h.update(f.digest())
print(h.hexdigest())
PY
)"
python3 - "$META" "$VERSION" "$COMMIT" "$ARCHIVE" "$ARCHIVE_SHA256" "$TREE" "$TREE_SHA" "$BINARY" "$BINARY_SHA" "$GO_VERSION" <<'PY'
import datetime,json,pathlib,sys
(meta,version,commit,archive,archive_sha,tree,tree_sha,binary,binary_sha,go_version)=sys.argv[1:]
obj={
 "schema":"fa3.ai-infra-guard-build-metadata.v1",
 "release":version,
 "release_commit":commit,
 "source_archive":str(pathlib.Path(archive).resolve()),
 "source_archive_sha256":archive_sha,
 "source_root":str(pathlib.Path(tree).resolve()),
 "source_tree_sha256":tree_sha,
 "binary":str(pathlib.Path(binary).resolve()),
 "binary_sha256":binary_sha,
 "build_toolchain":go_version,
 "build_flags":["CGO_ENABLED=0","GOOS=linux","GOARCH=amd64","-trimpath","-buildvcs=false"],
 "built_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "non_root_build":True,
}
pathlib.Path(meta).write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
print(json.dumps(obj,indent=2))
PY
