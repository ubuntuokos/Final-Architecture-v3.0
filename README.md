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

MiniMax H3 **SGLang, vLLM, Diffusers and ComfyUI** projections are registered as `PRODUCTION_INTEGRATION_TARGET`, but are **not current-host promoted**. The pinned upstream reference is `MiniMax-AI/MiniMax-H3@d21241f0a4b3acbb34c97dae47fa417b7065e438`. The portable `h3-prompt-writing` skill is registered only as non-authoritative prompt/recipe knowledge (`skills-lock` hash `3d01859464bc9438585c8fdbf7fcd4b4c54404fadd3f1a64ab7970ae8877d086`): it may help project canonical intent into an H3-native prompt, but it cannot replace `VideoGenerationIR`, become the Video Context Compiler, select a provider or execute one. Local H3 deployment remains licence/territory/authorization gated and fail-closed. Every selected runtime requires an immutable version pin, adapter conformance, Host Resource Broker admission and real video E2E/QC/provenance evidence. The ComfyUI projection additionally remains blocked on version-pinned H3 compatibility and audio-path regressions because open upstream risks were observed in `Comfy-Org/ComfyUI#15960` and `#15970`.

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

Then collect production E2E evidence with a **real** audio file through the existing Host Resource Broker v1.0.0 interface. The harness asks the broker to choose the accelerator, issues an `AcceleratorExecutionLease@1`, resolves the leased GPU UUID back to the current CUDA ordinal, applies the lease-derived PyTorch allocator guard, runs Demucs, validates evidence, and revokes the lease on exit:

```bash
bash bin/fa3-demucs-hrb-production-e2e.sh /path/to/real-audio.wav
```

The default broker path is `/usr/local/bin/fa3-host-resource-broker`; override it with `FA3_HRB_BIN` only when the canonical HRB is installed elsewhere. The default lease asks for 6 GiB VRAM for one hour and can be changed with `FA3_DEMUCS_HRB_MEMORY_BYTES` and `FA3_DEMUCS_HRB_TTL_SECONDS`. CUDA has **no implicit CPU fallback** and bare `cuda` is rejected: execution must resolve to explicit `cuda:N` from the broker-issued GPU UUID.

For an already-issued canonical lease, the lower-level collector is also available:

```bash
bash bin/fa3-demucs-current-host.sh \
  --input /path/to/real-audio.wav \
  --model htdemucs \
  --device auto \
  --hrb-lease /path/to/accelerator-execution-lease.json
```

By default model resolution is offline/cache-only. Add `--allow-network-model-fetch` only when the trusted model is not cached and the applicable FA3 egress policy permits the fetch.

The collector writes `evidence/receipts/demucs-current-host.json` plus runtime execution/stem evidence. The production gate:

```bash
./bin/fa3-enforce demucs-current-host
```

accepts only `CURRENT_HOST_PRODUCTION_E2E_PASS`, rejects synthetic input, verifies the execution-evidence digest, requires safetensors + class-allowlist proof, and for CUDA requires the canonical HRB lease schema/issuer, broker `VALID` result, GPU UUID revalidation, and lease-derived allocator guard. A synthetic collector run may be useful as a smoke test but cannot claim production current-host PASS.


## Kdenlive canonical editorial baseline

`FA3-KDENLIVE-EDITORIAL-001` and `FA3-PROVIDER-KDENLIVE-001` consolidate the FA3 Kdenlive decisions as a non-root projection over existing `CAP-121` and `CAP-126`. Kdenlive is the **primary Linux/Kubuntu human NLE and final-assembly frontend**, but it is **not a hard backend dependency**, does not own orchestration or timeline semantics, and adds no capability or architectural authority. The canonical capability count remains **143**.

The automated editing representation is **OpenTimelineIO (OTIO)**. The canonical flow is:

```text
AI / agent editorial intent
        ↓
canonical OTIO timeline artifact
        ↓
Kdenlive import / human refinement / finishing
        ↓
evidence-backed export or delivery
```

Automation is **API-first**. Native OTIO import/export is the preferred interchange path; typed/versioned Kdenlive/MLT or D-Bus surfaces may be used only when capability-discovered. GUI automation is fallback-only and requires explicit unavailable-surface evidence, an auditable/reproducible action trace, pre/post project identity evidence, and HITL approval for critical mutations. External direct `.kdenlive` XML mutation remains forbidden.

