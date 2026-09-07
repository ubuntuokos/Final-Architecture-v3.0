# FA3 Buzz safe runtime admission

`FA3-PROVIDER-BUZZ-001` remains an optional, disabled-by-default reference provider. This layer does **not** make Buzz an FA3 authority and does **not** claim that Buzz is installed or production-admitted on the current host.

## Canonical route

```text
Buzz actor identity
  -> DelegatedCallerContext
  -> CapabilityGrant
  -> FA3 Security/Governance authorization lease
  -> Central MCP/Capability Gateway
  -> FA3 Buzz wrapper
  -> bounded workspace/provider operation
  -> proposed diff
  -> authorization or human gate
  -> atomic apply
  -> post-state verification
  -> FA3 evidence projection
```

The raw `buzz-dev-mcp` direct host-tool path is explicitly denied. Upstream provider/tool permissions are only a maximum surface; they are never an FA3 grant.

## Admission invariants

Provider discovery must not execute the provider. The selected provider is staged and bound to an exact path/digest, then revalidated before protocol negotiation. Protocol/version negotiation completes before delegated capability or secret-handle transfer. Shadowed or duplicate provider candidates fail closed.

Workspace access requires an explicit bounded root. Canonical paths and symlinks are revalidated before mutation; filesystem-root, whole-home, traversal and symlink escape are denied. Host-resolved paths are not carried into a remote execution substrate; the target-side path is re-derived there.

Mutations use:

```text
read current state
-> proposed diff
-> authorization/human gate
-> revalidate path and base state
-> atomic apply
-> verify post-state
```

Apply-then-diff ordering is not conforming.

Secrets remain under the existing FA3 secrets boundary. Raw private-key or `nsec` handoff is denied by default. The wrapper admits bounded leased/scoped secret handles only after protocol negotiation and only within the authorized capability scope.

External execution is typed, `shell=false`, bounded by command size, timeout and output limits, and requires process-tree cancellation. Provider stdout/stderr/results are hostile input and must be bounded, validated and redacted before use.

Tenant/community scope is server-owned and derived before authorization/handling. Client override is denied. Intentional termination is final; abnormal restart is a separate policy decision.

## Evidence and promotion

Run the reference/security gate with:

```bash
./bin/fa3-buzz-runtime-admission-gate
```

The CI regression suite uses a synthetic provider fixture and cannot claim current-host production conformance.

Current canonical state:

```text
runtime admission: NOT_ADMITTED_PENDING_CURRENT_HOST
current-host production evidence: NOT_CLAIMED
raw buzz-dev-mcp direct host-tool provider: DENIED
global promotion impact while Buzz is disabled: NONE
```

A later runtime promotion requires a real current-host E2E receipt at `evidence/receipts/buzz-runtime-current-host.json`. CI reference evidence alone is insufficient.
