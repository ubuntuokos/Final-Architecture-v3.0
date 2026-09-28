#!/usr/bin/env python3
"""FA3 PR Watch: authenticated GitHub observation, never an execution authority.

Ingress is deliberately transport-free. An admitted webhook receiver may hand over
the exact GitHub payload/signature/secret FD. The adapter does not open ports,
fetch remote code, execute user-supplied instructions, or contact model providers.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import hmac
import json
import os
import re
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "fa3.pr-watch-projection.v1"
EVENT_SCHEMA = "fa3.pr-watch-event.v1"
MAX_PAYLOAD = 1_048_576
MAX_EVENTS = 10_000
MAX_ITEMS = 1_000
SHA40 = re.compile(r"^[a-fA-F0-9]{40}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ACTOR = re.compile(r"^[A-Za-z0-9_-]{1,39}(\[bot\])?$")
DELIVERY = re.compile(r"^[A-Za-z0-9_.:-]{1,150}$")
ACTIONS = {
    "pull_request": frozenset({"opened", "synchronize", "reopened", "ready_for_review", "closed"}),
    "issues": frozenset({"opened", "reopened", "assigned", "closed"}),
    "issue_comment": frozenset({"created"}),
    "pull_request_review": frozenset({"submitted"}),
    "check_run": frozenset({"completed"}),
    "workflow_run": frozenset({"completed"}),
}
READ_ONLY = "OBSERVATION_ONLY"


class PRWatchDenied(ValueError):
    """Fail-closed error with a code; never interpolate external payload/secrets."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _required_str(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PRWatchDenied(code)
    return value.strip()


def _timestamp(value: Any) -> str:
    if not isinstance(value, str):
        raise PRWatchDenied("TIMESTAMP_REQUIRED")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise PRWatchDenied("TIMESTAMP_INVALID") from None
    if parsed.tzinfo is None:
        raise PRWatchDenied("TIMESTAMP_TIMEZONE_REQUIRED")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_title(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(c if c.isprintable() and c not in "\r\n\t" else " " for c in value)[:200]


def verify_signature(body: bytes, signature: str, secret: bytes) -> None:
    """GitHub X-Hub-Signature-256. A signature authenticates transport, not an actor's permissions."""
    if not isinstance(body, bytes) or len(body) > MAX_PAYLOAD or not body:
        raise PRWatchDenied("PAYLOAD_SIZE_OR_TYPE")
    if not isinstance(secret, bytes) or len(secret) < 16 or len(secret) > 4096:
        raise PRWatchDenied("SECRET_INVALID")
    if not isinstance(signature, str) or not re.fullmatch(r"sha256=[0-9a-fA-F]{64}", signature):
        raise PRWatchDenied("SIGNATURE_INVALID")
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature.lower()):
        raise PRWatchDenied("SIGNATURE_MISMATCH")


