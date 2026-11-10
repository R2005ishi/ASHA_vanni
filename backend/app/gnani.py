"""Gnani Prisma (speech-to-text) and Timbre (text-to-speech) clients.

API reference: https://docs.gnani.ai/api/STT/speech-to-text.md and
https://docs.gnani.ai/api/TTS/tts-inference.md

Credit-saving rules built in:
  * every transcript and every synthesized clip is cached on disk by content hash,
    so the same audio / sentence is never sent twice;
  * one request at a time (some accounts allow only 1 active request),
    with back-off on HTTP 429.
"""
import asyncio
import json
import logging
from pathlib import Path

import httpx

from .audio import sha, silent_wav
from .config import LOCALE, settings
from .normalize import KEYTERMS

log = logging.getLogger("gnani")
_lock = asyncio.Semaphore(1)

STT_CACHE = settings.cache_dir / "stt"
TTS_CACHE = settings.cache_dir / "tts"
STT_CACHE.mkdir(parents=True, exist_ok=True)
TTS_CACHE.mkdir(parents=True, exist_ok=True)

# simple usage log so you can see how many calls you've spent
USAGE_LOG = settings.cache_dir / "usage.jsonl"


def _log_usage(kind: str, **kw):
    with USAGE_LOG.open("a") as f:
        f.write(json.dumps({"kind": kind, **kw}, ensure_ascii=False) + "\n")


class GnaniError(RuntimeError):
    pass


async def _post_with_retry(client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    delay = 0.8
    for attempt in range(4):
        async with _lock:
            resp = await client.post(url, **kwargs)
        if resp.status_code != 429:
            return resp
        await asyncio.sleep(delay)
        delay *= 2
    return resp


# ------------------------------------------------------------------ STT
MOCK_TRANSCRIPT = {
    "ta": "லக்ஷ்மி, முருகன் மனைவி, கோவூர். ஆறு மாதம் கர்ப்பம். BP 150/95. Hb 9.5. IFA 30 மாத்திரை கொடுத்தேன். தலைவலி இருக்கு. அடுத்த visit 15ஆம் தேதி.",
    "hi": "सुनीता, रमेश की पत्नी, गाँव रामपुर। छह महीने की गर्भवती। BP 120/80. IFA की 30 गोलियाँ दीं। अगली विज़िट 15 तारीख।",
}


async def transcribe(wav: bytes, lang: str, visit_type: str, mock_text: str | None = None) -> dict:
    """Return {"transcript", "language", "cached", "model"}."""
    key = sha(wav)
    cache_file = STT_CACHE / f"{key}.json"
    if cache_file.exists():
        out = json.loads(cache_file.read_text())
        out["cached"] = True
        return out

    if settings.mock_stt or not settings.gnani_api_key:
        out = {"transcript": mock_text or MOCK_TRANSCRIPT[lang], "language": LOCALE[lang],
               "model": "mock", "cached": False}
        return out  # don't cache mocks, so switching to real STT works immediately

    data = {
        "language_code": f"{LOCALE[lang]},en-IN",   # code-mixed: regional language + English terms
        "model": settings.prisma_model,
    }
    if settings.prisma_model == "prisma-v3.0":
        data["format"] = "codemix"                  # keep English medical words in Latin script
        data["keyterms"] = json.dumps(KEYTERMS)
        data["topic"] = f"ASHA health worker dictating a {visit_type} home visit note"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await _post_with_retry(
            client, f"{settings.gnani_base_url}/stt/v3",
            headers={"X-API-Key-ID": settings.gnani_api_key},
            files={"audio_file": ("visit.wav", wav, "audio/wav")},
            data=data,
        )
    if resp.status_code != 200:
        raise GnaniError(f"Prisma STT failed ({resp.status_code}): {resp.text[:300]}")
    body = resp.json()
    out = {"transcript": body.get("transcript", ""),
           "language": body.get("detected_language_code", LOCALE[lang]),
           "model": body.get("model", settings.prisma_model), "cached": False}
    cache_file.write_text(json.dumps(out, ensure_ascii=False))
    _log_usage("stt", seconds_hint=round(len(wav) / 32000, 1), model=out["model"])
    return out


# ------------------------------------------------------------------ TTS
async def synthesize(text: str, lang: str) -> str:
    """Synthesize text, return the cache key. Audio is served at /api/audio/{key}.wav."""
    voice = settings.timbre_voice[lang]
    key = sha(f"{settings.timbre_model}|{voice}|{lang}|{text}".encode())
    path: Path = TTS_CACHE / f"{key}.wav"
    if path.exists():
        return key

    if settings.mock_tts or not settings.gnani_api_key:
        path.write_bytes(silent_wav())
        return key

    payload = {
        "text": text,
        "voice": voice,
        "model": settings.timbre_model,
        "language": LOCALE[lang],
        "speed": 0.95,  # a touch slower: clearer for field use
        "audio_config": {"sample_rate": 24000, "num_channels": 1, "sample_width": 2,
                         "encoding": "linear_pcm", "container": "wav"},
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await _post_with_retry(
            client, f"{settings.gnani_base_url}/api/v1/tts/inference",
            headers={"X-API-Key-ID": settings.gnani_api_key, "Content-Type": "application/json"},
            json=payload,
        )
    if resp.status_code != 200 or not resp.content:
        raise GnaniError(f"Timbre TTS failed ({resp.status_code}): {resp.text[:300]}")
    path.write_bytes(resp.content)
    _log_usage("tts", chars=len(text), model=settings.timbre_model, voice=voice)
    return key


def tts_path(key: str) -> Path:
    return TTS_CACHE / f"{key}.wav"
