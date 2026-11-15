from __future__ import annotations

import subprocess
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

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
        self._speech_process = None

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
        self.status_label = QLabel("IDLE · LOCAL PROTOTYPE")
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
        self.input.setPlaceholderText("Type a message · try: remember favorite color = amber")
        self.input.returnPressed.connect(self._send)
        row.addWidget(self.input, stretch=1)
        self.voice_btn = QPushButton("Speak reply")
        self.voice_btn.setToolTip("Use the built-in macOS voice to read the latest reply aloud.")
        self.voice_btn.clicked.connect(self._speak_latest)
        self.voice_btn.setEnabled(sys.platform == "darwin")
        row.addWidget(self.voice_btn)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._send)
        row.addWidget(self.send_btn)
        layout.addLayout(row)

        note = QLabel("Text input is active. Microphone capture and an AI model connection are not wired up yet.")
        note.setStyleSheet("color: #84919b; font-size: 11px;")
        layout.addWidget(note)

        self.setCentralWidget(root)
        self._append("I.P.A.", "The original starter app is running. Your memories stay in a local JSON file.")
        self.set_status("idle")
        self._speech_timer = QTimer(self)
        self._speech_timer.timeout.connect(self._check_speech)

    def _append(self, speaker: str, text: str) -> None:
        safe = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.chat.append(f'<span style="color:#d99a4e"><b>{speaker}</b></span> &nbsp; {safe}')

    def _set_status(self, state: str) -> None:
        self.hud.set_status(state)
        self.status_label.setText(f"{state.upper()} · LOCAL PROTOTYPE")

    def set_status(self, status: str) -> None:
        self.assistant.set_status(status)
        self._set_status(status)

    def _send(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._append("YOU", text)
        show_on_screen = any(phrase in text.lower() for phrase in (
            "show on screen", "show it on screen", "display that", "put it on screen",
        ))
        self._set_status("thinking")
        response = self.assistant.ask(text)
        self._append(self.settings.assistant_name, response)
        if show_on_screen:
            self.content.setPlainText(response)
            self.content_title.show()
            self.content.show()
        self._set_status("idle")

    def _speak_latest(self) -> None:
        if sys.platform != "darwin":
            return
        text = self.assistant.state.last_response.strip()
        if not text or (self._speech_process and self._speech_process.poll() is None):
            return
        try:
            self._speech_process = subprocess.Popen(["say", text])
            self.set_status("speaking")
            self._speech_timer.start(100)
        except OSError as exc:
            QMessageBox.warning(self, "Speech unavailable", str(exc))

    def _check_speech(self) -> None:
        if self._speech_process is None or self._speech_process.poll() is not None:
            self._speech_timer.stop()
            self._speech_process = None
            self.set_status("idle")

    def _show_memory(self) -> None:
        facts = self.memory_store.load()
        body = "\n".join(f"{key}: {value}" for key, value in facts.items()) or "No saved memories yet."
        QMessageBox.information(self, "Local memory", body)

    def _show_settings(self) -> None:
        QMessageBox.information(
            self, "I.P.A. settings",
            "This starter runs locally and stores memory in data/memory.json.\n\n"
            "AI model connection and microphone capture are not enabled yet. "
            "The Speak reply button uses the built-in macOS ‘say’ voice.",
        )

    def closeEvent(self, event) -> None:
        if self._speech_process and self._speech_process.poll() is None:
            self._speech_process.terminate()
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    window = IpaApp()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
