# CFA3 Unified Execution & Fulfillment Fabric (UEFF) — jóváhagyott architekturális beillesztés

**Dátum:** 2026-10-14  
**Státusz:** Tulajdonos által jóváhagyott, kanonikus tervbe illesztendő koncepció; nem implementáció, nem futtatókijelölés, nem Current Host PASS.  
**Elhelyezés:** a meglévő `ORCHESTRATION_WORKFLOW_FABRIC` közös CFA3-szolgáltatási kategória kibővített, egységes célarchitektúrája.  
**Képességváltozás:** 0; a meglévő 175-ös baseline változatlan. **Új végrehajtási/biztonsági hatóság:** 0.

## 1. Az UEFF és a CFF viszonya

A CFF (Capability & Fulfillment Fabric) **az UEFF integrált belső doménje**, nem második önálló CFA3 Shared Service. A CFF kezeli a szükségletet, célokat, minőséget, élettartamot, szakértelmet, eszközt, erőforrás-ellátást, kapacitást, egyeztetést és vállalhatóságot. Az UEFF ezen felül egységes tartós workflow-koordinációs képességet specifikál. A logikai integráció nem ír elő egyetlen monolitot és nem engedélyez párhuzamos végrehajtási állapotigazságokat.

A helyes rétegezés: **CFA3 alkalmazások → UEFF (CFF + durable orchestration) → már meglévő UAF / Security / HRB / Model Router / MCP / Work Management / Journal / Evidence / Engine Selection szolgáltatások**. Az UEFF nem kerül e meglévő hatóságok fölé, és nem teremt új jogosultságot.

## 2. Temporal: jelenlegi működés kontra jövőbeni technológiai döntés

- A **jelenlegi operatív workflow-k Temporal-függő életciklus-hatósága változatlan**, amíg külön jóváhagyott és bizonyított migráció nem történik.
- A **UEFF célarchitektúrájának tartós végrehajtómotorja NYITOTT KIVÁLASZTÁS**. Nem rögzített végleges Temporal-választás, és nem automatikus Temporal-eltávolítás.
- Vizsgálandó megoldási irányok: önhostolható meglévő durable runtime; beágyazható, adatbázis-központú motor; vagy indokolt esetben saját, PostgreSQL-alapú végrehajtási mag. A jelöltek nem automatikusan elfogadott donorok vagy telepíthető függőségek.
- A célarchitektúra motorfüggetlen **viselkedési szerződést** határoz meg; a végrehajtási garanciák eltérései miatt nem ígér korlátlan motorcserélhetőséget.
- Engine Selection preferenciát/kompatibilitást nyilvántarthat, de nem jogosult önálló runtime-admission vagy új végrehajtási hatóság létrehozására.

## 3. A CFF munkamenete

1. Az eredeti kérés változatlan megőrzése; a megrendelő tényleges céljának és szükségletének diagnosztikája.
2. Megoldásalternatívák összevetése (eredeti, kisebb, nagyobb, eltérő megoldás), nem bizonyított helyzetnél célzott további vizsgálat.
3. Rendeltetési, használati, minőségi és életciklusprofil: díszlet versus hosszú távú épület, rövid render versus tartósan használható asset.
4. Kötelező alkalmassági feltételek: kompetencia, jogosultság, eszköz, anyag, környezet, idő, bizonyíték és biztonság. Kemény kizárást költségpontszám nem írhat felül.
5. Belső és külső ellátási lehetőségek szétválasztása: ténylegesen rendelkezésre álló / visszaigazolt / potenciálisan beszerezhető / nem ismert. Külső partner bevonása nem azonos saját igazolt képességgel.
6. Erőforrás-terv munkafázisonként: állandó, ütemezett, időszakos, feltételes és vészhelyzeti igények. A teherautót a ki- és elpakolásra foglaljuk, a bontóvésőre feltételes hozzáférési/készenléti terv készül.
7. A teljes életciklusra, kockázatra, késedelemre, ellenőrzésre, visszajavításra és koordinációra értékelt megoldások bemutatása.
8. Megrendelői egyeztetés és explicit jóváhagyott terjedelem; a vállalás külön kapacitás- és feltételvizsgálat után léphet hatályba.
9. Jóváhagyott végrehajtás, minőségi ellenőrzés, átadás és a pozitív/negatív bizonyítékok rögzítése. A munkafázisok végén az ideiglenes erőforrások felszabadulnak.

## 4. Kötelező Responsibility, Commitment & Warranty domén

A CFF szerződéses, teljesítési és minőségellenőrzési részének **kötelező integrált része** a kétoldalú felelősség-, kötelezettség-, átadás-átvétel- és garanciakezelés.

### 4.1 Fogalmi elválasztás

