# FA3 Skill Fabric Inspector — read-only Control Center projection

Date: 2026-09-28. Stacked implementation: PR1 source audit → PR2 exact-byte activation → PR3 opt-in agent/language binding → PR4 GUI and evidence boundaries.

The existing Qt6/QML Control Center exposes \`SkillFabricService\` as \`fa3SkillFabric\`. The service reads the existing \`canonical/skill-registry.json\` (five FA3-native quality skills) and the *local* \`reports/skill-fabric-gate-report.json\`, reporting the latter strictly as a **static/reference gate**. It never creates authorization, activation, runtime evidence, a provider, a daemon or a new skill authority. The GUI route \`decision.skill-fabric\` also appears in global search and from the existing Agent Action Center, Context Inspector, Decision Inspector and Language Control surfaces.

**Evidence boundary:** this service does not have an authenticated CAP-080 current-host evidence bridge and therefore \`currentHostVerified\` remains false. Even a user-supplied or stale report claiming \`current_host_runtime_claim=true\` is displayed as \`UNTRUSTED_RUNTIME_CLAIM\`, not host PASS. The UI shows only registry metadata and a static report SHA-256; it does not claim that a skill was loaded, executed or approved on the active machine. Missing repository/report appears as unavailable, not PASS.

**Physical next step:** after independently verified native-skill issuer receipts are wired through the existing Evidence authority and CAP-080 has been run physically, add a *separately authenticated* read-only current-host evidence adapter and revise this status with appropriate negative, stale-record and source-tamper tests. Do not infer runtime PASS from JSON file presence, CI or reference tests.

**Hardware Audit:** Qt6/QML, no GPU/vendor/desktop lock-in, Wayland preferred and X11 supported. CPU-only backend; any future model-assisted semantic analysis must use Model Router and HRB and the existing display GPU arbitration. Software coexistence: reads repository and local report only; no global host agent/skill directory mutation.
