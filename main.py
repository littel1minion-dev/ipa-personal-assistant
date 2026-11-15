from __future__ import annotations

import wave
from pathlib import Path

import sounddevice as sd


def record_wav(path: str | Path, seconds: float = 5.0, sample_rate: int = 16000, channels: int = 1) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    frames = sd.rec(
        int(sample_rate * seconds),
        samplerate=sample_rate,
        channels=channels,
        dtype="int16",
        blocking=True,
    )
    with wave.open(str(target), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(frames.tobytes())
    return str(target)
