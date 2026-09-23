#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from fa3_caption_subtitle import CaptionError, build_narration_plan, export_subtitle, parse_subtitle, timing_repair, validate_document
from fa3_caption_workflows import build_audio_description_gap_plan, build_browser_overlay_projection, build_editorial_projection, build_hardsub_recovery_request, caption_quality_report, edit_cue, synchronize_document

MAX_BODY=20*1024*1024

def _html(mode:str)->str:
    narration=mode=="narration"; title="FA3 Narration Studio" if narration else "FA3 Subtitle Studio"
    extra=('''<div class="row"><label>Voice identity <input id="voice" value="FA3-VOICE-DEFAULT"></label><label>Mode <select id="nmode"><option>NARRATION</option><option>VOICE_OVER</option><option>DUBBING</option><option>AUDIO_DESCRIPTION_READY</option></select></label><button onclick="narrate()">Build narration plan</button></div>''' if narration else '''<div class="row"><label>Offset ms <input id="offset" type="number" value="0"></label><label>Drift ppm <input id="drift" type="number" value="0"></label><button onclick="syncNow()">Sync</button><button onclick="qcNow()">QC</button><button onclick="exportFmt('srt')">Export SRT</button><button onclick="exportFmt('vtt')">Export VTT</button><button onclick="exportFmt('ass')">Export ASS</button><button onclick="exportFmt('ttml')">Export TTML</button><button onclick="exportFmt('json')">Export FA3 JSON</button></div>''')
    return f'''<!doctype html><html><head><meta charset="utf-8"><title>{title}</title><style>
body{{font-family:system-ui,sans-serif;margin:0;background:#17191d;color:#e8eaf0}} header{{padding:16px 22px;background:#20242a;border-bottom:1px solid #343a44}} main{{padding:18px;display:grid;gap:14px}}
.panel{{background:#20242a;border:1px solid #343a44;border-radius:10px;padding:14px}} .row{{display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
textarea{{width:100%;min-height:250px;background:#111318;color:#e8eaf0;border:1px solid #414854;border-radius:8px;padding:10px}} pre{{white-space:pre-wrap;background:#111318;border-radius:8px;padding:10px;max-height:340px;overflow:auto}}
input,select,button{{background:#292f38;color:#e8eaf0;border:1px solid #4a5361;border-radius:7px;padding:7px 10px}} button{{cursor:pointer}} .ok{{color:#89d185}} .err{{color:#ff8a8a}}</style></head>
<body><header><b>{title}</b><div>FA3-CAPTION-SUBTITLE-001 · local-only focused workspace</div></header><main>
<div class="panel row"><input id="file" type="file"><label>Format <select id="fmt"><option>srt</option><option>vtt</option><option>ass</option><option>ssa</option><option>sbv</option><option>ttml</option><option>microdvd</option><option>mpl2</option><option>json</option></select></label><label>Language <input id="lang" value="hu-HU"></label><button onclick="parseNow()">Parse</button></div>
<div class="panel"><textarea id="src" placeholder="Drop or paste subtitle content here"></textarea></div><div class="panel"><div class="row"><b>Canonical Caption IR</b><span id="status"></span></div>{extra}<pre id="out"></pre></div></main>
<script>
let documentModel=null; const fmt=document.getElementById('fmt'),lang=document.getElementById('lang'),src=document.getElementById('src'),out=document.getElementById('out'),status=document.getElementById('status');
document.getElementById('file').addEventListener('change',async e=>{{const f=e.target.files[0];if(!f)return;src.value=await f.text();const ext=f.name.split('.').pop().toLowerCase();for(let i=0;i<fmt.options.length;i++)if(fmt.options[i].value===ext)fmt.selectedIndex=i;}});
async function api(path,payload){{const r=await fetch(path,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(payload)}});const j=await r.json();if(!r.ok)throw new Error(j.error||'request failed');return j;}}
async function parseNow(){{try{{const j=await api('/api/parse',{{format:fmt.value,language:lang.value,content:src.value}});documentModel=j.document;out.textContent=JSON.stringify(j,null,2);status.textContent='PASS';status.className='ok';}}catch(e){{status.textContent='FAIL';status.className='err';out.textContent=e.message;}}}}
async function exportFmt(format){{if(!documentModel)await parseNow();if(!documentModel)return;try{{const j=await api('/api/export',{{format,document:documentModel}});out.textContent=j.content;}}catch(e){{out.textContent=e.message;}}}}
async function syncNow(){{if(!documentModel)await parseNow();if(!documentModel)return;try{{const j=await api('/api/sync',{{document:documentModel,offset_ms:Number(document.getElementById('offset').value||0),drift_ppm:Number(document.getElementById('drift').value||0)}});documentModel=j.document;out.textContent=JSON.stringify(j,null,2);}}catch(e){{out.textContent=e.message;}}}}
async function qcNow(){{if(!documentModel)await parseNow();if(!documentModel)return;try{{const j=await api('/api/qc',{{document:documentModel}});out.textContent=JSON.stringify(j,null,2);}}catch(e){{out.textContent=e.message;}}}}
async function narrate(){{if(!documentModel)await parseNow();if(!documentModel)return;try{{const j=await api('/api/narration-plan',{{document:documentModel,voice_identity_ref:document.getElementById('voice').value,mode:document.getElementById('nmode').value}});out.textContent=JSON.stringify(j,null,2);}}catch(e){{out.textContent=e.message;}}}}
</script></body></html>'''

