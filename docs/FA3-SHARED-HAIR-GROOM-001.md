# FA3 Shared Hair, Groom & Strand Asset Fabric

## Status
Owner-approved static materialization. Capability baseline remains **175**. This change creates no new architectural authority and no runtime/provider/model admission.

## Purpose
`FA3-SHARED-HAIR-GROOM-001` is the shared cross-family semantic layer for hair, grooming and strand assets. It is consumed through application adapters instead of being a standalone application.

## Authority boundaries
- Geometry semantics remain with `FA3-3D-GEOM-001`.
- Final DCC scene/asset authority remains `FA3-DCC-RT3D-001`.
- Model/provider routing remains with Model Router.
- Device/resource placement remains with HRB.
- Engine selection remains outside this component.
- License/Rights, Security and Evidence remain existing authorities.
- Static materialization is not Current Host runtime promotion.

## Canonical Hair Asset
Representations: `STRANDS`, `GUIDES`, `CURVES`, `CARDS`, `HYBRID`.

Attachments: `SCALP`, `BEARD`, `MUSTACHE`, `EYEBROW`, `EYELASH`, `BODY_HAIR`, `CUSTOM_SURFACE`.

The asset keeps stable identity separate from revision and carries governed references to provenance and rights. Lossy representation conversion requires a fidelity receipt.

## Groom lifecycle
Supported static semantics include grow, cut, trim, comb, brush, transform, curl/straighten, density, clump/frizz, parting, region editing, guide editing and strands-to-cards projection. All edits use Preview → Apply → Undo/Redo with non-destructive history.

## AI policy
AI is optional per application/module/function. Disabling AI means no model launch, provider call or background AI service. Manual/procedural grooming remains available. No direct provider, model, engine or accelerator selection is allowed in the canonical request surface.

## Consumers
Primary consumers: FA3 Character Studio and Bforartists-hosted DCC workflows.
Creative/Media projections: FA3 Video Editor and image/photo editing via the existing application inventory.

## Donor serialization boundary
PR #644 has merged into published main. This materialization still does **not** modify the Donor & Reference Registry, create donor intake deltas, or create donor usage edges. The seven separately owner-marked Digital Salon / 3D hair sources remain a separate serialized intake and require a fresh live-slot check before registration.

## Current Host
This change is static metadata/contracts/mapping/validation only and claims `NO_RUNTIME_IMPACT`. Any executable worker, package/runtime dependency, provider/model activation, hardware execution, credential path or physical application binding escalates to mandatory physical Current Host positive/negative/rollback qualification.
