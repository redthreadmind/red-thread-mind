import logging
import os
import requests
from . import config

log = logging.getLogger("rtm.sources")
AUDIO_DIR = os.path.join(config.WORKDIR, "audio")


def _commercial_ok(url):
    u = (url or "").lower()
    if "-nc" in u:
        return False
    return "publicdomain/zero" in u or "licenses/by" in u


def _download(url, dest):
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)


def fetch_music():
    """Background music from Jamendo (Creative Commons, commercial use allowed)."""
    if not config.JAMENDO_CLIENT_ID:
        return None, []
    try:
        r = requests.get("https://api.jamendo.com/v3.0/tracks/", params={
            "client_id": config.JAMENDO_CLIENT_ID,
            "format": "json",
            "limit": 40,
            "tags": config.MUSIC_TAG,
            "order": "popularity_month",
            "audiodownload_allowed": "true",
            "include": "licenses",
        }, timeout=30)
        r.raise_for_status()
        for t in r.json().get("results", []):
            lic = t.get("license_ccurl", "")
            url = t.get("audiodownload") or ""
            if url and _commercial_ok(lic):
                os.makedirs(AUDIO_DIR, exist_ok=True)
                dest = os.path.join(AUDIO_DIR, "music.mp3")
                _download(url, dest)
                credit = f'Music: "{t["name"]}" by {t["artist_name"]} (Jamendo, {lic})'
                return dest, [credit]
    except Exception as e:
        log.warning("Music fetch failed: %s", e)
    return None, []


def fetch_sfx():
    """Whoosh sound effect from Freesound (Creative Commons, commercial use allowed)."""
    if not config.FREESOUND_API_KEY:
        return None, []
    try:
        r = requests.get("https://freesound.org/apiv2/search/text/", params={
            "query": "whoosh",
            "token": config.FREESOUND_API_KEY,
            "filter": "duration:[0.3 TO 2.5]",
            "fields": "id,name,username,license,previews",
            "page_size": 15,
        }, timeout=30)
        r.raise_for_status()
        for s in r.json().get("results", []):
            lic = s.get("license", "")
            url = (s.get("previews") or {}).get("preview-hq-mp3")
            if url and _commercial_ok(lic):
                os.makedirs(AUDIO_DIR, exist_ok=True)
                dest = os.path.join(AUDIO_DIR, "sfx.mp3")
                _download(url, dest)
                credit = f'SFX: "{s["name"]}" by {s["username"]} (Freesound, {lic})'
                return dest, [credit]
    except Exception as e:
        log.warning("SFX fetch failed: %s", e)
    return None, []


def fetch_audio():
    music, c1 = fetch_music()
    sfx, c2 = fetch_sfx()
    return music, sfx, c1 + c2