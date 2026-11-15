from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MemoryStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def load(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def remember(self, key: str, value: str) -> None:
        data = self.load()
        data[key] = value
        self.save(data)

    def forget(self, key: str) -> None:
        data = self.load()
        data.pop(key, None)
        self.save(data)

    def get(self, key: str, default: Any = None) -> Any:
        return self.load().get(key, default)
