"""Deterministic danger-sign rules.

These are deliberately NOT done by the LLM: they must be predictable,
explainable and testable. Thresholds follow common Indian maternal/newborn
screening guidance (hypertension >=140/90, anaemia Hb <11 and severe <7,
low birth weight <2.5 kg, newborn fever >=37.5 C / hypothermia <35.5 C).
Verify thresholds with a clinician before any real use.

The app FLAGS for ANM review. It never diagnoses or prescribes.
"""
from .schemas import RECORD_MODEL

DANGER_COMPLAINTS = {
    "ANC": {"bleeding", "convulsions", "blurred vision", "severe headache", "swelling of face",
            "reduced fetal movement", "leaking fluid", "fever", "headache"},
    "HBNC": {"not feeding", "fast breathing", "convulsions", "yellow skin", "cord pus",
             "lethargic", "cold to touch", "fever"},
    "IMMUNISATION": {"convulsions", "fast breathing", "high fever"},
}

LABELS = {
    "high_bp": {"en": "High BP", "ta": "BP அதிகம்", "hi": "BP ज़्यादा"},
    "severe_anaemia": {"en": "Severe anaemia", "ta": "கடும் ரத்தசோகை", "hi": "गंभीर खून की कमी"},
    "anaemia": {"en": "Anaemia", "ta": "ரத்தசோகை", "hi": "खून की कमी"},
    "bp_said_high": {"en": "BP reported high", "ta": "BP அதிகம் என்று சொன்னீர்கள்", "hi": "BP ज़्यादा बताया"},
    "low_birth_weight": {"en": "Low birth weight", "ta": "எடை குறைவு", "hi": "वज़न कम"},
    "very_low_weight": {"en": "Very low weight", "ta": "மிகக் குறைந்த எடை", "hi": "बहुत कम वज़न"},
    "newborn_fever": {"en": "Newborn fever", "ta": "குழந்தைக்கு காய்ச்சல்", "hi": "शिशु को बुखार"},
    "hypothermia": {"en": "Baby too cold", "ta": "குழந்தை குளிர்ச்சி", "hi": "शिशु ठंडा"},
    "not_feeding": {"en": "Not breastfeeding", "ta": "பால் குடிக்கவில்லை", "hi": "दूध नहीं पी रहा"},
    "danger_symptom": {"en": "Danger symptom", "ta": "ஆபத்து அறிகுறி", "hi": "खतरे का लक्षण"},
}


def _flag(code: str, severity: str, detail: str) -> dict:
    return {"code": code, "severity": severity, "detail": detail, "labels": LABELS[code]}


def evaluate(visit_type: str, record: dict) -> list[dict]:
    r = RECORD_MODEL[visit_type].model_validate(record).model_dump()
    flags: list[dict] = []

    if visit_type == "ANC":
        s, d = r["bp_systolic"], r["bp_diastolic"]
        if (s and s >= 140) or (d and d >= 90):
            sev = "urgent" if (s and s >= 160) or (d and d >= 110) else "high"
            flags.append(_flag("high_bp", sev, f"BP {s}/{d}"))
        elif r["bp_status_spoken"] == "high":
            flags.append(_flag("bp_said_high", "high", "BP described as high, no reading"))
        if r["hb"] is not None:
            if r["hb"] < 7:
                flags.append(_flag("severe_anaemia", "urgent", f"Hb {r['hb']}"))
            elif r["hb"] < 11:
                flags.append(_flag("anaemia", "medium", f"Hb {r['hb']}"))

    if visit_type == "HBNC":
        w, t = r["weight_kg"], r["temperature_c"]
        if w is not None:
            if w < 1.8:
                flags.append(_flag("very_low_weight", "urgent", f"{w} kg"))
            elif w < 2.5:
                flags.append(_flag("low_birth_weight", "high", f"{w} kg"))
        if t is not None:
            if t >= 37.5:
                flags.append(_flag("newborn_fever", "urgent", f"{t} °C"))
            elif t < 35.5:
                flags.append(_flag("hypothermia", "urgent", f"{t} °C"))
        if r["breastfeeding_ok"] is False:
            flags.append(_flag("not_feeding", "urgent", "not breastfeeding"))

    # complaints already covered by a measured flag are not stamped twice
    covered = {"not_feeding": "not feeding", "newborn_fever": "fever"}
    already = {covered[f["code"]] for f in flags if f["code"] in covered}
    for c in r.get("complaints", []):
        c = c.lower()
        if c in DANGER_COMPLAINTS[visit_type] and c not in already:
            flags.append(_flag("danger_symptom", "high", c))
    return flags
