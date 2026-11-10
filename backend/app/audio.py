"""Audio helpers. Browsers record webm/opus, which Prisma does not accept,
so every clip is converted to 16 kHz mono WAV with ffmpeg first."""
import hashlib
import io
import subprocess
import wave


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:24]


def to_wav_16k(data: bytes, max_seconds: int) -> bytes:
    """Convert any audio container to 16 kHz mono 16-bit WAV, trimmed to max_seconds."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
         "-t", str(max_seconds), "-ac", "1", "-ar", "16000", "-sample_fmt", "s16",
         "-f", "wav", "pipe:1"],
        input=data, capture_output=True, check=False,
    )
    if proc.returncode != 0 or not proc.stdout:
        raise ValueError(f"Could not decode audio: {proc.stderr.decode(errors='ignore')[:200]}")
    return proc.stdout


def duration_seconds(wav_bytes: bytes) -> float:
    with wave.open(io.BytesIO(wav_bytes)) as w:
        return w.getnframes() / float(w.getframerate())


def silent_wav(seconds: float = 0.4, rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))
    return buf.getvalue()
