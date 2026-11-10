"""Turn a visit transcript into a structured record.

Primary path: Gnani Evon v3.3 served behind an OpenAI-compatible endpoint
(vLLM / llama.cpp). Fallback path (MOCK_LLM=1 or Evon unreachable): a small
deterministic regex extractor so the app still works offline and in tests.

The LLM only *extracts what was said*. Danger signs are decided by rules.py,
never by the LLM.
"""
import json
import logging
import re
from datetime import date, timedelta

import httpx
from pydantic import ValidationError

from .config import settings
from .normalize import canon_vaccine
from .schemas import EXPECTED_FIELDS, RECORD_MODEL, Extraction, PatientRef

log = logging.getLogger("llm")

FIELD_GUIDE = {
    "ANC": """gestation_months (int, pregnancy month 1-10), bp_systolic (int), bp_diastolic (int),
bp_status_spoken ("normal"|"high"|"low" ONLY if BP was described in words without numbers),
hb (float g/dL), weight_kg (float), ifa_tablets_given (int count of Iron Folic Acid tablets),
calcium_tablets_given (int), td_dose ("Td1"|"Td2"|"Td-booster"),
complaints (list of short English phrases, e.g. "headache", "bleeding", "swelling of face", "blurred vision", "reduced fetal movement", "fever"),
next_visit_date (YYYY-MM-DD)""",
    "HBNC": """baby_age_days (int), weight_kg (float), temperature_c (float, convert Fahrenheit to Celsius),
breastfeeding_ok (bool), cord_ok (bool, umbilical cord clean/dry),
complaints (list of short English phrases, e.g. "not feeding", "fast breathing", "yellow skin", "cord pus", "lethargic", "convulsions", "cold to touch"),
next_visit_date (YYYY-MM-DD)""",
    "IMMUNISATION": """child_age_weeks (int), vaccines_given (list using ONLY these names:
BCG, OPV0, OPV1, OPV2, OPV3, HepB0, Penta1, Penta2, Penta3, Rota1, Rota2, Rota3, PCV1, PCV2,
PCV-booster, fIPV1, fIPV2, MR1, MR2, VitA, DPT-booster1),
complaints (list of short English phrases), next_visit_date (YYYY-MM-DD)""",
}

SYSTEM = """You are a careful data-entry assistant for ASHA community health workers in India.
You receive a short spoken visit note (Tamil, Hindi, or code-mixed with English) and output ONE JSON object.

Rules:
- Extract ONLY facts that were actually said. If something was not said, use null (or [] for lists). Never guess.
- Numbers may be spoken as words in Tamil/Hindi/English; convert them to digits.
- "BP 120 by 80" / "120/80" / "நூற்று இருபது எண்பது" means systolic 120, diastolic 80.
- Resolve relative dates ("15th", "next Monday", "அடுத்த வாரம்", "अगले हफ्ते") using TODAY. A bare day-of-month means the next such date on or after TODAY.
- Names stay in the script/spelling spoken. Translate complaints into short English phrases.
- Output JSON only, no explanation, in exactly this shape:
{"patient": {"name": str|null, "husband_name": str|null, "village": str|null}, "record": {...fields...}}
For HBNC and immunisation visits, husband_name holds the MOTHER's name and name holds the baby's name if said (else the mother's)."""


def _user_prompt(transcript: str, visit_type: str, today: date) -> str:
    return (f"TODAY: {today.isoformat()}\nVISIT TYPE: {visit_type}\n"
            f"Record fields:\n{FIELD_GUIDE[visit_type]}\n\nTRANSCRIPT:\n{transcript}")


def _parse_json(text: str) -> dict:
    # Evon is a reasoning model: drop any <think>...</think> block first
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON object in model output")
    return json.loads(text[start:end + 1])


