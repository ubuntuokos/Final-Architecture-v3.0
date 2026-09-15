#!/usr/bin/env python3
import argparse, json, os, socketserver, threading
from datetime import datetime, timezone
from pathlib import Path

class State:
    def __init__(self, out):
        self.out = Path(out)
        self.out.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def write(self, peer, mail_from, rcpt_to, data):
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "peer": peer[0],
            "mail_from": mail_from,
            "rcpt_to": rcpt_to,
            "data": data,
        }
        with self.lock:
            with self.out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

class SMTPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.wfile.write(b"220 fa3-smtp-sink ESMTP\r\n")
        self.wfile.flush()
        mail_from = ""
        rcpt_to = []
        data_mode = False
        lines = []
        while True:
            raw = self.rfile.readline()
            if not raw:
                return
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if data_mode:
                if line == ".":
                    self.server.state.write(self.client_address, mail_from, rcpt_to, "\n".join(lines))
                    data_mode = False
                    lines = []
                    self.wfile.write(b"250 queued\r\n")
                    self.wfile.flush()
                    continue
                if line.startswith(".."):
                    line = line[1:]
                lines.append(line)
                continue

            upper = line.upper()
            if upper.startswith("EHLO") or upper.startswith("HELO"):
                self.wfile.write(b"250-fa3-smtp-sink\r\n250-8BITMIME\r\n250 SMTPUTF8\r\n")
            elif upper.startswith("MAIL FROM:"):
                mail_from = line.split(":", 1)[1].strip()
                self.wfile.write(b"250 ok\r\n")
            elif upper.startswith("RCPT TO:"):
                rcpt_to.append(line.split(":", 1)[1].strip())
                self.wfile.write(b"250 ok\r\n")
            elif upper == "DATA":
                data_mode = True
                self.wfile.write(b"354 end with <CRLF>.<CRLF>\r\n")
            elif upper == "RSET":
                mail_from = ""
                rcpt_to = []
                lines = []
                data_mode = False
                self.wfile.write(b"250 reset\r\n")
            elif upper == "NOOP":
                self.wfile.write(b"250 ok\r\n")
            elif upper == "QUIT":
                self.wfile.write(b"221 bye\r\n")
                self.wfile.flush()
                return
            else:
                self.wfile.write(b"250 ok\r\n")
            self.wfile.flush()

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=1025)
    p.add_argument("--output", default="/data/messages.jsonl")
    a = p.parse_args()
    with Server((a.host, a.port), SMTPHandler) as s:
        s.state = State(a.output)
        s.serve_forever()

if __name__ == "__main__":
    main()
