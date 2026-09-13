#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding="utf-8")

def validate():
    mission=read("apps/fa3-control-center/qml/MissionControlAppShell.qml")
    model=read("apps/fa3-control-center/qml/ModelManagerHubPage.qml")
    app=read("apps/fa3-control-center/qml/AppShell.qml")
    civ=read("apps/fa3-control-center/qml/CivitaiPanel.qml")
    omdb=read("apps/fa3-control-center/qml/OpenModelDbPanel.qml")
    main=read("apps/fa3-control-center/src/main.cpp")
    failures=[]
    checks=[
        ("MissionControlAppShell.qml" in main,"mission-shell-active"),
        ("VISUAL MISSION CONTROL" in mission and "MODEL SOURCES" in mission,"mission-control-header"),
        (all(x in mission for x in ["Hugging Face","CivitAI","OpenModelDB"]),"three-provider-portals"),
        ("StarterModelsPage" in model and "Hugging Face" in model and "CivitAI" in model and "OpenModelDB" in model and "llmfit" in model and "Remote AI Hub" in model,"model-hub-required-tabs"),
        ('if (key === "starterModels")' in app,"starter-hidden-from-primary-nav"),
        (all(x in app for x in ["Marketing","Website","Presentation","Presenton","FA3-MARKETING-001","FA3-PROVIDER-OPENHERO-001","FA3-PROVIDER-PRESENTON-001"]),"studio-production-areas-canonical-bindings"),
        ("SplitView" not in omdb and "TabBar" in omdb,"openmodeldb-no-squeeze"),
        ('root.width < 760' in civ,"civitai-adaptive-layout"),
        ("Qt.openUrlExternally" not in mission,"web-contained"),
    ]
    failures += [name for ok,name in checks if not ok]
    return failures

if __name__=="__main__":
    f=validate()
    if f:
        print("FA3 GUI mission-control gate: FAIL")
        for x in f: print(" -",x)
        raise SystemExit(1)
    print("FA3 GUI mission-control gate: PASS")
