# FA3 Shared Execution Security

This shared, non-authoritative layer hardens effectful agent/tool execution. It consumes existing FA3 authorization, MCP/tool mediation, HRB resource leases, Model Router routes, Secret Broker references and Evidence Authority validation; it creates none of those authorities.

## OpenShell donor boundary

NVIDIA/OpenShell is used as canonical architecture-pattern donor `FA3-DONOR-NVIDIA-OPENSHELL-001`. Selected patterns include bounded policy proving, executable identity/digest binding, deny-by-default filesystem/process/network enforcement, endpoint-bound credential projection, MCP L7 inspection, fail-closed enforcement loss and structured security events.

No OpenShell source is copied. OpenShell is not a required runtime dependency, gateway, broker, scheduler, model router, secret authority, resource authority or evidence authority.

## Core rule

`effective_execution_policy ⊆ authorized_policy_boundary`.

Policy proof states are `PROVED`, `DENIED` and `UNPROVEN`. Where proof is mandatory, only `PROVED` may execute.

## Current Host

Static materialization does not claim runtime PASS. The existing Runtime Isolation / Agent Sandbox Current Host surface must be physically requalified for filesystem/process/network denial, executable digest swap, stale policy/lease handling, credential exfiltration denial, MCP bypass denial, enforcer loss, restart stale-token denial and rollback. CPU-only remains mandatory; accelerator proof is conditional and stays behind HRB and Hardware Safety.
