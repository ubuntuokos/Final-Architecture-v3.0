# FA3 Motion & Video v3 + shared Video Refinement — 2026-10-02

This materialization keeps MiniMax H3 as an optional, disabled-by-default conditional reference and routes all applications through the shared FA3 Motion & Video Generation Fabric.

The v3 execution boundary reuses VideoGenerationIR/MMG Context IR, Model Router routing, HRB resource admission, Workload Mode, and the existing provider lifecycle contract. Applications do not directly bind to H3 or any refiner.

The new `FA3-VIDEO-REFINEMENT-CONTRACTS-001` separates base generation from refinement. It supports one-step distilled and multi-step reference refinement, draft-to-target resolution, multi-generator interoperability, and explicit REFERENCE/OPTIMIZED/APPROXIMATE quality modes. Approximate execution must be disclosed.

Five donor patterns are adopted with canonical usage edges: Diffusers, xDiT, SkyReels-V3, VideoSys and NVlabs/Sana. Sana/SoL-Refiner is used only as an architecture-pattern source. No Sana runtime, weights, checkpoints, external LTX/MiniMax weights, or vendor-specific GPU kernels are imported or admitted by this change.

CPU reference execution is mandatory at fabric level. CUDA, ROCm/HIP, Intel XPU and remote execution are optional admitted backend classes. Model Router remains the provider/model/refiner selection authority and HRB remains the physical device/resource authority. Silent provider/model/refiner/device/backend/cloud fallback is forbidden.

Capability baseline remains 175. No new capability or architectural authority is introduced. Static materialization does not claim Current Host PASS; physical positive/negative/rollback requalification remains separate.
