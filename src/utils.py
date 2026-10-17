import glob
import os
import re
import subprocess

TAG_RE = re.compile(r"<[^>]+>")

def strip_tags(text):
    """Remove <expression> tags so they never reach captions."""
    return TAG_RE.sub("", text).strip()

def run_ffmpeg(args):
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + r.stderr[-1500:])

def first_file(folder, exts):
    for ext in exts:
        found = sorted(glob.glob(os.path.join(folder, f"*{ext}")))
        if found:
            return os.path.abspath(found[0])
    return None

def ff_path(path):
    """Escape a path for use inside an ffmpeg filter graph (works on Windows too)."""
    p = os.path.abspath(path).replace("\\", "/")
    return p.replace(":", "\\:")