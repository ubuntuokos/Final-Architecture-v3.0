# FA3 Language Fabric and LLM Gateway

This document materializes the canonical multilingual and LLM-routing boundary defined by:

- `FA3-LANGUAGE-POLICY-001`
- `FA3-LANGUAGE-FABRIC-001`
- `FA3-LANGUAGE-ADMISSION-001`
- `FA3-LLM-GATEWAY-001`

All four are P0/MUST and add **zero** capabilities and **zero** architectural authorities. `FA3-LANGUAGE-BRIDGE-001` is their non-authoritative runtime mediation projection and becomes mandatory whenever mediation is required.

## Three separate language planes

FA3 MUST keep three language concepts separate:

1. **Canonical platform language** — immutable machine/protocol language: English (`en`).
2. **User interaction language** — selected Primary/Secondary/Additional languages and per-request language context.
3. **Model/application admission language** — evidence-backed `NATIVE`, `VALIDATED`, `BRIDGED`, `UNVERIFIED` or `UNSUPPORTED` capability.

The English canonical machine plane is **not** a requirement that English be a user's Primary or Secondary language. It exists to keep machine interfaces deterministic across localized installations.

The following identifiers/fields remain English and are not replaced by localized labels: capability IDs, command IDs, GUI action IDs, tool/function names, schema keys, protocol fields, event types, policy rules, error codes, audit/security fields, metric names, model-capability descriptor fields, application-manifest fields, executable gate IDs, test IDs, evidence fields and provenance fields. Human-readable labels/descriptions may be localized, but a localized projection is non-authoritative and cannot mutate the canonical payload.

## Installation language contract

Every FA3 installation MUST have exactly:

1. one primary language;
2. one distinct secondary language;
3. zero or more optional additional languages.

Primary and secondary use BCP47 locale identifiers. Installation or migration state is incomplete while either is missing or they are equal.

No specific **user** language is globally mandatory. Hungarian (`hu-HU`) is one supported language among many. Hungarian-specific models, adapters, translation assets and locale-quality gates become required only when `hu-HU` is selected as the primary or secondary system language. The requirement is **validated Hungarian operability**, not the presence of a Hungarian-specific LLM.

## Language context

Request mediation distinguishes:

- `user_language`: language of interaction with the user;
- `work_language`: language that best fits the selected admitted model/application;
- `output_language`: required result language;
- `source_language`: optional language of source material.

The work language may differ from the user/output language. This lets an internationally strong English-only application remain admissible when an FA3-approved Language Fabric route preserves semantics and policy.

## Capability classes

Language capability evidence uses only:

- `NATIVE`
- `VALIDATED`
- `BRIDGED`
- `UNVERIFIED`
- `UNSUPPORTED`

`NATIVE`, `VALIDATED` and `BRIDGED` can satisfy language operability when their evidence and policy scope match the request. Bridged support never rewrites or masquerades as native support.

## Language Fabric

`FA3-LANGUAGE-FABRIC-001` owns provider-neutral mediation logic, not architectural authority. It covers language detection, translation/adaptation, transliteration/locale handling, terminology preservation, structured-data/code protection, prompt/response adaptation and STT/TTS language selection.

The original input remains authoritative. Translation is a derived projection with provenance. Language requirements cannot override privacy or provider policy. `SECRET` data is never externally translated.

The user-facing Translator / Language Control remains the GUI projection of this backend boundary through `FA3-GUI-LANGUAGE-CONTROL-001` and `FA3-LANGUAGE-BRIDGE-001`.

## Language Bridge runtime contract

`FA3-LANGUAGE-BRIDGE-001` materializes the mediation path as an explicit pipeline rather than a generic translator. The canonical runtime projection contains:

1. language/locale detection with confidence;
2. data-class routing before provider selection;
3. versioned terminology/glossary projection;
4. protected-token and structured-content guarding;
5. model/application language-capability routing;
6. prompt adaptation without authority expansion;
7. provider-neutral text translation/adaptation;
8. speech mediation delegated to admitted STT/TTS profiles;
9. response adaptation to the requested output language;
10. semantic validation;
11. provenance/evidence emission.

