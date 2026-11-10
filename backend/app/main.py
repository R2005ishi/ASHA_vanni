"""ASHA Vaani API.

Flow for one visit:
  POST /api/visits           audio -> Prisma -> normalise -> Evon -> match -> rules -> Timbre read-back  (draft)
  POST /api/visits/{id}/reply  ASHA's spoken reply: "yes" confirms, anything else is a correction
  POST /api/visits/{id}/confirm | /discard | /patient     button fallbacks
"""
import csv
import io
import logging
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import briefing, db, gnani, llm, matching, rules
from .audio import sha, to_wav_16k
from .config import BACKEND_DIR, settings
from .normalize import normalise
from .speech_text import T, is_yes, readback

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="ASHA Vaani", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
db.init()

AUDIO_DIR = settings.cache_dir / "visits"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------ helpers
async def _speech_to_text(audio: UploadFile | None, lang: str, visit_type: str,
                          mock_text: str | None) -> tuple[str, str, dict]:
    if audio is None:
        if not mock_text:
            raise HTTPException(400, "Send an audio file (or mock_text in mock mode).")
        return normalise(mock_text), "", {"model": "typed", "cached": False}
    raw = await audio.read()
    try:
        wav = to_wav_16k(raw, settings.max_clip_seconds)
    except ValueError as e:
        raise HTTPException(400, str(e))
    key = sha(wav)
    (AUDIO_DIR / f"{key}.wav").write_bytes(wav)
    try:
        stt = await gnani.transcribe(wav, lang, visit_type, mock_text=mock_text)
    except gnani.GnaniError as e:
        raise HTTPException(502, str(e))
    return normalise(stt["transcript"]), key, stt


async def _readback_payload(v: dict) -> dict:
    lang = v["lang"]
    name = (v["patient_spoken"] or {}).get("name")
    text = readback(lang, name, v["visit_type"], v["record"], v["flags"], v["missing"])
    try:
        audio_key = await gnani.synthesize(text, lang)
        audio_url = f"/api/audio/{audio_key}.wav"
    except gnani.GnaniError as e:
        logging.error(e)
        audio_url = None
    return {"visit": v, "readback_text": text, "readback_audio": audio_url}


# ------------------------------------------------------------------ routes
@app.get("/api/health")
def health():
    return {"ok": True, "today": settings.today().isoformat(),
            "mock": {"stt": settings.mock_stt or not settings.gnani_api_key,
                     "tts": settings.mock_tts or not settings.gnani_api_key,
                     "llm": settings.mock_llm},
            "models": {"stt": settings.prisma_model, "tts": settings.timbre_model,
                       "llm": settings.evon_model}}


@app.get("/api/patients")
def list_patients(asha_id: str = "asha_ta_01"):
    return db.patients(asha_id)


@app.post("/api/visits")
async def create_visit(visit_type: str = Form(...), lang: str = Form("ta"), asha_id: str = Form("asha_ta_01"),
                       audio: UploadFile | None = File(None), mock_text: str | None = Form(None)):
    if visit_type not in ("ANC", "HBNC", "IMMUNISATION") or lang not in ("ta", "hi"):
        raise HTTPException(400, "visit_type must be ANC|HBNC|IMMUNISATION and lang ta|hi")
    transcript, audio_key, stt = await _speech_to_text(audio, lang, visit_type, mock_text)
    if not transcript.strip():
        raise HTTPException(422, "No speech heard. Please record again.")
    ext, engine = await llm.extract(transcript, visit_type)
    m = matching.match(ext.patient.model_dump(), visit_type, asha_id)
    flags = rules.evaluate(visit_type, ext.record)
    v = db.create_visit(asha_id=asha_id, visit_type=visit_type, lang=lang, transcript=transcript,
                        record=ext.record, patient_spoken=ext.patient.model_dump(), flags=flags,
                        missing=ext.missing_fields, engine=engine, audio_key=audio_key,
                        patient_id=m["patient"]["id"] if m["patient"] else None,
                        visit_date=settings.today().isoformat())
    out = await _readback_payload(v)
    out.update({"match": m, "stt": stt})
    return out


@app.post("/api/visits/{vid}/reply")
async def reply(vid: str, audio: UploadFile | None = File(None), mock_text: str | None = Form(None)):
    """The ASHA answers the read-back by voice: 'sari'/'haan' confirms; anything else is a correction."""
    v = db.get_visit(vid) or _404()
    transcript, _, _ = await _speech_to_text(audio, v["lang"], v["visit_type"], mock_text)
    if is_yes(transcript):
        return await _confirm(v)
    corr, engine = await llm.extract(transcript, v["visit_type"])
    record = llm.merge(v["record"], corr.record)
    patient = llm.merge(v["patient_spoken"], corr.patient.model_dump())
    flags = rules.evaluate(v["visit_type"], record)
    v = db.update_visit(vid, record=record, patient_spoken=patient, flags=flags,
                        missing=llm.missing_fields(v["visit_type"], record),
                        transcript=v["transcript"] + " || correction: " + transcript)
    out = await _readback_payload(v)
    out["correction_heard"] = transcript
    return out