def normalize_webhook(
    body: bytes, *, signature: str, secret: bytes, event_type: str, delivery_id: str,
) -> dict[str, Any]:
    verify_signature(body, signature, secret)
    if event_type not in ACTIONS:
        raise PRWatchDenied("EVENT_NOT_SUPPORTED")
    if not isinstance(delivery_id, str) or not DELIVERY.fullmatch(delivery_id):
        raise PRWatchDenied("DELIVERY_ID_INVALID")
    try:
        raw = json.loads(body)
    except (UnicodeError, ValueError):
        raise PRWatchDenied("PAYLOAD_JSON_INVALID") from None
    if not isinstance(raw, dict) or raw.get("action") not in ACTIONS[event_type]:
        raise PRWatchDenied("EVENT_ACTION_NOT_SUPPORTED")
    repository = raw.get("repository")
    sender = raw.get("sender")
    if not isinstance(repository, dict) or not isinstance(sender, dict):
        raise PRWatchDenied("REPOSITORY_OR_SENDER_MISSING")
    repo = _required_str(repository.get("full_name"), "REPOSITORY_INVALID")
    actor = _required_str(sender.get("login"), "ACTOR_INVALID")
    if not REPO.fullmatch(repo) or not ACTOR.fullmatch(actor):
        raise PRWatchDenied("REPOSITORY_OR_ACTOR_INVALID")

    obj: dict[str, Any]
    if event_type == "pull_request":
        obj = raw.get("pull_request")
    elif event_type == "issues":
        obj = raw.get("issue")
    elif event_type == "issue_comment":
        obj = raw.get("issue")
    elif event_type == "pull_request_review":
        obj = raw.get("pull_request")
    else:
        container = raw.get(event_type)
        prs = container.get("pull_requests") if isinstance(container, dict) else None
        if not isinstance(prs, list) or len(prs) != 1:
            raise PRWatchDenied("CHECK_PR_BINDING_AMBIGUOUS")
        obj = prs[0]
    if not isinstance(obj, dict) or type(obj.get("number")) is not int or obj["number"] < 1:
        raise PRWatchDenied("EXTERNAL_OBJECT_INVALID")

    number = obj["number"]
    is_pr = (event_type in {"pull_request", "pull_request_review", "check_run", "workflow_run"}
             or event_type == "issue_comment" and isinstance(obj.get("pull_request"), dict))
    kind = "PR" if is_pr else "ISSUE"
    observation_only = event_type in {"issue_comment", "pull_request_review", "check_run", "workflow_run"}
    revision = obj.get("updated_at") or obj.get("created_at")
    if observation_only:
        source = raw.get("comment") or raw.get("review") or raw.get("check_run") or raw.get("workflow_run")
        if isinstance(source, dict):
            revision = source.get("updated_at") or source.get("created_at") or revision
    if not revision:
        raise PRWatchDenied("TIMESTAMP_REQUIRED")

    head_sha = ""
    base_sha = ""
    if event_type == "pull_request":
        head, base = obj.get("head"), obj.get("base")
        if not isinstance(head, dict) or not isinstance(base, dict):
            raise PRWatchDenied("PR_REFS_REQUIRED")
        head_sha = _required_str(head.get("sha"), "HEAD_SHA_REQUIRED").lower()
        base_sha = _required_str(base.get("sha"), "BASE_SHA_REQUIRED").lower()
        if not SHA40.fullmatch(head_sha) or not SHA40.fullmatch(base_sha):
            raise PRWatchDenied("PR_SHA_INVALID")
    # Check/review events cannot silently replace a previously observed PR head.
    canonical_key = f"github:{repo.lower()}:{kind.lower()}:{number}"
    return {
        "schema": EVENT_SCHEMA,
        "source": "VERIFIED_GITHUB_WEBHOOK",
        "event_type": event_type,
        "action": raw["action"],
        "delivery_id": delivery_id,
        "payload_sha256": hashlib.sha256(body).hexdigest(),
        "external_key": canonical_key,
        "repository": repo,
        "number": number,
        "kind": kind,
        "actor": actor,
        "actor_authorized": False,
        "revision": _timestamp(revision),
        "title": _clean_title(obj.get("title")),
        "head_sha": head_sha,
        "base_sha": base_sha,
        "observation_only": observation_only,
        "action_authorized": False,
        "canonical_evidence": False,
    }


def default_state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME")
    if base:
        p = Path(base).expanduser()
        if not p.is_absolute():
            raise PRWatchDenied("XDG_STATE_HOME_NOT_ABSOLUTE")
    else:
        p = Path.home() / ".local" / "state"
    return p / "fa3" / "pr-watch"


def _new_state() -> dict[str, Any]:
    return {
        "schema": SCHEMA, "status": READ_ONLY,
        "authority": False, "execution_enabled": False,
        "items": {}, "delivery_digests": {},
    }


def _safe_regular_file(path: Path) -> None:
    if path.is_symlink():
        raise PRWatchDenied("SYMLINK_STATE_PATH")
    if path.exists():
        mode = path.stat().st_mode
        if not stat.S_ISREG(mode) or mode & 0o077:
            raise PRWatchDenied("UNSAFE_STATE_PERMISSIONS")


