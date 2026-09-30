# FA3 SCP Manager

Qt 6/QML standalone projection for the **FA3 Secure Communication & Proxy Fabric**.

The application uses the same shared source as embedded FA3 applications:

- `apps/shared/scp/SCPSettingsService.{h,cpp}`
- `apps/shared/scp/qml/SecureCommunicationSettings.qml`

It is a projection and draft-intent surface, not a new security authority. Runtime discovery reports only `UNAVAILABLE` or `DISCOVERED_NOT_ADMITTED`; it does not promote providers.

## Build

```bash
cmake -S apps/fa3-scp-manager -B build/fa3-scp-manager -GNinja -DCMAKE_BUILD_TYPE=Release
cmake --build build/fa3-scp-manager
./build/fa3-scp-manager/fa3-scp-manager
```

## Draft changes

The GUI can create local `DRAFT_NOT_SUBMITTED` JSON ChangeSets under the user's FA3 data directory. It never directly mutates firewall, PKI, provider, canonical repository or privileged host state.

## Current Host

Physical runtime promotion is **PENDING**. See `canonical/FA3-SCP-CURRENT-HOST-001.json`.
