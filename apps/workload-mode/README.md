# Workload Mode

Standalone-first Linux workload state and interoperability core for AIMode and RenderMode.

## Materialized in this change

- D-Bus service `org.workloadmode.Manager1`;
- AI / RENDER / GAME effective-mode composition;
- typed external workload registration: OBSERVED / COORDINATED / MANAGED;
- FA3 handshake that delegates FA3 physical resource authority to the existing HRB;
- GameMode D-Bus availability/status observation without making GameMode a dependency;
- `workmodectl` and `workmoderun` plus AIMode/RenderMode aliases;
- Blender/Bforartists render-lifecycle reference adapter;
- mandatory FA3 install service/bridge packaging.

This initial runtime intentionally performs **no privileged host-resource mutation**. systemd/cgroup placement, vendor GPU telemetry and physical performance tuning remain current-host evidence-gated. The absence of those providers must never be represented as a runtime PASS.

### Standalone

```bash
deployment/workload-mode/install.sh
workmodectl status
aimoderun --domain AI your-command
rendermoderun --domain RENDER your-command
```

### FA3-required installation

```bash
deployment/workload-mode/install.sh --fa3-required
```

FA3 is a dependency consumer of Workload Mode; Workload Mode does not depend on FA3.
