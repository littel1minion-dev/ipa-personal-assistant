from __future__ import annotations

from dataclasses import dataclass, field
import os

from app.credentials import CredentialStoreError, load_api_key
from app.gemini import GeminiClient, GeminiConfigurationError, GeminiRequestError


@dataclass
class AssistantState:
    status: str = "idle"
    last_response: str = ""
    history: list[tuple[str, str]] = field(default_factory=list)


class PersonalAssistant:
    """Text-chat assistant retained for local commands and non-live Gemini requests."""

    def __init__(self, settings, memory_store):
        self.settings = settings
        self.memory = memory_store
        self.state = AssistantState()
        self._client: GeminiClient | None = None
        try:
            self._saved_api_key = load_api_key()
        except CredentialStoreError:
            self._saved_api_key = None

    @property
    def gemini_configured(self) -> bool:
        return bool(self._saved_api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))

    def ask(self, text: str) -> str:
        prompt = (text or "").strip()
        if not prompt:
            return "I’m ready when you are."
        self.state.status = "thinking"
        try:
            response = self._local_command(prompt)
            if response is None:
                if not self.gemini_configured:
                    response = "Open Settings to securely add your Gemini API key."
                else:
                    key = self._saved_api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
                    if self._client is None:
                        self._client = GeminiClient(self.settings.gemini_model, api_key=key)
                    response = self._client.generate(prompt, self.state.history)
            self.state.last_response = response
            self.state.history.extend((("user", prompt), ("assistant", response)))
            self.state.history = self.state.history[-20:]
            return response
        except (GeminiConfigurationError, GeminiRequestError) as exc:
            return f"Gemini request failed: {exc}"
        finally:
            self.state.status = "idle"

    def _local_command(self, prompt: str) -> str | None:
        lower = prompt.lower()
        if lower.startswith("remember ") and "=" in prompt:
            key, value = (part.strip() for part in prompt[9:].split("=", 1))
            if key and value:
                self.memory.remember(key, value)
                return f"Saved locally as ‘{key}’."
        if lower.startswith("forget "):
            key = prompt[7:].strip()
            self.memory.forget(key)
            return f"Forgot ‘{key}’."
        if lower in {"what do you remember", "show memory"}:
            facts = self.memory.load()
            return "; ".join(f"{key}: {value}" for key, value in facts.items()) or "No saved memories yet."
        return None

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
