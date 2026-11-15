from __future__ import annotations

from PyQt6.QtWidgets import QApplication, QMainWindow

from app.assistant import PersonalAssistant
from app.config import DEFAULT_SETTINGS
from app.memory import MemoryStore
from app.ui.hud import HudWidget


class IpaApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = DEFAULT_SETTINGS
        self.settings.ensure_dirs()

        self.memory_store = MemoryStore(self.settings.memory_file)
        self.assistant = PersonalAssistant(self.settings, self.memory_store)

        self.hud = HudWidget(self.settings.assistant_name)
        self.setCentralWidget(self.hud)
        self.resize(1000, 700)
        self.setWindowTitle(self.settings.app_name)

    def set_status(self, status: str) -> None:
        self.hud.set_status(status)
        self.assistant.set_status(status)

    def run_demo(self) -> None:
        self.set_status("listening")



def main() -> None:
    app = QApplication([])
    window = IpaApp()
    window.show()
    window.run_demo()
    app.exec()


if __name__ == "__main__":
    main()
