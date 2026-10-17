import re
from . import config
from .utils import strip_tags
from .keywords import CAPTION_RULES

W, H = config.VIDEO_W, config.VIDEO_H
CX, CY = W // 2, H // 2
WHITE = "&H00FFFFFF&"
YELLOW = "&H0000C8FF&"
RED = "&H000006E1&"
BLACK = "&H00000000&"
SANS = "Liberation Sans"
SERIF = "Liberation Serif"
CONDENSED = "DejaVu Sans Condensed"
MAX_WORDS = min(int(CAPTION_RULES.get("max_words_per_caption", 3)), 3)
MAX_CHARS = 18

HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Base,Liberation Sans,108,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,8,2,5,60,60,40,1

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


def _groups(words):
    out, cur = [], []
    for w in words:
        trial = " ".join(cur + [w])
        if cur and (len(cur) >= MAX_WORDS or len(trial) > MAX_CHARS):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return out


def _longest(g):
    return max(range(len(g)), key=lambda i: len(g[i]))


def _emph(g):
    hi = _longest(g)
    return " ".join("{\\c" + YELLOW + "}" + w + "{\\c" + WHITE + "}" if i == hi else w
                    for i, w in enumerate(g))


def _move(motion):
    d = 250
    if motion == "left_to_right":
        return f"\\move({CX - 500},{CY},{CX},{CY},0,{d})"
    if motion == "right_to_left":
        return f"\\move({CX + 500},{CY},{CX},{CY},0,{d})"
    if motion == "up":
        return f"\\move({CX},{CY + 200},{CX},{CY},0,{d})"
    if motion == "down":
        return f"\\move({CX},{CY - 200},{CX},{CY},0,{d})"
    return f"\\pos({CX},{CY})"


def _one(tags, text):
    return ["{" + tags + "}" + text]


UP = lambda g: " ".join(w.upper() for w in g)


# Each style returns a list of caption texts. Most return one; split and stack return several.

def punch(g, m, ms, n):
    return _one(f"\\an5\\pos({CX},{CY})\\fs148\\fscx70\\fscy70\\t(0,120,\\fscx100\\fscy100)",
                _emph([w.upper() for w in g]))


def slide(g, m, ms, n):
    return _one("\\an5" + _move(m) + "\\fs128", UP(g))


def outline(g, m, ms, n):
    return _one(f"\\an5\\pos({CX},{CY + 260})\\fs108\\bord18\\3c{RED}\\shad0", UP(g))


def flash(g, m, ms, n):
    return _one(f"\\an5\\pos({CX},{CY})\\fs188\\c{YELLOW}\\fscx80\\fscy80\\t(0,100,\\fscx100\\fscy100)", UP(g))


def drift(g, m, ms, n):
    font = SERIF if n % 2 else SANS
    italic = "\\i1" if font == SERIF else ""
    return _one(f"\\an5\\fn{font}\\fs118{italic}\\fad(180,120)"
                f"\\move({CX},{CY + 40},{CX},{CY - 20},0,{min(max(ms, 100), 600)})", " ".join(g))


def zoom(g, m, ms, n):
    return _one(f"\\an5\\pos({CX},{CY})\\fn{CONDENSED}\\fs120\\fscx150\\fscy150"
                f"\\t(0,{min(max(ms, 100), 400)},\\fscx100\\fscy100)", UP(g))


def typewriter(g, m, ms, n):
    # Approximation: each letter is revealed in sequence with a karaoke sweep.
    text = UP(g)
    letters = sum(1 for c in text if c != " ")
    cs = max(2, int(ms / 10 / max(letters, 1)))
    body = "".join(c if c == " " else "{\\kf" + str(cs) + "}" + c for c in text)
    return _one(f"\\an5\\pos({CX},{CY})\\fs120", body)


def glitch(g, m, ms, n):
    # Approximation: no real digital distortion in ASS, so the text jitters and gets a red edge.
    return _one(f"\\an5\\pos({CX},{CY})\\fs140\\c{YELLOW}\\bord4\\3c{RED}"
                "\\frz-2\\t(0,70,\\frz2)\\t(70,140,\\frz-1)\\t(140,220,\\frz0)", _emph([w.upper() for w in g]))


