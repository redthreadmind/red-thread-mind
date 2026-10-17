import os
from . import config
from .utils import run_ffmpeg, first_file, ff_path

W, H, FPS = config.VIDEO_W, config.VIDEO_H, config.FPS

def make_segment(src, dst, dur):
    """Crop/scale one clip to exactly `dur` seconds, no audio."""
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},setsar=1,fps={FPS},"
          f"tpad=stop_mode=clone:stop_duration={dur:.3f}")
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

def mux(base, ass_path, voice, sfx_times, out_path):
    args = ["-i", os.path.abspath(base), "-i", os.path.abspath(voice)]
    idx = 2
    fc = [f"[0:v]ass={ff_path(ass_path)}[v]", "[1:a]volume=1.0[va]"]
    mix = ["[va]"]

    music = first_file("assets/music", (".mp3", ".wav", ".m4a"))
    if music:
        args += ["-stream_loop", "-1", "-i", music]
        fc.append(f"[{idx}:a]volume=0.12[ma]")
        mix.append("[ma]")
        idx += 1

    sfx = first_file("assets/sfx", (".wav", ".mp3")) if sfx_times else None
    if sfx:
        k = min(len(sfx_times), 20)
        args += ["-i", sfx]
        fc.append(f"[{idx}:a]asplit={k}" + "".join(f"[s{j}]" for j in range(k)))
        for j, t in enumerate(sfx_times[:k]):
            ms = int(t * 1000)
            fc.append(f"[s{j}]adelay={ms}|{ms},volume=0.5[sf{j}]")
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

def build(slices, clip_paths, plan, voice, ass_path, out_path):
    segments = []
    for s in slices:
        src = clip_paths[s["index"]]
        seg = os.path.join(config.WORKDIR, f"seg_{s['index']:04d}.mp4")
        make_segment(src, seg, s["end"] - s["start"])
        os.remove(src)  # free disk space on the runner
        segments.append(seg)

    base = os.path.join(config.WORKDIR, "base.mp4")
    concat(segments, base)

    # Whoosh SFX at each point where the motion direction changes.
    sfx_times = [
        s["start"] for s in slices[1:]
        if plan[s["index"]]["motion"] != plan[s["index"] - 1]["motion"]
    ]
    mux(base, ass_path, voice, sfx_times, out_path)
    return out_path