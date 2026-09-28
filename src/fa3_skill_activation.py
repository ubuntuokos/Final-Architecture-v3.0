#!/usr/bin/env python3
"""FA3 Skill Fabric: read-only, task-scoped exact-byte activation.

This is a data materializer, NOT an admission, identity, execution or evidence
authority. The caller must supply independently issuer-verified admission,
selection and lease callbacks from the existing FA3 authorities. No network,
subprocess, shell, model call or write to a skill package occurs here.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

SHA256 = re.compile(r"^[0-9a-f]{64}$")
MAX_SKILL_BYTES = 4 * 1024 * 1024
ReceiptVerifier = Callable[[Mapping[str, Any]], bool]
TokenCounter = Callable[[str], int]


class SkillActivationDenied(RuntimeError):
    pass


def _need(condition: bool, reason: str) -> None:
    if not condition:
        raise SkillActivationDenied(reason)


def _relative_parts(path: Any) -> tuple[str, ...]:
    _need(isinstance(path, str) and bool(path), "SKILL_PATH_INVALID")
    _need("\\" not in path and not path.startswith("/"), "SKILL_PATH_INVALID")
    parts = tuple(path.split("/"))
    _need(all(part not in ("", ".", "..") and "\x00" not in part for part in parts), "SKILL_PATH_INVALID")
    return parts


def read_snapshot_file(package_root: Path, entrypoint: str) -> bytes:
    """Open every path component relative to an already trusted package root.

    Linux/POSIX O_NOFOLLOW + dir_fd prevent symlink traversal inside the
    snapshot. The package root itself must be handed over by a trusted store.
    Never return a pathname to be reopened by a later consumer.
    """
    root = Path(package_root).absolute()
    _need(not root.is_symlink(), "PACKAGE_ROOT_SYMLINK")
    parts = _relative_parts(entrypoint)
    dir_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC | os.O_NOFOLLOW
    fd = -1
    try:
        fd = os.open(root, dir_flags)
        _need(stat.S_ISDIR(os.fstat(fd).st_mode), "PACKAGE_ROOT_NOT_DIRECTORY")
        for part in parts[:-1]:
            next_fd = os.open(part, dir_flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        file_fd = os.open(parts[-1], file_flags, dir_fd=fd)
        try:
            info = os.fstat(file_fd)
            _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "SKILL_NOT_PRIVATE_REGULAR_FILE")
            _need(info.st_size <= MAX_SKILL_BYTES, "SKILL_TOO_LARGE")
            # A bounded read rejects growth between fstat and read.
            data = bytearray()
            while len(data) <= MAX_SKILL_BYTES:
                chunk = os.read(file_fd, min(65536, MAX_SKILL_BYTES + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
            _need(len(data) <= MAX_SKILL_BYTES, "SKILL_TOO_LARGE")
            after = os.fstat(file_fd)
            _need(
                stat.S_ISREG(after.st_mode)
                and (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
                == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
                "SKILL_CHANGED_DURING_READ",
            )
            return bytes(data)
        finally:
            os.close(file_fd)
    except (OSError, ValueError) as exc:
        raise SkillActivationDenied("SNAPSHOT_OPEN_DENIED") from exc
    finally:
        if fd >= 0:
            os.close(fd)


class ActiveSkillContext:
    """Ephemeral context owned by the caller's with-block; no persistent file."""

    def __init__(self, payload: bytes, receipt: dict[str, Any]) -> None:
        self._buffer = bytearray(payload)
        self._active = True
        self.receipt = receipt
        self.close_receipt: dict[str, Any] | None = None

    def read_text(self) -> str:
        _need(self._active, "SKILL_LEASE_CLOSED")
        return self._buffer.decode("utf-8", errors="strict")

    def close(self) -> dict[str, Any]:
        if self.close_receipt is not None:
            return self.close_receipt
        for index in range(len(self._buffer)):
            self._buffer[index] = 0
        self._buffer.clear()
        self._active = False
        self.close_receipt = {
            "schema": "fa3.skill-activation-close-receipt.v1",
            "state": "CLOSED",
            "materialization_receipt_ref": self.receipt["materialization_receipt_ref"],
            "ephemeral_buffer_cleared": True,
            "no_persistent_snapshot_written": True,
            "current_host_production_claim": False,
        }
        return self.close_receipt


