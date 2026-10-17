import json
import re
import requests
from . import config

BASE = "https://generativelanguage.googleapis.com/v1beta/models"

def _headers():
    # Key goes in a header, not the URL, so it can't leak into error messages.
    return {"x-goog-api-key": config.GEMINI_API_KEY, "Content-Type": "application/json"}

def generate_text(prompt, json_mode=False):
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    if json_mode:
        body["generationConfig"] = {"responseMimeType": "application/json"}
    r = requests.post(f"{BASE}/{config.TEXT_MODEL}:generateContent",
                      headers=_headers(), json=body, timeout=180)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]

def generate_json(prompt):
    raw = generate_text(prompt, json_mode=True).strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw).strip()
    return json.loads(raw)