"""Shared Gemini authentication helpers for API key and ADC flows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import google.auth
    from google.auth.transport.requests import Request as GoogleAuthRequest
except ImportError:  # pragma: no cover - exercised only when ADC is configured without runtime deps
    google = None
    GoogleAuthRequest = None


GEMINI_AUTH_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/generative-language.retriever",
]
GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _load_google_credentials(credentials_path: str | None, scopes: list[str]) -> tuple[Any, str | None]:
    if google is None:
        raise ValueError("google-auth is required for Gemini ADC authentication")

    if credentials_path:
        credentials_file = Path(credentials_path).expanduser()
        credentials, project_id = google.auth.load_credentials_from_file(credentials_file, scopes=scopes)
        return credentials, project_id

    return google.auth.default(scopes=scopes)


class GeminiAuthSession:
    """Build Gemini requests using either API keys or ADC bearer tokens."""

    def __init__(self, settings: Any) -> None:
        self.settings = settings
        self.api_key = getattr(settings, "gemini_api_key", "")
        self.oauth_access_token = getattr(settings, "google_oauth_access_token", "")
        self.credentials_path = getattr(settings, "google_application_credentials", "")
        self.project_id = getattr(settings, "google_cloud_project", "")
        self.explicit_adc = bool(getattr(settings, "gemini_use_adc", False))
        self.use_adc = bool(
            self.explicit_adc
            or self.credentials_path
            or (self.project_id and not self.api_key and not self.oauth_access_token)
        )
        self._credentials: Any | None = None
        self._google_request: Any | None = None
        self._resolved_project_id = self.project_id

    def is_configured(self) -> bool:
        return bool(self.api_key or self.oauth_access_token or self.use_adc)

    def post_generate_content(
        self,
        http_client: Any,
        model: str,
        prompt: str,
        *,
        temperature: float,
        max_output_tokens: int,
    ) -> Any:
        request_kwargs = {
            "json": {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_output_tokens,
                },
            }
        }

        if self.use_adc:
            access_token, project_id = self._get_access_token()
            request_kwargs["headers"] = self._build_oauth_headers(access_token, project_id)
            return http_client.post(GEMINI_URL_TEMPLATE.format(model=model), **request_kwargs)

        if self.oauth_access_token:
            request_kwargs["headers"] = self._build_oauth_headers(self.oauth_access_token)
            return http_client.post(GEMINI_URL_TEMPLATE.format(model=model), **request_kwargs)

        if self.api_key:
            request_kwargs["params"] = {"key": self.api_key}
            return http_client.post(GEMINI_URL_TEMPLATE.format(model=model), **request_kwargs)

        raise ValueError("No Gemini credentials configured")

    def _build_oauth_headers(self, access_token: str, project_id: str | None = None) -> dict[str, str]:
        resolved_project_id = project_id or self.project_id
        if not resolved_project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT is required when using Gemini OAuth authentication")
        return {
            "Authorization": f"Bearer {access_token}",
            "x-goog-user-project": resolved_project_id,
        }

    def _get_access_token(self) -> tuple[str, str]:
        if self._credentials is None:
            self._credentials, discovered_project = _load_google_credentials(
                self.credentials_path,
                GEMINI_AUTH_SCOPES,
            )
            if not self._resolved_project_id:
                self._resolved_project_id = (
                    discovered_project
                    or getattr(self._credentials, "quota_project_id", None)
                    or ""
                )

        if not self._resolved_project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT is required when using Gemini ADC authentication")

        if self.GoogleRequestClass is None:
            raise ValueError("google-auth is required for Gemini ADC authentication")

        if self._google_request is None:
            self._google_request = self.GoogleRequestClass()

        if not getattr(self._credentials, "valid", False) or not getattr(self._credentials, "token", None):
            self._credentials.refresh(self._google_request)

        return self._credentials.token, self._resolved_project_id

    @property
    def GoogleRequestClass(self) -> Any:
        return GoogleAuthRequest