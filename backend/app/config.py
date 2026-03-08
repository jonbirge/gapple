from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # Encryption
    gapple_encryption_key: str = ""

    # App
    gapple_base_url: str = "http://localhost:8000"
    gapple_db_path: str = "./data/gapple.db"
    gapple_log_level: str = "info"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
