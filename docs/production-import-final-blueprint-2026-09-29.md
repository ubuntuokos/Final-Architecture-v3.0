# FA3 Production Import & Migration Fabric — újraelemzett rendszerterv v2
**Felülvizsgálat: 2026-09-29.** Ez a v2 döntési fedőlap újraértelmezi a lent megőrzött v1 részletes specifikációt a legutóbbi FA3- és donornyilvántartási változások alapján. A v1 17 stabil output ID-ja, szerkeszthetőségi és minőségvizsgálati feltételei továbbra is kötelezők; ahol v2 és v1 eltér, a v2 a jelenlegi javaslat. **Terv; nem runtime, provider- vagy current-host-elfogadás.** 175 képesség; dinamikus provider szám; nulla új központi hatóság.

## V2-1. Tényalap, donor-unió és forrásváltozatok
GitHub összevetés: ellenőrzött main cb3e5b34da3e0f4002f8fb82b4d1c0ae05375194 = 592 canonical donor; #528 előző feje 68c885da9f4938529e6e5477d6e0c11892935701 = 667. A main és #528–#533 normalizáltkulcs-alapú, még NEM beolvasztott egyesítési halmaza 750 külön forrás; ebből 83 nincs jelen a #528-ban. Két átfedő forrásazonosító a #531 és #532 között: a modelcontextprotocol szervezeti index és a modelcontextprotocol/servers. Ez **csak a hat vizsgált PR + main összehasonlítása**, nem az összes nyitott donorág teljes globális uniója: fel kell dolgozni az egyéb aktív #460, #510, #512–#519, #522, #525 és #526 donor-PR-eket is. Fiók/ágonkénti régi számot soha nem szabad kész main-rekordként feltüntetni.

A donor-azonosítás négy külön osztálya: SOURCE_REPOSITORY, ORGANIZATION_DISCOVERY, TOPIC_DISCOVERY_WITH_QUERY_VIEW és HISTORICAL/MAINTAINED_FORK_LINEAGE; ezekhez alias, redirect, source snapshot/version/commit, licence és célalkalmazás mezők. Témaoldalak nem programok, szervezetek nem telepíthető provider-halmazok. Egy repo ugyanazon normalizált kulcsa mezőnként veszteségmentesen összevezetendő; nem helyes a nagyobb ág rekordjainak egyszerű felülírása sem. A visszautasított és SUPERSEDED történeti vizsgálat megmarad, de nem lesz új aktív donor. A G'MIC történeti alias nem nyithat új párhuzamos donor-identitást.

Konkrét felülvizsgálandó kettős/hibás identitás: a #531 korábbi modelcontextprotocol/specification útja nem volt elérhető a GitHub API-n; a #532 modelcontextprotocol/modelcontextprotocol aktív, hivatalos forrás. Ellenőrzött canonical mapping után a téves vagy történeti locator alias/SUPERSEDED státuszba helyezendő, nem két SDK-ként promótálandó. A BBC/bmx archivált történeti repo, az EBU/bmx külön, nem archivált további forrás; lineage kapcsolattal mindkettő rögzítendő. Az OpenMAX IL multimédia, az azonos névhez hasonló ML és AI-agent projektek, az AV1-kodek AOM és accessibility AOM, valamint a Render.com cloud és a képi renderer-kutatás nem keverhetők. A Nokia HEIF licencének nem kereskedelmi mezőjét, AGPL/GPL és ismeretlen modellweights jogát külön FAIL-CLOSED szűrni kell. Konkrét forrás használata csak független licenc/security/distribution/Software Coexistence/Hardware Audit/Reuse Discovery és adott runtime admission után engedélyezhető.

## V2-2. Újraértelmezett architekturális források és függőségek
A #405 Creative Project Workflow beolvadt: a projekten belüli jelenet/shot/media gráf, célzott revízió és human acknowledgement onnan újrahasznosítandó, nincs új production graph. A #195 Tools/File Conversion még nyitott: a tervezett file.convert.inspect/plan/execute és a meglévő UAF/FFmpeg/Document/Geometry/Audio szakadapterek összevezetése előfeltétel, nem második konverziós hatóság. A #413/#520 Story ág nyitott: Fountain/FDX csak a függetlenül bizonyított, azonos formátumba oda-vissza exportálható részhalmazban nevezhető szerkeszthetőnek; Office/ODF/WPS/ONLYOFFICE teljes formátumcsalád nem automatikusan admitált. A #410 globális Software Coexistence retroaktív és fizikai bizonyítási kötelezettség; a #464 display-GPU megvalósítás külön draft és nem tekinthető kész hitelesített vezérlésnek. A #523 egyesített Unreal-szabály enged opcionális, külön auditált interchange-et, nem kötelező Unreal runtime-ot. A #524 Capture/Local Inbox pending forrásproducer; core offline import nem várhat rá. A #521 prompt/mesh-receiver PR lezárt, de NEM merge-elt; semmilyen terv nem állíthatja már főági, futó receiverek meglétét. A #528 S1–S6 előkészítők nem valós média- vagy célalkalmazás-E2E bizonyítékok.

