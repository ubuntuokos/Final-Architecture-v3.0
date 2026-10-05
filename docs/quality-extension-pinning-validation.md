# FA3 quality routing, extensions, pinning and layered validation

This materialization introduces four cross-cutting controls without changing the active capability count or creating a new architectural authority.

## Quality-aware voice routing

Voice requests are classified as BASIC, STANDARD, PRODUCTION or PREMIUM_CLONING. Routing requires language support, provider admission, quality eligibility and—when an accelerator is used—an HRB lease. MARKETING_PRODUCTION requires PRODUCTION quality and explicitly denies Piper. Piper remains available for BASIC/STANDARD CPU-oriented use cases. Silent quality downgrade is forbidden.

## Capability-neutral extensions

An extension is CAPABILITY_NEUTRAL only when it binds exclusively to existing capability IDs, creates zero capabilities and zero architectural authorities, and owns neither device-selection nor model-routing authority. A new user-visible capability, autonomous decision right, privileged-action owner or architectural authority forces CAPABILITY_CHANGING classification and release/capability/authority reconciliation. Unclassified extensions fail closed.

## Managed immutable upstream pinning

Immutable upstream identities are retained and centralized in `canonical/FA3-UPSTREAM-LOCK-REGISTRY-001.json`. Floating `main` is forbidden for runtime and promotion evidence. Updates follow discover -> immutable resolution -> security scan -> sandbox conformance -> current-host when required -> evidence -> review -> promotion.

## Layered audio validation

The provider-neutral audio preflight runs six layers before provider-specific execution: input integrity, media contract, resource budget, HRB admission, provenance, and output contract. Provider-specific gates remain mandatory; FastAPI/Pydantic schema validation is not treated as a replacement for canonical governance.
