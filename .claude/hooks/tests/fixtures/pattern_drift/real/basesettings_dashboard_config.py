import os

from pydantic_settings import BaseSettings, SettingsConfigDict

_PREFIX = "DASHBOARD_"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix=_PREFIX, extra="ignore")

    refresh_seconds: int = 60