Deterministic media inspection/transformation uses explicit `ffprobe` / `ffmpeg` commands with artifact lineage. Linux/Kubuntu/KDE Plasma/Wayland remains the first-class desktop projection.

Canonical gate:

```bash
./bin/fa3-enforce kdenlive-editorial
```

The upstream reference record is `canonical/references/FA3-KDENLIVE-UPSTREAM-REFERENCE-2026-08-30.json`; it records Kdenlive 26.04 native OTIO import/export and supported subtitle import as reference evidence only, never as current-host promotion evidence.


## Blackhole / Kdenlive long-form transcription integration

`FA3-STT-001` and its child `FA3-STT-MEDIA-001` are now materialized as provider-neutral speech-recognition profiles. `FA3-BLACKHOLE-KDENLIVE-001` is a non-root integration projection over existing `CAP-017` and `CAP-121`; it creates no new capability or architectural authority, so the canonical count remains **143**.

The executable bridge is `src/fa3_blackhole_kdenlive.py`. It implements:

```text
Kdenlive media / timeline zone
        ↓
FFmpeg PCM24 stereo extraction
        ↓
optional FA3 Demucs vocals preprocessing
        ↓
FFmpeg 16 kHz mono PCM16 normalization
        ↓
provider-neutral STT request/result artifacts
        ↓
timestamp validation + timeline offset projection
        ↓
SRT + VTT + canonical caption JSON
        ↓
Kdenlive subtitle import descriptor
```

Demucs is **optional preprocessing only**. STT remains valid when `preprocessing = "none"`; when Demucs is explicitly requested, a Demucs failure is fail-closed and there is no silent raw-audio fallback.

The integration deliberately does **not** modify `.kdenlive` project XML. It produces sidecar subtitle artifacts for Kdenlive's supported subtitle-import path. This keeps human editorial state and project mutation inside Kdenlive rather than giving the Blackhole worker direct project-write authority.

CI gate:

```bash
./bin/fa3-enforce blackhole-kdenlive
```

The gate validates canonical registry relationships and runs the executable integration conformance suite.

### Prepare a timeline/media range

Copy and edit `examples/blackhole-kdenlive-request.json`, then:

```bash
bash bin/fa3-blackhole-kdenlive prepare \
  --request examples/blackhole-kdenlive-request.json
```

The output directory receives:

- `decoded-audio.wav`
- optional `demucs/vocals.wav` and Demucs execution evidence
- `stt-input.wav` (16 kHz mono PCM16)
- `blackhole-media-handoff.json`

### Provider-neutral STT command contract

For a full pipeline, `stt_command` must contain both `{request}` and `{result}` placeholders. The command is executed with `shell=False`. The STT worker receives a `fa3.stt-media-request.v1` JSON and must return `fa3.stt-media-result.v1` bound to the exact prepared-audio SHA256.

Run:

```bash
bash bin/fa3-blackhole-kdenlive pipeline \
  --request examples/blackhole-kdenlive-request.json
```

A complete run additionally produces:

- `blackhole-subtitles.srt`
- `blackhole-subtitles.vtt`
- `blackhole-caption-track.json`
- `kdenlive-subtitle-import.json`
- `blackhole-kdenlive-pipeline-result.json`

Import the generated SRT/VTT through Kdenlive's subtitle import function. No direct project XML write is performed.

### CUDA Demucs preprocessing through HRB

The Blackhole integration reuses the existing Demucs per-provider venv and canonical Host Resource Broker contract. It does not select a GPU itself.

```bash
FA3_BLACKHOLE_PYTHON="$PWD/.venv-demucs/bin/python" \
bash bin/fa3-blackhole-kdenlive-hrb-e2e.sh \
  /path/to/blackhole-kdenlive-request.json
```

The harness requests a broker-selected accelerator lease, maps the lease GPU UUID back to the current CUDA ordinal, injects the canonical HRB verifier into the Demucs subrequest, runs the current-host collector, and revokes the lease on exit.

Current-host evidence levels are distinct:

- `CURRENT_HOST_MEDIA_PREP_PASS`: media/range extraction and STT handoff completed, but no STT backend was executed.
- `CURRENT_HOST_KDENLIVE_BLACKHOLE_E2E_PASS`: STT result validation plus SRT/VTT/Kdenlive import projection also completed.