## V2-3. Egységes működési szerződés
Egyetlen meglévő Production Studio / Director GUI; import mód LINK_ONLY, DERIVED_ONLY, COPY_EDITABLE, HYBRID, ARCHIVAL_COPY; bemenet FILE, EXISTING_PROJECT, AUTHORIZED_LAN_SOURCE, LIVE_VIDEO, LIVE_AUDIO és LIVE_CAPTIONS. Pontosan 4 szöveg + 6 hang + 7 videó, többes jelölőnégyzetes kimenet marad, az átiratok nyelvi T1–T4 feldolgozásával. Forrás és időtartomány, target app/host, producer/rights, eredeti-vagy-becsült osztály, beállított nyelvek, forrás-revízió és audit minden levélen önálló. Nem jön létre 18. kimenet azért, mert a forrás élő vagy felirat-only.

Feldolgozás: DISCOVER → PROBE/SECURE → IMMUTABLE_STAGE → CAPABILITY/LOSS PREVIEW → HUMAN APPROVAL → HRB/MODEL ADMISSION → UAF/TEMPORAL EXECUTION → PER-OUTPUT QC → REAL TARGET-APP ACK/OPEN → EDITABLE CLAIM esetén SAME-TYPE EXTERNAL ROUNDTRIP → COMMIT_OR_ROLLBACK. Forrásmegőrzés és LAN-továbbítás csak a meglévő Logistics és Asset Graph, workflow és app-címzés csak Director/Temporal/UAF/Central MCP. Nem lehet új CAS, második asset registry, scheduler, service bus, subtitle authority, conversion daemon, runtime-cloud uploader vagy credential store. Független sikeres output megőrizhető sikertelen/stale más leaf-ek mellett, de explicit részleges jóváhagyás és per-output receipt szükséges.

Hangnál eredeti diszkrét track elsőbbsége. A meglévő Demucs négy stemje nem garantál beszéd–ének, tiszta instrumentális vagy ambience/SFX szétválasztást; a specialisták (Asteroid, SpeechBrain stb.) csak bizonyított stem ontology, jogtiszta modellweights, CPU-only, HRB/Router és független bleed/emberi minőségvizsgálat után válhatnak opcionális adapterré. A denoiser eltávolított residual-ja nem tiszta kért atmoszféra. FFsubsync csak timingot, Chromaprint csak tájékoztató relinket, libebur128 loudnesst és VMAF referenciaalapú percepciós hasonlóságot mér; egyik sem bizonyít önmagában szétválasztási vagy szerkeszthető projekt-egyenértékűséget.

OTIO külső edit-interchange, médiatartalmat nem tárol; média- és asset-linket a meglévő FA3 Logistics/Asset Graph őriz. A teljes Story, FDX/Fountain/Office, OTIO/AAF/XGES, DAWproject/MIDI/MusicXML/ABC, OpenToonz Xsheet, USD/glTF/Alembic, broadcast MXF/ADM, live EBU-TT/HLS és opcionális Unreal projektcsalád mind pontos source-version/target-version/feature/direction párokkal külön admitálandó. A Flat MP4/WAV/PDF, renderelt sztereó mix, IMF és az OCR mindig preview/delivery-derivátum vagy archívum, nem hallgatólagos teljes projektmigráció. Külső forrás-jóváhagyás, C2PA bejegyzés és producer permission nem automatikus FA3 Human Approval.

## V2-4. Célzott, párhuzamos donorágakból hasznosítandó megoldások
- #529 ONNX és NNStreamer inference/stream-model interfész, AOMedia AV1 és libavif az ismert médiaútvonal alá; sem új inference, sem új képkonverter-authority.
- #530/#531 OpenAL/hangtér és FFmpeg-helyesbítő hagyományos OpenMAX adatcsere, libheif/libde265/libavif pontos codec licensing és verziófüggetlen roundtrip-kutatás; Nokia HEIF csak referencia, ha a konkrét jogok nem megfelelőek.
- #532 Microsoft MarkItDown az eredeti Document Fabric alá kizárólag alkalmas, meghatározott dokumentumrészhalmazokra; MCP upstream official spec meglévő Central MCP Gateway számára; HPC IO/transfer reference meglévő Logistics/HRB alá.
- #533/#517 Novel, novelWriter, Manuskript csak dokumentumszerkezet, szerzői UI és változatkezelési minták; sem Vercel/cloud, sem donor-webalkalmazás nem kötelező FA3-függőség.
- #512–#516/#518 Video, storyboard, QuickClip, beat/daw donorminták csak natív Video/QuickClip, Story/Shot Designer és Music Studio felé. Narrative beat ≠ zenei beat; Beat Saber beatmap-parser nem általános zenei beatdetektor.
- #526 Dagger content-key lineage és SkyPilot locality/cost csak opcionális minták a meglévő Director/Temporal/HRB/Logistics alatt. #522 Godot/fbx2glTF optional interchange, #523 Unreal opcionális; nincs motor/runtime-telepítési kényszer.
- #528 QCTools QC referencia, Netflix libvmaf a már meglévő FFmpeg QC-be, BBC/EBU bmx MXF, EBU ADM Renderer/Toolbox objektumalapú audio, AMWA NMOS tests kizárólag izolált stúdiólabban; BBC audiowaveform történeti GUI referenciaként (a tényleges fejlesztés másik upstreamen folyik).

