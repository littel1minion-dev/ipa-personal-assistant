# Ian's Personal Assistant (I.P.A.)

An original, macOS-first desktop assistant prototype with a procedural amber HUD, local memory, and optional Gemini chat.

## Add your Gemini key from inside the app
1. Start I.P.A. using the run steps below.
2. Click **Settings**.
3. Paste your Gemini API key into the password field and click **Save**.
4. Send a message to test the connection.

The key is stored using the operating system's credential manager (macOS Keychain, Windows Credential Manager, or the configured Linux keyring), not in the repository or a plain-text settings file. If secure storage is unavailable, the app offers a session-only option; that key is discarded when the app closes. Do not share your key. Messages you send to Gemini are sent to Google, so avoid including sensitive information.

You can alternatively set `GOOGLE_API_KEY` in a local `.env` file. `.env` is ignored by Git.

## Run on macOS
Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

## Current features
- Original animated amber particle sphere and scanner-style interface.
- Gemini chat with conversation context in the current app session.
- API calls in a background thread, keeping the UI responsive.
- Key/value local memory commands: `remember key = value`, `forget key`, and `what do you remember`.
- macOS speech output using the built-in `say` command.

Memory is stored in `data/memory.json`, which is excluded from Git. Microphone input and speech transcription are not implemented yet.

## Project layout
- `main.py` — desktop UI, settings dialog, and background worker
- `app/assistant.py` — local commands and Gemini orchestration
- `app/credentials.py` — secure OS credential store integration
- `app/gemini.py` — Gemini SDK wrapper
- `app/config.py` — app settings
- `app/memory.py` — local JSON memory
- `app/ui/hud.py` — original procedural HUD renderer

## Privacy notes
Keep the API key private. Typed prompts are sent to Gemini when configured. Local memory commands are handled on-device. Review Gemini's current terms and billing/quotas before use.
