#!/usr/bin/env python3
from __future__ import annotations

from collections import deque
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

SCHEMA = "fa3.story-studio-project.v1"
NOTE_SCHEMA = "fa3.story-studio-note.v1"
RELEASE_SCHEMA = "fa3.story-studio-final-release.v1"

PRODUCTION_PROFILES = {
    "FEATURE_FILM", "TV_MOVIE", "TV_SERIES", "COMMERCIAL", "LIVE_BROADCAST",
    "DOCUMENTARY", "NEWS_MAGAZINE", "ANIMATION", "AUDIO_DRAMA", "STAGE_PLAY",
    "MUSIC_VIDEO", "SHORT_FORM", "INTERACTIVE", "DUBBING_LOCALIZATION", "CUSTOM",
}
ROLES = {
    "OWNER", "AUTHOR", "EDITOR", "COMMENTER", "FINAL_PUBLISHER", "RELEASE_APPROVER",
    "TRANSLATOR", "ADAPTOR", "DUBBING_DIRECTOR", "RECORDING_ENGINEER", "VOICE_ACTOR",
}
EDIT_ROLES = {"OWNER", "AUTHOR", "EDITOR", "TRANSLATOR", "ADAPTOR", "DUBBING_DIRECTOR"}
RELEASE_POLICIES = {"SINGLE_DESIGNATED", "ANY_DESIGNATED", "ALL_DESIGNATED"}


