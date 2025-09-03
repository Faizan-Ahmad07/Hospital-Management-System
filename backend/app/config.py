from pydantic import BaseModel
import os
from functools import lru_cache

class Settings(BaseModel):
    APP_NAME: str = "Hospital Management System"
    ENV: str = os.getenv("ENV", "dev")
    DEBUG: bool = ENV == "dev"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+pymysql://Testing:1234@localhost:3306/hms_db")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change_me_secret")
    JWT_REFRESH_SECRET_KEY: str = os.getenv("JWT_REFRESH_SECRET_KEY", "change_me_refresh")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    PASSWORD_HASH_SCHEME: str = "bcrypt"
    AES_ENCRYPTION_KEY: str = os.getenv("AES_ENCRYPTION_KEY", "16byteslongkey!!")  # EXACTLY 16/24/32 bytes

@lru_cache
def get_settings() -> Settings:
    return Settings()