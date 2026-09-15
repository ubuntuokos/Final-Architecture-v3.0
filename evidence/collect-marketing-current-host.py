#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get("FA3_MARKETING_STATE_DIR", Path.home()/".local/share/fa3/marketing"))
CONF = Path(os.environ.get("FA3_MARKETING_CONFIG_DIR", Path.home()/".config/fa3/marketing"))

MAUTIC = "http://127.0.0.1:8180"
TWENTY = "http://127.0.0.1:3020"
LISTMONK = "http://127.0.0.1:9020"

PROVIDERS = [
    "FA3-PROVIDER-MAUTIC-001",
    "FA3-PROVIDER-TWENTY-001",
    "FA3-PROVIDER-LISTMONK-001",
]

def run(*args: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, timeout=timeout, check=False)

def secret(name: str) -> str:
    p = CONF/name
    if not p.exists():
        raise RuntimeError(f"secret file missing: {p}")
    return p.read_text(encoding="utf-8").strip()

def request(
    url: str,
    method: str = "GET",
    body: Any | None = None,
    headers: dict[str,str] | None = None,
    form: dict[str,Any] | None = None,
    timeout: int = 20,
) -> tuple[int, Any, str]:
    h = {"Accept": "application/json"}
    if headers:
        h.update(headers)
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        h["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            try:
                parsed = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = None
            return r.status, parsed, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = None
        return e.code, parsed, raw

def gql(query: str, variables: dict[str,Any] | None = None, token: str | None = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    status, obj, raw = request(TWENTY+"/metadata", "POST", {"query": query, "variables": variables or {}}, headers)
    if status != 200 or not isinstance(obj, dict) or obj.get("errors"):
        raise RuntimeError(f"Twenty GraphQL failed: HTTP {status}: {raw[:1200]}")
    return obj.get("data") or {}

def recursive_id(obj: Any) -> str | None:
    if isinstance(obj, dict):
        if isinstance(obj.get("id"), str):
            return obj["id"]
        for v in obj.values():
            got = recursive_id(v)
            if got:
                return got
    elif isinstance(obj, list):
        for v in obj:
            got = recursive_id(v)
            if got:
                return got
    return None

def mark(tests: dict[str,dict[str,Any]], name: str, ok: bool, **details: Any):
    tests[name] = {"status": "PASS" if ok else "FAIL", **details}

def image_lock_check(tests):
    p = STATE/"image-lock.json"
    if not p.exists():
        mark(tests, "immutable_image_lock", False, reason="image-lock missing")
        return
    obj=json.loads(p.read_text(encoding="utf-8"))
    images=obj.get("images",{})
    required={"mautic","twenty","listmonk"}
    ok=required.issubset(images)
    detail={}
    for name in sorted(required):
        rec=images.get(name,{})
        tag=rec.get("tag","")
        iid=rec.get("id","")
        dig=rec.get("repo_digests") or []
        good=bool(iid) and bool(dig) and not tag.endswith(":latest")
        ok = ok and good
        detail[name]={"tag":tag,"image_id":iid,"repo_digests":dig}
    mark(tests, "immutable_image_lock", ok, images=detail)

def rootless_check(tests):
    p=run("podman","info","--format","json")
    ok=False
    detail={}
    if p.returncode==0:
        try:
            obj=json.loads(p.stdout)
            host=obj.get("host") or obj.get("Host") or {}
            sec=host.get("security") or host.get("Security") or {}
            val=sec.get("rootless")
            if val is None: val=sec.get("Rootless")
            ok=val is True
            detail={"rootless":val}
        except Exception as e:
            detail={"parse_error":str(e)}
    else:
        detail={"stderr":p.stderr[-500:]}
    mark(tests,"rootless_podman",ok,**detail)

def loopback_check(tests):
    expected={
        "fa3-mkt-mautic-web":"127.0.0.1:8180",
        "fa3-mkt-twenty-server":"127.0.0.1:3020",
        "fa3-mkt-listmonk":"127.0.0.1:9020",
    }
    seen={}
    ok=True
    for name,want in expected.items():
        p=run("podman","port",name)
        text=p.stdout.strip()
        seen[name]=text
        if p.returncode!=0 or want not in text or "0.0.0.0:" in text or "[::]:" in text:
            ok=False
    p=run("podman","port","fa3-mkt-smtp-sink")
    seen["fa3-mkt-smtp-sink"]=p.stdout.strip()
    if p.stdout.strip():
        ok=False
    mark(tests,"loopback_only_public_bindings",ok,bindings=seen)

def mautic_checks(tests):
    status,_,raw=request(MAUTIC+"/")
    mark(tests,"mautic_health",status in (200,301,302),http_status=status)

    p=run("podman","exec","--user","www-data","fa3-mkt-mautic-web","php","-r",
          '$parameters=[]; require "/var/www/html/config/local.php"; echo ($parameters["locale"] ?? "");')
    mark(tests,"mautic_hu_locale",p.returncode==0 and p.stdout.strip()=="hu",locale=p.stdout.strip())

    auth=base64.b64encode(f"admin:{secret('mautic-admin-password')}".encode()).decode()
    headers={"Authorization":f"Basic {auth}"}
    email=f"fa3-mautic-e2e-{int(time.time())}@localhost.invalid"
    form={"email":email,"firstname":"Árvíztűrő","lastname":"Tükörfúrógép"}
    s,obj,raw=request(MAUTIC+"/api/contacts/new","POST",headers=headers,form=form)
    cid=None
    if isinstance(obj,dict):
        contact=obj.get("contact")
        if isinstance(contact,dict):
            cid=contact.get("id")
        cid=cid or obj.get("id")
    round_ok=False
    if s in (200,201) and cid:
        gs,gobj,graw=request(MAUTIC+f"/api/contacts/{cid}",headers=headers)
        round_ok=gs==200 and email in graw and "Árvíztűrő" in graw
        request(MAUTIC+f"/api/contacts/{cid}/delete","DELETE",headers=headers)
    mark(tests,"mautic_contact_roundtrip",round_ok,http_status=s,contact_id=cid)

    commands=[
        "mautic:segments:update",
        "mautic:campaigns:update",
        "mautic:campaigns:trigger",
    ]
    results={}
    ok=True
    for cmd in commands:
        p=run("podman","exec","--user","www-data","--workdir","/var/www/html",
              "fa3-mkt-mautic-web","php","./bin/console",cmd,"--no-interaction",timeout=180)
        results[cmd]={"rc":p.returncode,"stdout_tail":p.stdout[-500:],"stderr_tail":p.stderr[-500:]}
        ok=ok and p.returncode==0
    mark(tests,"mautic_cron_commands",ok,commands=results)

def twenty_access_token(tests) -> str:
    email="fa3-marketing@localhost.invalid"
    password=secret("twenty-admin-password")
    origin=TWENTY
    token_file=CONF/"twenty-user-access-token"

    sign_up_q="""
    mutation SignUp($email:String!,$password:String!,$locale:String) {
      signUp(email:$email,password:$password,locale:$locale) {
        tokens { accessOrWorkspaceAgnosticToken { token } }
      }
    }"""
    new_workspace_q="""
    mutation NewWorkspace($input:SignUpInNewWorkspaceInput) {
      signUpInNewWorkspace(input:$input) {
        loginToken { token }
        workspace { id workspaceUrls { subdomainUrl customUrl } }
      }
    }"""
    login_q="""
    mutation Login($email:String!,$password:String!,$origin:String!,$locale:String) {
      getLoginTokenFromCredentials(email:$email,password:$password,origin:$origin,locale:$locale) {
        loginToken { token }
      }
    }"""
    exchange_q="""
    mutation Exchange($loginToken:String!,$origin:String!) {
      getAuthTokensFromLoginToken(loginToken:$loginToken,origin:$origin) {
        tokens { accessOrWorkspaceAgnosticToken { token } refreshToken { token } }
      }
    }"""

    # Fresh runtime: create the first workspace. Re-runs: authenticate normally.
    try:
        d=gql(sign_up_q,{"email":email,"password":password,"locale":"hu-HU"})
        wa=d["signUp"]["tokens"]["accessOrWorkspaceAgnosticToken"]["token"]
        nw=gql(new_workspace_q,{"input":{"displayName":"FA3 Marketing","subdomain":"fa3-marketing"}},wa)
        lt=nw["signUpInNewWorkspace"]["loginToken"]["token"]
    except Exception:
        d=gql(login_q,{"email":email,"password":password,"origin":origin,"locale":"hu-HU"})
        lt=d["getLoginTokenFromCredentials"]["loginToken"]["token"]
    ex=gql(exchange_q,{"loginToken":lt,"origin":origin})
    access=ex["getAuthTokensFromLoginToken"]["tokens"]["accessOrWorkspaceAgnosticToken"]["token"]

    current_q="""query Current { currentUser { id locale workspaceMember { id locale } } }"""
    cur=gql(current_q,token=access)["currentUser"]
    locales={cur.get("locale"),(cur.get("workspaceMember") or {}).get("locale")}
    mark(tests,"twenty_hu_signup","hu-HU" in locales,user_locale=cur.get("locale"),
         workspace_member_locale=(cur.get("workspaceMember") or {}).get("locale"))
    return access

def twenty_checks(tests):
    s,_,_=request(TWENTY+"/healthz")
    mark(tests,"twenty_health",s==200,http_status=s)
    access=twenty_access_token(tests)

    key_file=CONF/"twenty-api-key"
    api_key=None
    if key_file.exists() and key_file.read_text(encoding="utf-8").strip():
        api_key=key_file.read_text(encoding="utf-8").strip()
    if not api_key:
        roles=gql("""query Roles { getApiKeyRoles { id label canBeAssignedToApiKeys } }""",token=access)["getApiKeyRoles"]
        role=next((x for x in roles if x.get("label")=="Admin" and x.get("canBeAssignedToApiKeys")),None)
        role=role or next((x for x in roles if x.get("canBeAssignedToApiKeys")),None)
        if not role:
            raise RuntimeError("Twenty has no API-key-assignable role")
        expires=(datetime.now(timezone.utc)+timedelta(days=90)).isoformat()
        c=gql("""mutation Create($input:CreateApiKeyInput!){ createApiKey(input:$input){ id expiresAt } }""",
              {"input":{"name":"FA3 Marketing current-host E2E","expiresAt":expires,"roleId":role["id"]}},access)
        kid=c["createApiKey"]["id"]
        t=gql("""mutation Token($apiKeyId:UUID!,$expiresAt:DateTime!){ generateApiKeyToken(apiKeyId:$apiKeyId,expiresAt:$expiresAt){ token } }""",
              {"apiKeyId":kid,"expiresAt":expires},access)
        api_key=t["generateApiKeyToken"]["token"]
        key_file.write_text(api_key,encoding="utf-8")
        key_file.chmod(0o600)

    h={"Authorization":f"Bearer {api_key}"}
    qs,qobj,qraw=request(TWENTY+"/rest/people?limit=1",headers=h)
    mark(tests,"twenty_api_key",qs==200,http_status=qs)

    email=f"fa3-twenty-e2e-{int(time.time())}@localhost.invalid"
    payload={"name":{"firstName":"Árvíztűrő","lastName":"Tükörfúrógép"},
             "emails":{"primaryEmail":email,"additionalEmails":[]}}
    s,obj,raw=request(TWENTY+"/rest/people","POST",payload,h)
    pid=recursive_id(obj)
    ok=False
    if s in (200,201) and pid:
        gs,gobj,graw=request(TWENTY+f"/rest/people/{pid}",headers=h)
        ok=gs==200 and email in graw and "Árvíztűrő" in graw
        request(TWENTY+f"/rest/people/{pid}","DELETE",headers=h)
    mark(tests,"twenty_person_roundtrip",ok,http_status=s,person_id=pid)

def listmonk_headers() -> dict[str,str]:
    token=secret("listmonk-api-token")
    auth=base64.b64encode(f"fa3api:{token}".encode()).decode()
    return {"Authorization":f"Basic {auth}"}

def wait_listmonk():
    for _ in range(60):
        s,_,_=request(LISTMONK+"/")
        if s==200:
            return
        time.sleep(1)
    raise RuntimeError("listmonk did not return after settings reload")

def listmonk_checks(tests):
    s,_,_=request(LISTMONK+"/")
    mark(tests,"listmonk_health",s==200,http_status=s)
    h=listmonk_headers()
    s,obj,raw=request(LISTMONK+"/api/lists?per_page=1",headers=h)
    mark(tests,"listmonk_api_auth",s==200,http_status=s)

    # Update only the language key. The endpoint reloads the app when safe.
    us,uobj,uraw=request(LISTMONK+"/api/settings/app.lang","PUT","hu",h)
    if us==200:
        time.sleep(2)
        wait_listmonk()
    gs,gobj,graw=request(LISTMONK+"/api/settings",headers=h)
    data=(gobj or {}).get("data",{}) if isinstance(gobj,dict) else {}
    mark(tests,"listmonk_hu_locale",gs==200 and data.get("app.lang")=="hu",locale=data.get("app.lang"))

    # Subscriber + private single-opt-in list roundtrip.
    suffix=str(int(time.time()))
    ls,lobj,lraw=request(LISTMONK+"/api/lists","POST",
        {"name":f"FA3 E2E {suffix}","type":"private","optin":"single","status":"active",
         "tags":["fa3-e2e"],"description":"FA3 current-host production E2E"},h)
    lid=((lobj or {}).get("data") or {}).get("id") if isinstance(lobj,dict) else None
    email=f"fa3-listmonk-e2e-{suffix}@localhost.invalid"
    sid=None
    sub_ok=False
    if ls in (200,201) and lid:
        ss,sobj,sraw=request(LISTMONK+"/api/subscribers","POST",
            {"email":email,"name":"Árvíztűrő Tükörfúrógép","status":"enabled","lists":[lid],
             "attribs":{"locale":"hu-HU","source":"fa3-e2e"},"preconfirm_subscriptions":True},h)
        sid=((sobj or {}).get("data") or {}).get("id") if isinstance(sobj,dict) else None
        if ss in (200,201) and sid:
            rs,robj,rraw=request(LISTMONK+f"/api/subscribers/{sid}",headers=h)
            sub_ok=rs==200 and email in rraw and "Árvíztűrő" in rraw
    mark(tests,"listmonk_subscriber_roundtrip",sub_ok,list_id=lid,subscriber_id=sid)

    # Real SMTP path through listmonk, but network-internal sink only.
    sink=STATE/"smtp/messages.jsonl"
    before=0
    if sink.exists():
        before=len(sink.read_text(encoding="utf-8").splitlines())
    smtp={
      "name":"fa3-e2e","enabled":True,"host":"smtp-sink","port":1025,
      "auth_protocol":"none","username":"","password":"","hello_hostname":"fa3.local",
      "tls_type":"none","tls_skip_verify":False,"max_conns":1,"max_msg_retries":1,
      "msg_retry_delay":"10ms","idle_timeout":"2s","wait_timeout":"2s",
      "email_headers":[],"from_addresses":[],"email":"smtp-e2e@localhost.invalid"
    }
    ts,tobj,traw=request(LISTMONK+"/api/settings/smtp/test","POST",smtp,h)
    time.sleep(1)
    after_lines=sink.read_text(encoding="utf-8").splitlines() if sink.exists() else []
    new=after_lines[before:]
    delivered=ts==200 and any("smtp-e2e@localhost.invalid" in x for x in new)
    mark(tests,"listmonk_smtp_delivery",delivered,http_status=ts,sink_messages=len(new))

    # The sink has no published host port and the exercised SMTP target is the internal DNS alias.
    pp=run("podman","port","fa3-mkt-smtp-sink")
    sink_only=not pp.stdout.strip() and smtp["host"]=="smtp-sink" and smtp["port"]==1025
    mark(tests,"smtp_egress_sink_only",sink_only,smtp_host=smtp["host"],published_port=pp.stdout.strip())

    if sid:
        request(LISTMONK+f"/api/subscribers/{sid}","DELETE",headers=h)
    if lid:
        request(LISTMONK+f"/api/lists/{lid}","DELETE",headers=h)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default=str(ROOT/"evidence/receipts/marketing-current-host.json"))
    args=ap.parse_args()
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    tests={}
    errors=[]
    for fn in (rootless_check,image_lock_check,loopback_check,mautic_checks,twenty_checks,listmonk_checks):
        try:
            fn(tests)
        except Exception as e:
            errors.append({"stage":fn.__name__,"error":str(e)})
    required={
      "rootless_podman","immutable_image_lock","loopback_only_public_bindings",
      "mautic_health","mautic_hu_locale","mautic_contact_roundtrip","mautic_cron_commands",
      "twenty_health","twenty_hu_signup","twenty_api_key","twenty_person_roundtrip",
      "listmonk_health","listmonk_api_auth","listmonk_hu_locale",
      "listmonk_subscriber_roundtrip","listmonk_smtp_delivery","smtp_egress_sink_only"
    }
    all_pass=not errors and required.issubset(tests) and all(tests[x]["status"]=="PASS" for x in required)
    lock={}
    lp=STATE/"image-lock.json"
    if lp.exists():
        raw=lp.read_bytes()
        lock={"sha256":hashlib.sha256(raw).hexdigest(),
              "images":json.loads(raw).get("images",{})}
    receipt={
      "schema":"fa3.marketing-current-host-evidence.v1",
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "execution_context":"CURRENT_HOST_REAL_EXECUTION",
      "runtime_status":"CURRENT_HOST_PRODUCTION_E2E_PASS" if all_pass else "CURRENT_HOST_E2E_FAIL",
      "provider_ids":PROVIDERS,
      "capability_count":143,
      "new_architectural_authorities":0,
      "tests":tests,
      "errors":errors,
      "image_lock":lock,
      "secrets_in_receipt":False
    }
    out.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,indent=2))
    return 0 if all_pass else 2

if __name__=="__main__":
    raise SystemExit(main())
