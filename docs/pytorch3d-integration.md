# PyTorch3D integráció az FA3-ban

A `facebookresearch/pytorch3d` a `FA3-PROVIDER-PYTORCH3D-001` alatt kötelezően támogatott referencia és feltételes helyi végrehajtó provider. Nem új 3D-rendszergyökér: a `FA3-DIFFERENTIABLE-3D-001` nem-root alprofil a `FA3-3D-GEOM-001` egyetlen canonical geometry authority alatt, és kizárólag a már létező `CAP-032 — Metric 3D Reconstruction` képességet vetíti ki.

## Aktuális admission állapot

- Canonical és executable reference gate: `PASS`.
- Forrás: `facebookresearch/pytorch3d@0a7d4c1a171e8b768c63f15b17564f9ad495f49b`.
- Licenc: BSD-3-Clause.
- Runtime: `PENDING_CURRENT_HOST`.
- Production promotion: nincs engedélyezve.
- Capability-k száma: változatlanul 143.
- Új architectural authority: 0.

Az upstream `INSTALL.md` legfeljebb PyTorch 2.4.1-et dokumentál, az NVIDIA CI pedig Python 3.12 + PyTorch 2.4.1 + CUDA 12.1 kombinációt futtat. Az upstream karbantartó az #2046 issue-ban megerősítette, hogy aktuális hivatalos binárisok hosszú ideje nem készülnek. Emiatt a jelenlegi FA3 politika `SOURCE_BUILD_ONLY`.

Az `@stable` név létezik, de egy régi `V0.7.8` tagre mutat; emiatt sem floating `main`, sem `stable`, sem Conda/nightly, sem `pytorch3duniverse`, sem ellenőrizetlen közösségi wheel nem használható production identityként.

## Végrehajtási határok

A provider nem birtokolhat geometry-, DCC-, workflow-, MCP-, model-registry-, model-routing-, host-resource-, device-routing-, security- vagy evidence-authorityt. A Bforartists/Blender-kompatibilis DCC-réteg marad a scene és final asset authority. A PyTorch3D csak a következő typed job surface végrehajtója lehet:

- `3d.mesh.fit`
- `3d.mesh.render`
- `3d.pointcloud.render`
- `3d.camera.optimize`
- `3d.volume.marching-cubes`
- `3d.geometry.convert`

GPU-végrehajtáshoz Host Resource Broker lease, UUID + PCI BDF stabil identity, egyetlen látható compute accelerator és explicit CUDA-kérés kell. A runtime ordinal csak ideiglenes leképezés, nem canonical identity. Display GPU, másik GPU, CPU vagy cloud irányába nincs automatikus fallback.

## Source build

A builder nem tölt le forrást vagy függőséget. Előfeltételei:

1. az exact commitra checkoutolt, integritásvizsgált forrás;
2. külön pip venv a megfelelő Torch/torchvision párral;
3. a Torch által használt CUDA major.minor verzióval egyező side-by-side build toolkit;
4. érvényes HRB build/accelerator receipt;
5. telepített Syft az SBOM előállításához.

Példa:

```bash
CUDA_HOME=/usr/local/cuda-12.8 \
  ./bin/fa3-pytorch3d-source-build.sh \
  --source-dir /path/to/pytorch3d \
  --venv /path/to/pytorch3d-venv \
  --wheelhouse /path/to/wheelhouse \
  --hrb-receipt /path/to/hrb-build-receipt.json \
  --receipt /path/to/pytorch3d-build-receipt.json \
  --sbom /path/to/pytorch3d-wheel.cdx.json \
  --provenance /path/to/pytorch3d-build-provenance.json
```

A builder exact source pint, tiszta tracked source tree-t, izolált venvet, CUDA ABI-egyezést és HRB-ből származó accelerator-architektúrát/build thread budgetet követel. Az eredmény egy SHA-256-tal azonosított wheel, SBOM és build provenance.

## Current-host E2E

A source-built wheelt előbb a megadott izolált venvbe kell telepíteni `--no-index --no-deps` módban, majd az alábbi collector futtatható:

```bash
./bin/fa3-pytorch3d-current-host.sh \
  --source-dir /path/to/pytorch3d \
  --venv /path/to/pytorch3d-venv \
  --wheel /path/to/pytorch3d.whl \
  --sbom /path/to/pytorch3d-wheel.cdx.json \
  --provenance /path/to/pytorch3d-build-provenance.json \
  --build-receipt /path/to/pytorch3d-build-receipt.json \
  --hrb-receipt /path/to/hrb-runtime-receipt.json
```

A collector valódi CUDA-extension importot, mesh/pointcloud műveletet, Chamfer-gradienst, mesh rasterizálást, kamera-transzformációt, marching cubes műveletet, OBJ/PLY roundtripet és Pulsar renderelést futtat. Negatív teszt igazolja, hogy hibás CUDA-eszköznél fail-closed hiba keletkezik, és a hívó aktív eszköze nem változik. A probe subprocess kilépése után a collector ellenőrzi, hogy a folyamat GPU-contextje megszűnt.

A `fa3-pytorch3d-current-host.yml` workflow csak manuálisan indul a `[self-hosted, linux, x64, fa3-current-host]` runneren. A receipt megszületéséig a `CAP-032` globális runtime státusza változatlanul `PENDING_CURRENT_HOST`; reference vagy dokumentumalapú PASS nem promóció.
