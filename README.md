# Ian's Personal Assistant (I.P.A.)

An original, macOS-first desktop assistant prototype with a custom amber animated HUD and local memory.

## Current prototype
- Animated amber holographic-style sphere with idle motion and status states.
- Text conversation window.
- Local key/value memory (`remember key = value`, `forget key`, `what do you remember`).
- Memory viewer and settings information.
- Optional macOS speech output using the built-in `say` command.
- A separate data panel appears when you explicitly ask to show a response on screen.

## Not connected yet
This is an early prototype, not a fully capable AI assistant. It does not yet connect to an AI model or capture microphone audio. General messages receive a transparent prototype response rather than an AI-generated answer. The microphone input and secure phone access are future work.

## Run on macOS
Requires Python 3.10+ and Qt for Python (PyQt6).

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On macOS, click **Speak reply** to read the latest response aloud. To save a memory, type for example:

```text
remember favorite color = amber
```

Use **Memory** to view saved facts. Memory is stored in `data/memory.json` and is excluded from Git. Type `forget favorite color` to remove one fact.

To reveal a response in the separate display panel, include a phrase such as `show that on screen` in your message. Normal responses are not automatically copied into that panel.

## Project layout
- `main.py` — desktop application and UI wiring
- `app/assistant.py` — local prototype response and memory commands
- `app/config.py` — app settings
- `app/memory.py` — local JSON memory
- `app/ui/hud.py` — original animated core renderer

## Privacy and safety
The app has no model or network connection at this stage. Do not put secrets in memory. Review the dependency licenses and the applicable AI provider terms before adding a service or distributing the app.
