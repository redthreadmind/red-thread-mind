import logging
import os
import time
import requests
from . import config

log = logging.getLogger("rtm.clips")
FALLBACK_QUERIES = [
    "cinematic sunrise mountains",
    "city street night walk",
    "ocean waves slow motion",
    "forest path morning",
]
_search_cache = {}
_disabled = set()


class RateLimited(Exception):
    pass


def _get(url, headers=None, params=None):
    for attempt in range(3):
        r = requests.get(url, headers=headers, params=params, timeout=30)
        if r.status_code == 429:
            time.sleep(20 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RateLimited(url)


def _pixabay(query):
    if not config.PIXABAY_API_KEY:
        return []
    time.sleep(0.7)  # Pixabay allows about 100 requests per minute
    data = _get("https://pixabay.com/api/videos/",
                params={"key": config.PIXABAY_API_KEY, "q": query,
                        "per_page": 10, "safesearch": "true"})
    out = []
    for hit in data.get("hits", []):
        f = hit.get("videos", {}).get("large") or hit.get("videos", {}).get("medium") or {}
        if f.get("url"):
            out.append({"id": f"px-{hit['id']}", "url": f["url"],
                        "duration": hit.get("duration", 0), "w": f.get("width", 0)})
    return out


def _pexels(query):
    if not config.PEXELS_API_KEY:
        return []
    data = _get("https://api.pexels.com/videos/search",
                headers={"Authorization": config.PEXELS_API_KEY},
                params={"query": query, "per_page": 10, "orientation": "landscape"})
    out = []
    for v in data.get("videos", []):
        files = [f for f in v.get("video_files", [])
                 if f.get("file_type") == "video/mp4" and f.get("width", 0) >= 1280]
        if not files:
            continue
        best = max(files, key=lambda f: f.get("width", 0))
        out.append({"id": f"px2-{v['id']}", "url": best["link"],
                    "duration": v.get("duration", 0), "w": best.get("width", 0)})
    return out


SOURCES = [("pixabay", _pixabay), ("pexels", _pexels)]


def _search(query):
    if query in _search_cache:
        return _search_cache[query]
    results = []
    for name, fn in SOURCES:
        if name in _disabled:
            continue
        try:
            results += fn(query)
        except RateLimited:
            log.warning("%s rate limit reached; skipping it for the rest of this run", name)
            _disabled.add(name)
        except Exception as e:
            log.warning("%s failed for %r: %s", name, query, e)
    _search_cache[query] = results
    return results


def _pick(query, used):
    candidates = [c for c in _search(query) if c["id"] not in used and c["duration"] >= 1.5]
    candidates.sort(key=lambda c: c.get("w", 0), reverse=True)
    return candidates[0] if candidates else None


def _download(url, dest):
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)


def fetch_all(slices, plan):
    clip_dir = os.path.join(config.WORKDIR, "clips")
    os.makedirs(clip_dir, exist_ok=True)
    used, result = set(), {}

    for s in slices:
        query = plan[s["index"]]["query"]
        pick = _pick(query, used)
        if not pick:
            for fb in FALLBACK_QUERIES:
                pick = _pick(fb, used)
                if pick:
                    break
        if not pick:
            raise RuntimeError(f"No free clip found for line {s['index']} ({query})")

        used.add(pick["id"])
        dest = os.path.join(clip_dir, pick["id"] + ".mp4")
        if not os.path.exists(dest):
            _download(pick["url"], dest)
        result[s["index"]] = dest
    return result