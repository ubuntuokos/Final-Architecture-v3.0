# Final Architecture v3.0

Canonical governance and runtime-promotion enforcement for **FINAL ARCHITECTURE v3.0**.

## Permanent gates

- `canonical-regression / P0` validates the exact 143-capability catalog, v3.0.11 source-graph attestation, 36/36 reconciliation, geometry closure, and scope invariants.
- `promotion-safety / fail-closed` proves that runtime `PROMOTED` cannot be set until the current-host Evidence Registry and all 19 acceptance criteria are PASS.

Runtime evidence starts at `PENDING_CURRENT_HOST`; documentation alone never promotes the runtime.

## Commands

```bash
./bin/fa3-enforce static
./bin/fa3-enforce runtime
./bin/fa3-enforce acceptance
./bin/fa3-enforce promote
```

Read-only host evidence collection:

```bash
./evidence/collect-current-host.sh
```

The removed **Linux Recovery/Rebuild Projection** remains explicitly `OUT-OF-SCOPE`.


## Terax reference-provider enforcement

`FA3-PROVIDER-TERAX-001` is an optional terminal-first native Developer/ADE provider and security/interaction pattern source. It creates no new capability or architectural authority; the canonical capability count remains 143.

CI executes the immutable reference and all 17 Terax-derived invariants:

```bash
./bin/fa3-enforce --ci-only terax
PYTHONPATH=src python -m unittest discover -s tests -v
```

The five P0 implementation invariants are read-before-edit, diff-before-apply, typed authenticated local control, executable security regression evidence, and effectively zero runtime cost when disabled.

Current-host evidence is deliberately separate from CI. On the actual FA3 workstation, with Terax kept disabled/reference-only:

```bash
python3 evidence/collect-terax-current-host.py --state disabled-reference
./bin/fa3-enforce terax
```

The collector is read-only, performs no network access, and does not read credentials. A PASS proves the disabled Terax provider has zero observed process/RAM/VRAM/polling/background-inference cost on that collecting host. It does not by itself promote the full 143-capability runtime.

Reference evidence is pinned to Terax v0.8.6 / commit `1fdbc50e53b3ac53db3ba80057805a2d54258545`. The later local-control pattern is separately pinned to exact commit `e9b489c5d50cb9e654fc9a61f901c0eb9f341be3`; floating `main` is forbidden as promotion evidence.


## Kaneo optional-provider canonical enforcement

`FA3-PROVIDER-KANEO-001` registers `usekaneo/kaneo` strictly as an optional self-hosted work-management / human-agent coordination provider and architectural pattern source. It creates no new capability and no new architectural authority; the canonical capability count remains **143**.

Four Kaneo-derived rules are mandatory P0 canonical invariants and are executable in CI through `FA3-KANEO-GATESET-001`:

1. human and agent operations share the same authoritative authorization boundary;
2. equivalent API/MCP/SDK capability projections fail closed on surface drift;
3. changes cannot close until every declared applicable surface has PASS evidence;
4. security-relevant state that crosses replicas must be shared, expiring, atomically consumed, and replay-protected.

Run the gate directly with:

```bash
./bin/fa3-enforce kaneo
```

The provider runtime itself is **not** required for global FA3 promotion while Kaneo is disabled. The canonical rules remain mandatory regardless of whether the optional provider is deployed. Reference evidence is pinned to Kaneo `v2.22.0` / commit `4faa14858913801cfc62991cb326f35fe5fcae00`; floating `main` is forbidden as promotion evidence.


## Demucs optional-provider canonical enforcement

`FA3-PROVIDER-DEMUCS-001` registers `adefossez/demucs` strictly as an optional local audio source-separation / stem-decomposition provider, reference implementation and architectural pattern source under `FA3-AUDIO-SEPARATION-001`. The profile is a non-root `SUBPROFILE-OF FA3-AUDIO-001` projection over existing `CAP-017` and `CAP-066`; it creates no new capability and no new architectural authority, so the canonical capability count remains **143**.

The executable `FA3-DEMUCS-GATESET-001` enforces 18 audio-separation invariants plus two cross-cutting model-loading trust rules. In particular: unsupported/experimental stem handling is fail-closed; accelerator execution requires a Host Resource Broker lease; model variants, quantized weights, bags and separated stems are typed first-class artifacts with lineage; chunk/overlap/normalization/clipping policies are explicit; and safe model containers do not by themselves authorize execution.

Two global model-loading rules are canonicalized:

- `FA3-MODEL-LOAD-TRUST`: container safety is not execution authorization; provenance, admission, implementation identity and execution policy must also PASS.
- `FA3-MODEL-CLASS-ALLOWLIST`: external model metadata cannot select arbitrary local classes/modules; resolution must use an allowlisted registry implementation mapping.

Run directly with:

```bash
./bin/fa3-enforce demucs
```

The provider runtime is **not** required for global FA3 promotion while Demucs is disabled. Reference evidence is pinned to Demucs `v4.1.0` / commit `6a604bb002d12c4fbabb303ba64db40b5c5743f0`; floating `main` is forbidden as promotion evidence.


## FA3 generative-video canonical baseline

`FA3-VIDEO-001` is the P0/MUST provider-independent generative-video production profile over existing `CAP-016`, `CAP-123` and `CAP-126`. It creates **no new capability** and **no new architectural authority**; the canonical capability count remains **143**.

