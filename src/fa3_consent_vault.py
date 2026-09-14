#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import shlex
import subprocess
import tempfile
from pathlib import Path


class ConsentVaultError(RuntimeError):
    pass


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class FA3ConsentVault:
    """Erasable encrypted storage kept outside the immutable audit ledger.

    Encryption/decryption is delegated to an approved external provider
    (for example age, SOPS, Vault Transit, TPM-backed tooling). The vault never
    persists plaintext. The audit ledger should store only the opaque consent
    reference and the ciphertext digest returned by `put`.
    """

    def __init__(
        self,
        root: str | os.PathLike[str],
        *,
        encrypt_command: str,
        decrypt_command: str,
    ) -> None:
        if not encrypt_command.strip() or not decrypt_command.strip():
            raise ConsentVaultError("encrypt and decrypt commands are required")
        self.root = Path(root)
        self.encrypt_argv = shlex.split(encrypt_command)
        self.decrypt_argv = shlex.split(decrypt_command)
        if not self.encrypt_argv or not self.decrypt_argv:
            raise ConsentVaultError("invalid encryption command")
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)

    def _record_path(self, consent_ref: str) -> Path:
        if not consent_ref or len(consent_ref) > 512:
            raise ConsentVaultError("invalid consent_ref")
        opaque = hashlib.sha256(consent_ref.encode("utf-8")).hexdigest()
        return self.root / f"{opaque}.enc"

    @staticmethod
    def _run(argv: list[str], payload: bytes) -> bytes:
        try:
            result = subprocess.run(
                argv,
                input=payload,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ConsentVaultError(f"crypto provider execution failed: {exc}") from exc
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace")[-1000:]
            raise ConsentVaultError(
                f"crypto provider rejected operation (exit={result.returncode}): {detail}"
            )
        if not result.stdout:
            raise ConsentVaultError("crypto provider returned empty output")
        return result.stdout

    def put(self, consent_ref: str, plaintext: bytes) -> str:
        if not plaintext:
            raise ConsentVaultError("empty consent payload is forbidden")
        ciphertext = self._run(self.encrypt_argv, plaintext)
        if ciphertext == plaintext:
            raise ConsentVaultError("crypto provider returned plaintext unchanged")
        target = self._record_path(consent_ref)
        fd, tmp = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(self.root))
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(ciphertext)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, target)
            _fsync_dir(self.root)
        except Exception:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise
        return "sha256:" + hashlib.sha256(ciphertext).hexdigest()

    def get(self, consent_ref: str) -> bytes:
        target = self._record_path(consent_ref)
        try:
            ciphertext = target.read_bytes()
        except FileNotFoundError as exc:
            raise ConsentVaultError("consent record not found") from exc
        return self._run(self.decrypt_argv, ciphertext)

    def delete(self, consent_ref: str) -> bool:
        target = self._record_path(consent_ref)
        try:
            target.unlink()
        except FileNotFoundError:
            return False
        _fsync_dir(self.root)
        return True

    def exists(self, consent_ref: str) -> bool:
        return self._record_path(consent_ref).is_file()
