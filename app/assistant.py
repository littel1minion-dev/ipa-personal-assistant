from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AssistantState:
    status: str = "idle"
    last_response: str = ""


class PersonalAssistant:
    """Small local prototype; no cloud model is connected yet."""

    def __init__(self, settings, memory_store):
        self.settings = settings
        self.memory = memory_store
        self.state = AssistantState()

    def set_status(self, status: str) -> None:
        self.state.status = status

    def ask(self, text: str) -> str:
        text = (text or "").strip()
        self.set_status("thinking")
        response = self._reply(text)
        self.state.last_response = response
        self.set_status("idle")
        return response

    def _reply(self, text: str) -> str:
        if not text:
            return "I’m ready when you are."

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
            return f"I forgot ‘{key}’." if existed else f“I couldn’t find a memory called ‘{key}’."

        if "what do you remember" in lower or lower.strip() == "show memory":
            facts = self.memory.load()
            if not facts:
                return "I don’t have any saved facts yet. Try ‘remember favorite color = amber’."
            return "Saved memories: " + "; ".join(f"{key}: {value}" for key, value in facts.items())

        if lower in {"hello", "hi", "hey"} or lower.startswith(("hello ", "hi ", "hey ")):
            name = self.memory.get("user_name", "there")
            return f"Hello, {name}. I’m here and ready to help."

        return (
            "I received your message. This starter version has local memory and macOS speech, "
            "but it isn’t connected to an AI model yet."
        )
