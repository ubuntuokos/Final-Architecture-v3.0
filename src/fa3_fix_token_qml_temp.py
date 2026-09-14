from pathlib import Path

qml = Path("apps/fa3-control-center/qml/TokenControlCenterPage.qml")
s = qml.read_text(encoding="utf-8")
replacements = {
    '                            RowLayout { Label { text: "Napi token budget:"; color: root.textMuted }; SpinBox { id: dailyTokens; from: 0; to: 1000000000; value: 0; editable: true } }\n': '''                            RowLayout {\n                                Label { text: "Napi token budget:"; color: root.textMuted }\n                                SpinBox { id: dailyTokens; from: 0; to: 1000000000; value: 0; editable: true }\n                            }\n''',
    '                            RowLayout { Label { text: "Havi token budget:"; color: root.textMuted }; SpinBox { id: monthlyTokens; from: 0; to: 2000000000; value: 0; editable: true } }\n': '''                            RowLayout {\n                                Label { text: "Havi token budget:"; color: root.textMuted }\n                                SpinBox { id: monthlyTokens; from: 0; to: 2000000000; value: 0; editable: true }\n                            }\n''',
    '                            RowLayout { Label { text: "Max context / request:"; color: root.textMuted }; SpinBox { id: contextBudget; from: 0; to: 10000000; value: 0; editable: true } }\n': '''                            RowLayout {\n                                Label { text: "Max context / request:"; color: root.textMuted }\n                                SpinBox { id: contextBudget; from: 0; to: 10000000; value: 0; editable: true }\n                            }\n''',
}
for old, new in replacements.items():
    if old not in s:
        raise SystemExit(f"missing token QML repair anchor: {old.strip()}")
    s = s.replace(old, new, 1)
qml.write_text(s, encoding="utf-8")

workflow = Path(".github/workflows/fa3-token-qml-repair-temp.yml")
if workflow.exists():
    workflow.unlink()
Path(__file__).unlink()
