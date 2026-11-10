"""Run with:  cd backend && MOCK_STT=1 MOCK_TTS=1 MOCK_LLM=1 DB_PATH=data/test.db pytest -q"""
import os
import subprocess
from datetime import date

os.environ.update({"MOCK_STT": "1", "MOCK_TTS": "1", "MOCK_LLM": "1", "DB_PATH": "data/test.db",
                   "DEMO_TODAY": "2026-11-06"})

from app.config import settings  # noqa: E402

if settings.db_path.exists():
    settings.db_path.unlink()

from fastapi.testclient import TestClient  # noqa: E402

from app import llm, rules  # noqa: E402
from app.main import app  # noqa: E402
from app.normalize import normalise  # noqa: E402
from app.speech_text import is_yes  # noqa: E402

client = TestClient(app)
TODAY = date(2026, 11, 6)


def test_normalise_medical_terms():
    assert "IFA" in normalise("आयरन की गोली 30 दी")
    assert normalise("பி பி 120/80") == "BP 120/80"


def test_mock_extract_anc():
    out = llm.mock_extract("லக்ஷ்மி, முருகன் மனைவி, கோவூர். ஆறு மாதம் கர்ப்பம். BP 150/95. Hb 9.5. "
                           "IFA 30 மாத்திரை கொடுத்தேன். அடுத்த visit 15ஆம் தேதி.", "ANC", TODAY)
    r = out["record"]
    assert (r["bp_systolic"], r["bp_diastolic"]) == (150, 95)
    assert r["gestation_months"] == 6 and r["ifa_tablets_given"] == 30 and r["hb"] == 9.5
    assert r["next_visit_date"] == "2026-11-15"
    assert out["patient"]["husband_name"] == "முருகன்"


def test_rules():
    flags = rules.evaluate("ANC", {"bp_systolic": 150, "bp_diastolic": 95, "hb": 6.5})
    codes = {f["code"] for f in flags}
    assert codes == {"high_bp", "severe_anaemia"}
    assert rules.evaluate("ANC", {"bp_systolic": 118, "bp_diastolic": 76, "hb": 11.5}) == []
    hb = rules.evaluate("HBNC", {"weight_kg": 2.1, "temperature_c": 38.0, "breastfeeding_ok": False})
    assert {f["code"] for f in hb} == {"low_birth_weight", "newborn_fever", "not_feeding"}


def test_invalid_values_are_dropped_not_crashing():
    rec = llm._safe_record("ANC", {"bp_systolic": 9999, "gestation_months": 6})
    assert rec["bp_systolic"] is None and rec["gestation_months"] == 6


def test_yes_detection():
    assert is_yes("சரி") and is_yes("हाँ ठीक है") and not is_yes("இல்லை BP 140/90")


def _wav(tmp_path):
    p = tmp_path / "clip.webm"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=300:duration=2",
                    "-c:a", "libopus", str(p)], check=True)
    return p.read_bytes()


def test_full_visit_flow(tmp_path):
    audio = _wav(tmp_path)  # browser-style webm/opus -> converted with ffmpeg
    r = client.post("/api/visits", data={"visit_type": "ANC", "lang": "ta", "asha_id": "asha_ta_01"},
                    files={"audio": ("clip.webm", audio, "audio/webm")})
    assert r.status_code == 200, r.text
    body = r.json()
    v = body["visit"]
    assert v["status"] == "draft" and v["record"]["bp_systolic"] == 150
    assert any(f["code"] == "high_bp" for f in v["flags"])
    # two Lakshmis exist; husband name + village should pick the right one
    assert body["match"]["status"] == "matched" and body["match"]["patient"]["id"] == "p_ta_01"
    assert "சரியா" in body["readback_text"]
    assert client.get(body["readback_audio"]).status_code == 200

    # spoken correction, then spoken yes
    r = client.post(f"/api/visits/{v['id']}/reply", data={"mock_text": "இல்லை, BP 130/85"})
    assert r.json()["visit"]["record"]["bp_systolic"] == 130
    assert not any(f["code"] == "high_bp" for f in r.json()["visit"]["flags"])
    r = client.post(f"/api/visits/{v['id']}/reply", data={"mock_text": "சரி"})
    assert r.json()["saved"] is True

    csv = client.get("/api/export.csv").text
    assert "லக்ஷ்மி" in csv and "130" in csv


def test_briefing():
    b = client.get("/api/briefing", params={"asha_id": "asha_ta_01", "lang": "ta"}).json()
    assert b["items"] and b["text"].startswith("வணக்கம்")
