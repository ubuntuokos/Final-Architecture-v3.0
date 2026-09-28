"""FA3 native screenplay interchange and source-linked breakdown foundation.

No external donor code, remote services, AI execution or authority to publish a
production schedule. Only a deliberately bounded, bidirectional Fountain/FDX
subset is implemented; unsupported fidelity is an explicit error by default.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from typing import Any

SCHEMA = "fa3.screenplay-document.v1"
BREAKDOWN_SCHEMA = "fa3.screenplay-breakdown.v1"
PROFILES = frozenset({"FEATURE", "TV_MOVIE", "EPISODIC", "COMMERCIAL", "LIVE_BROADCAST", "OTHER"})
FORMATS = {"fountain": "EXPERIMENTAL_BIDIRECTIONAL_SUBSET", "fdx": "EXPERIMENTAL_BIDIRECTIONAL_SUBSET"}
ELEMENT_TYPES = frozenset({"ACTION", "CHARACTER", "PARENTHETICAL", "DIALOGUE", "TRANSITION", "SHOT"})
STYLES = frozenset({"Bold", "Italic", "Underline"})
MAX_SOURCE_BYTES = 5 * 1024 * 1024
MAX_SCENES = 3000
MAX_ELEMENTS = 30000
_HEADING = re.compile(r"^(?:\.|INT\.|EXT\.|INT/EXT\.|EXT/INT\.|I/E\.)", re.I)
_NUMBER = re.compile(r"\s+#([^#\n]{1,48})#$")
_TITLE = re.compile(r"^([\w][\w -]{0,40}):\s*(.+)$")
_PRODUCTION_TAG = re.compile(r"(?<!\w)(PROP|WARDROBE|VFX|SFX|VEHICLE|EXTRA|CAST):\s*([^;\n]+)", re.I)
_SHOT_CUE = re.compile(r"\b(CLOSE ON|INSERT|POV|WIDE SHOT|TRACKING SHOT)\b", re.I)


class ScreenplayError(ValueError):
    """Invalid input or an unapproved fidelity loss; never silently recover."""


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def _bounded(text: str) -> None:
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise ScreenplayError("source is not text or exceeds the 5 MiB input limit")
    if "\x00" in text:
        raise ScreenplayError("NUL is not allowed in a screenplay")


def _element(kind: str, text: str, spans: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if kind not in ELEMENT_TYPES:
        raise ScreenplayError(f"unsupported element: {kind}")
    obj: dict[str, Any] = {"type": kind, "text": text}
    if spans:
        if "".join(span["text"] for span in spans) != text:
            raise ScreenplayError("style spans do not match element text")
        obj["spans"] = spans
    return obj


def _new_document(scenes: list[dict[str, Any]], profile: str, source_format: str,
                  title_lines: list[str] | None = None) -> dict[str, Any]:
    doc = {"schema": SCHEMA, "story_id": "story-" + digest([scenes, title_lines or []])[:20],
           "branch_id": "main", "revision": 1, "profile": profile,
           "title_lines": title_lines or [], "scenes": scenes,
           "provenance": {"source_format": source_format, "fidelity": "BOUNDED_SUBSET"}}
    validate_document(doc)
    return doc


def validate_document(doc: dict[str, Any]) -> None:
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ScreenplayError("invalid canonical screenplay schema")
    if doc.get("profile") not in PROFILES:
        raise ScreenplayError("unknown production profile")
    if not isinstance(doc.get("story_id"), str) or not doc["story_id"]:
        raise ScreenplayError("missing story identity")
    if not isinstance(doc.get("branch_id"), str) or not doc["branch_id"]:
        raise ScreenplayError("missing branch identity")
    if type(doc.get("revision")) is not int or doc["revision"] < 1:
        raise ScreenplayError("invalid screenplay revision")
    if not isinstance(doc.get("provenance"), dict):
        raise ScreenplayError("document provenance is required")
    scenes = doc.get("scenes")
    if not isinstance(scenes, list) or not scenes or len(scenes) > MAX_SCENES:
        raise ScreenplayError("expected 1..3000 screenplay scenes")
    if not isinstance(doc.get("title_lines", []), list) or any(not isinstance(x, str) for x in doc["title_lines"]):
        raise ScreenplayError("invalid title lines")
    seen: set[str] = set()
    count = 0
    for scene in scenes:
        sid = scene.get("scene_id")
        if not isinstance(sid, str) or not sid or sid in seen:
            raise ScreenplayError("scene IDs must be unique and stable")
        seen.add(sid)
        if not isinstance(scene.get("heading"), str) or not scene["heading"]:
            raise ScreenplayError("missing scene heading")
        if scene.get("number") is not None and (not isinstance(scene["number"], str) or not scene["number"]):
            raise ScreenplayError("invalid scene number")
        elements = scene.get("elements")
        if not isinstance(elements, list):
            raise ScreenplayError("scene elements must be a list")
        count += len(elements)
        for el in elements:
            if el.get("type") not in ELEMENT_TYPES or not isinstance(el.get("text"), str):
                raise ScreenplayError("invalid screenplay element")
            if "spans" in el:
                spans = el["spans"]
                if not isinstance(spans, list) or not spans:
                    raise ScreenplayError("empty style spans")
                for span in spans:
                    if not isinstance(span.get("text"), str) or not isinstance(span.get("styles"), list):
                        raise ScreenplayError("invalid style span")
                    if not set(span["styles"]).issubset(STYLES):
                        raise ScreenplayError("unsupported style")
                if "".join(x["text"] for x in spans) != el["text"]:
                    raise ScreenplayError("style spans/text mismatch")
    if count > MAX_ELEMENTS:
        raise ScreenplayError("maximum screenplay element count exceeded")


def _loss(reason: str, at: str) -> dict[str, str]:
    return {"field": at, "reason": reason}


def _fidelity(losses: list[dict[str, str]], *, allow_loss: bool, stage: str) -> None:
    if losses and not allow_loss:
        excerpt = "; ".join(x["field"] + ": " + x["reason"] for x in losses[:4])
        raise ScreenplayError(f"{stage} fidelity blocked; explicit allow_loss required: {excerpt}")


def _fountain_markup(text: str) -> list[dict[str, Any]] | None:
    # Safe, deliberately small subset: exactly one explicitly marked span.
    for marker, styles in (("***", ["Bold", "Italic"]), ("**", ["Bold"]),
                           ("*", ["Italic"]), ("_", ["Underline"])):
        if text.startswith(marker) and text.endswith(marker) and len(text) > 2 * len(marker):
            inner = text[len(marker):-len(marker)]
            if marker not in inner:
                return [{"text": inner, "styles": styles}]
    return None


def parse_fountain(text: str, *, profile: str = "FEATURE", allow_loss: bool = False
                   ) -> tuple[dict[str, Any], dict[str, Any]]:
    _bounded(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    lines = text.split("\n")
    losses: list[dict[str, str]] = []
    title_lines: list[str] = []
    i = 0
    while i < len(lines) and lines[i].strip() and _TITLE.match(lines[i].strip()):
        title_lines.append(lines[i].strip())
        i += 1
    if title_lines and i < len(lines) and not lines[i].strip():
        i += 1
    scenes: list[dict[str, Any]] = []
    dialogue = False
    while i < len(lines):
        original = lines[i]
        line = original.strip()
        i += 1
        if not line:
            dialogue = False
            continue
        if any(x in line for x in ("[[", "]]", "/*", "*/")) or line.endswith("^"):
            losses.append(_loss("notes/boneyards/dual dialogue are outside the supported Fountain subset", f"line {i}"))
            if allow_loss:
                continue
        if line.startswith("~") or line.startswith("=") or line.startswith("#") or line.startswith("!"):
            losses.append(_loss("lyrics/page breaks/sections/forced action are outside the supported subset", f"line {i}"))
            if allow_loss:
                continue
        if _HEADING.match(line):
            heading = line[1:].strip() if line.startswith(".") else line
            m = _NUMBER.search(heading)
            number = m.group(1) if m else None
            if m:
                heading = heading[:m.start()].rstrip()
            if not heading:
                raise ScreenplayError(f"empty scene heading at line {i}")
            scenes.append({"scene_id": f"scene-{len(scenes)+1:06d}", "heading": heading,
                           "number": number, "elements": []})
            dialogue = False
            continue
        if not scenes:
            raise ScreenplayError(f"source text before first scene at line {i}; use a title page")
        kind = "ACTION"
        if dialogue and line.startswith("(") and line.endswith(")"):
            kind, line = "PARENTHETICAL", line[1:-1]
        elif dialogue:
            kind = "DIALOGUE"
        elif line.startswith(">") and line.endswith(":"):
            kind, line = "TRANSITION", line[1:].strip()
        elif line.endswith("TO:") and line.isupper():
            kind = "TRANSITION"
        else:
            next_line = lines[i].strip() if i < len(lines) else ""
            forced = line.startswith("@")
            if forced:
                line = line[1:].strip()
            if forced or (line == line.upper() and len(line) <= 65 and bool(next_line)
                          and bool(re.fullmatch(r"[\wÁÉÍÓÖŐÚÜŰáéíóöőúüű .()'-]+", line))):
                kind, dialogue = "CHARACTER", True
        markup = _fountain_markup(line) if kind in {"ACTION", "DIALOGUE"} else None
        if markup:
            line = markup[0]["text"]
        scenes[-1]["elements"].append(_element(kind, line, markup))
    _fidelity(losses, allow_loss=allow_loss, stage="Fountain import")
    doc = _new_document(scenes, profile, "FOUNTAIN", title_lines)
    receipt = {"format": "fountain", "stage": "IMPORT", "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
               "losses": losses, "fidelity": "LOSSY_OPT_IN" if losses else "SUBSET_SEMANTIC"}
    return doc, receipt


def _styled_text(elem: ET.Element, losses: list[dict[str, str]], at: str) -> tuple[str, list[dict[str, Any]]]:
    txt = "".join(elem.itertext())
    style_raw = elem.attrib.get("Style", "")
    styles = [x for x in re.split(r"[+,]", style_raw) if x]
    unknown = set(elem.attrib) - {"Style"}
    if set(styles) - STYLES or unknown or list(elem):
        losses.append(_loss("unsupported FDX text attributes/styles/nested XML", at))
    return txt, [{"text": txt, "styles": [s for s in styles if s in STYLES]}]


def parse_fdx(text: str, *, profile: str = "FEATURE", allow_loss: bool = False
             ) -> tuple[dict[str, Any], dict[str, Any]]:
    _bounded(text)
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.I):
        raise ScreenplayError("DTD/entity declarations are forbidden in FDX")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ScreenplayError(f"invalid FDX XML: {exc}") from exc
    if root.tag != "FinalDraft" or root.find("Content") is None:
        raise ScreenplayError("FDX must have FinalDraft/Content")
    if sum(1 for _ in root.iter()) > MAX_ELEMENTS * 2:
        raise ScreenplayError("maximum FDX XML element count exceeded")
    losses: list[dict[str, str]] = []
    if set(root.attrib) - {"DocumentType", "Template", "Version"}:
        losses.append(_loss("unmodeled root attributes", "FinalDraft"))
    if root.attrib.get("DocumentType", "Script") != "Script":
        losses.append(_loss("unsupported FinalDraft document type", "FinalDraft.DocumentType"))
    for child in root:
        if child.tag not in {"TitlePage", "Content"}:
            losses.append(_loss("unsupported FDX document section", "FinalDraft/" + child.tag))
    title_lines: list[str] = []
    title = root.find("TitlePage")
    if title is not None:
        title_content = title.find("Content")
        if title_content is not None and (title_content.attrib or any(x.tag != "Paragraph" for x in title_content)):
            losses.append(_loss("unsupported title-page content sections", "TitlePage/Content"))
        if title.attrib or any(x.tag != "Content" for x in title):
            losses.append(_loss("unsupported FDX title-page structure", "TitlePage"))
        for p in title.findall("Content/Paragraph"):
            if set(p.attrib) - {"Type", "Alignment"} or any(x.tag != "Text" for x in p):
                losses.append(_loss("unsupported title paragraph metadata", "TitlePage/Paragraph"))
            text_parts = []
            for t in p.findall("Text"):
                txt, spans = _styled_text(t, losses, "TitlePage/Text")
                if spans and any(sp["styles"] for sp in spans):
                    losses.append(_loss("styled title page currently modeled as plain title text", "TitlePage/Text"))
                text_parts.append(txt)
            title_lines.append("".join(text_parts))
    content_section = root.find("Content")
    if content_section is not None and (content_section.attrib or any(x.tag != "Paragraph" for x in content_section)):
        losses.append(_loss("unsupported screenplay content sections", "Content"))
    scenes: list[dict[str, Any]] = []
    for p in root.findall("Content/Paragraph"):
        if any(x.tag != "Text" for x in p) or set(p.attrib) - {"Type", "Number"}:
            losses.append(_loss("unsupported paragraph metadata or nested sections", "Content/Paragraph"))
        kind = p.attrib.get("Type", "Action")
        texts, spans = [], []
        for part in p.findall("Text"):
            value, part_spans = _styled_text(part, losses, "Content/Paragraph/Text")
            texts.append(value)
            spans.extend(part_spans)
        value = "".join(texts)
        if kind == "Scene Heading":
            scenes.append({"scene_id": f"scene-{len(scenes)+1:06d}", "heading": value,
                           "number": p.attrib.get("Number"), "elements": []})
            continue
        mapped = {"Action": "ACTION", "General": "ACTION", "Character": "CHARACTER",
                  "Parenthetical": "PARENTHETICAL", "Dialogue": "DIALOGUE",
                  "Transition": "TRANSITION", "Shot": "SHOT"}.get(kind)
        if mapped is None:
            losses.append(_loss(f"unmapped FDX paragraph type {kind}", "Content/Paragraph"))
            if allow_loss:
                continue
        if not scenes:
            raise ScreenplayError("FDX screenplay content before the first scene")
        if mapped:
            scenes[-1]["elements"].append(_element(mapped, value, spans if any(x["styles"] for x in spans) else None))
    _fidelity(losses, allow_loss=allow_loss, stage="FDX import")
    doc = _new_document(scenes, profile, "FDX", title_lines)
    return doc, {"format": "fdx", "stage": "IMPORT", "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
                 "losses": losses, "fidelity": "LOSSY_OPT_IN" if losses else "SUBSET_SEMANTIC"}


def import_screenplay(text: str, fmt: str, *, profile: str = "FEATURE", allow_loss: bool = False
                     ) -> tuple[dict[str, Any], dict[str, Any]]:
    if fmt.lower().lstrip(".") == "fountain":
        return parse_fountain(text, profile=profile, allow_loss=allow_loss)
    if fmt.lower().lstrip(".") == "fdx":
        return parse_fdx(text, profile=profile, allow_loss=allow_loss)
    raise ScreenplayError(f"format {fmt!r} has no admitted bidirectional codec")


def _fountain_line(element: dict[str, Any], losses: list[dict[str, str]], where: str) -> str:
    text = element["text"]
    spans = element.get("spans")
    if spans:
        if len(spans) == 1 and spans[0]["styles"]:
            styles = set(spans[0]["styles"])
            marker = {frozenset({"Bold", "Italic"}): "***", frozenset({"Bold"}): "**",
                      frozenset({"Italic"}): "*", frozenset({"Underline"}): "_"}.get(frozenset(styles))
            if marker:
                text = marker + text + marker
            else:
                losses.append(_loss("style combination not representable by the admitted Fountain subset", where))
        elif any(span["styles"] for span in spans):
            losses.append(_loss("mixed inline styles not supported by the Fountain subset", where))
    return text


def export_fountain(doc: dict[str, Any], *, allow_loss: bool = False) -> tuple[str, dict[str, Any]]:
    validate_document(doc)
    losses: list[dict[str, str]] = []
    blocks = ["\n".join(doc["title_lines"])] if doc["title_lines"] else []
    for scene in doc["scenes"]:
        heading = scene["heading"]
        if scene.get("number"):
            heading += " #" + scene["number"] + "#"
        blocks.append(heading)
        dialogue_lines: list[str] = []
        for i, el in enumerate(scene["elements"]):
            where = f"{scene['scene_id']}/element/{i}"
            line = _fountain_line(el, losses, where)
            typ = el["type"]
            if typ == "SHOT":
                losses.append(_loss("FDX shot type not expressible as typed Fountain subset element", where))
                typ = "ACTION"
            if typ == "CHARACTER":
                if dialogue_lines:
                    blocks.append("\n".join(dialogue_lines))
                dialogue_lines = ["@" + line]
            elif typ == "PARENTHETICAL":
                if not dialogue_lines:
                    losses.append(_loss("orphan parenthetical", where))
                    blocks.append("(" + line + ")")
                else:
                    dialogue_lines.append("(" + line + ")")
            elif typ == "DIALOGUE":
                if not dialogue_lines:
                    losses.append(_loss("orphan dialogue", where))
                    blocks.append(line)
                else:
                    dialogue_lines.append(line)
            else:
                if dialogue_lines:
                    blocks.append("\n".join(dialogue_lines))
                    dialogue_lines = []
                blocks.append("> " + line if typ == "TRANSITION" else line)
        if dialogue_lines:
            blocks.append("\n".join(dialogue_lines))
    _fidelity(losses, allow_loss=allow_loss, stage="Fountain export")
    out = "\n\n".join(x for x in blocks if x).rstrip() + "\n"
    return out, {"format": "fountain", "stage": "EXPORT", "source_document_sha256": digest(doc),
                 "losses": losses, "fidelity": "LOSSY_OPT_IN" if losses else "SUBSET_SEMANTIC",
                 "canonical_sidecar_required": True}


def export_fdx(doc: dict[str, Any], *, allow_loss: bool = False) -> tuple[str, dict[str, Any]]:
    validate_document(doc)
    losses: list[dict[str, str]] = []
    root = ET.Element("FinalDraft", DocumentType="Script", Template="No", Version="1")
    if doc["title_lines"]:
        title = ET.SubElement(ET.SubElement(root, "TitlePage"), "Content")
        for line in doc["title_lines"]:
            ET.SubElement(ET.SubElement(title, "Paragraph"), "Text").text = line
    content = ET.SubElement(root, "Content")
    for scene in doc["scenes"]:
        attrs = {"Type": "Scene Heading"}
        if scene.get("number"):
            attrs["Number"] = scene["number"]
        ET.SubElement(ET.SubElement(content, "Paragraph", attrs), "Text").text = scene["heading"]
        for i, el in enumerate(scene["elements"]):
            kind = {"ACTION": "Action", "CHARACTER": "Character", "PARENTHETICAL": "Parenthetical",
                    "DIALOGUE": "Dialogue", "TRANSITION": "Transition", "SHOT": "Shot"}[el["type"]]
            par = ET.SubElement(content, "Paragraph", Type=kind)
            spans = el.get("spans", [{"text": el["text"], "styles": []}])
            for span in spans:
                attrib = {"Style": "+".join(span["styles"])} if span["styles"] else {}
                ET.SubElement(par, "Text", attrib).text = span["text"]
    _fidelity(losses, allow_loss=allow_loss, stage="FDX export")
    out = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"
    return out, {"format": "fdx", "stage": "EXPORT", "source_document_sha256": digest(doc),
                 "losses": losses, "fidelity": "SUBSET_SEMANTIC", "canonical_sidecar_required": True}


def export_screenplay(doc: dict[str, Any], fmt: str, *, allow_loss: bool = False
                     ) -> tuple[str, dict[str, Any]]:
    key = fmt.lower().lstrip(".")
    if key == "fountain":
        return export_fountain(doc, allow_loss=allow_loss)
    if key == "fdx":
        return export_fdx(doc, allow_loss=allow_loss)
    raise ScreenplayError(f"format {fmt!r} has no admitted bidirectional codec")


def fork_branch(doc: dict[str, Any], branch_id: str) -> dict[str, Any]:
    validate_document(doc)
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}", branch_id) or branch_id == doc["branch_id"]:
        raise ScreenplayError("new branch needs a distinct, safe identity")
    out = copy.deepcopy(doc)
    out["branch_id"] = branch_id
    out["revision"] = 1
    out["provenance"] = {"parent_branch": doc["branch_id"], "parent_sha256": digest(doc),
                         "source_format": doc["provenance"].get("source_format", "FA3")}
    validate_document(out)
    return out


def edit_scene(doc: dict[str, Any], scene_id: str, *, heading: str | None = None,
               elements: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    validate_document(doc)
    out = copy.deepcopy(doc)
    scene = next((s for s in out["scenes"] if s["scene_id"] == scene_id), None)
    if scene is None:
        raise ScreenplayError(f"unknown scene: {scene_id}")
    if heading is not None:
        scene["heading"] = heading
    if elements is not None:
        scene["elements"] = elements
    out["revision"] += 1
    out["provenance"] = {"parent_sha256": digest(doc), "last_changed_scene": scene_id,
                         "source_format": "FA3_NATIVE"}
    validate_document(out)
    return out


def _scene_hash(scene: dict[str, Any]) -> str:
    return digest({k: v for k, v in scene.items() if k != "scene_id"})


def _candidate(scene: dict[str, Any], source_index: int, kind: str, value: str,
               *, confidence: str) -> dict[str, Any]:
    sh = _scene_hash(scene)
    return {"id": "candidate-" + digest([scene["scene_id"], sh, source_index, kind, value])[:20],
            "kind": kind, "value": value.strip(), "scene_id": scene["scene_id"],
            "source_element": source_index, "source_scene_sha256": sh,
            "confidence": confidence, "approval": "PENDING"}


def _scene_breakdown(scene: dict[str, Any]) -> dict[str, Any]:
    heading = scene["heading"]
    m = re.match(r"^(INT/EXT\.|EXT/INT\.|I/E\.|INT\.|EXT\.)\s*(.*)", heading, re.I)
    inout = m.group(1).upper() if m else "UNKNOWN"
    remainder = m.group(2) if m else heading
    parts = re.split(r"\s+-\s+", remainder)
    location = parts[0].strip()
    daynight = parts[-1].strip().upper() if len(parts) > 1 else "UNKNOWN"
    proposals: list[dict[str, Any]] = []
    speaking: list[str] = []
    for ix, el in enumerate(scene["elements"]):
        if el["type"] == "CHARACTER":
            name = el["text"].split("(", 1)[0].strip()
            if name and name not in speaking:
                speaking.append(name)
            continue
        if el["type"] not in {"ACTION", "SHOT"}:
            continue
        for match in _PRODUCTION_TAG.finditer(el["text"]):
            kind = match.group(1).upper()
            val = match.group(2).strip(" .,!")
            if val:
                proposals.append(_candidate(scene, ix, kind, val, confidence="EXPLICIT_SOURCE_MARKER"))
        for match in _SHOT_CUE.finditer(el["text"]):
            proposals.append(_candidate(scene, ix, "SHOT_CUE", match.group().upper(),
                                        confidence="DETERMINISTIC_TEXT_CUE"))
    return {"scene_id": scene["scene_id"], "source_scene_sha256": _scene_hash(scene),
            "number": scene.get("number"), "heading": heading, "location": location,
            "inout": inout, "daynight": daynight, "speaking_cast": speaking,
            "silent_and_background_cast_verified": False, "proposals": proposals,
            "status": "REVIEW_REQUIRED" if proposals else "NO_TAG_PROPOSALS"}


def derive_breakdown(doc: dict[str, Any], previous: dict[str, Any] | None = None,
                     *, refresh_affected: bool = False) -> dict[str, Any]:
    validate_document(doc)
    previous_map: dict[str, dict[str, Any]] = {}
    if previous is not None:
        if previous.get("schema") != BREAKDOWN_SCHEMA or previous.get("story_id") != doc["story_id"] \
           or previous.get("branch_id") != doc["branch_id"]:
            raise ScreenplayError("cannot reuse a breakdown from another story or branch")
        previous_map = {s["scene_id"]: s for s in previous["scenes"]}
    result = []
    for scene in doc["scenes"]:
        prior = previous_map.get(scene["scene_id"])
        if prior is not None and prior["source_scene_sha256"] == _scene_hash(scene):
            result.append(copy.deepcopy(prior))
        elif prior is not None and not refresh_affected:
            stale = copy.deepcopy(prior)
            stale["status"] = "STALE"
            result.append(stale)
        else:
            result.append(_scene_breakdown(scene))
    return {"schema": BREAKDOWN_SCHEMA, "story_id": doc["story_id"],
            "branch_id": doc["branch_id"], "source_revision": doc["revision"],
            "source_document_sha256": digest(doc), "profile": doc["profile"],
            "scenes": result, "review_log": copy.deepcopy(previous.get("review_log", [])) if previous else [],
            "authority": "NON_CANONICAL_DERIVED_PROPOSAL"}


def review_candidate(breakdown: dict[str, Any], candidate_id: str, decision: str, actor: str
                    ) -> dict[str, Any]:
    if decision not in {"APPROVED", "REJECTED"} or not actor or not actor.strip():
        raise ScreenplayError("explicit review decision and local actor are required")
    out = copy.deepcopy(breakdown)
    for scene in out.get("scenes", []):
        if scene["status"] == "STALE":
            continue
        for p in scene["proposals"]:
            if p["id"] == candidate_id:
                p["approval"] = decision
                if all(x["approval"] != "PENDING" for x in scene["proposals"]):
                    scene["status"] = "LOCAL_REVIEW_COMPLETE"
                out.setdefault("review_log", []).append({"candidate_id": candidate_id,
                                                            "decision": decision, "actor": actor,
                                                            "assurance": "LOCAL_UNVERIFIED_REVIEW"})
                return out
    raise ScreenplayError("unknown or stale candidate cannot be reviewed")


def project_handoff(doc: dict[str, Any], breakdown: dict[str, Any]) -> dict[str, Any]:
    validate_document(doc)
    if breakdown.get("schema") != BREAKDOWN_SCHEMA or breakdown.get("story_id") != doc["story_id"] \
       or breakdown.get("branch_id") != doc["branch_id"]:
        raise ScreenplayError("foreign breakdown cannot generate project handoff")
    blockers: list[str] = []
    current = {s["scene_id"]: s for s in doc["scenes"]}
    rows = []
    for scene in breakdown["scenes"]:
        source = current.get(scene["scene_id"])
        if source is None or scene["status"] == "STALE" or scene["source_scene_sha256"] != _scene_hash(source):
            blockers.append(f"stale or deleted scene {scene['scene_id']}")
            continue
        pending = [x["id"] for x in scene["proposals"] if x["approval"] == "PENDING"]
        blockers.extend("pending human review " + cid for cid in pending)
        rows.append({"scene_id": scene["scene_id"], "heading": scene["heading"],
                     "inout": scene["inout"], "daynight": scene["daynight"],
                     "location": scene["location"], "speaking_cast_only": scene["speaking_cast"],
                     "silent_and_background_cast_unknown": True,
                     "approved_tags": [{"kind": p["kind"], "value": p["value"], "source_element": p["source_element"]}
                                       for p in scene["proposals"] if p["approval"] == "APPROVED"]})
    if len(rows) != len(doc["scenes"]):
        blockers.append("not all source scenes have a current breakdown")
    if breakdown.get("source_document_sha256") != digest(doc):
        blockers.append("document revision differs; rederive the breakdown before handoff")
    return {"schema": "fa3.screenplay-handoff.v1", "story_id": doc["story_id"],
            "branch_id": doc["branch_id"], "source_document_sha256": digest(doc),
            "profile": doc["profile"], "status": "BLOCKED" if blockers else "LOCAL_REVIEW_ONLY",
            "publish_authority": False, "schedule_authority": False, "model_invocations": 0,
            "blockers": blockers, "film_planning_scene_rows": rows,
            "editorial_projection": {"target": "FA3 Video Editor / QuickClip", "editable_project_generated": False,
                                     "native_project_formats_preserved": ["project.fa3video", ".fa3clip"]},
            "notes": ["Speaking cast does not prove silent or background cast absence.",
                      "No authoritative shooting schedule, AI model call or native editor project is created."]}
