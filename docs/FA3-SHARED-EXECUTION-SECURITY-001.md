# FA3 Shared Execution Security Fabric

`FA3-SHARED-EXECUTION-SECURITY-001` is a provider-neutral, non-authoritative shared enforcement contract below existing FA3 authorization and dispatch boundaries.

## Placement

```
Security Governance / Testőr
  -> UAF / Shared Tool & Action Mediation / Central MCP Gateway
  -> Shared Execution Security
  -> Agent Sandbox / admitted execution backend
  -> workload
```

It never grants capability, authorization, model/provider selection, host resources, secrets, workflow authority or evidence PASS.

## OpenShell reuse

NVIDIA OpenShell is used through the canonical usage edge
`FA3-USAGE-NVIDIA-OPENSHELL-EXECUTION-SECURITY-001` as an **architecture-pattern donor** for policy proving, executable identity/digest binding, deny-by-default filesystem/process/network enforcement, credential projection, MCP L7 inspection, fail-closed sandbox lifecycle and structured security events.

No OpenShell code is copied and OpenShell is not a required runtime dependency. An optional OpenShell backend would require a later independent runtime/dependency/current-host admission.

## Fail-closed rules

- effective execution policy may only equal or narrow the authorized boundary;
- `UNPROVEN` is not PASS when proof is required;
- executable digest/policy revision changes require revalidation;
- expired approval/resource/secret leases deny execution;
- silent security-assurance downgrade is forbidden;
- enforcer loss freezes or terminates the workload;
- raw secrets are not exposed when broker projection is available;
- direct MCP/model/provider bypass is forbidden.

## Current Host

Static materialization does not claim physical runtime proof. The existing Runtime Isolation / Agent Sandbox Current Host surface must be requalified for filesystem, process/syscall, network, executable identity, credential non-exposure, lease expiry, enforcer-loss and rollback behavior. CPU-only proof remains mandatory; accelerator proof is conditional and the display-GPU policy is unchanged.
