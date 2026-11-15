from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AssistantState:
    status: str = "idle"
    last_response: str = ""
    notes: list[str] = field(default_factory=list)


class PersonalAssistant:
    def __init__(self, settings, memory_store):
        self.settings = settings
        self.memory = memory_store
        self.state = AssistantState()

    def set_status(self, status: str) -> None:
        self.state.status = status

    def remember(self, key: str, value: str) -> None:
        self.memory.remember(key, value)

    def ask(self, text: str) -> str:
        self.set_status("thinking")
        response = self._build_reply(text)
        self.state.last_response = response
        self.set_status("idle")
        return response

    def _build_reply(self, text: str) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            return "I’m ready when you are."

        user_name = self.memory.get("user_name", "friend")
        if cleaned.lower().startswith("hello"):
            return f"Hello {user_name}. I’m here and ready to help."

        if cleaned.lower().startswith("remember"):
            return "I can save important information for you in local memory."

        if cleaned.lower().startswith("what do you remember"):
            data = self.memory.load()
            if not data:
                return "I don’t have any saved memory yet."
            facts = ", ".join(f"{key}: {value}" for key, value in data.items())
            return f"I remember: {facts}."

        return f"I heard: \"{cleaned}\". I’m ready to help with tasks, reminders, and memory."

    def speak(self, text: str) -> None:
        self.state.last_response = text
        self.set_status("speaking")
