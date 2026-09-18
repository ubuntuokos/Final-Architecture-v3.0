#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "\${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_ROOT="\${FA3_PAGEINDEX_MCP_SOURCE_ROOT:-}"
OAUTH_HOME="\${FA3_PAGEINDEX_MCP_OAUTH_HOME:-}"
SAMPLE_PDF="\${FA3_PAGEINDEX_MCP_SAMPLE_PDF:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source-root) SOURCE_ROOT="$2"; shift 2 ;;
    --oauth-home) OAUTH_HOME="$2"; shift 2 ;;
    --sample-pdf) SAMPLE_PDF="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

test -n "$SOURCE_ROOT" || { echo "FA3_PAGEINDEX_MCP_SOURCE_ROOT/--source-root required" >&2; exit 2; }
test -n "$OAUTH_HOME" || { echo "FA3_PAGEINDEX_MCP_OAUTH_HOME/--oauth-home required" >&2; exit 2; }
test -n "$SAMPLE_PDF" || { echo "FA3_PAGEINDEX_MCP_SAMPLE_PDF/--sample-pdf required" >&2; exit 2; }
test -r "$OAUTH_HOME/.pageindex-mcp/oauth-tokens.json" || { echo "ephemeral OAuth materialization missing" >&2; exit 2; }
test -r "$SAMPLE_PDF" || { echo "sample PDF missing" >&2; exit 2; }

PYTHONPATH="$ROOT/src\${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$ROOT/evidence/collect-pageindex-mcp-current-host.py" \
  --source-root "$SOURCE_ROOT" \
  --oauth-home "$OAUTH_HOME" \
  --sample-pdf "$SAMPLE_PDF"

PYTHONPATH="$ROOT/src\${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$ROOT/src/fa3_pageindex_mcp_gate.py" --root "$ROOT" --current-host
