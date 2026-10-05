# FA3 Marketing – végleges Agent Native/Jev megvalósítási terv

Állapot: **statikus és referencia-megvalósítás kész; a három szolgáltató production runtime admissionje függőben**.

## Kötelező architektúra

Minden GUI-, agent-, CLI-, MCP-, A2A- és automatizációs kérés ugyanazon UAF Action Contracton halad át. Az engedélyezés és az alkalmazandó egyszer használatos emberi jóváhagyás megelőzi a szolgáltatói műveletet. A policy által adott, nem üres és korlátozott jelölthalmaz determinisztikus szűrése megelőzi az opcionális Jev advisory reranket. A Jev nem bővíthet jelölthalmazt, nem engedélyezhet műveletet, nem válhat identity-, policy-, secret-, workflow-, resource- vagy evidence-authorityvá. Minden döntéshez DecisionReceipt és ContextEnvelope tartozik.

Az élő szolgáltatói útvonal: `surface → UAF → auth/approval → deterministic policy → optional advisory → HRB/Secret Broker → provider adapter → evidence`.

## Szolgáltatói felelősségek

| Komponens | Konfigurált szerep | Nem lehet |
|---|---|---|
| Twenty | CRM-workspace és kontakt-projekció | kanonikus customer/consent authority |
| Mautic | kampány- és automatizációs projekció | kanonikus campaign/workflow authority |
| listmonk | newsletter-előkészítés és jóváhagyott dispatch | consent/suppression megkerülő küldési authority |
| Jev-kompatibilis advisory | bounded context selection, ranking, classification, retry/stop/continue, semantic validation | authorization vagy közvetlen provider mutation |

## Munkacsomagok és belépési feltételek

| ID | Eredmény | Állapot | Belépési feltétel |
|---|---|---|---|
| MKT-00 | PR #65 hasznos részeinek újraértékelése | kész | current main |
| MKT-01 | kanonikus döntés, Decision Fabric contract, 15 UAF-akció | kész | authority delta = 0 |
| MKT-02 | determinisztikus decision runtime és negatív tesztek | kész | no candidate expansion |
| MKT-03 | Mautic/Twenty/listmonk UAF adapterek | referencia mód kész | élő módhoz Secret Broker + admission |
| MKT-04 | consent/suppression/approval negatív current-host követelmények | kész | v2 receipt schema |
| MKT-05 | AI Studio állapot és műveleti felület | státuszprojekció kész | valódi mutáció továbbra is UAF |
| MKT-06 | self-hosted current-host admission workflow | kapu kész | adminisztrátor által admitted host driver és valódi receipt szükséges |
| MKT-07 | élő provider materializáció és restart/roundtrip | függőben | szolgáltatói image/adat/egress döntés és Secret Broker receptek |
| MKT-08 | backup/restore, upgrade/rollback, üzemeltetési runbook | függőben | MKT-07 PASS |
| MKT-09 | production promotion | függőben | pontos `CURRENT_HOST_PRODUCTION_E2E_PASS` |

## Felvételi határ

A `[self-hosted, linux, x64, fa3-current-host]` runneren keletkezett, nem szintetikus v2 receiptnek mindhárom providert, az UAF/no-bypass és Secret Broker útvonalat, a pozitív roundtripokat, a consent/suppression/approval negatív eseteket, a csak belső SMTP sinket, a delivery reconciliationt és a restart recoveryt is PASS-ra kell igazolnia. A statikus kapu és a referencia adapter PASS **nem production PASS**.

## Következő legnagyobb értékű lépések

1. Rögzíteni kell a production image-digesteket, adatbázis- és hálózati topológiát, valódi outbound SMTP/egress döntést és rollback célokat.
2. Secret Broker receptekkel kell materializálni a három provider rövid életű credential-projekcióját; tartós `.env` vagy környezeti secret nem elfogadható.
3. A runneren adminisztrátor által felvett `/usr/local/libexec/fa3/marketing-current-host-e2e` driverrel létre kell hozni a valós v2 receiptet, majd futtatni a `./bin/fa3-enforce marketing-current-host` kaput. A driver telepítése külön host-üzemeltetési döntés; a repository nem emelhet önkényesen host-jogosultságot.
4. Csak ezután következhet backup/restore, upgrade/rollback és operátori runbook, majd production promotion.

## Változatlan FA3 alapelvek

A capability-szám 143, az authority-delta 0. A HRB kizárólagos resource authority; a Secret Broker kizárólagos secret-projekciós határ; a Central MCP/UAF útvonal nem kerülhető meg. CPU-only működés kötelező, accelerator cardinality `0..N`, vendor/SKU/topológia nem globális feltétel. Wayland preferált, X11 támogatott, KDE-only core tilos. Az AI-kommunikáció ember számára olvasható és auditálható; privát vagy emergens nyelv nem megengedett.
