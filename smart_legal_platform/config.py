from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SLP_", env_file=".env", extra="ignore")

    app_name: str = "Smart Legal Platform"
    jwt_secret: str = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    token_expire_minutes: int = 90
    encryption_key: str = Field(
        default="x4iJeWByTJ7RkAnVZZ3kIlqS1v6VUu6WgVUNKSBi0iE="
    )
    cloud_backup_dir: str = "cloud_backup"


@lru_cache
def get_settings() -> Settings:
    return Settings()

