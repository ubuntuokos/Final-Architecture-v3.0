# FA3 Agent Workload Runtime — current-host closure

This current-host surface can promote only the native runner on the evidenced host/run. It cannot promote Google AX, Podman, process/VM checkpointing or global FA3.

A real PASS requires a pre-existing FA3 Resource Admission receipt whose workload id is exactly `fa3-agent-workload-native-current-host` and whose HRB authorization is current, externally validated and scope-bound. The existing generic CPU-only HRB authorization bootstrap is not fabricated by this project; until that authorization path exists or an authoritative receipt is supplied, the runtime remains **PENDING_CURRENT_HOST**.

The real collector proves non-root execution, unified cgroup v2, a user-systemd transient scope, actual SIGSTOP/SIGCONT pause-resume behavior, cleanup and the parent static workload gate. The workflow is restricted to `[self-hosted, linux, x64, fa3-current-host]` and is operator-dispatchable only.

Google AX remains `PENDING_CURRENT_HOST_OR_CLUSTER` and requires a separate Kubernetes/Agent Substrate provider E2E.
