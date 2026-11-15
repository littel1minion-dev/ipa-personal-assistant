# Ian's Personal Assistant (I.P.A.)

An original personal AI companion built for a personal desktop experience.

This project is intentionally independent and fresh: it has its own codebase, naming, and design direction rather than copying any prior implementation.

## Features planned
- Voice-first personal assistant
- Local memory store
- Animated HUD with an amber core
- Status states: listening, thinking, speaking
- Task and reminder primitives
- Expandable architecture for future integrations

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Structure

- `app/assistant.py` — assistant logic
- `app/config.py` — settings and configuration
- `app/memory.py` — local memory persistence
- `app/ui/hud.py` — animated desktop HUD
- `main.py` — app entry point

## Notes

This is a starter foundation for a personal assistant product. It is intentionally easy to extend with voice models, task automation, and richer personal memory in later iterations.
