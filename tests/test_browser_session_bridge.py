from __future__ import annotations
import json
import os
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path

from fa3_browser_session_bridge import (
    BrowserSessionBridgeServer,
    EXPECTED_EXTENSION_ID,
    PROTOCOL,
    validate_native_host_manifest,
)


class BrowserSessionBridgeTests(unittest.TestCase):
    def test_real_unix_socket_handshake_and_request_response(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"run"/"fa3"/"browser-session"
            root.mkdir(parents=True,mode=0o700)
            os.chmod(root,0o700)
            bridge=BrowserSessionBridgeServer(root,timeout=2)
            bridge.start()

            def fake_native():
                sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
                sock.connect(str(bridge.socket_path))
                def send(obj):
                    sock.sendall((json.dumps(obj,separators=(",",":"))+"\n").encode())
                send({"type":"native-host-ready","protocol":PROTOCOL,"pid":12345,"authority":False})
                send({"type":"hello","protocol":PROTOCOL,"extension_id":EXPECTED_EXTENSION_ID,"expected_extension_id":EXPECTED_EXTENSION_ID,"authority":False})
                buf=bytearray()
                while True:
                    block=sock.recv(65536)
                    if not block:
                        break
                    buf.extend(block)
                    if b"\n" not in buf:
                        continue
                    raw,_,rest=buf.partition(b"\n")
                    buf=bytearray(rest)
                    req=json.loads(raw)
                    self.assertEqual("request",req["type"])
                    self.assertEqual("ping",req["method"])
                    send({"type":"response","reply_to":req["request_id"],"ok":True,"result":{"status":"PONG","protocol":PROTOCOL,"extension_id":EXPECTED_EXTENSION_ID}})
                    break
                sock.close()

            th=threading.Thread(target=fake_native,daemon=True)
            th.start()
            bridge.accept()
            result=bridge.request("ping",{})
            self.assertEqual("PONG",result["status"])
            self.assertEqual(EXPECTED_EXTENSION_ID,result["extension_id"])
            th.join(timeout=2)
            bridge.close()
            self.assertFalse(bridge.socket_path.exists())

    def test_native_manifest_is_exact_origin_and_path_bound(self):
        executable=Path("/tmp/fa3-browser-session-native-host.py")
        good={
            "name":"org.fa3.browser.session_bridge",
            "description":"x",
            "path":str(executable.resolve()),
            "type":"stdio",
            "allowed_origins":[f"chrome-extension://{EXPECTED_EXTENSION_ID}/"],
        }
        self.assertEqual([],validate_native_host_manifest(good,executable_path=executable))
        bad=dict(good)
        bad["allowed_origins"]=["chrome-extension://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/"]
        self.assertIn("NATIVE_HOST_ORIGIN_INVALID",validate_native_host_manifest(bad,executable_path=executable))


if __name__=="__main__":
    unittest.main()
