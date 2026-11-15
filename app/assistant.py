from __future__ import annotations

import os
from dataclasses import dataclass, field

from app.gemini import GeminiClient, GeminiConfigurationError, GeminiRequestError


@dataclass
class AssistantState:
    status: str = "idle"
    last_response: str = ""
    history: list[tuple[str, str]] = field(default_factory=list)


class PersonalAssistant:
    """Desktop assistant with local commands and an optional Gemini backend."""

    def __init__(self, settings, memory_store):
        self.settings = settings
        self.memory = memory_store
        self.state = AssistantState()
        self._gemini: GeminiClient | None = None

    @property
    def gemini_configured(self) -> bool:
        return bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))

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
        if not self.gemini_configured:
            return (
                "Gemini isn’t configured yet. Add your key to a local .env file as "
                "GOOGLE_API_KEY=your_key, then restart I.P.A. See the README for setup."
            )
        try:
            if self._gemini is None:
                self._gemini = GeminiClient(self.settings.gemini_model)
            return self._gemini.generate(text, self.state.history)
        except (GeminiConfigurationError, GeminiRequestError) as exc:
            return f"I couldn’t reach Gemini: {exc}"