Neither status can be claimed by GitHub-hosted CI.

Runtime policy remains native Linux/KDE: system FFmpeg plus per-provider Python venvs. Conda/Miniforge and a separate Blackhole GUI are not part of this projection.


## Whisper STT provider materialization

`FA3-PROVIDER-WHISPER-001` is the first executable local production-candidate provider behind the provider-neutral `FA3-STT-MEDIA-001` contract. It does not become STT authority, model-routing authority or GPU-placement authority. The canonical capability count remains **143** and no new architectural authority is created.

The provider is pinned to `openai/whisper v20250625` / commit `31243bad24cc746f07d4c8bfdd2d974872cb1803`. The default local long-form model is `turbo`; `large-v3`, `medium`, `small`, `base` and `tiny` are registry-allowlisted fallback/quality tiers. Arbitrary checkpoint paths are not accepted by the FA3 production surface.

The execution contract is:

```text
fa3.stt-media-request.v1
        ↓
FA3-PROVIDER-WHISPER-001
        ↓
official model allowlist + SHA256 verification
        ↓
explicit CPU or HRB-leased cuda:N
        ↓
Whisper transcribe + native word timestamps
        ↓
timing validation
        ↓
fa3.stt-media-result.v1
```

Upstream Whisper `translate` is intentionally not exposed by this adapter. Translation remains the separate typed FA3 translation stage so source text, source language, target language, provider identity and lineage are not collapsed into the STT result.

CI-safe gates:

```bash
./bin/fa3-enforce whisper-stt
./bin/fa3-enforce whisper-stt-provider
```

The executable provider conformance contains 18 positive/negative cases covering typed request/result, exact prepared-audio hash binding, 16 kHz mono PCM16 enforcement, official model allowlisting, arbitrary checkpoint denial, offline cache behavior, runtime version pinning, HRB CUDA admission, timing validation, word-timestamp preservation and execution lineage.

### Install the provider runtime

No Conda/Miniforge is used:

```bash
bash bin/fa3-whisper-bootstrap.sh
```

This creates `.venv-whisper` and installs the exact upstream commit. Override the venv with `FA3_WHISPER_VENV`. Model cache defaults to `${XDG_CACHE_HOME:-$HOME/.cache}/whisper`; set `FA3_WHISPER_MODEL_CACHE` to place it on the workstation AI cache.

Model fetch is **offline by default**. The first trusted fetch must be explicit with `--allow-network-model-fetch`; the downloaded bytes are then checked against the canonical SHA256.

### Blackhole → Whisper → Kdenlive

Use `examples/blackhole-kdenlive-whisper-request.json` as the full pipeline template. Because the provider has its own venv, Blackhole invokes the wrapper explicitly through `bash` while still using `shell=False` at the subprocess boundary.

A current-host full pipeline can be started with:

```bash
FA3_WHISPER_MODEL_CACHE=/path/to/whisper-cache \
FA3_WHISPER_ALLOW_NETWORK_MODEL_FETCH=1 \
bash bin/fa3-blackhole-whisper-e2e.sh \
  /path/to/blackhole-kdenlive-request.json
```

After the model is cached, remove `FA3_WHISPER_ALLOW_NETWORK_MODEL_FETCH=1` for offline execution.

The successful chain produces:

```text
media / Kdenlive timeline range
→ optional Demucs preprocessing
→ 16 kHz mono PCM16 STT audio
→ real Whisper transcription
→ word/segment timing evidence
→ validated fa3.stt-media-result.v1
→ SRT + VTT + caption JSON
→ Kdenlive subtitle import descriptor
```

### HRB-backed Whisper CUDA production E2E

For direct provider current-host evidence through a broker-selected GPU:

```bash
bash bin/fa3-whisper-hrb-production-e2e.sh \
  /path/to/fa3-stt-media-request.json \
  --allow-network-model-fetch
```

The harness issues `AcceleratorExecutionLease@1` with purpose `FA3 Whisper STT production E2E`, maps the broker-selected GPU UUID to the current `cuda:N`, projects `memory_max_bytes` into `torch.cuda.set_per_process_memory_fraction`, runs transcription, and revokes the lease on exit.

