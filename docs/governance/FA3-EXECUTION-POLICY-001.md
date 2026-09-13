# FA3-EXECUTION-POLICY-001

Status: CANONICAL_CANDIDATE

## Execution Fabric

FA3 execution targets are governed through a common policy model:

- LOCAL
- LAN
- CLUSTER
- CLOUD
- HYBRID

Host-specific mechanisms such as systemd, cgroups v2, NUMA placement and local accelerator allocation are enforcement projections, not the definition of FA3 execution governance.

## Lease model

FA3 SHALL treat execution authority as explicit leases. The common family includes:

- CPUExecutionLease
- AcceleratorExecutionLease
- RemoteExecutionLease
- ExternalServiceExecutionLease

An ExternalServiceExecutionLease SHOULD constrain, when applicable:

- provider
- operation/capability
- request count
- maximum cost
- TTL
- egress policy
- credential scope

## Risk-based human control

FA3 SHALL use risk-based Human-in-the-Loop handling:

- LOW: automatic execution allowed under policy;
- MEDIUM: automatic execution allowed with audit and rollback capability;
- HIGH: proposal plus human approval required;
- CRITICAL: execution forbidden.

Universal human approval is not an FA3 requirement.