class Handler(BaseHTTPRequestHandler):
    server_version="FA3CaptionStudio/1.0"; mode="subtitle"
    def _send(self,code:int,body:bytes,content_type:str)->None:
        self.send_response(code); self.send_header("Content-Type",content_type); self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store"); self.send_header("X-Content-Type-Options","nosniff"); self.send_header("Content-Security-Policy","default-src 'self' 'unsafe-inline'; connect-src 'self'"); self.end_headers(); self.wfile.write(body)
    def do_GET(self)->None:
        if urlparse(self.path).path!="/": self._send(404,b"not found","text/plain; charset=utf-8"); return
        self._send(200,_html(self.mode).encode(),"text/html; charset=utf-8")
    def do_POST(self)->None:
        if self.headers.get("Content-Type","").split(";",1)[0].strip()!="application/json": self._json(415,{"error":"application/json required"}); return
        try:
            n=int(self.headers.get("Content-Length","0"))
            if n<=0 or n>MAX_BODY: raise CaptionError("invalid request size")
            payload=json.loads(self.rfile.read(n)); path=urlparse(self.path).path
            if path=="/api/parse":
                doc=parse_subtitle(payload["content"],payload["format"],language=payload.get("language","und"),fps=float(payload.get("fps",25.0))); self._json(200,{"document":doc,"validation":validate_document(doc)})
            elif path=="/api/export": self._json(200,{"content":export_subtitle(payload["document"],payload["format"])})
            elif path=="/api/edit": self._json(200,{"document":edit_cue(payload["document"],payload["cue_id"],payload["text"],actor=payload.get("actor","USER"))})
            elif path=="/api/sync": self._json(200,{"document":synchronize_document(payload["document"],offset_ms=int(payload.get("offset_ms",0)),drift_ppm=float(payload.get("drift_ppm",0.0)),actor=payload.get("actor","USER"))})
            elif path=="/api/qc": self._json(200,caption_quality_report(payload["document"]))
            elif path=="/api/editorial-projection": self._json(200,build_editorial_projection(payload["document"],payload["target"]))
            elif path=="/api/overlay-projection": self._json(200,build_browser_overlay_projection(payload["document"]))
            elif path=="/api/audio-description-plan": self._json(200,build_audio_description_gap_plan(payload["document"],int(payload["media_duration_ms"]),min_gap_ms=int(payload.get("min_gap_ms",1500))))
            elif path=="/api/hardsub-request": self._json(200,build_hardsub_recovery_request(payload["media_ref"],language=payload.get("language","und"),regions=payload.get("regions"),provider_constraints=payload.get("provider_constraints")))
            elif path=="/api/narration-plan": self._json(200,build_narration_plan(payload["document"],voice_identity_ref=payload.get("voice_identity_ref","FA3-VOICE-DEFAULT"),speaker_voice_map=payload.get("speaker_voice_map"),narration_mode=payload.get("mode","NARRATION")))
            elif path=="/api/timing-repair": self._json(200,timing_repair(int(payload["target_duration_ms"]),int(payload["actual_duration_ms"])))
            else: self._json(404,{"error":"not found"})
        except (CaptionError,KeyError,ValueError,json.JSONDecodeError) as e: self._json(400,{"error":str(e)})
    def _json(self,code:int,value:object)->None: self._send(code,(json.dumps(value,ensure_ascii=False,indent=2)+"\n").encode(),"application/json; charset=utf-8")
    def log_message(self,fmt:str,*args:object)->None: print("fa3-caption-studio:",fmt%args,file=sys.stderr)

def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=("subtitle","narration"),default="subtitle"); ap.add_argument("--port",type=int,default=0); ap.add_argument("--no-browser",action="store_true"); args=ap.parse_args(argv)
    Handler.mode=args.mode; server=ThreadingHTTPServer(("127.0.0.1",args.port),Handler); host,port=server.server_address; url=f"http://{host}:{port}/"; print(url)
    if not args.no_browser: webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0
if __name__=="__main__": raise SystemExit(main())