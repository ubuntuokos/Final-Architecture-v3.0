# Covert Coder donor adoption — 2026-10-05

**Source:** https://github.com/AnonymousNomad/covert-coder  
**Canonical donor:** `FA3-DONOR-ANONYMOUSNOMAD-COVERT-CODER-001`  
**Status:** `ACCEPTED_REFERENCE`  
**Observed upstream:** `covert-production@81aff88b924db05c689dc734aa3e67605f4b18ce`  
**Observed root license:** Apache-2.0

## Adoption boundary

The owner explicitly marked the source `donornak` and approved direct application of the previously reviewed patterns. CFA3 adopts only independently expressed architecture patterns. No Covert Coder source code, package, runtime, model, provider, service, installer or port is imported or activated.

The upstream project describes itself as an Engineering Preview. Its profile-specific runtime qualification is therefore not generalized into CFA3 hardware, provider, release or Current Host claims.

## Materialized pattern deltas

1. **Model Router truth:** configured/selected identity is not proof of observed execution identity; observed provider/model/runtime identity requires a receipt; fallback transitions remain explicit and receipted.
2. **Typed governed execution:** model/agent/plugin output is an untrusted proposal and must pass parse, schema, capability, policy, approval where required, existing execution authority, independent verification and evidence.
3. **Plugin/extension trust:** presence or installation is not admission; admission is not readiness; external plugin/dependency/imported-artifact/model output remains untrusted by default.
4. **Evidence semantics:** IMPLEMENTED / AVAILABLE / CONFIGURED / AUTHENTICATED / QUALIFIED / AUTHORIZED / EXECUTED / VERIFIED / READY are distinct claims.
5. **Failure preservation:** a later green retry cannot erase or silently convert an earlier unexplained failure to PASS.

## Existing CFA3 authorities preserved

- Model routing: `FA3-AUTH-MODEL-ROUTER-001`
- Tool/action mediation: `FA3-AUTH-MCP-GATEWAY-001` / existing UAF
- Evidence: `FA3-AUTH-OBS-EVIDENCE-001`
- Durable workflow: Temporal through the existing Orchestration Workforce
- Host resources: `FA3-AUTH-HOST-RESOURCE-BROKER-001`
- Plugin/extension classification: `FA3-EXTENSION-BOUNDARY-001`

Capability baseline remains **175**. Capability delta and architectural-authority delta are both **0**. No physical Current Host PASS is claimed.

## Usage traceability

- `FA3-USAGE-COVERT-CODER-MODEL-ROUTER-001`
- `FA3-USAGE-COVERT-CODER-MCP-TYPED-EXECUTION-001`
- `FA3-USAGE-COVERT-CODER-EXTENSION-TRUST-001`
- `FA3-USAGE-COVERT-CODER-EVIDENCE-STATE-001`

Canonical donor-use decision: `FA3-DEC-COVERT-CODER-GOVERNED-EXECUTION-DONOR-USE-2026-10-05`.