| Fogalom | UEFF követelmény |
| --- | --- |
| Szereplő / szerződéses fél | Jogi vagy szervezeti fél, jogosult képviselő, pontos szerződés- és verzióhivatkozás |
| Felelősségi hozzárendelés | Ki szervezi, ellenőrzi, illetve teljesíti a feladatot; a jogi felelősség ettől elkülönül |
| Kötelezettségvállalás | Kötelezett, jogosult, szolgáltatás, tárgy, mennyiség, minőség, határidő, feltételek, bizonyíték |
| Kölcsönös teljesítési előfeltétel | Ki és meddig biztosítja az áramot, helyszínt, alapanyagot, jogokat, hozzáférést és információt |
| Átadás / átvétel / elfogadás | A teljesítés bejelentése, ellenőrizhetősége, hibajegyzék, igazolt és vitatott eredmény |
| Szavatosság / jogszabályi jótállás / önkéntes kereskedelmi garancia | Eltérő jogcímek, kötelezettek, időszakok, jogok és feltételek |
| Hibabejelentés és jogorvoslat | Bejelentés, vizsgálat, oksági bizonyíték, határidők, javítás/csere/egyéb megoldás, vitakezelés |

A kötelezettség nem pusztán a „feladat felelőse” mező: meg kell őrizni az elfogadott feltételeket és azok későbbi teljesülését, továbbá a másik fél saját kötelezettségeit. A teljesítés és az elfogadás elkülönül; a **NEM ELLENŐRIZHETŐ** állapot nem alakítható automatikusan PASS-szá vagy FAIL-lé.

### 4.2 Hűtőszekrény-teszt: két külön ok és két külön kötelezettség

- **Áramellátás hiánya:** ha a megállapodás alapján a megrendelő biztosítja, teljesítési/tesztelési előfeltétel hiányzik. A készülék működőképessége ettől még ismeretlen; a vizsgálat blokkolható, de a termék nem minősíthető pusztán ezért hibásnak vagy hibátlannak.
- **Kompresszor hiánya:** ha a kivitelező vállalta a komplett hűtő átadását, az alkatrész hiánya önálló, bizonyítható hibás/hiányos teljesítés. A hiányzó megrendelői áramellátás nem mentesíti automatikusan ez alól.
- **Mindkettő fennállhat:** külön esemény, felelős fél, határidő és bizonyíték; oksági és jogi következményt nem lehet mechanikusan egyetlen félre terhelni.
- **Garancia:** a jogszabályi kötelezettségek és az önként vállalt feltételek külön rögzítendők. A rossz használat vagy előfeltételhiány nem szüntethet meg automatikusan minden törvényes igényt; ok, joghatóság, konkrét hiba és bizonyíték vizsgálandó.

### 4.3 Vállalási és igénykezelési állapotok

- Vállalás: `DRAFT → PROPOSED → ACCEPTED → ACTIVE → FULFILLED / BREACHED / CANCELLED / DISPUTED`.
- Teljesítésigazolás: `SUBMITTED → UNDER_REVIEW → VERIFIED / DEFECTIVE / NOT_VERIFIABLE / DISPUTED`.
- Garanciális/szavatossági igény: `REPORTED → ACKNOWLEDGED → INVESTIGATING → DECIDED → REMEDY_IN_PROGRESS → RESOLVED / DISPUTED`.

Állapotváltást csak jogosult szereplő és a szükséges bizonyíték végrehajtásával szabad véglegesíteni. A vita, a bizonytalan okság vagy a hiányzó adat külön kezelendő; a UEFF **nem bíró vagy önálló jogi döntéshozó**.

### 4.4 Adatigény

Logikai rekordok: `party`, `party_role`, `agreement`, `agreed_baseline`, `obligation`, `obligation_dependency`, `precondition`, `responsibility_assignment`, `acceptance_criterion`, `delivery_record`, `inspection_record`, `defect_record`, `cause_assessment`, `warranty_policy`, `warranty_coverage`, `warranty_claim`, `remedy`, `dispute`, `decision_record`, `evidence_reference`.

Minden releváns rekordhoz kellhet: szerződés/jogszabály eredete, érintett fél és képviseleti jogosultság, terjedelem- és definícióverzió, időbélyeg, érvényesség, bizonyíték, szerepköralapú hozzáférés, változtatási/elfogadási esemény. A jogi részletszabályok területi illetékességhez kötöttek: a rendszer nem használhat globálisan egyetlen garanciamodellt.

## 5. Váratlan esemény és scope-korlát

