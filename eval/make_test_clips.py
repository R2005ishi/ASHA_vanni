"""Bootstrap test audio: synthesize each test sentence with Gnani Timbre, then
make a noisy copy (village background: fan hum + chatter-like noise).

    cd backend && python ../eval/make_test_clips.py            # needs GNANI_API_KEY, MOCK_TTS=0

Synthetic voices are a START, not proof. Before quoting numbers in your post,
add 20+ clips recorded by real people (friends, a nursing student, an ASHA)
to eval/audio/ with the same file names + a matching line in testset.jsonl.
Each synthesized sentence is cached, so re-running costs nothing.
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "backend"))

from app import gnani  # noqa: E402
from app.config import settings  # noqa: E402

OUT = ROOT / "audio"
OUT.mkdir(exist_ok=True)


def add_noise(src: Path, dst: Path, level: float = 0.06):
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
        "-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude={level}",
        "-f", "lavfi", "-i", "sine=frequency=110:sample_rate=16000",   # ceiling-fan / transformer hum
        "-filter_complex", "[2]volume=0.02[h];[0][1][h]amix=inputs=3:duration=first:normalize=0",
        "-ac", "1", "-ar", "16000", str(dst)], check=True)


async def main():
    if settings.mock_tts or not settings.gnani_api_key:
        sys.exit("Set GNANI_API_KEY and MOCK_TTS=0 in backend/.env first.")
    for line in (ROOT / "testset.jsonl").read_text().splitlines():
        case = json.loads(line)
        clean = OUT / f"{case['id']}.wav"
        if not clean.exists():
            key = await gnani.synthesize(case["text"], case["lang"])
            clean.write_bytes(gnani.tts_path(key).read_bytes())
        noisy = OUT / f"{case['id']}__noisy.wav"
        if not noisy.exists():
            add_noise(clean, noisy)
        print("ok", case["id"])

asyncio.run(main())
