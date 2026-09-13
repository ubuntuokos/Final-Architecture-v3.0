#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_GENERATED_QML = [
    ROOT / "apps/fa3-control-center/qml/MissionControlAppShell.qml",
    ROOT / "apps/fa3-control-center/qml/ModelManagerHubPage.qml",
    ROOT / "apps/fa3-control-center/qml/CivitaiPanel.qml",
    ROOT / "apps/fa3-control-center/qml/OpenModelDbPanel.qml",
]

OPTIONAL_GENERATED_QML = [
    ROOT / "apps/fa3-control-center/qml/ModelManagerHuggingFacePage.qml",
    ROOT / "apps/fa3-control-center/qml/EmbeddedPortalPanel.qml",
]


def normalize_qml(text: str) -> str:
    """Expand compact generated QML into Qt 6.4-safe declarative syntax.

    The mission-control materializer intentionally emits compact QML. Qt 6.4's
    qmlcachegen is stricter about semicolon-separated child-object bodies than
    newer Qt versions. This formatter expands braces and top-level semicolons,
    while preserving semicolons inside parentheses (notably JS for-loops).
    """
    out: list[str] = []
    indent = 0
    line_start = True
    quote: str | None = None
    escape = False
    paren_depth = 0

    def emit_indent() -> None:
        nonlocal line_start
        if line_start:
            out.append("    " * max(indent, 0))
            line_start = False

    def newline() -> None:
        nonlocal line_start
        while out and out[-1] in (" ", "\t"):
            out.pop()
        if not out or out[-1] != "\n":
            out.append("\n")
        line_start = True

    i = 0
    while i < len(text):
        ch = text[i]

        if quote is not None:
            emit_indent()
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                quote = None
            i += 1
            continue

        if ch in ('"', "'"):
            emit_indent()
            quote = ch
            out.append(ch)
            i += 1
            continue

        if ch == "/" and i + 1 < len(text) and text[i + 1] == "/":
            emit_indent()
            j = text.find("\n", i)
            if j == -1:
                out.append(text[i:])
                break
            out.append(text[i:j])
            newline()
            i = j + 1
            continue

        if ch == "(":
            emit_indent()
            paren_depth += 1
            out.append(ch)
            i += 1
            continue
        if ch == ")":
            emit_indent()
            paren_depth = max(0, paren_depth - 1)
            out.append(ch)
            i += 1
            continue

        if ch == "{":
            emit_indent()
            out.append("{")
            indent += 1
            newline()
            i += 1
            continue

        if ch == "}":
            if not line_start:
                newline()
            indent = max(0, indent - 1)
            emit_indent()
            out.append("}")
            i += 1
            continue

        if ch == ";" and paren_depth == 0:
            newline()
            i += 1
            continue

        if ch == "\n":
            newline()
            i += 1
            continue

        if ch in " \t" and line_start:
            i += 1
            continue

        emit_indent()
        out.append(ch)
        i += 1

    result = "".join(out)
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")
    return result.rstrip() + "\n"


def replace_one_of(text: str, candidates: list[str], replacement: str, label: str) -> str:
    if replacement in text:
        return text
    for old in candidates:
        if old in text:
            return text.replace(old, replacement, 1)
    raise SystemExit(f"AI Studio canonical binding marker missing: {label}")


def patch_ai_studio_bindings() -> None:
    path = ROOT / "apps/fa3-control-center/qml/AppShell.qml"
    text = path.read_text(encoding="utf-8")

    text = replace_one_of(
        text,
        [
            'subtitle: "Campaigns · copy · channel outputs"',
            'subtitle: "Mautic / Twenty / listmonk / campaign & CRM workflows"',
        ],
        'subtitle: "FA3-MARKETING-001 · Mautic / Twenty / listmonk · campaign & CRM workflows"',
        "Marketing",
    )
    text = replace_one_of(
        text,
        [
            'subtitle: "Web creative · landing page · asset flow"',
            'subtitle: "AI-assisted website design / build / preview / publish workflows"',
        ],
        'subtitle: "FA3-PROVIDER-OPENHERO-001 · Web creative · website design / build / preview / publish"',
        "Website",
    )
    text = replace_one_of(
        text,
        [
            'subtitle: "Deck narrative · slide generation"',
            'subtitle: "Presenton / slide generation / deck production / export"',
        ],
        'subtitle: "FA3-PROVIDER-PRESENTON-001 · Presenton · slide generation / deck production / export"',
        "Presentation",
    )
    path.write_text(text, encoding="utf-8")


def patch_gate_bindings() -> None:
    path = ROOT / "src/fa3_gui_mission_control_gate.py"
    text = path.read_text(encoding="utf-8")
    old = '(all(x in app for x in ["Marketing","Website","Presentation","Presenton"]),"studio-production-areas"),'
    new = '(all(x in app for x in ["Marketing","Website","Presentation","Presenton","FA3-MARKETING-001","FA3-PROVIDER-OPENHERO-001","FA3-PROVIDER-PRESENTON-001"]),"studio-production-areas-canonical-bindings"),'
    if new not in text:
        if old not in text:
            raise SystemExit("mission-control AI Studio gate marker missing")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    missing = [str(p) for p in REQUIRED_GENERATED_QML if not p.exists()]
    if missing:
        raise SystemExit("required generated QML missing before finalizer: " + ", ".join(missing))

    for path in REQUIRED_GENERATED_QML + OPTIONAL_GENERATED_QML:
        if path.exists():
            path.write_text(normalize_qml(path.read_text(encoding="utf-8")), encoding="utf-8")

    patch_ai_studio_bindings()
    patch_gate_bindings()
    print("FA3 mission-control Qt 6.4 finalizer: complete")


if __name__ == "__main__":
    main()
