from __future__ import annotations

import subprocess
import sys

from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from app.assistant import PersonalAssistant
from app.config import DEFAULT_SETTINGS
from app.memory import MemoryStore
from app.ui.hud import HudWidget


class AskWorker(QThread):
    completed = pyqtSignal(str)

    def __init__(self, assistant: PersonalAssistant, prompt: str):
        super().__init__()
        self.assistant = assistant
        self.prompt = prompt

    def run(self) -> None:
        try:
            result = self.assistant.ask(self.prompt)
        except Exception as exc:  # Keep unexpected provider errors out of the Qt event loop.
            result = f"The request failed: {exc}"
        self.completed.emit(result)


class IpaApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = DEFAULT_SETTINGS
        self.settings.ensure_dirs()
        self.memory_store = MemoryStore(self.settings.memory_file)
        self.assistant = PersonalAssistant(self.settings, self.memory_store)
        self._speech_process = None
        self._worker: AskWorker | None = None

        self.setWindowTitle(self.settings.app_name)
        self.resize(980, 760)
        self.setMinimumSize(720, 600)
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #071018; color: #e8edf2; }
            QLabel { color: #dce5eb; }
            QLineEdit, QTextEdit { background: #0c1822; border: 1px solid #263744;
                border-radius: 8px; padding: 9px; color: #eef4f7; selection-background-color: #89531e; }
            QPushButton { background: #17232c; border: 1px solid #394955; border-radius: 8px;
                padding: 8px 13px; color: #f3d4a9; }
            QPushButton:hover { background: #26323a; border-color: #d89342; }
            QPushButton:disabled { color: #66717a; }
        """)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 16, 22, 18)
        layout.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel(self.settings.assistant_name)
        title.setStyleSheet("font-size: 22px; letter-spacing: 4px; color: #f4d29d;")
        header.addWidget(title)
        header.addStretch()
        self.status_label = QLabel("IDLE · GEMINI" if self.assistant.gemini_configured else "IDLE · SET UP GEMINI")
        self.status_label.setStyleSheet("color: #c28a4c; letter-spacing: 2px;")
        header.addWidget(self.status_label)
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self._show_settings)
        header.addWidget(settings_btn)
        memory_btn = QPushButton("Memory")
        memory_btn.clicked.connect(self._show_memory)
        header.addWidget(memory_btn)
        layout.addLayout(header)

        self.hud = HudWidget(self.settings.assistant_name)
        layout.addWidget(self.hud, stretch=4)
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setMaximumHeight(145)
        self.chat.setPlaceholderText("Your conversation will appear here.")
        layout.addWidget(self.chat, stretch=1)

        self.content_title = QLabel("ON-SCREEN DATA")
        self.content_title.setStyleSheet("color: #e5ae68; letter-spacing: 2px; font-size: 11px;")
        self.content_title.hide()
        self.content = QTextEdit()
        self.content.setReadOnly(True)
        self.content.setMaximumHeight(120)
        self.content.hide()
        layout.addWidget(self.content_title)
        layout.addWidget(self.content)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask I.P.A. · try ‘remember favorite color = amber’")
        self.input.returnPressed.connect(self._send)
        row.addWidget(self.input, stretch=1)
        self.voice_btn = QPushButton("Speak reply")
        self.voice_btn.setToolTip("Read the latest reply aloud with the built-in macOS voice.")
        self.voice_btn.clicked.connect(self._speak_latest)
        self.voice_btn.setEnabled(sys.platform == "darwin")
        row.addWidget(self.voice_btn)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._send)
        row.addWidget(self.send_btn)
        layout.addLayout(row)

        note_text = "Gemini connected · text chat is ready." if self.assistant.gemini_configured else (
            "Add GOOGLE_API_KEY to .env to enable Gemini. Microphone capture is not wired up yet."
        )
        self.note = QLabel(note_text)
        self.note.setStyleSheet("color: #84919b; font-size: 11px;")
        layout.addWidget(self.note)
        self.setCentralWidget(root)
        self._append("I.P.A.", "I’m ready. This app sends your messages to Gemini when a key is configured; local memory commands stay on this device.")
        self._set_status("idle")
        self._speech_timer = QTimer(self)
        self._speech_timer.timeout.connect(self._check_speech)

    def _append(self, speaker: str, text: str) -> None:
        safe = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.chat.append(f'<span style="color:#d99a4e"><b>{speaker}</b></span> &nbsp; {safe}')

    def _set_status(self, state: str) -> None:
        self.hud.set_status(state)
        suffix = "GEMINI" if self.assistant.gemini_configured else "NO API KEY"
        self.status_label.setText(f"{state.upper()} · {suffix}")

    def _send(self) -> None:
        text = self.input.text().strip()
        if not text or (self._worker and self._worker.isRunning()):
            return
        self.input.clear()
        self._append("YOU", text)
        self._show_requested = any(phrase in text.lower() for phrase in (
            "show on screen", "show it on screen", "display that", "put it on screen",
        ))
        self._set_status("thinking")
        self.input.setEnabled(False)
        self.send_btn.setEnabled(False)
        self._worker = AskWorker(self.assistant, text)
        self._worker.completed.connect(self._on_answer)
        self._worker.start()

    def _on_answer(self, response: str) -> None:
        self._append(self.settings.assistant_name, response)
        if getattr(self, "_show_requested", False):
            self.content.setPlainText(response)
            self.content_title.show()
            self.content.show()
        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.input.setFocus()
        self._set_status("idle")

    def _speak_latest(self) -> None:
        if sys.platform != "darwin":
            return
        text = self.assistant.state.last_response.strip()
        if not text or (self._speech_process and self._speech_process.poll() is None):
            return
        try:
            self._speech_process = subprocess.Popen(["say", text])
            self._set_status("speaking")
            self._speech_timer.start(100)
        except OSError as exc:
            QMessageBox.warning(self, "Speech unavailable", str(exc))

    def _check_speech(self) -> None:
        if self._speech_process is None or self._speech_process.poll() is not None:
            self._speech_timer.stop()
            self._speech_process = None
            self._set_status("idle")

    def _show_memory(self) -> None:
        facts = self.memory_store.load()
        body = "\n".join(f"{key}: {value}" for key, value in facts.items()) or "No saved memories yet."
        QMessageBox.information(self, "Local memory", body)

    def _show_settings(self) -> None:
        key_status = "Gemini API key detected." if self.assistant.gemini_configured else "No Gemini API key detected."
        QMessageBox.information(
            self, "I.P.A. settings",
            f"{key_status}\nModel: {self.settings.gemini_model}\n\n"
            "Set GOOGLE_API_KEY in your local .env file and restart the app. "
            "Never paste or commit your API key into source files.\n\n"
            "Microphone capture is not enabled yet. macOS speech output is available via ‘Speak reply’.",
        )

    def closeEvent(self, event) -> None:
        if self._speech_process and self._speech_process.poll() is None:
            self._speech_process.terminate()
        if self._worker and self._worker.isRunning():
            self._worker.wait(1500)
        super().closeEvent(event)


def main() -> None:
    load_dotenv()
    app = QApplication(sys.argv)
    window = IpaApp()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
