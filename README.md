# Ian's Personal Assistant (I.P.A.)

An original, macOS-first desktop assistant prototype with a procedural amber HUD, local memory, and optional Gemini voice prompts.

## Configure Gemini
1. Create a Gemini API key in Google AI Studio.
2. Start I.P.A.
3. Click **Settings** and paste your key.
4. The key is saved in the operating-system credential manager (Keychain / Credential Manager / keyring), not in the repository.

You can also set `GOOGLE_API_KEY` in a local `.env` file. `.env` is ignored by Git.

## Run
Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

## Use it
- Type in the box and press **Send**.
- Or press **Listen** to record a 5-second voice prompt, transcribe it with Gemini, and answer it.
- Press **Speak reply** to read the latest answer aloud on macOS using the built-in `say` command.

## Notes
- This version avoids the unstable Gemini Live WebSocket path and instead uses the standard `google-genai` SDK for text generation and short audio transcription.
- The app does not continuously listen in the background.
- The microphone only records a short clip when you press **Listen**.
