from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App-wide settings."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    MAX_RETRIES = 5
    api_url: str = "https://api.example.com/v1"
    model: str = "example-model"
    timeout_s: float = 30.0


settings = Settings()
