"""Local Supertonic 3 TTS — on-device, free, no API calls.

Wraps the `supertonic` package. Models are downloaded once (from Hugging Face)
into the repo-local SUPERTONIC_MODEL_DIR rather than the user's global HF cache,
so the asset location is explicit and self-contained.
"""
from __future__ import annotations

import os
from pathlib import Path

from .config import (
    SUPERTONIC_MODEL_DIR,
    SUPERTONIC_VOICE_EN,
    SUPERTONIC_VOICE_KO,
)

# Belt-and-suspenders: make sure any underlying Hugging Face download lands in
# our tree regardless of how the package resolves its cache location. Set before
# `supertonic` (and therefore huggingface_hub) is imported.
os.environ.setdefault("HF_HOME", str(SUPERTONIC_MODEL_DIR / "hf"))

_tts = None  # lazily-constructed module-level singleton


_SAMPLE_RATE = 44100  # Supertonic outputs 44.1kHz studio-grade audio.


def _get_tts():
    """Construct (once) and return the Supertonic TTS engine."""
    global _tts
    if _tts is None:
        SUPERTONIC_MODEL_DIR.mkdir(parents=True, exist_ok=True)
        from supertonic import TTS

        # `model_dir` controls where models are downloaded/loaded; auto_download
        # fetches them there on first use.
        _tts = TTS(model_dir=str(SUPERTONIC_MODEL_DIR), auto_download=True)
    return _tts


def synthesize_to_file(
    text: str,
    lang: str,
    out_path: Path,
    speed: float | None = None,
) -> float:
    """Synthesize `text` to `out_path` (WAV). Returns the audio duration in seconds."""
    tts = _get_tts()
    voice_name = SUPERTONIC_VOICE_EN if lang == "en" else SUPERTONIC_VOICE_KO
    style = tts.get_voice_style(voice_name=voice_name)
    kwargs = dict(text=text, voice_style=style, total_steps=8, lang=lang)
    if speed is not None:
        kwargs["speed"] = speed
    wav, _ = tts.synthesize(**kwargs)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tts.save_audio(wav, str(out_path))
    return len(wav) / _SAMPLE_RATE
