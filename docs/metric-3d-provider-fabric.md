# CAP-032 Metric 3D Reconstruction provider fabric

A CAP-032 — **Metric 3D Reconstruction** — az FA3-ban provider-neutral képesség. A képesség current-host lezárása nem függhet egyetlen külső Python/CUDA könyvtár telepíthetőségétől.

## Core current-host proof

A core proof primitív neve:

`metric_3d_reconstruction`

A proof a már admitted Bforartists/Blender geometry kernelt használja, és valódi rekonstrukciós műveletet hajt végre:

1. nyolc metrikus 3D pontból pontkészletet hoz létre;
2. convex-hull mesh-t rekonstruál;
3. ellenőrzi a nem üres topológiát;
4. ellenőrzi az egységkocka 1×1×1 kiterjedését;
5. ellenőrzi az 1.0 térfogatot.

Ez a proof **nem** állít differenciálható renderelést, neural reconstructiont vagy provider-specifikus GPU runtime PASS-t.

## Provider szerepek

- **Open3D — FA3-PROVIDER-OPEN3D-001**: preferált általános rekonstrukciós, registrációs, pontfelhő- és geometriai provider.
- **Kaolin — FA3-PROVIDER-KAOLIN-001**: preferált differenciálható/neural 3D provider.
- **PyTorch3D — FA3-PROVIDER-PYTORCH3D-001**: támogatott kompatibilitási/reference provider; saját source-build és current-host admission gate-je megmarad.
- **nvdiffrast — FA3-PROVIDER-NVDIFFRAST-001**: alacsony szintű differenciálható raster backend, kizárólag research/evaluation scope-ban, amíg a licencfeltétel külön production használatot nem engedélyez.

## Provider selection

Provider-választás csak typed job alapján történhet. Nincs silent provider-, GPU→CPU- vagy cloud fallback. Accelerator használat esetén a Host Resource Broker marad az admission, placement, reservation és lease authority.

A `FA3-3D-GEOM-001` marad az egyetlen geometry semantic authority, a DCC/final-asset authority pedig változatlan.

## Closure semantics

A FULL-429 globális preflight:

- **nem** követel PyTorch3D importot;
- **nem** követel Kaolin/Open3D importot;
- megköveteli a core geometry runtime-ot a CAP-032 provider-neutral proofhoz;
- a specializált provider runtime-okat külön, provider-specifikus gate-ek promótálják.

Ez megszünteti azt a hibás helyzetet, amelyben egyetlen opcionális CUDA extension blokkolta mind a 429 current-host kötelezettség végrehajtását.
