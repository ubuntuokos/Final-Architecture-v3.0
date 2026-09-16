#!/usr/bin/env bash
set -euo pipefail

HELPER="/usr/local/libexec/fa3-host-resource-broker-validate-root"

if [[ $# -ne 2 || ( "$1" != "validate-lease" && "$1" != "validate-authorization" ) ]]; then
  echo "usage: fa3-host-resource-broker-validator {validate-lease|validate-authorization} /absolute/path/to/record.json" >&2
  exit 3
fi
if [[ "$2" != /* ]]; then
  echo "DENIED: record path must be absolute" >&2
  exit 2
fi
exec sudo -n -- "$HELPER" "$1" "$2"
