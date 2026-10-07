# Animation / character-motion donor intake + global access reconciliation — 2026-10-03

## Owner-marked intake

The owner supplied 29 URLs with an explicit `donornak` marker. The repeated `ai-animation-generator` topic URL occurs three times, so intake normalizes the batch to **27 unique exact source identities**.

Published-parent registry used for the intake:

- parent main: `0284f0ae4d2609b1e46557414481b1062ac0aafc`
- parent registry blob: `50580a9f3082161a3317383baa3e18879e98187e`
- parent registry entries: **1357**
- resulting entries: **1384**
- capability baseline: **175**
- capability delta: **0**
- authority delta: **0**

All 27 records are `ACCEPTED_REFERENCE`. This intake does not import code, weights, datasets, binaries or assets; it does not admit a provider/model/runtime and creates no usage edge.

## Source classes

The batch contains GitHub topic discovery views, organization/profile discovery indexes, concrete repositories and research/project pages spanning:

- image/reference driven character animation;
- face and pose animation;
- sprite/2D animation;
- interactive animation;
- character replacement and motion transfer;
- 3D text-to-motion and constrained motion;
- animation blending/retargeting and DCC handoff.

Organization/profile/topic records are discovery indexes only. Child repositories are not recursively admitted.

## HY-Motion hard boundary

`Tencent-Hunyuan/HY-Motion-1.0` is registered as a restricted reference. Its observed upstream `License.txt` states that the agreement does not apply in the European Union, United Kingdom or South Korea and limits the license to its defined Territory.

FA3 therefore:

- does **not** admit HY-Motion code, weights or runtime through this intake;
- does **not** use proxy/VPN/foreign-host/artifact-relocation techniques to bypass the restriction;
- does not use outputs for model training where upstream terms prohibit it;
- marks the associated capability need as requiring a global substitute before any restricted material adoption.

The replacement is capability-level, not vendor-level: an independently rights-cleared donor combination or FA3-native implementation must provide the same FA3 function without donor-specific geographic exclusion.

## Registry-wide consequence

The owner subsequently required this interpretation to apply to the **entire donor list**. The same change therefore binds the registry to `FA3-UNIVERSAL-CAPABILITY-ACCESS-POLICY-001` and introduces a retroactive audit/gate over all current and future donor records.

The structural audit is not a claim that every donor is legally cleared. Unknown/unverified rights remain fail-closed for material adoption.

## Exact-head verification note

This intake is merge-eligible only when donor serialization, application-donor inventory, reuse/release projection and permanent canonical checks all pass on the same current PR head; earlier-SHA PASS results are not promotion evidence.
