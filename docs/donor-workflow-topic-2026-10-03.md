# FA3 workflow-topic donor intake — 2026-10-03

## Owner marker

The owner explicitly marked the exact source `https://github.com/topics/workflow` as **donornak** on 2026-10-03.

## Classification

- canonical source key: `github:topics/workflow`
- donor id: `FA3-DONOR-WORKFLOW-TOPIC-001`
- source kind: `GITHUB_TOPIC`
- status: `ACCEPTED_REFERENCE`
- mode: metadata-only `DISCOVERY_INDEX`
- capability delta: **0**
- authority delta: **0**
- capability baseline: **175**

The topic page is a discovery index, not a workflow engine and not a runtime/provider admission. Child repositories are never recursively enrolled. Concrete repositories discovered here require a separate source-specific review before any material adoption or usage-edge registration.

## FA3 mapping

The discovery source maps to the existing **Orchestration & Workflow Fabric**, especially visual workflow authoring, state/lifecycle modelling, DAG/task orchestration, scheduling/retry, automation/connectors, human approval, agent/MCP workflows, browser workflows and container/batch patterns.

The mapping does not alter authority. **Temporal remains the sole global durable lifecycle authority.** Specialist engines remain task-local and must stay inside the existing UAF, Security, HRB, Model Router and Evidence/Gate boundaries.

## Initial discovery examples

The topic currently surfaces projects in categories represented by projects such as n8n, Dify, Airflow, xyflow, XState, Kestra, Activepieces, Prefect, Argo Workflows, Dagster, Flowable and Skyvern. Their presence in the topic is discovery evidence only; this intake does not register those child repositories.

## Reuse boundaries

Any later concrete-repository intake must independently check provenance and license/rights, security, Software Coexistence, Hardware Safety where applicable, compatibility with the FA3 175-capability model, architectural layer placement, duplicate donor identity, and usage-edge registration for actual adoption.

No automatic download, install, dependency, code import, provider/model selection, runtime activation, Current Host PASS, or architectural authority is created by this intake.
