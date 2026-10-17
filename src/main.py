import logging
import os
import sys
from . import config, tts, transcribe, timeline, keywords, clips, typography, render, metadata, youtube, notify

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rtm")

def main():
    config.validate()
    topic = os.environ["TOPIC"].strip()
    script = os.environ["SCRIPT"].strip()
    chat_id = os.environ["CHAT_ID"].strip()
    W = config.WORKDIR
    os.makedirs(W, exist_ok=True)

    try:
        log.info("1/7 voiceover")
        voice = tts.synthesize(script, os.path.join(W, "voice.wav"))

        log.info("2/7 word timings")
        total = timeline.audio_duration(voice)
        words = transcribe.word_timings(voice)
        slices = timeline.build_slices(words, total)

        log.info("3/7 visual plan (%d lines)", len(slices))
        plan = keywords.plan_visuals(slices)

        log.info("4/7 stock clips")
        clip_paths = clips.fetch_all(slices, plan)

        log.info("5/7 captions")
        ass = typography.write_ass(slices, plan, os.path.join(W, "captions.ass"))

        log.info("6/7 render")
        out = os.path.join(W, "final.mp4")
        render.build(slices, clip_paths, plan, voice, ass, out)

        log.info("7/7 metadata + upload")
        meta = metadata.build(topic, script)
        publish_at = youtube.next_publish_slot() if config.SCHEDULE_MODE == "publish_at" else None
        video_id = youtube.upload(out, meta["titles"][0], meta["description"], meta["tags"], publish_at)

        titles = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(meta["titles"]))
        notify.send(chat_id,
            "Video uploaded as PRIVATE.\n"
            f"Studio: https://studio.youtube.com/video/{video_id}/edit\n\n"
            f"Title options:\n{titles}\n\n"
            "Next: review it, add the thumbnail, and schedule it in Studio.")
    except Exception as e:
        log.exception("Pipeline failed")
        notify.send(chat_id, f"Failed at this step: {str(e)[:500]}")
        sys.exit(1)

if __name__ == "__main__":
    main()