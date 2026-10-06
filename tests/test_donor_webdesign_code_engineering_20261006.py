import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELTA = ROOT / "canonical" / "deltas" / "CFA3-DONOR-WEBDESIGN-CODE-ENGINEERING-BATCH-2026-10-06.json"
PAIDF = ROOT / "canonical" / "deltas" / "CFA3-DONOR-NVIDIA-PHYSICAL-AI-DATA-FACTORY-2026-10-06.json"

EXPECTED = [
    "https://www.quickandeasywebbuilder.com",
    "https://github.com/KDE/kimagemapeditor",
    "https://github.com/KDE/quanta",
    "https://www.dyad.sh/docs",
    "https://getpublii.com/docs/",
    "https://github.com/wikimedia/VisualEditor",
    "https://github.com/JiHong88/suneditor",
    "https://github.com/ckeditor/ckeditor4",
    "https://github.com/topics/ai-editor?l=html",
    "https://github.com/topics/ai-editor",
    "https://github.com/topics/html-editor",
    "https://github.com/topics/ai-code-editor",
    "https://github.com/topics/ai-html",
    "https://github.com/topics/offline-ai-logo-generation",
    "https://github.com/topics/ai-image-editing",
    "https://github.com/nexu-io",
    "https://github.com/nexu-io/html-anything",
    "https://github.com/nexu-io/open-design",
    "https://github.com/nexu-io/html-video",
    "https://github.com/Sayhi-bzb/Agent-HTML",
    "https://github.com/components-ai/css.gui",
    "https://github.com/components-ai",
    "https://github.com/markrahq/markra",
    "https://github.com/arshad-yaseen/monacopilot",
    "https://github.com/inbharat-ai/codein.pro",
    "https://github.com/GraysonBannister/omni-code",
    "https://github.com/SamurAIGPT/ai-logo-studio",
    "https://github.com/Nutlope/logocreator",
    "https://github.com/centralpigeonnippers/ai-logo-maker",
    "https://github.com/nothing331/mirai-image-editor",
    "https://github.com/howardrock88/semcanvas-ai",
    "https://github.com/XBastille/DeepFX-Studio",
    "https://github.com/SamurAIGPT/clearmark-ai",
    "https://github.com/apache/netbeans",
    "https://github.com/eclipse-platform/eclipse.platform",
    "https://github.com/eclipse-jdt/eclipse.jdt.core",
    "https://github.com/eclipse-lsp4e/lsp4e",
    "https://github.com/eclipse-theia/theia",
    "https://github.com/microsoft/vscode",
    "https://github.com/JetBrains/intellij-community",
    "https://github.com/KDE/kdevelop",
    "https://github.com/qt-creator/qt-creator",
    "https://gitlab.gnome.org/GNOME/gnome-builder",
    "https://github.com/zed-industries/zed",
    "https://github.com/lapce/lapce",
    "https://github.com/eclipse-che/che",
    "https://github.com/microsoft/monaco-editor"
]

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_exact_owner_authorized_webdesign_code_engineering_set():
    data = load(DELTA)
    assert data["status"] == "STAGED_PENDING_ROLLING_BATCH_APPEND"
    assert data["authorization"]["owner_command"] == "donornak"
    assert data["authorization"]["explicit_user_approval"] is True
    assert data["submitted_or_planning_used_urls"] == EXPECTED
    assert data["new_source_count"] == 47
    keys = [row["normalized_key"] for row in data["canonical_identities"]]
    assert len(keys) == len(set(keys)) == 47

def test_pr731_combined_source_union_is_exactly_48():
    data = load(DELTA)
    paidf = load(PAIDF)
    keys = {row["normalized_key"] for row in data["canonical_identities"]}
    paidf_keys = {row["normalized_key"] for row in paidf["canonical_identities"]}
    assert keys.isdisjoint(paidf_keys)
    assert len(keys | paidf_keys) == 48
    assert data["combined_with_existing_pr731_paidf_delta"]["combined_new_source_count"] == 48

def test_non_authoritative_staging_boundaries():
    data = load(DELTA)
    assert data["capability_baseline"] == 175
    assert data["capability_delta"] == 0
    assert data["authority_delta"] == 0
    assert data["usage_edges_created"] == 0
    assert data["canonical_registry_materialized"] is False
    assert data["waiting_queue_only"] is True
    assert all(value is False for value in data["boundaries"].values())
