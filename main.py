from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from app.audio import LiveVoiceWorker
from app.config import DEFAULT_SETTINGS
from app.credentials import CredentialStoreError, load_api_key, save_api_key
from app.memory import MemoryStore
from app.ui.hud import HudWidget


class ApiKeyDialog(QDialog):
    def __init__(self, parent: QWidget, has_key: bool):
        super().__init__(parent)
        self.setWindowTitle("Connect Gemini Live")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        explanation = QLabel(
            "Enter your Gemini API key. It is saved in your operating system's credential store, "
            "not in this project. While a voice session is active, microphone audio is streamed to Google. "
            "Click End conversation to stop the microphone."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("Gemini API key")
        self.key_edit.setClearButtonEnabled(True)
        layout.addWidget(self.key_edit)
        if has_key:
            note = QLabel("A key is already configured. Enter a replacement, or leave blank to keep it.")
            note.setWordWrap(True)
            layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class IpaApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = DEFAULT_SETTINGS
        self.settings.ensure_dirs()
        self.memory = MemoryStore(self.settings.memory_file)
        self.worker: LiveVoiceWorker | None = None
        self.setWindowTitle(self.settings.app_name)
        self.resize(960, 760)
        self.setMinimumSize(720, 600)
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #070b0a; color: #e8edf2; }
            QLabel { color: #dce5eb; }
            QTextEdit { background: #0c1110; border: 1px solid #392819; border-radius: 8px; padding: 9px; color: #eef4f7; }
            QPushButton { background: #171b18; border: 1px solid #5b4024; border-radius: 8px; padding: 9px 14px; color: #f3d4a9; }
            QPushButton:hover { background: #29231a; border-color: #e3a34f; }
            QPushButton:disabled { color: #66717a; }
        """)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 16, 20, 16)
        header = QHBoxLayout()
        title = QLabel(self.settings.assistant_name)
        title.setStyleSheet("font-size: 22px; letter-spacing: 4px; color: #f4d29d;")
        header.addWidget(title)
        header.addStretch()
        self.status_label = QLabel("IDLE")
        self.status_label.setStyleSheet("color: #c28a4c; letter-spacing: 2px;")
        header.addWidget(self.status_label)
        self.settings_button = QPushButton("Gemini settings")
        self.settings_button.clicked.connect(self._settings)
        header.addWidget(self.settings_button)
        self.memory_button = QPushButton("Memory")
        self.memory_button.clicked.connect(self._show_memory)
        header.addWidget(self.memory_button)
        layout.addLayout(header)

        self.hud = HudWidget(self.settings.assistant_name)
        layout.addWidget(self.hud, stretch=4)
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setMaximumHeight(170)
        layout.addWidget(self.chat, stretch=1)

        controls = QHBoxLayout()
        self.talk_button = QPushButton("Start talking")
        self.talk_button.setMinimumHeight(44)
        self.talk_button.clicked.connect(self._toggle_talk)
        controls.addWidget(self.talk_button, stretch=1)
        self.end_button = QPushButton("End conversation")
        self.end_button.setEnabled(False)
        self.end_button.clicked.connect(self._stop_talk)
        controls.addWidget(self.end_button)
        layout.addLayout(controls)
        self.note = QLabel("Microphone is off. Click Start talking to begin a live Gemini voice session.")
        self.note.setWordWrap(True)
        self.note.setStyleSheet("color: #9a8b78; font-size: 11px;")
        layout.addWidget(self.note)
        self.setCentralWidget(root)
        self._append("I.P.A.", "Ready. Start talking when you want to open a live voice conversation.")
        self._refresh_status("idle")

    def _append(self, speaker: str, text: str) -> None:
        safe = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.chat.append(f'<span style="color:#e2a04f"><b>{speaker}</b></span> &nbsp; {safe}')

    def _get_key(self) -> str | None:
        key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if key:
            return key
        try:
            return load_api_key()
        except CredentialStoreError:
            return None

    def _refresh_status(self, state: str) -> None:
        self.status_label.setText(state.upper())
        self.hud.set_status(state)
        if state == "listening":
            self.note.setText("Live microphone is on and audio is being streamed to Gemini. Click End conversation to stop.")
        elif state == "speaking":
            self.note.setText("Gemini is speaking. You can continue talking to interrupt or respond.")
        elif state == "connecting":
            self.note.setText("Connecting to Gemini Live…")
        else:
            self.note.setText("Microphone is off. Click Start talking to begin a live Gemini voice session.")

    def _toggle_talk(self) -> None:
        if self.worker and self.worker.isRunning():
            self._stop_talk()
            return
        key = self._get_key()
        if not key:
            QMessageBox.information(self, "Gemini key needed", "Click Gemini settings and enter your API key first.")
            return
        self.worker = LiveVoiceWorker(key, self.settings.gemini_model)
        self.worker.status_changed.connect(self._refresh_status)
        self.worker.transcript.connect(self._on_transcript)
        self.worker.failed.connect(self._on_voice_error)
        self.worker.finished.connect(self._on_voice_finished)
        self.talk_button.setText("Conversation active")
        self.talk_button.setEnabled(False)
        self.end_button.setEnabled(True)
        self.worker.start()

    def _stop_talk(self) -> None:
        if self.worker and self.worker.isRunning():
            self._refresh_status("ending")
            self.end_button.setEnabled(False)
            self.worker.stop()

    def _on_transcript(self, line: str) -> None:
        if ":" in line:
            speaker, text = line.split(":", 1)
            self._append(speaker, text.strip())

    def _on_voice_error(self, message: str) -> None:
        self._append("SYSTEM", message)
        QMessageBox.warning(self, "Voice conversation", message)

    def _on_voice_finished(self) -> None:
        self.talk_button.setEnabled(True)
        self.talk_button.setText("Start talking")
        self.end_button.setEnabled(False)
        self._refresh_status("idle")

    def _settings(self) -> None:
        dialog = ApiKeyDialog(self, bool(self._get_key()))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        key = dialog.key_edit.text().strip()
        if not key:
            QMessageBox.information(self, "Gemini", "No changes made.")
            return
        try:
            save_api_key(key)
            QMessageBox.information(self, "Gemini", "API key saved in the OS credential store.")
        except CredentialStoreError as exc:
            QMessageBox.warning(self, "Secure storage unavailable", f"{exc}\n\nSet GOOGLE_API_KEY in your shell instead; the key will not be saved in the project.")

    def _show_memory(self) -> None:
        facts = self.memory.load()
        text = "\n".join(f"{key}: {value}" for key, value in facts.items()) or "No saved memories yet."
        QMessageBox.information(self, "Local memory", text)

    def closeEvent(self, event) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)
        super().closeEvent(event)


def main() -> None:
    load_dotenv()
    app = QApplication(sys.argv)
    window = IpaApp()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
