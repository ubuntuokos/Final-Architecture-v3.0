import json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 p=json.loads((ROOT/"canonical/profiles/FA3-OBJECTIVE-COORDINATION-INTELLIGENCE-001.json").read_text())
 c=json.loads((ROOT/"canonical/contracts/FA3-OBJECTIVE-COORDINATION-INTELLIGENCE-CONTRACTS-001.json").read_text())
 assert p["capability_baseline"]==175 and p["capability_delta"]==0 and p["authority_delta"]==0
 assert p["fail_closed"] is True and p["hardware"]["cpu_only_required"] is True
 assert p["current_host_status"]=="PENDING_PHYSICAL_CURRENT_HOST_EVIDENCE"
 assert c["rules"]["required_cycles"]=="DENY_FAIL_CLOSED" and c["rules"]["ready_is_authorization"] is False
 print("FA3 OBJECTIVE COORDINATION INTELLIGENCE GATE: PASS")
if __name__=="__main__": main()
