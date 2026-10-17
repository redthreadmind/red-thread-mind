import logging
from .gemini import generate_json

log = logging.getLogger("rtm.keywords")
STYLES = [
    "punch",
    "slide",
    "outline",
    "flash",
    "drift",
    "zoom",
    "typewriter",
    "glitch",
    "shake",
    "rise",
    "split",
    "stack",
    "underline",
    "highlight",
    "blur_in",
    "drop",
    "word_by_word",
    "kinetic"
]

MOTIONS = {
    "left_to_right",
    "right_to_left",
    "up",
    "down",
    "zoom_in",
    "zoom_out",
    "static",
    "bounce",
    "rotate_in",
    "shake",
    "fade_in",
    "blur_to_sharp"
}
BATCH = 60

GUIDE = """
punch: One or two bold words bounce in with impact.
Use for commands, powerful statements, and verbal punches.

slide: Words travel horizontally with the footage direction.
Use for running, driving, movement, and forward momentum.

outline: A short phrase appears inside a red outlined box.
Use for the single most important lesson in a scene.

flash: One large yellow word appears instantly.
Use sparingly for shock, warnings, and emotional emphasis.

drift: Elegant serif and clean sans-serif words rise gently.
Use for reflection, personal truths, and quieter moments.

zoom: Condensed bold words snap in from an oversized scale.
Use for urgency, challenges, and direct confrontations.

typewriter: Letters appear progressively like a typing machine.
Use for inner thoughts, realizations, and deliberate statements.

glitch: Text briefly distorts with digital interference.
Use for hard truths, disruption, and sudden revelations.

shake: Text vibrates briefly before settling into place.
Use for anger, pressure, and aggressive commands.

rise: Text moves upward from below with controlled easing.
Use for progress, resilience, and overcoming obstacles.

split: Two words or phrases enter from opposite directions.
Use for contrasts like excuses versus action.

stack: Two to four short words build into a vertical arrangement.
Use for memorable statements and rhythmic narration.

underline: A line draws beneath a selected word or phrase.
Use for emphasis without overwhelming the footage.

highlight: A single key word receives a solid color background.
Use for lessons, important nouns, and actionable takeaways.

blur_in: Text transitions from blurred to crisp and readable.
Use for clarity, realizations, and moments of understanding.

drop: Bold text drops into place with a weighted landing.
Use for commands, declarations, and decisive moments.

word_by_word: Words appear sequentially, synchronized to speech.
Use for longer statements and carefully paced narration.

kinetic: Words change scale, position, and emphasis rhythmically.
Use for high-energy passages, but preserve readability.
"""
CAPTION_RULES = {
    "max_words_per_caption": 3,
    "max_lines": 2,
    "min_duration": 0.45,
    "max_duration": 2.5,
    "max_emphasis_words": 2,
    "avoid_consecutive_same_style": True,
    "avoid_consecutive_same_motion": True,
    "reserve_flash_for_impact": True,
    "reserve_glitch_for_rare_moments": True,
    "prioritize_readability": True,
    "sync_to_spoken_words": True,
}

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
        f'  "motion": one of {sorted(MOTIONS)},\n'
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