async def _call_evon(transcript: str, visit_type: str, today: date) -> dict:
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": _user_prompt(transcript, visit_type, today)}]
    last_err = None
    async with httpx.AsyncClient(timeout=120) as client:
        for _ in range(2):  # one retry with the error fed back
            resp = await client.post(
                f"{settings.evon_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.evon_api_key}"},
                json={"model": settings.evon_model, "messages": messages,
                      "temperature": 0.0, "max_tokens": 1200,
                      # Evon reasons by default; extraction doesn't need it and it adds latency
                      "chat_template_kwargs": {"enable_thinking": False}},
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            try:
                return _parse_json(content)
            except (ValueError, json.JSONDecodeError) as e:
                last_err = e
                messages += [{"role": "assistant", "content": content},
                             {"role": "user", "content": "That was not valid JSON. Reply with the JSON object only."}]
    raise ValueError(f"Evon returned invalid JSON twice: {last_err}")


def _safe_record(visit_type: str, raw: dict) -> dict:
    """Validate field by field: an out-of-range value becomes null instead of failing the whole visit."""
    model = RECORD_MODEL[visit_type]
    clean = {}
    for name in model.model_fields:
        if name not in raw:
            continue
        try:
            model.model_validate({name: raw[name]})
            clean[name] = raw[name]
        except ValidationError:
            log.warning("dropping invalid %s=%r", name, raw[name])
    if visit_type == "IMMUNISATION":
        clean["vaccines_given"] = [v for v in (canon_vaccine(x) or x for x in clean.get("vaccines_given", []))
                                   if v]
    return model.model_validate(clean).model_dump()


def missing_fields(visit_type: str, record: dict) -> list[str]:
    missing = []
    for f in EXPECTED_FIELDS[visit_type]:
        if f == "bp":
            if record.get("bp_systolic") is None and record.get("bp_status_spoken") is None:
                missing.append("bp")
        elif record.get(f) in (None, []):
            missing.append(f)
    return missing


async def extract(transcript: str, visit_type: str, today: date | None = None) -> tuple[Extraction, str]:
    """Returns (extraction, engine_used)."""
    today = today or settings.today()
    engine = "evon"
    if settings.mock_llm:
        raw, engine = mock_extract(transcript, visit_type, today), "mock"
    else:
        try:
            raw = await _call_evon(transcript, visit_type, today)
        except Exception as e:  # Evon down: keep the ASHA working, flag it in the response
            log.error("Evon failed, using fallback extractor: %s", e)
            raw, engine = mock_extract(transcript, visit_type, today), "fallback"
    record = _safe_record(visit_type, raw.get("record", {}) or {})
    patient = PatientRef.model_validate(raw.get("patient", {}) or {})
    return Extraction(visit_type=visit_type, patient=patient, record=record,
                      missing_fields=missing_fields(visit_type, record)), engine


def merge(base: dict, correction: dict) -> dict:
    """Apply a spoken correction: any field the correction states overrides the draft."""
    out = dict(base)
    for k, v in correction.items():
        if v not in (None, [], ""):
            out[k] = v
    return out


# ------------------------------------------------------------------ deterministic fallback
NUM_WORDS = {
    # English
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    # Tamil
    "ஒன்று": 1, "ஒரு": 1, "இரண்டு": 2, "ரெண்டு": 2, "மூன்று": 3, "மூணு": 3, "நான்கு": 4, "நாலு": 4,
    "ஐந்து": 5, "அஞ்சு": 5, "ஆறு": 6, "ஏழு": 7, "எட்டு": 8, "ஒன்பது": 9, "பத்து": 10,
    # Hindi
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "छह": 6, "छः": 6, "सात": 7,
    "आठ": 8, "नौ": 9, "दस": 10,
}
_NUM = r"(\d+(?:\.\d+)?|" + "|".join(map(re.escape, NUM_WORDS)) + r")"


def _num(tok: str) -> float:
    return NUM_WORDS.get(tok.lower(), None) or float(tok)


def _next_day_of_month(day: int, today: date) -> str | None:
    d = today
    for _ in range(62):
        if d.day == day and d >= today:
            return d.isoformat()
        d += timedelta(days=1)
    return None


