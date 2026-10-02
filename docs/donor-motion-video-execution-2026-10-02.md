# FA3 Motion/Video execution donor intake — 2026-10-02

**Authority:** owner-explicit `donornak` registration.  
**Scope:** reference metadata only; no code, dependency, provider, model or runtime admission.

This intake registers five exact repositories as `ACCEPTED_REFERENCE`:

- Hugging Face Diffusers — https://github.com/huggingface/diffusers
- xDiT — https://github.com/xdit-project/xDiT
- HunyuanVideo-1.5 — https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5
- SkyReels-V3 — https://github.com/SkyworkAI/SkyReels-V3
- VideoSys — https://github.com/NUS-HPC-AI-Lab/VideoSys

## Planning value

The sources are intended to strengthen the approved #613 v2 Motion & Video design:

- Diffusers: common provider/model pipeline and adapter patterns.
- xDiT: multi-device/distributed DiT execution patterns without moving placement authority out of HRB.
- HunyuanVideo-1.5: consumer-GPU T2V/I2V model-interchange stress reference.
- SkyReels-V3: multimodal conditioning, audio-guided/V2V and multi-device capability-schema stress reference.
- VideoSys: scalable generation/inference/serving lifecycle and system-boundary reference.

## License and admission boundary

GitHub repository metadata reports Apache-2.0 for Diffusers, xDiT and VideoSys. HunyuanVideo-1.5 and SkyReels-V3 do not expose a standard SPDX license through repository metadata and therefore remain `EXACT_LICENSE_REVIEW_REQUIRED_BEFORE_MATERIAL_REUSE`.

No source code, model artifact, dependency, provider, runtime or service is admitted by this intake. No donor usage edge is created. Any later material adoption requires exact License & Rights/provenance, security, Software Coexistence, Hardware Safety and usage-edge review.

Capability baseline: **175**. Capability delta: **0**. Authority delta: **0**.

Parent published main: `d65215e75867d71605093ae8f46a0dfbd6c6f471`  
Parent donor count: **1344**  
Proposed donor count: **1349**
