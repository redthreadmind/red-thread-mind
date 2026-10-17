import base64
import logging
import re
import time
import wave
import requests
from . import config
from .utils import strip_tags

log = logging.getLogger("rtm.tts")
MAX_CHARS = 2000
PAUSE_SECONDS = 0.35
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def prepare_script(script):
    return script if config.ALLOW_EXPRESSION_TAGS else strip_tags(script)


def split_chunks(text, max_chars=MAX_CHARS):
    pieces = []
    for para in re.split(r"\n\s*\n", text):
        para = " ".join(para.split())
        if not para:
            continue
        if len(para) <= max_chars:
            pieces.append(para)
        else:
            pieces += re.split(r"(?<=[.!?])\s+", para)

    chunks, cur = [], ""
    for p in pieces:
        if cur and len(cur) + 1 + len(p) > max_chars:
            chunks.append(cur)
            cur = p
        else:
            cur = f"{cur} {p}".strip()
    if cur:
        chunks.append(cur)
    return chunks


def _rate_from(mime):
    m = re.search(r"rate=(\d+)", mime or "")
    return int(m.group(1)) if m else 24000


def _request_chunk(text):
    # Only the spoken words are sent. No instructions, so nothing gets read aloud.
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": config.VOICE_NAME}}
            },
        },
    }
    headers = {"x-goog-api-key": config.GEMINI_API_KEY, "Content-Type": "application/json"}
    url = URL.format(model=config.TTS_MODEL)

    for attempt in range(5):
        r = requests.post(url, headers=headers, json=body, timeout=300)
        if r.status_code in (429, 500, 503):
            wait = 15 * (attempt + 1)
            log.warning("TTS busy (%s), retrying in %ss", r.status_code, wait)
            time.sleep(wait)
            continue
        r.raise_for_status()
        inline = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
        return base64.b64decode(inline["data"]), _rate_from(inline.get("mimeType"))
    raise RuntimeError("TTS kept failing after retries")


def synthesize(script, out_path):
    chunks = split_chunks(prepare_script(script))
    if not chunks:
        raise RuntimeError("No spoken text found in the script")
    log.info("TTS chunks: %d, voice: %s", len(chunks), config.VOICE_NAME)

    parts, rate, silence = [], None, None
    for i, chunk in enumerate(chunks, 1):
        log.info("TTS chunk %d/%d", i, len(chunks))
        pcm, r = _request_chunk(chunk)
        if rate is None:
            rate = r
            silence = b"\x00\x00" * int(rate * PAUSE_SECONDS)
        if parts:
            parts.append(silence)
        parts.append(pcm)

    with wave.open(out_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(parts))
    return out_path