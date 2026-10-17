import base64
import re
import wave
import requests
from . import config
from .utils import strip_tags

def prepare_script(script):
    return script if config.ALLOW_EXPRESSION_TAGS else strip_tags(script)

def synthesize(script, out_path):
    text = f"{config.VOICE_STYLE}\n\n{prepare_script(script)}"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.TTS_MODEL}:generateContent"
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": config.VOICE_NAME}}
            },
        },
    }
    r = requests.post(url, headers={"x-goog-api-key": config.GEMINI_API_KEY,
                                    "Content-Type": "application/json"},
                      json=body, timeout=300)
    r.raise_for_status()
    inline = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
    rate_match = re.search(r"rate=(\d+)", inline.get("mimeType", ""))
    rate = int(rate_match.group(1)) if rate_match else 24000
    pcm = base64.b64decode(inline["data"])

    with wave.open(out_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return out_path