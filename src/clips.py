import logging
import os
import re
import time
import requests
from . import config

log = logging.getLogger("rtm.clips")
MIN_CLIP_SECONDS = 2.0

FALLBACK_QUERIES = [
    "man running sunrise",
    "person walking city night",
    "alarm clock morning",
    "man climbing stairs",
    "gym workout man",
    "mountain climb sunrise",
    "ocean waves slow motion",
]

_search_cache = {}
_pixabay_disabled = False


class RateLimited(Exception):
    pass


def _get(url, params):
    for attempt in range(3):
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 429:
            time.sleep(30 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RateLimited(url)


def _search(query):
    global _pixabay_disabled
    if query in _search_cache:
        return _search_cache[query]
    if _pixabay_disabled or not config.PIXABAY_API_KEY:
        return []

    time.sleep(0.7)  # Pixabay allows about 100 requests per minute
    try:
        data = _get("https://pixabay.com/api/videos/",
                    {"key": config.PIXABAY_API_KEY, "q": query,
                     "per_page": 30, "safesearch": "true", "order": "popular"})
    except RateLimited:
        log.warning("Pixabay rate limit reached; the rest of this run will use cached results only")
        _pixabay_disabled = True
        return []
    except Exception as e:
        log.warning("Pixabay failed for %r: %s", query, e)
        return []

    out = []
    for hit in data.get("hits", []):
        videos = hit.get("videos", {})
        f = videos.get("large") or videos.get("medium") or {}
        if f.get("url") and f.get("width", 0) >= 1280 and hit.get("duration", 0) >= MIN_CLIP_SECONDS:
            out.append({
                "id": f"px-{hit['id']}",
                "url": f["url"],
                "duration": hit["duration"],
                "w": f["width"],
                "tags": hit.get("tags", ""),
            })
    _search_cache[query] = out
    return out


def _words(text):
    return set(re.findall(r"[a-z]+", text.lower()))


def _score(clip, query):
    return len(_words(query) & _words(clip.get("tags", "")))


def _pick(query, used, strict, allow_reuse=False):
    cands = [c for c in _search(query) if allow_reuse or c["id"] not in used]
    if not cands:
        return None
    cands.sort(key=lambda c: (_score(c, query), c["w"]), reverse=True)
    best = cands[0]
    if strict and _score(best, query) == 0:
        return None
    return best


def _download(url, dest):
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)


def fetch_all(cuts, plan):
    """Return {cut_index: local_clip_path}. Prefers unused, relevant clips, then reuses if needed."""
    clip_dir = os.path.join(config.WORKDIR, "clips")
    os.makedirs(clip_dir, exist_ok=True)

    used, result = set(), {}
    counts = {"exact": 0, "fallback": 0, "reused": 0}

    for c in cuts:
        q = plan[c["index"]]["query"]
        attempts = [(q, True, False, "exact")]
        attempts += [(f, True, False, "fallback") for f in FALLBACK_QUERIES]
        attempts += [(q, False, False, "fallback")]
        attempts += [(f, False, False, "fallback") for f in FALLBACK_QUERIES]
        attempts += [(q, False, True, "reused")]
        attempts += [(f, False, True, "reused") for f in FALLBACK_QUERIES]

        pick, label = None, None
        for query, strict, reuse, lab in attempts:
            pick = _pick(query, used, strict, allow_reuse=reuse)
            if pick:
                label = lab
                break
        if not pick:
            raise RuntimeError(f"No Pixabay clip found for cut {c['index']} ({q})")

        counts[label] += 1
        used.add(pick["id"])
        dest = os.path.join(clip_dir, pick["id"] + ".mp4")
        if not os.path.exists(dest):
            _download(pick["url"], dest)
        result[c["index"]] = dest

    log.info("Clips: %d cuts, exact %d, fallback %d, reused %d",
             len(result), counts["exact"], counts["fallback"], counts["reused"])
    return result