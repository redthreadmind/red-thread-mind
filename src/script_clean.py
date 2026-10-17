import re

DROP_LABELS = re.compile(
    r"^\s*(visual|visuals|b-?roll|text|text overlay|overlay|kinetic|sfx|sound|"
    r"sound design|music|note|cue|shot|camera|on.?screen)\b[^:]*:", re.I)

KEEP_LABELS = re.compile(r"^\s*(hook|voice|voiceover|narration|vo)\b[^:]*:\s*", re.I)

VO_HEADING = re.compile(r"^\s*(voiceover|voice over|narration|spoken script)\s*:?\s*$", re.I)

END_HEADING = re.compile(r"^\s*(cue sheet|visual direction|sound design|kinetic typography)\b", re.I)

# Square and round brackets are production notes. Angle brackets <...> are kept: they are expression tags.
BRACKETS = re.compile(r"\[[^\]]*\]|\([^)]*\)")
MARKDOWN = re.compile(r"[*_`#|]+")
BULLET = re.compile(r"^\s*([-•]|\d+[.)])\s+")


def clean_script(raw):
    lines = raw.replace("\r", "").split("\n")

    starts = [i for i, l in enumerate(lines) if VO_HEADING.match(l)]
    if starts:
        start = starts[0] + 1
        end = len(lines)
        for j in range(start, len(lines)):
            if END_HEADING.match(lines[j]):
                end = j
                break
        lines = lines[start:end]

    out = []
    for line in lines:
        if DROP_LABELS.match(line):
            continue
        line = KEEP_LABELS.sub("", line)
        line = BRACKETS.sub("", line)
        line = MARKDOWN.sub("", line)
        line = BULLET.sub("", line)
        line = " ".join(line.split())
        if line:
            out.append(line)
    return "\n\n".join(out)