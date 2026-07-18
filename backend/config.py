import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # API Keys
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    SARVAM_API_KEY: Optional[str] = None
    OPENWEATHER_API_KEY: Optional[str] = None
    
    # Firebase
    FIREBASE_CREDENTIALS_PATH: str = "service-account.json"
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    
    model_config = SettingsConfigDict(
        # Local override is loaded after .env so a rotated key takes precedence.
        env_file=(".env", ".env.gemini-override", ".env.groq-override"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings()

# Setup Firebase environment variable if service account exists
if os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.FIREBASE_CREDENTIALS_PATH