Protected material includes code, identifiers, command/GUI action IDs, file paths, URLs, addresses, API/model/provider identifiers, hashes, structured keys and explicit glossary terms. Mutation or loss fails closed. A translation cannot grant tools, capabilities or permissions that the original request did not have.

Data classification is evaluated before any external translation route. `SECRET` is denied externally; `CONFIDENTIAL` requires explicit policy permission; `INTERNAL` and `PUBLIC` remain policy-gated. Language fallback never silently becomes model, provider or infrastructure fallback.

The executable provider-neutral reference core lives in `src/fa3_language_bridge.py`. It implements local-first provider selection, data-class admission, protected-token round-trip enforcement, critical/low-confidence semantic-validation requirements and attributable mediation receipts. Its built-in conformance deliberately uses deterministic mock translation and therefore makes **no translation-quality or current-host production claim**.

### LB acceptance gates

The Bridge is guarded by `LB-001` through `LB-012`:

- source language/detection confidence must be admitted;
- native and mediated capability remain distinct;
- original source remains authoritative and adaptations retain lineage;
- protected-token round-trip integrity is required;
- terminology revision and preservation are validated;
- prompt adaptation cannot broaden authorization;
- critical/low-confidence mediation requires semantic validation;
- data-class routing precedes provider selection and SECRET external translation is denied;
- fallback domains cannot silently cross;
- speech mediation delegates to existing STT/TTS authorities;
- evidence binds route, provider, languages, digests, terminology and validation outcomes;
- reference/documentation evidence cannot claim current-host production PASS.

Removing any required Bridge component or LB gate is an executable regression failure.

## LiteLLM gateway

LiteLLM is the reference implementation for `FA3-LLM-GATEWAY-001` and is used as a language-neutral, provider-neutral LLM API gateway.

LiteLLM may perform API normalization, gateway authentication/authorization, logical model aliasing, deployment routing, policy-equivalent fallback/retry, rate limiting, budget accounting and observability/guardrail integration.

LiteLLM MUST NOT become:

- the FA3 Model Registry;
- the model weight installer/store;
- the FA3 Vault or secret source of truth;
- the Host Resource Broker;
- the Language Fabric / translation authority;
- a general workflow orchestrator.

Blackhole is one LiteLLM client; it is not the universal front door for every FA3 AI workload.

## Local-first / remote-provider policy

Default state:

- local providers: enabled according to normal admission;
- external/paid providers: disabled;
- silent local-to-cloud fallback: forbidden.

External providers may be materialized only after an explicit system setting enables them and the provider allowlist, service authorization, privacy/data-export policy and request policy all permit their use. Language requirements never force cloud use.

Fallback domains remain separate:

1. language fallback / mediation;
2. model fallback;
3. provider fallback;
4. infrastructure/runtime fallback.

A failure in one domain cannot silently authorize movement into another policy domain.

## LiteLLM reference configuration

`deployment/litellm/config.yaml` intentionally contains only local OpenAI-compatible deployment aliases. Endpoint addresses and keys are injected at runtime. No plaintext master/backend key, global language blacklist or cloud provider is committed.

The Model Registry is expected to materialize the actual admitted model/deployment identity behind the logical aliases. HRB admission occurs before local accelerator execution; LiteLLM routing never substitutes for HRB placement or leasing.

## GUI semantics

The Language Control page contains two distinct layers:

- **System languages:** mandatory Primary + distinct Secondary, optional Additional languages;
- **Request language:** per-request input/output and mediation preferences.

The GUI remains a projection/intent surface. `PENDING_BACKEND`, `UNKNOWN`, missing system-language configuration or absent runtime evidence never means PASS. Localized GUI labels never replace canonical command/action identifiers.

## Enforcement

Run:

```bash
./bin/fa3-enforce language-gateway
python3 -m unittest \
  tests.test_canonical_language_gate \
  tests.test_language_gateway_gate \
  tests.test_language_bridge -v
./bin/fa3-enforce static
```

The `language-gateway` entrypoint first executes the **8-case canonical-English machine-language gate**, then the complete **37-case** language/gateway/Bridge reference contract, including the executable Bridge reference runtime. The global static command executes both fail-closed before the legacy static checks.

Real LiteLLM service identity/authentication, Vault injection, Model Registry materialization, HRB-integrated local inference and Language Fabric/Bridge translation E2E require current-host evidence before production promotion.
