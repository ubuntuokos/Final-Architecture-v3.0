# FA3 multi-distribution application runtime discovery

FA3 external applications may exist in more than one packaging form at the same time. The shared resolver in `src/fa3_application_runtime_resolver.py` extends the existing Host Adaptation lifecycle; it is discovery and health evidence, not installation, update or execution authority.

## Supported installation classes

The canonical registry recognizes `NATIVE`, `DEB`, `RPM`, `PACMAN`, `FLATPAK`, `SNAP`, `APPIMAGE`, `PORTABLE` and `MANUAL`. Native package ownership is identified where the host package database can prove it. Flatpak and Snap instances retain their application/package IDs. AppImage and portable binaries are accepted only through explicit configured paths rather than recursive filesystem scanning.

Desktop entries are a discovery source for distribution packages whose executable is not exposed under the expected PATH alias. Presence alone never proves usability.

## Health and coexistence

Every execution-relevant candidate has a bounded, application-specific smoke probe. A candidate that exists but cannot load its runtime libraries is `UNHEALTHY`, remains visible in evidence, and cannot satisfy a Current Host prerequisite. Other independently installed instances remain available; discovery does not uninstall or repair the broken instance.

Multiple Bforartists/Blender combinations are therefore valid, including Bforartists DEB with no Blender, both applications as Flatpak, Bforartists native plus Blender Snap, portable/AppImage builds, and explicitly registered custom paths.

The same semantics apply to other shared external applications. The initial registry also includes GIMP, Krita and LibreOffice identities so later consumers can reuse the same discovery layer rather than introducing application-local package-manager logic.

## Selection boundary

Discovery never performs silent runtime fallback. For user work, the existing Engine Selection Fabric or application-specific policy remains authoritative for the requested engine/application. During physical qualification only, a deterministic healthy candidate may be selected to prove a generic capability; that selection is explicitly marked `QUALIFICATION_PROBE_ONLY_NOT_USER_RUNTIME_SELECTION`.

Current Host qualification uses a deterministic **proof-only** healthy-candidate preference. This does not alter the user's engine choice: application/project/task runtime selection remains with the existing Engine Selection Fabric or application-specific policy. A future explicit qualification override must be introduced through a typed, audited input path rather than an inherited ambient environment variable.

## Current Host

CAP-016 and the FULL-525 preflight use the same shared resolver. The failed run `37109414350` remains immutable FAIL evidence. This change requires a fresh exact-head physical 175/525 run before #559 can close; prior receipts are not relabeled or reused.
