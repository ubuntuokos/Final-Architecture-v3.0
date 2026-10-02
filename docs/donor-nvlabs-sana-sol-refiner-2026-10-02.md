# NVlabs Sana / SoL-Refiner donor intake — 2026-10-02

## Owner-marked sources

The owner explicitly marked all three URLs as `donornak`:

- https://github.com/NVlabs/Sana/tree/sol-engine/models/sol-refiner
- https://github.com/NVlabs/SANA
- https://github.com/NVlabs

Repository identity is case-normalized to `github:nvlabs/sana`. The exact SoL-Refiner branch/path URL is preserved as component provenance under that repository identity rather than creating a duplicate repository donor.

## Canonical intake

- `FA3-DONOR-NVLABS-SANA-001` — `github:nvlabs/sana`
- `FA3-DONOR-NVLABS-ORG-001` — `github:nvlabs`
- registry: **1355 → 1357**
- capability baseline: **175 unchanged**
- capability delta: **0**
- authority delta: **0**
- usage edges: **none in this intake**

The NVlabs organization record is a discovery index only. It does not recursively admit child repositories.

## Observed upstream provenance

At intake preparation time:

- Sana default branch `main`: `f9178744c096dcf2a2ea773da183e341bcbeb044`
- `sol-engine` branch: `670482d8a857d578ac8a2ea89b052d0fb47badba`
- `models/sol-refiner` tree: `67717f3cf6e22ea280c258acef196f6c1b8a0ab2`
- SoL-Refiner README blob: `6ecd584c2397bc3a2e44aca271aa4bc34cf094c5`

The observed `sol-engine` merge commit identifies the SoL-Refiner inference extension for LTX-2.3 and MiniMax-H3.

The SoL-Refiner README describes a two-stage generator/refiner design: a base generator produces a lower-resolution draft and a separate refiner performs target-resolution refinement. It documents original LTX-2.3 one-step/multi-step paths and a later LTX-2.5/MiniMax-H3 extension, with refinement demonstrated across multiple base generators.

## FA3 planning value

The admitted reference may inform a shared provider-neutral Video Refinement / Enhancement Fabric, specifically:

- generator and refiner lifecycle separation;
- one-step distilled refinement and multi-step reference modes;
- draft-to-target-resolution enhancement;
- multi-generator refiner interoperability;
- streaming/bidirectional refinement patterns;
- explicit optimized/reference/approximate execution metadata;
- quality/evidence comparison between reference and optimized paths.

This registration does **not** decide that SoL-Refiner will be the only or default FA3 refiner.

## License and rights boundary

GitHub repository metadata for NVlabs/Sana declares Apache-2.0 at repository level. The `sol-engine` branch/component and its external model/runtime ecosystem must still be treated independently for material adoption.

In particular this intake does not admit or redistribute:

- LTX model weights/checkpoints;
- MiniMax H3 model weights;
- Hugging Face artifacts;
- Diffusers/NATTEN/CUDA/CUTLASS or other runtime dependencies;
- model datasets or training material;
- vendor-specific GPU kernels.

Any material reuse requires the existing FA3 License & Rights Authority and provenance checks.

## Runtime and hardware boundary

This is reference registration only. It does not install Sana, SoL-Refiner or any dependency and does not promote any provider/model/refiner/runtime.

Any later implementation must preserve:

- CPU-only FA3 baseline/conformance path;
- Model Router provider/model/refiner selection authority;
- HRB physical resource/device admission and placement authority;
- Hardware Safety Envelope and display-GPU rules;
- no silent CUDA/ROCm/XPU fallback or semantic substitution;
- immutable runtime/model identities;
- physical Current Host positive/negative/rollback evidence before runtime promotion.

## Usage-edge boundary

No donor usage edge is created here. After publication to `main`, any actual use of Sana/SoL patterns requires a fresh Reuse Assessment bound to the published registry containing these records, followed by explicit canonical usage-edge registration.
