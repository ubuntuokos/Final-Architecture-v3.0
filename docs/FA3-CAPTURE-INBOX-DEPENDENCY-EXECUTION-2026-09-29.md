# FA3 Capture & Inbox Fabric — prerequisite execution ledger (2026-09-29)

This branch is a **static governance/dependency implementation**, not the Capture runtime, a
second sync layer or a production/current-host admission. Preserve the canonical **175
capabilities**, dynamic provider count and **zero new architectural authorities**.

## Canonical reuse mapping

| Capture concern | Existing owner | Rule |
| --- | --- | --- |
| Canonical IDs/status | FA3-REGISTRY-001 | No local source-of-truth registry |
| Event history/audit | FA3-JOURNAL-001 + FA3-JOURNAL-CONTRACTS-001 | Append-only metadata; payload in existing FA3 artifact custody |
| Collection privacy | FA3-OS-POLICY-001 + FA3-AUTH-SECURITY-GOV-001 | Explicit user capture; deny-by-default sensors/clipboard/screen; pre-persistence redaction |
| Secrets and peer trust | FA3-SECRET-BROKER-001, existing trust/identity | No credential content in project or journal |
| Durable media/project | Existing FA3 artifact/project graph | Original and derived versions separate; provenance refs retained |
| Application handoff | CAP-152; UAF; Central MCP Gateway | Typed per-recipient action with explicit permission and acknowledgement |
| Offline LAN transfer | CAP-150 | Existing content-addressed cross-instance transfer only; no Capture Sync |
| Multi-host resource placement | HRB; Model Router only when AI required | CPU-only mandatory; no auto display-GPU AI enrollment |
| Scheduled dependencies | Existing Temporal/workforce | No local scheduler authority |
| Software coexistence | CAP-175 / PR #410 | XDG namespaced, no default port, upstream apps remain usable |
| Discovery | CAP-146/147 + FA3 Donor & Reference Registry | Source-normalized reference candidates, no auto import |

## Observed GitHub dependencies at branch creation

- main exact base: `6fc7650d0697ac2f648af5e66266eb9a15c2b0af`.
- PR #217: merged FA3 OS privacy substrate, existing profile still has old local
  `capability_count: 143` metadata; no authority or legacy evidence is silently rewritten here.
- PR #387: merged mandatory Reuse Discovery; CAP-146/147 already in 175 model.
- PR #403: merged 175 capability baseline; new runtime obligations remain separate.
- PR #410: open; comparison to main at check was 189 ahead / 1074 behind;
  global footprint schema and retroactive physical coexistence admission are **not closed**.
- PR #459: open 527-source donor reconciliation; main had 307 normalized records;
  PR #522 separately carried 314. This branch adds five **source-distinct** reference
  candidates on main's 307-record base (312 total). Reconcile **field-by-field**
  by `source.normalized_key` against #459/#522 before donor-registry merge;
  never replace either registry with the shorter version.
- PR #520: open first Story/Screenplay native application. Not an admitted live
  Capture handoff receiver yet.
- PR #521: closed **without merge**; signed mesh/recipient factory is not
  canonical. If reopened, its patterns must be reconciled through existing UAF/MCP,
  not treated as an already installed interface.
- CAP-150, CAP-152 and CAP-175: `PENDING_CURRENT_HOST` in the canonical Evidence
  Registry, empty physical artifact lists. CAP-150 loopback test is **not**
  cross-host production E2E; it requires at least two distinct host identities.

## Admission order and physical evidence needed

1. Reconcile #459/#522 donor branches losslessly, preserve all historical and
   rejected records; run canonical Reuse Discovery + license/provenance checks.
2. Rebase/reconcile #410 against current main and complete global policy/footprint
   acceptance. Add a Capture-specific footprint **under the existing CAP-175
   schema after it is merged**, not a competing policy/schema.
3. Resolve legacy 143 numeric metadata across relevant canonical profiles via
   existing capability-model governance without rewriting old 143 receipts.
4. Admit local Capture Core and Local Inbox against existing privacy, Journal and
   artifact custody. Test denied sensors and secrets, redaction before disk,
   derivative purge, explicit erasure/tombstone and offline reopen.
5. Admit an exact registered UAF receiver/action for each consuming application,
   beginning Ideation and the separately accepted Story implementation. Test
   recipient spoofing, permission revocation, schema mismatch, deduplication,
   unconnected recipient and missing/invalid ACK.
6. Use **only the existing CAP-150** admitted transfer path for LAN and CAP-152
   for typed workspace handoff. Prove resume/integrity, host identity, replay
   rejection, peer revocation, conflict preservation, offline recovery and
   selective erasure against two physically distinct host identities. No
   silent cloud fallback or donor-runtime auto-install.
7. Before current-host/global promotion: Hardware Audit, CAP-175 concurrent
   upstream run and install/reboot/uninstall non-interference receipts, negative
   privacy and security evidence, exact-head Canonical + Reuse Discovery +
   release/projection + current-host gates.

## This branch's static acceptance boundary

Run `PYTHONPATH=src python src/fa3_capture_inbox_dependency_gate.py --root .`
and `PYTHONPATH=src python -m unittest tests.test_capture_inbox_dependency_gate -v`.
A static PASS means the prerequisite records remain fail-closed. It does **not**
mean Capture exists as an admitted runtime or that CAP-150/152/175 physical
obligations have been satisfied. Global enforcement/release projection binding
and a merge-ready state require reconciliation with open prerequisite PRs.
