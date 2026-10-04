#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,secrets,sys
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from fa3_voice_workspace import VoiceWorkspace,VoiceWorkspaceError
MAX_BODY=4*1024*1024
def token_path():
    base=Path(os.environ.get("XDG_RUNTIME_DIR","/tmp"))/"fa3"; base.mkdir(parents=True,exist_ok=True)
    p=base/"voice-studio.token"
    p.write_text(secrets.token_urlsafe(32),encoding="utf-8"); p.chmod(0o600)
    return p
class Handler(BaseHTTPRequestHandler):
    workspace=None; token=""; server_version="FA3VoiceStudio/1.0"
    def _send(self,code,obj):
        raw=(json.dumps(obj,ensure_ascii=False,indent=2)+"\n").encode(); self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(raw))); self.send_header("Cache-Control","no-store"); self.send_header("X-Content-Type-Options","nosniff"); self.end_headers(); self.wfile.write(raw)
    def _auth(self):
        if self.headers.get("Authorization")!="Bearer "+self.token: self._send(401,{"error":"unauthorized"}); return False
        return True
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/healthz": self._send(200,self.workspace.health()); return
        if not self._auth(): return
        if path=="/api/profiles": self._send(200,{"profiles":self.workspace.list_profiles()})
        elif path=="/api/jobs": self._send(200,{"jobs":self.workspace.list_jobs()})
        elif path=="/capabilities": self._send(200,{"capabilities":["voice.generate","voice.profile.list","voice.profile.put","voice.capture.register","voice.fit-to-clip","voice.quick-dub.plan"]})
        else: self._send(404,{"error":"not found"})
    def do_POST(self):
        if not self._auth(): return
        try:
            n=int(self.headers.get("Content-Length","0"))
            if n<=0 or n>MAX_BODY: raise VoiceWorkspaceError("invalid request size")
            p=json.loads(self.rfile.read(n)); path=urlparse(self.path).path
            if path=="/api/profiles": out=self.workspace.put_profile(p)
            elif path=="/api/captures": out=self.workspace.register_capture(p)
            elif path=="/api/generate": out=self.workspace.generate(p)
            elif path=="/api/fit-to-clip": out=self.workspace.fit_to_clip(int(p["target_ms"]),int(p["actual_ms"]))
            elif path=="/api/quick-dub": out=self.workspace.quick_dub_plan(p)
            else: self._send(404,{"error":"not found"}); return
            self._send(200,out)
        except (VoiceWorkspaceError,KeyError,ValueError,json.JSONDecodeError) as e: self._send(400,{"error":str(e)})
        except Exception as e: self._send(500,{"error":str(e)})
    def log_message(self,fmt,*args): print("fa3-voice-studio:",fmt%args,file=sys.stderr)
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); ap.add_argument("--port",type=int,default=18796); ap.add_argument("--state-dir"); args=ap.parse_args(argv)
    ws=VoiceWorkspace(Path(args.root),Path(args.state_dir).expanduser() if args.state_dir else None); Handler.workspace=ws; Handler.token=token_path().read_text().strip()
    server=ThreadingHTTPServer(("127.0.0.1",args.port),Handler)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: ws.close(); server.server_close()
    return 0
if __name__=="__main__": raise SystemExit(main())
