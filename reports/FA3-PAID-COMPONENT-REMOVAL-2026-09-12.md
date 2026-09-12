# FA3 paid-component removal — 2026-09-12

Status: **CANONICAL CLEANUP / FREE-ONLY BASELINE**  
Policy: `FA3-FREE-SELF-HOSTED-ONLY-001`  
Gate: `FA3-FREE-ONLY-GATESET-001`

This report lists payment-bearing FA3 provider routes removed from active architecture. Tombstone provider records may remain only for provenance and regression prevention; tombstones are not active, routable, deployable, or promotable.

| Item | Previous FA3 surface | Removal | Retained free replacement / outcome |
|---|---|---|---|
| OpenAI Codex | `FA3-PROVIDER-CODEX-001` + current-host/runtime adapter surfaces | Removed from active FA3; runtime/service/current-host integration deleted; provider retained only as inactive tombstone/decommission guard | Existing provider-neutral `FA3-AGENT-EXEC-001` and local/self-hosted developer-agent providers |
| Kling AI | `FA3-PROVIDER-KLING-001` | Removed from active video provider registry; inactive tombstone only | Open/self-hosted video providers through `FA3-VIDEO-001` |
| ByteDance/BytePlus Seedance | `FA3-PROVIDER-SEEDANCE-001` | Removed from active video provider registry; inactive tombstone only | Open/self-hosted video providers through `FA3-VIDEO-001` |
| MiniMax H3 | `FA3-PROVIDER-MINIMAX-H3-001`, hosted service access, runtime admission, H3 adapters/current-host surfaces | Removed from active FA3; provider-specific runtime/service artifacts deleted; tombstone only | Provider-neutral `FA3-MMG-CONTEXT-IR-001` and `VideoGenerationIR` retained |
| NVIDIA NIM for SD3.5 | `FA3-PROVIDER-SD35-NVIDIA-NIM-001` | Removed from active Stability portfolio; inactive tombstone only because production use requires NVIDIA AI Enterprise | Local/free Stability routes remain subject to normal model/license admission |
| Stable Audio hosted API / Large route | `FA3-PROVIDER-STABLE-AUDIO-3-001` remote API/enterprise Large route | Paid route removed and fail-closed | Small Music, Small SFX and Medium local routes retained subject to model/license/runtime admission |
| Obsidian Sync | Obsidian provider optional sync surface | Removed/forbidden | Local Obsidian desktop + local Markdown vault retained |
| Obsidian Publish | Obsidian provider optional publish surface | Removed/forbidden | Local Obsidian desktop + local Markdown vault retained |

## Admission rule

A route is denied when it requires any of the following: paid subscription, PAYG billing, purchased credits, paid seat, paid hosted API, mandatory commercial fee, or production enterprise license. Free trials, promotional credits, and finite free quotas do **not** qualify as durable free routes.

Capability count remains **143**. No new architectural authority is introduced.
