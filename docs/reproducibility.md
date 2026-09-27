# FA3 Repository Reproducibility

`FA3-REPRODUCIBILITY-FABRIC-001` defines the canonical local/CI preparation and Python regression path. It adds no capability and no architectural authority.

## One Python module identity

The repository exposes `src/` on `sys.path` and FA3 Python modules are imported only as top-level `fa3_*` modules.

Allowed:

```python
from fa3_decision_fabric import DecisionError
```

Forbidden:

```python
from src.fa3_decision_fabric import DecisionError
from .fa3_decision_fabric import DecisionError
```

This prevents the same source file from being loaded under two module identities, which can break exception, singleton, registry and type identity.

## Prepare a fresh or shallow clone

```bash
bash bin/fa3-prepare-repository
```

The command reads the canonical release projection, checks the exact historical commit anchors required by release-projection validation, fetches only missing commit objects from `origin`, and verifies the declared root/canonical tree identities. It does not checkout another revision or mutate the working tree.

To diagnose without fetching:

```bash
bash bin/fa3-prepare-repository --check-only
```

A missing object report includes the exact SHA and recovery command.

## Canonical full regression

```bash
bash bin/fa3-test -v
```

The command uses an isolated XDG-cache venv and the pinned `requirements-test.txt` runner. It is the only canonical full-repository Python test entrypoint. Permanent Enforcement, release-projection reconciliation and Reuse Discovery use the same entrypoint.

Focused CI workflows may run a subset, but they do not define a second full-suite truth.

## Physical current-host boundary

`physical_current_host` is reserved for tests that actually require the labeled physical FA3 host. Hosted CI must not manufacture physical PASS evidence. Current-host collectors/workflows remain separately evidence-gated.

## Gate

```bash
./bin/fa3-enforce reproducibility
```

The gate checks the 175-capability baseline, zero authority/capability delta, pinned test runner, namespace policy, common CI entrypoints, repository-history bootstrap and non-interference with the repository working tree.