## V2-5. Hatlapos GUI és nem megkerülhető ellenőrzés
A meglévő, Wayland-first Qt6/QML Production Studio munkaterületen: (1) jogilag engedélyezett forrás és mód, (2) scene/track/projekt-szerkezet és hiányzó external link, (3) 17 checkbox + nyelvek/shotok/stemek és célalkalmazások, (4) DAG/erőforrás/loss/precíz runtime-előnézet, (5) rights/security/licence/human approval/külön audio-picture-language QC, (6) végrehajtás/target acknowledgement/roundtrip/rollback/per-output Evidence. Nem készül külön GUI-héj vagy KDE-specifikus alkalmazás.

P0 a teljes aktuális donor-PR-unió, normalizált alias/fork/index rendezés, Application Donor Inventory és Reuse Discovery; P1 #195/#405/#410/#413/#520 pontos szerződés- és coexistence-összevezetése; P2 a meglevő S1–S6 deduplikációs auditja és típusellenőrzése; P3 valódi, szigorúan eredeti-first CPU-only File/Document/FFmpeg import; P4 többnyelvű átirat/fordítás és specialistahang külön admission; P5 teljes projektcsaládonként független same-type reversible golden fixtures és külső source-app megnyitás; P6 UAF per-app receiver, többhostos CAP-150/CAP-152 + opcionális Capture; P7 jogszerű live és broadcast; P8 exact-head Canonical, Reuse, Release Projection, Evidence, hardver/Software Coexistence, fizikai aktuális host, valódi GUI/API/E2E. P3/P4 első felhasználható részprofilja nem vár minden P5–P7 formátumra, de csak a saját bizonyított scope-ján belül nevezhető működőnek.

Jelenlegi #528 ellenőrzött head: a Canonical, Reuse Discovery és Unified Current Host Projection FAIL a release projection 010 Git-blob drift és 014 unmanifested file hibái miatt. Előbb veszteségmentes donor-összevezetés, végleges exact-head manifest/release reconciliation és megfelelő független kapuk; a statikus S1–S6 kód sem fizikai current-host PASS. A régi evidence-pillanatképek változatlanok. CPU-only, 0..N accelerators, P0 Hardware Safety Envelope, no Conda/Mamba, no silent fallback, no auto display-GPU enlistment, no mandatory paid render runtime, no MiniMax H3 kötelező futtató minden profilban megmarad.

---

## Történeti v1 részletes specifikáció (a nem felülírt követelmények továbbra is érvényesek)

### Az eredeti v1 részletes terv
Dátum: 2026-09-29. Státusz: VÉGLEGES TERVJAVASLAT; alkalmazásfejlesztés, forráskód-beemelés és fizikai current-host PASS nélkül. Kapcsolódó PR: #528. Képességalap: **175 változatlan**. Provider-szám: dinamikus. Új központi hatóság: **0**.

Ez a dokumentum a [korábbi teljes terv](production-import-migration-plan-2026-09-29.md), a [pontos 17-választásos specifikáció](production-import-selective-content-plan-2026-09-29.md), a [történeti konverziós döntések](production-import-historical-conversion-reconciliation-2026-09-29.md), a [live források](production-import-live-source-intake-2026-09-29.md), valamint a [további forrásellenőrzött donorok](production-import-additional-github-donors-2026-09-29.md) egységes, fejlesztést megelőző műszaki szerződése. A hivatkozott dokumentumok részletes golden fixture és korábbi döntésadatai kötelező mellékletek; a történeti rekordok és bizonyítékok változatlanok maradnak.

## 1. Cél és nem-cél
**Cél:** egyetlen FA3 Production Studio → Produkció megnyitása / importálása munkaterületből (a) teljes, bizonyítottan szerkeszthető külső produkció, (b) részleges, 17 egymással kombinálható szöveg/hang/videó kimenet, (c) több produkció egy célprojektbe, (d) megőrzési archívum, (e) jóváhagyott hibrid kapcsolat, (f) jogszerű live videó, live hang/podcast és önálló live felirat feldolgozása. Eredeti projekt és eredeti média változatlan, minden kimenet eredete és vesztesége látható.

