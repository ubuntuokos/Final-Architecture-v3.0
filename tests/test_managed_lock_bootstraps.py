from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "FA3-UPSTREAM-LOCK-REGISTRY-001.json"


def test_whisper_bootstrap_consumes_central_lock():
    text = (ROOT / "bin/fa3-whisper-bootstrap.sh").read_text(encoding="utf-8")
    assert REGISTRY in text
    assert 'o["locks"]["whisper"]' in text
    assert "31243bad24cc746f07d4c8bfdd2d974872cb1803" not in text


def test_demucs_bootstrap_consumes_central_lock():
    text = (ROOT / "bin/fa3-demucs-bootstrap.sh").read_text(encoding="utf-8")
    assert REGISTRY in text
    assert 'o["locks"]["demucs"]' in text
    assert 'demucs==4.1.0' not in text
    assert "6a604bb002d12c4fbabb303ba64db40b5c5743f0" not in text
