"""Morning briefing: who should this ASHA visit today, in priority order."""
from datetime import date, timedelta

from . import db
from .speech_text import T

# National Immunisation Schedule (simplified): dose -> age in days
VAX_SCHEDULE = {
    "BCG": 0, "OPV0": 0, "HepB0": 0,
    "Penta1": 42, "OPV1": 42, "Rota1": 42, "PCV1": 42, "fIPV1": 42,
    "Penta2": 70, "OPV2": 70, "Rota2": 70,
    "Penta3": 98, "OPV3": 98, "Rota3": 98, "PCV2": 98, "fIPV2": 98,
    "MR1": 270, "PCV-booster": 270, "VitA": 270,
}
# HBNC home visits (days after birth) for institutional deliveries
HBNC_DAYS = [3, 7, 14, 21, 28, 42]


def build(asha_id: str, today: date, lang: str) -> dict:
    visits = db.list_visits("confirmed", asha_id)
    by_patient: dict[str, list] = {}
    for v in visits:
        by_patient.setdefault(v["patient_id"], []).append(v)

    items = []
    for p in db.patients(asha_id):
        pv = by_patient.get(p["id"], [])
        # 1. urgent flags from the last 7 days not yet reviewed by the ANM
        recent_flags = [f for v in pv if not v["reviewed"]
                        and v["visit_date"] and date.fromisoformat(v["visit_date"]) >= today - timedelta(days=7)
                        for f in (v["flags"] or []) if f["severity"] in ("urgent", "high")]
        if recent_flags:
            items.append({"priority": 0, "kind": "flag", "patient": p,
                          "detail": recent_flags[0]["labels"][lang]})
            continue
        # 2. a visit the ASHA herself scheduled for today
        if any((v["record"] or {}).get("next_visit_date") == today.isoformat() for v in pv):
            kind = {"pregnant": "anc", "newborn": "hbnc", "child": "vax"}[p["category"]]
            items.append({"priority": 1, "kind": kind, "patient": p, "detail": ""})
            continue
        # 3. schedule-based: newborn visit days and vaccines due
        if p["dob"]:
            age = (today - date.fromisoformat(p["dob"])).days
            given = {x for v in pv for x in (v["record"] or {}).get("vaccines_given", [])}
            due = [d for d, at in VAX_SCHEDULE.items() if at <= age <= at + 28 and d not in given]
            vax = ", ".join(due[:3])
            # one line per person: a newborn visit day also mentions any vaccines due
            if p["category"] == "newborn" and age in HBNC_DAYS:
                items.append({"priority": 2, "kind": "hbnc", "patient": p, "detail": f"day {age}", "vax": vax})
            elif due and p["category"] in ("child", "newborn"):
                items.append({"priority": 2, "kind": "vax", "patient": p, "detail": vax})

    items.sort(key=lambda x: x["priority"])
    t = T[lang]
    if not items:
        text = t["brief_none"]
    else:
        lines = [t["brief_head"].format(n=len(items))]
        for it in items[:6]:
            name = it["patient"]["name"]
            key = {"flag": "brief_item_flag", "anc": "brief_item_anc",
                   "hbnc": "brief_item_hbnc", "vax": "brief_item_vax"}[it["kind"]]
            lines.append(t[key].format(name=name, v=it["detail"]))
            if it.get("vax"):
                lines.append(t["brief_vax_also"].format(v=it["vax"]))
        text = " ".join(lines)
    return {"date": today.isoformat(), "items": items, "text": text}