class StoryStudioError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _members(project: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for member in project.get("collaboration", {}).get("members", []):
        actor_id = member.get("actor_id")
        if not isinstance(actor_id, str) or not actor_id:
            raise StoryStudioError("collaboration member actor_id required")
        if actor_id in out:
            raise StoryStudioError(f"duplicate collaboration member: {actor_id}")
        roles = member.get("roles", [])
        if not isinstance(roles, list) or not roles:
            raise StoryStudioError(f"roles required for {actor_id}")
        unknown = set(roles) - ROLES
        if unknown:
            raise StoryStudioError(f"unknown roles for {actor_id}: {sorted(unknown)}")
        out[actor_id] = member
    return out


def validate_project(project: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(project, dict) or project.get("schema") != SCHEMA:
        raise StoryStudioError("story studio project schema mismatch")
    if not project.get("project_id"):
        raise StoryStudioError("project_id required")
    if project.get("production_profile") not in PRODUCTION_PROFILES:
        raise StoryStudioError("supported production_profile required")

    members = _members(project)
    collaboration = project.get("collaboration", {})
    final_publishers = collaboration.get("final_publishers", [])
    if not isinstance(final_publishers, list) or not final_publishers:
        raise StoryStudioError("at least one designated final publisher required")
    if any(actor_id not in members for actor_id in final_publishers):
        raise StoryStudioError("final publisher must be a collaboration member")
    for actor_id in final_publishers:
        roles = set(members[actor_id].get("roles", []))
        if not roles & {"OWNER", "FINAL_PUBLISHER"}:
            raise StoryStudioError("designated final publisher lacks release role")
    policy = collaboration.get("release_policy")
    if policy not in RELEASE_POLICIES:
        raise StoryStudioError("explicit release_policy required")
    if policy == "SINGLE_DESIGNATED" and len(final_publishers) != 1:
        raise StoryStudioError("SINGLE_DESIGNATED requires exactly one final publisher")

    branches = project.get("branches", [])
    ids: set[str] = set()
    for branch in branches:
        branch_id = branch.get("branch_id")
        if not branch_id or branch_id in ids:
            raise StoryStudioError("branch_id must be unique and non-empty")
        ids.add(branch_id)
    for branch in branches:
        parent = branch.get("parent_branch_id")
        if parent is not None and parent not in ids:
            raise StoryStudioError("branch parent must exist")

    codecs = project.get("codec_registry", [])
    validate_codec_registry(codecs)

    for stash in project.get("stash", []):
        for key in ("stash_id", "content", "source_document_id", "author", "created_at"):
            if not stash.get(key):
                raise StoryStudioError(f"stash entry missing {key}")

    return {
        "result": "PASS",
        "project_id": project["project_id"],
        "production_profile": project["production_profile"],
        "collaborators": len(members),
        "final_publishers": list(final_publishers),
        "branches": len(branches),
        "stash_entries": len(project.get("stash", [])),
    }


def validate_codec_registry(codecs: list[dict[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    for codec in codecs:
        media_type = codec.get("media_type")
        if not isinstance(media_type, str) or not media_type:
            raise StoryStudioError("codec media_type required")
        if media_type in seen:
            raise StoryStudioError(f"duplicate codec media_type: {media_type}")
        seen.add(media_type)
        if codec.get("import") is not True or codec.get("export") is not True:
            raise StoryStudioError(f"one-way codec forbidden: {media_type}")
        if codec.get("roundtrip_test_required") is not True:
            raise StoryStudioError(f"roundtrip gate required: {media_type}")
    return {"result": "PASS", "codec_count": len(seen)}


def can_edit(project: dict[str, Any], actor_id: str) -> bool:
    members = _members(project)
    return actor_id in members and bool(set(members[actor_id].get("roles", [])) & EDIT_ROLES)


PROJECT_NODE_TYPES = {
    "PROJECT_SPEC", "STORY_DOCUMENT", "SCREENPLAY", "SERIES_BIBLE", "SEASON_BIBLE",
    "RUNDOWN", "SEGMENT", "SCENE", "BEAT", "SHOT", "STORYBOARD_CARD", "CHARACTER",
    "LOCATION", "ENVIRONMENT", "ASSET", "AUDIO", "CAPTION", "TIMELINE_SEGMENT",
    "REVIEW_NOTE", "APPROVAL", "DELIVERY",
}
PROJECT_EDGE_TYPES = {
    "DEPENDS_ON", "DERIVED_FROM", "BINDS_MEDIA", "CONTINUES_FROM",
    "PROVIDES_CONTEXT", "EDIT_SOURCE", "REVISION_IMPACTS",
}


def _project_node_map(project: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for node in project.get("nodes", []):
        node_id = node.get("node_id")
        if not isinstance(node_id, str) or not node_id:
            raise StoryStudioError("project node_id required")
        if node_id in out:
            raise StoryStudioError(f"duplicate project node_id: {node_id}")
        if node.get("type") not in PROJECT_NODE_TYPES:
            raise StoryStudioError(f"unsupported project node type: {node.get('type')}")
        out[node_id] = node
    return out


def validate_project_graph(project: dict[str, Any]) -> dict[str, Any]:
    nodes = _project_node_map(project)
    for edge in project.get("edges", []):
        if edge.get("type") not in PROJECT_EDGE_TYPES:
            raise StoryStudioError(f"unsupported project edge type: {edge.get('type')}")
        if edge.get("from") not in nodes or edge.get("to") not in nodes:
            raise StoryStudioError("project edge references unknown node")
        if not isinstance(edge.get("invalidate_on_revision"), bool):
            raise StoryStudioError("invalidate_on_revision must be explicit boolean")
    return {"result": "PASS", "nodes": len(nodes), "edges": len(project.get("edges", []))}


def plan_scoped_revision(
    project: dict[str, Any],
    *,
    actor_id: str,
    changed_node_ids: list[str],
) -> dict[str, Any]:
    """Compute only explicit downstream invalidation; preserve unrelated work by default."""
    validate_project(project)
    if not can_edit(project, actor_id):
        raise StoryStudioError("actor cannot edit project")
    validate_project_graph(project)
    nodes = _project_node_map(project)
    if not changed_node_ids or any(node_id not in nodes for node_id in changed_node_ids):
        raise StoryStudioError("changed_node_ids must reference known project nodes")

    graph: dict[str, list[str]] = {node_id: [] for node_id in nodes}
    for edge in project.get("edges", []):
        if edge["invalidate_on_revision"]:
            graph[edge["from"]].append(edge["to"])

    affected = set(changed_node_ids)
    queue = deque(sorted(affected))
    while queue:
        current = queue.popleft()
        for child in sorted(graph[current]):
            if child not in affected:
                affected.add(child)
                queue.append(child)

    approval_nodes = sorted(
        node_id for node_id in affected
        if nodes[node_id].get("locked") is True or nodes[node_id].get("human_approved") is True
    )
    return {
        "schema": "fa3.story-studio-scoped-revision-plan.v1",
        "project_id": project["project_id"],
        "requested_by": actor_id,
        "changed_node_ids": sorted(set(changed_node_ids)),
        "affected_node_ids": sorted(affected),
        "preserved_node_ids": sorted(set(nodes) - affected),
        "approval_required": bool(approval_nodes),
        "approval_boundary_node_ids": approval_nodes,
        "unaffected_nodes_preserved": True,
        "full_project_regeneration_default": False,
        "execution_authorized": False,
        "model_provider_selection": "FA3-AUTH-MODEL-ROUTER-001",
        "host_resource_admission": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "action_execution": "FA3-UNIFIED-ACTION-FABRIC-001",
    }


def _document_map(project: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for doc in project.get("documents", []):
        document_id = doc.get("document_id")
        if not isinstance(document_id, str) or not document_id:
            raise StoryStudioError("document_id required")
        if document_id in out:
            raise StoryStudioError(f"duplicate document_id: {document_id}")
        if not isinstance(doc.get("revision"), int) or doc["revision"] < 0:
            raise StoryStudioError("document revision must be a non-negative integer")
        out[document_id] = doc
    return out


def apply_collaborative_edit(
    project: dict[str, Any],
    *,
    actor_id: str,
    document_id: str,
    base_revision: int,
    content: str,
    change_summary: str,
) -> dict[str, Any]:
    """Apply an attributed optimistic-concurrency edit; stale writers fail closed."""
    validate_project(project)
    if not can_edit(project, actor_id):
        raise StoryStudioError("actor cannot edit project")
    documents = _document_map(project)
    if document_id not in documents:
        raise StoryStudioError("document not found")
    doc = documents[document_id]
    if base_revision != doc["revision"]:
        raise StoryStudioError(
            f"revision conflict: expected {doc['revision']}, got {base_revision}"
        )
    previous_digest = str(doc.get("content_digest") or sha256(
        str(doc.get("content", "")).encode("utf-8")
    ).hexdigest())
    next_revision = doc["revision"] + 1
    next_digest = sha256(content.encode("utf-8")).hexdigest()
    revision = {
        "document_id": document_id,
        "revision": next_revision,
        "parent_revision": base_revision,
        "parent_content_digest": previous_digest,
        "content_digest": next_digest,
        "author": actor_id,
        "change_summary": change_summary,
        "created_at": _utc_now(),
    }
    doc["content"] = content
    doc["revision"] = next_revision
    doc["content_digest"] = next_digest
    project.setdefault("revision_history", []).append(revision)
    return deepcopy(revision)


def add_collaboration_comment(
    project: dict[str, Any],
    *,
    actor_id: str,
    document_id: str,
    body: str,
    anchor: str | None = None,
) -> dict[str, Any]:
    validate_project(project)
    members = _members(project)
    if actor_id not in members:
        raise StoryStudioError("actor is not a project collaborator")
    if document_id not in _document_map(project):
        raise StoryStudioError("document not found")
    if not body:
        raise StoryStudioError("comment body required")
    comment = {
        "comment_id": f"comment-{len(project.get('comments', [])) + 1}",
        "document_id": document_id,
        "anchor": anchor,
        "author": actor_id,
        "body": body,
        "created_at": _utc_now(),
        "resolved": False,
    }
    project.setdefault("comments", []).append(comment)
    return deepcopy(comment)


def create_branch(
    project: dict[str, Any],
    *,
    actor_id: str,
    branch_id: str,
    label: str,
    parent_branch_id: str | None = None,
    from_node_id: str | None = None,
) -> dict[str, Any]:
    validate_project(project)
    if not can_edit(project, actor_id):
        raise StoryStudioError("actor cannot edit project")
    if any(item.get("branch_id") == branch_id for item in project.get("branches", [])):
        raise StoryStudioError("branch_id already exists")
    if parent_branch_id is not None and not any(
        item.get("branch_id") == parent_branch_id for item in project.get("branches", [])
    ):
        raise StoryStudioError("parent branch does not exist")
    branch = {
        "branch_id": branch_id,
        "label": label,
        "parent_branch_id": parent_branch_id,
        "from_node_id": from_node_id,
        "created_by": actor_id,
        "created_at": _utc_now(),
    }
    project.setdefault("branches", []).append(branch)
    return deepcopy(branch)


def stash_rejected_content(
    project: dict[str, Any],
    *,
    actor_id: str,
    stash_id: str,
    content: str,
    source_document_id: str,
    source_range: str,
    source_revision: str,
    reason: str,
) -> dict[str, Any]:
    validate_project(project)
    if not can_edit(project, actor_id):
        raise StoryStudioError("actor cannot edit project")
    if not content:
        raise StoryStudioError("rejected content cannot be empty")
    if any(item.get("stash_id") == stash_id for item in project.get("stash", [])):
        raise StoryStudioError("stash_id already exists")
    entry = {
        "stash_id": stash_id,
        "content": content,
        "source_document_id": source_document_id,
        "source_range": source_range,
        "source_revision": source_revision,
        "author": actor_id,
        "reason": reason,
        "created_at": _utc_now(),
    }
    project.setdefault("stash", []).append(entry)
    return deepcopy(entry)


def save_stash_as_note(
    project: dict[str, Any],
    *,
    actor_id: str,
    stash_id: str,
    note_id: str,
    title: str,
) -> dict[str, Any]:
    validate_project(project)
    members = _members(project)
    if actor_id not in members:
        raise StoryStudioError("actor is not a project collaborator")
    stash = next((x for x in project.get("stash", []) if x.get("stash_id") == stash_id), None)
    if stash is None:
        raise StoryStudioError("stash entry not found")
    if any(x.get("note_id") == note_id for x in project.get("notes", [])):
        raise StoryStudioError("note_id already exists")
    note = {
        "schema": NOTE_SCHEMA,
        "note_id": note_id,
        "title": title,
        "content": stash["content"],
        "note_kind": "REJECTED_CONTENT",
        "source_stash_id": stash_id,
        "source_document_id": stash["source_document_id"],
        "source_range": stash.get("source_range"),
        "source_revision": stash.get("source_revision"),
        "original_author": stash.get("author"),
        "saved_by": actor_id,
        "created_at": _utc_now(),
        "standalone_export_allowed": True,
    }
    project.setdefault("notes", []).append(note)
    return deepcopy(note)


def render_note_markdown(note: dict[str, Any]) -> str:
    if note.get("schema") != NOTE_SCHEMA:
        raise StoryStudioError("note schema mismatch")
    metadata = [
        f"# {note.get('title', 'Story note')}",
        "",
        f"- Source document: {note.get('source_document_id', '')}",
        f"- Source range: {note.get('source_range', '')}",
        f"- Source revision: {note.get('source_revision', '')}",
        f"- Original author: {note.get('original_author', '')}",
        "",
        note.get("content", ""),
        "",
    ]
    return "\n".join(metadata)


def issue_final_release(
    project: dict[str, Any],
    *,
    actor_id: str,
    revision_digest: str,
    approvals: list[str] | None = None,
) -> dict[str, Any]:
    validate_project(project)
    collaboration = project["collaboration"]
    final_publishers = list(collaboration["final_publishers"])
    policy = collaboration["release_policy"]
    if actor_id not in final_publishers:
        raise StoryStudioError("actor is not a designated final publisher")
    if not isinstance(revision_digest, str) or len(revision_digest) < 16:
        raise StoryStudioError("revision_digest required")

    approval_set = set(approvals or [])
    if policy == "SINGLE_DESIGNATED" and actor_id != final_publishers[0]:
        raise StoryStudioError("only the single designated publisher may release")
    if policy == "ALL_DESIGNATED" and not set(final_publishers).issubset(approval_set | {actor_id}):
        raise StoryStudioError("all designated final publishers must approve")

    receipt_material = "|".join([
        project["project_id"], revision_digest, actor_id, policy,
        ",".join(sorted(approval_set | {actor_id}))
    ])
    receipt = {
        "schema": RELEASE_SCHEMA,
        "project_id": project["project_id"],
        "revision_digest": revision_digest,
        "released_by": actor_id,
        "release_policy": policy,
        "publisher_approvals": sorted(approval_set | {actor_id}),
        "released_at": _utc_now(),
        "receipt_digest": sha256(receipt_material.encode("utf-8")).hexdigest(),
        "final": True,
    }
    project.setdefault("releases", []).append(receipt)
    return deepcopy(receipt)



PRESENTATION_TYPES = {
    "PITCH_DECK", "TREATMENT_DECK", "SERIES_BIBLE_DECK", "CHARACTER_DECK",
    "LOCATION_DECK", "STORYBOARD_DECK", "PRODUCTION_BRIEF", "LIVE_SHOW_DECK",
}
DUBBING_DOCUMENT_TYPES = {
    "DIALOGUE_LIST", "PIVOT_DIALOGUE_LIST", "DUBBING_ADAPTATION_SCRIPT",
    "AS_RECORDED_DUBBING_SCRIPT", "ADR_CUE_SHEET", "CHARACTER_SCRIPT",
}
DUBBING_SCHEMA = "fa3.dubbing-script.v1"


def build_presentation_projection(
    project: dict[str, Any],
    *,
    actor_id: str,
    presentation_type: str,
    selected_node_ids: list[str],
    title: str,
) -> dict[str, Any]:
    """Build a non-authoritative Story -> Presentation projection plan."""
    validate_project(project)
    members = _members(project)
    if actor_id not in members:
        raise StoryStudioError("actor is not a project collaborator")
    if presentation_type not in PRESENTATION_TYPES:
        raise StoryStudioError("unsupported presentation_type")
    nodes = _project_node_map(project)
    if not selected_node_ids or any(node_id not in nodes for node_id in selected_node_ids):
        raise StoryStudioError("presentation projection requires known story node refs")
    if not title:
        raise StoryStudioError("presentation title required")
    return {
        "schema": "fa3.story-presentation-projection.v1",
        "project_id": project["project_id"],
        "presentation_type": presentation_type,
        "title": title,
        "requested_by": actor_id,
        "source_node_refs": list(dict.fromkeys(selected_node_ids)),
        "source_story_profile": "FA3-STORY-001",
        "document_capability": "CAP-018",
        "primary_human_authoring": "LIBREOFFICE_IMPRESS_UNO",
        "optional_generation_provider": "FA3-PROVIDER-PRESENTON-001",
        "provider_authority": False,
        "writeback_mode": "LINKED_REFERENCE_OR_EXPLICIT_PROPOSAL",
        "silent_story_mutation": False,
        "final_story_release_authority_transferred": False,
    }


def validate_dubbing_script(document: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(document, dict) or document.get("schema") != DUBBING_SCHEMA:
        raise StoryStudioError("dubbing script schema mismatch")
    if document.get("document_type") not in DUBBING_DOCUMENT_TYPES:
        raise StoryStudioError("unsupported dubbing document_type")
    for key in ("document_id", "target_language", "source_video_digest", "source_revision"):
        if not document.get(key):
            raise StoryStudioError(f"dubbing script missing {key}")
    digest = str(document["source_video_digest"])
    normalized_digest = digest[7:] if digest.startswith("sha256:") else digest
    if len(normalized_digest) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in normalized_digest):
        raise StoryStudioError("source_video_digest must be SHA-256")

    seen: set[str] = set()
    events = document.get("events", [])
    if not isinstance(events, list):
        raise StoryStudioError("dubbing events must be a list")
    for event in events:
        for key in (
            "cue_id", "source_event_ref", "source_character", "in_timecode_ms",
            "out_timecode_ms", "source_text", "target_text",
        ):
            if key not in event or event[key] in (None, ""):
                raise StoryStudioError(f"dubbing cue missing {key}")
        cue_id = str(event["cue_id"])
        if cue_id in seen:
            raise StoryStudioError(f"duplicate dubbing cue_id: {cue_id}")
        seen.add(cue_id)
        start = event["in_timecode_ms"]
        end = event["out_timecode_ms"]
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
            raise StoryStudioError(f"invalid dubbing timing for {cue_id}")
        if document["document_type"] == "AS_RECORDED_DUBBING_SCRIPT" and not event.get("as_recorded_text"):
            raise StoryStudioError(f"as-recorded text required for {cue_id}")

    if document["document_type"] == "AS_RECORDED_DUBBING_SCRIPT" and not document.get("final_audio_digest"):
        raise StoryStudioError("final_audio_digest required for as-recorded dubbing script")
    return {
        "result": "PASS",
        "document_id": document["document_id"],
        "document_type": document["document_type"],
        "target_language": document["target_language"],
        "cue_count": len(events),
        "source_video_bound": True,
        "frame_accurate_timing_required": True,
        "caption_timing_profile": "FA3-CAPTION-SUBTITLE-001",
        "voice_authority": "FA3-VOICE-001",
        "provider_selection_owned_by_story_studio": False,
    }


def build_dubbing_conformance_plan(
    document: dict[str, Any],
    *,
    new_source_revision: str,
    changed_source_event_refs: list[str],
) -> dict[str, Any]:
    """Plan re-alignment after source dialogue/video revision without silently rewriting adaptation."""
    validate_dubbing_script(document)
    if not new_source_revision:
        raise StoryStudioError("new_source_revision required")
    changed = set(changed_source_event_refs)
    affected = [
        event["cue_id"] for event in document.get("events", [])
        if event.get("source_event_ref") in changed
    ]
    return {
        "schema": "fa3.dubbing-conformance-plan.v1",
        "document_id": document["document_id"],
        "old_source_revision": document["source_revision"],
        "new_source_revision": new_source_revision,
        "affected_cue_ids": affected,
        "stage_1": "ALIGN_AND_RETIME",
        "stage_2": "REVIEW_AND_EXPLICITLY_ADAPT_CONTENT",
        "silent_target_text_rewrite": False,
        "human_review_required": bool(affected),
    }


SPOILER_MODES = {
    "SPOILER_FREE_TEASER",
    "LIGHT_SPOILER",
    "PARTIAL_PLOT",
    "FULL_PLOT",
    "ENDING_EXPLAINED",
    "CHARACTER_ARC",
    "EPISODE_RECAP",
}
SPOILER_LEVEL_BY_MODE = {
    "SPOILER_FREE_TEASER": "NONE",
    "LIGHT_SPOILER": "LIGHT",
    "PARTIAL_PLOT": "PARTIAL",
    "FULL_PLOT": "FULL",
    "ENDING_EXPLAINED": "ENDING",
    "CHARACTER_ARC": "PARTIAL",
    "EPISODE_RECAP": "FULL",
}


def build_spoiler_generation_plan(
    project: dict[str, Any],
    *,
    actor_id: str,
    source_document_id: str,
    source_revision: int,
    branch_id: str,
    mode: str,
    source_node_refs: list[str],
    intended_audience: str,
) -> dict[str, Any]:
    """Plan a non-authoritative spoiler derivative from one explicit story revision and branch."""
    validate_project(project)
    members = _members(project)
    if actor_id not in members:
        raise StoryStudioError("actor is not a project collaborator")
    if mode not in SPOILER_MODES:
        raise StoryStudioError("unsupported spoiler mode")
    documents = _document_map(project)
    if source_document_id not in documents:
        raise StoryStudioError("source document not found")
    source_doc = documents[source_document_id]
    if source_revision != source_doc["revision"]:
        raise StoryStudioError("spoiler source revision must match selected document revision")
    branches = {item.get("branch_id") for item in project.get("branches", [])}
    if branch_id not in branches:
        raise StoryStudioError("spoiler branch must exist")
    if not source_node_refs:
        raise StoryStudioError("spoiler source_node_refs required")
    nodes = _project_node_map(project)
    if any(node_id not in nodes for node_id in source_node_refs):
        raise StoryStudioError("spoiler source_node_refs must reference known story nodes")
    if not intended_audience:
        raise StoryStudioError("intended_audience required")

    source_digest = str(source_doc.get("content_digest") or sha256(
        str(source_doc.get("content", "")).encode("utf-8")
    ).hexdigest())
    released_digests = {r.get("revision_digest") for r in project.get("releases", []) if r.get("final") is True}
    source_is_released = source_digest in released_digests

    return {
        "schema": "fa3.spoiler-generation-plan.v1",
        "project_id": project["project_id"],
        "source_document_id": source_document_id,
        "source_revision": source_revision,
        "source_revision_digest": source_digest,
        "branch_id": branch_id,
        "source_node_refs": list(dict.fromkeys(source_node_refs)),
        "mode": mode,
        "disclosure_level": SPOILER_LEVEL_BY_MODE[mode],
        "intended_audience": intended_audience,
        "source_is_released": source_is_released,
        "draft_marker_required": not source_is_released,
        "cross_branch_detail_mixing": False,
        "canonical_story_mutation": False,
        "model_provider_selection": "FA3-AUTH-MODEL-ROUTER-001",
        "host_resource_admission": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "external_publication_requires_release_approval": True,
        "execution_authorized": False,
    }


def register_spoiler_derivative(
    project: dict[str, Any],
    *,
    actor_id: str,
    spoiler_id: str,
    plan: dict[str, Any],
    text: str,
    disclosure_map: list[dict[str, Any]],
) -> dict[str, Any]:
    """Register generated spoiler text while preserving source lineage and disclosure metadata."""
    validate_project(project)
    if actor_id not in _members(project):
        raise StoryStudioError("actor is not a project collaborator")
    if plan.get("schema") != "fa3.spoiler-generation-plan.v1":
        raise StoryStudioError("spoiler generation plan schema mismatch")
    if not spoiler_id or not text:
        raise StoryStudioError("spoiler_id and text required")
    if any(x.get("spoiler_id") == spoiler_id for x in project.get("spoiler_derivatives", [])):
        raise StoryStudioError("spoiler_id already exists")
    if not isinstance(disclosure_map, list) or not disclosure_map:
        raise StoryStudioError("spoiler disclosure_map required")
    allowed_refs = set(plan.get("source_node_refs", []))
    for item in disclosure_map:
        if item.get("source_node_ref") not in allowed_refs:
            raise StoryStudioError("disclosure map references node outside selected spoiler source")
        if item.get("level") not in {"NONE", "LIGHT", "PARTIAL", "FULL", "ENDING"}:
            raise StoryStudioError("invalid disclosure level")
    derivative = {
        "schema": "fa3.spoiler-derivative.v1",
        "spoiler_id": spoiler_id,
        "created_by": actor_id,
        "created_at": _utc_now(),
        "source_document_id": plan["source_document_id"],
        "source_revision": plan["source_revision"],
        "source_revision_digest": plan["source_revision_digest"],
        "branch_id": plan["branch_id"],
        "source_node_refs": deepcopy(plan["source_node_refs"]),
        "mode": plan["mode"],
        "disclosure_level": plan["disclosure_level"],
        "intended_audience": plan["intended_audience"],
        "draft_marker_required": plan["draft_marker_required"],
        "text": text,
        "text_digest": sha256(text.encode("utf-8")).hexdigest(),
        "disclosure_map": deepcopy(disclosure_map),
        "canonical_story_mutation": False,
        "external_publication_approved": False,
    }
    project.setdefault("spoiler_derivatives", []).append(derivative)
    return deepcopy(derivative)


def approve_spoiler_publication(
    project: dict[str, Any],
    *,
    actor_id: str,
    spoiler_id: str,
) -> dict[str, Any]:
    """Approve a spoiler derivative for external publication using release-capable roles."""
    validate_project(project)
    members = _members(project)
    if actor_id not in members:
        raise StoryStudioError("actor is not a project collaborator")
    roles = set(members[actor_id].get("roles", []))
    if not roles & {"OWNER", "FINAL_PUBLISHER", "RELEASE_APPROVER"}:
        raise StoryStudioError("actor cannot approve spoiler publication")
    item = next((x for x in project.get("spoiler_derivatives", []) if x.get("spoiler_id") == spoiler_id), None)
    if item is None:
        raise StoryStudioError("spoiler derivative not found")
    item["external_publication_approved"] = True
    item["publication_approved_by"] = actor_id
    item["publication_approved_at"] = _utc_now()
    return deepcopy(item)

def new_reference_project() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "project_id": "story-demo",
        "production_profile": "FEATURE_FILM",
        "collaboration": {
            "members": [
                {"actor_id": "writer-a", "display_name": "Writer A", "roles": ["OWNER", "AUTHOR", "FINAL_PUBLISHER"]},
                {"actor_id": "writer-b", "display_name": "Writer B", "roles": ["AUTHOR"]},
            ],
            "final_publishers": ["writer-a"],
            "release_policy": "SINGLE_DESIGNATED",
        },
        "documents": [
            {
                "document_id": "screenplay-1",
                "document_type": "SCREENPLAY",
                "content": "",
                "revision": 0,
                "content_digest": sha256(b"").hexdigest(),
            }
        ],
        "revision_history": [],
        "comments": [],
        "nodes": [
            {"node_id": "story-1", "type": "STORY_DOCUMENT", "locked": False},
            {"node_id": "scene-1", "type": "SCENE", "locked": False},
            {"node_id": "shot-1", "type": "SHOT", "locked": False},
            {"node_id": "delivery-1", "type": "DELIVERY", "locked": True, "human_approved": True},
        ],
        "edges": [
            {"type": "DERIVED_FROM", "from": "story-1", "to": "scene-1", "invalidate_on_revision": True},
            {"type": "DERIVED_FROM", "from": "scene-1", "to": "shot-1", "invalidate_on_revision": True},
            {"type": "REVISION_IMPACTS", "from": "shot-1", "to": "delivery-1", "invalidate_on_revision": True},
        ],
        "branches": [{"branch_id": "main", "label": "Main", "parent_branch_id": None}],
        "stash": [],
        "notes": [],
        "releases": [],
        "spoiler_derivatives": [],
        "codec_registry": [
            {"media_type": "application/x-fountain", "import": True, "export": True, "roundtrip_test_required": True},
            {"media_type": "application/vnd.finaldraft", "import": True, "export": True, "roundtrip_test_required": True},
        ],
    }
