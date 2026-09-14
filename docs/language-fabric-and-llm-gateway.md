# FA3 Language Fabric and LLM Gateway

This document materializes the canonical multilingual and LLM-routing boundary defined by:

- `FA3-LANGUAGE-POLICY-001`
- `FA3-LANGUAGE-FABRIC-001`
- `FA3-LANGUAGE-ADMISSION-001`
- `FA3-LLM-GATEWAY-001`

All four are P0/MUST and add **zero** capabilities and **zero** architectural authorities.

## Installation language contract

Every FA3 installation MUST have exactly:

1. one primary language;
2. one distinct secondary language;
3. zero or more optional additional languages.

Primary and secondary use BCP47 locale identifiers. Installation or migration state is incomplete while either is missing or they are equal.

No specific language is globally mandatory. Hungarian (`hu-HU`) is one supported language among many. Hungarian-specific models, adapters, translation assets and locale-quality gates become required only when `hu-HU` is selected as the primary or secondary system language. The requirement is **validated Hungarian operability**, not the presence of a Hungarian-specific LLM.

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

`FA3-LANGUAGE-FABRIC-001` owns provider-neutral mediation logic, not architectural authority. It covers language detection, translation/adaptation, transliteration/locale handling, terminology preservation, structured-data/code protection and STT/TTS language selection.

The original input remains authoritative. Translation is a derived projection with provenance. Language requirements cannot override privacy or provider policy. `SECRET` data is never externally translated.

The user-facing Translator / Language Control remains the GUI projection of this backend boundary through `FA3-GUI-LANGUAGE-CONTROL-001` and `FA3-LANGUAGE-BRIDGE-001`.

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

The Language Control page now contains two distinct layers:

- **System languages:** mandatory Primary + distinct Secondary, optional Additional languages;
- **Request language:** per-request input/output and mediation preferences.

The GUI remains a projection/intent surface. `PENDING_BACKEND`, `UNKNOWN`, missing system-language configuration or absent runtime evidence never means PASS.

## Enforcement

Run:

```bash
./bin/fa3-enforce language-gateway
python3 -m unittest tests.test_language_gateway_gate -v
```

The gate proves static/reference conformance only. Real LiteLLM service identity/authentication, Vault injection, Model Registry materialization, HRB-integrated local inference and Language Fabric translation E2E require current-host evidence before production promotion.