def _verified_receipt(verifier: ReceiptVerifier, receipt: Mapping[str, Any], reason: str) -> None:
    _need(callable(verifier), "TRUSTED_RECEIPT_VERIFIER_REQUIRED")
    try:
        authorized = verifier(receipt)
    except Exception as exc:
        raise SkillActivationDenied(reason) from exc
    _need(authorized is True, reason)


@contextmanager
def activate_admitted_skill(
    *,
    package_root: Path,
    package: dict[str, Any],
    admission_receipt: dict[str, Any],
    selection_receipt: dict[str, Any],
    activation_lease: dict[str, Any],
    skill_id: str,
    task_id: str,
    verify_admission: ReceiptVerifier,
    verify_selection: ReceiptVerifier,
    verify_lease: ReceiptVerifier,
    count_tokens: TokenCounter,
    now_epoch: int | None = None,
) -> Iterator[ActiveSkillContext]:
    """Materialize one admitted, single-entrypoint, fully snapshotted skill.

    Receipts must be independently verified by their existing issuer adapters;
    comparing self-declared PASS JSON alone is intentionally insufficient.
    Multi-file packages fail closed until whole-manifest snapshot verification
    is available. Scripts, tools, dependencies and remote fetch never execute.
    """
    from fa3_skill_fabric_gate import package_admission_allowed

    _need(bool(skill_id) and bool(task_id), "TASK_OR_SKILL_MISSING")
    _need(package_admission_allowed(package), "PACKAGE_NOT_ADMITTED_BY_POLICY")
    _verified_receipt(verify_admission, admission_receipt, "ADMISSION_RECEIPT_UNVERIFIED")
    _verified_receipt(verify_selection, selection_receipt, "SELECTION_RECEIPT_UNVERIFIED")
    _verified_receipt(verify_lease, activation_lease, "ACTIVATION_LEASE_UNVERIFIED")

    entrypoints = package.get("entrypoints", [])
    _need(isinstance(entrypoints, list) and len(entrypoints) == 1, "SINGLE_ENTRYPOINT_SNAPSHOT_REQUIRED")
    entrypoint = entrypoints[0]
    _need(isinstance(entrypoint, dict), "ENTRYPOINT_INVALID")
    path = entrypoint.get("path")
    _need(isinstance(package.get("files"), list) and package["files"] == [path],
          "WHOLE_MANIFEST_VERIFICATION_REQUIRED")
    _relative_parts(path)
    digest = package["digests"]["content_sha256"]
    manifest = package["digests"]["manifest_sha256"]
    _need(SHA256.fullmatch(digest) is not None and SHA256.fullmatch(manifest) is not None,
          "PACKAGE_DIGEST_INVALID")

    _need(
        admission_receipt.get("status") == "PASS"
        and admission_receipt.get("package_id") == package["package_id"]
        and admission_receipt.get("source_commit") == package["source"]["commit"]
        and admission_receipt.get("content_sha256") == digest
        and admission_receipt.get("manifest_sha256") == manifest
        and admission_receipt.get("entrypoint_path") == path
        and admission_receipt.get("skill_version") == entrypoint.get("version")
        and bool(admission_receipt.get("admission_receipt_ref")),
        "ADMISSION_BINDING_MISMATCH",
    )

    eligible = selection_receipt.get("eligible_skill_ids")
    selected = selection_receipt.get("selected_skill_ids")
    _need(
        selection_receipt.get("status") == "PASS"
        and selection_receipt.get("task_id") == task_id
        and isinstance(eligible, list) and isinstance(selected, list)
        and all(isinstance(x, str) and bool(x) for x in eligible + selected)
        and len(set(selected)) == len(selected)
        and len(set(eligible)) == len(eligible)
        and set(selected).issubset(set(eligible))
        and skill_id in selected
        and selection_receipt.get("package_id") == package["package_id"]
        and selection_receipt.get("admission_receipt_ref") == admission_receipt["admission_receipt_ref"]
        and bool(selection_receipt.get("selection_receipt_ref")),
        "SELECTION_BINDING_MISMATCH",
    )

    current = int(time.time()) if now_epoch is None else now_epoch
    _need(type(current) is int, "CLOCK_INVALID")
    _need(
        activation_lease.get("state") == "ACTIVE_FOR_TASK"
        and activation_lease.get("task_id") == task_id
        and activation_lease.get("skill_id") == skill_id
        and activation_lease.get("selection_receipt_ref") == selection_receipt["selection_receipt_ref"]
        and activation_lease.get("admission_receipt_ref") == admission_receipt["admission_receipt_ref"]
        and activation_lease.get("content_sha256") == digest
        and type(activation_lease.get("expires_at_epoch")) is int
        and current < activation_lease["expires_at_epoch"]
        and bool(activation_lease.get("activation_lease_ref")),
        "LEASE_BINDING_OR_EXPIRY_MISMATCH",
    )

    actual = read_snapshot_file(package_root, path)
    _need(hashlib.sha256(actual).hexdigest() == digest, "SKILL_SOURCE_DIGEST_MISMATCH")
    try:
        content = actual.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise SkillActivationDenied("SKILL_UTF8_INVALID") from exc
    _need(callable(count_tokens), "CONTEXT_TOKEN_COUNTER_REQUIRED")
    try:
        actual_tokens = count_tokens(content)
    except Exception as exc:
        raise SkillActivationDenied("CONTEXT_TOKEN_COUNT_FAILED") from exc
    budget = package["context_budget"]
    _need(type(actual_tokens) is int and 0 <= actual_tokens <= budget["instructions_max_tokens"],
          "CONTEXT_BUDGET_EXCEEDED")
    _need(actual_tokens <= budget["instructions_used_tokens"], "CONTEXT_BUDGET_ATTESTATION_UNDERCOUNT")

    receipt = {
        "schema": "fa3.skill-materialization-receipt.v1",
        "materialization_receipt_ref": "skill-materialize:" + hashlib.sha256(
            (task_id + "\0" + skill_id + "\0" + digest + "\0" +
             selection_receipt["selection_receipt_ref"]).encode("utf-8")).hexdigest(),
        "state": "ACTIVE_FOR_TASK",
        "task_id": task_id,
        "skill_id": skill_id,
        "package_id": package["package_id"],
        "skill_version": entrypoint["version"],
        "content_sha256": hashlib.sha256(actual).hexdigest(),
        "manifest_sha256": manifest,
        "dependency_digest_sha256": package["dependencies"]["digest_sha256"],
        "admission_receipt_ref": admission_receipt["admission_receipt_ref"],
        "selection_receipt_ref": selection_receipt["selection_receipt_ref"],
        "activation_lease_ref": activation_lease["activation_lease_ref"],
        "expires_at_epoch": activation_lease["expires_at_epoch"],
        "instructions_used_tokens": actual_tokens,
        "read_only": True,
        "remote_fetch": False,
        "exec": False,
        "authority": False,
        "current_host_production_claim": False,
    }
    context = ActiveSkillContext(actual, receipt)
    try:
        yield context
    finally:
        context.close()


