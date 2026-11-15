from __future__ import annotations

from google import genai
from google.genai import types


class GeminiConfigurationError(RuntimeError):
    """The Gemini SDK or credentials are not configured."""


class GeminiRequestError(RuntimeError):
    """Gemini rejected or failed to answer a request."""


class GeminiClient:
    def __init__(self, model: str):
        self.model = model
        try:
            self.client = genai.Client()
        except Exception as exc:
            raise GeminiConfigurationError("check that your API key and google-genai installation are valid") from exc

    def generate(self, prompt: str, history: list[tuple[str, str]]) -> str:
        transcript = [
            "You are I.P.A. (Ian's Personal Assistant), a calm, concise and helpful desktop assistant. "
            "Be transparent about uncertainty. Do not claim to control devices, access files, or take actions "
            "unless the user explicitly enabled an integration that can do so. Local memory commands are "
            "handled by the app and are not part of this model request."
        ]
        for role, message in history[-12:]:
            label = "User" if role == "user" else "I.P.A."
            transcript.append(f"{label}: {message}")
        transcript.append(f"User: {prompt}\nI.P.A.:")
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents="\n\n".join(transcript),
                config=types.GenerateContentConfig(temperature=0.7, max_output_tokens=1024),
            )
            answer = (response.text or "").strip()
            if not answer:
                raise GeminiRequestError("the model returned an empty response")
            return answer
        except GeminiRequestError:
            raise
        except Exception as exc:
            raise GeminiRequestError("check your internet connection, API key, and model availability") from exc

    def close(self) -> None:
        self.client.close()
