import logging
import os
import sys
from . import config, tts, transcribe, timeline, keywords, clips, typography, render, metadata, youtube, notify

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rtm")


def say(chat_id, text):
    try:
        notify.send(chat_id, text)
    except Exception as e:
        log.warning("Telegram update failed: %s", e)


def main():
    config.validate()
    topic = os.environ["TOPIC"].strip()
    script = os.environ["SCRIPT"].strip()
    chat_id = os.environ["CHAT_ID"].strip()
    W = config.WORKDIR
    os.makedirs(W, exist_ok=True)

    try:
        log.info("1/7 voiceover")
        say(chat_id, "1/7 Generating voiceover...")
        voice = tts.synthesize(script, os.path.join(W, "voice.wav"))
        total = timeline.audio_duration(voice)
        say(chat_id, f"Voiceover ready: {total / 60:.1f} minutes.")

        log.info("2/7 word timings")
        words = transcribe.word_timings(voice)
        slices = timeline.build_slices(words, total)
        say(chat_id, f"2/7 Timing {len(slices)} lines...")

        log.info("3/7 visual plan")
        plan = keywords.plan_visuals(slices)
        say(chat_id, "3/7 Planned visuals and caption styles.")

        log.info("4/7 stock clips")
        clip_paths = clips.fetch_all(slices, plan)
        say(chat_id, "4/7 Stock clips downloaded.")

        log.info("5/7 captions")
        ass = typography.write_ass(words, slices, plan, os.path.join(W, "captions.ass"))

        log.info("6/7 render")
        say(chat_id, "5/7 Rendering the video. This is the slow step.")
        out = os.path.join(W, "final.mp4")
        render.build(slices, clip_paths, plan, voice, ass, out)

        if os.environ.get("DRY_RUN") == "true":
            say(chat_id, "DRY RUN finished. Nothing was uploaded.")
            log.info("DRY RUN: stopping before upload. Output: %s", out)
            return

        log.info("7/7 metadata + upload")
        say(chat_id, "6/7 Writing titles and uploading as private...")
        meta = metadata.build(topic, script)
        publish_at = youtube.next_publish_slot() if config.SCHEDULE_MODE == "publish_at" else None
        video_id = youtube.upload(out, meta["titles"][0], meta["description"], meta["tags"], publish_at)

        titles = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(meta["titles"]))
        say(chat_id,
            "Video uploaded as PRIVATE.\n"
            f"Length: {total / 60:.1f} minutes\n"
            f"Studio: https://studio.youtube.com/video/{video_id}/edit\n\n"
            f"Title options:\n{titles}\n\n"
            "Next: review it, add the thumbnail, and schedule it in Studio.")
    except Exception as e:
        log.exception("Pipeline failed")
        say(chat_id, f"Failed at this step: {str(e)[:500]}")
        sys.exit(1)


if __name__ == "__main__":
    main()