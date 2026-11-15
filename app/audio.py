from __future__ import annotations

import asyncio
import threading

import sounddevice as sd
from google import genai
from google.genai import types
from PyQt6.QtCore import QThread, pyqtSignal


class LiveVoiceWorker(QThread):
    """Bidirectional microphone/audio session with Gemini Live; mic runs only while active."""

    status_changed = pyqtSignal(str)
    transcript = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, api_key: str, model: str):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self._stop_requested = threading.Event()

    def stop(self) -> None:
        self._stop_requested.set()

    def run(self) -> None:
        try:
            asyncio.run(self._session())
        except Exception as exc:
            if not self._stop_requested.is_set():
                self.failed.emit(self._friendly_error(exc))
        finally:
            self.status_changed.emit("idle")

    async def _session(self) -> None:
        client = genai.Client(api_key=self.api_key)
        self.status_changed.emit("connecting")
        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            system_instruction=(
                "You are I.P.A., a helpful, natural, concise voice assistant. "
                "Answer conversationally. Be clear about uncertainty and do not claim to perform actions "
                "unless an available integration actually did them."
            ),
        )
        try:
            async with client.aio.live.connect(model=self.model, config=config) as session:
                self.status_changed.emit("listening")
                loop = asyncio.get_running_loop()
                audio_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=24)
                output_stream = None

                def enqueue_audio(data: bytes) -> None:
                    if audio_queue.full():
                        try:
                            audio_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                    try:
                        audio_queue.put_nowait(data)
                    except asyncio.QueueFull:
                        pass

                def mic_callback(indata, _frames, _time_info, status) -> None:
                    if status:
                        self.status_changed.emit("listening")
                    chunk = bytes(indata)
                    loop.call_soon_threadsafe(enqueue_audio, chunk)

                with sd.RawInputStream(
                    samplerate=16000,
                    blocksize=1600,
                    channels=1,
                    dtype="int16",
                    callback=mic_callback,
                ) as input_stream:
                    async def send_audio() -> None:
                        while not self._stop_requested.is_set():
                            chunk = await audio_queue.get()
                            await session.send_realtime_input(
                                audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
                            )

                    async def receive_audio() -> None:
                        nonlocal output_stream
                        async for response in session.receive():
                            if self._stop_requested.is_set():
                                break
                            server_content = getattr(response, "server_content", None)
                            if server_content is None:
                                continue
                            # Surface transcription events when the active model returns them.
                            for name in ("input_transcription", "output_transcription"):
                                item = getattr(server_content, name, None)
                                text = getattr(item, "text", None) if item else None
                                if text:
                                    label = "YOU" if name == "input_transcription" else "I.P.A."
                                    self.transcript.emit(f"{label}: {text.strip()}")
                            model_turn = getattr(server_content, "model_turn", None)
                            if model_turn is None:
                                continue
                            for part in model_turn.parts:
                                inline = getattr(part, "inline_data", None)
                                if inline is None or not inline.data:
                                    continue
                                if output_stream is None:
                                    output_stream = sd.RawOutputStream(
                                        samplerate=24000, channels=1, dtype="int16"
                                    )
                                    output_stream.start()
                                self.status_changed.emit("speaking")
                                await asyncio.to_thread(output_stream.write, inline.data)
                                self.status_changed.emit("listening")

                    send_task = asyncio.create_task(send_audio())
                    receive_task = asyncio.create_task(receive_audio())
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
                        if output_stream is not None:
                            output_stream.stop()
                            output_stream.close()
        finally:
            await client.aio.aclose()

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        message = str(exc).lower()
        if "device" in message or "input" in message or "portaudio" in message:
            return "Could not open the microphone or speakers. Check device selection and microphone permission."
        if "api key" in message or "unauthenticated" in message or "permission" in message:
            return "Gemini rejected the key or the key does not have Live API access. Check your API key and model access."
        return f"Voice connection failed: {exc}"
