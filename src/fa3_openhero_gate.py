#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, json, posixpath, re
from pathlib import Path
from urllib.parse import urlsplit

PROVIDER_ID="FA3-PROVIDER-OPENHERO-001"
CONTRACT_ID="FA3-WEB-CREATIVE-ASSET-PACKAGING-DELIVERY-CONTRACTS-001"
DECISION_ID="FA3-DEC-OPENHERO-WEB-CREATIVE-ASSET-2026-09-04"
GATE_ID="FA3-GATE-WEB-CREATIVE-ASSET-001"
GATESET_ID="FA3-WEB-CREATIVE-ASSET-GATESET-001"
UPSTREAM_PIN="d599548dd09fce4aff66e076c4ab87d73e1e8a3d"
EVIDENCE_PATH="evidence/reference/openhero-web-creative-asset-ci-2026-09-04.json"
PROJECTION_PATH="canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
CAPABILITY_IDS=["CAP-003","CAP-004","CAP-011","CAP-016","CAP-019","CAP-038","CAP-047","CAP-049","CAP-103","CAP-125"]
CASE_IDS=[f"WCA-{i:03d}" for i in range(1,33)]
SHA40=re.compile(r"^[0-9a-f]{40}$"); SHA256=re.compile(r"^[0-9a-f]{64}$")

