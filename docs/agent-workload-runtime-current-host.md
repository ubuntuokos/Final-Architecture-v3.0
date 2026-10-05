# FA3 Agent Workload Runtime — current-host closure

This current-host surface can promote only the native runner on the evidenced host/run. It cannot promote Google AX, Podman, process/VM checkpointing or global FA3.

A real PASS requires a fresh FA3 Resource Admission receipt whose workload id is exactly `fa3-agent-workload-native-current-host` and whose HRB authorization is current, externally validated and scope-bound. The generic CPU-only HRB authorization path is now materialized under `FA3-AUTH-HOST-RESOURCE-BROKER-001`; the remaining current-host prerequisite is installation of its root-separated bridge (`/usr/local/bin/fa3-host-resource-broker-admission` + privileged helper) and a successful dispatch-only production E2E. Until that host-local bridge/E2E is proven, the runtime remains **PENDING_CURRENT_HOST**.

The real collector proves non-root execution, unified cgroup v2, a user-systemd transient scope, actual SIGSTOP/SIGCONT pause-resume behavior, cleanup and the parent static workload gate. The workflow is restricted to `[self-hosted, linux, x64, fa3-current-host]` and is operator-dispatchable only.

Google AX remains `PENDING_CURRENT_HOST_OR_CLUSTER` and requires a separate Kubernetes/Agent Substrate provider E2E.
