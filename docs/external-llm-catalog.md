# FA3 External LLM Provider Discovery

`FA3-EXTERNAL-LLM-CATALOG-001` is a provider-neutral discovery and capability-intelligence projection. It does not create a provider, routing authority, credential store, egress authority, entitlement authority, or production fallback.

## Boundary

The lifecycle is:

`external source -> pinned observation -> normalized runtime catalog -> deterministic validation -> separate provider admission -> explicit external-route policy -> live capability probe -> Model Router`.

The normalized catalog state machine is:

`DISCOVERED -> OBSERVED -> VERIFIED -> ADMITTED -> ENABLED`.

The source parser can emit only `DISCOVERED`. A free tier, an API base URL, an OpenAI-compatible claim, or a model count never advances admission state.

`FA3-AUTH-MODEL-ROUTER-001` remains the single model/provider/runtime routing authority. LiteLLM remains the data plane. Existing baseline routes stay `LOCAL_ONLY` with external fallback denied. External/cloud use requires a separately materialized explicit policy.

## FreeLLM reference

The first reference source is `open-free-llm-api/awesome-freellm-apis`, observed at commit `4a91e1d93a6df0753ade804f75b4e17fbad89886` on 2026-09-24. The observed upstream repository is MIT-licensed, but the observed commit is unsigned and the default branch is not protected. FA3 therefore treats it as attributed discovery input, never as a trust anchor.

The normalizer deliberately accepts a local Markdown snapshot. It does not perform an implicit network fetch:

```bash
python3 src/fa3_external_llm_catalog.py normalize \
  --input /path/to/pinned/README.md \
  --output ~/.local/share/fa3/external-llm-catalog/catalog.json \
  --source-commit 4a91e1d93a6df0753ade804f75b4e17fbad89886 \
  --observed-at 2026-09-24
```

The output records SHA-256 of the exact source bytes and is runtime/user state, not canonical provider policy.

Canonical/static conformance is also available through the permanent enforcement entrypoint:

```bash
./bin/fa3-enforce external-llm-catalog
```


## Credential and privacy boundary

Catalog files must not contain API-key, bearer-token, password or other credential values. A later admitted provider may reference an opaque credential handle only after the existing FA3 secrets boundary admits it.

Before an external provider can be runtime-eligible, FA3 requires a canonical provider identity, security/privacy admission, explicit external egress policy, a provider/remote admission receipt, any required opaque credential handle, and a live model/capability probe.

## Decision Fabric

Decision Fabric may advise ranking only over the exact deterministically admitted external-provider set for an explicitly external-enabled route. It may use cost class, remaining quota, latency, context, modality, privacy class, jurisdiction, rate limits, provider health, credential availability, model capability and current entitlement as advisory metadata. It cannot add candidates, admit a provider, grant egress, obtain credentials, lease resources, or override Model Router.

## GUI

The Control Center exposes **Provider Explorer** as a child view of **Models & Providers**. It is read-only discovery plus **DRAFT admission intent**. It has no direct provider-enable control and no credential-entry field. A draft still requires the normal FA3 admission path before any runtime effect.

## Evidence

The dedicated reference gate proves parser behavior, source pin semantics, credential-value exclusion, sequential state transitions, negative runtime-eligibility cases, Decision Fabric boundaries, Model Router boundaries and the GUI read-only/draft-intent contract. It does not prove current entitlement, live remote availability, valid credentials, accepted provider terms, egress authorization or production cloud routing.
