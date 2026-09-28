import base64
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_pr_watch import PRWatchDenied
from fa3_pr_watch_secret_runtime import (CONSUMER_ID, DEFAULT_SECRET_REF, SECRET_KIND,
                                         obtain_single_secret, launch_receiver)
from fa3_secret_broker import Broker, SecretStore

SECRET=b"reference-test-hmac-credential-only"
SOCKET=Path("/tmp/unused-fa3-broker.sock")


def broker_result(secret=SECRET, ref=DEFAULT_SECRET_REF):
    return {"ok": True,
            "metadata": {"secret_id": ref, "version": 1,
                         "classification": "MACHINE_SERVICE_SECRET",
                         "secret_kind": SECRET_KIND},
            "secret_b64": base64.b64encode(secret).decode()}


class SecretProjectionTests(unittest.TestCase):
    def test_correct_single_secret_ref_and_projection(self):
        captured=[]
        def broker(socket, payload):
            captured.append((socket, payload))
            return broker_result()
        result=obtain_single_secret(DEFAULT_SECRET_REF,SOCKET,broker)
        self.assertEqual(SECRET, bytes(result))
        self.assertEqual([("get", DEFAULT_SECRET_REF, CONSUMER_ID, "UDS_SINGLE_SECRET")],
                         [(p["op"],p["secret_id"],p["consumer_id"],p["projection"])
                          for _,p in captured])

    def test_actual_existing_secret_store_not_second_vault(self):
        with tempfile.TemporaryDirectory() as td:
            store=SecretStore(Path(td))
            stored=store.put(DEFAULT_SECRET_REF,SECRET,"MACHINE_SERVICE_SECRET",SECRET_KIND)
            self.assertEqual(1,stored["version"])
            meta,value=store.get(DEFAULT_SECRET_REF)
            result=obtain_single_secret(DEFAULT_SECRET_REF,SOCKET,
                lambda _sock,p: {"ok": True, "metadata": {
                    "secret_id":p["secret_id"],"version":meta["version"],
                    "classification":meta["classification"],"secret_kind":meta["secret_kind"]},
                    "secret_b64":base64.b64encode(value).decode()})
            self.assertEqual(SECRET,bytes(result))

    def test_denied_policy_fails_closed(self):
        with self.assertRaises(PRWatchDenied) as e:
            obtain_single_secret(DEFAULT_SECRET_REF,SOCKET,
                                 lambda *_: {"ok":False,"error":"don't echo secret"})
        self.assertEqual("BROKER_DENIED",e.exception.code)

    def test_wrong_ref_kind_or_classification_denied(self):
        for field,bad in [("secret_id","different"),("version",0),
                          ("classification","USER_SESSION_SECRET"),
                          ("secret_kind","API_TOKEN")]:
            r=broker_result()
            r["metadata"][field]=bad
            with self.subTest(field=field):
                with self.assertRaises(PRWatchDenied):
                    obtain_single_secret(DEFAULT_SECRET_REF,SOCKET,lambda *_:r)

    def test_invalid_or_oversized_secret_denied_without_echo(self):
        for value in ["not-base64??",base64.b64encode(b"a"*5000).decode(),
                      base64.b64encode(b"x").decode()]:
            r=broker_result()
            r["secret_b64"]=value
            with self.assertRaises(PRWatchDenied):
                obtain_single_secret(DEFAULT_SECRET_REF,SOCKET,lambda *_:r)

    def test_no_public_bind_even_with_valid_secret(self):
        value=bytearray(SECRET)
        with self.assertRaises(PRWatchDenied):
            launch_receiver(value,bind="0.0.0.0")
        self.assertEqual(SECRET,bytes(value))

    def test_real_fork_exec_fd_transfer_and_zeroize(self):
        with tempfile.TemporaryDirectory() as td:
            # Uses the actual receiver to ingest into a controlled local test dir.
            # Keep a live subprocess only for this test, never a persistent daemon.
            value=bytearray(SECRET)
            import subprocess, time, urllib.request, hashlib, hmac
            from fa3_pr_watch import ProjectionStore
            import socket
            # A child writing a readiness line is not a runtime-admission proof.
            # Direct Popen here tests that the credential is transmitted by FD
            # rather than an environment variable or command line.
            out=Path(td)/"stdout.log"
            receiver=ROOT/"bin/fa3-pr-watch-receiver"
            with out.open("wb") as sink:
                with patch("fa3_pr_watch_secret_runtime.subprocess.Popen", wraps=subprocess.Popen) as spawn:
                    proc=launch_receiver(value,port=0,state_dir=Path(td)/"state",
                                         receiver_entrypoint=receiver,
                                         allowed_repositories=["fa3/reference-fixture"])
                    try:
                        self.assertEqual(bytearray(b"\x00"*len(SECRET)),value)
                        argv=spawn.call_args.args[0]
                        self.assertNotIn(SECRET.decode(),str(argv))
                        env=spawn.call_args.kwargs["env"]
                        self.assertNotIn("GITHUB_TOKEN",env)
                    finally:
                        proc.terminate()
                        proc.wait(timeout=4)


if __name__=="__main__":
    unittest.main()
