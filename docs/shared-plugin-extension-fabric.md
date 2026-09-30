# FA3 Shared Plugin & Extension Fabric

`FA3-SHARED-PLUGIN-EXTENSION-FABRIC-001` makes both **plugins** and **extensions** shared FA3 components.

A component is not owned by one application. It declares provided capabilities, required host capabilities and host contracts. FA3 derives candidate bindings for every compatible application. A binding is offered only when the application satisfies the host requirements and the component provides at least one capability the application does not already have. Candidate discovery never activates a component automatically.

## AI access

AI access is separately controllable at five levels: **global → application → module → component → capability**. `DISABLED` at any level blocks the AI path. The global disable is an absolute ceiling and cannot be overridden below it. External shared components default to AI disabled until explicitly enabled.

When enabled, a shared component may request a logical AI capability only through `FA3-AUTH-MODEL-ROUTER-001`. It cannot select a physical provider or model, call a provider directly, or silently fall back. Remote AI is separately gated by the global egress ceiling and existing policy. Hardware placement remains under HRB.

Where the feature is meaningful without AI, disabling AI must preserve the non-AI path.

## Admission and lifecycle

The lifecycle is: discovery → immutable source pin → license/security/dependency review → normalized shared manifest → capability/host-contract match → Software Coexistence → Hardware Safety Envelope → admission → dynamic binding projection → explicit per-application activation → runtime policy → audit → readmission on update → rollback.

The shared manifest does not grant authority. Existing Layer Guard, Orchestrator/Conductor boundaries, Security Governance, Secret Broker, Model Router, HRB and Evidence authorities remain unchanged.

## Retroactive application

The rule applies to existing, in-progress, planned and future FA3 applications. Existing plugin/extension integrations must be reconciled into the shared fabric where their semantics apply, without losing previously verified capability. The migration inventory starts with Skill Fabric, OpenFX, Browser Session extension and inference EP plugin families. A migration is not considered closed without regression, coexistence, safety and, where runtime promotion is claimed, physical current-host evidence.

## Current-host status

The architecture and executable policy are materialized, but production runtime promotion remains `PENDING_CURRENT_HOST`. A physical host must prove at least one admitted shared component can be enabled in two distinct eligible FA3 applications and that each AI toggle level blocks runtime requests as specified. Simulated or historical evidence cannot substitute for this proof.
