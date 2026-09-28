# FA3 – 3DCoat-donorötletek alkalmazásokon átívelő megvalósítási terve

**Dátum:** 2026-09-28  
**Állapot:** TERVEZET / kizárólag tervezési dokumentum; nem kanonikus döntés, nem új authority, nem implementáció, nem runtime- vagy current-host PASS.  
**Cél:** a 3DCoat és három különálló nyilvános 3DCoat/Blender donor lehetséges mintáit a meglévő FA3 alkalmazásaira vetíteni, duplikált architektúra helyett.  
**Kiinduló main:** ab1d15b6a886b7d46999b3c56e7b0f39114b4454; a tényleges implementáció előtt újraellenőrzendő. Ezen a commiton a capability-model 175; számot nem változtatunk automatikusan.

## 0. Kötelező felderítés és forrásjegyzék

Minden implementációs PR előfeltétele az aktuális FA3-REUSE-DISCOVERY-001 lekérdezése, a donor registry és Khronos source family ellenőrzése, a meglévő capability, provider, alkalmazás, GUI, contract és action keresése, és az erre épített dokumentált gap analysis. A repo aktuális canonical állapota elsőbbséget élvez e tervvel szemben.

Jelenleg megvizsgált konkrét források:

| Forrás | Újrahasznosítható minta | Határ |
| --- | --- | --- |
| [3DCoat hivatalos oldal](https://3dcoat.com/) és [funkciók](https://3dcoat.com/features/) | voxeles és felületi modellezés, retopológia, UV, PBR, procedurális anyagok, 2026-os GPU-node rendszer, térfogati rács, Python/Core API | kereskedelmi/zárt; munkafolyamat- és opcionális külső alkalmazás referencia, nem szabad forráskód |
| [AndrewShpagin/io-coat3d](https://github.com/AndrewShpagin/io-coat3d), megfigyelt: 15b51ab8d1bfe9937fb6ecf967581c9a239b12b3 | oda-vissza fájlcsere, objektum-/anyagazonosítók, UV/UDIM/PBR csatornák és célzott textúrafrissítés | az ellenőrzött forrásfájl GPL-2.0-or-later fejlécet tartalmaz; átvétel külön licenc- és függőségvizsgálattal |
| [Blender/blender-addons io_coat3D](https://github.com/blender/blender-addons/tree/main/io_coat3D), megfigyelt repó HEAD: b42d68627734cb18af0e6f41537063984313a284 | független adatcsere-referencia és kompatibilitási tesztforrás | GPL-2.0-or-later a vizsgált __init__.py fájlban; a két AppLinket nem szabad automatikusan párhuzamosan telepíteni |
| [LiamSmyth/LKS_3DCTools](https://github.com/LiamSmyth/LKS_3DCTools), megfigyelt: 8b69798f9ead57068aa8e53e7d05f45a947439c1 | radiális menü, négy műveleti hatókör, közös objektumok deduplikációja, tömeges műveletek, referenciaalapú geometriai részletesség, profilok, schema migráció, billentyűkonfliktus-felismerés | README informális felhasználási engedélye nem tisztázott forráslicenc; LKS-kódmásolás tiltott, amíg a jogok nincsenek rendezve |

Donor állapot: PR [#478](https://github.com/ubuntuokos/Final-Architecture-v3.0/pull/478) négy külön forrást tesz CANDIDATE státuszba; PR [#477](https://github.com/ubuntuokos/Final-Architecture-v3.0/pull/477) két, részben átfedő forrást rögzít. **Beolvasztás előtt kötelező a két PR kanonikus forráskulcs szerinti összeegyeztetése; az egyik egyesítése után a másik nem írhatja felül a frissebb registryt vagy duplikálhatja a bejegyzéseket.** Ez a terv-PR a registryt nem módosítja, hanem mindkettőre hivatkozik.

Meglévő újrahasznosítási belépők:
- canonical/profiles/FA3-REUSE-DISCOVERY-001.json, docs/fa3-reuse-discovery.md;
- canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json, canonical/FA3-APPLICATION-DONOR-LINKS-001.json és canonical/FA3-AI-STUDIO-APP-CATALOG-001.json;
- canonical/contracts/FA3-VIDEO-TIMELINE-PROVIDER-CONTRACTS-001.json: typed/versioned operations, projektazonosság, idempotency key, destructive dry-run/diff/approval, mutation receipt;
- canonical/FA3-KHRONOS-ADAPTER-REGISTRY-001.json: glTF Validator, KTX, Vulkan/glslang/SPIR-V stb. mint már feltárt adapterek;
- OpenUSD/OpenSubdiv donorok a registryben: jelenet- és geometriai újrahasznosítás; kihasználásuk felülvizsgálandó, nem feltételezett telepített állapot;
- Bforartists az elsődleges DCC, ComfyUI/InvokeAI image, Natron/Gaffer VFX a curated app katalógusában; FA3 Video Editor / QuickClip / Story / Music / Character az alkalmazáskapcsolati deklarációkban;
- kizárólag a meglévő FA3 HRB, Model Router, MCP Gateway és evidence hatóságok szolgálhatnak engedélyezési és megfigyelési pontként.

## 1. Architekturális cél és határok

Négy **keresztalkalmazási képességcsoport** készüljön meglévő FA3-hatóságok alárendelt könyvtáraként, komponenseként és adaptereként, ne önálló, párhuzamos termékként:

1. **Interaction & Operation Adapter:** közös typed parancsleírók, paraméterek, kontextusfüggő parancsfelfedezés, radiális/keresős GUI-projekciók, parancsok hatókörének kiválasztása, jogosultság.
2. **Scoped Batch & Change Plan:** deduplikált elemlista, száraz próba, erőforrásbecslés, diff, végrehajtás, cancel, részleges hiba, receipt, undo/kompenzáció, checkpoint.
3. **Asset Graph Interchange Adapter:** explicit oda-vissza átadás verziózott manifesttel, natív projektreferencia, forrás/derivatív identitás, csak változott tartalom importja, ütközéskezelés és review.
4. **Domain-specific Procedural Recipe Adapter:** 3D/material/voxel, kép/VFX, audio és video műveletek *külön* típusos gráfjai; közös végrehajtási szabályok, de sem közös monolit node engine, sem új model/provider authority.

A UI nem futtat közvetlenül szabad szövegű tetszőleges parancsot. Az UI, agent, recorder és billentyű ugyanahhoz az engedélyezett, verziózott műveletazonosítóhoz fordul. AI-vezérelt lépések a meglévő Router → HRB → admitted provider láncon haladnak, és **nem** bővítik automatikusan a kijelölt modellek listáját. A teljesen automatikus / emberi jóváhagyásos / vegyes workflow-mód csak a meglévő jóváhagyási policy engedte műveletekre alkalmazható; destruktív vagy külső adatátadással járó feladat nem kap hallgatólagos engedélyt.

Tervezett szemantikus lánc:

    FA3 alkalmazás / GUI / jóváhagyott agent
      -> meglévő FA3 command/action és policy authority
      -> Typed OperationDescriptor + ProjectIdentity + Scope
      -> MutationPlan / DryRun / Diff / Approval
      -> HRB lease szükség esetén; AI esetén egyetlen Model Router
      -> megfelelő app/provider adapter (nem új authority)
      -> Asset Graph revízió + native project + receipt + rollback

Ez **illesztési terv**: a tényleges új osztályneveket és canonical recordokat a Reuse Discovery gap elemzése után kell kijelölni.

## 2. Munkacsomag A – egységes interakció, menük és műveletek

**Donorjel:** LKS JSON Schema v3, v1→v2→v3 migráció, per-app sparse binding override, négy scope (CURRENT/TREE/OTHER/ALL), radiális hierarchia, progress callback, hotkey-conflict minták.

### A1 – meglevő műveleti szerződésekre illesztés

Elvárt minimális OperationDescriptor-mezők: action_id; schema_version; title/help; application/capability; typed parameters; entity kinds; declared scope support; side_effect_class (READ_ONLY/REVERSIBLE/DESTRUCTIVE/EXTERNAL); project_identity; permissions; policy/admission reference; estimated_cost descriptor; hardware/backend requirements; async/cancel/undo support. A Video Timeline Provider meglévő strukturált műveleti szerződését újra kell használni, **nem** lehet azonos funkcióra második Video Command Bus.

Az adapter kizárólag engedélyezett action_id + paraméterek feloldását végezheti. Hiányzó parancs, nem támogatott paraméter, lejárt projektazonosság vagy jogosulatlan scope fail-closed.

### A2 – közös scope és batch

FA3-szintű scope-javaslat: SELECTED, DESCENDANTS, EXCEPT_SELECTED_SUBTREE, WHOLE_PROJECT, plusz az alkalmazás által explicit támogatott CUSTOM_FILTER. Domainadapter oldja fel a hatókört, stabil entitásazonosítóval és „shared backing resource” azonosítóval: ugyanazt a Bforartists geometriát, Krita shared layer assetet, egyetlen videós médiát vagy Asset Graph objektumot ne dolgozzuk föl többször. Ne keverjük a deduplikált adatfeldolgozást és a több előfordulás megjelenítését; azonos inputból eltérő, explicit paraméterezett változatokat külön munkaként kell kezelni.

Batch lifecycle: resolve → validate → estimate → dry_run → diff → approve → acquire_lease_if_needed → execute_checkpointed → receipt → commit, vagy cancel → compensation/rollback. Tömeges destruktív lépésnél részletesen megjelenített kiválasztás és kötelező jóváhagyás. Immutable idempotency key, artifact hash és input revision véd a véletlen duplafuttatás ellen. A recovery journal soha ne állítson be nem bizonyított PASS-t.

### A3 – többféle GUI-projekció és profil

Qt6/QML alapú, desktop-semleges GUI-komponens: hierarchikus radiális menü, parancskereső, parancs-paletta, paraméterpanel, tooltip és ugyanannak az action_id-nek a billentyű- vagy egérgesztus-bindolása. Wayland elsődleges; X11 támogatott; sem KDE-, sem GNOME-specifikus globális hook nem kötelező. Az elsőként beépíthető hostok a Bforartists adapter/Creative Studio és az FA3 Video Editor; natív menük kiegészítése, nem azok lecserélése.

Profil: verziózott deklaratív JSON, application_id, action_id és ritka user-overrides, migrációs lánc, .bak + temp-file + atomic rename, rollback, konfliktusriport. Nem írhatja felül egy futó külső alkalmazás konfigurációját: annak hivatalos API-ját használja, vagy csak bezárt alkalmazásnál végez explicit, mentett import/exportot. A profil nem tárolhat tokent vagy jelszót.

### A4 – biztonságos műveletrögzítő

A recorder kizárólag már tipizált és naplózható Command Bus eseményeket rögzíthet; nem keylogger, nem nyers képernyőrögzítés. Projekt- és fájlazonosítókat lehet paraméterezni; titkok, szabad szövegként beírt személyes adatok és clipboard nem kerülhetnek automatikusan receptekbe. Visszajátszás előtt dependency-resolution, scope diff és permission review; agent számára külön admission.

**Elfogadási példák:** Bforartists három objektumából a közösen használt meshen egyetlen tényleges változtatás; Krita két rétege esetén csak a kijelölt hatókör érintett; Video Editor timeline-művelet idempotens; inkompatibilis régi hotkey-séma backup után migrálódik vagy hibával, adatvesztés nélkül elutasításra kerül; letiltott destructive action agenten keresztül sem hajtható végre.

## 3. Munkacsomag B – Asset Graph-alapú alkalmazásközi oda-vissza adatcsere

**Donorjel:** két Blender–3DCoat Applink exchange-folder és material/texture refresh referencia. Első valós pilot: Bforartists → opcionális telepített 3DCoat → Bforartists. A 3DCoat *nem* kötelező FA3 dependency. Native Bforartists/Blender .blend, 3DCoat .3b, Krita .kra, Ardour session, FA3 project.fa3video és .fa3clip sértetlenül megmarad.

### B1 – típizált InterchangeManifest

Minimális mezők: schema_version, exchange_id, source_application, target_application, source_project_ref, source_revision, source_native_format, source_asset_ids, export_intent, approved_operations, asset_graph_parent_ids, per_artifact path+hash+media_type+size, coordinate_system/units, color_space, PBR channel mapping és UV/UDIM metadata ahol releváns, object/material identity mapping, expected_return_type, provenance, human_approval_reference, policy, external_app_version, adapter_version, timestamps, conflict_policy és receipt_ref.

Az Asset Graph tárolja az immutable snapshotot és a származtatott kapcsolatot. Az external return először staged/quarantine területre érkezik. A visszaírás háromutas összevetéssel vizsgálja az exportált revíziót, a közben módosított forrást és a külső eredményt: módosított eredeti projekt esetén felhasználói merge/rebase döntés, automatikus felülírás nélkül.

### B2 – biztonságos exchange transport

Csak felhasználó által jóváhagyott, projektre szűkített exchange-mappa és explicit Send/GetBack művelet. A forrásprogram saját megbízható AppLink útvonala opcionális adapter. A fájlfigyelés eseményjelző, nem automatikus felülírási authority: stabil/lezárt fájl, tartalmi hash és producer-receipt nélkül nem importál. Atomic manifest write, limited size/count, symlink/hardlink/path traversal/TOCTOU ellenőrzés, fájltípus validáció, sandboxos dekódolás, auditált törlés és kvóta. A globális home-könyvtárak figyelése és vak fájlrendezés tiltott. Nincs portütközés vagy AdGuardHome-módosítás.

### B3 – 3D adatfolyam és kompatibilitás

A Bforartists és külső 3DCoat pontos, elérhető formátumait runtime-probe határozza meg. A vendor Applink FBX-alapú mintája csak kompatibilitási referencia; ahol alkalmas és már admitted, OpenUSD vagy glTF/GLB csere használható. Khronos glTF Validator és KTX, illetve meglévő OpenUSD donorok felülvizsgálata szükséges, duplikált könyvtárbundle nélkül.

Minimum oda-vissza próbák: eltérő transzform és méter/mm egységek; nested collections/hierarchy; két UV set; UDIM 1001+; albedo/roughness/metallic/normal/emission/AO/alpha channel; színtér, csatornakonvenciók és normal-map orientation; mesh topology változás és material slots; forrás közbeni módosulás; stale manifest; hibás symlink; hiányzó/licenc nélküli 3DCoat. Támogatás csak az adott verzióval bizonyított alhalmazra állítható.

### B4 – általános célú, változásalapú adapter

Krita layered artwork → FA3 Video Editor; Bforartists render és kamera → FA3 Video Editor; Music Studio/Ardour audió és MIDI asset → Video Editor; Story/Screenplay approved beat/Shot → Video Editor; Character animation → Video Editor és Asset Graph. Az alkalmazásspecifikus export/projektséma marad a host tulajdona, a közös réteg csak identitást, revíziót, megállapodott hordozóformátumot, provenance-t, átvételi jóváhagyást és conflict policy-t egységesít.

**Elfogadási példák:** az érintetlen textúra nem kap új tartalmi revíziót; módosított forrás és visszaérkező állomány nem veszít adatot konfliktus esetén; path-traversal, symlink-escape vagy unsigned manifest elutasítva; 3DCoat hiánya mellett a teljes FA3 és más interoperabilitás tovább működik.

## 4. Munkacsomag C – domainenkénti procedurális receptek, minőségi szándék, előnézet

**Donorjel:** 3DCoat 2026.11 node-os anyag/maszk/volumetrikus minták, korai sculpt textúraelőnézet; LKS referencia-meshhez viszonyított részletesség, világkoordinátás tris/unit² és cél-poligonszám, módosító paraméterek megőrzése.

A meglévő ComfyUI/InvokeAI, Natron/Gaffer, Bforartists, OpenUSD, Khronos és FA3 Video/Audio komponensek adaptálása elsőbbséget élvez. Nem készül új, minden terület fölött álló node runtime. A közös rész csak a deklaratív recept-envelope: recipe_id/version, domain, input references/hashes, operator descriptors, deterministic parameters/seeds where supported, quality_intent, resource_intent, approval, provider capabilities, output refs, loss report, provenance.

**Domainadapterek:**
- 3D/Material: görbület, AO, magasság, maszk, kopás, anyagcsatornák, voxeles displacement; OpenUSD/glTF/KTX és adott rendererre fordítás, opcionális vendor-specifikus shader backend. 3DCoat NGL nem lesz FA3 canonical IR.
- Image/VFX: Krita layer/selection maszk, Gaffer/Natron/ComfyUI node recipe meglévő adaptereire fordított, verziózott workflow; nincs titkos/önkényes AI provider kiválasztás.
- Video: meglévő OTIO / Video Timeline Provider strukturált effektek, proxy/preview és approved render; projekt.fa3video az elsődleges, QuickClip teljes import export contractja megmarad.
- Audio/Music: MIDI normál audio-típusú assetként kezelendő; effektek/voice workflow meglévő provider interfészen; minőségi szándék csak a domain tényleges paramétereire fordítandó.
- World Generator / Character / VFX: eljárásos minták, rétegelt szennyeződés, ruha/bőr/surface maszkok, szikla/talaj/városrészek, dinamikusLOD- és attribútum-konverzió, de fizikai/tudományos megalapozottságot ne állítsunk egy látványalgoritmusról.

**Minőségi profilok:** „interactive-preview”, „approved-review”, „final-output” csupán felhasználói szándékcímkék. 3D-nél világmértékegységhez kötött sűrűség/target faces és error bound; képnél felbontás/color intent; videónál proxy/codec/bitrates és render-hűség; hangnál SR/bit depth/LUFS ahol releváns. Domain-specifikus mérőszámok nem közvetlenül összehasonlíthatók. Resource planner csak az HRB-nek továbbított igényeket becsüli, erőforrást önállóan nem foglal.

**Korai előnézet:** draft geometry / draft mask / draft composition -> preview artifact, provenance és „preview-not-final” jelzés. Nem kötelezünk UV-ra vagy final topologyra előnézetkor, de a végleges export figyelmeztet a hiányzó elfogadott lépésekre.

**Elfogadási példák:** ugyanabból a paraméterezett 3D-anyagreceptből két külön kimeneti backend konzisztens, vagy eltérést jelentő loss reporttal tér vissza; CPU-only backend mellett a kép- vagy metadata-recept nem omlik össze; hiányzó GPU-s backend esetén nem indul rejtett display-GPU / NPU felhasználás.

## 5. Munkacsomag D – speciális 3D, LOD és volumetrikus műveletek

D1. **Sculpt → retopo → UV → PBR:** az elsődleges DCC Bforartists; a 3DCoat opcionális külső feldolgozási út. Referencia mesh, kézi ellenőrzés, UV/UDIM/normal validáció, topology- és material-diff, original/high-poly megtartása. Az upstream AUTOPO → multires LKS-ben WIP; csak kísérleti minta, nem állítható kész FA3-funkciónak.

D2. **LOD és referenciaalapú geometriai minőség:** world-unit metadata nélkül tris/unit² érték nem elfogadható; rétegelt LOD parent-child lineage, maximal face budget, visszaállítható high-poly és független approximation/error report. OpenSubdiv CPU path és meglévő 3D Fabric/World Generator megoldások felülvizsgálata; GPU csak opcionális admitted backend.

D3. **Voxel és procedural volume:** CPU-only egyszerű referenciavoxel-műveletek, részletességi plafon, erőforrásbecslés; 3DCoat külső GPU node és voxel lattice csak explicit integráció mellett. Nyomtatásnál watertightness, units, wall thickness és manifold check; felhasználás előtt geometriai validáció, nem automatikus teherbírási állítás.

D4. **Kontextusfüggő symmetry/split/visibility:** LKS mode-aware symmetrize / masked split inspiráció; FA3 saját, jól meghatározott, bizonyított és undo-képes adapterei. Másolás helyett szerződés és tesztek. Instancing-aware scene traversal végtelen ciklus és dupla feldolgozás nélkül.

D5. **Procedurális, csempézhető minták:** 3×3 instanced seamless tile preview Character/World/VFX anyagokhoz; shared-source edit és eltérő instancing occurrence világos szétválasztásával.

**Első 3D end-to-end pilot:** Bforartistsben készített többobjektumos mintajelenet (köztük linkelt mesh és UDIM material), explicit 3DCoat Send, retopo/texturing, staged GetBack, quality/diff és approval, Bforartists native .blend + 3DCoat .3b megőrzése, Asset Graph receipt, majd egy jóváhagyott still/render átadása FA3 Video Editor projektbe. Ha 3DCoat nincs telepítve/admitted, OpenUSD/glTF import/export konformancia és Bforartists-only pilot fut; a vendor út „UNAVAILABLE”, nem hibaelfedő silent fallback.

## 6. Pontos alkalmazásmátrix és első közös használók

| Meglévő vagy tervezett FA3 alkalmazás | Első igény | Kapcsolódó csomag |
| --- | --- | --- |
| FA3 GUI / Control Center | egységes keresés, hotkey-profil és radiális Command Palette, elérhető műveletek | A |
| FA3 Video Editor (saját project.fa3video, saját timeline; MLT/FFmpeg) | typed command/dry-run, kötegelt clip/effect, külső asset return, preview és loss report | A+B+C |
| FA3 QuickClip (.fa3clip) | gyors scoped actions, approved clip/metadata átadás a Video Editorba | A+B |
| Story/Screenplay és Docs/Notes | approved scene/shot/asset átadás, AI-notes elkülönítés, script recorder csak typed actions | A+B |
| Music Studio/Ardour/LMMS | batch audio/midi, native session, video timeline handoff, domain-specific recipe | A+B+C |
| Bforartists / Blender | scene scope, mesh instance dedup, explicit 3DCoat AppLink, topology/material/LOD | A+B+C+D |
| Krita | layers/selection scope, safe profile, procedurális maszk és jóváhagyott layered handoff | A+B+C |
| Natron/Gaffer / VFX | typed graph-recipe projection, render/asset manifests, volumetric output import | B+C+D |
| Character Studio / Performance | retopo/rig-target geometry és pose/clip provenance, safe instance traversal | A+B+D |
| World Generator / environment visualization | procedural foliage/terrain/weathering, visual voxels and LOD; scientific data path separate | B+C+D |
| Asset Graph | shared revisions, exchange receipts, diff, provenance, dependency graph invalidation | B+C |
| ComfyUI/InvokeAI | existing node workflows wrapped as admitted recipe adapters, Router/HRB boundaries | C |
| Developer Agent / Mentor | allowlisted typed action scripting, before/after receipts, contextual help, human gates | A+B |

Más FA3-alkalmazás csak explicit relevance/reuse-assessment után kapjon új felületet; ne generáljunk minden appnak automatikusan felesleges menüt vagy új függőséget.

## 7. Végrehajtható, egymástól elkülöníthető PR-szeletek

A dátumok és becslések helyett **elvégezhető műszaki egységek** szerepelnek. Az egyes szeletek akkor vehetők elő, amikor az érintett FA3-modul fejlesztése aktuális; a korai közös szerződések minimalizálják a későbbi újramunkát.

| Szelet | Konkrét deliverable | Függőség és minimális ellenőrzés |
| --- | --- | --- |
| P0 – Reconciliation | #477/#478 donoradatok ütközésmentes összevonása; minden source key egyszer, megfelelő license és státusz; ApplicationIntent + deterministic Reuse Assessment a ténylegesen fejlesztendő első funkcióra | registry test, backfill count, Application Donor Index, Khronos donor check; tervezett contract nevét csak ezután véglegesítjük |
| P1 – Typed Action Adapter | meglévő command/action API-k használatára épített tipizált registry projection, jogosultság + scope, no-execution dry-run reference | A1; rossz paraméter, unauthorized, expired project, duplicate idempotency fail-closed |
| P2 – Scope + Batch | selected/tree/other/all resolver, identity/instance dedup, progress/cancel/compensation receipts, Video Editor és Bforartists reference tests | P1; duplicate mutation és partial rollback regresszió |
| P3 – GUI / Profiles | Qt6/QML radial+palette, per-app shortcut collision, sparse override migration/backup, Wayland/X11 GUI test | P1; nincs globális input hook, profil adatvesztésmentes |
| P4 – Asset Graph Exchange | manifest v1, content hash/staging, versioned native references, conflicts/approval, mock roundtrip | Reuse Discovery és Asset Graph; no path escape/no overwrite/no global polling |
| P5 – Optional 3DCoat pilot | 3DCoat adapter csak ha telepítve és verziószinten igazolt; Bforartists mesh+UDIM+PBR roundtrip, return review | P4 + külön license/security/runtime admission; nem kötelező product install |
| P6 – Cross-app Handoff | Krita→Video Editor; Bforartists render→Editor; Story→Editor; Music→Editor, meglévő links contractokra építve | P4; native .kra/.blend/Ardour/project.fa3video/.fa3clip megmarad |
| P7 – Typed Recipe Projection | minimális recipe envelope + 3D material és existing Gaffer/Natron/ComfyUI illesztők, preview/loss report | Reuse Discovery, P4, provider/model/hardware review; CPU-only FA3 reference path |
| P8 – 3D Features | LOD/density tests, explicit sculpt/retopo/UV/PBR pipeline, voxel/lattice optional adapter, print-geometry validation | P4/P5/P7 igény szerint; CPU-only ref, high-poly/native preserved |

Minden szelet PR-ja jelezze: melyik meglévő capability/contract bővül, mely donorokat vizsgálták, melyik alternatíva lett elvetve/halasztva, és melyik app válik valóban érintetté. Új canonical capability és authority létrehozása tiltott automatikus mellékhatásként; ha elengedhetetlen, külön rendes governance-döntés és release reconciliation szükséges.

## 8. Kötelező Hardware Audit és platformkorlátok

**Audit a terv elfogadásának előfeltétele:** minden új FA3 alapréteg vendor-semleges, CPU-only működőképes, gyorsítószám 0..N, fizikai/logikai CPU külön riportálva. A host resource placement/lease kizárólag FA3-AUTH-HOST-RESOURCE-BROKER-001; modellútvonal kizárólag FA3-AUTH-MODEL-ROUTER-001 a LiteLLM adatútvonalon. Nincs fix Ollama, LM Studio vagy modell kiválasztás; jelenlegi host-eredmény nem általános követelmény.

Megjelenítő GPU alaphelyzetben megjelenítésre fenntartva: FA3-irányított AI feldolgozásra akkor vonható be automatikusan a rögzített kivétel szerint, ha sem másik GPU, sem NPU nincs; egyébként csak konkrét modellre és feladatra történő kifejezett alkalmazáson belüli kijelöléssel. Második GPU vagy NPU pusztán rendelkezésre állás miatt sosem kapcsolódik be; silent fallback nincs. A harmadik fél 3DCoat saját erőforráskezelését nem lehet FA3-ként átírni: külső app használata consent és saját vendor támogatási feltételei mellett, a FA3 erőforrás-lefoglalás és evidence önálló igazolásával történik.

Qt6 GUI: Wayland preferált, X11 támogatott, KDE/GNOME/XFCE kompatibilis alkalmazáshatár, nem KDE-specifikus architektúra. 3DCoat termék Linux- és konkrét Ubuntu 26.04 kompatibilitása, GUI és esetleges Core API fordítása önálló current-host ellenőrzés; a dokumentált Core API C++/Visual Studio leírásából tilos Linux build támogatást következtetni. Külső vendor GPU shader nem lehet mandatory CPU-only FA3 út.

Sem installer, sem profil, sem script nem végez host-global tuningot, portütközés miatti AdGuardHome-átállítást, veszélyes órajel/feszültség/ventilátor/termál állítást vagy autorun third-party installer műveletet.

## 9. Tesztek, bizonyíték és célállapot

A statikus teszt és hosted CI nem azonos a fizikai hoston ellenőrzött integrációval; PENDING érvényes eredmény.

1. **Canonical és reused contract:** capability/authority drift=0 a külön döntés nélküli szeletekben, deterministic reuse assessment és Khronos check minden új/ténylegesen módosított modul előtt.
2. **Biztonság/licenc:** minden forrás exact commit/license/third-party dependency/redistribution decision; LKS source-copy blokkolt tisztázásig; approved script source és sandbox, denied-by-default external actions.
3. **Command/scope:** 4 kötelező scope, jogosulatlan action tiltás, duplicate instance csak egyszer a shared data útvonalon, eltérő occurrence helyes, cancellation/partial failure konzervatív és auditált.
4. **Profil:** régi v1/v2→aktuális migráció, hiányzó lépés vagy újabb ismeretlen verzió fail-closed, atomic write és .bak, hotkey ütközés, aktív alkalmazás konfigurációjának nem felülírása.
5. **Exchange:** native roundtrip aranyminták hash-sel, unit/axis, multi-UV/UDIM, material semantics, 3-way concurrent edit conflict, auditált no data loss.
6. **Fault injection:** sérült/truncated manifest, túlméretes állomány, symlink escape, stale data, elérhetetlen provider, GPU nélküli gép, megszakított job, idegen temp fájl.
7. **Quality:** golden images/geometries/mapping, renderer-specifikus toleranciák és projection loss report; dry-run becslés vs actual separate receipt.
8. **Host:** explicit aktuális exact host + driver + desktop session, külön Wayland/X11 és CPU-only baseline; opcionális GPU-backed és külső 3DCoat út külön bizonyítékkal, nem feltételezhető.
9. **CI:** az érintett unit/regression + FA3 Reuse Discovery, Application Donor Index, Khronos, distribution compliance, hardware baseline és global static enforcement. Meglévő, érvényes gate gyengítése PASS kedvéért tilos.

**Minimális pilot kész feltétele:** minden aranyminta és negatív biztonsági teszt lefut, a száraz próba mutatja a tényleges változásokat, az eredeti natív projektek érintetlenek, a visszatérő változás explicit review-t kap, minden input/output hash/adapter/driver/backend/provenance rögzített, és a current-host receipt csak tényleges megfigyelésből készül.

## 10. Nyitott döntések – csak akkor, amikor az adott szelet sorra kerül

- A meglévő FA3 command/action réteg melyik végpontja adja a P1 pontos belépési pontját; ha a Video Timeline Provider typed operation szerződése nem általánosítható, készülhet kizárólag alárendelt adapter, új command authority nem.
- Az Asset Graphnak pontosan melyik meglévő entitása reprezentál immutable derivált file revisiont és approval-t; az InterchangeManifest csak adapter contract vagy ténylegesen szükséges kanonikus gyermek-e.
- Melyik OpenUSD/glTF/KTX megoldás admitted a kiválasztott konkrét hoston; ne csomagoljuk duplán a Bforartistsben/FA3 Khronosban már meglévő technológiákat.
- LKS szerzői/third-party license tisztázódik-e. Enélkül kizárólag ötlet- és UI/workflow-minta.
- 3DCoat telepítési/licenc és Linux/Wayland/X11/API kompatibilitás aktuálisan rendelkezésre áll-e. Enélkül a P5 csak mock és kompatibilitási terv, nem integrált runtime.
- A felhasználó által jóváhagyható „automatic / approval / mixed” módokat hogyan képezik le a már létező FA3 policy szerződések: erős action-specific jogosultság a szöveges agent-utasítástól függetlenül.

**A dokumentum nem ígér háttérben futó munkát.** Az implementáció a fenti kisebb PR-szeletekben, az aktuális FA3 repository és meglévő governance alapján, tényleges kód- és current-host evidenciával folytatható.
