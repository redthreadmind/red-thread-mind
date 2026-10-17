import re
from . import config
from .utils import strip_tags

W, H = config.VIDEO_W, config.VIDEO_H
WHITE = "&H00FFFFFF&"
YELLOW = "&H0000C8FF&"
RED = "&H000006E1&"
CX, CY = W // 2, H // 2

HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Base,Liberation Sans,120,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,8,2,5,60,60,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""


def _t(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = min(99, int(round((sec - int(sec)) * 100)))
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _clean(word):
    return re.sub(r"[{}\\]", "", strip_tags(word)).strip()


def _line(start, end, text):
    end = max(end, start + 0.08)
    return f"Dialogue: 0,{_t(start)},{_t(end)},Base,,0,0,0,,{text}"


def _chunks(words, n=3):
    return [words[i:i + n] for i in range(0, len(words), n)]


def _emph(group):
    hi = max(range(len(group)), key=lambda i: len(group[i]))
    parts = []
    for i, w in enumerate(group):
        if i == hi:
            parts.append("{\\c" + YELLOW + "}" + w + "{\\c" + WHITE + "}")
        else:
            parts.append(w)
    return " ".join(parts)


def _move(motion):
    if motion == "left_to_right":
        return f"\\move({CX - 500},{CY},{CX},{CY},0,250)"
    if motion == "right_to_left":
        return f"\\move({CX + 500},{CY},{CX},{CY},0,250)"
    if motion == "up":
        return f"\\move({CX},{CY + 200},{CX},{CY},0,250)"
    if motion == "down":
        return f"\\move({CX},{CY - 200},{CX},{CY},0,250)"
    return f"\\pos({CX},{CY})"


def punch(group, motion):
    tags = f"\\an5\\pos({CX},{CY})\\fs150\\fscx70\\fscy70\\t(0,120,\\fscx100\\fscy100)"
    return "{" + tags + "}" + _emph([w.upper() for w in group])


def slide(group, motion):
    tags = "\\an5" + _move(motion) + "\\fs130"
    return "{" + tags + "}" + " ".join(w.upper() for w in group)


def outline(group, motion):
    tags = f"\\an5\\pos({CX},{CY + 260})\\fs110\\bord20\\3c{RED}\\shad0"
    return "{" + tags + "}" + " ".join(w.upper() for w in group)


def flash(group, motion):
    tags = (f"\\an5\\pos({CX},{CY})\\fs190\\c{YELLOW}"
            "\\fscx80\\fscy80\\t(0,100,\\fscx100\\fscy100)")
    return "{" + tags + "}" + " ".join(w.upper() for w in group)


STYLE_FN = {"punch": punch, "slide": slide, "outline": outline, "flash": flash}


def write_ass(cuts, plan, path):
    """One caption event per group of up to 3 words, times set so events never overlap."""
    lines = [HEADER]
    for c in cuts:
        words = [w for w in (_clean(x) for x in c["text"].split()) if w]
        if not words:
            continue
        p = plan.get(c["index"], {})
        fn = STYLE_FN.get(p.get("style"), punch)
        motion = p.get("motion", "static")

        groups = _chunks(words, 3)
        span = (c["end"] - c["start"]) / len(groups)
        for k, g in enumerate(groups):
            start = c["start"] + k * span
            end = c["end"] if k == len(groups) - 1 else start + span
            lines.append(_line(start, end, fn(g, motion)))

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path