import os

def _get(name, default=""):
    return os.environ.get(name, default).strip()

GEMINI_API_KEY = _get("GEMINI_API_KEY")
PEXELS_API_KEY = _get("PEXELS_API_KEY")
PIXABAY_API_KEY = _get("PIXABAY_API_KEY")
TELEGRAM_BOT_TOKEN = _get("TELEGRAM_BOT_TOKEN")
YOUTUBE_CLIENT_ID = _get("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = _get("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN = _get("YOUTUBE_REFRESH_TOKEN")

# Models: change these here if Google renames them. Check AI Studio.
TTS_MODEL = _get("TTS_MODEL", "gemini-2.5-flash-preview-tts")
TEXT_MODEL = _get("TEXT_MODEL", "gemini-2.5-flash")
WHISPER_MODEL = _get("WHISPER_MODEL", "small")

VOICE_NAME = "Charon"
VOICE_STYLE = (
    "Read the following as a calm, warm, confident American narrator. "
    "Speak at a steady, slightly slower pace with natural pauses. "
    "Emphasize key words lightly. Do not sound theatrical."
)

ALLOW_EXPRESSION_TAGS = _get("ALLOW_EXPRESSION_TAGS", "false").lower() == "true"
SCHEDULE_MODE = _get("SCHEDULE_MODE", "private")   # "private" or "publish_at"

VIDEO_W = 1920
VIDEO_H = 1080
FPS = 30
SLICE_SECONDS = 3.0
WORKDIR = "tmp"

REQUIRED = [
    "GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN",
    "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN",
]

def validate():
    missing = [n for n in REQUIRED if not os.environ.get(n, "").strip()]
    if not (PIXABAY_API_KEY or PEXELS_API_KEY):
        missing.append("PIXABAY_API_KEY or PEXELS_API_KEY")
    if missing:
        raise SystemExit("Missing secrets: " + ", ".join(missing))