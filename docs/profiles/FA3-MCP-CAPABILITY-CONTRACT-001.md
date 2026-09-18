# FA3-MCP-CAPABILITY-CONTRACT-001 — Canonical MCP/Tool Capability Contract

- **Status:** SUBPROFILE / P0 / MUST
- **Parent:** `FA3-AUTH-MCP-GATEWAY-001`
- **Runtime projection:** `FA3-MCP-CURRENT-HOST-001`
- **Authority:** no independent authority; contract only

## 1. Objective

Normalize MCP tools, native application actions, plugins and controlled external adapters into one stable FA3 capability namespace so callers depend on capability semantics instead of provider-specific tool names or transports.

## 2. Canonical identifier

Every exposed capability MUST use a stable identifier:

```text
fa3.<domain>.<verb>[.<qualifier>]
```

Examples:

```text
fa3.image.edit
fa3.video.transcode
fa3.audio.transcribe
fa3.document.retrieve
fa3.browser.navigate
fa3.memory.retrieve
fa3.3d.mesh.generate
```

Provider names MUST NOT appear in the canonical capability identifier.

## 3. Required manifest fields

```yaml
capability_id: fa3.video.transcode
schema_version: 1
description: Transcode an admitted media asset
input_schema_ref: schemas/fa3.video.transcode.input.v1.json
output_schema_ref: schemas/fa3.video.transcode.output.v1.json
risk_class: R1
side_effects:
  filesystem: write
  network: none
  application_state: none
approval:
  mode: policy
resource:
  hrb_required: true
policy_ref: fa3.policy.video.transcode
provider_candidates:
  - provider_id: PROVIDER-KDENLIVE-001
    adapter_id: fa3.adapter.kdenlive
    priority: 100
transport_abstraction: true
```

## 4. Provider binding

Provider selection for a tool capability MUST be constrained to admitted candidates bound to that capability. Binding does not transfer authority to the provider.

A provider binding MUST expose:

- provider ID;
- adapter ID;
- admission state;
- health state;
- supported schema versions;
- transport type;
- resource profile reference;
- policy compatibility;
- evidence capability;
- deterministic priority or selection metadata.

## 5. Schema rules

- Inputs and outputs MUST be typed.
- Unknown mandatory fields MUST fail validation.
- Schema version changes that are not backward compatible MUST create a new schema version.
- Provider-native arguments MUST be translated behind the gateway adapter.
- Caller-facing schemas MUST remain provider-neutral.

## 6. Side effects

Every capability MUST declare expected side-effect classes:

```text
none
filesystem-read
filesystem-write
filesystem-destructive
network-read
network-write
application-read
application-write
process-exec
privileged-system-change
```

These declarations are inputs to policy enforcement; they are not themselves policy decisions.

## 7. Risk classes

| Risk | Meaning |
| --- | --- |
| R0 | non-mutating read/search/query |
| R1 | bounded non-destructive creation/export |
| R2 | mutable application/project state |
| R3 | destructive/overwrite/delete |
| R4 | privilege, security or system-boundary change |

Security Governance may impose stricter handling than this baseline.

## 8. Transport abstraction

The same canonical capability MAY be backed by:

- current MCP HTTP;
- managed stdio MCP;
- native IPC/application adapter;
- controlled REST/API adapter;
- other admitted FA3 tool transport.

The transport is provider metadata and MUST NOT alter the caller contract.

## 9. Compatibility rule

Legacy provider names MAY be retained as aliases for migration and evidence correlation, but callers SHOULD migrate to canonical `fa3.*` capability identifiers.

## 10. Non-goals

This profile does not define model routing, workflow orchestration, policy authorship, secret storage, resource scheduling or evidence retention.
