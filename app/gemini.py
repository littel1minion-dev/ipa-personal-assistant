from __future__ import annotations

from pathlib import Path

from google import genai
from google.genai import types


class GeminiConfigurationError(RuntimeError):
    """Gemini credentials or SDK are not configured."""


class GeminiRequestError(RuntimeError):
    """The Gemini service could not complete a request."""


class GeminiClient:
    def __init__(self, model: str, api_key: str | None = None):
        self.model = model
        try:
            self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
        except Exception as exc:
            raise GeminiConfigurationError("check the API key and google-genai installation") from exc

    def generate(self, prompt: str, history: list[tuple[str, str]]) -> str:
        contents = [
            "You are I.P.A., a helpful and concise desktop assistant. Be transparent about uncertainty. "
            "Do not claim to perform actions unless an enabled integration actually did them."
        ]
        contents.extend(f"{role}: {message}" for role, message in history[-12:])
        contents.append(f"user: {prompt}")
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents="\n\n".join(contents),
                config=types.GenerateContentConfig(temperature=0.7, max_output_tokens=1024),
            )
            text = (response.text or "").strip()
            if not text:
                raise GeminiRequestError("Gemini returned an empty response")
            return text
        except GeminiRequestError:
            raise
        except Exception as exc:
            raise GeminiRequestError("check connection, API key, and model availability") from exc

    def close(self) -> None:
        self.client.close()
