# FA3 Application Portfolio and Entitlements

FA3 separates operating scale from application selection. The canonical Product Family taxonomy remains `FA3-PRODUCT-FAMILY-REGISTRY-001`; this materialization reuses it and does not create a second family or execution authority.

The product equation is `Operating Level + individual applications + automatic technical dependencies + optional Domain Pack/bundle + optional Engine/Provider/Capacity/Support`.

Higher Operating Levels add scale, deployment and governance scope, not automatic applications. One application may be used at Enterprise level. Required platform dependencies are included without granting unrelated applications. Story/Screenplay + Render Manager resolves to Professional and includes 3D/render core dependencies without granting 3D/DCC Studio.

Operational requirements are resolved independently from application count. For example, `LAN_DISTRIBUTED_EXECUTION` raises the minimum level to Studio without adding applications.

Portfolio state (`FUTURE / PLANNED / IN_PROGRESS / EXISTING / RETIRED`) is separate from `FA3-APP-LIFECYCLE-001` provisioning state (`AVAILABLE / READY_TO_INSTALL / INSTALLING / INSTALLED / INCOMPATIBLE / RECIPE_REQUIRED / ERROR`). New physical/internal applications fail closed without a Portfolio record. Incremental reconciliation checks application additions, state changes and removals; records are retired rather than silently removed.

Domain Packs and bundles are optional commercial/convenience groupings. Engine, Provider, Capacity and Support are also optional product axes. None override Security, License & Rights, HRB, Model Router, Engine Selection or Evidence authorities; product entitlement may restrict but never widen those authorities. External application entitlement never grants upstream rights. Runtime dependencies are not user-facing application entitlements, and a restricted donor may not be the sole required dependency.

Validation:

    bin/fa3-application-portfolio --check
    bin/fa3-application-portfolio --apps fa3.story-screenplay fa3.render-manager
    bin/fa3-application-portfolio --apps fa3.story-screenplay --requirement LAN_DISTRIBUTED_EXECUTION
    bin/fa3-application-portfolio --reconcile-from <base-commit>
    python3 src/fa3_product_entitlement_gate.py
    PYTHONPATH=. python3 -m unittest tests.test_application_portfolio -v

The Control Center **My FA3** page is a read-only projection of the canonical model; it is not an entitlement or execution authority.

Static/CI PASS does not create Current Host PASS, global runtime promotion, upstream rights, or release eligibility. The separate retroactive License & Rights audit remains authoritative for release eligibility.
