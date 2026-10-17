import logging
import os
from . import config
from .utils import run_ffmpeg, ff_path

log = logging.getLogger("rtm.render")
W, H, FPS = config.VIDEO_W, config.VIDEO_H, config.FPS
GRADE = "eq=contrast=1.12:saturation=1.18:brightness=-0.02,vignette=PI/5"
MAX_SFX = 60


def make_segment(src, dst, dur):
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
          f"fps={FPS},{GRADE},tpad=stop_mode=clone:stop_duration={dur:.3f}")
    run_ffmpeg(["-i", os.path.abspath(src), "-vf", vf, "-t", f"{dur:.3f}", "-an",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-pix_fmt", "yuv420p", os.path.abspath(dst)])


def concat(segments, out_path):
    list_file = os.path.join(config.WORKDIR, "concat.txt")
    with open(list_file, "w") as f:
        for s in segments:
            f.write(f"file '{os.path.abspath(s)}'\n")
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", os.path.abspath(list_file),
                "-c", "copy", os.path.abspath(out_path)])


def _sfx_times(cuts, plan):
    """Play a whoosh where the caption style changes, capped at MAX_SFX."""
    times = [c["start"] for prev, c in zip(cuts, cuts[1:])
             if plan[c["index"]]["style"] != plan[prev["index"]]["style"]]
    if len(times) > MAX_SFX:
        step = len(times) / MAX_SFX
        times = [times[int(i * step)] for i in range(MAX_SFX)]
    return times


def mux(base, ass_path, voice, music, sfx, sfx_times, out_path):
    args = ["-i", os.path.abspath(base), "-i", os.path.abspath(voice)]
    fc = [f"[0:v]ass={ff_path(ass_path)}[v]", "[1:a]volume=1.0[va]"]
    mix = ["[va]"]
    idx = 2

    if music:
        args += ["-stream_loop", "-1", "-i", os.path.abspath(music)]
        fc.append(f"[{idx}:a]volume=0.10[ma]")
        mix.append("[ma]")
        idx += 1

    if sfx and sfx_times:
        k = len(sfx_times)
        args += ["-i", os.path.abspath(sfx)]
        fc.append(f"[{idx}:a]asplit={k}" + "".join(f"[s{j}]" for j in range(k)))
        for j, t in enumerate(sfx_times):
            ms = int(t * 1000)
            fc.append(f"[s{j}]adelay={ms}|{ms},volume=0.45[sf{j}]")
            mix.append(f"[sf{j}]")

    fc.append("".join(mix) + f"amix=inputs={len(mix)}:duration=first:"
                             "dropout_transition=0:normalize=0[a]")

    args += ["-filter_complex", ";".join(fc),
             "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k",
             "-shortest", "-movflags", "+faststart",
             os.path.abspath(out_path)]
    run_ffmpeg(args)


def build(cuts, clip_paths, plan, voice, ass_path, music, sfx, out_path):
    segments = []
    for c in cuts:
        seg = os.path.join(config.WORKDIR, f"seg_{c['index']:05d}.mp4")
        make_segment(clip_paths[c["index"]], seg, c["end"] - c["start"])
        segments.append(seg)

    base = os.path.join(config.WORKDIR, "base.mp4")
    concat(segments, base)
    for s in segments:
        os.remove(s)

    mux(base, ass_path, voice, music, sfx, _sfx_times(cuts, plan), out_path)
    log.info("Render complete: %s", out_path)
    return out_path