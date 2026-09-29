# OpenAL / OpenMAX / OpenMax / HEIF donor curation — 2026-09-29

This capture extends the **existing** canonical `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`. It does not establish a second registry, install or promote any upstream runtime, change a model/provider authority, or alter the fixed **175-capability baseline**.

## Source identities and individually inspected projects

| User-supplied entry | Kind | Individually inspected upstream(s) | FA3 reuse boundary |
| --- | --- | --- | --- |
| [kcat](https://github.com/kcat) | Discovery profile | [OpenAL Soft](https://github.com/kcat/openal-soft), [Alure](https://github.com/kcat/alure) | CPU-capable OpenAL 3D audio, HRTF, EFX, streaming and caching patterns. Integrate only through existing FA3 Audio Fabric and existing hardware/runtime governance; avoid global device-configuration collisions. |
| [OpenAL Haskell topic filter](https://github.com/topics/openal?l=haskell&o=asc&s=updated) | Dynamic discovery query | No automatic mass enrollment | Optional language bindings / FFI patterns, not a requirement that FA3 run Haskell. |
| [openmaxai](https://github.com/openmaxai) | Discovery organization | [openmax-agent-sdk](https://github.com/openmaxai/openmax-agent-sdk), [hxa-connect-sdk](https://github.com/openmaxai/hxa-connect-sdk) | Agent protocol, authenticated reconnect, heartbeat, gap reconciliation, inbox dedup, agent/thread collaboration; FA3's central Director/Workforce, federation, addressing, Secret Broker and Model Router remain authoritative. |
| [nikita-petrashen](https://github.com/nikita-petrashen) | Discovery profile | [openmax](https://github.com/nikita-petrashen/openmax) | Extreme-value open-set classifier/unknown-class scoring; **not** OpenMAX multimedia IL, **not** OpenMax AI workspace. Repository has no observed root license; reference-only until source rights are verified. |
| [openmax-server](https://github.com/openmax-server) | Discovery organization | [server](https://github.com/openmax-server/server), [docs](https://github.com/openmax-server/docs) | MAX/TamTam **messenger** server and protocol, unrelated to OpenMAX IL. Privacy, security, rights and actual relevance must be reviewed before any communication connector decision. |
| [OpenMAX IL C++ topic](https://github.com/topics/openmax-il?l=c%2B%2B) | Dynamic discovery query | No automatic mass enrollment | Legacy multimedia/codec interface compatibility research. Do not assume current Linux support or direct codec acceleration. |
| [Intel omxil_core](https://github.com/intel/omxil_core) | Individual repository | Archived Intel OpenMAX IL/VA-API reference | No root license found in inspected root; no maintained-runtime or distribution assumption. Prefer existing FFmpeg/MLT/Khronos-compatible interchange where applicable. |
| [Nokia HEIF](https://github.com/nokiatech/heif) | Individual repository | HEIF ISO-BMFF reader/writer / image-sequence reference | **Nokia HEIF License 2.1 restricts the licensed field to non-commercial evaluation, testing and academic research.** Source copying, commercial embedding, redistribution and codec-patent rights must not be inferred. Reference-only pending legal review. |
| [nokiatech](https://github.com/nokiatech) | Discovery profile | Nokia HEIF above | Source-specific terms; not a blanket licensing or vendor-dependency approval. |
| [HEIC C](https://github.com/topics/heic?l=c&o=asc&s=updated), [HEIC Go](https://github.com/topics/heic?l=go), [HEIC converter HTML](https://github.com/topics/heic-converter?l=html) | Three distinct dynamic search filters | No automatic mass enrollment | Container/codec adapter and import/export UX research for existing Photo/Image Studio and Production Import & Migration Fabric. |

The 12 user-supplied URLs and seven additional, individually inspected project URLs are captured as **19 unique source-normalized entries**; profiles and topic-filter URLs remain discovery-only. The separate repository records enable targeted Reuse Discovery without enrolling every project from an account or live topic query.

## Source/license observations (not legal clearance)

- OpenAL Soft describes LGPL 2 or later, with separately licensed bundled components and HRTF data; Alure has a Zlib-style root license.
- OpenMax AI HXA Connect SDK declares MIT; `openmax-agent-sdk` has no root license in the inspected repository tree. Do not infer rights from an npm package or README alone.
- `openmax-server/server` and `openmax-server/docs` declare BSD-3-Clause in repository metadata. Messaging protocol, platform policy, privacy, access control and source rights still need review.
- Intel `omxil_core` is archived and has no observed root license. Nokia's custom HEIF terms expressly restrict permitted use; codec-patent rights are separate.
- Topic/profile pages are discovery indexes, not code donors and not proof of license or project suitability. Each future source must be separately normalized, checked and assessed.

## FA3 planning and admission boundaries

1. Reuse Discovery queries the canonical registry and merges by normalized source; discovery indexes never automatically enroll every result.
2. Keep the fixed 175 capabilities, dynamic provider count, sole central HRB/Model Router, central agent addressing, Software Coexistence and Host Non-Interference. No parallel audio, messaging, media, model or provider authority.
3. Preserve generic Linux/CPU-only execution and `0..N` optional accelerators. Device and display-GPU allocation requires current Hardware Audit and explicit policy; no silent fallback, vendor pin or global audio-device override.
4. Preserve existing original image/audio/video projects and bidirectional import/export admission rules; codec format compatibility, encoder availability, patent status and project roundtrip are independent checks.
5. These 19 entries are **CANDIDATE**, metadata-only, non-authoritative, auto-fetch/install/import/provider/model selection disabled. No physical current-host PASS or commercial source reuse is claimed by this curation PR.
