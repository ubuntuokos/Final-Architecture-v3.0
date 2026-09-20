#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${FA3_SESSION_VAULT_IMAGE:-$HOME/.local/share/fa3/state/fa3-state.img}"
RUNTIME="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
TRANSFER="${FA3_STEP_CA_TRANSFER_DIR:-$RUNTIME/fa3-step-ca-transfer}"
RECEIPT="${FA3_STEP_CA_ROOT_CEREMONY_RECEIPT:-$ROOT/evidence/receipts/step-ca-root-ceremony.json}"
OPERATOR_ID="${FA3_STEP_CA_OPERATOR_ID:-local-operator}"
LOOP=""
CLEAR=""
MOUNT=""

die(){ echo "step-ca root ceremony: $*" >&2; exit 2; }
need(){ command -v "$1" >/dev/null 2>&1 || die "missing prerequisite: $1"; }

cleanup(){
  if [[ -n "$MOUNT" ]] && findmnt -rn "$MOUNT" >/dev/null 2>&1; then
    udisksctl unmount --block-device "$CLEAR" >/dev/null 2>&1 || true
  fi
  if [[ -n "$LOOP" && -b "$LOOP" ]]; then
    udisksctl lock --block-device "$LOOP" >/dev/null 2>&1 || true
    udisksctl loop-delete --block-device "$LOOP" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

[[ "$(id -u)" -ne 0 ]] || die "run as the desktop user, not root"
for c in udisksctl openssl python3 findmnt lsblk install cp cmp grep awk stat; do need "$c"; done
[[ -f "$IMAGE" && ! -L "$IMAGE" ]] || die "FA3 state image missing: $IMAGE"
[[ "$(stat -c '%a' "$IMAGE")" == "600" ]] || die "FA3 state image mode must be 0600"

loop_out="$(udisksctl loop-setup --file "$IMAGE")"
LOOP="$(printf '%s\n' "$loop_out" | grep -oE '/dev/loop[0-9]+' | tail -n1)"
[[ -n "$LOOP" && -b "$LOOP" ]] || die "failed to discover UDisks2 loop device"

echo "Unlocking FA3 encrypted state image. Enter the vault passphrase when prompted."
unlock_out="$(udisksctl unlock --block-device "$LOOP")"
CLEAR="$(printf '%s\n' "$unlock_out" | grep -oE '/dev/(dm-[0-9]+|mapper/[^ .]+)' | tail -n1)"
if [[ -z "$CLEAR" || ! -b "$CLEAR" ]]; then
  CLEAR="$(lsblk -nrpo NAME,TYPE "$LOOP" | awk '$2=="crypt"{print $1; exit}')"
fi
[[ -n "$CLEAR" && -b "$CLEAR" ]] || die "failed to discover cleartext vault device"

udisksctl mount --block-device "$CLEAR" --options nodev,nosuid,noexec >/dev/null
MOUNT="$(findmnt -rn -S "$CLEAR" -o TARGET | head -n1)"
[[ -n "$MOUNT" && -d "$MOUNT" ]] || die "failed to discover vault mount point"

ROOT_DIR="$MOUNT/pki/root"
install -d -m0700 "$ROOT_DIR"
umask 077

required=(
  root-password.txt root_ca_key root_ca.crt
  intermediate-password.txt intermediate_ca_key intermediate_ca.csr
  intermediate.ext intermediate_ca.crt jwk-password.txt
)
present=0
for f in "${required[@]}"; do [[ -e "$ROOT_DIR/$f" ]] && ((present+=1)) || true; done
if (( present != 0 && present != ${#required[@]} )); then
  die "partial PKI material found in vault ($present/${#required[@]}); refusing regeneration"
fi

if (( present == 0 )); then
  echo "Creating encrypted FA3 Root and Intermediate CA material inside the state image."
  openssl rand -base64 48 > "$ROOT_DIR/root-password.txt"
  openssl rand -base64 48 > "$ROOT_DIR/intermediate-password.txt"
  openssl rand -base64 48 > "$ROOT_DIR/jwk-password.txt"

  openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-384     -aes-256-cbc -pass file:"$ROOT_DIR/root-password.txt"     -out "$ROOT_DIR/root_ca_key"

  openssl req -new -x509 -sha384 -days 3650     -key "$ROOT_DIR/root_ca_key"     -passin file:"$ROOT_DIR/root-password.txt"     -subj "/CN=FA3 Offline Root CA"     -addext "basicConstraints=critical,CA:TRUE,pathlen:1"     -addext "keyUsage=critical,keyCertSign,cRLSign"     -out "$ROOT_DIR/root_ca.crt"

  openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256     -aes-256-cbc -pass file:"$ROOT_DIR/intermediate-password.txt"     -out "$ROOT_DIR/intermediate_ca_key"

  openssl req -new -sha256     -key "$ROOT_DIR/intermediate_ca_key"     -passin file:"$ROOT_DIR/intermediate-password.txt"     -subj "/CN=FA3 Issuing Intermediate CA"     -out "$ROOT_DIR/intermediate_ca.csr"

  cat > "$ROOT_DIR/intermediate.ext" <<'EOF'
basicConstraints=critical,CA:TRUE,pathlen:0
keyUsage=critical,keyCertSign,cRLSign
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer
EOF

  openssl x509 -req -sha256 -days 1095     -in "$ROOT_DIR/intermediate_ca.csr"     -CA "$ROOT_DIR/root_ca.crt"     -CAkey "$ROOT_DIR/root_ca_key"     -passin file:"$ROOT_DIR/root-password.txt"     -CAcreateserial     -extfile "$ROOT_DIR/intermediate.ext"     -out "$ROOT_DIR/intermediate_ca.crt"
fi

grep -q "ENCRYPTED PRIVATE KEY" "$ROOT_DIR/root_ca_key" || die "Root private key is not encrypted"
grep -q "ENCRYPTED PRIVATE KEY" "$ROOT_DIR/intermediate_ca_key" || die "Intermediate private key is not encrypted"
openssl verify -CAfile "$ROOT_DIR/root_ca.crt" "$ROOT_DIR/root_ca.crt" >/dev/null
openssl verify -CAfile "$ROOT_DIR/root_ca.crt" "$ROOT_DIR/intermediate_ca.crt" >/dev/null

python3 "$ROOT/evidence/collect-step-ca-root-ceremony.py"   --root-cert "$ROOT_DIR/root_ca.crt"   --intermediate-cert "$ROOT_DIR/intermediate_ca.crt"   --operator-id "$OPERATOR_ID"   --medium-id "fa3-state-image"   --output "$RECEIPT" >/dev/null

rm -rf -- "$TRANSFER"
install -d -m0700 "$TRANSFER"
install -m0644 "$ROOT_DIR/root_ca.crt" "$TRANSFER/root_ca.crt"
install -m0644 "$ROOT_DIR/intermediate_ca.crt" "$TRANSFER/intermediate_ca.crt"
install -m0600 "$ROOT_DIR/intermediate_ca_key" "$TRANSFER/intermediate_ca_key"
install -m0600 "$ROOT_DIR/intermediate-password.txt" "$TRANSFER/intermediate-password.txt"
install -m0600 "$ROOT_DIR/jwk-password.txt" "$TRANSFER/jwk-password.txt"
install -m0644 "$RECEIPT" "$TRANSFER/step-ca-root-ceremony.json"

for forbidden in root_ca_key root-password.txt root_ca.key root.key; do
  [[ ! -e "$TRANSFER/$forbidden" ]] || die "forbidden Root secret escaped into transfer bundle"
done
[[ "$(find "$TRANSFER" -maxdepth 1 -type f | wc -l)" -eq 6 ]] || die "unexpected transfer-bundle contents"

echo "FA3 step-ca Root ceremony PASS"
echo "Root custody remains inside encrypted state image: $ROOT_DIR"
echo "Online activation bundle: $TRANSFER"
echo
echo "Next command:"
echo "  sudo FA3_REPO_ROOT=\"$ROOT\" $ROOT/bin/fa3-step-ca-activate.sh \\"
echo "    --transfer-dir \"$TRANSFER\" \\"
echo "    --ceremony-receipt \"$TRANSFER/step-ca-root-ceremony.json\" \\"
echo "    --intermediate-password-file \"$TRANSFER/intermediate-password.txt\" \\"
echo "    --jwk-password-file \"$TRANSFER/jwk-password.txt\""
