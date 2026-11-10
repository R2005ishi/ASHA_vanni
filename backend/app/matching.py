"""Match the spoken patient to the ASHA's registered beneficiaries.

Name alone is unreliable (many Lakshmis in a village), so we score
name + husband/mother name + village, and only auto-match when one
candidate is clearly ahead. Otherwise the app asks the ASHA to pick.
"""
from rapidfuzz import fuzz

from . import db

CATEGORY_FOR = {"ANC": "pregnant", "HBNC": "newborn", "IMMUNISATION": "child"}


def _score(spoken: dict, p: dict) -> float:
    s = 0.0
    if spoken.get("name") and p.get("name"):
        s += 0.6 * fuzz.WRatio(spoken["name"], p["name"])
    if spoken.get("husband_name") and p.get("husband_name"):
        s += 0.25 * fuzz.WRatio(spoken["husband_name"], p["husband_name"])
    if spoken.get("village") and p.get("village"):
        s += 0.15 * fuzz.WRatio(spoken["village"], p["village"])
    present = (0.6 if spoken.get("name") else 0) + (0.25 if spoken.get("husband_name") else 0) + \
              (0.15 if spoken.get("village") else 0)
    return s / present if present else 0.0


def match(spoken: dict, visit_type: str, asha_id: str) -> dict:
    cat = CATEGORY_FOR[visit_type]
    pool = [p for p in db.patients(asha_id) if p["category"] == cat] or db.patients(asha_id)
    ranked = sorted(({"patient": p, "score": round(_score(spoken, p), 1)} for p in pool),
                    key=lambda x: -x["score"])
    top = ranked[:3]
    if not top or top[0]["score"] < 60:
        return {"status": "new", "patient": None, "candidates": top}
    if len(top) > 1 and top[0]["score"] - top[1]["score"] < 8:
        return {"status": "ambiguous", "patient": None, "candidates": top}
    return {"status": "matched", "patient": top[0]["patient"], "candidates": top}
