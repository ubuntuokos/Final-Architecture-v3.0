# FA3 MCP Gateway — first 24 hours of transaction observation

This implementation observes the **existing** single logical Central MCP Gateway
(FA3-AUTH-MCP-GATEWAY-001), not the historical three-fixed-port shard-router sketch.
It neither changes the canonical MCP 2026-07-28 stateless contract nor creates
a new authority. The active FA3 capability baseline is 175; the MCP registry
contains only its explicitly exposed/admitted subset.

## Hardware Audit compliance (before any host execution)

- Observation-only Python code: CPU-only valid; 0..N accelerators; no vendor,
  GPU SKU, PCI address, CPU-core count, desktop environment or scheduler pin.
- The monitoring code never chooses a device, starts a model, changes port
  assignments, adjusts affinity or writes to cgroups.
- HRB remains the only resource placement/lease authority. Physical cores and
  logical processors must not be conflated in host diagnostics.
- X11/Wayland and KDE/GNOME/other desktop sessions are outside this server-side
  observer. It imposes no graphical session requirement.
- No new external donor dependency is introduced. The central Donor & Reference
  Registry was queried; the standard library suffices for this scoped change.

## Enable only for a controlled first-day run

The normal Gateway stays unchanged when telemetry is disabled. For a first-day
observation run, create a private log directory and pass a path using the CLI
or environment variable (both use the same code):

```bash
install -d -m 0700 "$HOME/.local/state/fa3/mcp"
export FA3_MCP_TELEMETRY_JSONL="$HOME/.local/state/fa3/mcp/transactions.jsonl"
./bin/fa3-mcp-gateway
# Alternative if invoking the Python server directly:
# PYTHONPATH=src python3 src/fa3_mcp_gateway_server.py \
#   --registry canonical/mcp-capability-registry.json \
#   --telemetry-jsonl "$FA3_MCP_TELEMETRY_JSONL"
```

Use the existing admitted adapter, external policy resolver, approval and HRB
provisioning. Merely starting the server does not make an adapter CONNECTED.
Do not expose the default loopback port externally or alter AdGuardHome ports.

Every completed dispatch/deny through `McpGateway.invoke` writes **only**
receipt status, reason code, profile, safe capability/provider identifiers,
duration and timestamp. Rejected untrusted capability identifiers are hidden.
No action arguments, provider result, user/agent identity, session ID, request
hash, policy token, raw credential or secret reference is persisted.

The log is a **local operational observation**, not an immutable security
journal, signed evidence receipt, Temporal event or runtime-promotion proof.
Writes use `O_APPEND`, advisory locking, `fsync` and private (0600) files.
A broken observer does not return a false-successful Gateway response, but
the observer runs after provider execution and cannot undo already-completed
side effects. The existing provider audit, canonical Journal and Evidence
Registry remain the durable sources of truth.

## First-day report

```bash
python3 bin/fa3-mcp-day1 \
  --jsonl "$FA3_MCP_TELEMETRY_JSONL" \
  --hours 24 \
  --require-events
```

A report contains observed successful/denied invocations, denial reason counts
and p95 gateway processing time. If there were no matching events,
`--require-events` exits nonzero. Missing, corrupt, oversized or non-private
files also produce a nonzero exit; no result is silently promoted.

## Host-side checklist

1. Verify the *actual* Gateway instance and its admitted adapters; query its
   `/healthz`, `/readyz`, and canonical `server/discover` route through the
   configured loopback/Unix socket. Healthy process != admitted provider.
2. Read the 24-hour transaction report. Investigate repeated unexpected deny
   reasons and rising duration; a deliberate negative-policy test is **not**
   itself a production security incident. Confirm required provider receipts
   and Journal/Evidence links separately.
3. Run the real canonical `./bin/fa3-enforce mcp-current-host` check on the
   designated host with actual scope-bound E2E evidence. Do not substitute
   mocked tests, this telemetry report or a historical 143-capability receipt.
4. Examine the host's *actual* resource allocation under HRB. Check process
   `Cpus_allowed_list` and `Mems_allowed_list` in `/proc/<pid>/status` and
   inspect current cgroup effective masks and the applicable HRB lease.
   `ps -o psr` reports only the last observed CPU, **not** allowed affinity.
   Use `podman stats --no-stream` only for containers that actually exist.
5. Check the canonical Journal/retention and incident-handling pipeline.
   The JSONL observer does not automatically rotate logs or trigger Temporal.
   Escalate only a validated incident through the existing Security/UAF/
   Temporal authorities; an ordinary malformed request must not shut down
   every workload.
6. Validate desktop independence and the vendor-neutral CPU-only case in
   regression tests. Confirm that the host's real hardware evidence remains
   separate from the portable, static test fixtures.

For repository-level verification:

```bash
python3 -m unittest discover -s tests -p 'test_mcp_day1_telemetry.py' -v
python3 -m unittest discover -s tests -p 'test_mcp_gateway_final.py' -v
./bin/fa3-enforce mcp-gateway
```

A successful unit test or static gate does **not** assert the current host has
been promoted. UAF actions that do not enter MCP require their own separately
authorized observability adapter; this change does not claim to observe them.
