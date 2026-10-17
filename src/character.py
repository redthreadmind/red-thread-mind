import logging
import os
import random
import subprocess
from .utils import run_ffmpeg

log = logging.getLogger("rtm.character")

CLIP = os.path.join("assets", "character", "presenter.mp4")
EVERY_N_SPOKEN_CUTS = 5   # about 1 in 5 spoken cuts
MIN_START_GAP = 1.5       # seconds between the start points of two slices


def available():
    return os.path.exists(CLIP)


def duration():
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", os.path.abspath(CLIP)],
        capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def plan(cuts):
    """Return the set of cut indexes that show the presenter."""
    spoken = [c["index"] for c in cuts if c["text"]]
    if not spoken:
        return set()
    chosen = {spoken[0], spoken[-1]}   # hook and closing
    chosen |= {idx for k, idx in enumerate(spoken) if k % EVERY_N_SPOKEN_CUTS == 0}
    return chosen


def make_clip(cut, dst, used_starts, rng=None):
    """Cut a slice of the presenter clip for one cut. Slices never start too close to each other."""
    rng = rng or random.Random()
    length = cut["end"] - cut["start"]
    total = duration()
    length = min(length, total)

    start = 0.0
    for _ in range(30):
        candidate = rng.uniform(0, max(0.0, total - length))
        if all(abs(candidate - s) >= MIN_START_GAP for s in used_starts):
            start = candidate
            break
    used_starts.append(start)

    run_ffmpeg([
        "-ss", f"{start:.3f}", "-t", f"{length:.3f}",
        "-i", os.path.abspath(CLIP),
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        os.path.abspath(dst),
    ])
    log.info("Presenter cut %d uses %.2fs from %.2fs", cut["index"], length, start)
    return dst