#!/usr/bin/env bash
set -euo pipefail
: "${TYPEPHP_ENTRYPOINT:?Set TYPEPHP_ENTRYPOINT to pinned TypePHP bin/tpc.php or vendor/bin/tpc.php}"
[[ -f "$TYPEPHP_ENTRYPOINT" ]] || { echo "TypePHP entrypoint not found: $TYPEPHP_ENTRYPOINT" >&2; exit 2; }
command -v php >/dev/null
command -v sha256sum >/dev/null
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
cat >"$work/canary.php" <<'PHP'
<?php
function main(): void
{
    echo "FA3_TYPEPHP_CANARY_OK\n";
}
PHP
(
  cd "$work"
  php "$TYPEPHP_ENTRYPOINT" canary.php
  [[ -x ./canary ]]
  out="$(./canary)"
  [[ "$out" == "FA3_TYPEPHP_CANARY_OK" ]]
  sha256sum ./canary > artifact.sha256
)
printf '{"gate":"FA3-GATE-TYPEPHP-AOT-NATIVE-001","result":"PASS","scope":"LIVE_COMPILER_CANARY","artifact_sha256":"%s","current_host_runtime_promotion":"NOT_AUTOMATIC"}\n' "$(cut -d' ' -f1 "$work/artifact.sha256")"
