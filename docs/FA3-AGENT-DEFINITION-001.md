# FA3 Agent Definition Fabric

`FA3-AGENT-DEFINITION-001` is the provider-neutral child profile that separates **what an agent role means** from **which runtime/provider/model is allowed to execute work**.

## Canonical chain

```text
FA3-AGENT-EXEC-001
  -> FA3-AGENT-DEFINITION-001
      -> FA3-AGENT-DEFINITION-CONTRACTS-001
      -> FA3-AGENT-DEFINITION-REGISTRY-001
      -> FA3-AGENT-DEFINITION-GATESET-001
```

The layer adds no capability and no architectural authority. The canonical capability count remains 143.

## Definition semantics

A canonical role definition may contain human-readable role purpose, domains, competency intents, anti-capabilities, risk classification, human-gate policy and immutable source provenance.

It is **not**:

- a security identity;
- an authorization or capability grant;
- a tool permission;
- a model/provider assignment;
- a secret/resource grant;
- a Workforce specialist;
- a durable-workflow authority;
- current-host runtime evidence.

Definitions can decorate an already eligible Workforce specialist with task-scoped role context. They cannot expand the eligible specialist set, authorized AI participant set, override hard filters, select a runtime provider, select a model, or directly execute a provider.

## External source normalization

External agent/persona projects may be used as immutable reference sources. The source repository, commit and file/content identity are recorded. Upstream persona or runbook bodies are **not implicitly vendored**.

FA3-native derived role/template metadata may be materialized without copying upstream bodies. A future verbatim or substantial source-content import is a separate Distribution Compliance/content-admission event.

## Runtime boundary

Runtime selection remains outside this fabric:

- Workforce/provider eligibility remains with the existing orchestration/agent execution layer;
- model routing remains with `FA3-AUTH-MODEL-ROUTER-001`;
- tool execution remains behind UAF/Central MCP;
- host resource admission remains with HRB;
- authorization remains with Security Governance / human approval;
- evidence remains with `FA3-AUTH-OBS-EVIDENCE-001`.

A static Agent Definition PASS cannot promote a runtime or current-host state.

## Initial source projection

The first materialized source projection is `FA3-PROVIDER-AGENCY-AGENTS-001`, producing 12 FA3-native role definitions and 5 FA3-native coordination templates from immutable Agency Agents references while leaving the upstream bodies reference-only.
