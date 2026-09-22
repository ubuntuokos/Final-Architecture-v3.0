#!/usr/bin/env bash
set -euo pipefail
ROOT="${FA3_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STATE="${FA3_STEP_CA_BOOTSTRAP_STATE:-$ROOT/.fa3-current-host/step-ca/bootstrap}"
IDENTITY_RE='https://github\.com/smallstep/workflows/.*'; ISSUER='https://token.actions.githubusercontent.com'
arch(){ case "$(uname -m)" in x86_64|amd64) echo amd64;; aarch64|arm64) echo arm64;; *) echo "unsupported arch" >&2; exit 2;; esac; }
cosign_expected_sha(){ case "$1" in amd64) echo f7622ed3cf22e55e1ae6377c080979ff77a22da9981c11df222a2e444991e7cf;; arm64) echo 90e7ae0b5dfd60f20816b52c012addf7fc055ebcc7bea4ce81c428ca8518c302;; *) return 2;; esac; }
validate_cosign(){
 local path="$1" a="$2" expected
 expected="$(cosign_expected_sha "$a")" || return 2
 [[ -x "$path" ]] || return 1
 [[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || return 1
 "$path" version 2>&1 | grep -Fq "3.1.2"
}
bootstrap_cosign(){
 local a="$1" asset expected work="$STATE/work/cosign" base="https://github.com/sigstore/cosign/releases/download/v3.1.2"
 case "$a" in amd64) asset="cosign-linux-amd64";; arm64) asset="cosign-linux-arm64";; *) return 2;; esac
 expected="$(cosign_expected_sha "$a")" || return 2
 mkdir -p "$work" "$STATE/bin"
 curl -fL --retry 3 "$base/cosign_checksums.txt" -o "$work/cosign_checksums.txt"
 curl -fL --retry 3 "$base/$asset" -o "$work/$asset"
 [[ "$(sha "$work/cosign_checksums.txt")" == "3ef5d389c3f508b96025fd1b92744a305c46e95951c91242b57467567d5622db" ]] || { echo "cosign checksum-manifest digest mismatch" >&2; return 2; }
 [[ "$(sha "$work/$asset")" == "$expected" ]] || { echo "cosign binary digest mismatch" >&2; return 2; }
 verify_checksum_entry "$work/cosign_checksums.txt" "$asset" "$work" >&2
 install -m0755 "$work/$asset" "$STATE/bin/cosign"
 validate_cosign "$STATE/bin/cosign" "$a" || { echo "bootstrapped cosign identity mismatch" >&2; return 2; }
 echo "$STATE/bin/cosign"
}
resolve_cosign(){
 local a="$1" candidate
 for candidate in "${FA3_COSIGN_BIN:-}" /ai-cache/fa3/model-security/bin/cosign "$(command -v cosign 2>/dev/null || true)"; do
  [[ -n "$candidate" ]] || continue
  if validate_cosign "$candidate" "$a"; then echo "$candidate"; return 0; fi
 done
 bootstrap_cosign "$a"
}
sha(){ sha256sum "$1"|awk '{print $1}'; }
verify_checksum_entry(){
 local manifest="$1" asset="$2" workdir="$3" line count
 line="$(awk -v name="$asset" '$2 == name {print}' "$manifest")"
 count="$(printf '%s\n' "$line" | sed '/^$/d' | wc -l)"
 [[ "$count" -eq 1 ]] || { echo "checksum manifest must contain exactly one entry for $asset (found $count)" >&2; return 2; }
 if ! (cd "$workdir" && printf '%s\n' "$line" | sha256sum -c -); then
  echo "checksum verification failed for $asset" >&2
  return 2
 fi
}
fetch_verify(){ local repo="$1" ver="$2" asset="$3" expected="$4" bundle="$5" csum="$6" out="$7" verifier="$8"; local base; base="https://github.com/$repo/releases/download/v$ver"; mkdir -p "$out"; curl -fL --retry 3 "$base/checksums.txt" -o "$out/checksums.txt"; curl -fL --retry 3 "$base/$asset" -o "$out/$asset"; curl -fL --retry 3 "$base/$asset.sigstore.json" -o "$out/$asset.sigstore.json"; [[ "$(sha "$out/checksums.txt")" == "$csum" ]]; [[ "$(sha "$out/$asset")" == "$expected" ]]; [[ "$(sha "$out/$asset.sigstore.json")" == "$bundle" ]]; verify_checksum_entry "$out/checksums.txt" "$asset" "$out"; "$verifier" verify-blob --bundle "$out/$asset.sigstore.json" --certificate-identity-regexp "$IDENTITY_RE" --certificate-oidc-issuer "$ISSUER" "$out/$asset" >/dev/null; }
extract_bin(){ python3 - "$1" "$2" "$3" <<'PY'
import os,sys,tarfile
from pathlib import Path
a=Path(sys.argv[1]); n=sys.argv[2]; o=Path(sys.argv[3]); o.mkdir(parents=True,exist_ok=True)
with tarfile.open(a,"r:gz") as t:
 for m in t.getmembers():
  p=(o/m.name).resolve()
  if o.resolve()!=p and o.resolve() not in p.parents: raise SystemExit("path traversal")
  if m.issym() or m.islnk(): raise SystemExit("archive links forbidden")
 t.extractall(o)
c=[p for p in o.rglob(n) if p.is_file()]
if len(c)!=1: raise SystemExit(f"expected one {n}, found {len(c)}")
os.chmod(c[0],0o755); print(c[0])
PY
}
prepare(){
 [[ "$(id -u)" -ne 0 ]] || { echo "prepare must be non-root" >&2; exit 2; }; command -v curl >/dev/null; command -v python3 >/dev/null
 local a sasset ssha sbundle casset csha cbundle; a="$(arch)"
 if [[ "$a" == amd64 ]]; then sasset="step-ca_linux_0.30.2_amd64.tar.gz"; ssha="126615795bafe3f2d3f890e2d628fa6e2857315fb48d0671d34b23047cc37d73"; sbundle="10d2a667781a8c1fd4aaf45faafe6dcf830ca60e5c9456b7ce242225ae91260c"; casset="step_linux_0.30.6_amd64.tar.gz"; csha="e44a5dc5f880a694b24a0f2941a69a81b0bc6ee053170fdfde18453d4d5816de"; cbundle="d8f8e032e25bf897b05164b7f3c9ddbe3f004099a33e7166ecaea457f7a40f5c"; else sasset="step-ca_linux_0.30.2_arm64.tar.gz"; ssha="43f79d1b0b8cab9895dbadd46b0a014006f682a6b1341e1fadf0be31d4b9f4b4"; sbundle="57f7814370c5ba0f6d84525eec6e73fc116beec589cb16ccc8403e012266930c"; casset="step_linux_0.30.6_arm64.tar.gz"; csha="eff511c3e6797039702e74fada62b10b079e413742f925703e5b7d810e611619"; cbundle="fdb33d602d7541b002bca55094da3cb8f161878227a60afc97372a2bc438efed"; fi
 rm -rf "$STATE/work"; mkdir -p "$STATE/work/server" "$STATE/work/client" "$STATE/bin"
 local verifier
 if ! verifier="$(resolve_cosign "$a")"; then echo "unable to obtain pinned cosign 3.1.2 verifier" >&2; exit 2; fi
 fetch_verify smallstep/certificates 0.30.2 "$sasset" "$ssha" "$sbundle" 5076defb1b4759f270fd85a31fc7e4756ddf2551237249aa12739f5be1544f98 "$STATE/work/server" "$verifier"
 fetch_verify smallstep/cli 0.30.6 "$casset" "$csha" "$cbundle" f546be6b4ccd74e9939d374390f2f0053949f447bf314e8dbd1572ad05493862 "$STATE/work/client" "$verifier"
 install -m0755 "$(extract_bin "$STATE/work/server/$sasset" step-ca "$STATE/work/server/extracted")" "$STATE/bin/step-ca"; install -m0755 "$(extract_bin "$STATE/work/client/$casset" step "$STATE/work/client/extracted")" "$STATE/bin/step"
 python3 - "$STATE" "$a" "$sasset" "$ssha" "$casset" "$csha" "$verifier" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
s=Path(sys.argv[1]); h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def v(p):
 r=subprocess.run([str(p),"version"],text=True,capture_output=True)
 return (r.stdout or r.stderr).strip()
x={"schema":"fa3.step-ca-supply-chain-receipt.v1","status":"PASS","architecture":sys.argv[2],"verifier":{"name":"cosign","version":"3.1.2","binary_sha256":h(Path(sys.argv[7])),"version_output":v(Path(sys.argv[7])),"trust_bootstrap":"REPO_PINNED_BINARY_AND_CHECKSUMS_DIGEST"},"server":{"version":"0.30.2","asset":sys.argv[3],"asset_sha256":sys.argv[4],"binary_sha256":h(s/"bin/step-ca"),"version_output":v(s/"bin/step-ca"),"sigstore_verified":True},"client":{"version":"0.30.6","asset":sys.argv[5],"asset_sha256":sys.argv[6],"binary_sha256":h(s/"bin/step"),"version_output":v(s/"bin/step"),"sigstore_verified":True},"secret_values_collected":False}
(s/"supply-chain.json").write_text(json.dumps(x,indent=2)+"\n")
PY
}
install_runtime(){
 [[ "$(id -u)" -eq 0 ]] || { echo "install requires root" >&2; exit 2; }; [[ -f "$STATE/supply-chain.json" && -x "$STATE/bin/step-ca" && -x "$STATE/bin/step" ]]
 id fa3-step-ca >/dev/null 2>&1 || useradd --system --home-dir /var/lib/fa3-step-ca --shell /usr/sbin/nologin fa3-step-ca
 install -d -o fa3-step-ca -g fa3-step-ca -m0755 /var/lib/fa3-step-ca/{certs,evidence}
 install -d -o fa3-step-ca -g fa3-step-ca -m0711 /var/lib/fa3-step-ca/secrets
 install -d -o fa3-step-ca -g fa3-step-ca -m0700 /var/lib/fa3-step-ca/db
 install -d -o root -g root -m0755 /usr/local/lib/fa3/step-ca/0.30.2/bin /usr/local/lib/fa3/step-cli/0.30.6/bin /etc/fa3/step-ca; install -d -o root -g root -m0700 /etc/fa3/secrets
 install -m0755 "$STATE/bin/step-ca" /usr/local/lib/fa3/step-ca/0.30.2/bin/step-ca; install -m0755 "$STATE/bin/step" /usr/local/lib/fa3/step-cli/0.30.6/bin/step; ln -sfn /usr/local/lib/fa3/step-ca/0.30.2/bin/step-ca /usr/local/bin/step-ca; ln -sfn /usr/local/lib/fa3/step-cli/0.30.6/bin/step /usr/local/bin/step
 install -m0644 "$ROOT/deployment/step-ca/fa3-step-ca.service" /etc/systemd/system/fa3-step-ca.service; systemctl daemon-reload; echo "Installed verified binaries/unit only; no CA key created, service not started."
}
case "${1:-}" in prepare) prepare;; install) install_runtime;; *) echo "usage: $0 {prepare|install}" >&2; exit 2;; esac
