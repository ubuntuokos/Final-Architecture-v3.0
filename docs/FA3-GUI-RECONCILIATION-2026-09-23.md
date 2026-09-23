# FA3 GUI reconciliation — final plan (2026-09-23)

## Decision

The FA3 Control Center remains the native Qt/QML projection and intent surface. The reconciliation incorporates the post-baseline Decision Fabric/Jev and Agent Native/UAF architecture without creating a new authority, capability, model-routing layer, tool boundary, resource broker, evidence authority or provider runtime.

Capability count remains **143** and architectural-authority delta remains **0**.

## Materialized now

1. **Stable semantic routing** — user-facing navigation, search and shortcuts resolve semantic route IDs; StackLayout indices are implementation detail.
2. **Semantic navigation groups** — Home, Create, Agents, Models & Data, Decision & Context, Integrations, Governance and System.
3. **Agent Action Center** — reads canonical `canonical/actions/*.json` UAF contracts. It exposes mutating/read-only semantics, approval, HRB and DecisionReceipt requirements. The only mutation available from this GUI is a local `DRAFT_NOT_SUBMITTED` intent.
4. **Decision & Context** — Decision Fabric, Decision Inspector, Context Inspector and Project Radar are grouped together while their runtime/authority boundaries stay separate.
5. **Canonical application discovery** — GUI search uses `FA3-AI-STUDIO-APP-CATALOG-001` through `fa3AppCatalog`; the stale independent application list is removed.
6. **Work Management repair** — previously unhandled GUI signals now refresh read projections or create draft intent only. Provider events never authorize state transitions.
7. **Accelerator Guard repair** — current GPU/NPU device discovery is projected through the existing device model. Telemetry/conflict state is never fabricated. Any future explicit decision remains draft intent until the existing guard/policy/HRB chain accepts it.
8. **Desktop portability wording** — Wayland remains primary, X11 remains supported; KDE Plasma is a Tier-1 reference rather than a core dependency.
9. **Fail-closed regression coverage** — the GUI gate now checks the reconciliation decision, stable surface registry, Agent Native surface, Decision Fabric grouping, canonical app catalog search, dead-signal repairs and portability wording.

## Canonical interaction model

`user intent → surface → typed UAF action contract → deterministic eligibility → optional bounded Decision Fabric advice → authorization/approval → provider compatibility → HRB/Secret Broker when required → execution → output validation → Journal/Evidence`

Decision Fabric is advisory only. It cannot expand an eligible candidate set, authorize an action, become Model Router authority, invoke tools directly or allocate host resources.

Agent Native is expressed through UAF typed actions. No direct GUI/agent → provider production bypass is permitted.

## Hardware Audit compliance

The GUI is vendor-neutral. Accelerator inventory is dynamic **0..N**. No NVIDIA/AMD/Intel vendor, GPU ordinal, SKU, CUDA/ROCm API or local current-host observation becomes a global GUI or architecture requirement. Hardware observations are read projections; HRB remains the resource admission/placement/lease authority.

## Required closure before GUI runtime promotion

The structural reconciliation has **reference PASS** (static/unit + Qt6 reference build), but it does **not** promote the GUI runtime. Runtime promotion remains fail-closed until all of the following are attributable to a current-host visual/runtime receipt:

- GUI static regression gate PASS;
- Qt reference build PASS;
- UI Component Fabric closure for shared design tokens, light/dark/system behavior, keyboard/focus accessibility, reduced-motion handling and visual-regression coverage;
- real current-host interactive smoke on Wayland or supported X11;
- current-host visual/navigation receipt covering the semantic groups and Agent Action Center;
- no fabricated telemetry, CONNECTED or PASS state.

The existing `FA3-GUI-RUNTIME-CONFORMANCE-001` therefore remains `PENDING_CURRENT_HOST`.


## Reference validation result

Reference validation is **PASS** for tested head `79a71114a3d9c5a83fe8431039c3862e01d8136d`:

- FA3 GUI Gate run **35902144865**;
- static-contract job **107320747988**: PASS;
- Qt6 reference-build job **107320748620**: PASS.

This reference PASS is deliberately not a current-host Wayland/X11 visual/runtime PASS.


## Installer reconciliation

The user-local installer source-contract preflight was migrated from the removed first-level `Keresés` navigation marker and brittle navigation assumptions to the semantic route contract. It now requires the stable route table, Agent Action Center, Decision & Context routes, Work Management, Accelerator Guard, FA3 OS, the global search toolbar and the Generic Linux / Wayland-primary / X11-supported portability label. It also fails closed if `NavButton` regresses to direct `pageIndex` coupling.
