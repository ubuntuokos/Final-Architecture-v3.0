# Hair / Groom donor intake — 2026-10-03

## Owner-marked intake

The owner explicitly marked **16 submitted sources** as `donornak`.

- published parent main: `0a5641204c6f8caaf65e2e4bfc4af928b5579d54`
- parent donor registry blob: `ee3a274e842471a3362c343f1ffa2eee935f85f0`
- registry: **1405 → 1421**
- capability baseline: **175**
- capability delta: **0**
- architectural authority delta: **0**
- donor usage edges created: **0**

All 16 records are metadata/reference-only `ACCEPTED_REFERENCE` entries.

## Canonical source resolution

The submitted `https://github.com/Vanessi k` locator contained whitespace and is not a valid GitHub URL. It is preserved in intake provenance and canonically registered as the verified profile `https://github.com/Vanessik`.

## Sources

| Submitted source | Canonical source | Class | Donor ID |
| --- | --- | --- | --- |
| https://github.com/kyleolsz | https://github.com/kyleolsz | profile-discovery | `FA3-DONOR-KYLEOLSZ-001` |
| https://github.com/facebookresearch/iphg | https://github.com/facebookresearch/iphg | repository-reference | `FA3-DONOR-FACEBOOKRESEARCH-IPHG-001` |
| https://github.com/SamurAIGPT/ai-hair-style-simulator | https://github.com/SamurAIGPT/ai-hair-style-simulator | repository-reference | `FA3-DONOR-SAMURAIGPT-AI-HAIR-STYLE-SIMULATOR-001` |
| https://github.com/facebookresearch/CT2Hair | https://github.com/facebookresearch/CT2Hair | repository-reference | `FA3-DONOR-FACEBOOKRESEARCH-CT2HAIR-001` |
| https://github.com/Vanessi k | https://github.com/Vanessik | profile-discovery | `FA3-DONOR-VANESSIK-001` |
| https://haiminluo.github.io/hairgpt/ | https://haiminluo.github.io/hairgpt/ | research-project | `FA3-DONOR-HAIRGPT-001` |
| https://github.com/c-he | https://github.com/c-he | profile-discovery | `FA3-DONOR-C-HE-001` |
| https://github.com/MengZephyr | https://github.com/MengZephyr | profile-discovery | `FA3-DONOR-MENGZEPHYR-001` |
| https://github.com/Xiaojiu-z | https://github.com/Xiaojiu-z | profile-discovery | `FA3-DONOR-XIAOJIU-Z-001` |
| https://github.com/cychungg | https://github.com/cychungg | profile-discovery | `FA3-DONOR-CYCHUNGG-001` |
| https://github.com/AIRI-Institute | https://github.com/AIRI-Institute | organization-discovery | `FA3-DONOR-AIRI-INSTITUTE-001` |
| https://github.com/jin-cao-tma | https://github.com/jin-cao-tma | profile-discovery | `FA3-DONOR-JIN-CAO-TMA-001` |
| https://github.com/yimin-pan | https://github.com/yimin-pan | profile-discovery | `FA3-DONOR-YIMIN-PAN-001` |
| https://chufengxiao.github.io/SketchHairSalon/ | https://chufengxiao.github.io/SketchHairSalon/ | research-project | `FA3-DONOR-SKETCHHAIRSALON-001` |
| https://github.com/topics/hair-color | https://github.com/topics/hair-color | topic-discovery | `FA3-DONOR-GITHUB-TOPIC-HAIR-COLOR-001` |
| https://github.com/deepmancer | https://github.com/deepmancer | profile-discovery | `FA3-DONOR-DEEPMANCER-001` |

## Boundaries

- GitHub profile, organization and topic pages are **discovery indexes only**; their child repositories are not recursively admitted.
- Repository/project registration does not copy code, weights, datasets or assets and does not install dependencies.
- No model, provider, hosted service, MCP endpoint or runtime is admitted by this intake.
- License & Rights, provenance, Security, Software Coexistence, Hardware Safety/model-runtime review and Universal Capability Access remain mandatory before material reuse.
- Upstream GPU/CUDA requirements may be studied as references but may not replace FA3 CPU-only viability or the Host Resource Broker / Model Router authorities.
- This intake does not create an application donor usage edge; any later adoption must register an explicit usage edge.

## Relationship to Shared Hair & Groom Fabric

The open Shared Hair & Groom Fabric work is separate from this registry intake. These newly registered references are not consumed by that pending branch unless a later, separately approved adoption/reconciliation explicitly creates usage edges.

## Gate-driven reconciliation

The first full PR gate pass correctly failed closed because the previous serialized donor-intake regression pinned the global registry to exactly 1405 entries and the unified release projection still described the pre-intake registry blob and release surface.

This branch therefore makes the prior intake regression append-only safe while preserving its own delta result at 1405, and regenerates the existing unified release projection for the 1421-entry registry. This reconciliation adds no capability, architectural authority, provider/runtime admission or donor usage edge.
