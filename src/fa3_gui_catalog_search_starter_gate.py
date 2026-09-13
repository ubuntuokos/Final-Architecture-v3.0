#!/usr/bin/env python3
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
def text(path): return (ROOT / path).read_text(encoding="utf-8")

def validate():
    failures=[]
    decision=json.loads(text("canonical/decisions/FA3-DEC-GUI-CATALOG-SEARCH-STARTER-2026-09-13.json"))
    gate=json.loads(text("canonical/FA3-GATE-GUI-CATALOG-SEARCH-STARTER-001.json"))
    shell=text("apps/fa3-control-center/qml/AppShell.qml")
    mission=text("apps/fa3-control-center/qml/MissionControlAppShell.qml")
    settings=text("apps/fa3-control-center/qml/SettingsPage.qml")
    model=text("apps/fa3-control-center/qml/ModelManagerHubPage.qml")
    search=text("apps/fa3-control-center/qml/SearchPage.qml")
    starter=text("apps/fa3-control-center/qml/StarterModelsPage.qml")
    civcpp=text("apps/fa3-control-center/src/CivitaiClient.cpp")
    civqml=text("apps/fa3-control-center/qml/CivitaiPanel.qml")
    omdbqml=text("apps/fa3-control-center/qml/OpenModelDbPanel.qml")
    omdb=text("apps/fa3-control-center/src/OpenModelDbService.cpp")
    secret_h=text("apps/fa3-control-center/src/SecretBrokerService.h")
    secret_cpp=text("apps/fa3-control-center/src/SecretBrokerService.cpp")
    cmake=text("apps/fa3-control-center/CMakeLists.txt")
    checks=[
        (decision.get("capability_count_after")==143,"capability-count"),
        (decision.get("new_architectural_authorities")==0,"no-new-authority"),
        (gate.get("fail_closed") is True,"fail-closed"),
        ('{ key: "search"' in shell and 'if (key === "starterModels")' in shell,"search-primary-starter-not-primary"),
        ('["starter", t("Starter modellek", "Starter Models")]' in model and 'StarterModelsPage {' in model,"starter-under-model-manager"),
        ('["huggingface", "Hugging Face"]' in model and '["civitai", "CivitAI"]' in model and '["openmodeldb", "OpenModelDB"]' in model,"model-manager-provider-tabs"),
        ('Hugging Face' in mission and 'CivitAI' in mission and 'OpenModelDB' in mission and 'MODEL SOURCES' in mission,"header-provider-portals"),
        ('https://huggingface.co/' in mission and 'https://civitai.com/' in mission and 'https://openmodeldb.info/' in mission,"provider-web-urls"),
        ('Szolgáltatás' in search and 'Projekt' in search and 'Beszélgetés' in search,"search-three-scopes"),
        ('NO_CANONICAL_CONVERSATION_INDEX_ADAPTER' in text("apps/fa3-control-center/src/SearchIndexService.cpp"),"conversation-fail-closed"),
        ('ACQUIRE_STARTER_MODEL' in starter and 'createDraftChangeSet' in starter,"starter-gated-acquisition"),
        ('TabBar' in omdbqml and 'SplitView' not in omdbqml,"openmodeldb-responsive"),
        ('columns: root.width < 760 ? 1 : 2' in civqml,"civitai-responsive"),
        ('Tokenek & hozzáférések' in settings and 'fa3SecretBroker' in settings,"credentials-ui"),
        ('kwalletRequired() const { return false; }' in secret_h and 'KWallet (optional)' in secret_cpp,"kwallet-optional"),
        ('Authorization' in civcpp and 'Bearer ' in civcpp,"civitai-bearer"),
        ('query.addQueryItem(QStringLiteral("token")' not in civcpp and 'apiKey' not in civcpp,"civitai-no-query-secret"),
        ('upstream scan' in civqml.lower() and 'security pass' in civqml.lower(),"civitai-scan-nonauthoritative"),
        ('QCryptographicHash::Sha256' in omdb or 'Sha256' in omdb,"openmodeldb-sha256"),
        ('KWALLET' not in cmake and 'KF6Wallet' not in cmake,"no-kwallet-build-dependency"),
        ('Qt.openUrlExternally' not in mission and 'Qt.openUrlExternally' not in civqml and 'Qt.openUrlExternally' not in omdbqml,"no-external-ai-browser"),
        ('m_sessionSecrets' in secret_cpp,"session-secret-memory"),
        ('Marketing' in shell and 'Website' in shell and 'Presentation' in shell and 'Presenton' in shell,"ai-studio-complete"),
    ]
    failures += [name for ok,name in checks if not ok]
    return failures

if __name__ == "__main__":
    f=validate()
    if f:
        print("FA3 GUI catalog/search/starter gate: FAIL")
        for item in f: print(" -",item)
        raise SystemExit(1)
    print("FA3 GUI catalog/search/starter gate: PASS")
