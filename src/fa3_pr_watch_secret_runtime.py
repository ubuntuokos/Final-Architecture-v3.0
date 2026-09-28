#!/usr/bin/env python3
"""Opt-in FA3 PR Watch credential projection and receiver lifecycle.

Only the *existing* FA3 Secret Broker authorizes credential reads. The
supervisor transfers a single credential over a one-shot inherited pipe; no
secret text is passed in argv, environment, files, logs or the projection.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from fa3_pr_watch import PRWatchDenied
from fa3_secret_broker import DEFAULT_SOCKET, request

CONSUMER_ID = "FA3-PR-WATCH-001"
SECRET_KIND = "GENERIC_FA3_CREDENTIAL"
PROJECTION = "UDS_SINGLE_SECRET"
DEFAULT_SECRET_REF = "integration/relay/001"
RECEIVER_ENTRYPOINT = Path(__file__).resolve().parents[1] / "bin/fa3-pr-watch-receiver"


def obtain_single_secret(
    secret_ref: str, broker_socket: Path,
    broker_request: Callable[[Path, dict[str, Any]], dict[str, Any]] = request,
) -> bytearray:
    """Retrieve only the explicitly configured SecretRef, with metadata checks."""
    if not isinstance(secret_ref, str) or not secret_ref or len(secret_ref) > 256:
        raise PRWatchDenied("SECRET_REF_REQUIRED")
    from fa3_secret_broker import valid_secret_id
    if not valid_secret_id(secret_ref):
        raise PRWatchDenied("SECRET_REF_INVALID")
    result = broker_request(Path(broker_socket), {
        "op": "get", "secret_id": secret_ref,
        "consumer_id": CONSUMER_ID, "projection": PROJECTION,
    })
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise PRWatchDenied("BROKER_DENIED")
    meta = result.get("metadata")
    if not isinstance(meta, dict) or any((
        meta.get("secret_id") != secret_ref,
        meta.get("classification") != "MACHINE_SERVICE_SECRET",
        meta.get("secret_kind") != SECRET_KIND,
        type(meta.get("version")) is not int,
        meta.get("version", 0) < 1,
    )):
        raise PRWatchDenied("BROKER_METADATA_MISMATCH")
    encoded = result.get("secret_b64")
    if not isinstance(encoded, str) or len(encoded) > 6000:
        raise PRWatchDenied("BROKER_VALUE_INVALID")
    try:
        secret = bytearray(base64.b64decode(encoded, validate=True))
    except (ValueError, base64.binascii.Error):
        raise PRWatchDenied("BROKER_VALUE_INVALID") from None
    if not 16 <= len(secret) <= 4096:
        for i in range(len(secret)):
            secret[i] = 0
        raise PRWatchDenied("BROKER_VALUE_INVALID")
    return secret


def launch_receiver(
    secret: bytearray, *, bind: str = "127.0.0.1", port: int = 0,
    state_dir: Path | None = None,
    receiver_entrypoint: Path = RECEIVER_ENTRYPOINT,
    operator_export_path: Path | None = None,
) -> subprocess.Popen:
    """Supply a preopened one-shot secret FD to the existing receiver process."""
    import ipaddress
    if (not isinstance(secret, bytearray) or not 16 <= len(secret) <= 4096
            or not 0 <= port <= 65535):
        raise PRWatchDenied("LAUNCH_PARAMETERS_INVALID")
    try:
        ip = ipaddress.ip_address(bind)
    except ValueError:
        raise PRWatchDenied("LOOPBACK_REQUIRED") from None
    if not ip.is_loopback:
        raise PRWatchDenied("LOOPBACK_REQUIRED")
    if not receiver_entrypoint.is_file():
        raise PRWatchDenied("RECEIVER_ENTRYPOINT_MISSING")
    rd, wr = os.pipe2(os.O_CLOEXEC)
    try:
        command = [sys.executable, str(receiver_entrypoint), "--secret-fd", str(rd),
                   "--bind", bind, "--port", str(port)]
        if state_dir is not None:
            command += ["--state-dir", str(state_dir)]
        if operator_export_path is not None:
            command += ["--operator-export-path", str(operator_export_path)]
        # No inherited broker or GitHub credentials reach the receiver child.
        env = {k: v for k, v in os.environ.items()
               if not any(word in k.upper() for word in
                          ("TOKEN", "PASSWORD", "SECRET", "API_KEY", "GITHUB", "GH_", "GIT_"))}
        process = subprocess.Popen(command, pass_fds=(rd,), close_fds=True,
                                   stdin=subprocess.DEVNULL, env=env)
        with os.fdopen(wr, "wb", closefd=True) as out:
            wr = -1
            out.write(secret)
            out.flush()
        return process
    finally:
        os.close(rd)
        if wr >= 0:
            os.close(wr)
        for i in range(len(secret)):
            secret[i] = 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FA3 Secret Broker -> PR Watch credential projection")
    parser.add_argument("--secret-ref", default=DEFAULT_SECRET_REF)
    parser.add_argument("--broker-socket", type=Path, default=Path(DEFAULT_SOCKET))
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--operator-export-path", type=Path)
    args = parser.parse_args(argv)
    proc = None
    try:
        value = obtain_single_secret(args.secret_ref, args.broker_socket)
        proc = launch_receiver(value, bind=args.bind, port=args.port, state_dir=args.state_dir,
                               operator_export_path=args.operator_export_path)
        return proc.wait()
    except KeyboardInterrupt:
        return 130
    except (PRWatchDenied, OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        code = exc.code if isinstance(exc, PRWatchDenied) else "BROKER_OR_RECEIVER_UNAVAILABLE"
        print(json.dumps({"status": "DENIED", "code": code}), file=sys.stderr)
        return 2
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


if __name__ == "__main__":
    raise SystemExit(main())
