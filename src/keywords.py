import logging
from .gemini import generate_json

log = logging.getLogger("rtm.keywords")
STYLES = ["beat", "fluid", "brand", "structural", "cinematic", "lyric", "mixed", "spin"]
MOTIONS = {"left_to_right", "right_to_left", "up", "down", "zoom_in", "static"}
BATCH = 40

STYLE_GUIDE = """
beat: punchy, energetic lines with big words that pop on each beat (action, urgency)
fluid: smooth lines that drift in the footage's direction (calm reflection)
brand: one key takeaway phrase with a bold outline (the main point)
structural: numbered points for steps, lists, or facts (explanations, tips)
cinematic: slow, serious, reflective lines in serif type (emotion, philosophy)
lyric: rhythmic lines with a word-by-word color sweep (poetic phrasing)
mixed: playful mix of fonts and colors (hooks, curiosity, surprise)
spin: one bold word that rotates (a single strong idea)
"""


def _ask(batch):
    prompt = (
        "You plan visuals for a faceless motivational YouTube video.\n"
        "For each line return a JSON array of items with:\n"
        '  "index": the line index,\n'
        '  "query": 1 or 2 concrete English keywords for stock video search (no names, no brands),\n'
        '  "motion": "left_to_right", "right_to_left", "up", "down", "zoom_in", or "static",\n'
        f'  "style": one of {STYLES}, chosen from this guide:\n{STYLE_GUIDE}\n'
        "Vary the styles. Return only the JSON array.\n\n"
        f"Lines: {batch}"
    )
    try:
        items = generate_json(prompt)
        return items if isinstance(items, list) else []
    except Exception as e:
        log.warning("Visual planning batch failed, using defaults: %s", e)
        return []


def plan_visuals(slices):
    lines = [{"index": s["index"], "text": s["text"]} for s in slices if s["text"]]
    items = []
    for i in range(0, len(lines), BATCH):
        items += _ask(lines[i:i + BATCH])

    plan = {}
    for it in items:
        try:
            idx = int(it["index"])
        except (KeyError, TypeError, ValueError):
            continue
        motion = it.get("motion", "static")
        style = it.get("style", "")
        plan[idx] = {
            "query": str(it.get("query", "cinematic motivation"))[:60].strip() or "cinematic motivation",
            "motion": motion if motion in MOTIONS else "static",
            "style": style if style in STYLES else None,
        }

    for s in slices:
        i = s["index"]
        entry = plan.setdefault(i, {"query": "cinematic motivation", "motion": "static", "style": None})
        if not entry["style"]:
            entry["style"] = STYLES[i % len(STYLES)]

    ordered = sorted(plan)
    for k in range(2, len(ordered)):
        cur = ordered[k]
        if plan[cur]["style"] == plan[ordered[k - 1]]["style"] == plan[ordered[k - 2]]["style"]:
            plan[cur]["style"] = next(s for s in STYLES if s != plan[cur]["style"])
    return plan