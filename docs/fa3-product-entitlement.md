# FA3 Product Entitlement and Application Portfolio

FA3 separates **Operating Level** from **application entitlement**.

Operating Levels are MINIMAL, PERSONAL, PROFESSIONAL, STUDIO, BUSINESS and ENTERPRISE. They describe operating scope, collaboration, deployment and governance. They do not form application bundles.

User-facing applications remain individually selectable when `individually_entitleable=true`. A single application can therefore be used at a supported higher Operating Level up to Enterprise. The effective minimum is the maximum of the selected applications' minimum levels and requested operating features.

Required technical dependencies are resolved from `FA3-APPLICATION-DEPENDENCY-REGISTRY-001`. They are not user-facing application entitlements and cannot silently unlock another application.

Domain Packs are optional convenience bundles. They never become technical dependencies and individual selection remains valid.

The Product Entitlement layer is non-authoritative. Security, License & Rights, hardware/resource admission, Model Router, Evidence and other higher FA3 authorities remain fail-closed. Entitlement may restrict but cannot widen a higher-authority denial.

Portfolio state (FUTURE / PLANNED / IN_PROGRESS / EXISTING / RETIRED) is separate from the existing application provisioning lifecycle. CI scans materialized top-level `apps/` roots and fails closed when a new root has no portfolio classification or when a PLANNED record already has a materialized root.

Example:

```bash
PYTHONPATH=src python3 bin/fa3-product-entitlement \
  --select fa3.story-screenplay \
  --select fa3.render-manager
```

This resolves to PROFESSIONAL, includes the render application's technical 3D/render dependencies, and does **not** grant FA3 3D / DCC Studio.

For an Enterprise operating profile with only Story / Screenplay:

```bash
PYTHONPATH=src python3 bin/fa3-product-entitlement \
  --select fa3.story-screenplay \
  --requested-level ENTERPRISE
```

Static resolution is entitlement intent only; it does not execute applications, select providers, allocate hardware or claim Current Host PASS.
