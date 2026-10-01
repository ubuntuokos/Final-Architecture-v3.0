<!-- SPDX-License-Identifier: Apache-2.0 -->
# FA3 Office

Qt6/QML control and authoring workspace for the shared FA3 Office / Document Fabric.

This materialization establishes the FA3-native surface and fail-closed session/format contracts. It **does not** vendor LibreOffice, import upstream source, start LibreOffice, claim editable Office-format fidelity, or claim a physical Current Host PASS.

## Engine boundary

The approved primary engine candidate is LibreOffice Core through an isolated worker using LibreOfficeKit, UNO and/or headless conversion APIs. The full LibreOffice GUI is not embedded.

The current service only performs a read-only executable discovery probe and produces governed session plans. Actual worker execution stays disabled until exact-version License & Rights review and physical Current Host admission are complete.

## Editing model

- Writer
- Sheets
- Presentation
- Documents
- Forms

Foreign Office files are source/projection artifacts around the existing FA3 document authority. ODT/DOCX/ODS/XLSX/ODP/PPTX are candidate editable profiles and remain pending golden roundtrip evidence. PDF is delivery/preview by default.

AI is optional. Non-AI authoring remains a required path. Assisted mutations must use Preview -> explicit Apply -> Undo.

## Build

```bash
cmake -S apps/fa3-office -B build/office
cmake --build build/office
ctest --test-dir build/office --output-on-failure
```
