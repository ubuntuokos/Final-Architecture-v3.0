# Terax: real-host observation and coexistence closure

The Terax provider remains optional and disabled by default. Its reference CI is
not a physical workstation qualification. The active FA3 baseline is 175
capabilities and 525 independent positive/negative/rollback obligations.

## Non-disruptive operator opt-in

GitHub Actions > FA3 Terax Current-Host Observation > Run workflow.
Choose main and set execute_current_host=true. This manual-only workflow
requires the real self-hosted Linux/x64 runner labeled fa3-current-host.
It runs the runner/HRB doctor followed by the read-only disabled-reference
collector. It does not install, uninstall, reboot, launch Terax, acquire a
compute GPU, change hardware settings or collect secrets.

Equivalent commands, only from the actual FA3 workstation repository checkout:

    ./bin/fa3-current-host-runner-doctor
    python3 evidence/collect-terax-current-host.py --state disabled-reference
    PYTHONPATH=src python3 src/fa3_terax_host_observation.py --root .
    ./bin/fa3-enforce terax

Result reports: reports/terax-host-observation.json,
evidence/receipts/terax-current-host.json and reports/terax-gate-report.json.
These reports do not make a physical current-host PASS claim: absence of
Terax-named processes cannot prove absence of differently named helpers,
undisclosed HRB leases, GPU ownership or independent upstream resource use.

## Outstanding independent P0 evidence

Before a physical enabled-provider coexistence PASS is admitted, collect:

- installed FA3/upstream ownership manifests and verified upstream preservation;
- observed concurrent startup and execution with service/path/socket/port checks;
- independently verified authoritative HRB lease and reservation inventory;
- complete owned process, unnamed helper, RAM/VRAM and polling measurements;
- operator-approved install/reboot/rollback/uninstall cases where applicable;
- provenance-signed evidence for the exact same host, commit, run and timeframe.

The coexistence source-integration bridge was merged into the #410 branch via
#470. PR #410 remains separate until its whole global baseline is reconciled
with current main and has its own permanent CI and physical host evidence.

Do not promote any FA3 capability or the global runtime from optional Terax
observations. Do not commit host-specific receipts. The previously suspended
Terax watch remains suspended.
