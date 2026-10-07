#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "must run as root" >&2
  exit 2
fi
if [[ $# -ne 1 ]]; then
  echo "usage: $0 /path/to/security-governance-approval.pub" >&2
  exit 2
fi

src=$1
dst_dir=/etc/fa3/trust
dst=${dst_dir}/security-governance-approval.pub

[[ -f "$src" ]] || { echo "public key not found: $src" >&2; exit 2; }
command -v openssl >/dev/null 2>&1 || { echo "openssl required" >&2; exit 2; }

openssl pkey -pubin -in "$src" -noout >/dev/null 2>&1 || {
  echo "input is not a valid public key" >&2
  exit 2
}

install -d -o root -g root -m 0755 "$dst_dir"
tmp=$(mktemp "${dst_dir}/.approval-key.XXXXXX")
trap 'rm -f "$tmp"' EXIT
install -o root -g root -m 0644 "$src" "$tmp"
mv -f "$tmp" "$dst"
trap - EXIT

owner=$(stat -c '%u' "$dst")
mode=$(stat -c '%a' "$dst")
[[ "$owner" == "0" ]] || { echo "verification key is not root-owned" >&2; exit 2; }
case "$mode" in
  644|640|600) ;;
  *) echo "unexpected verification key mode: $mode" >&2; exit 2 ;;
esac

echo "installed $dst"