**Nem-cél:** új asztali alkalmazás, ütemező, eszköztár, felirat-authority, fordítási authority, modellválasztó, médiakonverter, háttérszinkron, hálózati vezérlő, renderfarm, cloud upload, automatikus forráskód-átvétel. Egy renderelt MP4/WAV/PDF vagy kép-szekvencia önmagában sosem egyenértékű a natív szerkeszthető forrásprojekttel.

## 2. Hét kötött architekturális határ
1. **Creative Project Graph + Director/Production Studio**: felhasználói és produkciós tulajdonosi kapcsolatok, jelenetek, epizódok, asset és feladat-kapcsolatok; nincs második projekt-authority.
2. **#195 Tools / File Conversion és UAF**: típusos file.convert.inspect/plan/execute és megengedett formátumpár-adapterek; FFmpeg, Document Interchange, Geometry, Video, Audio csak alárendelt útvonalak. A #195 korábbi 143-as metaadata történeti; az összevezetésben 175 marad, történeti evidence nem írható át.
3. **Asset Graph + FA3 Logistics**: immutábilis forráspéldány, SHA-256 és tartalomazonosító, útvonal-feloldás, verziózás, megszakítás után folytatható LAN-átvitel, célalkalmazásra történő publikálás; nincs új CAS, relink-adatbázis vagy sync daemon.
4. **Temporal + Director/Workforce**: a teljes import DAG tartós állapota, függőségek, gép-/alkalmazás-címzés, részfeladat-kész jelzések, leállítás és rollback; nincs párhuzamos feladatmotor.
5. **HRB + Model Router**: egyetlen erőforrás- és modellfuttatás-hatóság; CPU-only kötelező, modell/model-checkpoint dinamikus admission, nulla silent fallback, kijelző-GPU csak a jóváhagyott FA3-szabályok szerint.
6. **Security Governance + Secret Broker + Evidence/PKI**: jog, adatvédelmi kategória, egress-tiltás, hiteles forrás, engedély, audit és aláírt current-host receipt; importált plug-in, makró, script és legacy render job alaphelyzetben inert.
7. **Domén-tulajdonosok**: Story/Document, Language, Caption/Subtitle, Audio Source Separation, Music Studio, Video Editor/QuickClip, 3D/Geometry, Photo, Live Studio és Credits; kizárólag ezek kanonikus célformátumát írhatjuk.

## 3. Pontosan 17 független, kombinálható kimenet
A menü három forráscsaláddal és összesen 17 jelölőnégyzettel működik. Minden kiválasztás külön célt, formátumot, eredetstátuszt, QC-t, nyelvet, jóváhagyást és hibakezelést kap.

| Forrás | Stabil selector | Magyar felhasználói választás és kötelező eredmény |
|---|---|---|
| SZÖVEG | ORIGINAL_LANGUAGE | T1 Eredeti nyelven – eredeti dokumentumszerkezet és nyelvi metaadat. |
| SZÖVEG | ONE_TRANSLATION | T2 Egy kiválasztott nyelven – egy önálló, visszaköthető fordított változat. |
| SZÖVEG | MULTI_TRANSLATION | T3 Több nyelvre lefordítva – egy célváltozat minden kért nyelvre. |
| SZÖVEG | ORIGINAL_PLUS_TRANSLATIONS | T4 Eredeti és fordított változatok együtt – egy közös lineage-bundle, külön revíziók. |
| HANG | FULL_AUDIO | H1 Teljes hang – eredeti stream, kiválasztott rész és csatornatérkép megőrzése. |
| HANG | TRANSCRIPT_ONLY | H2 Csak szöveges átirat – időzített szöveg, audio-kimenet publikálása nélkül. |
| HANG | SPEECH_OR_SINGING_SEPARATE | H3 Beszéd vagy ének külön – megnevezett vokális kategória, csak igazolt forrásstem vagy jóváhagyott becslés. |
| HANG | INSTRUMENTAL_ONLY | H4 Csak zene, ének nélkül – eredeti instrumentális sáv vagy ESTIMATED leválasztás. |
| HANG | AMBIENCE_AND_SFX | H5 Környezeti hangok és hangeffektusok – külön ambience és SFX, nem összetévesztendő eltávolított zajjal. |
| HANG | DENOISED_SPEECH | H6 Zajcsökkentett beszéd – érthetőségi QC és az eredeti változat kötelező megőrzése. |
| VIDEÓ | FULL_VIDEO | V1 Teljes videó – natív projekt csak ha az adott verzió/formátumpár bizonyított; különben delivery. |
| VIDEÓ | VIDEO_WITHOUT_AUDIO | V2 Csak kép, hang nélkül – picture-only időalap-, HDR- és színtéradatokkal. |
| VIDEÓ | FULL_AUDIO_ONLY | V3 Csak teljes hang – eredeti audio és csatornák, videópublikálás nélkül. |
| VIDEÓ | TRANSCRIPT_ONLY | V4 Csak beszédátirat – belső demux megengedett, rejtett audio-kimenet tilos. |
| VIDEÓ | MUSIC_OR_INSTRUMENTAL_ONLY | V5 Csak zene vagy instrumentális rész – eredeti sáv elsőbbsége; becsült szétválasztás megjelölve. |
| VIDEÓ | AMBIENCE_AND_SFX_ONLY | V6 Csak környezeti hangok és effektek – külön forrássáv vagy külön admitált becslés. |
| VIDEÓ | FRAMES_OR_SCENES | V7 Képkockák vagy kiválasztott jelenetek – frame/shot/timecode tartomány, stabil forráskapcsolat. |

