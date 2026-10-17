import difflib
import hashlib
import json
import os
import random
import re
from datetime import datetime, timedelta, timezone

HISTORY_DIR = "history"
LOG_PATH = os.path.join(HISTORY_DIR, "log.json")
MAX_SIMILARITY = 0.20      # share of 5-word phrases shared with an earlier script
MAX_PER_WEEK = 3
TITLE_SIMILAR = 0.80
KEEP_ENTRIES = 100

ORDER = ["story", "lessons", "myth", "challenge"]

# Music tags must match Jamendo tags. Check that each returns results.
FORMATS = {
    "story": {
        "cut": (1.5, 1.9), "music": "ambient",
        "styles": ["drift", "blur_in", "typewriter", "rise", "underline", "word_by_word"],
    },
    "lessons": {
        "cut": (1.3, 1.6), "music": "cinematic",
        "styles": ["stack", "split", "outline", "underline", "highlight", "slide"],
    },
    "myth": {
        "cut": (1.1, 1.4), "music": "dark",
        "styles": ["glitch", "blur_in", "zoom", "typewriter", "flash"],
    },
    "challenge": {
        "cut": (1.0, 1.3), "music": "epic",
        "styles": ["punch", "zoom", "flash", "shake", "drop", "kinetic", "slide"],
    },
}


def load_log():
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_log(entries):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries[-KEEP_ENTRIES:], f, indent=1)


def shingles(text, n=5):
    words = re.findall(r"[a-z0-9']+", text.lower())
    grams = {" ".join(words[i:i + n]) for i in range(max(0, len(words) - n + 1))}
    return {hashlib.md5(g.encode()).hexdigest()[:10] for g in grams}


def check_originality(script, history):
    mine = shingles(script)
    best, match = 0.0, ""
    for e in history:
        theirs = set(e.get("shingles", []))
        if not mine or not theirs:
            continue
        score = len(mine & theirs) / len(mine | theirs)
        if score > best:
            best, match = score, e.get("title", "")
    return best <= MAX_SIMILARITY, best, match


def _parse(ts):
    return datetime.fromisoformat(ts)


def limit_wait(history):
    """Return the date the next upload is allowed, or '' if under the weekly limit."""
    now = datetime.now(timezone.utc)
    recent = sorted(_parse(e["date"]) for e in history
                    if "date" in e and _parse(e["date"]) > now - timedelta(days=7))
    if len(recent) < MAX_PER_WEEK:
        return ""
    return (recent[len(recent) - MAX_PER_WEEK] + timedelta(days=7)).strftime("%Y-%m-%d")


def recent_titles(history):
    return [e.get("title", "") for e in history[-30:] if e.get("title")]


def pick_title(titles, recent):
    for t in titles:
        if all(difflib.SequenceMatcher(None, t.lower(), r.lower()).ratio() < TITLE_SIMILAR
               for r in recent):
            return t
    return titles[0]


def apply_format(history, topic):
    name = ORDER[len(history) % len(ORDER)]
    seed_src = f"{topic}|{datetime.now(timezone.utc).isoformat()}"
    rng = random.Random(int(hashlib.md5(seed_src.encode()).hexdigest()[:8], 16))
    return name, FORMATS[name], rng


def grade_for(rng):
    contrast = round(rng.uniform(1.05, 1.18), 2)
    saturation = round(rng.uniform(1.0, 1.3), 2)
    vignette = rng.choice([4, 5, 6])
    tint = rng.choice([
        "",
        ",colorbalance=rs=0.06:bs=-0.04",
        ",colorbalance=rs=-0.04:bs=0.06",
    ])
    return f"eq=contrast={contrast}:saturation={saturation}:brightness=-0.02{tint},vignette=PI/{vignette}"


def make_entry(topic, title, fmt_name, script, video_id):
    return {
        "date": datetime.now(timezone.utc).isoformat(),
        "topic": topic,
        "title": title,
        "format": fmt_name,
        "video_id": video_id,
        "shingles": sorted(shingles(script)),
    }