The current-host collector writes `evidence/receipts/whisper-stt-current-host.json` only after a real transcription returns at least one validated speech segment. GitHub-hosted CI is explicitly forbidden from claiming this receipt.

Canonical provider-production promotion therefore remains:

```text
EXECUTABLE_PROVIDER_CONFORMANCE = PASS
CANONICAL_WHISPER_STT_GATE       = PASS
CURRENT_HOST_WHISPER_STT_E2E     = required for production promotion
```


## Buzz optional collaborative-workspace reference provider

`FA3-PROVIDER-BUZZ-001` registers `block/buzz` as an **OPTIONAL human–agent collaborative workspace / evented development-forge reference provider + STRONG architectural pattern source for delegated agent identity, signed event provenance, provider boundaries, remote-agent lifecycle, workflow traceability and release integrity**.

Buzz creates **no new capability** and **no new architectural authority**; the canonical capability count remains **143**. Its patterns may be absorbed only through existing FA3 authority boundaries.

The mandatory P0 authority-separation constraint is:

> **Buzz SHALL NOT become an FA3 identity, authorization, MCP, workflow, evidence, secrets, host-resource or developer-execution authority.**

Canonical records:

- `canonical/providers/FA3-PROVIDER-BUZZ-001.json`
- `canonical/decisions/FA3-DEC-BUZZ-2026-08-30.json`
- `canonical/buzz-enforcement.json` (`FA3-BUZZ-GATESET-001`, fail-closed policy record)

Any future registry, profile, contract, runtime or promotion projection that assigns Buzz one of those prohibited authority roles must be rejected rather than promoted.


### Buzz executable regression gate

The permanent fail-closed gate is executable with:

```bash
./bin/fa3-enforce buzz
```

`FA3-BUZZ-GATESET-001` performs canonical record integrity checks, recursively scans canonical JSON for prohibited Buzz authority assignments, and executes 10 regression cases: eight authority-escalation denials plus canonical-root and capability/authority-count drift denials. The gate is also invoked by the global `static` enforcement path and GitHub CI.

The generated report is `reports/buzz-gate-report.json`. Buzz remains optional at runtime; the authority-separation rule is mandatory regardless of provider deployment.


## X-CMD optional terminal toolchain provider

`FA3-PROVIDER-XCMD-001` registers `x-cmd/x-cmd` as an **OPTIONAL terminal toolchain / agent-shell integration / on-demand CLI provisioning reference provider + architectural pattern source**. It adds no new capability and no new architectural authority; the canonical capability count remains **143**.

The upstream default branch is a rolling `X` branch. The 2026-08-30 reference observation is pinned to `X@390fa27a231579f1ee493bcd7961bcba4cb85034`; the immutable release reference is `v0.10.1@1594d06582bf024d0a71ee108afe06a98629ec9a`. Neither a floating `X` branch nor provider self-upgrade is production promotion evidence.

The executable `FA3-XCMD-GATESET-001` enforces 12 P0 rules: remote network content cannot transition directly into shell execution; executable identity must be immutable; package curation is not transitive trust; agent shell use requires caller/workspace/capability mediation; project agent instructions remain untrusted scoped context; self-update and host-global mutation require external authorization; model/secrets/egress/MCP/HRB/artifact/evidence boundaries remain external; lazy materialization cannot become hidden background activity; disabled/reference-only cost is near-zero; X-CMD remains non-authoritative; and every material execution is attributable.

Run:

```bash
./bin/fa3-enforce xcmd
PYTHONPATH=src python -m unittest tests.test_xcmd_gate -v
```

Canonical production provisioning explicitly rejects direct `curl/wget -> eval/sh` execution even though upstream documents such bootstrap convenience. Network-retrieved executable content must first be materialized, pinned, integrity/provenance checked, policy-admitted and then executed through the FA3-controlled tool path.


## Modular MAX / Mojo optional execution provider family

`FA3-PROVIDER-MAX-001` and `FA3-PROVIDER-MOJO-001` register `modular/modular` as an **OPTIONAL AI serving / accelerator-execution provider family + STRONG architectural pattern source**. This creates **no new capability**, **no new architectural authority**, and **no new canonical root**; the canonical capability count remains **143**.

The provider family is deliberately split:

