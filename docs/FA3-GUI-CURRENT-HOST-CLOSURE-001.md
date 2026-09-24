# FA3 GUI current-host closure

The Control Center reference/static build is not physical runtime evidence. GUI runtime promotion requires a real local graphical session on the exact `[self-hosted, linux, x64, fa3-current-host]` runner.

The closure is fail-closed:

1. check out the exact PR/source SHA;
2. run as the non-root runner user;
3. discover an active local Wayland or X11 session using the existing desktop-admission substrate;
4. configure and build `apps/fa3-control-center` from that same source SHA without package installation or network-fetch helpers;
5. force the native Qt platform for the proven session (`wayland` or `xcb`); `offscreen` and `minimal` are forbidden;
6. launch the real `fa3-control-center` process for at least five seconds;
7. require the process to remain alive and free of fatal Qt/QML startup markers;
8. terminate and clean up the probe process;
9. emit a secret-free, hashed-host-fingerprint receipt;
10. validate the receipt with `FA3-GUI-CURRENT-HOST-GATESET-001`.

A PASS receipt may promote **FA3 GUI current-host runtime conformance only**. It does not promote the whole FA3 release, create authority, or bypass the 19-criterion global promotion gate.

The canonical receipt path is `evidence/receipts/fa3-gui-current-host.json`. Until a physical PASS receipt is adopted, `FA3-GUI-RUNTIME-CONFORMANCE-001` remains non-production and fail-closed.