Az Audio/Video TRANSCRIPT_ONLY kimenetére a négy szövegnyelvi opció ismét alkalmazható. Ezzel nem keletkezik újabb selector vagy képességazonosító. Az eredeti átirat marad a fordított változatok szülője.

## 4. Forrásdimenzió és öt migrációs mód
Forrás: FILE | EXISTING_PROJECT | LIVE_VIDEO | LIVE_AUDIO | LIVE_CAPTIONS. Az önálló feliratforrás sem hangot, sem videót nem követelhet. Beágyazott 608/708 vagy HLS-ben integrált felirat esetén a tényleges kinyeréshez szükséges AV-beolvasásról előre tájékoztatni kell; NO_AV_FETCH esetén ez a profil blokkolt.

Mód: LINK_ONLY (külső forráshely); DERIVED_ONLY (kijelölt kimenetek); COPY_EDITABLE (csak bizonyított, azonos formátumba visszaexportálható részhalmaz); HYBRID (forrás snapshot + jóváhagyott read-only kapcsolat, opcionális külön writeback-engedély); ARCHIVAL_COPY (immutábilis, hash-ellenőrzött eredeti és sidecar). A teljes produkció LINK_ONLY, COPY_EDITABLE, HYBRID vagy ARCHIVAL_COPY lehet; részleges kiválasztások ugyanezen forrás gráfjához tartoznak.

## 5. Adatszerződések, semantikai egyenértékűség
A meglévő Creative Project Graph gyermekei: ProductionSourceManifest, ImportCapabilityMatrix, ProductionImportPlan, SelectiveImportRequest, ProductionImportReceipt, PerOutputReceipt. Ezek alárendelt, verziózott rekordok – nem új központi hatóságok.

**SourceManifest minimum:** forrásalkalmazás/verzió, produkciótípus, projektazonosító, SHA-256, jogosultsági és adatvédelmi kategória, engedélyezett fájlfa és külső linkek, revíziók, relatív elérési utak, track/stream/channel/codec, scene/shot, nyelv/BCP-47, forrás időalap és timecode, forrás képi színtér/HDR, kockázatos külső plug-in és script felsorolás, immutábilis snapshot.
**CapabilityMatrix:** exact source app-version + destination-version + format-version + direction + semantic feature. Eredmények: EXACT, PARAMETRIC_EQUIVALENT, LOSS_DECLARED, EXTERNAL_LINK_ONLY, INSPECT_ONLY, UNSUPPORTED. Ismeretlen UNSUPPORTED. Mindkét irány külön bizonyítandó.
**PerOutputReceipt:** eredeti és cél digest, adapter/verzió/digest, original-versus-estimated osztály, output és review state, kiválasztott tartomány, elveszett tulajdonságok, QC, forrás/target nyelv, human approval, HRB/UAF/Model Router és Evidence ref, pontos célapp-változat, megnyitás és reverse-export eredménye. Ne fogadjon el hitelesítés nélküli, bemondott PASS logikai mezőt.

## 6. Egyszer beolvasott forrás, közös végrehajtási DAG
DISCOVER → PROBE → INSPECT → SECURITY/RIGHTS → IMMUTABLE_STAGE → PROVENANCE/CAPABILITY_MATRIX → PREVIEW/LOSS_MAP → OPERATOR_APPROVAL → HRB ADMISSION → BOUNDED EXECUTE → INDEPENDENT QC → TARGET-APP OPEN → OPTIONAL SAME-TYPE EXPORT/REIMPORT → PER-OUTPUT COMMIT vagy ROLLBACK. A részfeladatok állapotát kizárólag Temporal és Director kezeli.
- Egy forrásdemux, egy eredetileg szükséges ASR és egyező forrástartományon közös időzítés; fordítási fan-out külön nyelvenként.
- Forrás track előbb, algoritmikus stem csak explicit megfelelő ontology és modell-admission után; hibás leaf nem semmisítheti meg a többi független, igazolt outputot.
- A csak-átirat belső audio-derivátuma átmeneti és retention/egress-tilalom alatt áll; csak kért output publikálható.
- Staging csak jóváhagyott könyvtárba; könyvtárbejárás, symlink escape, archive bomb, makrófuttatás és külső szerverkapcsolat alapból tiltva.

