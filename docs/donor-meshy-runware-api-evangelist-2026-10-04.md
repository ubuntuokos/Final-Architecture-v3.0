# FA3 Meshy / Runware / API Evangelist donor intake — 2026-10-04

## Owner marker

The owner explicitly marked 10 URLs as `donornak` on 2026-10-04. All ten are preserved in this batch's provenance.

## Cross-intake nonduplication

Before #676 was created, **PR #675** had already registered the exact source `https://github.com/api-evangelist` as the planned identity `FA3-DONOR-API-EVANGELIST-ORG-001`.

Therefore #676 does **not** create a second API Evangelist donor mutation. It records the submitted URL as cross-intake provenance and reuses #675:

- existing intake: **#675**
- existing head observed during reconciliation: `4635a980ccf5c8291bb54d608953b6cd5faf128e`
- disposition: `REUSE_EARLIER_PENDING_CANONICAL_INTAKE_NO_DUPLICATE_MUTATION`

This batch therefore contributes **6 new canonical identities**, not 7.

## Canonicalization

The 10 owner-submitted URLs are handled as:

- 9 URLs in this PR's donor mutation scope;
- 1 exact URL delegated to the earlier #675 intake;
- the four filtered Meshy topic views collapse to one `github:topics/meshy` identity while every exact submitted URL remains preserved as provenance.

Planned new identities in #676:

1. `FA3-DONOR-GITHUB-TOPIC-MESHY-001`
2. `FA3-DONOR-MESHY-DEV-MESHY-GUIDE-001`
3. `FA3-DONOR-MESHY-DEV-ORG-001`
4. `FA3-DONOR-GITHUB-TOPIC-AI-3D-MODEL-GENERATOR-001`
5. `FA3-DONOR-RUNWARE-ORG-001`
6. `FA3-DONOR-GITHUB-TOPIC-RUNWARE-001`

Published-main duplicate search found no current canonical registry record for these six identities at parent main `df24cb9d1fa2413b08c8d47461bdb2db799585f6`.

## FA3 reference value

Reference-only discovery areas include:

- AI-assisted 3D generation, text/image-to-3D, texturing, remeshing, rigging/animation and export workflow patterns;
- 3D-generation API/agent integration and provider-neutral job/progress/result contracts;
- media-generation SDK, CLI, ComfyUI and MCP integration patterns from Runware-related discovery;
- tutorial/manual integration candidates where Meshy Guide workflows map to existing FA3 capabilities.

The API Evangelist governance/discovery source remains covered by #675 and is not duplicated here.

## Authority and safety boundaries

This registration does not:

- create a new FA3 application, provider, model, engine, runtime or architectural authority;
- recursively admit repositories listed by a topic or organization page;
- install or fetch source, models, assets, SDKs or external services;
- create usage edges;
- override Model Router, Host Resource Broker, Hardware Safety, Software Coexistence, License & Rights, Security Governance or Current Host gates;
- override the CPU-only baseline or display-GPU AI policy;
- change the fixed capability baseline of **175**.

Any later material adoption requires exact provenance, License & Rights review, security review, Software Coexistence review, Hardware Safety/model-runtime review where relevant, correct shared/application-layer placement and an explicit typed canonical donor usage edge.

## FIFO waiting state

Parent published main: `df24cb9d1fa2413b08c8d47461bdb2db799585f6`

Parent registry blob: `1362d75186c6da74e5cf947fdf0b8867d462636a`

Parent entry count: **1427**

Parent-relative proposed count for the six #676 identities: **1433**

The API Evangelist count delta belongs to #675 and is deliberately excluded from #676.

This PR is intentionally staged as a **FIFO waiting donor intake**. The central registry is not modified while the rolling five-slot active window is full. Pending identities are therefore **not canonical planning inputs**.

Canonical gate evidence on #676 reported:

- active donor PRs: #651, #657, #663, #664, #671
- waiting donor PRs ahead of #676: #672, #673, #675
- next finalizable active PR: #671

When #676 is admitted into the active window, it must be reconciled against the then-current published main, the six local identities appended without losing intervening donor records, #675 reuse revalidated, counts/tests regenerated, and exact-head gates passed before finalization.
