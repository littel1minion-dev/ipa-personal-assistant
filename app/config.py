from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass
class Settings:
    app_name: str = "Ian's Personal Assistant"
    assistant_name: str = "I.P.A."
    data_dir: Path = field(default_factory=lambda: Path("data"))
    memory_file: Path = field(default_factory=lambda: Path("data/memory.json"))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)


DEFAULT_SETTINGS = Settings()
