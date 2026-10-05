from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "canonical/CFA3-ONE-CLICK-CONVERSATION-HANDOFF-POLICY-001.json"
AGENTS = ROOT / "AGENTS.md"
QML = ROOT / "apps/shared/conversation-handoff/qml/OneClickHandoffBox.qml"
CHAT = ROOT / "apps/fa3-control-center/qml/ChatWorkspace.qml"
HEADER = ROOT / "apps/fa3-control-center/src/ChatFileService.h"
CPP = ROOT / "apps/fa3-control-center/src/ChatFileService.cpp"
CMAKE = ROOT / "apps/fa3-control-center/CMakeLists.txt"


def test_one_click_handoff_policy_covers_development_and_product() -> None:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["requirement"] == "MUST"
    assert policy["scope"]["development_line"] == "FA3_CFA3_DEVELOPMENT"
    assert set(policy["scope"]["product_families"]) == {"CFA3", "FA3"}
    assert policy["development_policy"]["single_copyable_container_required"] is True
    assert policy["development_policy"]["single_word_is_not_exempt"] is True
    assert policy["product_ux_policy"]["copy_action_count"] == 1
    assert policy["product_ux_policy"]["copy_must_capture_full_payload"] is True
    assert policy["compatibility"]["capability_baseline"] == 175
    assert policy["compatibility"]["capability_delta"] == 0
    assert policy["compatibility"]["new_architectural_authority"] is False


def test_development_projection_is_explicit() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    assert "One-click new-conversation handoff rule" in text
    assert "single word" in text
    assert "exactly one one-click-copyable" in text


def test_shared_handoff_component_has_single_full_copy_action() -> None:
    text = QML.read_text(encoding="utf-8")
    assert 'text: "Másolás"' in text
    assert "clipboardService.copyTextToClipboard(handoffText)" in text
    assert "selectByMouse: false" in text
    assert 'visible: handoffText.length > 0' in text
    assert text.count('text: "Másolás"') == 1


def test_control_center_consumes_shared_handoff_and_clipboard_service() -> None:
    chat = CHAT.read_text(encoding="utf-8")
    header = HEADER.read_text(encoding="utf-8")
    cpp = CPP.read_text(encoding="utf-8")
    cmake = CMAKE.read_text(encoding="utf-8")
    assert "OneClickHandoffBox" in chat
    assert "function presentNewConversationHandoff" in chat
    assert "copyTextToClipboard" in header
    assert "QGuiApplication::clipboard()" in cpp
    assert "OneClickHandoffBox.qml" in cmake