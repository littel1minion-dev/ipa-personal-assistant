# Ian's Personal Assistant (I.P.A.)

An original, macOS-first desktop assistant prototype with a procedural amber HUD, local memory, and optional Gemini text chat.

## Current features
- Original animated amber particle sphere and scanner-style interface.
- Text chat with Gemini using Google's `google-genai` Python SDK.
- Conversation context retained in the current app session.
- Local key/value memory commands: `remember key = value`, `forget key`, and `what do you remember`.
- Memory viewer.
- macOS speech output using the built-in `say` command.
- API requests run in a background thread so the interface remains responsive.

## Configure Gemini
1. Create a Gemini API key in Google AI Studio.
2. Copy `.env.example` to `.env` in the project root.
3. Put your key in `.env` as `GOOGLE_API_KEY=your_key_here`.
4. Restart I.P.A.

Never commit `.env` or paste an API key into Python source. `.env` is ignored by Git. Requests typed into I.P.A. are sent to Google's Gemini API when the key is configured; avoid entering sensitive information unless you are comfortable sending it to that provider. Local `remember`/`forget` commands are handled on-device and are not sent as Gemini prompts.

## Run on macOS
Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your Gemini API key, then:
python main.py
```

Windows PowerShell equivalent for activating the venv is `.venv\\Scripts\\Activate.ps1`; launch using `python main.py`.

To save a local memory, type e.g. `remember favorite color = amber`. Use the **Memory** button to inspect saved facts or `forget favorite color` to remove one. Memory is stored in `data/memory.json`, which is excluded from Git.

On macOS, click **Speak reply** to read the latest assistant reply aloud. Microphone capture and speech transcription are not implemented yet; voice input is a future step.

## Model setting
The default model is `gemini-2.5-flash`. Override it in `.env` with `GEMINI_MODEL=...` if you want to use another model available to your API key.

## Layout
- `main.py` — desktop UI and background worker
- `app/assistant.py` — local commands and assistant turn handling
- `app/gemini.py` — Gemini SDK wrapper
- `app/config.py` — app settings
- `app/memory.py` — local JSON memory
- `app/ui/hud.py` — original procedural HUD renderer

## Privacy notes
This is an early prototype, not an always-listening assistant. It does not record audio. Keep API keys private, review Gemini's current terms and billing/quotas, and do not send confidential prompts unless permitted by your policies.
