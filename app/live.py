from __future__ import annotations

import asyncio
import threading

import sounddevice as sd
from google import genai
from google.genai import types
from PyQt6.QtCore import QThread, pyqtSignal


class LiveVoiceWorker(QThread):
    """Stream microphone PCM to Gemini Live and play its streamed PCM replies."""

    status_changed = pyqtSignal(str)
    transcript = pyqtSignal(str)
    failed = pyqtSignal(str)

    INPUT_RATE = 16000
    OUTPUT_RATE = 24000
    CHANNELS = 1
    BLOCKSIZE = 1024

    def __init__(self, api_key: str, model: str):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self._stop_requested = threading.Event()

    def stop(self) -> None:
        self._stop_requested.set()

    def run(self) -> None:
        try:
            asyncio.run(self._run_session())
        except Exception as exc:
            if not self._stop_requested.is_set():
                self.failed.emit(self._friendly_error(exc))
        finally:
            self.status_changed.emit("idle")

    async def _run_session(self) -> None:
        client = genai.Client(api_key=self.api_key)
        output_stream = None
        self.status_changed.emit("connecting")
        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            system_instruction=(
                "You are I.P.A., a helpful, natural, concise voice assistant. "
                "Be transparent about uncertainty and do not claim to perform actions "
                "unless an available integration actually did them."
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
        )
        try:
            # connect() returns an async context manager; enter it before using the session.
            async with client.aio.live.connect(model=self.model, config=config) as session:
                loop = asyncio.get_running_loop()
                mic_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=32)

                def enqueue(data: bytes) -> None:
                    if mic_queue.full():
                        try:
                            mic_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                    try:
                        mic_queue.put_nowait(data)
                    except asyncio.QueueFull:
                        pass

                def mic_callback(indata, _frames, _time, _status) -> None:
                    loop.call_soon_threadsafe(enqueue, bytes(indata))

                async def send_mic() -> None:
                    while not self._stop_requested.is_set():
                        data = await mic_queue.get()
                        await session.send_realtime_input(
                            audio=types.Blob(
                                data=data,
                                mime_type=f"audio/pcm;rate={self.INPUT_RATE}",
                            )
                        )

                async def receive_reply() -> None:
                    nonlocal output_stream
                    async for response in session.receive():
                        if self._stop_requested.is_set():
                            return
                        server_content = getattr(response, "server_content", None)
                        if server_content is None:
                            continue
                        for field, speaker in (("input_transcription", "YOU"),
                                               ("output_transcription", "I.P.A.")):
                            item = getattr(server_content, field, None)
                            text = getattr(item, "text", None) if item else None
                            if text and text.strip():
                                self.transcript.emit(f"{speaker}: {text.strip()}")
                        model_turn = getattr(server_content, "model_turn", None)
                        if model_turn is None:
                            continue
                        for part in getattr(model_turn, "parts", []) or []:
                            inline = getattr(part, "inline_data", None)
                            audio = getattr(inline, "data", None) if inline else None
                            if not audio:
                                continue
                            if output_stream is None:
                                output_stream = sd.RawOutputStream(
                                    samplerate=self.OUTPUT_RATE,
                                    channels=self.CHANNELS,
                                    dtype="int16",
                                    blocksize=self.BLOCKSIZE,
                                )
                                output_stream.start()
                            self.status_changed.emit("speaking")
                            await asyncio.to_thread(output_stream.write, audio)
                            self.status_changed.emit("listening")

                with sd.RawInputStream(
                    samplerate=self.INPUT_RATE,
                    channels=self.CHANNELS,
                    dtype="int16",
                    blocksize=self.BLOCKSIZE,
                    callback=mic_callback,
                ) as input_stream:
                    self.status_changed.emit("listening")
                    send_task = asyncio.create_task(send_mic())
                    receive_task = asyncio.create_task(receive_reply())
                    try:
                        while not self._stop_requested.is_set():
                            if send_task.done():
                                await send_task
                            if receive_task.done():
                                await receive_task
                                break
                            await asyncio.sleep(0.05)
                    finally:
                        input_stream.stop()
                        for task in (send_task, receive_task):
                            if not task.done():
                                task.cancel()
                        await asyncio.gather(send_task, receive_task, return_exceptions=True)
        finally:
            if output_stream is not None:
                try:
                    output_stream.stop()
                    output_stream.close()
                except Exception:
                    pass
            try:
                client.close()
            except Exception:
                pass

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        message = str(exc)
        low = message.lower()
        if "404" in low or "not found" in low:
            return ("Gemini Live rejected the configured model. Check that the model is "
                    "available to your API key; you can set GEMINI_LIVE_MODEL to another "
                    "Live model shown for your account. Details: " + message[:240])
        if any(word in low for word in ("device", "portaudio", "input", "sound")):
            return "Could not open the microphone or speakers. Check macOS microphone permission and audio devices."
        if any(word in low for word in ("api key", "unauthenticated", "permission", "403")):
            return "Gemini rejected the API key or Live API access. Check your key and account access."
        return f"Voice connection failed: {message[:300]}"
