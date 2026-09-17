# FA3 Development Mode + Update Fabric

Status: **P0 / MUST — canonical materialization**

This materialization keeps the FA3 production domain fail-closed while providing a bounded development trust domain and a unified update/security-maintenance policy. It adds no capability and no architectural authority; the canonical capability count remains **143**.

## Canonical profiles

- `FA3-DEV-MODE-001` — separate mutable development execution domain.
- `FA3-UPDATE-FABRIC-001` — unified update discovery, compatibility, staging, health and rollback contract.
- `FA3-SECURITY-UPDATE-001` — background security maintenance policy.
- `FA3-UPDATE-RESTART-001` — workload-aware restart/reboot coordination.
- `FA3-DEV-UPDATE-RUNTIME-CONFORMANCE-001` — current-host evidence boundary; current-host E2E remains pending until real host execution produces the required receipts.

## Development lifecycle

Production policy is never relaxed in place. Development is a separate trust domain.

```text
DEV EDIT
   -> deterministic Git-index SNAPSHOT
   -> immutable CANDIDATE FREEZE
   -> hosted STATIC validation
   -> trusted CURRENT-HOST validation
   -> PROMOTION_READY
   -> controlled canonical PROMOTION
```

`DEV_*` states are never production PASS evidence. A policy relaxation sets sticky taint; promotion creates new authoritative evidence rather than rewriting a development receipt.

### Enter development mode

```bash
./bin/fa3-dev enter
./bin/fa3-dev status
```

`FA3_ENV=development` is only a runtime hint. The development session record is the local session identity. Development cannot write canonical or production-evidence paths and cannot receive production secrets automatically.

### Git hook bootstrap

```bash
./bin/fa3-init-hooks.sh
```

This configures repository-local:

```text
core.hooksPath=.githooks
```

The pre-commit hook snapshots the **full staged Git index**, not the working tree. Generated development evidence is non-authoritative. The hook is automation only: remote CI re-proves the boundary independently, so `git commit --no-verify` is not a promotion bypass.

### Manual snapshot / freeze

```bash
./bin/fa3-dev snapshot
./bin/fa3-dev verify-snapshot --source index
./bin/fa3-dev freeze
```

`freeze` creates host-local state under `state/promotion-candidates/`. It never updates canonical SSOT and never means production promotion.

## Update Fabric

There is deliberately **no blind Update All** operation.

Supported interaction model:

- Check All — discovery only.
- Update Selected.
- Update Recommended.
- Update Security.
- Update Component.
- Update Group.

Updates are dependency-aware bounded transactions with per-batch health and rollback boundaries. A failed batch blocks dependent batches.

### Update classes

- OS-managed — distribution/APT ownership (for example Kdenlive and other repository packages).
- FA3-managed — FA3 release/control-plane components.
- External provider — Git/GitHub Release/uv/AppImage/deb/binary/custom provider recipes.
- Model — separate model queue; large downloads are never implicit.
- Host-critical — kernel, NVIDIA driver, CUDA and equivalent host runtime changes.

Provider Python environments remain isolated. Updating one provider cannot mutate another provider's Python/PyTorch environment.

### Plan example

```json
{
  "components": [
    {"id":"kdenlive","class":"OS_MANAGED","security_update":false,"impact":"NORMAL"},
    {"id":"openssl-security","class":"OS_MANAGED","security_update":true,"impact":"QUICK"},
    {"id":"nvidia-driver-security","class":"HOST_CRITICAL","security_update":true,"impact":"HOST_CRITICAL"}
  ]
}
```

```bash
./bin/fa3-update plan --input update-input.json
```

Low-risk OS security updates may be classified for background installation. Host-critical changes are staged and require controlled activation.

## Security updates and restart UX

Background security maintenance is automatic where the policy classifies the update as low risk. It is never invisible after activation is required.

When restart or reboot is required, FA3 persists the state and presents these choices:

- `RESTART_NOW`
- `WHEN_IDLE_SAFE` — recommended default
- `SCHEDULE`
- `LATER`

A protected workload always wins over a scheduled or immediate automatic restart. The host is never silently rebooted.

Example policy-engine operations:

```bash
./bin/fa3-update require-restart --kind host --component kernel --active-workload render
./bin/fa3-update choose-restart WHEN_IDLE_SAFE --active-workload render
./bin/fa3-update restart-status
```

Service restart and host reboot are distinct states.

The Control Center includes `UpdateCenterPage.qml`, a backend-owned update/restart decision surface. It exposes Check All, selected/security update intents, persistent restart-required state, workload warnings and the four restart choices. It intentionally does not invent PASS, update safety or restart authority in QML.

## Network, secrets and MCP development boundary

Development defaults:

- unknown egress: `MOCK_OR_DENY`;
- production credential forwarding: `DENY`;
- direct agent writes: development playground/drafts only;
- Maker–Checker: deferred during iteration, mandatory after freeze;
- CPU accelerator fallback: permitted only with provenance;
- HRB lease: ephemeral auto lease;
- accelerator contention: delegated to `FA3-ACCEL-GUARD-001`, defaulting to user decision.

## CI and current-host promotion boundary

Hosted CI workflow:

```text
.github/workflows/fa3-dev-update-gate.yml
```

It uses read-only permissions, immutable Action SHAs, regenerates the deterministic checked-out-tree snapshot, executes the fail-closed boundary lock, canonical gate, regressions and existing FA3 static gate.

Trusted current-host probe:

```text
.github/workflows/fa3-dev-update-current-host.yml
```

It is `workflow_dispatch` only, runs only from `main`, and never executes untrusted PR code on the FA3 current host. The initial probe is deliberately non-mutating and keeps `CURRENT_HOST_E2E_PASS` and `GLOBAL_FA3_PROMOTION` as explicit non-claims.

Real promotion requires the current-host evidence listed by `FA3-DEV-UPDATE-RUNTIME-CONFORMANCE-001`, including filesystem boundary, HRB/ACCEL-GUARD integration, actual update behavior, protected-workload non-interruption, persistent notification, user-selected activation and rollback/health receipts.

## Enforcement

```bash
./bin/fa3-enforce dev-update
python3 bin/fa3-ci-lock-check.py
```

The remote lock check rejects canonical contamination by development state, tracked local promotion candidates, authoritative claims in development receipts, snapshot/tree mismatch, capability-count drift and policy changes that weaken the defined boundaries.
