import re
from . import config
from .utils import strip_tags

W, H = config.VIDEO_W, config.VIDEO_H
SANS = "Liberation Sans"
SERIF = "Liberation Serif"

# ASS colours are written as &HAABBGGRR&
WHITE = "&H00FFFFFF&"
YELLOW = "&H0000C8FF&"   # #FFC800
RED = "&H000006E1&"      # #E10600
TEAL = "&H00AA9A1B&"     # #1B9AAA
MIX = [WHITE, YELLOW, RED, TEAL]

HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Base,{SANS},110,{WHITE},{YELLOW},&H00000000&,&H80000000&,-1,0,0,0,100,100,0,0,1,6,2,5,80,80,40,1

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
    end = max(end, start + 0.1)
    return f"Dialogue: 0,{_t(start)},{_t(end)},Base,,0,0,0,,{text}"


def _chunks(items, n):
    return [items[i:i + n] for i in range(0, len(items), n)]


def _tag(tags, text):
    return "{" + tags + "}" + text


def beat(words, hi, motion):
    out = []
    for i, w in enumerate(words):
        end = words[i + 1]["start"] if i + 1 < len(words) else hi
        color = YELLOW if i % 2 == 0 else WHITE
        tags = (f"\\an5\\pos({W // 2},{H // 2})\\fs190\\fscx150\\fscy150"
                f"\\c{color}\\t(0,120,\\fscx100\\fscy100)")
        out.append(_line(w["start"], end, _tag(tags, _clean(w["word"]).upper())))
    return out


def fluid(words, hi, motion):
    # Text starts on the side the footage is moving from, then travels with it.
    dx, dy = {
        "left_to_right": (-160, 0),
        "right_to_left": (160, 0),
        "up": (0, 120),
        "down": (0, -120),
    }.get(motion, (0, 80))
    x, y = W // 2, H // 2
    out = []
    groups = _chunks(words, 4)
    for gi, g in enumerate(groups):
        start = g[0]["start"]
        end = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else hi
        ms = int((end - start) * 1000)
        tags = (f"\\an5\\move({x + dx},{y + dy},{x},{y},0,{min(350, ms)})"
                f"\\fad(200,200)\\fs110\\c{WHITE}\\blur1")
        out.append(_line(start, end, _tag(tags, " ".join(_clean(w["word"]) for w in g))))
    return out


def brand(words, hi, motion):
    text = " ".join(_clean(w["word"]) for w in words).upper()
    tags = (f"\\an5\\pos({W // 2},{H // 2})\\fs96\\c{WHITE}"
            f"\\bord24\\3c{RED}\\shad0\\fad(150,150)")
    return [_line(words[0]["start"], hi, _tag(tags, text))]


def structural(words, hi, motion):
    out = []
    rows = _chunks(words, 3)[:4]
    for n, row in enumerate(rows):
        start = row[0]["start"]
        end = rows[n + 1][0]["start"] if n + 1 < len(rows) else hi
        y = H // 2 - 200 + n * 130
        number = f"{{\\c{YELLOW}}}{n + 1:02d}{{\\c{WHITE}}}"
        text = " ".join(_clean(w["word"]).upper() for w in row)
        tags = f"\\an4\\pos(180,{y})\\fs84\\fad(150,0)"
        out.append(_line(start, end, _tag(tags, number + "  " + text)))
    return out


def cinematic(words, hi, motion):
    text = " ".join(_clean(w["word"]) for w in words)
    ms = int((hi - words[0]["start"]) * 1000)
    tags = (f"\\an2\\pos({W // 2},{H - 140})\\fn{SERIF}\\fs92\\i1\\fsp36"
            f"\\fad(700,500)\\t(0,{ms},\\fsp4\\fscx104\\fscy104)")
    return [_line(words[0]["start"], hi, _tag(tags, text))]


def lyric(words, hi, motion):
    parts = []
    for w in words:
        cs = max(1, int(round((w["end"] - w["start"]) * 100)))
        parts.append("{\\k" + str(cs) + "}" + _clean(w["word"]))
    tags = f"\\an2\\pos({W // 2},{H - 260})\\fs104\\1c{YELLOW}\\2c{WHITE}\\b1"
    return [_line(words[0]["start"], hi, _tag(tags, " ".join(parts)))]


def mixed(words, hi, motion):
    out = []
    groups = _chunks(words, 4)
    for gi, g in enumerate(groups):
        start = g[0]["start"]
        end = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else hi
        pieces = []
        for i, w in enumerate(g):
            font = SERIF if i % 2 == 1 else SANS
            italic = 1 if i % 3 == 2 else 0
            color = MIX[(gi * 4 + i) % len(MIX)]
            size = 120 if i == 0 else 92
            pieces.append(f"{{\\fn{font}\\i{italic}\\c{color}\\fs{size}}}{_clean(w['word'])}")
        tags = f"\\an5\\pos({W // 2},{H // 2})\\fad(120,80)"
        out.append(_line(start, end, _tag(tags, " ".join(pieces) + "{\\r}")))
    return out


def spin(words, hi, motion):
    out = []
    for i, w in enumerate(words):
        end = words[i + 1]["start"] if i + 1 < len(words) else hi
        ms = max(int((end - w["start"]) * 1000), 200)
        tags = (f"\\an5\\pos({W // 2},{H // 2})\\fs220\\c{YELLOW}"
                f"\\t(0,{ms},\\frz360)")
        out.append(_line(w["start"], end, _tag(tags, _clean(w["word"]).upper())))
    return out


STYLES = {
    "beat": beat,
    "fluid": fluid,
    "brand": brand,
    "structural": structural,
    "cinematic": cinematic,
    "lyric": lyric,
    "mixed": mixed,
    "spin": spin,
}


def write_ass(words, slices, plan, path):
    lines = [HEADER]
    for s in slices:
        sw = [w for w in words if s["start"] <= w["start"] < s["end"] and _clean(w["word"])]
        if not sw:
            continue
        p = plan.get(s["index"], {})
        fn = STYLES.get(p.get("style"), mixed)
        lines += fn(sw, s["end"], p.get("motion", "static"))

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path