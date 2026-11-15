# I.P.A. — Ian's Personal Assistant

An original desktop assistant with an amber HUD and optional **live, two-way Gemini voice conversation**.

## Run
Python 3.10+ is recommended.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

## Connect Gemini
Start the app, click **Gemini settings**, paste your key, and save. The key is stored using the OS credential manager (macOS Keychain, Windows Credential Manager, or the Linux keyring backend). Alternatively, define `GOOGLE_API_KEY` in the environment or a local `.env` file; `.env` is ignored by Git.

Create keys in [Google AI Studio](https://aistudio.google.com/app/apikey). Keep the key private. Gemini Live API access and model availability can depend on account, region, and current Google offering.

## Talk naturally
1. Click **Start talking** and allow microphone access if your OS asks.
2. Speak normally; audio is streamed live to Gemini and the response is played through your default speakers/headphones.
3. Click **End conversation** to stop microphone streaming.

This is not an always-listening app: the microphone starts only after you click **Start talking**, and stops when the session ends or the app closes. Live speech is sent to Google's Gemini service for processing. Use headphones to reduce speaker echo. The app expects mono 16 kHz PCM microphone input and plays mono 24 kHz PCM output.

The default Live API model can be overridden with `GEMINI_LIVE_MODEL` if Google changes model availability or your account uses a different model. The microphone, Live API, network, and platform audio backends must be available. Linux may require installing PortAudio and configuring a Secret Service keyring.

## Local memory
Memory is stored in `data/memory.json` and excluded from Git. The Memory button shows existing facts. Local memory commands are available in the retained assistant module, but the live voice UI does not currently execute actions based on speech.

## Structure
- `main.py` — desktop UI, credential setup, live voice controls
- `app/audio.py` — live microphone and audio playback worker
- `app/gemini.py` — Gemini text client
- `app/credentials.py` — operating-system credential store
- `app/assistant.py` — local commands and text assistant
- `app/ui/hud.py` — HUD visualizer
