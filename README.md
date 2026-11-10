# ASHA Vaani

**ASHA workers talk; the app does the paperwork.**

India's roughly 10 lakh ASHA (Accredited Social Health Activist) workers record every home visit
twice, once in a paper register and again in government apps, and lose incentive money when
uploads fail. ASHA Vaani lets her speak the visit in Tamil or Hindi in about 20 seconds. The app
turns it into a structured record, reads it back in her language for a spoken "yes", flags danger
signs for the ANM (Auxiliary Nurse Midwife), and briefs her each morning on who to visit.

Built for Gnani AI's **Great Indian AI Internship Challenge** on all three Gnani models:

| Gnani model | What it does here |
|---|---|
| **Prisma v3.0** (speech-to-text) | Transcribes her code-mixed Tamil/Hindi + English note. Uses `keyterms` (IFA, BP, Td, Penta…), `topic`, `codemix` output and `ta-IN,en-IN` language hints. |
| **Evon v3.3** (LLM) | Extracts the structured record from the transcript, including spoken numbers and relative dates. |
| **Timbre v3.0** (text-to-speech) | Reads every record back for confirmation, and speaks the morning briefing. Voice: *Chetana* (Gnani's healthcare voice). |

> Synthetic patients only. Danger flags are for ANM review, not diagnosis.
> Thresholds must be checked with a clinician before any real use.

---

## How it works

```
ASHA's phone (PWA, works offline)
  big record button → webm audio → IndexedDB queue if offline → sync when online
        │
        ▼
FastAPI backend
  1. ffmpeg      → 16 kHz mono WAV, trimmed to 29 s (Prisma REST limit is 30 s)
  2. Prisma STT  → transcript                         (cached by audio hash)
  3. normalise   → fix medical terms ("आयरन की गोली" → "IFA गोली")
  4. Evon        → JSON record, validated field by field with Pydantic
  5. match       → which registered woman/baby? name + husband/mother + village
  6. rules       → danger flags (deterministic, never the LLM)
  7. read-back   → template text (exactly what was stored) → Timbre audio (cached)
  8. ASHA replies by voice: "sari"/"haan" saves it; anything else is a correction
        │
        ├── Morning briefing: flagged women first, then scheduled visits, newborn days, vaccines due
        └── ANM dashboard: flags to review, "mark reviewed", CSV export in RCH-style columns
```

### Tech stack

| Layer | Choice | Why |
|---|---|---|
| Phone app | Plain HTML/CSS/JS **PWA** (no build step) | Installs from a link, works offline, runs on low-end Android |
| Offline | Service worker + IndexedDB queue | Records without network, syncs later |
| Backend | **FastAPI** (Python 3.11+) | Async, simple, matches Gnani's Python examples |
| Audio | **ffmpeg** | Browsers record webm/opus; Prisma needs WAV/MP3/OGG/… |
| Speech | Gnani **Prisma v3.0** + **Timbre v3.0** REST | |
| LLM | Gnani **Evon v3.3** via any OpenAI-compatible server (vLLM / llama.cpp) | See `docs/EVON_HOSTING.md` |
| Matching | rapidfuzz | Fuzzy name matching across spellings |
| Database | SQLite | Zero setup; swap for Postgres at scale |
| Hosting | One Docker container (Render / Railway / Fly.io) | Frontend is served by the same app |

---

## Run it (5 minutes, no keys needed)

Needs Python 3.11+ and ffmpeg (`brew install ffmpeg`, `sudo apt install ffmpeg`, or `winget install ffmpeg`).

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # starts in mock mode: no credits used
python -m uvicorn app.main:app --reload --port 8000
```

- ASHA app: <http://localhost:8000>
- ANM dashboard: <http://localhost:8000/dashboard.html>
- API docs: <http://localhost:8000/docs>

In mock mode a "type the note" box appears under the record button, so you can build and test
the whole flow without spending credits. Try:

```
லக்ஷ்மி, முருகன் மனைவி, கோவூர். ஆறு மாதம் கர்ப்பம். BP 150/95. Hb 9.5. IFA 30 மாத்திரை கொடுத்தேன். அடுத்த visit 15ஆம் தேதி.
```

Run the tests: `cd backend && python -m pytest -q`

**Testing on your phone:** the microphone only works on `https://` or `localhost`. Run
`cloudflared tunnel --url http://localhost:8000` and open the https link it prints on your phone.

## Switch on the real models

Edit `backend/.env`, one at a time:

1. `GNANI_API_KEY=…`, then `MOCK_TTS=0` → you hear real Tamil/Hindi read-backs.
2. `MOCK_STT=0` → real recordings go through Prisma.
3. Host Evon (`docs/EVON_HOSTING.md`), set `EVON_BASE_URL`, then `MOCK_LLM=0`.

`/api/health` shows which parts are live. Each visit stores `engine` (`evon`, `fallback` or `mock`).

## Saving credits

- Every transcript and every spoken sentence is cached by content hash. The same clip or sentence
  is never paid for twice, so replaying a read-back is free.
- Build the UI in mock mode; turn real APIs on only for testing and the demo.
- Calls are sent one at a time with back-off on HTTP 429 (some accounts allow only 1 active request).
- `backend/data/cache/usage.jsonl` logs every real API call so you can track spend.
- Check the real per-credit rates in the Gnani console once your credits arrive.

## Measure accuracy (your numbers for the post)

```bash
# 1. make clean + noisy test clips from eval/testset.jsonl with Timbre (cached, one-time)
cd backend && python ../eval/make_test_clips.py
# 2. add real human recordings to eval/audio/ (same file names) — this matters most
# 3. run
python ../eval/run_eval.py            # audio through the full pipeline
python ../eval/run_eval.py --text     # extraction + rules only, no STT credits
```

The script prints field accuracy, danger-flag recall and precision, and latency per language for
clean vs noisy audio, and writes `eval/report.csv`.

**Read the numbers honestly:** with `MOCK_LLM=1` the fallback extractor was written against these
same sentences, so 100% means nothing. Quote numbers from Evon on audio, ideally from real voices.

## Deploy

```bash
docker build -t asha-vaani .
docker run -p 8000:8000 --env-file backend/.env asha-vaani
```

On Render or Railway: create a web service from this repo using the Dockerfile and add the `.env`
values as environment variables. SQLite resets on redeploy, which is fine for a demo; the patients
re-seed automatically.

## Project layout

```
backend/app/
  main.py         API routes
  gnani.py        Prisma + Timbre clients (cache, retry, usage log)
  llm.py          Evon extraction + fallback extractor + correction merge
  rules.py        danger-sign rules
  matching.py     patient matching
  briefing.py     morning briefing + immunisation/HBNC schedule
  speech_text.py  everything the app says, in Tamil and Hindi
  normalize.py    medical-term clean-up + Prisma keyterms
  schemas.py      ANC / HBNC / immunisation record models
backend/data/patients_seed.json   synthetic beneficiaries (dates are relative to "today")
frontend/         index.html (ASHA app), dashboard.html (ANM), app.js, sw.js
eval/             test set, clip generator, accuracy script
docs/             Evon hosting guide, build plan
```

## Known limits (say these out loud; judges respect it)

- No direct RCH / ASHA Soft / U-WIN integration (no public API). Output is "ready for upload" CSV.
- Danger thresholds are simplified and need clinical validation.
- Two languages so far; adding one means a language code, voice, and the strings in
  `speech_text.py` and `app.js`.
- Patient names spoken in a different script from the register may match poorly; the app asks
  her to pick when unsure.