def loadj(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def writej(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def finding(c,m,**x): return {"code":c,"severity":"P0","message":m,**x}
def safe_path(s):
    if not isinstance(s,str) or not s or s.startswith("/") or "\\" in s: return False
    n=posixpath.normpath(s); return n not in (".","..") and not n.startswith("../") and "/../" not in f"/{n}/"
def origin(u):
    try: p=urlsplit(u)
    except Exception: return None
    if p.scheme!="https" or not p.hostname or p.username or p.password: return None
    try: port=p.port
    except ValueError: return None
    return None if port not in (None,443) else f"https://{p.hostname.lower()}"

def registry_paths(p):
    if p.get("request",{}).get("direct_filesystem_path") is not None: return None
    r=p.get("request",{}); key=f"{r.get('category','')}/{r.get('slug','')}"
    a=p.get("registry",{}).get("assets",{}).get(key)
    if not isinstance(a,dict): return None
    paths=(a.get("html_path"),a.get("video_path"))
    return paths if all(safe_path(x) for x in paths) else None

def asset_admission_allowed(p):
    try:
        s=p["source"]; rights=p["asset_rights"]; arc=p["archive"]; html=p["html_security"]; prev=p["preview"]
        deps=p["dependencies"]; supply=p["supply_chain"]; budget=p["resource_budget"]; qa=p["qa"]; pub=p["publication"]
        checks=[
          p.get("trust_default")=="UNTRUSTED", s.get("repository")=="CristianOlivera1/openhero", SHA40.fullmatch(s.get("commit","")) is not None,
          s.get("commit")==UPSTREAM_PIN, s.get("floating_ref_allowed") is False, s.get("auto_update") is False,
          p["code_license"].get("name")=="MIT", p["code_license"].get("snapshot_present") is True,
          rights.get("declared_per_asset") is True, bool(rights.get("license_or_rights_id")), rights.get("inherits_repository_code_license") is False,
          rights.get("source_provenance_present") is True, p.get("resolution_policy")=="REGISTRY_ONLY", registry_paths(p) is not None,
          arc.get("entry_count",999)<=8, arc.get("total_uncompressed_bytes",10**18)<=64*1024*1024, arc.get("max_compression_ratio",999)<=50,
          html.get("entrypoint")=="index.html", html.get("origin_validation")=="URL_PARSE_EXACT_ORIGIN", html.get("substring_domain_matching") is False,
          html.get("inline_script_policy") in {"DENY","HASH_OR_NONCE_ONLY"},
          prev.get("isolated_origin") is True, origin(prev.get("origin")) is not None, origin(prev.get("origin"))!=origin(prev.get("application_origin")),
          not ({"allow-scripts","allow-same-origin"}<=set(prev.get("sandbox_tokens",[]))), prev.get("csp_required") is True, bool(prev.get("csp")),
          prev.get("outbound_network_default_deny") is True, supply.get("sbom_present") is True, supply.get("scan_status")=="PASS",
          budget.get("bounded") is True, budget.get("render_timeout_seconds",0)>0, budget.get("max_download_bytes",0)>0,
          p["hardware"].get("portable") is True, p["hardware"].get("static_host_sku_required") is False,
          qa.get("accessibility")==qa.get("responsive")==qa.get("visual_regression")=="PASS",
          pub.get("content_addressed") is True, pub.get("immutable") is True, SHA256.fullmatch(pub.get("artifact_sha256","")) is not None,
          bool(pub.get("rollback_target")), pub.get("human_review")=="APPROVED", bool(pub.get("evidence_id")),
          p["runtime_claim"].get("current_host_runtime_evidence") is False, p["runtime_claim"].get("runtime_promotion_claim") is False,
        ]
        if not all(checks): return False
        for f in p["files"]:
            if not (safe_path(f.get("path")) and f.get("kind") in {"html","video","image","css","json","text"} and f.get("mime_verified") is True and f.get("magic_verified") is True and f.get("executable") is False): return False
        allow={origin(x) for x in html.get("external_script_origins",[])}-{None}
        if any(origin(x) not in allow for x in html.get("external_script_urls",[])): return False
        if html.get("inline_script_policy")=="HASH_OR_NONCE_ONLY" and html.get("inline_scripts_verified") is not True: return False
        for d in deps:
            if not (d.get("name") and d.get("version") and SHA256.fullmatch(d.get("integrity_sha256",""))): return False
        return True
    except (KeyError,TypeError,ValueError): return False

def good_package():
    key="nature/cinematic-horizons"
    return {
      "trust_default":"UNTRUSTED","source":{"repository":"CristianOlivera1/openhero","commit":UPSTREAM_PIN,"floating_ref_allowed":False,"auto_update":False},
      "code_license":{"name":"MIT","snapshot_present":True},"asset_rights":{"declared_per_asset":True,"license_or_rights_id":"OPENHERO-PER-ASSET-RIGHTS","inherits_repository_code_license":False,"source_provenance_present":True},
      "resolution_policy":"REGISTRY_ONLY","request":{"category":"nature","slug":"cinematic-horizons","direct_filesystem_path":None},
      "registry":{"assets":{key:{"html_path":"downloads/nature/cinematic-horizons/index.html","video_path":"downloads/nature/cinematic-horizons/video.mp4"}}},
      "archive":{"entry_count":2,"total_uncompressed_bytes":8*1024*1024,"max_compression_ratio":8},
      "files":[{"path":"index.html","kind":"html","mime_verified":True,"magic_verified":True,"executable":False},{"path":"video.mp4","kind":"video","mime_verified":True,"magic_verified":True,"executable":False}],
      "html_security":{"entrypoint":"index.html","origin_validation":"URL_PARSE_EXACT_ORIGIN","substring_domain_matching":False,"inline_script_policy":"HASH_OR_NONCE_ONLY","inline_scripts_verified":True,"external_script_origins":["https://cdn.jsdelivr.net"],"external_script_urls":["https://cdn.jsdelivr.net/npm/lucide@1.0.0/index.js"]},
      "preview":{"isolated_origin":True,"origin":"https://preview.invalid","application_origin":"https://app.invalid","sandbox_tokens":["allow-scripts"],"csp_required":True,"csp":"default-src 'none'; media-src https:; script-src 'sha256-x'; style-src 'unsafe-inline'","outbound_network_default_deny":True},
      "dependencies":[{"name":"lucide","version":"1.0.0","integrity_sha256":"a"*64}],"supply_chain":{"sbom_present":True,"scan_status":"PASS"},
      "resource_budget":{"bounded":True,"render_timeout_seconds":15,"max_download_bytes":64*1024*1024},"hardware":{"portable":True,"static_host_sku_required":False},
      "qa":{"accessibility":"PASS","responsive":"PASS","visual_regression":"PASS"},"publication":{"content_addressed":True,"immutable":True,"artifact_sha256":"b"*64,"rollback_target":"sha256:previous","human_review":"APPROVED","evidence_id":"EVID-WCA"},
      "runtime_claim":{"current_host_runtime_evidence":False,"runtime_promotion_claim":False}}

def mutate(base,fn): x=copy.deepcopy(base); fn(x); return x
def run_regressions():
    g=good_package(); bad=[]
    def add(fn): bad.append(mutate(g,fn))
    add(lambda x:x["source"].update(commit="main")); add(lambda x:x["source"].update(auto_update=True)); add(lambda x:x["asset_rights"].update(inherits_repository_code_license=True)); add(lambda x:x["asset_rights"].update(declared_per_asset=False))
    add(lambda x:x.update(resolution_policy="DIRECT_PATH")); add(lambda x:x["request"].update(direct_filesystem_path="/tmp/x")); add(lambda x:x["registry"]["assets"]["nature/cinematic-horizons"].update(html_path="../../etc/passwd")); add(lambda x:x["archive"].update(entry_count=999))
    add(lambda x:x["archive"].update(total_uncompressed_bytes=10**9)); add(lambda x:x["archive"].update(max_compression_ratio=1000)); add(lambda x:x["files"][0].update(mime_verified=False)); add(lambda x:x["html_security"].update(entrypoint="main.htm"))
    add(lambda x:x["files"][0].update(executable=True)); add(lambda x:x["html_security"].update(origin_validation="SUBSTRING")); add(lambda x:x["html_security"].update(external_script_urls=["https://cdn.jsdelivr.net.evil.example/x.js"])); add(lambda x:x["html_security"].update(substring_domain_matching=True))
    add(lambda x:x["html_security"].update(inline_script_policy="ALLOW_ALL")); add(lambda x:x["preview"].update(isolated_origin=False)); add(lambda x:x["preview"].update(sandbox_tokens=["allow-scripts","allow-same-origin"])); add(lambda x:x["preview"].update(csp_required=False))
    add(lambda x:x["preview"].update(outbound_network_default_deny=False)); add(lambda x:x["dependencies"][0].update(version="")); add(lambda x:x["supply_chain"].update(sbom_present=False)); add(lambda x:x["supply_chain"].update(scan_status="FAIL"))
    add(lambda x:x["resource_budget"].update(bounded=False)); add(lambda x:x["qa"].update(accessibility="FAIL")); add(lambda x:x["qa"].update(responsive="FAIL")); add(lambda x:x["qa"].update(visual_regression="FAIL"))
    add(lambda x:x["publication"].update(immutable=False)); add(lambda x:x["publication"].update(rollback_target="")); add(lambda x:x["publication"].update(human_review="PENDING")); add(lambda x:x["runtime_claim"].update(runtime_promotion_claim=True))
    oks=[asset_admission_allowed(g)]+[not asset_admission_allowed(x) for x in bad]
    cases=[{"case_id":c,"status":"PASS" if ok else "FAIL"} for c,ok in zip(CASE_IDS,oks)]
    return {"result":"PASS" if len(cases)==32 and all(x["status"]=="PASS" for x in cases) else "FAIL","total":len(cases),"passed":sum(x["status"]=="PASS" for x in cases),"case_ids_exact":[x["case_id"] for x in cases]==CASE_IDS,"cases":cases}

def canonical_check(root):
    root=Path(root); f=[]
    provider=loadj(root/"canonical/providers/FA3-PROVIDER-OPENHERO-001.json"); contract=loadj(root/"canonical/contracts/FA3-WEB-CREATIVE-ASSET-PACKAGING-DELIVERY-CONTRACTS-001.json")
    decision=loadj(root/"canonical/decisions/FA3-DEC-OPENHERO-WEB-CREATIVE-ASSET-2026-09-04.json"); evidence=loadj(root/EVIDENCE_PATH); profile=loadj(root/"canonical/profiles/FA3-MARKETING-001.json")
    marketing=loadj(root/"canonical/contracts/FA3-MARKETING-CONTRACTS-001.json"); policy=loadj(root/"canonical/enforcement-policy.json"); reg=loadj(root/"evidence/evidence-registry.json"); proj=loadj(root/PROJECTION_PATH)
    if not (provider.get("id")==PROVIDER_ID and provider.get("architectural_authority") is False and provider.get("canonical_root") is False and provider.get("new_capability") is False and provider.get("capability_count")==143 and provider.get("capabilities")==CAPABILITY_IDS and provider.get("upstream",{}).get("immutable_commit")==UPSTREAM_PIN and provider.get("runtime_activation_status")=="REFERENCE_ONLY_NOT_RUNTIME_DEPENDENCY"): f.append(finding("WCA-CANON-001","OpenHero provider boundary drift"))
    if not (contract.get("id")==CONTRACT_ID and contract.get("provider_neutral") is True and contract.get("capability_count")==143 and contract.get("rights_governance",{}).get("repository_code_license_cannot_imply_asset_rights") is True and contract.get("preview_security",{}).get("isolated_origin_required") is True): f.append(finding("WCA-CANON-002","Web creative asset contract drift"))
    if not (decision.get("id")==DECISION_ID and decision.get("upstream_pin")==UPSTREAM_PIN and decision.get("new_capabilities")==0 and decision.get("new_architectural_authorities")==0 and decision.get("current_host_runtime_claim") is False): f.append(finding("WCA-CANON-003","OpenHero decision drift"))
    if not (evidence.get("status")=="PASS" and evidence.get("regressions",{}).get("passed")==32 and evidence.get("current_host_runtime_evidence")=="NOT_CLAIMED" and evidence.get("current_host_runtime_promotion_claim") is False): f.append(finding("WCA-CANON-004","Reference evidence drift"))
    if not (CONTRACT_ID in profile.get("contracts",[]) and profile.get("providers",{}).get("web_creative_asset_library")==[PROVIDER_ID] and marketing.get("web_creative_asset_delivery",{}).get("contract_id")==CONTRACT_ID): f.append(finding("WCA-CANON-005","Marketing binding drift"))
    if not (GATESET_ID in policy.get("mandatory_reference_gates",[]) and policy.get("openhero_provider_id")==PROVIDER_ID and policy.get("openhero_capability_bindings")==CAPABILITY_IDS and policy.get("openhero_upstream_pin")==UPSTREAM_PIN): f.append(finding("WCA-CANON-006","Global policy binding drift"))
    invalid=[]
    for cap in CAPABILITY_IDS:
        r=next((x for x in reg.get("records",[]) if x.get("subject_id")==cap),{}); s=r.get("openhero_web_creative_asset_projection_status",{})
        if not (DECISION_ID in r.get("source_decision_ids",[]) and EVIDENCE_PATH in r.get("evidence_artifacts",[]) and s.get("provider_id")==PROVIDER_ID and s.get("gate_id")==GATE_ID and s.get("runtime_status")=="REFERENCE_ONLY_NOT_RUNTIME_DEPENDENCY" and s.get("code_license_media_rights_separate") is True): invalid.append(cap)
    if invalid: f.append(finding("WCA-CANON-007","Evidence Registry binding drift",capability_ids=invalid))
    rec=proj.get("openhero_web_creative_asset_reconciliation",{}); manifests={x.get("path") for x in proj.get("manifest",[])}
    required={"canonical/providers/FA3-PROVIDER-OPENHERO-001.json","canonical/contracts/FA3-WEB-CREATIVE-ASSET-PACKAGING-DELIVERY-CONTRACTS-001.json","canonical/decisions/FA3-DEC-OPENHERO-WEB-CREATIVE-ASSET-2026-09-04.json","canonical/references/FA3-OPENHERO-UPSTREAM-REFERENCE-2026-09-04.json","canonical/FA3-GATE-WEB-CREATIVE-ASSET-001.json","canonical/openhero-web-creative-asset-enforcement.json",EVIDENCE_PATH,"src/fa3_openhero_gate.py","tests/test_openhero_gate.py","src/fa3_release_projection_gate.py","src/fa3_enforce.py","evidence/evidence-registry.json"}
    if not (rec.get("provider_id")==PROVIDER_ID and rec.get("contract_id")==CONTRACT_ID and rec.get("gate_id")==GATESET_ID and rec.get("upstream_pin")==UPSTREAM_PIN and rec.get("capability_count_after")==143 and GATESET_ID in proj.get("mandatory_reference_gates",[]) and not(required-manifests)): f.append(finding("WCA-CANON-008","Release projection reconciliation drift"))
    return {"result":"PASS" if not f else "FAIL","findings":f}

def gate(root):
    c=canonical_check(root); r=run_regressions(); result="PASS" if c["result"]==r["result"]=="PASS" else "FAIL"
    out={"schema":"fa3.openhero-web-creative-asset-gate-report.v1","gate_id":GATE_ID,"gateset_id":GATESET_ID,"provider_id":PROVIDER_ID,"contract_id":CONTRACT_ID,"upstream_pin":UPSTREAM_PIN,"result":result,"canonical":c,"regressions":r,"current_host_runtime_claim":False,"production_runtime_admission":False}
    writej(Path(root)/"reports/openhero-web-creative-asset-gate-report.json",out); return out

def main():
    a=argparse.ArgumentParser(); a.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); x=gate(Path(a.parse_args().root).resolve()); print(json.dumps(x,ensure_ascii=False,indent=2)); return 0 if x["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
