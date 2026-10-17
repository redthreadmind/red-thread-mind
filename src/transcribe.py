from faster_whisper import WhisperModel
from . import config

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model

def word_timings(wav_path):
    """Return [{'word', 'start', 'end'}] from the voiceover audio."""
    segments, _ = _get_model().transcribe(wav_path, word_timestamps=True, language="en")
    words = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                words.append({"word": text, "start": w.start, "end": w.end})
    return words