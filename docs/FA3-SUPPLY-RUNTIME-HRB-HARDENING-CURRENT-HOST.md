# FA3 Supply/Runtime/HRB current-host closure

The static/canonical hardening gate does not claim physical runtime promotion. This closure has two separately scoped real-host surfaces.

## Hardware Audit

The test remains vendor-neutral and CPU-only compatible. Accelerator cardinality is 0..N. Any accelerator-bearing plan uses a live stable accelerator identity; runtime ordinals are not identity. The example files are templates only and are not evidence.

## Automated supply-chain admission

Select a real local artifact/source tree with an immutable source repository + commit, artifact kind and declared SPDX license. `SOURCE_BUILD` and `OCI_IMAGE_EXPORT` require a dependency lock; only `PREBUILT_BINARY` may omit it. Syft, Grype and ScanCode must already be installed on the host; the workflow never downloads scanners. The scan computes a content hash, generates a CycloneDX SBOM, evaluates vulnerabilities, derives license compatibility from `FA3-SCS-LICENSE-POLICY-001`, and writes `supply-chain-admission-current-host.json`.

## Provider runtime environment

Prepare one `fa3.provider-runtime-environment.v1` plan for the admitted provider being proven. Three non-evidence templates are included for VENV, OCI and HOST_NATIVE. After the physical SCS scan, `tools/fa3_bind_provider_runtime.py` writes a separate runtime copy bound to the exact SCS receipt SHA-256; the operator template is not modified. VENV proof checks the real environment, dependency-lock binding and isolated Python identity. OCI proof requires a preloaded digest-matching image and executes it rootlessly with `--pull=never --network none --read-only`. HOST_NATIVE proof is identity-only: the collector hashes the declared non-symlink executable and does not execute arbitrary host-native code.

## HRB composite control plane

Prepare a real current-host resource plan and capacity input from the live host audit. Do not use the checked-in example values as evidence. The collector exercises the atomic reservation plan, authenticated HRB-internal derived leases, aggregate child-budget refusal, forged-parent refusal and parent revocation cascade. It deliberately uses a one-run ephemeral HMAC key that is never persisted.

This surface proves control-plane semantics only. It does **not** claim that a production Blackhole, Whisper or Demucs workload has been physically resource-enforced by the installed privileged broker.

## hu-HU golden corpus

Prepare a corpus manifest covering every canonical FA3-HU-AQC-001 category. Each entry points to a real local PCM16 WAV plus a current-host scorer bundle accepted by the existing single-sample HU-AQC collector. Every entry requires an opaque provenance reference. Any scorer bundle with `cloning=true` requires explicit `GRANTED` consent plus an opaque consent reference; the dedicated voice-cloning category additionally requires `cloning=true`. Threshold relaxation is forbidden for closure.

The corpus and audio are operator inputs and are not committed to the repository.

## Self-hosted execution

Run the **FA3 Supply Runtime HRB Current-Host Closure** workflow with `execute_current_host=true` after placing the three input files under `.fa3-current-host/input/`, or supply explicit paths through workflow inputs.

Required outputs:

- `evidence/receipts/supply-chain-admission-current-host.json`
- `evidence/receipts/provider-runtime-current-host.json`
- `evidence/receipts/hrb-composite-current-host.json`
- `evidence/receipts/hu-aqc-golden-corpus-current-host.json`
- `reports/supply-runtime-hardening-current-host-gate-report.json`

A scoped PASS still has `production_broker_promotion_claim=false` and `global_promotion_claim=false`. Production workload promotion remains subject to the existing real workload/current-host gates.
