import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    # Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    
    # Google
    GOOGLE_DRIVE_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    GMAIL_USER_EMAIL: str = os.getenv("GMAIL_USER_EMAIL")
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID")
    
    # Application
    APPROVAL_TIMEOUT_HOURS: int = int(os.getenv("APPROVAL_TIMEOUT_HOURS", "48"))
    MAX_APPLICATIONS_PER_DAY: int = int(os.getenv("MAX_APPLICATIONS_PER_DAY", "20"))
    SCHEDULER_INTERVAL_MINUTES: int = int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "30"))
    
    # Paths
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/career_copilot.db")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/careercopilot.log")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"

settings = Settings()