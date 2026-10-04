#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,sqlite3,time,uuid,wave
from pathlib import Path
from typing import Any
from fa3_piper_provider import execute_piper
class VoiceWorkspaceError(RuntimeError): pass
def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()
class VoiceWorkspace:
    def __init__(self,root:Path,state_dir:Path|None=None):
        self.root=root.resolve()
        default=Path(os.environ.get("XDG_STATE_HOME",str(Path.home()/".local/state")))/"fa3/voice-studio"
        self.state=(state_dir or default).resolve(); self.state.mkdir(parents=True,exist_ok=True)
        self.assets=self.state/"assets"; self.assets.mkdir(exist_ok=True)
        self.db=sqlite3.connect(self.state/"voice-studio.sqlite3"); self.db.row_factory=sqlite3.Row
        self.db.executescript("create table if not exists profiles(id text primary key,payload text not null,updated real not null); create table if not exists jobs(id text primary key,kind text not null,state text not null,payload text not null,result text,error text,created real not null,updated real not null); create table if not exists captures(id text primary key,payload text not null,created real not null);")
        self.db.commit(); self.admission=json.loads((self.root/"canonical/FA3-VOICE-PROVIDER-ADMISSION-001.json").read_text())
    def close(self): self.db.close()
    def health(self): return {"status":"ok","profile_id":"FA3-VOICE-001","capability_baseline":175,"state_dir":str(self.state),"production_provider_claim":False}
    def list_profiles(self): return [json.loads(r["payload"]) for r in self.db.execute("select payload from profiles order by updated desc")]
    def put_profile(self,p):
        pid=str(p.get("id","")).strip()
        if not pid: raise VoiceWorkspaceError("profile id required")
        if p.get("human_voice") is True and not p.get("consent_ref"): raise VoiceWorkspaceError("human voice profile requires consent_ref")
        out={**p,"schema":"fa3.voice-profile.workspace.v1","id":pid}; now=time.time()
        self.db.execute("insert or replace into profiles(id,payload,updated) values(?,?,?)",(pid,json.dumps(out,ensure_ascii=False),now)); self.db.commit(); return out
    def register_capture(self,p):
        path=Path(str(p.get("audio_path",""))).expanduser().resolve()
        if not path.is_file(): raise VoiceWorkspaceError("capture audio missing")
        cid=str(p.get("id") or "capture-"+uuid.uuid4().hex)
        out={**p,"schema":"fa3.voice-capture.v1","id":cid,"audio_path":str(path),"audio_sha256":_sha(path)}
        self.db.execute("insert into captures(id,payload,created) values(?,?,?)",(cid,json.dumps(out,ensure_ascii=False),time.time())); self.db.commit(); return out
    def fit_to_clip(self,target_ms:int,actual_ms:int,max_speedup:float=1.15):
        if target_ms<=0 or actual_ms<=0: raise VoiceWorkspaceError("positive durations required")
        if actual_ms<=target_ms: return {"decision":"ACCEPT_AND_PAD","target_ms":target_ms,"actual_ms":actual_ms,"pad_ms":target_ms-actual_ms,"text_rewrite":False}
        ratio=actual_ms/target_ms
        if ratio<=max_speedup: return {"decision":"BOUNDED_RATE_ADJUSTMENT","target_ms":target_ms,"actual_ms":actual_ms,"rate":ratio,"text_rewrite":False}
        return {"decision":"HUMAN_REVIEW_REQUIRED","target_ms":target_ms,"actual_ms":actual_ms,"options":["SUGGEST_SHORTER_SCRIPT","EXTEND_VIDEO","KEEP_ORIGINAL_TIMING"],"text_rewrite":False}
    def quick_dub_plan(self,p):
        return {"schema":"fa3.quick-dub-plan.v1","source_media_ref":p.get("source_media_ref"),"source_language":p.get("source_language"),"target_language":p.get("target_language"),"speaker_voice_map":p.get("speaker_voice_map",{}),"stages":["FA3-STT-MEDIA-001","SPEAKER_SEGMENTATION","OPTIONAL_TRANSLATION","FA3-VOICE-001","ALIGNMENT","EDITABLE_MIX"],"provider_selection_owned_by_application":False,"silent_fallback":False}
    def _route(self,req):
        lang=str(req.get("language","")).replace("_","-")
        if lang not in {"hu","hu-HU"}: raise VoiceWorkspaceError("current workspace routing materializes hu-HU only")
        mode=req.get("mode","plain"); key="voice_clone" if mode in {"voice_clone","zero_shot","cross_lingual","instruct2"} else "plain_or_preset_tts"
        candidates=self.admission["routing"]["hu-HU"][key]; requested=req.get("provider_id")
        if requested:
            if requested not in candidates: raise VoiceWorkspaceError("provider override outside Model Router candidate set")
            return requested
        return candidates[0]
    def generate(self,req):
        for k in ("text","language","voice_identity_ref","license_and_rights_ref"):
            if not str(req.get(k,"")).strip(): raise VoiceWorkspaceError(k+" required")
        rid=str(req.get("request_id") or "voice-"+uuid.uuid4().hex)
        req={**req,"request_id":rid,"schema":"fa3.voice-synthesis-request.v2","execution_mode":"OFFLINE_LOCAL","output_intent":req.get("output_intent","MEDIA_MEZZANINE")}
        provider=self._route(req); jid="job-"+uuid.uuid4().hex; now=time.time()
        self.db.execute("insert into jobs(id,kind,state,payload,created,updated) values(?,?,?,?,?,?)",(jid,"VOICE_GENERATION","RUNNING",json.dumps(req,ensure_ascii=False),now,now)); self.db.commit()
        try:
            if provider=="FA3-PROVIDER-PIPER-001":
                if req.get("candidate_execution_ack") is not True: raise VoiceWorkspaceError("Piper is candidate-only; explicit candidate_execution_ack required")
                result=execute_piper({**req,"mode":req.get("mode","plain"),"device":"cpu"},self.assets/(jid+".wav"))
            else: raise VoiceWorkspaceError(provider+" has no admitted workspace executor on this host")
            if req.get("target_duration_ms"):
                with wave.open(result["audio_path"],"rb") as w: actual=round(w.getnframes()*1000/w.getframerate())
                result["fit_to_clip"]=self.fit_to_clip(int(req["target_duration_ms"]),actual)
            result["timeline_handoff"]={"schema":"fa3.quickclip-voice-handoff.v1","audio_ref":result["audio_path"],"audio_sha256":result["audio_sha256"],"caption_source_text":req["text"],"editable":True,"music_ducking_requested":bool(req.get("music_ducking"))}
            self.db.execute("update jobs set state='COMPLETED',result=?,updated=? where id=?",(json.dumps(result,ensure_ascii=False),time.time(),jid)); self.db.commit(); return {"job_id":jid,"state":"COMPLETED","result":result}
        except Exception as e:
            self.db.execute("update jobs set state='FAILED',error=?,updated=? where id=?",(str(e),time.time(),jid)); self.db.commit(); raise
    def list_jobs(self):
        return [{"id":r["id"],"kind":r["kind"],"state":r["state"],"payload":json.loads(r["payload"]),"result":json.loads(r["result"]) if r["result"] else None,"error":r["error"]} for r in self.db.execute("select * from jobs order by created desc limit 100")]
