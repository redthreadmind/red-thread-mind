import wave
from . import config


def audio_duration(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def build_cuts(words, total):
    """Split the voiceover into evenly sized cuts of about CUT_SECONDS each."""
    n = max(1, round(total / config.CUT_SECONDS))
    size = total / n
    cuts = []
    for i in range(n):
        start = i * size
        end = total if i == n - 1 else (i + 1) * size
        cw = [w for w in words if start <= w["start"] < end]
        text = " ".join(w["word"].strip() for w in cw).strip()
        cuts.append({"index": i, "start": start, "end": end, "text": text})
    return cuts