def mock_extract(t: str, visit_type: str, today: date) -> dict:
    low = t.lower()
    rec: dict = {}
    m = re.search(r"bp\s*(\d{2,3})\s*(?:/|by|बटा|ஓவர்|over)\s*(\d{2,3})", low)
    if m:
        rec["bp_systolic"], rec["bp_diastolic"] = int(m.group(1)), int(m.group(2))
    elif re.search(r"bp\s*(normal|நார்மல்|सामान्य|ठीक)", low):
        rec["bp_status_spoken"] = "normal"
    if m := re.search(r"hb\s*" + _NUM, low):
        rec["hb"] = _num(m.group(1))
    if m := re.search(_NUM + r"\s*(?:month|மாதம்|மாசம்|महीने|माह)", low):
        rec["gestation_months"] = int(_num(m.group(1)))
    # number AFTER "IFA" wins ("IFA 30 tablets"); else a number right before it ("30 IFA")
    if m := (re.search(r"ifa\D{0,15}?(\d+)", low) or re.search(r"(?<![\d.])(\d+)\s*(?:\S+\s*)?ifa", low)):
        rec["ifa_tablets_given"] = int(m.group(1))
    if m := re.search(r"(\d+(?:\.\d+)?)\s*kg", low):
        rec["weight_kg"] = float(m.group(1))
    if m := re.search(r"(\d+(?:\.\d+)?)\s*(?:degree|டிகிரி|डिग्री)", low):
        v = float(m.group(1))
        rec["temperature_c"] = round((v - 32) * 5 / 9, 1) if v > 50 else v
    if m := re.search(r"(\d{1,2})\s*(?:ஆம் தேதி|ம் தேதி|தேதி|तारीख|th|st|nd|rd)", low):
        rec["next_visit_date"] = _next_day_of_month(int(m.group(1)), today)
    if m := re.search(_NUM + r"\s*(?:days?|நாள்|दिन)", low):
        rec["baby_age_days"] = int(_num(m.group(1)))
    if visit_type == "HBNC":
        if any(w in low for w in ["பால் குடிக்கல", "दूध नहीं पी", "not feeding"]):
            rec["breastfeeding_ok"] = False
        elif any(w in low for w in ["பால் குடிக்குது", "दूध पी रहा", "feeding well", "feeding ok"]):
            rec["breastfeeding_ok"] = True
    complaints = []
    for words, label in [
        (["தலைவலி", "सिरदर्द", "headache"], "headache"),
        (["ரத்தப்போக்கு", "रक्तस्राव", "खून", "bleeding"], "bleeding"),
        (["வீக்கம்", "सूजन", "swelling"], "swelling of face"),
        (["காய்ச்சல்", "बुखार", "fever"], "fever"),
        (["கண் மங்கல்", "धुंधला", "blurred"], "blurred vision"),
        (["மூச்சு", "सांस", "breathing"], "fast breathing"),
        (["மஞ்சள்", "पीलिया", "yellow", "jaundice"], "yellow skin"),
        (["வலிப்பு", "दौरे", "convulsion", "fits"], "convulsions"),
        (["பால் குடிக்கல", "दूध नहीं पी", "not feeding"], "not feeding"),
    ]:
        if any(w in low for w in words):
            complaints.append(label)
    rec["complaints"] = complaints
    if visit_type == "IMMUNISATION":
        found = re.findall(r"(bcg|opv\s*\d|penta\s*\d|rota\s*\d|pcv\s*\d|f?ipv\s*\d|mr\s*\d|vitamin a)", low)
        rec["vaccines_given"] = [canon_vaccine(x) for x in found if canon_vaccine(x)]
    # Patient: first comma-separated chunk is usually the name
    first = re.split(r"[,।.]", t.strip())[0].strip()
    patient = {"name": first or None, "husband_name": None, "village": None}
    if m := re.search(r"(\S+)\s*(?:மனைவி|की पत्नी|wife)", t):
        patient["husband_name"] = m.group(1).rstrip(",")
    if m := re.search(r"(?:गाँव|गांव|village)\s*(\S+)", t):
        patient["village"] = m.group(1).strip("।.,")
    elif m := re.search(r"(?:மனைவி|wife)\s*,?\s*([^,.\s]+)", t):
        patient["village"] = m.group(1)
    return {"patient": patient, "record": rec}
