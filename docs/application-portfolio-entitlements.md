# FA3 Application Portfolio and Entitlements

FA3 separates operating scale from application selection. Higher operating levels add scale/governance, not automatic applications. Applications are individually entitleable by default; required platform dependencies are included without granting unrelated applications. Story/Screenplay + Render Manager resolves to Professional and includes 3D/render core dependencies without granting 3D/DCC Studio.

Domain packs are optional bundles only. Portfolio state (FUTURE / PLANNED / IN_PROGRESS / EXISTING / RETIRED) remains separate from FA3-APP-LIFECYCLE-001 provisioning state.

Validation:

    python3 src/fa3_application_portfolio.py --check
    python3 src/fa3_application_portfolio.py --apps fa3.story-screenplay fa3.render-manager
    PYTHONPATH=. python3 -m unittest tests.test_application_portfolio -v

Static materialization creates no Current Host PASS and no release-eligibility claim.