## 7. Nyelvek és többnyelvű revíziókezelés
Az eredeti forrás- és átiratszegmens a nyelvi authority; minden fordítás külön verziózott gyermek: source segment ID + target BCP-47 (nyelv/írás/régió) + termbase/glossary revision + modell/provider checksum + emberi korrekció + időzítés. Kódváltás szegmensenként; ne keverje az eredeti cue-t a fordított cue-val. A produkció saját névjegyzéke, szereplőnevei és terminológiája védett. A Story szemantika, a Subtitle időzített cue, a Language Fabric az engedélyezett fordítás, a Document az irodai/forgatókönyv formátum kezelés tulajdonosa. SECRET anyag külső fordítási modellhez explicit Security-admission nélkül nem küldhető; felhő alapértelmezésben tiltott.

## 8. A hangszétválasztás bizonyítható státuszai
1. **ORIGINAL_DISCRETE_STEM:** a natív DAW/broadcast projektben valóban elkülönített forrássáv. Csatorna, mintaszám, bext/ADM ID, időalap és hash alapján ellenőrzendő.
2. **ESTIMATED_SEPARATION:** előzetesen admitált modellből becsült speech/singing/music/instrumental/ambience/SFX. A Demucs dokumentált négy-stem (drums/bass/other/vocals) modellje nem bizonyít tiszta beszéd–ének vagy SFX–atmoszféra elkülönítést; hiányzó specifikus ontology esetén UNSUPPORTED.
3. **DENOISED_DERIVATIVE:** javított beszéd, amelynek eltávolított residual-ja NEM tekinthető tiszta atmoszférának.
4. **MISSING_OR_AMBIGUOUS:** explicit hiány, nincs csendes helyettesítés.
Asteroid, SpeechBrain és más meglévő donorok csupán kutatási jelöltek a kiegészítő modellhez; CPU, checkpoints, licenc, tényleges stem ontology, szivárgás és független listening/QC előbb kötelező. Chromaprint tanácsadó relink, libebur128 loudness/true peak és az eredeti minták visszaolvasása kiegészítő ellenőrzés, nem stem-fajtát bizonyító mérés.

## 9. Videó, broadcast és részletes kép-QC
FFmpeg/FFprobe és GStreamer a meglévő Tools/Video vonalon; OpenTimelineIO az Editorial IR külső csereformátuma, pyaaf2/AVB/FCPX/XML/XGES csak adott igazolt verzió- és irányrészhalmazban. Video-kimenetek: PTS/DTS, racionális időalap, drop-frame, változó frame-rate, hang-kép szinkron, aktív hangsáv, kamera/source track, színtér/OCIO, HDR metadata, pixel aspect, interlace, closed captions és feliratok külön vizsgálandók.

Új donorminták: BAVC QCTools pre-ingest preservation riport; BBC/bmx archivált történeti MXF-forrás, EBU/bmx a további vizsgálandó fork; Netflix/VMAF a már meglévő FFmpeg/libvmaf minőségmérési útvonal referenciaalapja. A perceptuális hasonlóság NEM helyettesíti a szín-/HDR- vagy timecode-azonosságot. MXF rewrap NEM jelenti az eredeti vágási projekt átvitelét. Az eredeti média és az átkódolt proxy mindig külön azonosítót kap.

## 10. Teljes produkciók forráscsaládjai és veszteségpolitikája
| Család | Prioritásos FA3 cél és átvétel | Kötelező kizárás |
|---|---|---|
| Story/FDX/Fountain/Office/ODF | Story + Document Fabric; jelenet, szereplő, branch, jóváhagyás, helyesírás/nyelv, produceri profil és azonos típusba visszaexport | OCR/PDF nem bizonyít teljes szerkeszthető eredetit; nincs hallgatólagos jóváhagyásátvitel |
| Video/OTIO/AAF/FCPX/XGES | natív .fa3video Editorial IR; opcionális .fa3clip variáns és oda-vissza léptetés; sávok, vágás, effektek/átmenetek részletes loss-map | MP4-only eredmény nem project import; unsupported effekt nem tűnhet el csendben |
| DAWproject/MIDI/MusicXML/ABC/BWF/ADM | Music Studio/Audio; hangsáv/clip/automation, tempó, hangjegy, score, stems, térbeli objektumok és eredeti presetek | stereo mix nem DAW session; hiányzó plug-in nem futtatható automatikusan |
| 2D/OpenToonz TNZ/Xsheet | Animation Studio; jelenet, rajz, paletta, Xsheet és külső mappakapcsolat | kirenderelt videó nem TNZ roundtrip |
| 3D/USD/glTF/GLB/Alembic | Geometry/World/Character/Shot/Render; USD layer/reference, material/rig/skin/morph, koordináta és animáció | hiányzó shader/morph/rig nem címkézhető EXACT-nek |
| AYON/Kitsu/OpenCue/broadcast/OBS/Unreal | Director/Asset Graph/Live Studio; asset, shot, rendezői feladatok, szabványos ütemezés és show/rundown | külső jóváhagyás és render job nem ad FA3 végrehajtási jogot; Unreal current-host admission külön |
| Archive/IMF/MXF/BagIt/OCFL | Logistics + Asset Graph + QC; eredeti csomag, fixity, version és külső relink | IMF delivery/archívum nem szerkeszthető natív produkció |

