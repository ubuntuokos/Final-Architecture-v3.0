# FA3 native System One Model Router admission

This adds a **conditional native protocol path**, not a second model router or a new FA3 authority. The normal service still requires its four mandatory local chat routes; `fa3-decision-system-one` is optional and stays absent unless a real provider is admitted.

## Execution path

`FA3 Decision Fabric BOUNDED_ACTION -> NativeRouterTransport -> central Model Router selection receipt -> authenticated LiteLLM pass-through -> admitted loopback native bridge -> explicitly admitted TypeSafe/OpenRouter upstream -> native probability distributions -> Decision Fabric confidence gate -> existing authorization authority`.

The provider-specific protocol bridge is a data-plane adapter, not a routing authority. The operator chooses a single approved upstream bridge at deployment. The central Model Router intersects the live `/models` catalogue with the explicit primary-model designation and chooses one allowed model; the bridge rejects any unselected model. There is no dynamic fallback to another native provider, external service or chat model. No direct model requests originate from FA3 applications.

The upstream reference is `HarnessRouter/SystemOneHarness@ab8e8f08b4a6268c0633a474423d556599ee06a4` (Apache-2.0). The FA3 implementation uses the documented native decision wire but does not vendor upstream source.

## Admission state

<escape>**Code and CI alone are not live provider admission.**</escape> The native provider record remains `RUNTIME_ADMISSION_PENDING_LIVE_PROVIDER_AND_SECRET_BROKER` until two *separate physical* receipts exist:

1. `fa3.system-one-native-current-host-receipt.v1`: the exact still-running loopback bridge, Secret Broker reference plus projected credentials, negative Bearer checks, live native model catalogue and one actual upstream probability-bearing response.
2. `fa3.system-one-router-e2e-current-host.v1`: the authenticated LiteLLM pass-through rejects both absent and invalid client credentials and transparently returns a second real native decision. It is bound to the exact runtime selection receipt, provider admission hash and repository HEAD.

The second gate is necessary because LiteLLM pass-through authentication can differ across deployed LiteLLM versions and editions. The presence of `auth: true` in a YAML file is not proof that that particular running proxy enforces it.

## Hardware Audit

All control and adapter code runs on CPU with no CUDA/ROCm/oneAPI/NPU dependency. The backend is a *vendor-neutral runtime interface* with cardinality 0..N accelerators managed only by HRB; the host-native bridge itself must show accelerator visibility blocked for its process lifetime. No KDE/Wayland/X11 dependency exists. No FA3 service may move or reserve AdGuardHome's port. The bridge defaults to a dynamically assigned loopback port; choose an available LiteLLM router port explicitly.

## Secret handling

The bridge accepts only systemd `CREDENTIALS_DIRECTORY` projected files named `fa3-system-one-upstream` and `fa3-system-one-bridge-token`. Both must be 0400/0600 regular files and remain outside the repository. The central Router obtains only the bridge token through its conditional `LoadCredential`, and its existing master credential remains independently protected. No credential, bearer value, request body or upstream error message is recorded in a canonical file or evidence receipt. Secret Broker is the only secret authority.

External egress is a single explicitly selected upstream, fixed in the bridge's code allowlist. It uses validated HTTPS, no configured HTTP proxy and no redirects; the deployment must additionally admit and constrain its network egress. A provider upstream that lacks the documented live catalogue fails closed instead of using a hard-coded model id.

## Live operator sequence

The following is **an operator runbook, not a claim of execution on the user's workstation**. An authorized operator must first approve the exact allowed native model ids, based on the chosen upstream's *live* catalogue, in a private designation JSON using schema `fa3.system-one-model-designation.v1`. It requires `result=PASS`, `router_authority=FA3-AUTH-MODEL-ROUTER-001`, `provider_id=FA3-PROVIDER-SYSTEM-ONE-NATIVE-001`, `logical_route=fa3-decision-system-one`, `approved_by_primary_model=true`, `upstream=openrouter` or `typesafe`, and nonempty `approved_models`; `served_model_aliases` permits explicitly reviewed canonical version ids. Do not write fictional approval to satisfy this schema.

Start the native bridge in its own restricted systemd scope with transient Secret Broker `LoadCredential` inputs for both named files, `FA3_SYSTEM_ONE_NATIVE_ENABLE=1`, empty `CUDA_VISIBLE_DEVICES`, `ROCR_VISIBLE_DEVICES` and `ZE_AFFINITY_MASK`, and an explicit private designation. For a dynamic port:

```bash
python3 src/fa3_model_router_system_one_native_bridge.py \
  --upstream openrouter --designation /run/fa3/system-one/designation.json \
  --designation-approval /run/fa3/system-one/model-approval.json --port 0
```

