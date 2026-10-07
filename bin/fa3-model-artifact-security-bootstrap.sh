#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${FA3_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
RUNTIME_ROOT="${FA3_MODEL_SECURITY_HOME:-/ai-cache/fa3/model-security}"
ALLOW_NETWORK="${FA3_MODEL_SECURITY_ALLOW_NETWORK_BOOTSTRAP:-0}"
ALLOW_SUDO="${FA3_MODEL_SECURITY_ALLOW_SUDO:-0}"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "Refusing root execution" >&2; exit 2
fi
case "$RUNTIME_ROOT" in
  "$HOME"|"$HOME"/*) echo "RUNTIME_ROOT must be outside HOME for secret-masking sandbox semantics" >&2; exit 2;;
esac

missing=()
for cmd in clamscan yara bwrap curl tar sha256sum; do command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd"); done
if ((${#missing[@]})); then
  if [[ "$ALLOW_SUDO" == "1" ]] && command -v sudo >/dev/null 2>&1; then
    sudo apt-get update
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends clamav yara bubblewrap curl ca-certificates tar
  else
    printf 'Missing system prerequisites: %s\n' "${missing[*]}" >&2
    echo "Install them first or rerun with FA3_MODEL_SECURITY_ALLOW_SUDO=1" >&2; exit 2
  fi
fi

PY="${FA3_MODEL_SECURITY_PYTHON:-}"
if [[ -z "$PY" ]]; then
  for candidate in python3.12 python3.11 python3.10; do command -v "$candidate" >/dev/null 2>&1 && { PY="$candidate"; break; }; done
fi
[[ -n "$PY" ]] || { echo "Python 3.10-3.12 required; system Python 3.14 is intentionally not used" >&2; exit 2; }

mkdir -p "$RUNTIME_ROOT"/{bin,cache/clamav,cache/trivy,cache/pip-audit,rules,state,quarantine,receipts,negative-fixtures,tmp}
chmod 700 "$RUNTIME_ROOT" "$RUNTIME_ROOT"/{quarantine,receipts,negative-fixtures,tmp}
install -m 0644 "$REPO_ROOT/deployment/model-security/yara/fa3-model-security.yar" "$RUNTIME_ROOT/rules/fa3-model-security.yar"

install_venv() {
  local venv="$1"; shift
  if [[ ! -x "$venv/bin/python" ]]; then
    [[ "$ALLOW_NETWORK" == "1" ]] || { echo "Missing $venv and network bootstrap is disabled" >&2; exit 2; }
    "$PY" -m venv "$venv"
  fi
  if [[ "$ALLOW_NETWORK" == "1" ]]; then
    "$venv/bin/python" -m pip install --disable-pip-version-check --no-input --upgrade pip
    "$venv/bin/python" -m pip install --disable-pip-version-check --no-input --upgrade "$@"
  fi
}

install_venv "$RUNTIME_ROOT/venv-static" \
  'modelaudit[all-ci]==0.2.52' 'modelscan==0.8.8' 'picklescan==1.0.5' \
  'fickling==0.1.12' 'bandit==1.9.4' 'pip-audit==2.10.1'
install_venv "$RUNTIME_ROOT/venv-garak" 'garak==0.16.0'

install_release_binary() {
  local name="$1" version="$2" asset="$3" checksums="$4" urlbase="$5"
  local dest="$RUNTIME_ROOT/bin/$name" work="$RUNTIME_ROOT/tmp/$name-$version"
  if [[ -x "$dest" ]]; then
    if [[ "$name" == "cosign" ]]; then
      "$dest" version 2>&1 | grep -Fq "$version" && return 0
    else
      "$dest" --version 2>&1 | head -n1 | grep -Fq "$version" && return 0
    fi
  fi
  [[ "$ALLOW_NETWORK" == "1" ]] || { echo "$name $version missing and network bootstrap disabled" >&2; exit 2; }
  rm -rf "$work"; mkdir -p "$work"
  curl -fL --retry 3 "$urlbase/$checksums" -o "$work/$checksums"
  curl -fL --retry 3 "$urlbase/$asset" -o "$work/$asset"
  (cd "$work" && grep -E "[[:space:]]${asset//./\\.}$" "$checksums" | sha256sum -c -)
  case "$asset" in
    *.tar.gz) tar -xzf "$work/$asset" -C "$work"; install -m 0755 "$work/$name" "$dest" ;;
    *) install -m 0755 "$work/$asset" "$dest" ;;
  esac
}

install_release_binary trivy 0.74.0 trivy_0.74.0_Linux-64bit.tar.gz trivy_0.74.0_checksums.txt https://github.com/aquasecurity/trivy/releases/download/v0.74.0
install_release_binary cosign 3.1.2 cosign-linux-amd64 cosign_checksums.txt https://github.com/sigstore/cosign/releases/download/v3.1.2

if [[ "$ALLOW_NETWORK" == "1" ]]; then
  "$RUNTIME_ROOT/bin/trivy" image --cache-dir "$RUNTIME_ROOT/cache/trivy" --download-db-only
  if command -v freshclam >/dev/null 2>&1; then
    freshclam --datadir="$RUNTIME_ROOT/cache/clamav" || true
  fi
fi

if ! find "$RUNTIME_ROOT/cache/clamav" /var/lib/clamav -maxdepth 1 -type f \( -name '*.cvd' -o -name '*.cld' \) -size +0c -print -quit 2>/dev/null | grep -q .; then
  echo "No ClamAV signature database available" >&2; exit 2
fi
if ! find "$RUNTIME_ROOT/cache/trivy" -type f -name trivy.db -size +0c -print -quit 2>/dev/null | grep -q .; then
  echo "No Trivy vulnerability database available" >&2; exit 2
fi

python3 - "$RUNTIME_ROOT" <<'PY'
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]); rows=[]
for base in [root/'cache/clamav', Path('/var/lib/clamav'), root/'cache/trivy']:
    if base.is_dir():
        for p in sorted(base.rglob('*')):
            if p.is_file() and p.stat().st_size:
                rows.append({'path_class':base.name,'name':p.name,'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns})
payload=json.dumps(rows,sort_keys=True).encode()
out={'schema':'fa3.model-security-database-manifest.v1','entries':rows,'manifest_sha256':hashlib.sha256(payload).hexdigest()}
(root/'state/database-manifest.json').write_text(json.dumps(out,indent=2)+'\n')
PY

export FA3_MODEL_SECURITY_HOME="$RUNTIME_ROOT"
PYTHONPATH="$REPO_ROOT/src" python3 - "$REPO_ROOT" <<'PY'
import json,sys
from pathlib import Path
from fa3_model_artifact_security_runtime import collect_tool_inventory,runtime_home
root=Path(sys.argv[1]); inv=collect_tool_inventory(root,runtime_home())
missing=[k for k,v in inv.items() if not v.get('present') or not v.get('binary_or_package_digest') or not v.get('ruleset_digest')]
print(json.dumps(inv,indent=2))
if missing: raise SystemExit('tool identity incomplete: '+','.join(missing))
PY

echo "FA3 model artifact security runtime bootstrap complete: $RUNTIME_ROOT"
