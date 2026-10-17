import re
from . import config
from .utils import strip_tags

W, H = config.VIDEO_W, config.VIDEO_H
WORDS_PER_LINE = 4

HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Kinetic,Liberation Sans,120,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,2,0,1,7,3,5,80,80,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""

def _time(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = int(round((sec - int(sec)) * 100))
    if cs == 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def _motion_tag(motion, dur_ms):
    cx, cy, d = W // 2, H // 2, 800
    if motion == "left_to_right":
        return f"\\move({cx - d // 2},{cy},{cx + d // 2},{cy},0,{dur_ms})"
    if motion == "right_to_left":
        return f"\\move({cx + d // 2},{cy},{cx - d // 2},{cy},0,{dur_ms})"
    if motion == "up":
        return f"\\move({cx},{cy + 300},{cx},{cy - 300},0,{dur_ms})"
    if motion == "down":
        return f"\\move({cx},{cy - 300},{cx},{cy + 300},0,{dur_ms})"
    if motion == "zoom_in":
        return f"\\pos({cx},{cy})\\t(0,{dur_ms},\\fscx115\\fscy115)"
    return f"\\pos({cx},{cy})"

def _highlight(words):
    hi = max(range(len(words)), key=lambda i: len(words[i]))
    parts = []
    for i, w in enumerate(words):
        t = w.upper()
        if i == hi:
            parts.append("{\\c&H000000FF&}" + t + "{\\c&H00FFFFFF&}")
        else:
            parts.append(t)
    return " ".join(parts)

def write_ass(slices, plan, path):
    lines = [HEADER]
    for s in slices:
        words = [re.sub(r"[{}\\]", "", strip_tags(w)) for w in s["text"].split()]
        words = [w for w in words if w]
        if not words:
            continue

        motion = plan.get(s["index"], {}).get("motion", "static")
        chunks = [words[i:i + WORDS_PER_LINE] for i in range(0, len(words), WORDS_PER_LINE)]
        span = (s["end"] - s["start"]) / len(chunks)

        for k, chunk in enumerate(chunks):
            start = s["start"] + k * span
            end = start + span
            dur_ms = int(round((end - start) * 1000))
            pop = "\\fscx70\\fscy70\\t(0,150,\\fscx100\\fscy100)" if motion != "zoom_in" else ""
            override = "{" + _motion_tag(motion, dur_ms) + pop + "}"
            lines.append(
                f"Dialogue: 0,{_time(start)},{_time(end)},Kinetic,,0,0,0,,"
                + override + _highlight(chunk)
            )

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path