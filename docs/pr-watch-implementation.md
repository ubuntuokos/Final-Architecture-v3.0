# FA3 PR Watch — implemented GitHub development integration

Implemented source branch: `fa3/donor-anthropics-claude-code-action-20260928`.
Parent donor and plan: [PR #507](https://github.com/ubuntuokos/Final-Architecture-v3.0/pull/507).
Upstream reference: `anthropics/claude-code-action` at `8ce9314fa9a404564fa7e954cd84f25bcba2b829`; MIT source declaration; source copying is **not** done here.

## Delivered executable scope

PR Watch is a **GitHub observation and plan/evidence preview component** inside the existing Work Management application. It is not another app, model router, durable scheduler, tool executor or evidence authority.

- `src/fa3_pr_watch.py`: real GitHub HMAC-SHA256 webhook signature verification, bounded JSON ingestion, repository/actor/PR checks, revision and immutable SHA normalization, replay deduplication, stale/conflict handling, an append-only delivery digest index, and a local redacted read-only operator projection.
- `src/fa3_pr_watch_receiver.py`: an optional, **loopback-only**, disabled-by-default HTTP receiver. Port `0` asks the OS for a free port so there is no fixed port or AdGuardHome port collision. No public bind, no token storage, no model calls, no GitHub write access.
- `bin/fa3-pr-watch` and `bin/fa3-pr-watch-receiver`: real CLI entrypoints. A preopened secret file descriptor must be supplied by the existing admitted FA3 Secret Broker transport. The secret is never passed as a CLI string or persisted in the projection.
- `apps/fa3-control-center/src/PrWatchService.{h,cpp}`: Qt service loads the local projection with format/permission/authority checks and a filesystem watcher. No direct GitHub API or executor calls.
- `apps/fa3-control-center/qml/WorkManagementPage.qml`: PR Watch tab inside existing Work Management, displaying authenticated local observations, immutable observed head SHA, event, actor-independent work-item projection state and a **draft-only** action.
- `src/fa3_pr_watch.py::preview_goal_plan`: a non-executing bridge into existing Goal Execution Foundation, real Workforce routing and Agent Workload validators. A plan is tied to the last observed immutable source SHA and repo. Preflight strings remain review references, never validated admission.
- `src/fa3_pr_watch.py::preview_evidence`: calls existing Goal evidence assessment. It refuses to award VERIFIED or to use semantic feedback as proof.
- `canonical/contracts/FA3-GITHUB-DEVELOPMENT-INTEGRATION-CONTRACTS-001.json`: non-authoritative contract extending the existing Work Item, Developer Coordination, Workload Runtime, Goal Execution, Security, UAF, Temporal, Model Router, HRB, Journal and Evidence boundaries.
- `tests/test_pr_watch.py`, `tests/test_pr_watch_receiver.py`, `.github/workflows/fa3-pr-watch.yml`: deterministic positive and adversarial tests including live loopback HTTP ingest, wrong signature, changed delivery, stale/force-pushed source, unsafe filesystem permissions and denied untrusted source claims. Existing Work Management and Goal Execution tests are also rerun.

This code provides **real functional local ingestion and GUI display** once an authorized GitHub webhook transport is configured. It does **not** silently register a GitHub App, invent a canonical Work Management ID or start any worker. Direct use of GitHub as a new tool/model/evidence authority is forbidden.

## Startup and local commands

On a checkout containing the implementation, the receiver's only ingress is HTTP `POST /github` on a loopback socket. It requires the exact GitHub `X-Hub-Signature-256`, `X-GitHub-Event` and `X-GitHub-Delivery` headers plus the exact raw request body. An independently approved reverse proxy or relay can forward those bytes to the displayed loopback endpoint; only the proxy needs any external interface.

An admitted Secret Broker caller must arrange a preopened FD containing the GitHub webhook shared secret, accessible only by the PR Watch process. Example *process invocation* (FD preparation is deliberately NOT implemented using a plaintext file or environment secret here):

```sh
# Secret Broker provides an already open FD 3; no plaintext secret is stored.
PYTHONPATH=src python3 bin/fa3-pr-watch-receiver --secret-fd 3 --bind 127.0.0.1 --port 0 --allow-repo ubuntuokos/Final-Architecture-v3.0
# prints {"listen":"http://127.0.0.1:<dynamic-port>/github", ...}
```

No GitHub App, listener, proxy or background service is installed automatically. `GET /health` on that loopback listener returns a non-authoritative readiness signal. Stop the foreground process to disable incoming events.

For one already captured exact signed webhook event, an approved caller can instead use:

```sh
PYTHONPATH=src python3 bin/fa3-pr-watch ingest \
  --payload /path/to/exact-raw-github-body.json \
  --event pull_request --delivery <delivery-id> \
  --signature 'sha256=<header-from-github>' --secret-fd 3
PYTHONPATH=src python3 bin/fa3-pr-watch list
```

The `--signature` value is the **public HMAC digest header**, not the secret. The raw event path must be a trusted, locally controlled transport artifact; attacker-controlled comments and PR files cannot act as commands. The event cache defaults to `$XDG_STATE_HOME/fa3/pr-watch/projection.json` or `~/.local/state/fa3/pr-watch/projection.json` with directory mode 0700 and state mode 0600. The cache contains only redacted metadata and SHA-256 payload digests; it is not a canonical work-item registry, Journal or Evidence Registry.

Once signed events are ingested, open the existing FA3 Control Center -> **Work Management -> PR Watch** and press Refresh. A PR with an observed immutable head SHA offers **Tervezet**: it submits only a standard FA3 GUI draft changeset. It does not execute a model, mutate GitHub, claim actor authorization or approve the draft.

To compile a **non-executing** proposal from an existing user-owned Goal Execution contract:

```sh
PYTHONPATH=src python3 bin/fa3-pr-watch preview-plan \
  --external-key github:owner/repo:pr:123 \
  --goal goal.json --steps authorized-step-candidates.json \
  --preflight preflight-review-refs.json --root .
```

The review-only `preflight` MUST contain the same exact `source_sha` and `repository_scope` as the last observed PR plus the existing Goal foundation's required Reuse/Hardware/Security reference fields. The existing Goal compiler independently validates goal schema, bounded execution policy, selected Workforce eligibility and Agent Workload task shape. Its output is a *candidate*, not permission to run.

Review evidence completeness without asserting an independent PASS:

```sh
PYTHONPATH=src python3 bin/fa3-pr-watch preview-evidence \
  --goal goal.json --observations verifier-observation-refs.json
```

These observations are **references only**. Existing canonical Evidence/Gate must independently fetch/validate authentic evidence, bind it to the exact goal, source SHA, checker, runtime and authorized approvals, and alone may grant VERIFIED.

## Security and Hardware Audit

- HMAC verification precedes event parsing. Unknown actions, unverifiable delivery IDs and ambiguous check-run PR bindings fail closed; external issue bodies/comments are never saved or interpreted as instructions.
- The signed sender identity is still **not** permission to execute anything. A GitHub event, comment or check-run cannot request token elevation, grant model/tool access or self-certify a task.
- GitHub PR head code, `.mcp.json`, package scripts, compiler/plugin hooks and hidden prompt-injection content are untrusted. They must not be executed on the privileged FA3 current-host runner. Upstream GitHub security advisory GHSA-8q5r-mmjf-575q is an explicit optional-provider admission obligation.
- A separate broker/operator must verify credential scope, repo installation/actor rights, typed UAF action authorization, fresh current-host runner/HRB admission, an approved Model Router route, isolated workspace and existing Temporal state before any effectful follow-on PR.
- No new device requirements. CPU-only works with 0 accelerators; GPUs/NPUs are permitted only by existing HRB and display-GPU explicit task/model selection rules. This feature does not change OS drivers, CPU tuning, ports or AdGuardHome configuration. GUI uses Qt6 on Wayland or X11 and does not assume KDE-only APIs.

## Functional gates and honest remaining boundary

Run source regression tests:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p test_pr_watch.py -v
PYTHONPATH=src python3 -m unittest discover -s tests -p test_pr_watch_receiver.py -v
PYTHONPATH=src python3 -m unittest discover -s tests -p test_pr_watch_goal_bridge.py -v
PYTHONPATH=src python3 -m unittest discover -s tests -p test_work_management_gate.py -v
PYTHONPATH=src python3 -m unittest discover -s tests -p test_goal_execution_foundation.py -v
```

The GitHub Actions workflow tests source syntax, signed payload and real local HTTP semantics, negative cases and existing Work Management/Goal contracts. A hosted CI PASS is **not** physical execution evidence or GUI native-session qualification.

**Not yet runtime-admitted:** an external GitHub App/webhook-to-loopback relay, real GitHub write operations, actual agent execution by Temporal/Agent Workload on received PRs, automatic repair, production current-host scoped E2E, and physical GUI-session PASS. These need separately approved and evidenced follow-on P3–P5 integration; source-only code cannot claim those capabilities. No dependency on an Anthropic token or proprietary Claude backend has been added. When disabled, the adapter has no running worker or network session.

## Rollback and retention

Stop the optional local receiver. This stops new observations without mutating GitHub, the original project, FA3 central work-item identity or existing Workload/Temporal state. Keep the signed observation cache as bounded private operational metadata under existing retention policy; it is never the proof source. At 10,000 delivery digests or 1,000 distinct work items, the reader remains available but ingestion **fails closed**, requiring an explicitly authorized archival/reconciliation procedure rather than silently forgetting replay IDs.

The accepted FA3 donor registry is planning metadata. No upstream Claude Code Action code has been copied and no automatic provider/runtime/source promotion is implied by this app.

## Opt-in dedicated service and GitHub App setup

The source now includes the Secret Broker runtime bridge, a dedicated-service
unit template, the Secret Broker allowlist policy, a group-only redacted GUI
exporter and a safe configuration renderer. These are implemented sources,
not installed services or an already registered GitHub App.

1. From the FA3 repository run:

    python3 bin/fa3-pr-watch-render-service --github-repo ubuntuokos/Final-Architecture-v3.0 --webhook-url https://YOUR-APPROVED-RELAY.example/github

   This writes the service unit and private read-only GitHub App manifest to
   reports/pr-watch. The action performs no privileged installation and writes
   no secrets. Review both files. Register a private GitHub App using the
   generated manifest and install it only on approved repositories. An
   administrator must separately authorize the reachable HTTPS relay, which
   preserves the exact signed request bytes and GitHub headers.

2. The host administrator creates the dedicated fa3-pr-watch Unix service
   account, fa3-pr-watch-viewers group and supplemental fa3-secret-clients
   membership, then installs the rendered systemd unit. Never install the
   unrendered template: FA3_REPO_ROOT and FA3_GITHUB_REPOSITORY are mandatory
   substitution markers. The unit requires and is PartOf fa3-secrets.target;
   it must stop before the encrypted credential image is closed.

3. After starting the existing FA3 secrets runtime, use the existing tools:

    fa3-secrets-admin policy-check deployment/pr-watch/policy.example.json
    fa3-secrets-admin policy-install deployment/pr-watch/policy.example.json
    fa3-secrets-admin put integration/relay/001 --kind GENERIC_FA3_CREDENTIAL

   Enter the real webhook secret interactively, never through argv, environment,
   a repository file or a log. Policy permits consumer FA3-PR-WATCH-001 only
   in the named systemd unit for the dedicated Unix user and
   UDS_SINGLE_SECRET projection. The runtime obtains the single secret from
   the existing broker and passes it over an inherited one-shot pipe to the
   already implemented loopback receiver. At least one exact --allow-repo is
   mandatory. The dynamic local port does not interfere with AdGuardHome.

4. Private service state remains under
   /var/lib/fa3-pr-watch/fa3/pr-watch/projection.json (0700/0600).
   The separately redacted GUI projection lives under
   /run/fa3-pr-watch/operator.json (directory 0750, file 0640, group
   fa3-pr-watch-viewers). Only explicitly admitted group members can read
   that view. Following operator group re-login, start Control Center with
   FA3_PR_WATCH_PROJECTION_PATH=/run/fa3-pr-watch/operator.json.
   Work Management -> PR Watch then displays the local read-only view.
   No agent commands, secrets, raw untrusted PR bodies or credentials are
   exported to the GUI.

5. The UAF bridge in src/fa3_pr_watch_workload_bridge.py checks immutable
   PR and goal SHA binding, exact task and plan digests, external approval,
   and the existing agent.workload.start action contract. It refuses to
   dispatch without real connected Security authorization, external approval,
   HRB acquire/release and evidence sink callbacks. It calls the existing
   UAF dispatcher only and never claims canonical completion.

6. The new bin/fa3-pr-watch-e2e-fixture --fixture-only command signs a
   synthetic event, actually runs two subprocess workers in separate
   isolated worktrees through the existing FA3 Developer Agent Coordinator,
   and invokes a separate checker process on the immutable integrated Git
   commit and exact expected file bytes. This is reference E2E, not a real
   provider, untrusted GitHub checkout or current-host promotion.

Not silently activated: the external GitHub App and HTTPS relay; local
operator account/policy creation; approved production UAF/Temporal/HRB/Model
Router dispatch; real scoped current-host and desktop-session evidence. The
PR remains fail-closed and draft until independently proven.