- **MAX**: optional high-performance model inference/serving, OpenAI-compatible serving projection, model-graph execution, provider-local scheduling, distributed execution and KV-cache implementation.
- **Mojo**: optional portable kernel/accelerator execution, target specialization and custom MAX-operation implementation.

Neither provider may absorb FA3 authority. Model routing remains `FA3-AUTH-MODEL-ROUTER-001`; accelerator admission/placement/reservation remains `FA3-AUTH-HOST-RESOURCE-BROKER-001`; authorization/policy remains `FA3-AUTH-SECURITY-GOV-001`; workflow, secrets, artifact/model identity and evidence remain under their existing FA3 authorities.

The permanent `FA3-MODULAR-GATESET-001` enforces 14 fail-closed invariants covering execution-topology/resource-authority separation, provider-local/global scheduling separation, portable semantic vs target-artifact identity, specialization semantic preservation, model-variant compatibility evidence, compiled-artifact lineage, warm-cache scoping, cache ownership/lifecycle, cancellation cleanup, shared-cache security boundaries, topology-bound benchmark evidence, OpenAI API projection boundaries, stable/nightly evidence separation and explicit licence/redistribution admission.

The upstream reference is pinned to `modular/modular@f08ac164e2743513f60e46621de6dc4a5a5a30e7` (observed `Mojo 1.1.0.dev2026083005`, `MAX 26.6.0.dev2026083005`) as **nightly development reference evidence only**. Floating `main` is forbidden as promotion evidence.

Run the canonical gate with:

```bash
./bin/fa3-enforce modular
PYTHONPATH=src python -m unittest tests.test_modular_gate -v
```

The provider runtime remains optional when disabled; the 14 architectural invariants are mandatory globally.


## Munder Difflin optional multi-agent coordination provider

`FA3-PROVIDER-MUNDER-DIFFLIN-001` registers `chaitanyagiri/munder-difflin` as an **OPTIONAL local multi-agent developer-workspace / coordination reference provider + strong provider-neutral architectural pattern source**. It adds **no new capability**, **no new architectural authority**, and **no required runtime dependency**; the canonical capability count remains **143**.

The absorbed value is deliberately narrower than the upstream application. FA3 adopts the coordination invariants, not the office UI or provider-local authority model: isolated agent processes/sessions; single-writer mutable coordination state; single-committer repository mutation; atomic one-file-per-message mailboxes; idempotent consumption with independent cursors; bounded request/reply hops; isolated concurrent worktrees; policy-classified human escalation; steer → constrain → terminate circuit breaking; strict telemetry allowlisting; context that cannot grant authority; transition-specific lifecycle evidence; fault injection for normally unreachable failure paths; and complete ephemeral-worker teardown.

The mandatory boundary is:

> **Munder Difflin SHALL NOT become an FA3 identity, authorization, MCP/tool-mediation, model-routing, secrets, network-egress, host-resource, workflow/orchestration, evidence, developer-execution, git/release or registry authority.**

The upstream reference is pinned in `canonical/references/FA3-MUNDER-DIFFLIN-UPSTREAM-REFERENCE-2026-08-30.json`: latest release `v0.4.6` at commit `64bd64df0e8d315a6e895283f776b81f84eef2cc`, plus observed `main` commit `fc436bd8b673913c71e3230de08e44f355ffc2e3`. Upstream explicitly describes security support as **main-only / early prototype**, and the release tag is not treated as signed promotion evidence. Therefore provider runtime activation remains **NOT_PROMOTED_REFERENCE_ONLY** until a separate immutable current-host conformance path exists.

Run the executable gate with:

```bash
./bin/fa3-enforce munder-difflin
PYTHONPATH=src python -m unittest tests.test_munder_difflin_gate -v
```

`FA3-MUNDER-DIFFLIN-GATESET-001` executes 16 positive/negative regressions and recursively rejects canonical records that promote Munder Difflin into an FA3 authority. The gate is bound into the global static enforcement and permanent GitHub CI.


## AI Engineering from Scratch cross-cutting reference

`FA3-SOURCE-AI-ENGINEERING-FROM-SCRATCH-001` registers `rohitg00/ai-engineering-from-scratch` as an **ACCEPTED cross-cutting architectural pattern source + engineering/evidence reference + agent-skill/MCP conformance reference + educational reference**.

