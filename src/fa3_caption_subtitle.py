#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, html, json, re, uuid
import xml.etree.ElementTree as ET
from typing import Any

SCHEMA="fa3.caption-document.v1"
VOICE_REQUEST_SCHEMA="fa3.voice-synthesis-request.v2"

class CaptionError(ValueError): pass

_TIME_RE=re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})[,.](\d{1,3})$")

def _ms(value:str)->int:
    m=_TIME_RE.match(value.strip())
    if not m: raise CaptionError(f"invalid timestamp: {value}")
    h=int(m.group(1) or 0); minute=int(m.group(2)); sec=int(m.group(3)); frac=m.group(4).ljust(3,"0")[:3]
    return ((h*60+minute)*60+sec)*1000+int(frac)

def _fmt(ms:int,sep:str=",")->str:
    if ms<0: raise CaptionError("negative timestamp")
    h,rem=divmod(ms,3600000); m,rem=divmod(rem,60000); s,milli=divmod(rem,1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{milli:03d}"

def _fmt_sbv(ms:int)->str:
    h,rem=divmod(ms,3600000); m,rem=divmod(rem,60000); s,milli=divmod(rem,1000)
    return f"{h}:{m:02d}:{s:02d}.{milli:03d}"

def _ass_time(ms:int)->str:
    h,rem=divmod(ms,3600000); m,rem=divmod(rem,60000); s,milli=divmod(rem,1000); cs=int(round(milli/10.0))
    if cs==100: s+=1; cs=0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def _cue(start:int,end:int,text:str,idx:int,**extra:Any)->dict[str,Any]:
    out={"id":f"cue-{idx:06d}","start_ms":int(start),"end_ms":int(end),"text":text.strip()}
    out.update({k:v for k,v in extra.items() if v not in (None,"",[])})
    return out

def new_document(cues:list[dict[str,Any]],*,language:str="und",source_format:str="MANUAL",provenance:dict[str,Any]|None=None,overlap_policy:str="REJECT")->dict[str,Any]:
    doc={"schema":SCHEMA,"revision":1,"timebase":{"kind":"milliseconds","units_per_second":1000},
         "tracks":[{"id":"caption-track-1","language":language,"overlap_policy":overlap_policy,"cues":sorted(cues,key=lambda x:(x["start_ms"],x["end_ms"],x["id"]))}],
         "provenance":{"source_format":source_format,"source_kind":"IMPORTED_OR_MANUAL",**(provenance or {})}}
    validate_document(doc); return doc

def parse_srt(text:str,*,language:str="und")->dict[str,Any]:
    cues=[]
    for block in re.split(r"\r?\n\s*\r?\n",text.strip()):
        lines=block.replace("\r","").split("\n")
        if lines and re.fullmatch(r"\d+",lines[0].strip()): lines=lines[1:]
        if not lines or "-->" not in lines[0]: continue
        left,right=[x.strip().split()[0] for x in lines[0].split("-->",1)]
        cues.append(_cue(_ms(left),_ms(right),"\n".join(lines[1:]),len(cues)+1))
    return new_document(cues,language=language,source_format="SRT")

def parse_vtt(text:str,*,language:str="und")->dict[str,Any]:
    raw=text.replace("\r","")
    if raw.lstrip().startswith("WEBVTT"): raw=raw.lstrip()[6:].lstrip("\n")
    cues=[]
    for block in re.split(r"\n\s*\n",raw.strip()):
        lines=block.split("\n")
        if not lines or lines[0].startswith(("NOTE","STYLE","REGION")): continue
        ti=0 if "-->" in lines[0] else (1 if len(lines)>1 and "-->" in lines[1] else -1)
        if ti<0: continue
        left=lines[ti].split("-->",1)[0].strip().split()[0]; right=lines[ti].split("-->",1)[1].strip().split()[0]
        cues.append(_cue(_ms(left),_ms(right),"\n".join(lines[ti+1:]),len(cues)+1,source_cue_id=lines[0].strip() if ti==1 else None))
    return new_document(cues,language=language,source_format="WebVTT")

def parse_sbv(text:str,*,language:str="und")->dict[str,Any]:
    cues=[]
    for block in re.split(r"\r?\n\s*\r?\n",text.strip()):
        lines=block.replace("\r","").split("\n")
        if not lines or "," not in lines[0]: continue
        a,b=[x.strip() for x in lines[0].split(",",1)]
        cues.append(_cue(_ms(a),_ms(b),"\n".join(lines[1:]),len(cues)+1))
    return new_document(cues,language=language,source_format="SBV")

def parse_ass(text:str,*,language:str="und",source_format:str="ASS")->dict[str,Any]:
    in_events=False; fields=["Layer","Start","End","Style","Name","MarginL","MarginR","MarginV","Effect","Text"]; cues=[]
    for raw in text.replace("\r","").split("\n"):
        line=raw.strip()
        if line.startswith("["): in_events=line.lower()=="[events]"; continue
        if not in_events: continue
        if line.lower().startswith("format:"): fields=[x.strip() for x in line.split(":",1)[1].split(",")]; continue
        if not line.lower().startswith("dialogue:"): continue
        values=line.split(":",1)[1].lstrip().split(",",len(fields)-1); data=dict(zip(fields,values))
        start=_ms(data.get("Start","0:00:00.00").replace(".",",")); end=_ms(data.get("End","0:00:00.00").replace(".",","))
        txt=data.get("Text","").replace("\\N","\n").replace("\\n","\n"); txt=re.sub(r"\{[^}]*\}","",txt)
        cues.append(_cue(start,end,txt,len(cues)+1,style=data.get("Style"),speaker=data.get("Name")))
    return new_document(cues,language=language,source_format=source_format)

def _ms_ttml(v:str)->int:
    v=v.strip()
    if v.endswith("ms"): return int(float(v[:-2]))
    if v.endswith("s") and ":" not in v: return int(float(v[:-1])*1000)
    if re.match(r"^\d+:\d{2}:\d{2}(?:\.\d+)?$",v):
        h,m,sec=v.split(":"); return int((int(h)*3600+int(m)*60+float(sec))*1000)
    return _ms(v.replace(".",","))

def parse_ttml(text:str,*,language:str="und")->dict[str,Any]:
    root=ET.fromstring(text); cues=[]
    for elem in root.iter():
        if elem.tag.rsplit("}",1)[-1]!="p": continue
        begin=elem.attrib.get("begin"); end=elem.attrib.get("end"); dur=elem.attrib.get("dur")
        if not begin: continue
        start=_ms_ttml(begin); finish=_ms_ttml(end) if end else start+_ms_ttml(dur or "0:00:00.001")
        cues.append(_cue(start,finish,"".join(elem.itertext()).strip(),len(cues)+1))
    return new_document(cues,language=language,source_format="TTML")

def parse_microdvd(text:str,*,language:str="und",fps:float=25.0)->dict[str,Any]:
    if fps<=0: raise CaptionError("fps must be positive")
    cues=[]; rx=re.compile(r"^\{(\d+)\}\{(\d+)\}(.*)$")
    for line in text.replace("\r","").split("\n"):
        m=rx.match(line)
        if m: cues.append(_cue(round(int(m.group(1))*1000/fps),round(int(m.group(2))*1000/fps),m.group(3).replace("|","\n"),len(cues)+1))
    return new_document(cues,language=language,source_format="MicroDVD",provenance={"fps":fps})

def parse_mpl2(text:str,*,language:str="und")->dict[str,Any]:
    cues=[]; rx=re.compile(r"^\[(\d+)\]\[(\d+)\](.*)$")
    for line in text.replace("\r","").split("\n"):
        m=rx.match(line)
        if m: cues.append(_cue(int(m.group(1))*100,int(m.group(2))*100,m.group(3).replace("|","\n"),len(cues)+1))
    return new_document(cues,language=language,source_format="MPL2")

def parse_subtitle(text:str,fmt:str,*,language:str="und",fps:float=25.0)->dict[str,Any]:
    key=fmt.strip().lower().lstrip(".")
    if key in ("json","fa3","fa3json"):
        doc=json.loads(text); validate_document(doc); return doc
    if key=="srt": return parse_srt(text,language=language)
    if key in ("vtt","webvtt"): return parse_vtt(text,language=language)
    if key=="sbv": return parse_sbv(text,language=language)
    if key in ("ass","ssa"): return parse_ass(text,language=language,source_format=key.upper())
    if key in ("ttml","dfxp","xml"): return parse_ttml(text,language=language)
    if key in ("sub","microdvd"): return parse_microdvd(text,language=language,fps=fps)
    if key=="mpl2": return parse_mpl2(text,language=language)
    raise CaptionError(f"unsupported subtitle format: {fmt}")

def validate_document(doc:dict[str,Any])->dict[str,Any]:
    if doc.get("schema")!=SCHEMA: raise CaptionError("invalid caption document schema")
    if not isinstance(doc.get("revision"),int) or doc["revision"]<1: raise CaptionError("invalid revision")
    tb=doc.get("timebase",{})
    if tb.get("kind")!="milliseconds" or tb.get("units_per_second")!=1000: raise CaptionError("unsupported or implicit timebase")
    tracks=doc.get("tracks")
    if not isinstance(tracks,list) or not tracks: raise CaptionError("at least one caption track is required")
    cue_count=0
    for track in tracks:
        policy=track.get("overlap_policy","REJECT"); last_end=-1; seen=set()
        for cue in sorted(track.get("cues",[]),key=lambda c:(c.get("start_ms",-1),c.get("end_ms",-1))):
            cid=cue.get("id")
            if not cid or cid in seen: raise CaptionError("cue ids must be stable and unique per track")
            seen.add(cid); start,end=cue.get("start_ms"),cue.get("end_ms")
            if not isinstance(start,int) or not isinstance(end,int) or start<0 or end<=start: raise CaptionError(f"invalid cue timing: {cid}")
            if policy=="REJECT" and start<last_end: raise CaptionError(f"overlapping cues rejected: {cid}")
            last_end=max(last_end,end)
            if not isinstance(cue.get("text"),str): raise CaptionError(f"cue text missing: {cid}")
            for word in cue.get("words",[]):
                if word["start_ms"]<start or word["end_ms"]>end or word["end_ms"]<=word["start_ms"]: raise CaptionError(f"word timing outside cue: {cid}")
            cue_count+=1
    return {"status":"PASS","tracks":len(tracks),"cues":cue_count,"digest":document_sha256(doc)}

def document_sha256(doc:dict[str,Any])->str:
    return hashlib.sha256(json.dumps(doc,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def revise_document(doc:dict[str,Any],*,operation:str,actor:str="USER")->dict[str,Any]:
    validate_document(doc); out=copy.deepcopy(doc); parent=document_sha256(doc); out["revision"]+=1
    out.setdefault("provenance",{})["parent_revision_sha256"]=parent; out["provenance"]["last_operation"]=operation; out["provenance"]["last_actor"]=actor
    return out

def shift_document(doc:dict[str,Any],offset_ms:int)->dict[str,Any]:
    out=revise_document(doc,operation=f"SHIFT:{offset_ms}ms")
    for track in out["tracks"]:
        for cue in track["cues"]:
            cue["start_ms"]+=offset_ms; cue["end_ms"]+=offset_ms
            if cue["start_ms"]<0: raise CaptionError("shift would create negative caption time")
            for word in cue.get("words",[]): word["start_ms"]+=offset_ms; word["end_ms"]+=offset_ms
    validate_document(out); return out

def export_subtitle(doc:dict[str,Any],fmt:str)->str:
    validate_document(doc); key=fmt.strip().lower().lstrip("."); cues=doc["tracks"][0]["cues"]
    if key in ("json","fa3","fa3json"): return json.dumps(doc,ensure_ascii=False,indent=2)+"\n"
    if key=="srt": return "\n\n".join(f"{i}\n{_fmt(c['start_ms'])} --> {_fmt(c['end_ms'])}\n{c['text']}" for i,c in enumerate(cues,1))+"\n"
    if key in ("vtt","webvtt"): return "WEBVTT\n\n"+"\n\n".join(f"{_fmt(c['start_ms'],'.')} --> {_fmt(c['end_ms'],'.')}\n{c['text']}" for c in cues)+"\n"
    if key=="sbv": return "\n\n".join(f"{_fmt_sbv(c['start_ms'])},{_fmt_sbv(c['end_ms'])}\n{c['text']}" for c in cues)+"\n"
    if key in ("ass","ssa"):
        header="[Script Info]\nScriptType: v4.00+\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Default,Arial,42,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,1,2,20,20,20,1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
        lines=[]
        for c in cues:
            txt=c["text"].replace("\n","\\N")
            lines.append(f"Dialogue: 0,{_ass_time(c['start_ms'])},{_ass_time(c['end_ms'])},{c.get('style','Default')},{c.get('speaker','')},0,0,0,,{txt}")
        return header+"\n".join(lines)+"\n"
    if key in ("ttml","dfxp","xml"):
        body="".join(f'<p begin="{_fmt(c["start_ms"],".")}" end="{_fmt(c["end_ms"],".")}">{html.escape(c["text"])}</p>' for c in cues)
        return f'<?xml version="1.0" encoding="UTF-8"?><tt xmlns="http://www.w3.org/ns/ttml"><body><div>{body}</div></body></tt>\n'
    raise CaptionError(f"unsupported export format: {fmt}")

def build_narration_plan(doc:dict[str,Any],*,language:str|None=None,voice_identity_ref:str="FA3-VOICE-DEFAULT",speaker_voice_map:dict[str,str]|None=None,narration_mode:str="NARRATION")->dict[str,Any]:
    validate_document(doc)
    if narration_mode not in {"NARRATION","VOICE_OVER","DUBBING","AUDIO_DESCRIPTION_READY"}: raise CaptionError("unsupported narration mode")
    speaker_voice_map=speaker_voice_map or {}; segments=[]
    for track in doc["tracks"]:
        lang=language or track.get("language","und")
        for cue in track["cues"]:
            speaker=cue.get("speaker","narrator"); voice=speaker_voice_map.get(speaker,voice_identity_ref); request_id=f"caption-{cue['id']}-{uuid.uuid4().hex[:12]}"
            req={"schema":VOICE_REQUEST_SCHEMA,"request_id":request_id,"text":cue["text"],"language":lang,"mode":"preset_voice","voice_identity_ref":voice,"execution_mode":"OFFLINE_LOCAL","output_intent":"MEDIA_MEZZANINE"}
            segments.append({"cue_id":cue["id"],"speaker":speaker,"target_start_ms":cue["start_ms"],"target_end_ms":cue["end_ms"],"target_duration_ms":cue["end_ms"]-cue["start_ms"],"source_text_sha256":hashlib.sha256(cue["text"].encode()).hexdigest(),"voice_request":req})
    return {"schema":"fa3.narration-plan.v1","caption_document_sha256":document_sha256(doc),"mode":narration_mode,"voice_authority":"FA3-VOICE-001","provider_selection_owned_by_application":False,"silent_text_rewrite_for_timing":False,"segments":segments}

def timing_repair(target_duration_ms:int,actual_duration_ms:int,*,max_speedup:float=1.15)->dict[str,Any]:
    if target_duration_ms<=0 or actual_duration_ms<=0: raise CaptionError("durations must be positive")
    if actual_duration_ms<=target_duration_ms:
        return {"schema":"fa3.narration-timing-receipt.v1","decision":"ACCEPT_AND_PAD_IF_NEEDED","target_duration_ms":target_duration_ms,"actual_duration_ms":actual_duration_ms,"pad_ms":target_duration_ms-actual_duration_ms,"text_rewrite":False}
    speed=actual_duration_ms/target_duration_ms
    if speed<=max_speedup:
        return {"schema":"fa3.narration-timing-receipt.v1","decision":"BOUNDED_RATE_ADJUSTMENT","target_duration_ms":target_duration_ms,"actual_duration_ms":actual_duration_ms,"speed_factor":round(speed,6),"max_speedup":max_speedup,"text_rewrite":False}
    return {"schema":"fa3.narration-timing-receipt.v1","decision":"HUMAN_REVIEW_TEXT_ADAPTATION_REQUIRED","target_duration_ms":target_duration_ms,"actual_duration_ms":actual_duration_ms,"required_speed_factor":round(speed,6),"max_speedup":max_speedup,"text_rewrite":False}

def build_dubbing_mix_plan(narration_plan:dict[str,Any],audio_results:dict[str,dict[str,Any]],*,original_dialogue_policy:str="REPLACE_DIALOGUE_KEEP_BACKGROUND")->dict[str,Any]:
    segments=[]
    for seg in narration_plan.get("segments",[]):
        req_id=seg["voice_request"]["request_id"]
        if req_id not in audio_results: raise CaptionError(f"missing voice result: {req_id}")
        result=audio_results[req_id]
        if not result.get("audio_sha256"): raise CaptionError(f"voice result missing digest: {req_id}")
        segments.append({"cue_id":seg["cue_id"],"start_ms":seg["target_start_ms"],"end_ms":seg["target_end_ms"],"audio_sha256":result["audio_sha256"],"audio_path":result.get("audio_path"),"synthetic_disclosure":result.get("synthetic_disclosure",True)})
    return {"schema":"fa3.dubbing-mix-plan.v1","source_narration_plan":narration_plan.get("caption_document_sha256"),"original_dialogue_policy":original_dialogue_policy,"background_audio_authority":"EXISTING_FA3_AUDIO_MEDIA_FABRICS","segments":segments}
