"""Settings read from environment / .env."""
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes"}


class Settings:
    gnani_api_key = os.getenv("GNANI_API_KEY", "")
    gnani_base_url = os.getenv("GNANI_BASE_URL", "https://api.vachana.ai").rstrip("/")
    prisma_model = os.getenv("PRISMA_MODEL", "prisma-v3.0")
    timbre_model = os.getenv("TIMBRE_MODEL", "timbre-v3.0")
    timbre_voice = {
        "ta": os.getenv("TIMBRE_VOICE_TA", "Chetana"),
        "hi": os.getenv("TIMBRE_VOICE_HI", "Chetana"),
    }

    evon_base_url = os.getenv("EVON_BASE_URL", "http://localhost:8001/v1").rstrip("/")
    evon_api_key = os.getenv("EVON_API_KEY", "not-needed")
    evon_model = os.getenv("EVON_MODEL", "gnani/gnani-evon-v3.3-30B-A3B")

    mock_stt = _flag("MOCK_STT", "1")
    mock_tts = _flag("MOCK_TTS", "1")
    mock_llm = _flag("MOCK_LLM", "1")

    db_path = BACKEND_DIR / os.getenv("DB_PATH", "data/asha_vaani.db")
    cache_dir = BACKEND_DIR / os.getenv("CACHE_DIR", "data/cache")
    demo_today = os.getenv("DEMO_TODAY", "").strip()

    # Prisma REST accepts clips up to 30 s. We keep a safety margin.
    max_clip_seconds = 29

    def today(self) -> date:
        return date.fromisoformat(self.demo_today) if self.demo_today else date.today()


settings = Settings()
settings.cache_dir.mkdir(parents=True, exist_ok=True)
settings.db_path.parent.mkdir(parents=True, exist_ok=True)

# language short code -> Gnani locale
LOCALE = {"ta": "ta-IN", "hi": "hi-IN"}
