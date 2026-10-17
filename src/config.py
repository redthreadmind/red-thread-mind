import os


def _get(name, default=""):
    return os.environ.get(name, default).strip()


GEMINI_API_KEY = _get("GEMINI_API_KEY")
PIXABAY_API_KEY = _get("PIXABAY_API_KEY")
TELEGRAM_BOT_TOKEN = _get("TELEGRAM_BOT_TOKEN")
YOUTUBE_CLIENT_ID = _get("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = _get("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN = _get("YOUTUBE_REFRESH_TOKEN")
JAMENDO_CLIENT_ID = _get("JAMENDO_CLIENT_ID")
FREESOUND_API_KEY = _get("FREESOUND_API_KEY")

TTS_MODEL = _get("TTS_MODEL", "gemini-3.8-flash-tts")
TEXT_MODEL = _get("TEXT_MODEL", "gemini-3.8-flash")
WHISPER_MODEL = _get("WHISPER_MODEL", "small")
VOICE_NAME = _get("VOICE_NAME", "Algieba")
MUSIC_TAG = _get("MUSIC_TAG", "cinematic")

ALLOW_EXPRESSION_TAGS = _get("ALLOW_EXPRESSION_TAGS", "true").lower() == "true"
SCHEDULE_MODE = _get("SCHEDULE_MODE", "private")

VIDEO_W = 1920
VIDEO_H = 1080
FPS = 30
CUT_SECONDS = float(_get("CUT_SECONDS", "1.4"))
WORKDIR = "tmp"

REQUIRED = [
    "GEMINI_API_KEY", "PIXABAY_API_KEY", "TELEGRAM_BOT_TOKEN",
    "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN",
]


def validate():
    missing = [n for n in REQUIRED if not os.environ.get(n, "").strip()]
    if missing:
        raise SystemExit("Missing secrets: " + ", ".join(missing))