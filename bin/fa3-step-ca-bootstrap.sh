#!/usr/bin/env bash
set -euo pipefail
ROOT="${FA3_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STATE="${FA3_STEP_CA_BOOTSTRAP_STATE:-$ROOT/.fa3-current-host/step-ca/bootstrap}"
IDENTITY_RE='https://github\.com/smallstep/workflows/.*'; ISSUER='https://token.actions.githubusercontent.com'
arch(){ case "$(uname -m)" in x86_64|amd64) echo amd64;; aarch64|arm64) echo arm64;; *) echo "unsupported arch" >&2; exit 2;; esac; }
cosign_bin(){ if [[ -n "${FA3_COSIGN_BIN:-}" && -x "$FA3_COSIGN_BIN" ]]; then echo "$FA3_COSIGN_BIN"; elif command -v cosign >/dev/null 2>&1; then command -v cosign; elif [[ -x /ai-cache/fa3/model-security/bin/cosign ]]; then echo /ai-cache/fa3/model-security/bin/cosign; else echo "cosign required" >&2; exit 2; fi; }
sha(){ sha256sum "$1"|awk '{print $1}'; }
fetch_verify(){ local repo="$1" ver="$2" asset="$3" expected="$4" bundle="$5" csum="$6" out="$7"; local base; base="https://github.com/$repo/releases/download/v$ver"; mkdir -p "$out"; curl -fL --retry 3 "$base/checksums.txt" -o "$out/checksums.txt"; curl -fL --retry 3 "$base/$asset" -o "$out/$asset"; curl -fL --retry 3 "$base/$asset.sigstore.json" -o "$out/$asset.sigstore.json"; [[ "$(sha "$out/checksums.txt")" == "$csum" ]]; [[ "$(sha "$out/$asset")" == "$expected" ]]; [[ "$(sha "$out/$asset.sigstore.json")" == "$bundle" ]]; (cd "$out" && grep -F "$asset" checksums.txt | sha256sum -c -); "$(cosign_bin)" verify-blob --bundle "$out/$asset.sigstore.json" --certificate-identity-regexp "$IDENTITY_RE" --certificate-oidc-issuer "$ISSUER" "$out/$asset" >/dev/null; }
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
 fetch_verify smallstep/certificates 0.30.2 "$sasset" "$ssha" "$sbundle" 5076defb1b4759f270fd85a31fc7e4756ddf2551237249aa12739f5be1544f98 "$STATE/work/server"
 fetch_verify smallstep/cli 0.30.6 "$casset" "$csha" "$cbundle" f546be6b4ccd74e9939d374390f2f0053949f447bf314e8dbd1572ad05493862 "$STATE/work/client"
 install -m0755 "$(extract_bin "$STATE/work/server/$sasset" step-ca "$STATE/work/server/extracted")" "$STATE/bin/step-ca"; install -m0755 "$(extract_bin "$STATE/work/client/$casset" step "$STATE/work/client/extracted")" "$STATE/bin/step"
 python3 - "$STATE" "$a" "$sasset" "$ssha" "$casset" "$csha" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
s=Path(sys.argv[1]); h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def v(p):
 r=subprocess.run([str(p),"version"],text=True,capture_output=True)
 return (r.stdout or r.stderr).strip()
x={"schema":"fa3.step-ca-supply-chain-receipt.v1","status":"PASS","architecture":sys.argv[2],"server":{"version":"0.30.2","asset":sys.argv[3],"asset_sha256":sys.argv[4],"binary_sha256":h(s/"bin/step-ca"),"version_output":v(s/"bin/step-ca"),"sigstore_verified":True},"client":{"version":"0.30.6","asset":sys.argv[5],"asset_sha256":sys.argv[6],"binary_sha256":h(s/"bin/step"),"version_output":v(s/"bin/step"),"sigstore_verified":True},"secret_values_collected":False}
(s/"supply-chain.json").write_text(json.dumps(x,indent=2)+"\n")
PY
}
install_runtime(){
 [[ "$(id -u)" -eq 0 ]] || { echo "install requires root" >&2; exit 2; }; [[ -f "$STATE/supply-chain.json" && -x "$STATE/bin/step-ca" && -x "$STATE/bin/step" ]]
 id fa3-step-ca >/dev/null 2>&1 || useradd --system --home-dir /var/lib/fa3-step-ca --shell /usr/sbin/nologin fa3-step-ca
 install -d -o fa3-step-ca -g fa3-step-ca -m0700 /var/lib/fa3-step-ca/{certs,secrets,db,evidence}; install -d -o root -g root -m0755 /usr/local/lib/fa3/step-ca/0.30.2/bin /usr/local/lib/fa3/step-cli/0.30.6/bin /etc/fa3/step-ca; install -d -o root -g root -m0700 /etc/fa3/secrets
 install -m0755 "$STATE/bin/step-ca" /usr/local/lib/fa3/step-ca/0.30.2/bin/step-ca; install -m0755 "$STATE/bin/step" /usr/local/lib/fa3/step-cli/0.30.6/bin/step; ln -sfn /usr/local/lib/fa3/step-ca/0.30.2/bin/step-ca /usr/local/bin/step-ca; ln -sfn /usr/local/lib/fa3/step-cli/0.30.6/bin/step /usr/local/bin/step
 install -m0644 "$ROOT/deployment/step-ca/fa3-step-ca.service" /etc/systemd/system/fa3-step-ca.service; systemctl daemon-reload; echo "Installed verified binaries/unit only; no CA key created, service not started."
}
case "${1:-}" in prepare) prepare;; install) install_runtime;; *) echo "usage: $0 {prepare|install}" >&2; exit 2;; esac
