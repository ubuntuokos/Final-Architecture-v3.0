# FA3 Agent Workload Runtime

Canonical profile: `FA3-AGENT-WORKLOAD-RUNTIME-001`

This profile materializes AX-derived Task, Workspace, Runner and lifecycle patterns as FA3-native execution contracts. It creates **no new architectural authority** and **no new capability**; the active capability count remains **143**, with the projection bound to existing `CAP-028` Managed External Agent Runtime.

## Authority boundary

```text
typed UAF action
  -> deterministic eligibility
  -> optional bounded Decision Fabric advisory
  -> Security / approval
  -> runner runtime admission
  -> HRB admission + fresh lease when execution/resume requires resources
  -> provider adapter
  -> execution
  -> Journal / Evidence
```

Temporal remains the sole global durable workflow lifecycle authority. The workload reconciler may reconcile only one workload's desired/actual lifecycle state. HRB remains the sole host resource admission, placement, reservation and lease authority. Model Router and Central MCP Gateway remain the sole model/provider/runtime routing and tool mediation boundaries.

## Work item versus workload

A Work Management work item is human/project work identity. An Agent Workload Task is an execution unit. A workload may carry a `work_item_ref`, but the two identities never collapse into one registry authority.

## Pause and suspend

`PAUSE` is non-durable and does not imply resource release. Durable suspension is explicitly one of `APPLICATION`, `PROCESS`, or `VM` checkpoint modes, and can only be claimed when the admitted runner proves that capability. Resume always requires fresh resource admission; an old HRB lease cannot be reactivated.

## Workspace and network

Production Git inputs use immutable commits. Skills enter through Skill Fabric. MCP capabilities enter through the Central MCP Gateway. A plain-language workspace goal cannot directly execute shell/package-manager commands; it must be converted to a typed UAF preparation plan.

Execution network envelopes are default-deny. Direct model-provider and direct external-tool bypasses are forbidden.

## Google AX

Pinned reference: `FA3-GOOGLE-AX-UPSTREAM-REFERENCE-2026-09-24` at commit `e6211f84a9e30dd309304167b8f1d51cbdaf8dab`.

AX remains optional and disabled by default. Its `ax.io/v1alpha1` resources are provider schemas, not canonical FA3 IR. AX `Model` does not become a Model Router authority and AX `Gateway` does not become an MCP/network authority.

The provider now has a pinned-schema manifest compiler (`src/fa3_google_ax_provider.py`) for the subset that AX can represent without weakening FA3 invariants. It emits only upstream-valid `Task`, `Workspace` and `Gateway` objects, requires a digest-pinned runner image, keeps debug guest services off, emits no AX `Model`, and preserves HRB / Model Router / MCP Gateway references outside AX authority.

At pinned commit `e6211f84a9e30dd309304167b8f1d51cbdaf8dab`, AX `Workspace.spec.git` supports a floating `branch` but no immutable commit field. Therefore a FA3 workspace containing an immutable Git source is **not** downgraded to a branch: provider compilation fails closed with `AX_V1ALPHA1_IMMUTABLE_GIT_COMMIT_UNREPRESENTABLE`. AX-native MCP/Skill registry discovery is likewise not used to bypass Central MCP Gateway or Skill Fabric.

The custom-runner execution-plan compiler (`src/fa3_google_ax_custom_runner.py`) is now materialized. It preserves immutable Git semantics by performing HTTPS fetch-by-commit, detached checkout, and HEAD verification inside the runner plan; the Git host must be explicitly present in the default-deny network envelope. Skill and MCP workspace sources are not reinterpreted by the runner, so Skill Fabric and Central MCP Gateway remain the admission/mediation boundaries.\n\nThis is still **source/static materialization only**. No digest-pinned runner image has been built/evidenced, no cluster-apply adapter is admitted, and no scope-bound cluster E2E exists. Runtime activation therefore remains `PENDING_RUNNER_IMAGE_CLUSTER_APPLY_AND_CLUSTER_E2E`.

## Static closure versus runtime closure

The reference gate proves schema, authority, negative-regression and distribution boundaries only. It does not promote the native runner, Podman runner, Google AX provider, process checkpoints, VM checkpoints, or GUI runtime.

## ADK 2.x-derived execution semantics

The mandatory child profile `FA3-AGENT-RUNTIME-SEMANTICS-001` adds provider-neutral graph, budget, resume/retry, model-capability, tool-confirmation, agent-transfer, MCP normalization, session/event and artifact-boundary semantics derived from selected Google ADK 2.x patterns. The implementation is FA3-native; Google ADK is REFERENCE_ONLY and is not a runtime dependency.

The child gate `FA3-ADK2-DERIVED-AGENT-RUNTIME-GATESET-001` is invoked by the existing Agent Workload Runtime gate, so these semantics are globally enforced through the already-mandatory parent gate without creating a new authority or capability.