def reference_regressions() -> dict[str, Any]:
    """Side-effect-free except temporary local fixture files; NOT current-host proof."""
    import copy
    import tempfile
    from fa3_skill_fabric_gate import good_package
    content = b"---\nname: example\ndescription: Demo\n---\nReview the task.\n"
    digest = hashlib.sha256(content).hexdigest()
    package = good_package()
    package["digests"]["content_sha256"] = digest
    package["hash_attestation"]["sha256"] = digest
    package["evaluation"]["bound_content_sha256"] = digest
    path = package["entrypoints"][0]["path"]
    admission = {
        "status": "PASS", "package_id": package["package_id"],
        "source_commit": package["source"]["commit"],
        "content_sha256": digest, "manifest_sha256": package["digests"]["manifest_sha256"],
        "entrypoint_path": path, "skill_version": "1.0.0", "admission_receipt_ref": "admit:1",
    }
    selection = {
        "status": "PASS", "task_id": "task:1", "package_id": package["package_id"],
        "admission_receipt_ref": "admit:1", "selection_receipt_ref": "select:1",
        "eligible_skill_ids": ["example"], "selected_skill_ids": ["example"],
    }
    lease = {
        "state": "ACTIVE_FOR_TASK", "task_id": "task:1", "skill_id": "example",
        "selection_receipt_ref": "select:1", "admission_receipt_ref": "admit:1",
        "content_sha256": digest, "activation_lease_ref": "lease:1", "expires_at_epoch": 2000000000,
    }
    checks: dict[str, bool] = {}
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        target = root / path
        target.parent.mkdir(parents=True)
        target.write_bytes(content)
        def attempt(**changes: Any) -> bool:
            args = {
                "package_root": root, "package": package, "admission_receipt": admission,
                "selection_receipt": selection, "activation_lease": lease,
                "skill_id": "example", "task_id": "task:1",
                "verify_admission": lambda r: r is admission,
                "verify_selection": lambda r: r is selection,
                "verify_lease": lambda r: r is lease,
                "count_tokens": lambda s: len(s.split()), "now_epoch": 1900000000,
            }
            args.update(changes)
            try:
                with activate_admitted_skill(**args) as activated:
                    _need(activated.read_text().encode() == content, "REOPEN_MISMATCH")
                _need(activated.close_receipt["state"] == "CLOSED", "CLEANUP_MISSING")
                try:
                    activated.read_text()
                except SkillActivationDenied:
                    return True
                return False
            except SkillActivationDenied:
                return False
        checks["exact-bytes-positive-and-cleanup"] = attempt()
        target.write_bytes(content + b"\nCHANGED\n")
        checks["modified-bytes-denied"] = not attempt()
        target.unlink()
        outside = root / "outside"
        outside.write_bytes(content)
        target.symlink_to(outside)
        checks["symlink-denied"] = not attempt()
        target.unlink()
        target.write_bytes(content)
        checks["foreign-task-denied"] = not attempt(task_id="task:else")
        checks["missing-selection-denied"] = not attempt(selection_receipt={})
        checks["unverified-admission-denied"] = not attempt(verify_admission=lambda r: False)
        stale = copy.deepcopy(lease)
        stale["expires_at_epoch"] = 1899999999
        checks["expired-lease-denied"] = not attempt(activation_lease=stale, verify_lease=lambda r: r is stale)
        expanded = copy.deepcopy(selection)
        expanded["selected_skill_ids"].append("not-eligible")
        checks["selection-expansion-denied"] = not attempt(
            selection_receipt=expanded, verify_selection=lambda r: r is expanded
        )
        wrong_root = root / "wrong"
        wrong_root.symlink_to(root, target_is_directory=True)
        checks["root-symlink-denied"] = not attempt(package_root=wrong_root)
        checks["token-overflow-denied"] = not attempt(count_tokens=lambda s: 999999)
    return {
        "schema": "fa3.skill-activation-reference-regressions.v1",
        "result": "PASS" if all(checks.values()) else "FAIL",
        "total": len(checks), "cases": checks,
        "current_host_production_claim": False,
    }