Új hiba esetén: észlelés és bizonyíték → érintett munka biztonságos megállítása → szükséges azonnali veszélyelhárítás a meglévő jogosultsági szabályok szerint → diagnózis → minimálisan szükséges javítási alternatívák → költség-/határidőhatás és a felek kötelezettségei → jogosult jóváhagyás → végrehajtás → ellenőrzés → eredeti munkafolyamat folytatása.

Az UEFF nem hozhat létre automatikusan új célt, nem bővítheti önkényesen a szerződéses terjedelmet, nem vállalhat a megrendelő nevében új kötelezettséget. A biztonsági vészhelyzet nem jogosít fel aránytalan vagy nem engedélyezett teljes projektre.

## 6. Motorfüggetlen tartós végrehajtási szerződés

Verziózott workflow-/feladatdefiníció; `TASK`, `DECISION`, `FORK/JOIN`, `TIMER`, `EVENT_WAIT`, `APPROVAL`, `QUALITY_GATE`, `SUBWORKFLOW`, `COMPENSATION`, `TERMINAL` csomópontok. Kötelező: durable állapot, atomikus claim/lease, fencing, idempotencia, outbox/inbox, retry-szemantika, eseménydeduplikáció, kompenzáció és verziótudatos folytatás. Külső nem-idempotens műveletre általános exactly-once ígéret tilos.

A UEFF üzleti tervet csak jóváhagyott `agreed_baseline`, teljesíthetőségi igazolás, élő előfeltétel-ellenőrzés és szükséges foglalás után adhat át az aktuális operatív workflow-nak. Egy workflow nem sajátíthatja ki vagy írhatja felül az üzleti célt és vállalást.

## 7. Meglévő CFA3-hatóságok változatlan határai

| Meglévő határ | UEFF viszony |
| --- | --- |
| Orchestration Workforce / Director | Újrahasznosított feladatfelbontás, determinisztikus alkalmasság és delegáció |
| Work Management | A feladatszervezési alapigazság nem duplikálódik |
| Security / Identity / UAF / Central MCP Gateway | Jogosultság és mellékhatás-közvetítés minden végrehajtásnál |
| Host Resource Broker / Hardware Safety | CPU/GPU/NPU, elhelyezés és fizikai resource lease kizárólagos hatósága; UEFF tervezési foglalása nem HRB-lease |
| Model Router | Kizárólagos AI-modell- és providerszelekció |
| Journal / Evidence & Gate | Hiteles bizonyíték és végső PASS/VERIFIED-hatóság, UEFF értékelés nem egyenértékű velük |
| License & Rights / Donor Registry | Jogok, licenc és jóváhagyott referenciaforrások; donorjegyzék nem engedély |
| Current Host | Külön fizikai bevezetési / PASS kapu, tervdokumentum nem runtime-bizonyíték |

CPU-only alapútvonal és kötelező felhőmentesség. A külső erőforrás, szakember, modell vagy cloud-opció csak önkéntes, külön jóváhagyott integráció lehet.

## 8. Bevezetési döntési kapuk és elfogadási esetek

A **terv beillesztése nem implementációs engedély**. Későbbi külön döntések: perzisztens tárolási motor és PostgreSQL-séma; workflow-runtime összehasonlítás; API/állapotgépek véglegesítése; Current Host hatás és fizikai tesztek; jogi/szavatossági országprofilok és vállalási jogosultságok.

Elfogadási minták: rövid távú díszlet vs. tartós székház; egyszeri szakember vs. állomány; csak a rakodási szakaszban szükséges teherautó; feltételes bontóvéső; áramhiány miatti `NOT_VERIFIABLE`; kompresszorhiány miatti `DEFECTIVE`; kettős mulasztás független kezelése; garanciális határidő/joghatóság; hibás worker lease/retry; megrendelő által jóvá nem hagyott scope-módosítás tiltása; offline CPU-only működés.

## 9. Dokumentációs hatás és átmeneti szabály

Ez **célarchitektúra-tervi kiegészítés**, nem a jelenlegi Temporal-alapú kód, workflow-k, tesztek, agentek vagy hatósági szerződések migrációja. A régebbi Temporal-kizárólagosságot kimondó operatív dokumentumok **a fennálló implementáció állapotára** igazak. A UEFF célmotorjának kijelölése **nyitott**, így az új terv és az aktuális üzemeltetési tény nem téveszthető össze. A migrációhoz külön explicit tulajdonosi döntés és hiteles tesztbizonyíték szükséges.

**Referencia:** `canonical/FA3-PLATFORM-001.json`, `canonical/FA3-PLATFORM-BINDING-RECONCILIATION-001.json`, `canonical/FA3-ORCHESTRATION-WORKFORCE-REGISTRY-001.json`. A UEFF célarchitektúrájának státuszát a kapcsolódó kanonikus döntés és Reuse Assessment rögzíti.
