#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import selectors
import signal
import socket
import threading
from pathlib import Path

STOP = threading.Event()


def _copy(src: socket.socket, dst: socket.socket) -> None:
    try:
        while not STOP.is_set():
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def serve(sock_path: Path, target_host: str, target_port: int) -> int:
    if target_host not in {"127.0.0.1", "::1", "localhost"}:
        raise RuntimeError("FA3 OpenHands router bridge target must be loopback")
    if not (1 <= target_port <= 65535):
        raise RuntimeError("invalid router bridge target port")
    sock_path = sock_path.resolve()
    sock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        sock_path.unlink()
    except FileNotFoundError:
        pass
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(sock_path))
    os.chmod(sock_path, 0o600)
    listener.listen(8)
    listener.settimeout(0.5)

    def stop(*_args):
        STOP.set()
        try:
            listener.close()
        except OSError:
            pass

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        while not STOP.is_set():
            try:
                client, _ = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                upstream = socket.create_connection((target_host, target_port), timeout=10)
            except OSError:
                client.close()
                continue
            threading.Thread(target=_copy, args=(client, upstream), daemon=True).start()
            threading.Thread(target=_copy, args=(upstream, client), daemon=True).start()
    finally:
        try:
            listener.close()
        except OSError:
            pass
        try:
            sock_path.unlink()
        except FileNotFoundError:
            pass
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 OpenHands loopback LiteLLM Unix-socket bridge")
    ap.add_argument("--socket", required=True)
    ap.add_argument("--target-host", default="127.0.0.1")
    ap.add_argument("--target-port", type=int, default=4000)
    args = ap.parse_args()
    return serve(Path(args.socket), args.target_host, args.target_port)


if __name__ == "__main__":
    raise SystemExit(main())
