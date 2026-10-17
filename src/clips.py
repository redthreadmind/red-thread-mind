import logging
import os
import re
import time
import requests
from . import config, rights, character

log = logging.getLogger("rtm.clips")
MIN_CLIP_SECONDS = 2.0
PIXABAY_LICENSE_URL = "https://pixabay.com/service/license/"

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


def _normalize(hit, f):
    tags = hit.get("tags", "")
    return {
        "provider": "pixabay",
        "asset_id": f"px-{hit['id']}",
        "title": tags[:80],
        "url": f["url"],
        "source_page_url": hit.get("pageURL", ""),
        "license_url": PIXABAY_LICENSE_URL,
        "attribution_required": False,
        "duration": hit["duration"],
        "w": f["width"],
        "tags": tags,
    }


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
        log.warning("Pixabay rate limit reached; the rest of this run uses cached results only")
        _pixabay_disabled = True
        return []
    except Exception as e:
        log.warning("Pixabay failed for %r: %s", query, e)
        return []

    out = []
    for hit in data.get("hits", []):
        videos = hit.get("videos", {})
        f = videos.get("large") or videos.get("medium") or {}
        if not f.get("url") or f.get("width", 0) < 1280 or hit.get("duration", 0) < MIN_CLIP_SECONDS:
            continue
        asset = _normalize(hit, f)
        allowed, reason = rights.check(asset)
        if allowed:
            out.append(asset)
        else:
            log.warning("Skipped %s: %s", asset["asset_id"], reason)

    _search_cache[query] = out
    return out


def _words(text):
    return set(re.findall(r"[a-z]+", text.lower()))


def _score(clip, query):
    return len(_words(query) & _words(clip.get("tags", "")))


def _pick(query, used, strict, allow_reuse=False):
    cands = [c for c in _search(query) if allow_reuse or c["asset_id"] not in used]
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


def fetch_all(cuts, plan, presenter=None):
    """
    Return (paths, records).
    paths:   {cut_index: local clip path}
    records: one rights record per asset, for the manifest
    """
    presenter = presenter or set()
    clip_dir = os.path.join(config.WORKDIR, "clips")
    os.makedirs(clip_dir, exist_ok=True)

    used, paths, records = set(), {}, []
    seen_assets, used_starts = set(), []
    counts = {"presenter": 0, "exact": 0, "fallback": 0, "reused": 0}

    for c in cuts:
        idx = c["index"]

        # Presenter cuts come from the owner's own clip.
        if idx in presenter:
            dest = os.path.join(clip_dir, f"presenter-{idx:05d}.mp4")
            character.make_clip(c, dest, used_starts)
            asset = {
                "provider": "own",
                "asset_id": f"presenter-{idx:05d}",
                "title": "Presenter clip (owner-made)",
                "source_page_url": "",
                "license_url": rights.OWN_LICENSE,
                "attribution_required": False,
            }
            allowed, reason = rights.check(asset)
            if not allowed:
                raise RuntimeError(f"Presenter clip blocked: {reason}")
            records.append(rights.manifest_record(asset, allowed, reason))
            paths[idx] = dest
            counts["presenter"] += 1
            continue

        # Stock cuts: search, prefer unused relevant clips, then fall back.
        q = plan[idx]["query"]
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
            raise RuntimeError(f"No Pixabay clip found for cut {idx} ({q})")

        counts[label] += 1
        used.add(pick["asset_id"])

        if pick["asset_id"] not in seen_assets:
            seen_assets.add(pick["asset_id"])
            allowed, reason = rights.check(pick)
            records.append(rights.manifest_record(pick, allowed, reason))

        dest = os.path.join(clip_dir, pick["asset_id"] + ".mp4")
        if not os.path.exists(dest):
            _download(pick["url"], dest)
        paths[idx] = dest

    log.info("Footage: %d cuts, presenter %d, exact %d, fallback %d, reused %d",
             len(paths), counts["presenter"], counts["exact"],
             counts["fallback"], counts["reused"])
    return paths, records