It is deliberately **not** a runtime provider, capability, canonical specification or architectural authority. It creates no new capability and no new architectural authority; the canonical capability count remains **143**. The observed upstream source is pinned to commit `a56b4b8ad43a3767c771953d217036813f697bc7`; floating `main` is reference discovery only and is forbidden as promotion evidence.

The permanent `FA3-AIENG-GATESET-001` absorbs and enforces 11 provider-neutral P0 invariants:

1. registry publication is not production admission;
2. skill/context availability is not execution authority;
3. an agent/provider assertion is not completion or promotion evidence;
4. material execution requires attributable evidence;
5. protocol/security conformance requires positive + negative/refusal + boundary evidence;
6. raw boundary/wire evidence and SDK/adapter projection evidence must both exist for critical protocols;
7. gateways/proxies preserve correlated ingress → origin → egress evidence;
8. compatibility/security downgrade is fail-closed unless explicitly authorized and evidenced;
9. sensitive evidence is redacted before serialization, hashing, logging or storage;
10. rollback readiness is established before applicable production promotion;
11. progressive disclosure may load branch-specific context only after activation and never grants authority.

Run directly with:

```bash
./bin/fa3-enforce ai-engineering
PYTHONPATH=src python -m unittest tests.test_ai_engineering_gate -v
```

The gate is also part of the global `static` enforcement path and the permanent GitHub CI workflow. It checks the immutable upstream reference, canonical decision/policy binding, source non-authority status and 11 executable negative regression cases.


## Modular MAX/Mojo executable runtime + current-host production evidence

The optional Modular provider family has a separate executable runtime contract at `canonical/FA3-MODULAR-RUNTIME-CONFORMANCE-001.json`, a production smoke-model allowlist at `canonical/FA3-MODULAR-MODEL-ALLOWLIST-001.json`, and fail-closed provider/current-host gates.

CI-safe provider conformance:

```bash
./bin/fa3-enforce modular-provider
```

This validates exact model/revision admission, loopback-only serving, remote-code denial, stable/nightly separation, explicit HRB GPU admission and lease-derived MAX memory guarding without claiming execution on the FA3 workstation.

Materialize the stable runtime in an isolated `uv` venv:

```bash
bash bin/fa3-modular-bootstrap.sh
```

Then execute the real current-host production E2E:

```bash
bash bin/fa3-modular-current-host.sh \
  --model-revision 9e6c6ccf47cd318696e137d381a7ded8fe4df09f \
  --devices cpu \
  --allow-network-model-fetch
```

The one-time network flag is explicit; after the pinned model is cached, omit it. The collector verifies the canonical `LiquidAI/LFM2.5-350M` safetensors digest, performs real loopback MAX `/v1/chat/completions` inference, compiles and executes a native Mojo program, and hashes all evidence artifacts. GPU execution requires explicit `gpu:N` plus a broker-valid `AcceleratorExecutionLease@1`; broad `gpu` / `gpu:all` placement is rejected.

Production validation:

```bash
./bin/fa3-enforce modular-current-host
```

Only a real host run can create `CURRENT_HOST_PRODUCTION_E2E_PASS`. GitHub-hosted CI cannot claim it. `.github/workflows/fa3-modular-current-host.yml` is restricted to a self-hosted Linux/x64 runner carrying the `fa3-current-host` label. See `docs/modular-current-host.md`.

## AutoGPT optional agentic workflow/workbench provider

`FA3-PROVIDER-AUTOGPT-001` registers `Significant-Gravitas/AutoGPT` as an **OPTIONAL agentic workflow/workbench execution reference provider + STRONG architectural pattern source**. It creates no new capability and no new architectural authority; the canonical capability count remains **143**.

FA3 absorbs 17 mandatory P0 invariants covering typed node contracts, delegated execution context, non-transitive graph authorization, delegated capability narrowing, monotonic credential-scope narrowing, validate-before-persist/activate, trigger/schedule non-authority, model-catalog and secrets boundaries, executor/resource boundaries, marketplace/library non-admission, attributable node evidence, MCP/egress/integration boundaries, immutable runtime identity, component-license admission, disabled-provider near-zero cost, and provider non-authority.

The mandatory authority boundary is:

