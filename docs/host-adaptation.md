# FA3 Host Adaptation

`FA3-HOST-ADAPTATION-001` is a non-authoritative lifecycle layer over the existing Hardware Audit, HRB, desktop portability, distribution, coexistence and Evidence boundaries.

## Installation

The installer performs full host discovery and records an immutable installation host profile. Selective materialization plans only implementations relevant to the observed host. The canonical 175-capability model does not depend on how many providers are materialized.

Discovery never grants resource, package, provider or promotion authority.

## Startup

Every FA3 startup re-discovers the live host and compares it with the latest accepted profile, or with the immutable installation profile when no later accepted profile exists.

The drift classes are `NO_DRIFT`, `OBSERVATIONAL_DRIFT`, `RUNTIME_REBIND`, `CONFIG_RECONCILE`, `COMPONENT_ADMISSION` and `SAFETY_BLOCK`.

A detected change does not authorize an update. It is input to the existing admission, distribution, HRB, hardware-safety and evidence authorities.

## Accelerator semantics

Accelerator state is separated into `DISCOVERED -> ELIGIBLE -> ASSIGNED_BY_HRB -> ACTUALLY_USED`. Display ownership is not compute placement, and an HRB assignment is not proof of actual execution. Accelerator-required evidence must separately prove the real execution path. CPU-only remains a valid host mode.

## Desktop semantics

FA3 is Qt6/QML native. Qt desktops use native Qt integration at full strength. KDE Plasma may add KF6 enhancements behind FA3 interfaces. Non-Qt desktops retain canonical functionality through Qt6 plus XDG/freedesktop/portal integration. Wayland is preferred and X11 is supported.

## Selective materialization and coexistence

The materialization output is a plan, not an installer authority. It discovers the native package-manager family and host-relevant provider selectors, after which normal FA3 admission applies. A missing device first makes dependent providers unavailable/inactive; it does not cause automatic uninstall. No fixed host port, upstream uninstall or global environment mutation is introduced.

## Evidence boundary

Installation and live snapshots are facts, not promotion receipts. Static, synthetic, CI, registration or materialization success cannot become physical current-host PASS through this layer.
