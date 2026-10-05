# Owner-marked GGUF, Comfy and codec reference intake (2026-09-30)

## Provenance, scope and duplicate handling

The owner supplied the same initial eight sources multiple times and expanded that group to twelve distinct URLs. Treat this as **one** explicitly `donornak:`-marked registration batch, not three registrations. Pinned parent main: `5bea571f5e79f2e42f6a4d4445656556529c534a`; the published registry contained 1221 entries with a fixed capability baseline of 175. All twelve normalized source keys were absent in that published registry at intake review.

| Owner's exact URL | Reference identity | Reference-only restriction |
| --- | --- | --- |
| https://github.com/topics/gguf | `github:topics/gguf` (GITHUB_TOPIC) | Dynamic discovery index only; listed child repos are not registered or admitted. |
| https://github.com/topics/gguf-models | `github:topics/gguf-models` (GITHUB_TOPIC) | Dynamic discovery index only; listed child repos are not registered or admitted. |
| https://github.com/city96/ComfyUI-GGUF | `github:city96/comfyui-gguf` (GITHUB) | Concrete repo metadata only; source copying requires license/provenance/security/coexistence review. |
| https://github.com/IBM/gguf | `github:ibm/gguf` (GITHUB) | Concrete repo metadata only; source copying requires license/provenance/security/coexistence review. |
| https://github.com/huggingface | `github:huggingface` (GITHUB_ORGANIZATION) | Dynamic discovery index only; listed child repos are not registered or admitted. |
| https://github.com/calcuis | `github:calcuis` (GITHUB_PROFILE) | Dynamic discovery index only; listed child repos are not registered or admitted. |
| https://github.com/topics/gguf?l=go&o=asc&s=stars | `github:topics/gguf?l=go&o=asc&s=stars` (GITHUB_TOPIC) | Dynamic discovery index only; listed child repos are not registered or admitted. |
| https://github.com/mitjafelicijan | `github:mitjafelicijan` (GITHUB_PROFILE) | Dynamic discovery index only; listed child repos are not registered or admitted. |
| https://github.com/orgs/Comfy-Org/repositories | `github:comfy-org` (GITHUB_ORGANIZATION) | Dynamic discovery index only; listed child repos are not registered or admitted. |
| https://github.com/Comfy-Org/desktop | `github:comfy-org/desktop` (GITHUB) | Archived historical source; explicitly superseded upstream by Comfy-Org/Comfy-Desktop, which is not registered by this batch. |
| https://github.com/topics/codec-evaluation | `github:topics/codec-evaluation` (GITHUB_TOPIC) | Dynamic discovery index only; listed child repos are not registered or admitted. |
| https://github.com/topics/quicktime?l=swift | `github:topics/quicktime?l=swift` (GITHUB_TOPIC) | Dynamic discovery index only; listed child repos are not registered or admitted. |

## Source observations and admission boundaries

- `city96/ComfyUI-GGUF`: public non-archived Apache-2.0 GitHub repository at review; its quantized ComfyUI diffusion/DiT and text-encoder loading patterns are potential **reference only**, not a ComfyUI add-on installed by FA3.
- `IBM/gguf`: public non-archived Apache-2.0 GitHub repository at review; Granite-to-GGUF conversion, test and CI patterns are candidates for Model Manager reference review, not model/provider admission.
- `Comfy-Org/desktop`: **archived**, upstream repo description points to `https://github.com/Comfy-Org/Comfy-Desktop`. Original marked archived URL is preserved. The unmarked replacement is context only, NOT a thirteenth donor.
- `huggingface` and `Comfy-Org`: organization indexes; `calcuis` and `mitjafelicijan`: profile indexes. Mentioning relevant listed repositories does not admit them.
- The GGUF base and Go-filter/sort topic URLs are separate requested discovery views, not permission to harvest either topic's child repositories. All topic listings are dynamic, have no aggregate source-code license, and require per-project review.
- `codec-evaluation` and filtered Swift `quicktime` topic views are media reference discovery only. No new codec implementation, production performance assertion, or provider admission is claimed.

## FA3 safety and authority

This PR stages twelve new reference identities: 1221 → **1233** derived from actual entry array length, not a manually incremented external counter. Existing 1221 entries must stay unchanged, in the same relative order. Capability baseline **175**, zero new architectural authority. CPU-only viable and vendor-neutral Hardware Audit remain required. HRB retains sole compute placement/lease authority; Model Router retains sole model route. No display-GPU automatic recruitment, software interference, unreviewed download, implicit model selection, source-code adoption or current-host proof. Any later adoption requires a separately owner-approved plan and license, provenance, security, Hardware Safety, Software Coexistence and actual physical-evidence gates.

Delta: `canonical/deltas/FA3-DONOR-GGUF-COMFY-CODEC-2026-09-30.json`. Remain draft until exact-HEAD Donor Serialization, Reuse Discovery, Permanent Canonical, Release Projection Reconcile, Application Donor Inventory, capability-175 and global mandatory GitHub checks PASS; recheck exclusive donor slot before merge.