The baseline requires a provider-neutral `VideoGenerationIR`, typed multimodal references, cinematic/shot controls, temporal edit/extend/regenerate semantics, fail-closed licence/policy admission, provider capability discovery, local/remote/hybrid execution projection, AV/continuity QC and full provenance.

Initial provider registry roles:

- `FA3-PROVIDER-KLING-001`: optional cloud cinematic/multi-shot/high-resolution/agent-facing reference provider. Provider MCP/CLI access must remain behind the FA3 Central MCP/Capability Gateway.
- `FA3-PROVIDER-SEEDANCE-001`: optional primary reference provider for large multimodal reference bundles, temporal editing, longer sequences and DCC/clay-reference projection.
- `FA3-PROVIDER-MINIMAX-H3-001`: conditional hybrid reference provider. H3 Context-IR is a pattern source only; canonical context compilation remains the FA3 Video Context Compiler + `VideoGenerationIR`.

MiniMax H3 native **Diffusers** and **ComfyUI** projections are registered as `PRODUCTION_INTEGRATION_TARGET`, but are **not current-host promoted**. Local H3 deployment remains licence/territory/authorization gated and fail-closed. Promotion requires explicit licence admission, artifact trust, Host Resource Broker admission, adapter conformance, video E2E execution, and QC/provenance PASS evidence.

Registry regression coverage:

```bash
PYTHONPATH=src python -m unittest tests.test_video_registry -v
```

## ACE-Step mandatory generative-music provider

`FA3-PROVIDER-ACE-STEP-001` registers `ace-step/ACE-Step-1.5` as the **required primary reference provider** under the materialized existing `FA3-MUSIC-001` profile. This adds no capability and no architectural authority: the canonical capability count remains **143**, with projection over `CAP-017`, `CAP-066` and `CAP-131`.

ACE-Step does not own model routing, GPU placement, durable orchestration, policy, evidence, or artifact identity. Local accelerator execution remains Host Resource Broker admitted; automation must use a typed authenticated loopback REST adapter behind the Central MCP/Capability Gateway; Gradio remains an optional human UI.

The executable `FA3-ACE-STEP-GATESET-001` makes the following upstream changes reference evidence, **not automatic promotion**:

- PR #1282 / `2c513f9e...`: non-turbo DCW REST/CLI plumbing and SFT/XL-SFT quality fix candidate;
- PR #1305 / `c86889f4...`: text2music cover-state hygiene fix;
- PR #1310 / `0b5ff8ac...`: KV-cache sizing invariance across service re-init;
- PR #1311 remains open and therefore is not promotion evidence for LM engine teardown/re-init memory safety.

The latest formal upstream release remains `v0.1.8` and does not contain the August fix set. Production therefore requires an immutable commit/release pin; floating `main`, provider self-update and production model auto-download are forbidden.

Run the canonical gate with:

```bash
./bin/fa3-enforce acestep
PYTHONPATH=src python -m unittest tests.test_acestep_gate -v
```

Runtime promotion remains separately fail-closed on `evidence/receipts/ace-step-current-host.json`. Required current-host evidence includes model-identity matching, HRB admission, authenticated REST conformance, Turbo/XL-Turbo audio-quality E2E, text2music state-hygiene regression, KV-cache re-init invariance, LM clean-teardown or process-recycle behavior, lossless WAV/FLAC master provenance, and additional DCW-off positive/negative quality evidence before any SFT/XL-SFT promotion.



## Demucs executable provider and current-host evidence

The canonical Demucs provider now has a real FA3 adapter at `src/fa3_demucs_provider.py`. The adapter is fail-closed around model trust and host placement: only `FA3-DEMUCS-MODEL-ALLOWLIST-001` models are accepted, safetensors model classes are resolved through a fixed local class allowlist, legacy pickle checkpoints are denied on this production path, and CUDA execution requires a typed lease from `FA3-AUTH-HOST-RESOURCE-BROKER-001` plus an external HRB verifier response.

CI-safe executable conformance:

```bash
./bin/fa3-enforce demucs-provider
```

This produces `reports/demucs-provider-conformance-report.json` and exercises 13 positive/negative provider invariants without downloading Demucs models.

For the actual workstation, use an isolated per-provider venv (no conda/mamba):

```bash
bash bin/fa3-demucs-bootstrap.sh
```

Then collect production E2E evidence with a real audio file. CUDA has no implicit CPU fallback; the actual HRB verifier command must be supplied:

```bash
bash bin/fa3-demucs-current-host.sh \
  --input /path/to/real-audio.wav \
  --model htdemucs \
  --device cuda:0 \
  --hrb-lease /path/to/hrb-lease.json \
  --hrb-verify-command-json '["/path/to/actual-hrb-verifier","verify","--lease","{lease}","--device","{device}","--json"]'
```

By default model resolution is offline/cache-only. Add `--allow-network-model-fetch` only when the trusted model is not cached and the applicable FA3 egress policy permits the fetch.

The collector writes `evidence/receipts/demucs-current-host.json` plus runtime execution/stem evidence. The production gate:

```bash
./bin/fa3-enforce demucs-current-host
```

accepts only `CURRENT_HOST_PRODUCTION_E2E_PASS`, rejects synthetic input, verifies the execution-evidence digest, requires safetensors + class-allowlist proof, and requires an HRB lease for CUDA evidence. A synthetic collector run may be useful as a smoke test but cannot claim production current-host PASS.
