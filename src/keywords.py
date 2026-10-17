import logging
from .gemini import generate_json

log = logging.getLogger("rtm.keywords")
STYLES = ["punch", "slide", "outline", "flash"]
MOTIONS = {"left_to_right", "right_to_left", "up", "down", "zoom_in", "static"}
BATCH = 60

GUIDE = """
punch: one or two bold words that pop in with a bounce (commands, strong statements)
slide: words that travel in the direction the footage moves (action, movement)
outline: a short phrase in a red-outlined box (the single key idea)
flash: one large yellow word (shock, emphasis)
"""


def _ask(batch):
    prompt = (
        "You choose stock video for a fast-cut motivational YouTube video.\n"
        "Each line is about 1.4 seconds of narration. For each line return a JSON array with:\n"
        '  "index": the line index,\n'
        '  "query": 1 to 3 English words naming what a camera can film for this exact line. '
        "Use the most concrete visible noun or action from the line, in the same words where "
        'possible. Examples: "run" becomes "man running", "wake up" becomes "alarm clock morning", '
        '"push" becomes "man pushing wall". Never use abstract words such as discipline, '
        "motivation, success, mindset, focus, or growth.\n"
        '  "motion": "left_to_right", "right_to_left", "up", "down", "zoom_in", or "static",\n'
        f'  "style": one of {STYLES}, chosen from this guide:\n{GUIDE}\n'
        "Vary the styles. Return only the JSON array.\n\n"
        f"Lines: {batch}"
    )
    try:
        items = generate_json(prompt)
        return items if isinstance(items, list) else []
    except Exception as e:
        log.warning("Visual planning batch failed, using defaults: %s", e)
        return []


def plan_visuals(cuts):
    lines = [{"index": c["index"], "text": c["text"]} for c in cuts if c["text"]]
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
            "query": str(it.get("query", "cinematic motivation"))[:50].strip() or "cinematic motivation",
            "motion": motion if motion in MOTIONS else "static",
            "style": style if style in STYLES else None,
        }

    for c in cuts:
        i = c["index"]
        entry = plan.setdefault(i, {"query": "cinematic motivation", "motion": "static", "style": None})
        if not entry["style"]:
            entry["style"] = STYLES[i % len(STYLES)]

    ordered = sorted(plan)
    for k in range(2, len(ordered)):
        cur = ordered[k]
        if plan[cur]["style"] == plan[ordered[k - 1]]["style"] == plan[ordered[k - 2]]["style"]:
            plan[cur]["style"] = next(s for s in STYLES if s != plan[cur]["style"])
    return plan