The bridge prints the dynamically assigned `http://127.0.0.1:<port>/v1` base. Obtain the real running PID of that process. In a separate scoped transient unit with its own authorized Secret Broker credential projection, create the provider admission receipt and append its descriptor to a registry containing the *already admitted* chat runtimes:

```bash
FA3_SYSTEM_ONE_NATIVE_ENABLE=1 \
python3 src/fa3_model_router_system_one_admit.py \
  --designation /run/fa3/system-one/designation.json \
  --designation-approval /run/fa3/system-one/model-approval.json \
  --bridge-api-base "http://127.0.0.1:<port>/v1" \
  --bridge-pid "<actual-pid>" \
  --output /run/fa3/system-one/native-admission.json \
  --runtime-registry /run/fa3/model-router/admitted-chat-providers.json \
  --runtime-output /run/fa3/system-one/providers.json
```

Only if that gate emits real PASS may the central Router be installed with the generated registry and the *broker-projected* native bridge credential file:

```bash
bin/fa3-model-router-install \
  --providers /run/fa3/system-one/providers.json \
  --credential-file /run/fa3/model-router/router-master.cred \
  --system-one-bridge-credential-file /run/fa3/system-one/bridge-token.cred \
  --port "<available-router-port>" --start
```

Once LiteLLM is active, perform the independent live pass-through auth/probability test before admitting the client:

```bash
FA3_SYSTEM_ONE_LIVE_ROUTER_ENABLE=1 \
python3 src/fa3_model_router_system_one_live_gate.py \
  --selection /run/user/"$(id -u)"/fa3-model-router/selection.json \
  --native-admission /run/fa3/system-one/native-admission.json \
  --router-origin "http://127.0.0.1:<router-port>" \
  --output /run/fa3/system-one/router-e2e.json
```

The E2E gate also needs the existing Secret Broker-projected `FA3_MODEL_ROUTER_MASTER_KEY` in its authorized transient environment. A client may use `SystemOneDecisionProvider` without injected test transport only after both `FA3_SYSTEM_ONE_ENABLE=1` and `FA3_SYSTEM_ONE_LIVE_ROUTER_ENABLE=1`, and with `FA3_MODEL_ROUTER_SELECTION_RECEIPT`, `FA3_MODEL_ROUTER_ORIGIN`, `FA3_MODEL_ROUTER_MASTER_KEY` and `FA3_SYSTEM_ONE_NATIVE_E2E_RECEIPT` scoped to that client's authorization. The E2E evidence must be from the current repository HEAD and younger than 24 hours.

## Fail-closed behavior

Missing provider credential, missing/expired designation, unsupported native catalogue, provider redirects, unknown model, missing or stale provider process, invalid evidence, LiteLLM auth bypass, out-of-range/missing probability, changed generated config, mismatch in receipt hash, or downstream model disagreement all fail the scoped action without execution or fallback. The approval, native provider, Router, HRB and tool-execution authorities remain separate. A passing native bridge admission does **not** imply global FA3 production promotion.

## Exact authenticated primary-model designation

Before the bridge can start or any native provider is admitted, the existing FA3 Trust PKI and Security Governance system must verify a protected `fa3.authenticated-approval-receipt.v2` using receipt type `MODEL_ROUTER_PRIMARY_MODEL_DESIGNATION` and the specifically authorized role `PRIMARY_MODEL_DESIGNATOR`. The Security Governance-signed role grant must authorize this receipt type with the dedicated `FA3_MODEL_ROUTER_MODEL_DESIGNATION` scope (distinct from release acceptance). The existing authenticated-approval verifier defaults to its unchanged release-acceptance scope for all other consumers. The signed receipt payload must bind `model_designation_sha256` (SHA-256 of the protected JSON), `provider_id`, `logical_route`, `upstream` and the exact `approved_models` list. The receipt's `source_commit` must match the running repository's exact HEAD. The normal primary-model approval decision remains a prerequisite; a signed file is not a substitute for an authorized decision. Neither credentials nor specimen signatures are put in Git. An operator must provision the real Security Governance role grant and model-designator signing identity before physical admission; CI mocks are reference tests only. On code updates the designation must be reapproved for the exact deployment commit. This adds no new FA3 authority and cannot be bypassed by a self-reported boolean.

The TypeSafe catalogue adapter reads the officially documented `models[].name`; the OpenRouter adapter reads `data[].id`. Wrong provider-specific catalogue shapes fail closed. CPU-only proof requires exactly one *empty* entry for each mask, an exact bridge process command and matching approved designation. Environment masks alone do not prove cgroup device isolation: the deployment still needs HRB-admitted restricted systemd execution with accelerator devices inaccessible, verified as separate current-host evidence. The LiteLLM authentication/probability E2E gate must be rerun for each deployed proxy version or configuration change; static YAML and these CI fixtures are not physical evidence.
