import os
from typing import Any

from infisical_sdk import InfisicalSDKClient  # noqa: PLC0415
from pydantic import SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class InfisicalSettingsSource(PydanticBaseSettingsSource):
    """Fetch secrets from Infisical via Universal Auth. No-op without INFISICAL_CLIENT_ID."""

    _PATHS = ["/prosper"]

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:  # type: ignore[override]
        return None, field_name, False

    def field_is_complex(self, field: Any) -> bool:  # type: ignore[override]
        return False

    def __call__(self) -> dict[str, Any]:
        client_id = os.environ.get("INFISICAL_CLIENT_ID")
        if not client_id:
            return {}
        client_secret = os.environ.get("INFISICAL_CLIENT_SECRET", "")
        project_id = os.environ.get("INFISICAL_PROJECT_ID", "")
        env_slug = os.environ.get("INFISICAL_ENV", "prod")

        client = InfisicalSDKClient(host="https://app.infisical.com")
        client.auth.universal_auth.login(
            client_id=client_id,
            client_secret=client_secret,
        )
        from infisical_sdk.infisical_requests import APIError  # noqa: PLC0415

        secrets: dict[str, Any] = {}
        for path in self._PATHS:
            try:
                response = client.secrets.list_secrets(
                    project_id=project_id,
                    environment_slug=env_slug,
                    secret_path=path,
                    view_secret_value=True,
                )
                prefix = (
                    self.settings_cls.model_config.get("env_prefix") or ""
                ).lower()
                for s in response.secrets:
                    key = s.secretKey.lower()
                    if prefix and key.startswith(prefix):
                        key = key[len(prefix) :]
                    secrets[key] = s.secretValue
            except APIError:
                pass  # path not found or not yet created — skip
        return secrets


class InfisicalBaseSettings(BaseSettings):
    """Shared Infisical + ``PROSPER_`` env prefix for domain Settings classes."""

    model_config = SettingsConfigDict(
        env_prefix="PROSPER_",
        extra="ignore",
        env_nested_delimiter="__",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            InfisicalSettingsSource(settings_cls),
            env_settings,
            dotenv_settings,
            init_settings,
        )


class Settings(InfisicalBaseSettings):
    """App-wide secrets and OpenRouter (LLM gateway) settings."""

    openrouter_api_key: SecretStr | None = None
    openrouter_url: str = "https://openrouter.ai/api/v1"
    openrouter_http_referer: str = "https://prospers.fr"
    openrouter_app_title: str = "Prosper"
    openrouter_model: str = "google/gemini-2.5-flash-lite"

    embedding_model: str = "openai/text-embedding-3-small"
    embedding_dimensions: int = 1536
    tagging_model: str = "anthropic/claude-haiku-4.5"

    icp_chat_model: str = "mistralai/mistral-medium-3-5"
    icp_chat_max_tool_calls: int = 5
    icp_chat_max_messages: int = 40
    icp_chat_max_messages_per_day: int = 200
    monthly_llm_cap_usd: float = 5.0
    delivery_reason_model: str = "mistralai/mistral-medium-3-5"
    # Site profile (crawl pilot 2026-11-05: 49/50 usable, ~0.58 $ / 1 000 sites).
    site_profile_model: str = "mistralai/mistral-small-3.2-24b-instruct"


def openrouter_headers(settings: Settings, feature: str) -> dict[str, str]:
    """OpenRouter app attribution: one referer for the app, and a title naming the
    environment and the feature, so every call is identifiable in OpenRouter's logs
    (e.g. "Prosper preprod - icp-chat"). Header values must stay ASCII."""
    env = os.environ.get("PROSPER_ENVIRONMENT") or "local"
    return {
        "HTTP-Referer": settings.openrouter_http_referer,
        "X-Title": f"{settings.openrouter_app_title} {env} - {feature}",
    }


settings = Settings()
