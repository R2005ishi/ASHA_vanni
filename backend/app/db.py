"""SQLite storage (swap DB_PATH for Postgres later if you deploy at scale)."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta

from .config import BACKEND_DIR, settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
  id TEXT PRIMARY KEY, asha_id TEXT, category TEXT, name TEXT, husband_name TEXT,
  village TEXT, lmp TEXT, dob TEXT, phone_last4 TEXT
);
CREATE TABLE IF NOT EXISTS visits (
  id TEXT PRIMARY KEY, asha_id TEXT, patient_id TEXT, visit_type TEXT, lang TEXT,
  status TEXT,                   -- draft | confirmed | discarded
  transcript TEXT, record TEXT, patient_spoken TEXT, flags TEXT, missing TEXT,
  engine TEXT, audio_key TEXT, created_at TEXT, confirmed_at TEXT, visit_date TEXT,
  reviewed INTEGER DEFAULT 0
);
"""


@contextmanager
def conn():
    c = sqlite3.connect(settings.db_path)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init(seed: bool = True):
    with conn() as c:
        c.executescript(SCHEMA)
        if seed and c.execute("SELECT COUNT(*) FROM patients").fetchone()[0] == 0:
            seed_file = BACKEND_DIR / "data" / "patients_seed.json"
            today = settings.today()
            for p in json.loads(seed_file.read_text()):
                # synthetic data: dates are relative to "today" so the demo always has visits due
                for off, col in (("lmp_offset_days", "lmp"), ("dob_offset_days", "dob")):
                    if off in p:
                        p[col] = (today + timedelta(days=p[off])).isoformat()
                c.execute("INSERT INTO patients VALUES (:id,:asha_id,:category,:name,:husband_name,"
                          ":village,:lmp,:dob,:phone_last4)",
                          {k: p.get(k) for k in ["id", "asha_id", "category", "name", "husband_name",
                                                 "village", "lmp", "dob", "phone_last4"]})


def patients(asha_id: str | None = None) -> list[dict]:
    with conn() as c:
        q, a = "SELECT * FROM patients", ()
        if asha_id:
            q, a = q + " WHERE asha_id=?", (asha_id,)
        return [dict(r) for r in c.execute(q, a)]


def _row(r) -> dict:
    d = dict(r)
    for k in ("record", "patient_spoken", "flags", "missing"):
        d[k] = json.loads(d[k]) if d.get(k) else None
    return d


def create_visit(**kw) -> dict:
    vid = "v_" + uuid.uuid4().hex[:10]
    now = datetime.now().isoformat(timespec="seconds")
    row = {"id": vid, "status": "draft", "created_at": now, "confirmed_at": None, "reviewed": 0, **kw}
    for k in ("record", "patient_spoken", "flags", "missing"):
        row[k] = json.dumps(row.get(k), ensure_ascii=False)
    with conn() as c:
        cols = ",".join(row)
        c.execute(f"INSERT INTO visits ({cols}) VALUES ({','.join('?' * len(row))})", list(row.values()))
    return get_visit(vid)


def update_visit(vid: str, **kw) -> dict:
    for k in ("record", "patient_spoken", "flags", "missing"):
        if k in kw:
            kw[k] = json.dumps(kw[k], ensure_ascii=False)
    with conn() as c:
        sets = ",".join(f"{k}=?" for k in kw)
        c.execute(f"UPDATE visits SET {sets} WHERE id=?", [*kw.values(), vid])
    return get_visit(vid)


def get_visit(vid: str) -> dict | None:
    with conn() as c:
        r = c.execute("SELECT * FROM visits WHERE id=?", (vid,)).fetchone()
    return _row(r) if r else None


def list_visits(status: str | None = "confirmed", asha_id: str | None = None) -> list[dict]:
    q, a = "SELECT * FROM visits WHERE 1=1", []
    if status:
        q += " AND status=?"
        a.append(status)
    if asha_id:
        q += " AND asha_id=?"
        a.append(asha_id)
    with conn() as c:
        return [_row(r) for r in c.execute(q + " ORDER BY created_at DESC", a)]
