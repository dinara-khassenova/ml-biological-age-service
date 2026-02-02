from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    #  Application setting 
    APP_NAME:  Optional[str] = None
    DEBUG: Optional[bool] = None
    APP_DESCRIPTION:  Optional[str] = None
    API_VERSION:  Optional[str] = None
    APP_HOST: Optional[str] = None
    APP_PORT: Optional[int] = None 

    #  Database setting  
    POSTGRES_HOST: Optional[str] = None
    POSTGRES_PORT: Optional[int] = None
    POSTGRES_DB: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None

    # JWT settings for Bearer authentication 
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore" 
    )

    @property
    def DATABASE_URL_asyncpg(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_psycopg(self) -> str:
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def validate(self) -> None:
        if not all(
            [
                self.POSTGRES_HOST,
                self.POSTGRES_PORT,
                self.POSTGRES_DB,
                self.POSTGRES_USER,
                self.POSTGRES_PASSWORD,
            ]
        ):
            raise ValueError(
                "Missing required database configuration"
            )
        
        if not self.JWT_SECRET_KEY:
            raise ValueError("Missing JWT_SECRET_KEY in env")

@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate()
    return settings
