from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "PicRout"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    SECRET_KEY: str = "cambia_esta_clave_por_una_muy_segura_y_larga"

    DATABASE_URL: str = "sqlite:///./app_routines.db"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    OTP_EXPIRE_MINUTES: int = 10

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@picrout.app"

    STORAGE_PATH: str = "./storage/uploads"
    MAX_PHOTO_SIZE_MB: int = 10

    ADMIN_EMAILS: str = "admin@picrout.app"

    # --- IA (prioridad: gratis primero) ---
    # true = usar LLM cloud si hay alguna key; false = solo heurísticas locales
    AI_USE_LLM: bool = True

    # 1) Groq – GRATIS (recomendado). Key en https://console.groq.com/keys
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # 2) Google Gemini – GRATIS (AI Studio). Key en https://aistudio.google.com/apikey
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # 3) xAI / Grok – opcional (suele requerir créditos)
    XAI_API_KEY: str = ""
    XAI_MODEL: str = "grok-4"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
