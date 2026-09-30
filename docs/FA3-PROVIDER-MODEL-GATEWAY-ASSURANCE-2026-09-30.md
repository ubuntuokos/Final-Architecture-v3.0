# FA3 Provider, Model & Gateway Assurance Fabric

This profile composes existing FA3 authorities; it does not create a new gateway, router, secret store, resource broker, workflow engine or evidence authority.

Flow:

`Provider Intelligence → Evidence Dossier → protocol/model-identity assurance → provider admission → deterministic eligibility → bounded advisory ranking → Model Router stage route → explicit bounded fallback/exhaustion → Gateway enforcement → execution → evidence`.

Key invariants:
- Model Router remains sole model/provider routing authority.
- Central MCP Gateway remains the MCP/tool trust boundary.
- HRB remains sole host-resource authority.
- Secret Broker remains credential custody/projection authority.
- Decision Fabric cannot expand the eligible candidate set.
- fallback is explicit, bounded and exhausted to failure; silent provider/model substitution is forbidden.
- MCP discovery may hide capabilities not visible to the principal/application/task context.
- REST/OpenAPI→MCP is a projection adapter, not a new authority.
- Wasm is only an optional plugin execution backend under the existing Plugin & Extension Manager.
- chat-analyzed sources without explicit owner `donornak` registration are not adopted.

Capability baseline: **175**. Capability delta: **0**. Authority delta: **0**. Runtime promotion: **none**.
