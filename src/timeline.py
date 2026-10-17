import math
import wave
from . import config

def audio_duration(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()

def build_slices(words, total):
    """Split the voiceover into fixed 3-second slices, each with the words spoken in it."""
    step = config.SLICE_SECONDS
    slices = []
    for i in range(math.ceil(total / step)):
        start = i * step
        end = min((i + 1) * step, total)
        text = " ".join(w["word"] for w in words if start <= w["start"] < end)
        slices.append({"index": i, "start": start, "end": end, "text": text.strip()})
    return slices