import logging
import os
import shutil
import sys
from . import (config, tts, transcribe, timeline, keywords, clips, typography,
               render, metadata, youtube, notify, sources, variety, character, manifest)
from .script_clean import clean_script

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
    chat_id = os.environ["CHAT_ID"].strip()
    dry = os.environ.get("DRY_RUN") == "true"

    script = clean_script(os.environ["SCRIPT"].strip())
    if not script:
        raise SystemExit("No spoken text left after cleaning the script")

    history = variety.load_log()

    ok, score, match = variety.check_originality(script, history)
    if not ok:
        say(chat_id, f"Stopped: this script is {score:.0%} similar to an earlier video "
                     f"(\"{match}\"). Write a new angle and send it again. Nothing was rendered.")
        return

    if not dry:
        wait = variety.limit_wait(history)
        if wait:
            say(chat_id, f"Skipped: weekly upload limit reached. Send the next video on or after {wait}.")
            return

    fmt_name, fmt, rng = variety.apply_format(history, topic)
    config.CUT_SECONDS = rng.uniform(*fmt["cut"])
    config.MUSIC_TAG = fmt["music"]
    keywords.STYLES = list(fmt["styles"])
    render.GRADE = variety.grade_for(rng)
    say(chat_id, f"Format: {fmt_name}. Cuts about {config.CUT_SECONDS:.1f} seconds.")

    W = config.WORKDIR
    os.makedirs(W, exist_ok=True)

    try:
        log.info("1/7 voiceover")
        say(chat_id, "1/7 Generating voiceover...")
        voice = tts.synthesize(script, os.path.join(W, "voice.wav"))
        total = timeline.audio_duration(voice)
        say(chat_id, f"Voiceover ready: {total / 60:.1f} minutes.")

        log.info("2/7 word timings and cuts")
        words = transcribe.word_timings(voice)
        cuts = timeline.build_cuts(words, total)
        say(chat_id, f"2/7 Built {len(cuts)} cuts.")

        log.info("3/7 visual plan")
        plan = keywords.plan_visuals(cuts)
        say(chat_id, "3/7 Planned search terms and caption styles.")

        presenter = character.plan(cuts) if character.available() else set()
        say(chat_id, f"Presenter cuts planned: {len(presenter)}"
                     if presenter else "No presenter clip found. Using stock footage only.")

        log.info("4/7 footage and rights")
        clip_paths, records = clips.fetch_all(cuts, plan, presenter)
        say(chat_id, "4/7 Footage downloaded and license-checked.")

        man = manifest.build(topic, fmt_name, cuts, presenter, records, dry)
        man_path = manifest.write(man)
        if not man["all_allowed"]:
            say(chat_id, "Stopped: some footage has unresolved rights. Nothing was uploaded.")
            return

        log.info("5/7 music and sfx")
        music, sfx, credits = sources.fetch_audio()
        say(chat_id, f"Audio: music {'found' if music else 'not found'}, "
                     f"sfx {'found' if sfx else 'not found'}.")

        log.info("5/7 captions")
        ass = typography.write_ass(cuts, plan, os.path.join(W, "captions.ass"))

        log.info("6/7 render")
        say(chat_id, "5/7 Rendering the video. This is the slow step.")
        out = os.path.join(W, "final.mp4")
        render.build(cuts, clip_paths, plan, voice, ass, music, sfx, out)
        shutil.rmtree(os.path.join(W, "clips"), ignore_errors=True)

        if dry:
            say(chat_id, "DRY RUN finished. Nothing was uploaded or saved to history.\n\n"
                         + manifest.summary(man))
            log.info("DRY RUN: output %s, manifest %s", out, man_path)
            return

        log.info("7/7 metadata + upload")
        say(chat_id, "6/7 Writing titles and uploading as private...")
        recent = variety.recent_titles(history)
        meta = metadata.build(topic, script, avoid=recent)
        title = variety.pick_title(meta["titles"], recent)
        description = meta["description"]
        if credits:
            description += "\n\nCredits:\n" + "\n".join(credits)
        publish_at = youtube.next_publish_slot() if config.SCHEDULE_MODE == "publish_at" else None
        video_id = youtube.upload(out, title, description, meta["tags"], publish_at)

        history.append(variety.make_entry(topic, title, fmt_name, script, video_id))
        variety.save_log(history)

        os.makedirs(os.path.join("history", "manifests"), exist_ok=True)
        shutil.copy(man_path, os.path.join("history", "manifests", f"{video_id}.json"))

        titles = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(meta["titles"]))
        say(chat_id,
            "Video uploaded as PRIVATE.\n"
            f"Format: {fmt_name}. Length: {total / 60:.1f} minutes, {len(cuts)} cuts.\n"
            f"Studio: https://studio.youtube.com/video/{video_id}/edit\n\n"
            f"Chosen title: {title}\n\n"
            f"Other options:\n{titles}\n\n"
            "Next: review it, add the thumbnail, and schedule it in Studio.")
    except Exception as e:
        log.exception("Pipeline failed")
        say(chat_id, f"Failed at this step: {str(e)[:500]}")
        sys.exit(1)


if __name__ == "__main__":
    main()