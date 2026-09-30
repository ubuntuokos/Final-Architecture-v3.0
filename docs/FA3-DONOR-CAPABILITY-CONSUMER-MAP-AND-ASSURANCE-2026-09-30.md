# FA3 Donor → Capability → Consumer Map and Assurance Fabric — final materialized plan

Status: **owner-approved; metadata/contracts/static gates materialized; runtime promotion not claimed**.

The existing application/donor graph is extended rather than replaced. Donor identity remains exclusively in the Donor & Reference Registry. Actual donor use remains one edge list in `FA3-APPLICATION-DONOR-LINKS-001`; capability/application/shared-module/authority/GUI/test/current-host views are derived from that list.

Capability IDs are never guessed from names or handwritten into a usage edge. They are resolved from referenced canonical profile/contract `capability_bindings`. Unresolved bindings remain explicit and `CAPABILITY_PATTERN` fails closed.

The assurance composition is: Provider Intelligence → Provider Evidence Dossier → protocol/model-identity assurance → existing provider admission → deterministic eligibility → bounded advisory ranking → Model Router stage route → explicit bounded fallback/exhaustion → Gateway identity/Layer Guard/capability visibility/quota/security/protocol enforcement → execution/evidence → update impact.

Existing authorities remain unchanged: Model Router, Central MCP Gateway, HRB, Secret Broker, Security/UAF, Evidence and Temporal. Chat-analyzed sources without explicit owner `donornak` marking remain outside the canonical donor registry and cannot be adopted by this change.

Capability baseline **175**; new capabilities **0**; new architectural authorities **0**.