> **AutoGPT SHALL NOT become an FA3 identity, authentication, authorization, secrets, MCP/capability-gateway, model-routing, durable-workflow, evidence/provenance, network-egress, host-resource, developer-execution, artifact-trust or canonical-registry authority.**

The upstream reference is pinned to observed `master@32a43d005c0c42079ceba68d9a49c28e0eeaa6c7` and latest release `autogpt-platform-beta-v0.7.3@f49bcca95ed327396d8ebdd0bdf7810de482ac1a`. Floating `master`, a release tag without immutable commit binding, marketplace adoption, or provider-local authorization are not production promotion evidence.

Run the permanent gate with:

```bash
./bin/fa3-enforce autogpt
PYTHONPATH=src python -m unittest tests.test_autogpt_gate -v
```

AutoGPT runtime activation remains **NOT_PROMOTED_REFERENCE_ONLY** and is not required for global FA3 promotion while disabled. `autogpt_platform/` is PolyForm Shield 1.0.0 while Classic and repository content outside `autogpt_platform/` are MIT; production runtime/code use therefore requires explicit component-license admission plus separate current-host conformance. Architectural pattern absorption does not copy AutoGPT Platform source code into the FA3 canonical core.



## Cross-conversation canonical reconciliation (2026-08-30)

The repository now materializes previously accepted FA3 decisions that were present in conversation/specification state but absent from the GitHub canonical SSOT. The reconciliation preserves the 143-capability baseline, creates no new architectural authority, keeps provider/reference implementations authority-free, and does not claim global runtime promotion. Permanent regression coverage: `tests/test_conversation_reconciliation.py` and `canonical/conversation-reconciliation-enforcement.json`.


## Controlled external API / service / MCP discovery

`FA3-EXTERNAL-API-DISCOVERY-001` is the P1 / MUST-IF-EXTERNAL-DISCOVERY-USED projection for controlled discovery of external APIs, services and MCP endpoints over existing `CAP-011`, `CAP-074` and `CAP-075`. It adds **no capability** and **no architectural authority**; the canonical capability count remains **143**.

Pinned discovery/reference sources:

- `FA3-SOURCE-PUBLIC-APIS-001` — primary curated reference source (`public-apis/public-apis`);
- `FA3-SOURCE-PUBLIC-API-LISTS-001` — primary machine-readable ingestion source (`public-api-lists/public-api-lists`);
- `FA3-SOURCE-API-MEGA-LIST-001` — secondary high-breadth untrusted discovery source (`cporter202/API-mega-list`), restricted to discovery metadata until licence/terms admission;
- `FA3-PATTERN-MEGALIST-001` — optional UI virtualization/windowing pattern source only (`meganz/megalist`), not an API catalog or runtime dependency.

The normative rule is: **external discovery is not authorization**. Catalog publication, popularity, sponsorship, advertised auth/CORS/schema metadata, or an MCP listing cannot directly register a tool, authorize egress, obtain secrets, create a capability, or execute anything.

The fail-closed admission sequence is:

```text
discover -> normalize -> deduplicate -> provenance -> licence/terms
-> endpoint verification -> protocol/schema discovery -> security classification
-> secrets requirements -> egress classification -> capability mapping
-> policy approval -> sandbox probe -> conformance evidence
-> registry admission -> execution
```

Run the executable gate with:

```bash
./bin/fa3-enforce external-api-discovery
```

The gate includes 13 positive/negative regressions covering non-authorization, immutable source identity, licence/terms handling, endpoint/schema verification, secret and egress boundaries, provider-neutral capability mapping, sandbox admission, MCP auto-registration denial, source-failure isolation, and source non-authority.

## Presenton optional presentation worker

`FA3-PROVIDER-PRESENTON-001` registers `presenton/presenton` as the optional self-hosted presentation/document generation, editing and PPTX/PDF export worker projected over existing `CAP-018`, `CAP-030` and `CAP-033`. It adds no capability and no architectural authority; the canonical capability count remains **143**.

The production candidate is pinned to upstream `v0.9.8-beta` / `88c28f18a63e29742e4922facdba6b95c67959cd` and OCI index `sha256:e6866086f2dbdf9f6c50c8f217123cada2a84f4dd03131ad78f397d6fb11b3d1` (`linux/amd64` manifest `sha256:2db3979c90d70952de075e301f6ba8cac207e5d06fe89e698d5b22101f9074dd`). Floating tags and `latest` are forbidden.

