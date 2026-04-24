from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./traveller.db"
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_prefix": "TRAVELLER_", "env_file": ".env"}


settings = Settings()
