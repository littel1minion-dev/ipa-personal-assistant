from __future__ import annotations

import keyring

SERVICE_NAME = "ipa-personal-assistant"
ACCOUNT_NAME = "gemini-api-key"


class CredentialStoreError(RuntimeError):
    """The operating system credential store is unavailable."""


def load_api_key() -> str | None:
    try:
        return keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
    except Exception as exc:
        raise CredentialStoreError("the operating system's secure credential store is unavailable") from exc


def save_api_key(api_key: str) -> None:
    try:
        keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, api_key)
    except Exception as exc:
        raise CredentialStoreError("could not save the key to the operating system's secure credential store") from exc


def delete_api_key() -> None:
    try:
        keyring.delete_password(SERVICE_NAME, ACCOUNT_NAME)
    except keyring.errors.PasswordDeleteError:
        pass
    except Exception as exc:
        raise CredentialStoreError("could not remove the key from the operating system's secure credential store") from exc
