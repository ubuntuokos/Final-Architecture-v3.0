#!/usr/bin/env python3
from __future__ import annotations

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
    "MUSIC_VIDEO", "SHORT_FORM", "INTERACTIVE", "CUSTOM",
}
ROLES = {"OWNER", "AUTHOR", "EDITOR", "COMMENTER", "FINAL_PUBLISHER", "RELEASE_APPROVER"}
EDIT_ROLES = {"OWNER", "AUTHOR", "EDITOR"}
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
        "branches": [{"branch_id": "main", "label": "Main", "parent_branch_id": None}],
        "stash": [],
        "notes": [],
        "releases": [],
        "codec_registry": [
            {"media_type": "application/x-fountain", "import": True, "export": True, "roundtrip_test_required": True},
            {"media_type": "application/vnd.finaldraft", "import": True, "export": True, "roundtrip_test_required": True},
        ],
    }
