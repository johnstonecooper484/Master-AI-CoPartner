# core/io/speech/stt_faster_whisper.py
"""
Offline Speech-to-Text using faster-whisper.

Design goals:
- Load the model once (lazy singleton)
- Work with WAV files (path in, text out)
- Keep settings simple and safe (CPU int8 default)
"""

from __future__ import annotations

import os
from typing import Optional

from core.logger import get_logger

log = get_logger("stt_faster_whisper")

_MODEL = None
_MODEL_NAME = os.getenv("STT_MODEL", "small")          # tiny / small / medium / large-v3
_DEVICE = os.getenv("STT_DEVICE", "cpu")               # cpu or cuda
_COMPUTE = os.getenv("STT_COMPUTE_TYPE", "int8")       # int8 for cpu, float16 for cuda often


def _get_model():
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel  # import only when needed
        log.info(f"[STT] Loading faster-whisper model='{_MODEL_NAME}' device='{_DEVICE}' compute='{_COMPUTE}'")
        _MODEL = WhisperModel(_MODEL_NAME, device=_DEVICE, compute_type=_COMPUTE)
        log.info("[STT] faster-whisper model loaded")
    return _MODEL


def transcribe_wav(wav_path: str, language: Optional[str] = None) -> str:
    """
    Transcribe a wav file to text.
    Returns "" if file missing or nothing heard.
    """
    if not wav_path or not os.path.exists(wav_path):
        log.warning(f"[STT] WAV not found: {wav_path}")
        return ""

    model = _get_model()

    try:
        segments, info = model.transcribe(
            wav_path,
            vad_filter=True,
            language=language,
        )

        text_parts = []
        for seg in segments:
            if seg.text:
                text_parts.append(seg.text.strip())

        text = " ".join([t for t in text_parts if t]).strip()
        if not text:
            log.info("[STT] No speech detected (empty transcription).")
            return ""

        log.info(f"[STT] Transcribed lang={getattr(info, 'language', None)} prob={getattr(info, 'language_probability', None)}")
        return text

    except Exception as exc:
        log.exception(f"[STT] Transcribe failed: {exc}")
        return ""
