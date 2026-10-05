# Owner-marked GitHub Actions and Temporal donor references (2026-09-30)

## Provenance and identity
The owner provided five URLs under one explicit `donornak:` marker. Each exact URL is retained as its own source identity; no listed child repository is automatically admitted.

| Owner URL | Reference scope | Evidence boundary |
| --- | --- | --- |
| https://github.com/actions/runner | GitHub Actions self-hosted runner repository; CI job execution, listener and update lifecycle patterns | Public repository; upstream GitHub metadata declares MIT. Source-copy and deployment require separate file-level license, security and host Software Coexistence review. Do not auto-install a runner. |
| https://github.com/actions | Official GitHub Actions organization discovery index | Existing `actions/runner-images` remains a separate candidate; no blanket approval for listed repositories. |
| https://github.com/temporalio | Temporal primary organization discovery index | Existing `temporalio/sdk-python` candidate remains unchanged. Temporal is already FA3's intended sole durable lifecycle; organization registration confers no second scheduler or new authority. |
| https://github.com/temporal-community | Community organization discovery index; examples and experimental projects | The upstream organization explicitly states its repositories have no guaranteed support or maintenance. No automatic adoption of the AI-agent demos or their provider configuration. |
| https://github.com/temporal-sa | Temporal SA organization discovery index; samples and design-pattern references | An index is not a reviewed license or runtime dependency. Individual repositories, sandbox dependencies and cloud-specific flows require separate approval. |

## FA3 boundaries and count
Published parent main: `653b1d0ba10fe8f584e66d0e3b7c054f8ec3ef71` with 1216 unique donor entries. Proposed metadata-only addition: five new identities, total **1221**, existing 1216 entry objects and relative order preserved; fixed capability baseline remains **175**. Source metadata is `ACCEPTED_REFERENCE` only when this intake merges to published main following exact-head mandatory checks. The owner-marked links pre-authorize **reference registration only**, not code reuse, implementation, source install, software substitution, model/provider admission, runtime activation or any physical current-host PASS.

Keep GitHub Actions runner execution separate from Temporal's durable workflow authority. Existing FA3 Hardware Safety Envelope, CPU-only support, HRB sole resource authority, Model Router sole model route, Secret Broker, security/provenance gates and Software Coexistence rules are unchanged. Organization listings must never recursively expand into registered or installed repositories. New designs may consult these references only after canonical publication.

Intake delta: `canonical/deltas/FA3-DONOR-ACTIONS-RUNNER-TEMPORAL-ORGS-2026-09-30.json`.
