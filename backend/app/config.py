from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./vista.db"
    jwt_secret: str
    jwt_minutes: int = 60
    bcrypt_rounds: int = 12
    cors_origins: str = ""
    organiser_code: str = ""
    security_code: str = ""
    # People per square metre that counts as 100% occupancy of a zone.
    # TODO(team): confirm this value against the Fruin source before the viva.
    ref_density: float = 1.08

    @field_validator("jwt_secret")
    @classmethod
    def _secret_ok(cls, v: str) -> str:
        if len(v) < 16 or v.lower().startswith("change-me"):
            raise ValueError("JWT_SECRET must be a random string of at least 16 characters")
        return v

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