Bármely olyan formátum, amely szerkeszthető importként belép, csak akkor **admitálható**, ha ugyanabba a formátumba és verziózott szemantikai részhalmazba exportálni és az eredeti forrásalkalmazásban megnyitni is bizonyított. Egyirányú, Preview-only és Delivery-only formátum másik osztály, ezt a GUI előre kijelzi.

## 11. Live források nem jelentenek 18. választást
Jogszerű helyi OBS/Studio, SRT/RIST, HLS/LL-HLS, engedélyezett RTMP/RTSP/WebRTC, Icecast audio/podcast, önálló EBU-TT Live/WebVTT caption; mind a meglévő 17 outputot állíthatják elő. LIVE_CAPTIONS önállóan működik, ideiglenes részleges cue és utólag véglegesített cue revízióval. A hálózati szerver, token, felvételi jog, feliratforrás, szegmens-gap, szekvenciaszám, szinkron/drift, megszakítás és retention a SourceManifest része. Sem automatikus scraping/DRM megkerülés, sem kontrollhálózati teszt a felhasználó engedélye nélkül.

Az AMWA NMOS teszt donor kizárólag izolált laborprofilban használható; mock mDNS forgalma tilos produkciós helyi hálózaton. EBU ADM Renderer és EBU ADM Toolbox segít a broadcast objektumalapú hangsávok megőrzésének tervezésében, de a renderelt objektumhangot nem szabad eredeti szerkeszthető ADM-forrásnak nevezni.

## 12. Egységes Qt6/QML GUI-terv a már meglévő Production Studio felületen
Főablak: **Production Studio → Produkció megnyitása / Importálása**. Wayland elsődleges, X11 fallback, nem KDE-specifikus. A meglévő FA3 Control Center/GUI-komponenseket és az összes akadálymentességi elvárást örökli.

Hat lap, egy folytonos, megszakítható munkafolyamatban:
1. **Források:** fájl/projekt/mappa/archívum, jóváhagyott LAN-peer, élő forrás és caption-only; felismerhető projektverzió, jogok, forrásméret, immutábilis eredeti.
2. **Produkciós szerkezet:** sorozat/epizód/jelenet/shot/track/forgatókönyv/nyelv hierarchia; eredeti/külső link/hiányzó asset, forrás- és célalkalmazás közti térkép.
3. **Kimenetek – 17 jelölőnégyzet:** 4 szöveg, 6 hang, 7 videó; nyelvek, szegmensek, sávok, frame/scene és időtartomány; eredeti + becsült hangszétválasztás státusza.
4. **Átalakítási terv:** végrehajtási DAG, újrahasznosított dekód/ASR, erőforrásigény és jóváhagyott gép-/alkalmazás-kiosztás; per-funkció fidelity (EXACT/PARAMETRIC/LOSS/EXTERNAL_LINK/UNSUPPORTED); előnézet.
5. **Ellenőrzés és jogosultság:** jog, licenc/egress, PII/SECRET, CPU/GPU előnézet, modellek, snapshot, részleges import/publikálás; felhasználó elfogadhat vagy elutasíthat egyenként.
6. **Folyamat és átadás:** stream/nyelv/output-specifikus progress, sorok, ideiglenes és végleges output, önálló retry/cancel, QC és receipt, célapp-megnyitás, visszaexport, rollback és audit.

A hangsáv előnézetének min/max csúcsérték- és zoom-mintájához a BBC audiowaveform kutatási donor használható, de az eredeti többsávos hullámformák és az időalap külön objektumok. A státuszhoz sosem elegendő csak egy zöld pipa: külön látható az eredeti sáv, a becsült szétválasztás, a QA-ra váró kimenet és a ténylegesen megnyitott szerkeszthető projekt.