The checked-in deployment projection uses a rootless Podman Quadlet, binds only `127.0.0.1:5001`, passes no GPU device, requires PostgreSQL, routes text generation only through the central LiteLLM gateway and routes image work to the separately admitted ComfyUI service. Web grounding and anonymous tracking are disabled, parallel image generation is disabled, and credentials/workflow JSON arrive through Podman secrets materialized from Infisical. Presenton-local Mem0 remains presentation-scoped working memory and is not canonical FA3 memory.

The authority boundary is mandatory:

> **Presenton SHALL NOT become an FA3 identity, authorization, MCP, workflow, event, model-routing, host-resource, image-generation, memory, evidence, secrets, network-egress or artifact-trust authority.**

CI-safe canonical and executable conformance:

```bash
./bin/fa3-enforce presenton
PYTHONPATH=src python -m unittest tests.test_presenton_gate -v
```

The real workstation path is documented in `deployment/presenton/README.md`. After the service, LiteLLM, ComfyUI, PostgreSQL, Caddy and access key are materialized, run:

```bash
bash bin/fa3-presenton-current-host.sh \
  --base-url http://127.0.0.1:5001 \
  --access-key-file /path/to/infisical-materialized-access-key
```

The collector requires the active rootless Quadlet and pinned OCI digest, proves unauthenticated denial, performs real asynchronous generation, downloads and hashes the PPTX, re-exports the same presentation to PDF, renders every PDF page with Poppler, and then submits the receipt to `./bin/fa3-enforce presenton-current-host`. CI or synthetic files cannot claim `CURRENT_HOST_PRODUCTION_E2E_PASS`; until that real-host run succeeds, the CAP-033 registry entry and Presenton production E2E remain `PENDING_CURRENT_HOST`.

## FA3-native multi-agent developer coordination reference runtime v0.1

`FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001` extends the existing mandatory `FA3-AGENT-EXEC-001` profile; it is **not a new capability or architectural authority**. The canonical capability count remains **143**. The contract family defines typed `AgentTask`, `AgentDelegation`, `WorkspaceLease`, `AgentMessage`, `AgentResult`, `HumanEscalation`, `CircuitBreakerAction`, `IntegrationIntent`, provider-adapter descriptors, coordination events and execution evidence.

The reference runtime is `FA3-DEVELOPER-AGENT-COORDINATION-REF-RUNTIME-001 v0.1.0` in `src/fa3_developer_agent_coordination.py`. It proves the provider-neutral coordination mechanics with real local Git worktrees and real subprocess workers while using a deterministic built-in fixture adapter rather than claiming Codex/Claude/Gemini production admission.

The positive E2E flow is:

```text
typed task/delegation
        ↓
3 isolated Git worktrees
        ↓
atomic mailbox + independent cursor
        ↓
3 separate worker processes
        ↓
uncommitted worker diffs
        ↓
path-conflict check
        ↓
single FA3 Integration committer
        ↓
integration commit + evidence
        ↓
complete process/worktree/message cleanup
```

The executable negative cases deny or terminate: duplicate mutating workspaces, worker direct commits to `main`, message-hop overflow, destructive action without human approval, cleanup leaks, provider authority escalation and overlapping worker diffs.

Run the reference E2E evidence collector:

```bash
chmod +x bin/fa3-developer-agent-coordination-e2e
./bin/fa3-developer-agent-coordination-e2e
```

It writes `evidence/receipts/developer-agent-coordination-ci-e2e.json` and `reports/developer-agent-coordination-e2e-report.json`. The receipt status is `CI_REFERENCE_RUNTIME_E2E_PASS`; it is explicitly **not** current-host production evidence for any external agent provider.

Run the permanent gate:

```bash
./bin/fa3-enforce developer-agent-coordination
PYTHONPATH=src python -m unittest tests.test_developer_agent_coordination -v
```

The provider adapter boundary exposes spawn/assign/observe/interrupt/constrain/terminate/collect-result semantics so future Codex, Claude Code, Gemini CLI, OpenCode, AutoGPT or Munder Difflin adapters can be attached without giving those providers FA3 authorization, tool-mediation, host-resource, evidence or repository-integration authority.
