from __future__ import annotations

import subprocess
import sys

from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from app.assistant import PersonalAssistant
from app.config import DEFAULT_SETTINGS
from app.credentials import CredentialStoreError, delete_api_key, save_api_key
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
            "Paste your Gemini API key below. I.P.A. stores it in your operating system’s "
            "secure credential store (Keychain on macOS, Credential Manager on Windows, "
            "or the configured keyring on Linux). The key is not written to the project files."
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

        self.note = QLabel()
        self.note.setStyleSheet("color: #84919b; font-size: 11px;")
        layout.addWidget(self.note)
        self.setCentralWidget(root)
        self._append("I.P.A.", "I’m ready. Configure Gemini in Settings to begin, or use local memory commands.")
        self._set_status("idle")
        self._speech_timer = QTimer(self)
        self._speech_timer.timeout.connect(self._check_speech)

    def _append(self, speaker: str, text: str) -> None:
        safe = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.chat.append(f'<span style="color:#d99a4e"><b>{speaker}</b></span> &nbsp; {safe}')

    def _set_status(self, state: str) -> None:
        self.hud.set_status(state)
        suffix = "GEMINI CONFIGURED" if self.assistant.gemini_configured else "SET UP GEMINI"
        self.status_label.setText(f"{state.upper()} · {suffix}")
        self.note.setText(
            "Gemini configured · normal prompts are sent to Google." if self.assistant.gemini_configured
            else "Open Settings to enter your Gemini API key. Microphone input is not implemented yet."
        )

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
            self.assistant.set_api_key(None)
            QMessageBox.information(self, "Gemini connected", "Your key was saved securely. Send a message to test the connection.")
        except CredentialStoreError as exc:
            choice = QMessageBox.question(
                self, "Secure storage unavailable",
                f"{exc}. Use this key for this app session only? It will not be saved and will be lost when I.P.A. closes.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if choice == QMessageBox.StandardButton.Yes:
                self.assistant.set_api_key(api_key)
                QMessageBox.information(self, "Gemini configured", "The key is active for this session only.")
        self._set_status("idle")

    def _show_memory(self) -> None:
        facts = self.memory_store.load()
        body = "\n".join(f"{key}: {value}" for key, value in facts.items()) or "No saved memories yet."
        QMessageBox.information(self, "Local memory", body)

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

    def closeEvent(self, event) -> None:
        if self._speech_process and self._speech_process.poll() is None:
            self._speech_process.terminate()
        if self._worker and self._worker.isRunning():
            self._worker.wait(1500)
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
