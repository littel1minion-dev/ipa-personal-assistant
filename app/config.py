from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    app_name: str = "Ian's Personal Assistant"
    assistant_name: str = "I.P.A."
    data_dir: Path = field(default_factory=lambda: Path("data"))
    memory_file: Path = field(default_factory=lambda: Path("data/memory.json"))
    # This comes from Mark's supplied main.py and can be overridden for a model
    # enabled on a particular Gemini key: GEMINI_LIVE_MODEL=models/...
    live_model: str = field(default_factory=lambda: os.getenv(
        "GEMINI_LIVE_MODEL", "models/gemini-3.1-flash-live-preview"))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)


DEFAULT_SETTINGS = Settings()