class ProjectionStore:
    """A local read-only operator projection. Canonical identity/evidence remain elsewhere."""

    def __init__(self, state_dir: Path | None = None):
        self.state_dir = Path(state_dir) if state_dir is not None else default_state_dir()

    def _paths(self) -> tuple[Path, Path]:
        return self.state_dir / "projection.json", self.state_dir / ".projection.lock"

    def _ensure_dir(self) -> None:
        p = self.state_dir
        if p.is_symlink():
            raise PRWatchDenied("SYMLINK_STATE_PATH")
        p.mkdir(mode=0o700, parents=True, exist_ok=True)
        if p.is_symlink() or p.stat().st_mode & 0o077:
            raise PRWatchDenied("UNSAFE_STATE_DIRECTORY")

    def read(self) -> dict[str, Any]:
        path, _ = self._paths()
        _safe_regular_file(path)
        if not path.exists():
            return _new_state()
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError, OSError):
            raise PRWatchDenied("STATE_CORRUPT") from None
        if not isinstance(state, dict) or state.get("schema") != SCHEMA or state.get("authority") is not False or state.get("execution_enabled") is not False:
            raise PRWatchDenied("STATE_AUTHORITY_DRIFT")
        if not isinstance(state.get("items"), dict) or not isinstance(state.get("delivery_digests"), dict):
            raise PRWatchDenied("STATE_CORRUPT")
        return state

    def ingest(self, event: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(event, dict) or event.get("schema") != EVENT_SCHEMA or event.get("source") != "VERIFIED_GITHUB_WEBHOOK":
            raise PRWatchDenied("EVENT_UNVERIFIED")
        self._ensure_dir()
        path, lock = self._paths()
        _safe_regular_file(lock)
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "w") as lk:
                fcntl.flock(lk, fcntl.LOCK_EX)
                state = self.read()
                delivery_key = hashlib.sha256((event["repository"].lower() + "\0" + event["delivery_id"]).encode()).hexdigest()
                digest = event["payload_sha256"]
                old = state["delivery_digests"].get(delivery_key)
                if old is not None:
                    return {"status": "DUPLICATE" if old == digest else "CONFLICT",
                            "external_key": event["external_key"], "execution_performed": False}
                if len(state["delivery_digests"]) >= MAX_EVENTS:
                    raise PRWatchDenied("EVENT_RETENTION_LIMIT_REQUIRES_RECONCILIATION")
                key = event["external_key"]
                item = state["items"].get(key)
                if item is None and len(state["items"]) >= MAX_ITEMS:
                    raise PRWatchDenied("ITEM_RETENTION_LIMIT_REQUIRES_RECONCILIATION")
                status = "INGESTED"
                if item is not None and not event["observation_only"]:
                    if event["revision"] < item["revision"]:
                        status = "STALE"
                    elif event["revision"] == item["revision"] and event["head_sha"] and item["head_sha"] and event["head_sha"] != item["head_sha"]:
                        status = "CONFLICT"
                if status == "INGESTED":
                    # No raw issue body/comment, actor permission claim or canonical work-item identity.
                    current = item or {
                        "external_key": key, "repository": event["repository"],
                        "number": event["number"], "kind": event["kind"],
                        "canonical_work_item_id": None, "reconciliation_state": "PENDING",
                        "head_sha": "", "base_sha": "", "revision": "", "title": "",
                    }
                    current["last_event"] = event["event_type"] + ":" + event["action"]
                    current["last_actor"] = event["actor"]
                    current["observed_at"] = event["revision"]
                    if not event["observation_only"]:
                        current["revision"] = event["revision"]
                        if event["title"]:
                            current["title"] = event["title"]
                        if event["head_sha"]:
                            current["head_sha"], current["base_sha"] = event["head_sha"], event["base_sha"]
                    state["items"][key] = current
                state["delivery_digests"][delivery_key] = digest
                state["last_observed_at"] = event["revision"]
                self._write(path, state)
                return {"status": status, "external_key": key, "execution_performed": False}
        finally:
            pass

    @staticmethod
    def _write(path: Path, data: dict[str, Any]) -> None:
        _safe_regular_file(path)
        fd, tmp = tempfile.mkstemp(prefix=".projection-", suffix=".json", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                os.fchmod(out.fileno(), 0o600)
                json.dump(data, out, sort_keys=True, ensure_ascii=False, indent=2)
                out.write("\n")
                out.flush()
                os.fsync(out.fileno())
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def operator_projection(self) -> dict[str, Any]:
        state = self.read()
        items = sorted(state["items"].values(), key=lambda x: (x.get("observed_at", ""), x["external_key"]), reverse=True)
        return {
            "schema": SCHEMA, "status": READ_ONLY,
            "authority": False, "execution_enabled": False,
            "count": len(items), "items": items,
            "last_observed_at": state.get("last_observed_at", ""),
        }


def preview_goal_plan(
    root: Path, item: dict[str, Any], goal: dict[str, Any],
    steps: list[dict[str, Any]], preflight: dict[str, Any],
) -> dict[str, Any]:
    """Compile only a proposal using existing FA3 Goal/Workforce/Workload validators."""
    if item.get("kind") != "PR" or not SHA40.fullmatch(item.get("head_sha", "")):
        raise PRWatchDenied("IMMUTABLE_PR_SHA_REQUIRED")
    if (preflight.get("source_sha") != item["head_sha"]
            or preflight.get("repository_scope") != item["repository"]):
        raise PRWatchDenied("SOURCE_OR_SCOPE_DRIFT")
    from fa3_goal_execution import compile_plan
    result = compile_plan(root, goal, steps, preflight)
    return {
        "schema": "fa3.pr-watch-plan-preview.v1",
        "source_sha": item["head_sha"],
        "external_key": item["external_key"],
        "proposal": result,
        "authority": False, "execution_performed": False,
        "requires_authenticated_uaf_security_hrb_router_and_temporal": True,
    }


def preview_evidence(goal: dict[str, Any], observations: list[dict[str, Any]]) -> dict[str, Any]:
    from fa3_goal_execution import assess_evidence
    result = assess_evidence(goal, observations)
    if result.get("verification_claim") is not False or result.get("canonical_gate_required") is not True:
        raise PRWatchDenied("EVIDENCE_AUTHORITY_DRIFT")
    return result


def _json_file(filename: str) -> Any:
    if filename == "-":
        return json.load(sys.stdin)
    with open(filename, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FA3 PR Watch (authenticated read-only GitHub adapter)")
    parser.add_argument("--state-dir", type=Path, default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    ing = sub.add_parser("ingest", help="Verify signed GitHub payload and update local read-only projection")
    ing.add_argument("--payload", required=True, help="Exact webhook payload path; - for stdin")
    ing.add_argument("--signature", required=True, help="X-Hub-Signature-256 header")
    ing.add_argument("--event", required=True, help="X-GitHub-Event header")
    ing.add_argument("--delivery", required=True, help="X-GitHub-Delivery header")
    ing.add_argument("--secret-fd", required=True, type=int, help="Preopened secret FD from admitted Secret Broker")
    sub.add_parser("list", help="Print non-authoritative projection")
    plan = sub.add_parser("preview-plan", help="Compile non-executing existing Goal/Workload plan")
    for name in ("goal", "steps", "preflight"):
        plan.add_argument("--" + name, required=True)
    plan.add_argument("--external-key", required=True)
    plan.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ev = sub.add_parser("preview-evidence", help="Check reference completeness, never award PASS")
    ev.add_argument("--goal", required=True)
    ev.add_argument("--observations", required=True)
    args = parser.parse_args(argv)
    try:
        store = ProjectionStore(args.state_dir)
        if args.command == "ingest":
            if args.secret_fd < 3:
                raise PRWatchDenied("SECRET_FD_INVALID")
            secret = os.read(args.secret_fd, 4097)
            os.close(args.secret_fd)
            if args.payload == "-":
                body = sys.stdin.buffer.read(MAX_PAYLOAD + 1)
            else:
                if Path(args.payload).stat().st_size > MAX_PAYLOAD:
                    raise PRWatchDenied("PAYLOAD_SIZE_OR_TYPE")
                body = Path(args.payload).read_bytes()
            result = store.ingest(normalize_webhook(
                body, signature=args.signature, secret=secret,
                event_type=args.event, delivery_id=args.delivery,
            ))
        elif args.command == "list":
            result = store.operator_projection()
        elif args.command == "preview-plan":
            item = store.read()["items"].get(args.external_key)
            if item is None:
                raise PRWatchDenied("UNKNOWN_EXTERNAL_KEY")
            result = preview_goal_plan(args.root, item, _json_file(args.goal),
                                       _json_file(args.steps), _json_file(args.preflight))
        else:
            result = preview_evidence(_json_file(args.goal), _json_file(args.observations))
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (PRWatchDenied, OSError, ValueError, TypeError, KeyError) as ex:
        # Do not echo attacker-controlled body, configured secret or untrusted field values.
        code = ex.code if isinstance(ex, PRWatchDenied) else "INPUT_OR_IO_DENIED"
        print(json.dumps({"status": "DENIED", "code": code}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
