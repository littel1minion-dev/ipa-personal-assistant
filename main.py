from __future__ import annotations

import os
import subprocess
import sys

from dotenv import load_dotenv
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QInputDialog, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from app.assistant import PersonalAssistant
from app.audio import record_wav
from app.config import DEFAULT_SETTINGS
from app.credentials import CredentialStoreError, load_api_key, save_api_key
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
        self._speech_timer = QTimer(self)
        self._speech_timer.timeout.connect(self._check_speech)

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
        self.status_label = QLabel("IDLE · SET UP GEMINI")
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

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask I.P.A. · try ‘remember favorite color = amber’")
        self.input.returnPressed.connect(self._send)
        row.addWidget(self.input, stretch=1)

        self.listen_btn = QPushButton("Listen")
        self.listen_btn.clicked.connect(self._listen)
        row.addWidget(self.listen_btn)

        self.voice_btn = QPushButton("Speak reply")
        self.voice_btn.clicked.connect(self._speak_latest)
        self.voice_btn.setEnabled(sys.platform == "darwin")
        row.addWidget(self.voice_btn)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._send)
        row.addWidget(self.send_btn)
        layout.addLayout(row)

        self.note = QLabel("Voice input is available for short recordings. Gemini must be configured first.")
        self.note.setStyleSheet("color: #84919b; font-size: 11px;")
        layout.addWidget(self.note)

        self.setCentralWidget(root)
        self._append("I.P.A.", "I’m ready. You can type or press Listen to record a short voice prompt.")
        self._set_status("idle")

    def _append(self, speaker: str, text: str) -> None:
        safe = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.chat.append(f'<span style="color:#d99a4e"><b>{speaker}</b></span> &nbsp; {safe}')

    def _set_status(self, state: str) -> None:
        self.hud.set_status(state)
        suffix = "GEMINI" if self.assistant.gemini_configured else "NO API KEY"
        self.status_label.setText(f"{state.upper()} · {suffix}")
        self.note.setText(
            "Gemini connected · text chat and voice prompts are ready." if self.assistant.gemini_configured
            else "Add GOOGLE_API_KEY or set Gemini in Settings to enable voice prompts."
        )

    def _send(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._append("YOU", text)
        self._set_status("thinking")
        response = self.assistant.ask(text)
        self._append(self.settings.assistant_name, response)
        self._set_status("idle")

    def _listen(self) -> None:
        if not self.assistant.gemini_configured:
            QMessageBox.warning(self, "Gemini not configured", "Open Settings and add a Gemini API key before using voice input.")
            return
        self._set_status("listening")
        try:
            audio_path = "data/mic_capture.wav"
            record_wav(audio_path, seconds=5.0)
            transcript = self.assistant.transcribe_audio_file(audio_path)
            if transcript.startswith("Gemini isn’t configured") or transcript.startswith("I couldn’t transcribe"):
                self._append("SYSTEM", transcript)
                self._set_status("idle")
                return
            self._append("VOICE", transcript)
            self._set_status("thinking")
            response = self.assistant.ask(transcript)
            self._append(self.settings.assistant_name, response)
            self._set_status("idle")
        except Exception as exc:
            self._set_status("idle")
            QMessageBox.warning(self, "Microphone issue", f"Could not capture audio: {exc}")

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
        current = self.assistant._api_key() or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        value, ok = QInputDialog.getText(
            self,
            "Gemini API key",
            f"Current: {'saved' if current else 'not set'}\n\nPaste your Gemini API key:",
            QLineEdit.EchoMode.Password,
        )
        if not ok or not value.strip():
            return
        key = value.strip()
        try:
            save_api_key(key)
            self.assistant.refresh_saved_api_key()
            self.assistant.set_api_key(None)
            self._set_status("idle")
            QMessageBox.information(self, "Gemini configured", "Your key was saved securely. The app is ready to use.")
        except CredentialStoreError as exc:
            QMessageBox.warning(self, "Secure storage unavailable", f"{exc}\n\nSet GOOGLE_API_KEY in your shell instead.")

    def closeEvent(self, event) -> None:
        if self._speech_process and self._speech_process.poll() is None:
            self._speech_process.terminate()
        self.assistant.close()
        super().closeEvent(event)


def main() -> None:
    load_dotenv()
    app = QApplication(sys.argv)
    window = IpaApp()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
