# FA3 Language Gateway / Language Bridge current-host evidence

## Purpose

This runbook proves a deliberately narrow current-host fact: an authenticated loopback LiteLLM gateway and the FA3 Language Bridge can execute real bidirectional Primary ↔ Secondary mediation on the actual `fa3-current-host` machine while preserving canonical protected tokens and producing attributable evidence.

A PASS at this layer is **not** a translation-quality promotion and is **not** a global FA3 production-promotion receipt.

## Preconditions

The current host must provide:

- a running LiteLLM gateway on a loopback origin, normally `http://127.0.0.1:4000`;
- an admitted logical local model alias exposed by `/v1/models`;
- a LiteLLM credential injected by the existing FA3 secret authority, either:
  - `FA3_LITELLM_MASTER_KEY_FILE` pointing to a non-group/world-readable file; or
  - `FA3_LITELLM_MASTER_KEY` in the runner environment;
- one harmless UTF-8 conformance sample file in the configured Primary language;
- one harmless UTF-8 conformance sample file in the distinct Secondary language.

Do not use confidential or secret material as a conformance sample. The collector classifies this test route as `PUBLIC` and records only sample/output hashes and lengths, not raw sample text.

## Manual execution

```bash
export FA3_LITELLM_MASTER_KEY_FILE=/run/credentials/fa3-litellm-master-key

bash bin/fa3-language-gateway-current-host.sh \
  --primary-language hu-HU \
  --secondary-language en-US \
  --primary-sample-file /var/lib/fa3/language-evidence/hu-HU.txt \
  --secondary-sample-file /var/lib/fa3/language-evidence/en-US.txt \
  --model-alias fa3-local-primary \
  --gateway-url http://127.0.0.1:4000
```

The language values above are examples only. The collector accepts any valid, distinct BCP47 Primary/Secondary pair; Hungarian and English are not globally hardcoded user languages.

The runner first collects evidence and then invokes:

```bash
./bin/fa3-enforce language-gateway-current-host
```

## GitHub Actions execution

Use workflow **FA3 Language Gateway Current-Host E2E**. It is `workflow_dispatch` only and requires the self-hosted labels:

```text
[self-hosted, linux, x64, fa3-current-host]
```

Inputs select the two system languages, logical LiteLLM model alias, loopback gateway origin and the two current-host sample-file paths. A credential-file path can be supplied, otherwise the runner environment must already provide one of the approved credential variables.

No credential value is passed as a workflow input or emitted into evidence.

## Evidence artifacts

Successful collection writes:

- `evidence/receipts/language-gateway-current-host.json`
- `evidence/runtime/language-gateway-current-host/execution.json`
- `reports/language-gateway-current-host-gate-report.json`

The gate verifies:

- real current-host execution;
- `fa3-current-host` runner class;
- authenticated loopback LiteLLM;
- `/v1/models` availability of the requested logical alias;
- exact Primary → Secondary and Secondary → Primary routes;
- local mediated Bridge route;
- protected-token round-trip;
- semantic-validation PASS;
- no authority expansion by mediation;
- collector and LiteLLM baseline config digests;
- runtime-evidence digest;
- absence of raw credentials and raw sample content in the execution evidence.

## Evidence level and limits

The receipt level is:

```text
CURRENT_HOST_GATEWAY_BRIDGE_E2E_PASS
```

It proves only real LiteLLM/Bridge transport and policy conformance on the collecting host. The validator deliberately uses the same selected gateway model, so it is not independent and the receipt records that limitation.

The receipt MUST keep all of the following false:

- `production_promotion_claim`
- `translation_quality_claim`
- underlying-backend production-admission claim
- HRB backend-admission proof
- Model Registry backend-admission proof
- global FA3 production-promotion proof

A production promotion still requires separate evidence for the selected backend's Model Registry admission, HRB admission when accelerated, independent semantic validation or approved equivalent, locale-specific quality, and the existing FA3 Acceptance/Promotion authorities.

## Fail-closed rules

Collection fails if the gateway is not loopback-scoped, authentication is unavailable, the logical model alias is absent, either system language/sample is missing, the languages are equal, protected tokens change, semantic validation does not return exact PASS, or any LiteLLM response omits executed model identity.

The current-host gate also rejects hand-built fixture receipts unless explicitly invoked with the test-only `--allow-fixture` switch. That switch is only for unit tests and never produces production evidence.
