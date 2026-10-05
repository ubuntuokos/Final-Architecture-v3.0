# CFA3 Character Platform / Human Studio — approved donor-complete final plan

Date: 2026-10-05
Conversation lineage: `conversation:cfa3-character-platform-human-studio-20261005`

## Approved architecture

The CFA3 Character Platform is a species-independent character/creature platform. Human Studio is a Human workspace/profile, not a separate human-only engine.

The approved plan combines:
- Character / Creature Recipe as canonical character authority;
- Morphological Primitive Library + Morphology Graph;
- Shared Creature Preset Library;
- Hybridization & Mutation Grammar;
- Shared Anatomy Data & Ontology Fabric and biomechanics;
- 2D, 3D and Hybrid authoring and representation;
- existing Character Motion & Animation / performance-capture fabrics;
- shared hair/groom and wardrobe capabilities;
- Character Interchange IR and round-trip external bridges;
- Blender/Bforartists, Poser, Unreal Engine and MetaHuman interoperability;
- CFA3 Plugin & Extension Fabric extension points for future species, tools, rigs, deformers, capture providers, formats and DCC bridges.

## Five-layer donor reuse boundary

1. Parametric character / morphology / preset patterns.
2. Anatomy-aware representation, fitting and character construction.
3. Rigging, motion, facial and reconstruction patterns.
4. Interchange / DCC / external-character bridge patterns.
5. Plugin / extension lifecycle and future expandability patterns.

External sources remain reference-only until separate usage-edge, License & Rights, security, Software Coexistence, Hardware Safety, provider/runtime and physical Current Host gates authorize material adoption.

## Processed donor/reference set newly requiring canonical registration

- https://github.com/makehumancommunity/makehuman
- https://github.com/makehumancommunity/makehuman2
- https://github.com/makehumancommunity/mpfb2
- https://github.com/Upliner/CharMorph
- https://github.com/animate1978/MB-Lab
- https://github.com/vchoutas/smplx
- https://github.com/yfeng95/DECA
- https://dev.epicgames.com/documentation/metahuman/metahuman-documentation
- https://www.posersoftware.com/documentation/13/HTML/Poser_Reference_Manual/OtherApps/PoserPython/How_Python_Integrates_with_Poser.htm

## Invariants

- Registration status: `ACCEPTED_REFERENCE`.
- Capability baseline remains 175.
- Provider count remains dynamic.
- No architectural authority is transferred to any donor.
- No source code, model, asset, dataset or dependency is automatically imported, installed or activated.
- SMPL-X and DECA remain non-commercial/research-license constrained unless separately licensed.
- MB-Lab and CharMorph code/data/output licensing requires separate component-level review.
- MakeHuman/MPFB2 code and asset licenses are tracked separately.
- MetaHuman and Poser are external reference/interop targets, not CFA3 authorities.
- Current Host promotion is not claimed by this plan or donor registration.