async def _confirm(v: dict) -> dict:
    v = db.update_visit(v["id"], status="confirmed", confirmed_at=settings.today().isoformat())
    text = T[v["lang"]]["saved"]
    key = await gnani.synthesize(text, v["lang"])
    return {"visit": v, "saved": True, "readback_text": text, "readback_audio": f"/api/audio/{key}.wav"}


@app.post("/api/visits/{vid}/confirm")
async def confirm(vid: str):
    return await _confirm(db.get_visit(vid) or _404())


@app.post("/api/visits/{vid}/discard")
def discard(vid: str):
    db.get_visit(vid) or _404()
    return db.update_visit(vid, status="discarded")


class PatientPick(BaseModel):
    patient_id: str


@app.post("/api/visits/{vid}/patient")
def pick_patient(vid: str, body: PatientPick):
    db.get_visit(vid) or _404()
    return db.update_visit(vid, patient_id=body.patient_id)


@app.post("/api/visits/{vid}/review")
def review(vid: str):
    """ANM marks a flagged visit as reviewed."""
    db.get_visit(vid) or _404()
    return db.update_visit(vid, reviewed=1)


@app.get("/api/visits")
def visits(status: str | None = "confirmed", asha_id: str | None = None):
    return db.list_visits(status, asha_id)


@app.get("/api/briefing")
async def get_briefing(asha_id: str = "asha_ta_01", lang: str = "ta"):
    b = briefing.build(asha_id, settings.today(), lang)
    key = await gnani.synthesize(b["text"], lang)
    b["audio"] = f"/api/audio/{key}.wav"
    return b


EXPORT_COLS = ["visit_id", "asha_id", "visit_date", "visit_type", "patient_id", "patient_name",
               "husband_or_mother_name", "village", "gestation_months", "bp_systolic", "bp_diastolic",
               "hb", "weight_kg", "ifa_tablets_given", "calcium_tablets_given", "td_dose",
               "baby_age_days", "temperature_c", "breastfeeding_ok", "cord_ok", "vaccines_given",
               "complaints", "danger_flags", "next_visit_date", "confirmed_by_asha", "transcript"]


@app.get("/api/export.csv")
def export_csv(asha_id: str | None = None):
    """RCH-style flat export the ANM / data-entry operator can upload or key in from one sheet."""
    pts = {p["id"]: p for p in db.patients()}
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=EXPORT_COLS)
    w.writeheader()
    for v in db.list_visits("confirmed", asha_id):
        r, sp = v["record"] or {}, v["patient_spoken"] or {}
        p = pts.get(v["patient_id"], {})
        w.writerow({
            "visit_id": v["id"], "asha_id": v["asha_id"], "visit_date": v["visit_date"],
            "visit_type": v["visit_type"], "patient_id": v["patient_id"] or "",
            "patient_name": p.get("name") or sp.get("name") or "",
            "husband_or_mother_name": p.get("husband_name") or sp.get("husband_name") or "",
            "village": p.get("village") or sp.get("village") or "",
            **{k: r.get(k, "") if r.get(k) is not None else "" for k in [
                "gestation_months", "bp_systolic", "bp_diastolic", "hb", "weight_kg", "ifa_tablets_given",
                "calcium_tablets_given", "td_dose", "baby_age_days", "temperature_c", "breastfeeding_ok",
                "cord_ok", "next_visit_date"]},
            "vaccines_given": "; ".join(r.get("vaccines_given", [])),
            "complaints": "; ".join(r.get("complaints", [])),
            "danger_flags": "; ".join(f"{f['labels']['en']} ({f['detail']})" for f in v["flags"] or []),
            "confirmed_by_asha": "yes", "transcript": v["transcript"],
        })
    buf.seek(0)
    return StreamingResponse(iter(["﻿" + buf.read()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=asha_vaani_export.csv"})


@app.get("/api/audio/{key}.wav")
def audio(key: str):
    if not key.isalnum():
        _404()
    for p in (gnani.tts_path(key), AUDIO_DIR / f"{key}.wav"):
        if Path(p).exists():
            return FileResponse(p, media_type="audio/wav")
    _404()


def _404():
    raise HTTPException(404, "not found")


# Serve the PWA from the same server (one deploy, no CORS headaches)
FRONTEND = BACKEND_DIR.parent / "frontend"
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
