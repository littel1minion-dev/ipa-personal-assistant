from __future__ import annotations

import os
from dataclasses import dataclass, field

from app.credentials import CredentialStoreError, load_api_key
from app.gemini import GeminiClient, GeminiConfigurationError, GeminiRequestError


@dataclass
class AssistantState:
    status: str = "idle"
    last_response: str = ""
    history: list[tuple[str, str]] = field(default_factory=list)


class PersonalAssistant:
    """Desktop assistant with local commands, optional Gemini text chat, and simple mic transcription."""

    def __init__(self, settings, memory_store):
        self.settings = settings
        self.memory = memory_store
        self.state = AssistantState()
        self._gemini: GeminiClient | None = None
        self._api_key_override: str | None = None
        try:
            self._saved_api_key = load_api_key()
        except CredentialStoreError:
            self._saved_api_key = None

    @property
    def gemini_configured(self) -> bool:
        return bool(self._api_key() or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))

    def _api_key(self) -> str | None:
        return self._api_key_override or self._saved_api_key

    def set_api_key(self, api_key: str | None) -> None:
        if self._gemini is not None:
            self._gemini.close()
            self._gemini = None
        self._api_key_override = api_key.strip() if api_key and api_key.strip() else None

    def refresh_saved_api_key(self) -> None:
        self._saved_api_key = load_api_key()
        if self._gemini is not None:
            self._gemini.close()
            self._gemini = None

    def set_status(self, status: str) -> None:
        self.state.status = status

    def ask(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return "I’m ready when you are."

        self.set_status("thinking")
        try:
            response = self._local_command(text)
            if response is None:
                response = self._ask_gemini(text)
            self.state.last_response = response
            self.state.history.extend((("user", text), ("assistant", response)))
            self.state.history = self.state.history[-20:]
            return response
        finally:
            self.set_status("idle")

    def transcribe_audio_file(self, path: str) -> str:
        api_key = self._api_key() or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "Gemini isn’t configured. Open Settings and add your API key before using voice input."
        try:
            if self._gemini is None:
                self._gemini = GeminiClient(self.settings.gemini_model, api_key=api_key)
            return self._gemini.transcribe_audio(path)
        except (GeminiConfigurationError, GeminiRequestError) as exc:
            return f"I couldn’t transcribe the audio: {exc}"

    def _local_command(self, text: str) -> str | None:
        lower = text.lower()
        if lower.startswith("remember "):
            item = text[9:].strip()
            if "=" not in item:
                return "Use: remember key = value"
            key, value = (part.strip() for part in item.split("=", 1))
            if not key or not value:
                return "Please include both a memory name and a value."
            self.memory.remember(key, value)
            return f"I saved that locally as ‘{key}’."

        if lower.startswith("forget "):
            key = text[7:].strip()
            if not key:
                return "Tell me the name of the memory to forget."
            existed = self.memory.get(key) is not None
            self.memory.forget(key)
            return f"I forgot ‘{key}’." if existed else f"I couldn’t find a memory called ‘{key}’."

        if "what do you remember" in lower or lower.strip() == "show memory":
            facts = self.memory.load()
            if not facts:
                return "I don’t have any saved facts yet. Try ‘remember favorite color = amber’."
            return "Saved memories: " + "; ".join(f"{key}: {value}" for key, value in facts.items())
        return None

    def _ask_gemini(self, text: str) -> str:
        api_key = self._api_key() or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "Gemini isn’t configured. Open Settings and add your Gemini API key to connect."
        try:
            if self._gemini is None:
                self._gemini = GeminiClient(self.settings.gemini_model, api_key=api_key)
            return self._gemini.generate(text, self.state.history)
        except (GeminiConfigurationError, GeminiRequestError) as exc:
            return f"I couldn’t reach Gemini: {exc}"

    def close(self) -> None:
        if self._gemini is not None:
            self._gemini.close()
            self._gemini = None