## 13. Függőségi térkép és kötelező sorrend
- **D0**: #528 és #527 donor/metaadat exact-head összevezetés; Donor & Reference Registry + Reuse Discovery; 175 invariáns, Software Coexistence, Historical Evidence változatlan.
- **D1**: #195 Tools/File Conversion és Document Interchange formátumpár/facade konfliktusmentes összevezetés. #413 Story és #520 szerkeszthető FDX/Fountain subset/handoff; szükség esetén újranyitandó hiányzó per-format roundtrip.
- **D2**: Logistics immutable staging/transfer és Asset Graph relink; PKI, Security Governance, Secret Broker; authorized LAN/live network szerződések.
- **D3**: ImportCapabilityMatrix + változatos golden fixture-ök; külső app verzió és valós olvashatóság; csak bizonyított párok promótálhatók.
- **D4**: Source scan és PROBE_ONLY, PREVIEW_ONLY; natív source track + offline/basic CPU-only STT; csak ismert nyelvek és fordítópárok; szükséges minőségsztenderdek.
- **D5**: Audio valódi stem vs estimated/denoised; Demucs jelenlegi ontology; speciális speech/singing/ambience modellek csak új admission után. Minden kimenet külön QC.
- **D6**: Editorial/DAW/Story/Animation/3D teljes projekt subsetek; kétirányú külső golden fixture-ök és célapp megnyitás; nem támogatott effektek/pluginek explicit veszteséggel.
- **D7**: Live videó/audio/caption-only jogosult források; broadcast MXF, ADM és izolált NMOS referencia; többgépes Director/Temporal handoff.
- **D8**: végső release-projekció, exact-head Canonical/Promotion/Reuse/reference, Security/Coexistence/Hardware Gates, Wayland GUI és fizikai CPU-only/current-host/real E2E + rollback.

D0–D3 a későbbi alkalmazásfejlesztés megkezdésének előfeltétele; a teljes produkciós ígéret csak a saját formátum- és forrásverzióosztályának D6–D8 bizonyítékával jelenhet meg. A korábbi #195/#413/#520/#410 és #523 függőségeket a tényleges főági állapothoz újra kell vizsgálni; a terv szövege nem bizonyítja automatikus lezárásukat.

## 14. Nem megkerülhető teszt- és bizonyítékmátrix
- **Szerkezeti:** pontosan 17 stabil ID, minden kombináció összeállítható; kéretlen kimenet nem publikálható; párhuzamos hatóság/adatbázis nincs; donorforrás-kulcsok és donor ID-k egyediek, új rekord mindig CANDIDATE.
- **Szöveg:** eredeti és 1/N fordítás együtt/magában, BCP-47, code-switching, protected glossary, részleges javítás, back-reference, időzítési lineage, SECRET egyezés és tiltott egress.
- **Audio:** mono/stereo/5.1/ADM/BWF timebase, discrete exact stem, becsült szétválasztás, speech/singing és SFX/ambience hiány negatív teszt, denoise ≠ tiszta környezeti stem, clipping/loudness, auditált kézi QC.
- **Video:** CFR/VFR, drop-frame, A/V drift, HDR/SDR, interlace, felirat, korrupt/chunk-hiányos forrás, képkocka/kiválasztott snitt kivét, eredeti MXF rewrap veszteségmátrix, VMAF csak megfelelő referenciával.
- **Editable roundtrip:** FDX/Fountain/DAWproject/OTIO/AAF/MusicXML/TNZ/USD profil-specifikus fixture; független forrásalkalmazásban visszanyitás, strukturális/semantikai különbséglista. PDF/OCR, WAV/MP4, IMF nem tehető teljes projektté.
- **Security és Hardware:** zip/symlink/path traversal, nem engedélyezett makró és plugin, streaming SSRF/redirect, egress és titokszivárgás, túl nagy erőforrásigény, leállítás/rollback, CPU-only, engedély nélküli kijelző-GPU vagy silent fallback negatív teszt.
- **Multi-host és live:** peer-kiosztás, elérhetetlenség, időszinkron, szegmens-gap és reconnect, caption-only NO_AV_FETCH, kontrollhálózattól elszigetelt NMOS labor.
- **Evidence:** minden terv/adapter/model/asset forrás- és cél SHA/azonosító; történeti evidence nem módosítható; új exact-head bizonyíték szükséges. S1–S6 statikus preflight nem fizikai importteszt.

## 15. Kiadhatóság és végső elfogadás
A **végleges terv** nem egyenlő a **megvalósított, elfogadott rendszerrel**. Teljes éles elfogadáshoz minden admitted source/target verziópárnak, tényleges céleszköz- és host-konfigurációnak, futtatott modellnek, kijelölt kimenetnek és jogosultsági profilnak külön visszakereshető current-host és alkalmazáson belüli ellenőrzési bizonyíték kell. Ahol nincs bizonyíték: INSPECT_ONLY, PREVIEW_ONLY, LOSS_DECLARED vagy UNSUPPORTED, soha nem hamis FULL_MIGRATION PASS. A felhasználó által még nem látott és jóvá nem hagyott új alkalmazás fejlesztése nem kezdhető meg; ez a terv a meglévő felületek kiterjesztésének specifikációja.