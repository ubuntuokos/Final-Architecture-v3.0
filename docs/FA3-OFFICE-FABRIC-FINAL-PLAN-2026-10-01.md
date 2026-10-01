<!-- SPDX-License-Identifier: Apache-2.0 -->
# FA3 Office Fabric — approved materialization plan

## Decision

FA3 Office is an FA3-native Qt6/QML application backed by a shared Office/Document Fabric. It reuses the existing **CAP-018 Documents/Knowledge Authoring** and **FA3-DOC-001** document authority. The capability baseline remains **175** and no new architectural authority is created.

The primary engine candidate is **LibreOffice Core**, reached only through a versioned, isolated LibreOfficeKit / UNO / headless adapter after License & Rights and physical Current Host admission. The full LibreOffice GUI is not embedded.

## Architecture

```text
FA3 Writer | Sheets | Presentation | Documents | Forms
                         |
                  FA3 Office Fabric
                         |
                 FA3 Document API
                         |
                    FA3-DOC-001
                         |
              isolated Office worker
                  /       |       \
         LibreOfficeKit  UNO   headless
                         |
                admitted LibreOffice
```

Foreign office formats are source/projection formats, not FA3 canonical state. The original input is preserved.

## Donor and reference roles

- `github:libreoffice`: existing canonical reference; primary engine candidate, but this change does not import source, bundle binaries or admit runtime execution.
- `github:onlyoffice`: existing canonical reference for OOXML/editor/collaboration patterns only.
- `github:apache/openoffice`: existing canonical legacy compatibility reference only.
- **Calligra**: approved intended primary Qt6 UI/workflow donor, but its canonical donor intake is pending.
- **Collabora Online**: approved intended optional collaboration provider/donor, but its canonical donor intake is pending.

The exclusive donor-intake slot is currently held by PR #581. Therefore Calligra and Collabora are not inserted into `FA3-DONOR-REFERENCE-REGISTRY-001` by this branch. This is fail-closed, not a bypass.

## Format contract

Editable admission is version/profile scoped. ODT, DOCX, ODS, XLSX, ODP and PPTX begin in `PENDING_GOLDEN_ROUNDTRIP`.

An editable import is not admitted unless the same format has an export path, external golden fixtures pass, semantic retention is measured, unrepresentable data produces an explicit loss receipt, and rollback is demonstrated.

PDF is delivery/preview by default. PDF text extraction or rendering is not proof of reversible editable import.

## Mutation contract

All assisted changes follow:

```text
exact source revision
 -> proposal
 -> Preview
 -> explicit human Apply
 -> new revision
 -> Undo available
```

Stale-revision apply is denied. Unknown format profile is denied. Macros, embedded scripts and external link activation are disabled by default.

AI is optional. When AI access is disabled, no model/provider invocation may occur and ordinary authoring/interchange remains available.

## Runtime isolation and coexistence

The Office worker uses FA3 XDG namespaces under `$XDG_*_HOME/fa3/office` and `$XDG_RUNTIME_DIR/fa3/office`. It may not require upstream uninstall, claim a fixed port, mutate the global environment, or reuse/mutate a user's normal LibreOffice profile.

No LibreOffice binary or source is vendored by this materialization.

## Retrospective consumers

The shared Office/Document layer must be reused by all affected existing/planned applications, especially Story/Screenplay, reporting/publishing, project/meeting outputs, Credits metadata exports and Presentation surfaces. Application-specific semantics remain owned by those applications.

## Current Host and release

Static materialization is not physical runtime closure. CAP-018/CAP-030 Office-specific startup, isolated worker, roundtrip, negative, crash-recovery and rollback evidence must be reconciled with active Current Host PR #559 before release promotion.

## Remaining bounded follow-ups

1. When donor intake #581 releases the slot, add/version-pin and rights-review Calligra and Collabora canonical donor records.
2. Perform exact-version LibreOffice License & Rights/runtime dependency clearance.
3. Run physical Current Host Office tests and attach evidence.
4. Promote only individually proven format profiles; never infer support from a successful PDF conversion.
