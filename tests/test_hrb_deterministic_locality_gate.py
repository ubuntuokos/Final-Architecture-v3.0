from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_hrb_deterministic_locality_gate import evaluate


def test_hrb_deterministic_locality_reference_gate_passes():
    result = evaluate(ROOT)
    assert result["status"] == "PASS"
    assert result["summary"] == {"passed": 22, "total": 22}
    assert result["current_host_runtime_promotion_claim"] is False


def test_hrb_authority_and_capability_count_are_preserved():
    result = evaluate(ROOT)
    by_name = {item["name"]: item for item in result["checks"]}
    assert by_name["capability-count-stable"]["status"] == "PASS"
    assert by_name["no-new-authority"]["status"] == "PASS"
    assert by_name["hrb-authority-preserved"]["status"] == "PASS"


def test_no_false_current_host_locality_claim():
    result = evaluate(ROOT)
    by_name = {item["name"]: item for item in result["checks"]}
    assert by_name["current-host-claim-honest"]["status"] == "PASS"
