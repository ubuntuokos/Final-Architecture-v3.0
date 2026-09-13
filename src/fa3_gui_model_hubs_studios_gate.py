#!/usr/bin/env python3
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def validate():
    failures = []
    decision_path = ROOT / "canonical/decisions/FA3-DEC-GUI-MODEL-HUBS-STUDIOS-2026-09-13.json"
    gate_path = ROOT / "canonical/FA3-GATE-GUI-MODEL-HUBS-STUDIOS-001.json"
    ops_path = ROOT / "apps/fa3-control-center/qml/OperationsAwareAppShell.qml"
    model_path = ROOT / "apps/fa3-control-center/qml/ModelManagerPage.qml"
    civitai_path = ROOT / "apps/fa3-control-center/qml/CivitaiPanel.qml"
    omdb_path = ROOT / "apps/fa3-control-center/qml/OpenModelDbPanel.qml"
    studio_path = ROOT / "apps/fa3-control-center/qml/AIStudioPage.qml"
    studio_shell_path = ROOT / "apps/fa3-control-center/qml/StudioAwareOperationsShell.qml"
    main_path = ROOT / "apps/fa3-control-center/src/main.cpp"

    for p in [decision_path, gate_path, ops_path, model_path, civitai_path, omdb_path, studio_path, studio_shell_path, main_path]:
        if not p.exists():
            failures.append(f"missing:{p.relative_to(ROOT)}")
    if failures:
        return failures

    decision = json.loads(decision_path.read_text())
    gate = json.loads(gate_path.read_text())
    ops = ops_path.read_text()
    model = model_path.read_text()
    civitai = civitai_path.read_text()
    omdb = omdb_path.read_text()
    studio = studio_path.read_text()
    studio_shell = studio_shell_path.read_text()
    main = main_path.read_text()

    checks = [
        (decision.get("capability_count_after") == 143, "capability-count"),
        (decision.get("new_architectural_authorities") == 0, "no-new-authority"),
        (gate.get("fail_closed") is True, "fail-closed"),
        ('text: "Hugging Face"' in ops and 'text: "CivitAI"' in ops and 'text: "OpenModelDB"' in ops, "header-web-buttons"),
        ('homeUrl: "https://huggingface.co/"' in ops and 'homeUrl: "https://civitai.com/"' in ops and 'homeUrl: "https://openmodeldb.info/"' in ops, "header-web-targets"),
        ("WebEngineView" in ops and "request.openIn(hubWebView)" in ops and "Qt.openUrlExternally" not in ops, "embedded-web-containment"),
        ('if (key === "starterModels")' in ops and "return false" in ops, "starter-hidden-global"),
        ('{ key: "starter", label:' in model and "StarterModelsPage" in model, "starter-under-model-manager"),
        ('{ key: "huggingface", label: "Hugging Face" }' in model and "HuggingFaceModelPanel" in model, "hf-under-model-manager"),
        ('{ key: "civitai", label: "CivitAI" }' in model and "CivitaiPanel" in model, "civitai-under-model-manager"),
        ('{ key: "openmodeldb", label: "OpenModelDB" }' in model and "OpenModelDbPanel" in model, "openmodeldb-under-model-manager"),
        ('{ key: "llmfit", label: "llmfit" }' in model and "LlmfitPanel" in model, "llmfit-under-model-manager"),
        ('{ key: "remotehub", label: "Remote AI Hub" }' in model and "RemoteAiHubPanel" in model, "remote-hub-under-model-manager"),
        ("SplitView" not in omdb and "ColumnLayout" in omdb, "openmodeldb-responsive"),
        ("RowLayout { anchors.fill: parent" not in civitai and "ColumnLayout" in civitai, "civitai-responsive"),
        ("Marketing AI Studio" in studio, "marketing-studio"),
        ("Weboldalkészítés AI Studio" in studio and "Website AI Studio" in studio, "website-studio"),
        ("Prezentáció AI Studio" in studio and "Presentation AI Studio" in studio, "presentation-studio"),
        ("FA3-PROVIDER-PRESENTON-001" in studio, "presenton-binding"),
        ("AIStudioPage" in studio_shell and "StudioAwareOperationsShell.qml" in main, "studio-active"),
    ]
    failures.extend(name for ok, name in checks if not ok)
    return failures


if __name__ == "__main__":
    failures = validate()
    if failures:
        print("FA3 GUI model hubs/studios gate: FAIL")
        for failure in failures:
            print(" -", failure)
        raise SystemExit(1)
    print("FA3 GUI model hubs/studios gate: PASS")
