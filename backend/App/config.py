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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()