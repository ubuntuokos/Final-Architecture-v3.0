# FA3 Coach — teljes alkalmazásarchitektúra és megvalósítási szerződés (v0.2)

**Dátum:** 2026-09-28 · **Állapot:** architekturális terv, **nem** kész alkalmazás, **nem** production PASS.  
**Kiindulópont:** \`FA3-COACH-001\`, \`FA3-COACH-CONTRACTS-001\`, \`FA3-PROVIDER-COACH-LOCAL-001\` v0.1.0; current-host: \`PENDING_CURRENT_HOST\`.  
**Kapcsolódás:** issue #499; FA3 Goal Execution PR #476/#479 és issue #482. A szeptember 28-án elkezdett \`fa3/coach-complete-floating-app-20260928\` ág **csak korai helyi GUI-vázlat és service-prototípus**; architekturális megfelelőség és production működés nélkül nem merge-elhető. E terv az alkalmazás és a működő backend elsőbbségét rögzíti.

## 0. Mi a termék?

A Coach egy **FA3-natív, hosszabb időn át használható, bizonyítékérzékeny cél- és haladástámogató alkalmazás**. Egyetlen közös magja szolgálja ki (1) a saját teljes Coach munkateret, (2) a Control Centerben és más FA3-alkalmazásokban megnyitható kontextuspanelt és (3) a tetszés szerint elhelyezhető lebegő Coach ablakot. **A GUI nem a termék magja; azonos adatok, jogosultságok és üzleti szabályok minden nézetben.**

A Coach nem projektmenedzser-, oktató-, agent- vagy végrehajtási hatóság. A felhasználó választja meg a célt, a vállalást, a zavarás és adatgyűjtés mértékét, és bármikor megállíthatja a támogatást. A Coach cél- és döntéstámogatást ad, nem kényszerít, nem értékeli a felhasználó személyiségét, nem alkalmaz klinikai/terápiás szerepet.

### Három használati profil

| Profil | Konkrét tárgy | Adatforrás és korlát |
| --- | --- | --- |
| \`USER_SELF\` | Saját munkacél, tanulási terv, fókusz, heti áttekintés | Alapból kizárólag a felhasználó által megadott adatok; minden további olvasás/mentés opt-in. |
| \`FA3_PROJECT\` | Projekt, workstream, alkalmazás, PR, kreatív produkció | Kijelölt projekt/Task Manager/Journal kanonikus olvasási projekciói; natív projektfájlok változatlanok. |
| \`AI_AGENT_WORK\` | Ügynöknek kiosztott cél és elvárt eredmény | Agent Workload/Temporal esemény, UAF-intent, független Evidence/Gate státusz; az ügynök önjelentése nem bizonyítás. |

A profilok között nincs automatikus személyes adatszivárgás vagy csendes projektváltás.

## 1. Újrahasznosítás és donorlekérdezés — minden implementáció előtt

A \`FA3-DONOR-REFERENCE-REGISTRY-001\` és \`FA3-REUSE-DISCOVERY-001\` kötelező. Az alkalmazás létrehozásakor \`ApplicationIntent\` és \`ReuseAssessment\` szükséges, valamint az alkalmazás kölcsönös donor-kapcsolatai kerüljenek be az alkalmazás/donor indexbe.

A meglévő registryből a következő *különálló* forrásrekordok alkalmazhatók:
- \`FA3-DONOR-POPONLINE63-NORTH-STAR-001\` — ellenőrizhető cél/Definition of Done; **CANDIDATE**.
- \`FA3-DONOR-VECTORIZE-IO-HINDSIGHT-001\` — korábbi döntés és kontextus provenienciájának mintái; **ACCEPTED_REFERENCE**, de nem saját Coach-memory.
- \`FA3-DONOR-TEMPORALIO-SDK-PYTHON-001\` — meglévő FA3 Temporal integráció erősítése; **CANDIDATE**.
- \`FA3-DONOR-LANGFUSE-LANGFUSE-001\` — opcionális trace/review UX, nem új Evidence authority; **CANDIDATE**.
- \`FA3-DONOR-PROMPTFOO-PROMPTFOO-001\` — offline adversarial/regressziós minták; **CANDIDATE**.
- \`FA3-DONOR-LANGCHAIN-AI-LANGGRAPH-001\` — megszakítás/folytatás kutatási minta, **nem** második durable orchestrator; **CANDIDATE**.

A #499 issue-ban azonosított *új jelöltek* még **nem egyenlők a canonical registrybe való felvétellel**: \`super-productivity/super-productivity\` (fókusz és időkeretek), \`ActivityWatch/activitywatch\` (kifejezett hozzájárulásos, helyi aktivitásadat), \`jontkaufman/LifeOS\` (strukturált beszélgetés/check-in, kizárólag nem klinikai referenciák). Forráskulcsonként deduplikálva CANDIDATE-ként rögzítendők; a kód és minden függőség licence, upstream commitja, biztonsága és disztribúciós alkalmassága külön vizsgálandó. Teljes donoralkalmazás beépítése nem cél.

## 2. Teljes felhasználói munkafolyamat

1. **Célfelvétel:** a felhasználó választ profilt és projektet, megfogalmazza az eredményt, korlátokat, out-of-scope elemeket, időkeretet és megengedett adatforrásokat. Természetes nyelv még semmire nem jogosít.
2. **Céltisztázás:** hiányzó, *lényeges* döntések felismerése; mérhető, külön ellenőrizhető \`SuccessCriterion\`-ok és felhasználó által szerkeszthető mérföldkövek. A cél elfogadása kifejezett user-művelet.
3. **Választható munkaterv:** cél → kritérium → mérföldkő → munkafeladat/függőség leképezés. Reuse Discovery + donor index; források, kapacitások és tiltások ellenőrzése. A Coach javasol; a Manager/Director/Workforce képezi és birtokolja az operatív munkatervet.
4. **Vállalás és jogosultság:** külön gomb a személyes vállaláshoz; ettől külön Security/UAF approval a valódi módosító művelethez. A vállalás nem hozzájárulás megfigyeléshez vagy tartós memóriaíráshoz.
5. **Munkavégzés közbeni támogatás:** kiválasztott cél, következő bizonyítható lépés, egyértelmű blokkoló, határidő/függőség, opcionális fókuszblokk. A munkakörnyezetből csak explicit engedélyezett, provenienciával rendelkező események vehetők át.
6. **Checkpoint:** a felhasználó kérésére vagy külön jóváhagyott ütem szerint olvasás a tényleges kanonikus projekt-/work-/Journal-/Evidence-forrásokból. Minden megfigyelés \`FACT / USER_REPORT / INFERENCE / UNAVAILABLE\` jelölést kap.
7. **Eltérésvizsgálat:** ténylegesen igazolt rész, még ellenőrizetlen feladat, kifutó idő/budget, blokkertípus és pontos hiányzó bizonyíték; legfeljebb néhány konkrét választási lehetőség.
8. **Javítás/delegálás:** Coach javaslat → emberi döntés vagy már jóváhagyott policy → typed Mentor/Manager/Director/Ellenőr/UAF-intent. Megnőtt költség, scope, új agent/provider vagy destruktív hatás csak új engedéllyel.
9. **Lezárás:** a Coach megjeleníti a végső állapotot **kizárólag a kanonikus Evidence/Gate alapján**. A részleges teljesítés, BLOCKED, PAUSED, CANCELLED és VERIFIED különálló.
10. **Visszatekintés:** projektzáró/heti retrospektív tényekkel, tanulságokkal, vállalt következő lépéssel. Keresztprojekt-memória csak kifejezett felhasználói hozzájárulás és a meglévő FA3 Memory-hatóság révén.

## 3. Funkciómodulok (az alkalmazás, nem a GUI)

### COACH-CORE — életciklus és szabályok
- A meglévő \`FA3-COACH-CONTRACTS-001\` kompatibilis, verziózott kiegészítése; nincs párhuzamos \`GoalContract\`.
- Személyes vállalások, checkpointok, idempotens javaslat-azonosítók, felhasználói pause/stop, állapotprojekció.
- Szerződés és policy ellenőrzés determinisztikus, modell nélkül is működik.

### COACH-GOAL — célok, részcélok, elfogadás
- A meglévő \`FA3-GOAL-EXECUTION-CONTRACTS-001\` \`goal_id\`, \`revision\`, \`owner_ref\`, \`workspace_ref\`, \`scope\`, \`acceptance_criteria\` és \`execution_policy\` adataira épül.
- Célverzió változásakor a korábbi jóváhagyás/eredmény **nem öröklődik automatikusan**.
- Human/agent/projekt típusokhoz típusos szemantika és kimenet, nem külön logika mindegyik GUI-ban.

### COACH-OBSERVE — megfigyelési projekció
- Adapterek a meglévő Task Manager/Manager, Director/Workforce, Agent Workload, Temporal, Journal, Evidence/Gate, alkalmazásspecifikus projektállapotokhoz.
- Mindegyik megfigyelés: forrás, objektumazonosító, exact revision/digest, időpont, freshness, adatkezelési hatókör, bizonyítási státusz.
- Hiányzó, nem elérhető vagy túl régi adat \`UNKNOWN/STALE\`; nem „minden rendben”.

### COACH-CHECKPOINT — haladás és bizonyíték
- Kritériumonként: \`NOT_STARTED / REPORTED / EVIDENCE_PENDING / REJECTED / VERIFIED\`; utolsó csak hiteles kanonikus receipt alapján.
- Valós, függetlenül igazolt eredmény, felhasználói jelzés és AI-állítás **három külön mutató**, soha nem mosódnak össze.
- Teljesítési százalék csak a megadott nevezővel és módszertannal; külön „önjelentett” és „hitelesített” vizualizáció.

### COACH-BLOCKER — eltérés, tudáshiány, akadály
- Okcsoportok: \`KNOWLEDGE / DEPENDENCY / AUTHORIZATION / RESOURCE / RUNTIME / EVIDENCE / SCOPE / PERSONAL_CHOICE / UNKNOWN\`.
- A \`KNOWLEDGE\` Mentorhoz; \`DEPENDENCY/PRIORITY\` Managerhez; \`AUTHORIZATION\` meglévő Security approval-felülethez; \`EVIDENCE\` Ellenőrhöz; operatív művelet typed UAF/MCP-delegáláson keresztül.
- Következő lépésnél a Manager prioritás- és megszakíthatósági döntése kötött; Coach nem írja felül.

### COACH-PLAN — választható következő lépések és adaptáció
- Determinisztikus elsőbbség: biztonsági/engedély blokkolás → bizonyítás nélküli kötelező kritérium → függőség → tervben következő mérföldkő.
- A Decision Fabric/Model Router opcionális szemantikus javaslatot adhat *csak* az eleve jogosult opciók közül; forrás és indoklás megjelenítendő.
- Bounded replanning, rollback-proposal és budget-korlát; nincs végtelen saját javító ciklus és önjóváhagyás.

### COACH-COMMUNICATE — coaching kommunikáció
- Kontextusfüggő kérdések, érthető magyarázatok, rövid vagy részletes stílus, többnyelvű Language Fabric, magyar GUI.
- Kommunikáció és domainállapot szétválasztása; az LLM válasza önmagában sem goal update, sem approval, sem evidence.
- Emberi céloknál segítő, nem manipulatív hangnem; tilos személyiségpontozás, rejtett befolyásolás, diagnózis.

### COACH-FOCUS — választható produktivitási eszközök
- Kézi, helyi 25/45/60 perces fókuszblokk; opcionális szünet és feladathoz kapcsolás.
- ActivityWatch-szerű megfigyelés csak explicit, visszavonható, adatfajtánkénti opt-in után; alapból OFF. Nincs automatikus képernyőrögzítés vagy produktivitás-/személypontszám.
- Fókuszidő soha nem bizonyítja a teljesített eredményt.

### COACH-REVIEW — visszacsatolás, visszatekintés
- User-requested vagy engedélyezett heti/projektzáró review.
- Tények, bizonyíték, változás, feloldott/nyitott akadályok, következő döntés; a bevont Memory-művelet külön jóváhagyandó.
- Semmilyen történeti pillanatkép nem írható felül.

## 4. Adatmodell és interfészek

**Hivatkozott, meglévő canonical objektumok:** \`UserOwnedGoal/GoalRevision\` (Goal Execution), \`SuccessCriterion\`, \`AgentWorkloadTask\`, \`UAF ActionContract\`, \`WorkItem\`, \`JournalRef\`, \`EvidenceReference\`, \`ApprovalRef\`, \`MemoryRef\`.

**Coach-specifikus, nem hatósági adatok:**
- \`CoachSessionContext\`: \`session_id, user_ref, profile, workspace_ref, allowed_context_refs, privacy_scope, created_at\`.
- \`CoachCheckpoint\`: \`checkpoint_id, goal_id, goal_revision, criterion_refs, observation_refs, verified_evidence_refs, requested_by, freshness\`.
- \`CoachObservation\`: \`observation_id, source_authority, source_object_ref, exact_revision, classification, observed_at, collected_with_consent\`.
- \`CoachBlocker\`: \`blocker_id, reason_class, affected_criterion_refs, source_refs, status, owner_ref\`.
- \`CoachNextStepProposal\`: \`proposal_id, goal_revision, source_blockers, expected_effect, target_role, necessary_approval, evidence_to_collect, expiry\`.
- \`CoachDelegationIntent\`: \`intent_id, target_existing_authority, goal_revision, requested_effect, approval_ref, state\`. \`PROPOSED\` nem azonos \`SUBMITTED\` vagy \`EXECUTED\` állapottal.
- \`CoachFocusBlock\`: \`duration, task_ref, local_start, paused, completion_self_reported\`; nem kanonikus evidence.
- \`CoachUIPreferences\`: hely/monitor/nézet/méret/opacity/pin/értesítési preferencia. Nem kerül a célok kanonikus tárába.

**Élettartamok:** (A) session cache: csak memóriában, (B) opcionális felhasználó által exportált helyi vázlat: nem kanonikus és importkor minden approval/evidence demóció, (C) projekt- vagy workstream-cél: meglévő jóváhagyott goal/project authority alatt, (D) keresztprojekt memória: csak meglévő FA3 Memory és külön hozzájárulás, (E) Temporal/Journaling: események és munkafolyamatok meglévő hatóságai alatt. A Coach nem hozhat létre rivális adatbázist vagy második durable lifecycle-t.

**Backend API-terv (lokális, típusos, jogosultságkapuzott):** \`create_goal_draft\`, \`propose_goal_revision\`, \`request_checkpoint\`, \`get_checkpoint_projection\`, \`get_next_step_candidates\`, \`propose_blocker_resolution\`, \`propose_delegation\`, \`request_human_commitment\`, \`pause_coaching\`, \`stop_coaching\`, \`request_review\`, \`export_local_draft\`. Az adatíró és effectful műveletek meglévő authority-hoz delegálnak; az API-ban \`PROPOSAL_ONLY\` és \`PENDING_APPROVAL\` az alapállapot.

## 5. Kapcsolódás az FA3-hoz — pontos felelősségi határok

| Komponens | Coach feladata | Mi marad a komponens saját hatásköre? |
| --- | --- | --- |
| Mentor | Tudáshiány és tanulási cél átadása | Oktatás, készségmérés és tudásanyag |
| Manager / Task / prioritás | Blokker- és fókuszjavaslat, statusprojekció | Munkaterv, függőség, prioritás és megszakíthatóság |
| Director / Workforce | Elfogadott cél és kritériumok átadása | Typified task-DAG és végrehajtó szereplők |
| Temporal + Agent Workload | Checkpointokra figyelő, jóváhagyott tartós folyamat igénylése | Durable workflow, timeout, retry, pause/resume, agent admission |
| UAF / MCP Gateway | Csak típusos végrehajtási szándék | Tool/action permission és effektív végrehajtás |
| HRB + Model Router | Erőforrás- és modelligény leírása | Fizikai erőforrás/lease és provider/model route |
| Journal / Evidence/Gate / Ellenőr | Provenienciával rendelkező eredményprojekció | Független ellenőrzés és \`VERIFIED\` |
| Security / Secret Broker | Szükséges jóváhagyás jelzése | Jogosultság, titok, approval, audit |
| Donor Registry / Reuse Discovery | Terv előtti kötelező lookup és hatásvizsgálat | Donorjelöltek életciklusa és újrahasznosítási döntések |
| Language Fabric | Magyar és választott nyelvű használat | Fordítás/nyelvi szemantika |
| FA3 natív kreatív appok | Projekt-, jelenet- vagy munkafolyamat-kontekstus megjelenítése | Saját projektformátum és projektállapot |

Az alkalmazásnak nincs kötelező fizetős vagy felhős komponense; működő CPU-only alapprofil kötelező.

## 6. Biztonság, megfigyelés, hardver, coexistence

- **P0 fail-closed:** hamis, hiányzó, elavult vagy más revízióból származó bizonyíték nem haladás. Self-report nem kanonikus PASS. Sem prompt, sem donor, sem szemantikus modellválasz nem engedélyezhet magának actiont.
- **Explicit felhasználói kontroll:** consent per adatforrás; opt-in ütemezés és aktivitásadat; stop/pause minden módon; a mentor/manager delegálás csak látható, visszavonható szándék.
- **Hardware Safety Envelope:** nincs paramétermódosítás és nincs bypass; CPU-only kötelező; 0..N accelerator. Kijelző-GPU AI-feladatra több GPU/NPU jelenlétében csak alkalmazáson belüli konkrét modell+feladat kijelölés után; nincs automatikus bevonás vagy néma fallback.
- **Software Coexistence:** FA3-névterek, fájlok és appazonosítók; külső app uninstall nem előfeltétel; nincs port- vagy global env-eltérítés, nincs saját GPU-foglalás, nincs saját adatbázis vagy idegen konfiguráció átírása.
- **Hibatűrés:** provider/Temporal/MCP hiányában a Coach **továbbra is használható helyi céltisztázásra és kézi tervezésre**, de minden nem elérhető adat explicit \`ADAPTER-GATED\` és a hiteles eredmény státusza \`UNKNOWN\`.

## 7. Csak a működő alkalmazásmag után: teljes GUI-terv

**Egyetlen CoachCore, három elrendezés:** önálló teljes alkalmazás, appba dokkolt kontextuspanel, mozgatható lebegő segítő. A teljes Coach rendelkezik célfa, checkpoint/evidence, blocker, coaching beszélgetés, fókusz és review nézetekkel; a lebegő ablak ezek szűrt, gyors interakciós projekciója.

**Lebegő nézet:** a Control Center Coach ikonja nyitja; kézzel tetszőleges helyre mozgatható és átméretezhető; compact/ikonmód, pin/always-on-top opcionális, opacity, többmonitoros best-effort pozíciómemória, képernyőn kívülre szorult ablak visszaállítása, egyszerű bezárás, billentyűzetes visszahívás. A Wayland kompozitor a globális pozíciót/always-on-top viselkedést korlátozhatja: \`startSystemMove/Resize\` natív API, X11 fallback; **nem** képernyőkoordináta-hack, nem compositor security-bypass, nem állítunk garantált globális pozíciót ott, ahol az OS tiltja.

**Zavarásminimalizálás:** nincs automatikus felugrás bootkor vagy minden eseményre; fókusz/kreatív munkában alapból néma. A user választja meg: csak ikon, compact, normál lebegő, dokkolt, teljes alkalmazás. Csak súlyos, kifejezetten engedélyezett munkafolyamat-változásokhoz küld értesítést.

**Valós bekötés elfogadási kritériuma:** az ablakban megjelenő adatok ugyanabból a typesafe Coach API-ból jönnek, mint a teljes alkalmazásban. Küldés/jóváhagyás/delegálás csak valódi role-chat és meglévő UAF/Policy adapterhez; amíg nincs adapter, **disabled/ADAPTER-GATED**, nem generált színlelt AI-válasz. Magyar nyelv, billentyűzet- és képernyőolvasó-kezelés, kis és többmonitoros elrendezés.

## 8. Implementációs sorrend és külön elfogadási kapuk

| Fázis | Valódi elkészítendő eredmény | Objektív done |
| --- | --- | --- |
| **A0: újrahasznosítás** | Donor-registry source-key dedupe, új jelöltek CANDIDATE, ApplicationIntent/ReuseAssessment, meglévő kód/szerződés inventory | Hiánytalan, forrásazonos metadata; jogi és security status nem állít többet a valósnál |
| **A1: Coach domain/core** | Versioned Coach domain objektumok, validátorok, egységes read model, explicit pause/stop és commitment | Python/Qt unit tesztek, state-transition, forged approval/evidence és visszavonás negatív tesztek |
| **A2: Goal / Manager bridge** | Meglévő GoalContract és source-bound preflight fogyasztása, UserOwnedGoal revision, Manager/Director/Workforce typed átadási szerződés | End-to-end terv–részcél–munkafeladat függőség; nincs külön Goal Registry |
| **A3: adat- és evidence adapterek** | Valós, autentikált Task/Journal/Evidence/approval projekció; stale és hiányzó adat kezelése | Per-criterion proof provenance és exact revision; AI self-reportból nincs VERIFIED |
| **A4: policy-gated delegálás** | Mentor/Manager/Ellenőr/UAF requestek, explicit approval, idempotencia, revocation | Valós adapter, pozitív és negatív permission/fallback/injection esetek |
| **A5: tartós működés** | Egy meglévő Temporal workflow/Agent Workload runtime adapter: checkpoint, pause/resume, leállítás, outage, bounded repair | Crash/replay/duplicate/cancel/revoked approval/renewed HRB admission teszt valódi target hoston |
| **A6: teljes app GUI** | Egy CoachCore-ra kötött saját Qt6 app: célfa, checkpoint, blocker, review, focus, beállítások | Nem mock: azonos domain/API, magyar UI, disabled pending műveletek, Wayland/X11 funkcionális tesztek |
| **A7: lebegő és beágyazott GUI** | Coach ikon, user által elhelyezett overlay, compact/dock/ikon, state sync, többmonitoros fallback | Szabadon mozgatható, képernyőről visszahozható, nem zavaró, nincs fiktív előrehaladás |
| **A8: pilot és production** | FA3 saját projekten és izolált ügynökmunkán hitelesített production E2E, exact-head gate/evidence/release reconciliation | Független bizonyítás mindhárom scope engedélyezési határára; production csak hiteles current-host receipt után |

Minden fázishoz: kód + dokumentáció + regressziós és negatív tesztek + releváns kötelező P0 gate + Hardware Audit és Coexistence. Egyetlen zöld source-only CI nem helyettesít real-host bizonyítékot. A **175-ös baseline változatlan**, új authority és új kötelező külső runtime nélkül. Meglevő történeti evidence soha nem írható felül.

## 9. Minimum end-to-end próbaforgatókönyvek

**Projekt:** „FA3 modul production admission” → adott cél és ellenőrzési kritériumok → Manager DAG → UAF engedélyezett feladat → hiányzó runtime-evidence felismerése → usernek megjelenített egyetlen következő bizonyítható lépés → canonical gate után VERIFIED. Negatív: hiányzó receipt + modell szerint „kész” ⇒ PENDING.

**Személyes munka:** saját 45 perces fókuszcél → kézi checkpoint → opcionális heti review → STOP azonnal megszakítja a Coach-asszisztenciát, személyes feljegyzés nem kerül csendben központi Memoryba.

**AI ügynök:** feladatkiosztás + megengedett résztvevők + költség-/retry-limit → ügynök partial output → független checker hibát jelez → bounded javítás **csak** új/adott jogosultságon belül → nincs self-approval vagy önhitelesített DONE.

**GUI:** ugyanazon projekt megnyitása teljes Coach appban, dock nézetben és lebegő ikonból; azonos kanonikus status, felhasználó által változtatható pozíció, működő close/hide és explicit helyreállítás Wayland/X11 alatt. Az overlay hiánya nem béníthatja meg a Coach magját.

## 10. Repo-munkaszabály a tévesen megkezdett GUI-ágra

A \`fa3/coach-complete-floating-app-20260928\` létező, korai GUI-s ág marad **nem promotálható prototípus**. Nem jelölhető kész Coach alkalmazásnak; nem merge-elhető pusztán látvány vagy QML-gate miatt. Hasznos kódrészletek csak A6/A7-ben, a végleges A1–A5 API-szerződések, licencek, biztonsági és Wayland/X11 tesztek után, célzottan visszaemelve hasznosíthatók. Ez a terv külön tiszta, mainből kiinduló architektúra-ágon készül, kizárólag dokumentációként.
