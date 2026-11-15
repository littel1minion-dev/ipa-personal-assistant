from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from app.assistant import PersonalAssistant
from app.config import DEFAULT_SETTINGS
from app.credentials import CredentialStoreError, load_api_key, save_api_key
from app.live import LiveVoiceWorker
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
        except Exception as exc:
            result = f"The request failed: {exc}"
        self.completed.emit(result)


class ApiKeyDialog(QDialog):
    def __init__(self, parent: QWidget, has_key: bool):
        super().__init__(parent)
        self.setWindowTitle("Connect Gemini")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        description = QLabel(
            "Paste your Gemini API key. I.P.A. stores it in your operating system’s secure "
            "credential store. While a live voice conversation is active, microphone audio is "
            "streamed to Google; click Stop talking to end it."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("Gemini API key")
        self.key_input.setClearButtonEnabled(True)
        layout.addWidget(self.key_input)
        if has_key:
            current = QLabel("A key is already configured. Enter a replacement, or leave blank to keep it.")
            current.setWordWrap(True)
            layout.addWidget(current)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def api_key(self) -> str:
        return self.key_input.text().strip()


class IpaApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = DEFAULT_SETTINGS
        self.settings.ensure_dirs()
        self.memory_store = MemoryStore(self.settings.memory_file)
        self.assistant = PersonalAssistant(self.settings, self.memory_store)
        self._ask_worker: AskWorker | None = None
        self._live_worker: LiveVoiceWorker | None = None

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
        self.status_label = QLabel()
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
        self.chat.setMaximumHeight(160)
        self.chat.setPlaceholderText("Your conversation will appear here.")
        layout.addWidget(self.chat, stretch=1)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message or start a live voice conversation")
        self.input.returnPressed.connect(self._send)
        row.addWidget(self.input, stretch=1)
        self.talk_button = QPushButton("Start talking")
        self.talk_button.clicked.connect(self._toggle_talk)
        row.addWidget(self.talk_button)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._send)
        row.addWidget(self.send_btn)
        layout.addLayout(row)

        self.note = QLabel()
        self.note.setStyleSheet("color: #84919b; font-size: 11px;")
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.setCentralWidget(root)
        self._append("I.P.A.", "I’m ready. Configure Gemini in Settings, then click Start talking for a live voice session.")
        self._set_status("idle")

    def _append(self, speaker: str, text: str) -> None:
        safe = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.chat.append(f'<span style="color:#d99a4e"><b>{speaker}</b></span> &nbsp; {safe}')

    def _set_status(self, state: str) -> None:
        self.hud.set_status(state)
        suffix = "GEMINI CONFIGURED" if self.assistant.gemini_configured else "SET UP GEMINI"
        self.status_label.setText(f"{state.upper()} · {suffix}")
        if state.lower() in {"listening", "speaking"}:
            self.note.setText("Live voice is active. Microphone audio is being streamed to Google. Click Stop talking to end.")
        elif state.lower() == "connecting":
            self.note.setText("Connecting to Gemini Live…")
        else:
            self.note.setText("Microphone is off. Start talking to open a live session; typed chat remains available.")

    def _send(self) -> None:
        text = self.input.text().strip()
        if not text or (self._ask_worker and self._ask_worker.isRunning()):
            return
        self.input.clear()
        self._append("YOU", text)
        self._set_status("thinking")
        self.input.setEnabled(False)
        self.send_btn.setEnabled(False)
        self._ask_worker = AskWorker(self.assistant, text)
        self._ask_worker.completed.connect(self._on_answer)
        self._ask_worker.start()

    def _on_answer(self, response: str) -> None:
        self._append(self.settings.assistant_name, response)
        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.input.setFocus()
        self._set_status("idle")

    def _api_key(self) -> str | None:
        key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if key:
            return key
        try:
            return load_api_key()
        except CredentialStoreError:
            return None

    def _toggle_talk(self) -> None:
        if self._live_worker and self._live_worker.isRunning():
            self._live_worker.stop()
            self.talk_button.setText("Starting to stop…")
            self.talk_button.setEnabled(False)
            return
        api_key = self._api_key()
        if not api_key:
            QMessageBox.information(self, "Gemini key needed", "Open Settings and add your Gemini API key first.")
            return
        model = self.settings.live_model
        self._live_worker = LiveVoiceWorker(api_key, model)
        self._live_worker.status_changed.connect(self._set_status)
        self._live_worker.transcript.connect(self._on_transcript)
        self._live_worker.failed.connect(self._on_voice_error)
        self._live_worker.finished.connect(self._on_live_finished)
        self.talk_button.setText("Stop talking")
        self._live_worker.start()

    def _on_transcript(self, line: str) -> None:
        if ":" in line:
            speaker, text = line.split(":", 1)
            self._append(speaker, text.strip())
            if speaker == "I.P.A.":
                self.assistant.state.last_response = text.strip()

    def _on_voice_error(self, message: str) -> None:
        self._append("SYSTEM", message)
        QMessageBox.warning(self, "Voice conversation", message)

    def _on_live_finished(self) -> None:
        self.talk_button.setEnabled(True)
        self.talk_button.setText("Start talking")
        self._set_status("idle")

    def _show_settings(self) -> None:
        dialog = ApiKeyDialog(self, self.assistant.gemini_configured)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        api_key = dialog.api_key
        if not api_key:
            QMessageBox.information(self, "Gemini", "No changes made.")
            return
        try:
            save_api_key(api_key)
            self.assistant.refresh_saved_api_key()
            QMessageBox.information(self, "Gemini connected", "Your key was saved securely.")
        except CredentialStoreError as exc:
            QMessageBox.warning(self, "Secure storage unavailable", f"{exc}\n\nSet GOOGLE_API_KEY in your shell or local .env file instead.")
        self._set_status("idle")

    def _show_memory(self) -> None:
        facts = self.memory_store.load()
        body = "\n".join(f"{key}: {value}" for key, value in facts.items()) or "No saved memories yet."
        QMessageBox.information(self, "Local memory", body)

    def closeEvent(self, event) -> None:
        if self._live_worker and self._live_worker.isRunning():
            self._live_worker.stop()
            self._live_worker.wait(4000)
        if self._ask_worker and self._ask_worker.isRunning():
            self._ask_worker.wait(1500)
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
