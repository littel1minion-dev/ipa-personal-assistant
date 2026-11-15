from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from pathlib import Path

import numpy as np
import sounddevice as sd
from google import genai
from google.genai import types


class GeminiConfigurationError(RuntimeError):
    """The Gemini SDK or credentials are not configured."""


class GeminiRequestError(RuntimeError):
    """Gemini rejected or failed to answer a request."""


class GeminiLiveSession:
    """A thin wrapper around the Google GenAI Live API for mic audio -> Gemini -> speaker audio."""

    def __init__(self, client, model: str, *, on_text: Callable[[str], None] | None = None, on_audio: Callable[[bytes], None] | None = None):
        self.client = client
        self.model = model
        self.on_text = on_text
        self.on_audio = on_audio
        self._session = None
        self._stop = threading.Event()
        self._loop = None
        self._thread = None

    async def connect(self):
        self._session = await self.client.aio.live.connect(
            model=self.model,
            config={"response_modalities": ["AUDIO"], "temperature": 0.7},
        )
        return self

    async def send_audio(self, pcm: bytes) -> None:
        if self._session is None:
            return
        await self._session.send_realtime_input(
            audio=types.Blob(
                data=pcm,
                mime_type="audio/pcm;rate=16000",
            )
        )

    async def _receive_loop(self) -> None:
        if self._session is None:
            return
        async for response in self._session.receive():
            if getattr(response, "server_content", None) is None:
                continue
            turns = getattr(response.server_content, "model_turn", None)
            if turns is None:
                continue
            for part in getattr(turns, "parts", []) or []:
                if getattr(part, "text", None):
                    if self.on_text is not None:
                        self.on_text(str(part.text))
                if getattr(part, "inline_data", None):
                    audio = getattr(part.inline_data, "data", None)
                    if audio and self.on_audio is not None:
                        self.on_audio(audio)

    async def _mic_loop(self) -> None:
        with sd.InputStream(samplerate=16000, channels=1, dtype="int16") as stream:
            while not self._stop.is_set():
                block, _ = stream.read(1024)
                if block.size == 0:
                    continue
                await self.send_audio(block.tobytes())

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()

        def runner() -> None:
            async def main() -> None:
                await self.connect()
                await asyncio.gather(self._mic_loop(), self._receive_loop())

            try:
                asyncio.run(main())
            except Exception as exc:
                raise GeminiRequestError("live audio session closed unexpectedly") from exc

        self._thread = threading.Thread(target=runner, daemon=True, name="gemini-live-thread")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None


class GeminiClient:
    def __init__(self, model: str, api_key: str | None = None):
        self.model = model
        try:
            self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
        except Exception as exc:
            raise GeminiConfigurationError("check that your API key and google-genai installation are valid") from exc

    def generate(self, prompt: str, history: list[tuple[str, str]]) -> str:
        transcript = [
            "You are I.P.A. (Ian's Personal Assistant), a calm, concise and helpful desktop assistant. "
            "Be transparent about uncertainty. Do not claim to control devices, access files, or take actions "
            "unless the user explicitly enabled an integration that can do so. Local memory commands are "
            "handled by the app and are not part of this model request."
        ]
        for role, message in history[-12:]:
            label = "User" if role == "user" else "I.P.A."
            transcript.append(f"{label}: {message}")
        transcript.append(f"User: {prompt}\nI.P.A.:")
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents="\n\n".join(transcript),
                config=types.GenerateContentConfig(temperature=0.7, max_output_tokens=1024),
            )
            answer = (response.text or "").strip()
            if not answer:
                raise GeminiRequestError("the model returned an empty response")
            return answer
        except GeminiRequestError:
            raise
        except Exception as exc:
            raise GeminiRequestError("check your internet connection, API key, and model availability") from exc

    def transcribe_audio(self, path: str | Path) -> str:
        file_path = Path(path)
        if not file_path.exists():
            raise GeminiRequestError("the audio file was not created successfully")
        data = file_path.read_bytes()
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    "Transcribe the spoken words in this clip. Return only the transcript, no commentary.",
                    types.Part.from_bytes(data=data, mime_type="audio/wav"),
                ],
                config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=512),
            )
            text = (response.text or "").strip()
            if not text:
                raise GeminiRequestError("the transcript was empty")
            return text
        except Exception as exc:
            raise GeminiRequestError("check that the mic recording is valid and the API key can access the model") from exc

    def open_live_session(self, *, on_text: Callable[[str], None] | None = None, on_audio: Callable[[bytes], None] | None = None) -> GeminiLiveSession:
        return GeminiLiveSession(self.client, self.model, on_text=on_text, on_audio=on_audio)

    def close(self) -> None:
        try:
            self.client.close()
        except Exception:
            pass


__all__ = [
    "GeminiClient",
    "GeminiConfigurationError",
    "GeminiRequestError",
    "GeminiLiveSession",
]



def _play_pcm_bytes(pcm: bytes, sample_rate: int = 24000) -> None:
    """Playback helper for the live audio stream."""
    if not pcm:
        return
    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    if samples.size == 0:
        return
    sd.play(samples, samplerate=sample_rate)
    sd.wait()


# Convenience alias for app code that wants a one-liner.
def play_live_audio(pcm: bytes, sample_rate: int = 24000) -> None:
    _play_pcm_bytes(pcm, sample_rate=sample_rate)


# The app can also call: GeminiLiveSession(..., on_audio=play_live_audio)






























































































































































































































"""
Legacy compatibility: this file originally contained the non-live Gemini client.
The live session code above is intentionally kept in the same module so existing
imports continue to work without a larger project refactor.
"""












































































































































































































""" 






































"""





















































































	










































































































































































































































n



















































n














