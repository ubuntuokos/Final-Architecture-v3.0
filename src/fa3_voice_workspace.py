#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,sqlite3,time,uuid,wave
from pathlib import Path
from typing import Any,Protocol
from fa3_piper_provider import execute_piper
from fa3_whisper_stt_provider import execute_transcription,RuntimeOptions
from fa3_voice_synthesis_gate import validate_transformation_request
class VoiceWorkspaceError(RuntimeError): pass
class VoiceProviderAdapter(Protocol):
    provider_id:str
    def execute(self,request:dict[str,Any],output:Path)->dict[str,Any]: ...
class PiperAdapter:
    provider_id="FA3-PROVIDER-PIPER-001"
    def execute(self,request:dict[str,Any],output:Path)->dict[str,Any]: return execute_piper(request,output)

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
        self.db.commit(); self.admission=json.loads((self.root/"canonical/FA3-VOICE-PROVIDER-ADMISSION-001.json").read_text()); self.adapters={"FA3-PROVIDER-PIPER-001":PiperAdapter()}
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
    def effects_plan(self,p):
        source=str(p.get("source_audio_ref","")).strip()
        chain=p.get("chain")
        if not source or not isinstance(chain,list): raise VoiceWorkspaceError("source_audio_ref and chain required")
        allowed={"pitch","eq","compression","reverb","delay","chorus","gain","highpass","lowpass"}
        for step in chain:
            if not isinstance(step,dict) or str(step.get("effect","")).lower() not in allowed: raise VoiceWorkspaceError("unsupported effect")
        return {"schema":"fa3.voice-effects-plan.v1","source_audio_ref":source,"chain":chain,"non_destructive":True,"original_overwrite":False,"execution_authority":"FA3-AUDIO-001","runtime_status":"PENDING_ADMITTED_AUDIO_PROCESSOR"}
    def transform_preflight(self,p):
        return validate_transformation_request(p,rights_admitted=bool(p.get("rights_admitted")),provider_status=str(p.get("provider_status") or "REFERENCE_ONLY"),provider_reference_only=bool(p.get("provider_reference_only",True)),resource_admission_ref=p.get("resource_admission_ref"))
    def transcribe(self,p):
        path=Path(str(p.get("audio_path",""))).expanduser().resolve()
        if not path.is_file(): raise VoiceWorkspaceError("audio_path missing")
        req={"schema":"fa3.stt-media-request.v1","required_result_schema":"fa3.stt-media-result.v1","time_origin":"RELATIVE_ZERO","task":"transcribe","audio_path":str(path),"audio_hash":_sha(path),"language":str(p.get("language") or "auto")}
        options=RuntimeOptions(model=str(p.get("model") or "turbo"),device="cpu",offline=True,model_cache=os.environ.get("FA3_WHISPER_MODEL_CACHE"),word_timestamps=True)
        return execute_transcription(self.root,req,options)
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
        if req.get("candidate_execution_ack") is True and key=="plain_or_preset_tts" and "FA3-PROVIDER-PIPER-001" in candidates:
            return "FA3-PROVIDER-PIPER-001"
        return candidates[0]
    def generate(self,req):
        for k in ("text","language","voice_identity_ref","license_and_rights_ref"):
            if not str(req.get(k,"")).strip(): raise VoiceWorkspaceError(k+" required")
        rid=str(req.get("request_id") or "voice-"+uuid.uuid4().hex)
        req={**req,"request_id":rid,"schema":"fa3.voice-synthesis-request.v2","execution_mode":"OFFLINE_LOCAL","output_intent":req.get("output_intent","MEDIA_MEZZANINE")}
        provider=self._route(req); jid="job-"+uuid.uuid4().hex; now=time.time()
        self.db.execute("insert into jobs(id,kind,state,payload,created,updated) values(?,?,?,?,?,?)",(jid,"VOICE_GENERATION","RUNNING",json.dumps(req,ensure_ascii=False),now,now)); self.db.commit()
        try:
            adapter=self.adapters.get(provider)
            if adapter is None: raise VoiceWorkspaceError(provider+" has no admitted workspace executor on this host")
            if provider=="FA3-PROVIDER-PIPER-001" and req.get("candidate_execution_ack") is not True: raise VoiceWorkspaceError("Piper is candidate-only; explicit candidate_execution_ack required")
            result=adapter.execute({**req,"mode":req.get("mode","plain"),"device":"cpu"},self.assets/(jid+".wav"))
            if req.get("target_duration_ms"):
                with wave.open(result["audio_path"],"rb") as w: actual=round(w.getnframes()*1000/w.getframerate())
                result["fit_to_clip"]=self.fit_to_clip(int(req["target_duration_ms"]),actual)
            result["timeline_handoff"]={"schema":"fa3.quickclip-voice-handoff.v1","audio_ref":result["audio_path"],"audio_sha256":result["audio_sha256"],"caption_source_text":req["text"],"editable":True,"music_ducking_requested":bool(req.get("music_ducking"))}
            self.db.execute("update jobs set state='COMPLETED',result=?,updated=? where id=?",(json.dumps(result,ensure_ascii=False),time.time(),jid)); self.db.commit(); return {"job_id":jid,"state":"COMPLETED","result":result}
        except Exception as e:
            self.db.execute("update jobs set state='FAILED',error=?,updated=? where id=?",(str(e),time.time(),jid)); self.db.commit(); raise
    def dispatch_action(self,action:str,payload:dict):
        allowed={"voice.speak","voice.transcribe","voice.transform.preflight","voice.effects.plan","voice.profile.put","voice.fit-to-clip","voice.quick-dub.plan"}
        if action not in allowed: raise VoiceWorkspaceError("unsupported UAF voice action")
        if action=="voice.speak": return self.generate(payload)
        if action=="voice.transcribe": return self.transcribe(payload)
        if action=="voice.transform.preflight": return self.transform_preflight(payload)
        if action=="voice.effects.plan": return self.effects_plan(payload)
        if action=="voice.profile.put": return self.put_profile(payload)
        if action=="voice.fit-to-clip": return self.fit_to_clip(int(payload["target_ms"]),int(payload["actual_ms"]))
        return self.quick_dub_plan(payload)
    def list_jobs(self):
        return [{"id":r["id"],"kind":r["kind"],"state":r["state"],"payload":json.loads(r["payload"]),"result":json.loads(r["result"]) if r["result"] else None,"error":r["error"]} for r in self.db.execute("select * from jobs order by created desc limit 100")]