def shake(g, m, ms, n):
    # Approximation: rotation jitter.
    return _one(f"\\an5\\pos({CX},{CY})\\fs132"
                "\\frz-3\\t(0,60,\\frz3)\\t(60,120,\\frz-3)\\t(120,180,\\frz0)", UP(g))


def rise(g, m, ms, n):
    return _one(f"\\an5\\fs120\\fad(150,100)\\move({CX},{CY + 140},{CX},{CY},0,260)", UP(g))


def split(g, m, ms, n):
    half = max(1, len(g) // 2)
    a = " ".join(g[:half]).upper()
    b = " ".join(g[half:]).upper()
    out = [f"{{\\an6\\fs130\\move(-300,{CY},{CX - 40},{CY},0,220)}}{a}"]
    if b:
        out.append(f"{{\\an4\\fs130\\c{YELLOW}\\move({W + 300},{CY},{CX + 40},{CY},0,220)}}{b}")
    return out


def stack(g, m, ms, n):
    return [f"{{\\an5\\pos({CX},{CY - 120 + i * 110})\\fs120\\fad(120,80)}}{w.upper()}"
            for i, w in enumerate(g)]


def underline(g, m, ms, n):
    hi = _longest(g)
    parts = [("{\\u1}" + w + "{\\u0}") if i == hi else w for i, w in enumerate(g)]
    return _one(f"\\an5\\pos({CX},{CY})\\fs124", " ".join(p.upper() if "{" not in p else p for p in parts))


def highlight(g, m, ms, n):
    # Approximation: a bold yellow outline behind black text, since ASS has no per-word box.
    hi = _longest(g)
    parts = []
    for i, w in enumerate(g):
        if i == hi:
            parts.append("{\\1c" + BLACK + "\\3c" + YELLOW + "\\bord16}" + w.upper() + "{\\1c" + WHITE + "\\3c" + BLACK + "\\bord2}")
        else:
            parts.append(w.upper())
    return _one(f"\\an5\\pos({CX},{CY})\\fs130\\bord2", " ".join(parts))


def blur_in(g, m, ms, n):
    return _one(f"\\an5\\pos({CX},{CY})\\fs126\\blur8\\t(0,{min(max(ms, 200), 500)},\\blur0)", UP(g))


def word_by_word(g, m, ms, n):
    per = max(10, int(ms / 10 / len(g)))
    parts = ["{\\kf" + str(per) + "}" + w.upper() for w in g]
    return _one(f"\\an5\\pos({CX},{CY})\\fs118", " ".join(parts))


def drop(g, m, ms, n):
    return _one(f"\\an5\\fs150\\move({CX},{CY - 360},{CX},{CY},0,220)", UP(g))


def kinetic(g, m, ms, n):
    parts = []
    for i, w in enumerate(g):
        size, color = (138, YELLOW) if i % 2 == 0 else (110, WHITE)
        parts.append("{\\fs" + str(size) + "\\c" + color + "}" + w.upper())
    return _one(f"\\an5\\pos({CX},{CY})", " ".join(parts))


STYLE_FN = {
    "punch": punch, "slide": slide, "outline": outline, "flash": flash,
    "drift": drift, "zoom": zoom, "typewriter": typewriter, "glitch": glitch,
    "shake": shake, "rise": rise, "split": split, "stack": stack,
    "underline": underline, "highlight": highlight, "blur_in": blur_in,
    "drop": drop, "word_by_word": word_by_word, "kinetic": kinetic,
}


def write_ass(cuts, plan, path):
    lines = [HEADER]
    for c in cuts:
        words = [w for w in (_clean(x) for x in c["text"].split()) if w]
        if not words:
            continue
        p = plan.get(c["index"], {})
        fn = STYLE_FN.get(p.get("style"), punch)
        motion = p.get("motion", "static")

        groups = _groups(words)
        span = (c["end"] - c["start"]) / len(groups)
        for k, g in enumerate(groups):
            start = c["start"] + k * span
            end = c["end"] if k == len(groups) - 1 else start + span
            ms = int((end - start) * 1000)
            for text in fn(g, motion, ms, c["index"]):
                lines.append(_line(start, end, text))

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path