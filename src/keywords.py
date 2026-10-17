import logging
from .gemini import generate_json

log = logging.getLogger("rtm.keywords")
MOTIONS = {"left_to_right", "right_to_left", "up", "down", "zoom_in", "static"}

def plan_visuals(slices):
    payload = [{"index": s["index"], "text": s["text"]} for s in slices if s["text"]]
    prompt = (
        "You choose stock footage for a faceless motivational YouTube video.\n"
        "For each line, return a JSON array. Each item has:\n"
        '  "index": the line index,\n'
        '  "query": 1 or 2 concrete English keywords for stock video search '
        "(visual, no names, no brand names),\n"
        '  "motion": the camera or subject movement that footage most naturally shows: '
        '"left_to_right", "right_to_left", "up", "down", "zoom_in", or "static".\n'
        "Return only the JSON array.\n\n"
        f"Lines: {payload}"
    )
    try:
        items = generate_json(prompt)
    except Exception as e:
        log.warning("Keyword planning failed, using defaults: %s", e)
        items = []

    plan = {}
    for it in items:
        try:
            idx = int(it["index"])
        except (KeyError, TypeError, ValueError):
            continue
        motion = it.get("motion", "static")
        plan[idx] = {
            "query": str(it.get("query", "cinematic motivation"))[:60].strip() or "cinematic motivation",
            "motion": motion if motion in MOTIONS else "static",
        }

    for s in slices:
        plan.setdefault(s["index"], {"query": "cinematic motivation", "motion": "static"})
    return plan