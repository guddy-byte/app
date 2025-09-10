from pydantic import BaseSettings
from typing import List

class Settings(BaseSettings):
    PAYSTACK_SECRET_KEY: str
    PAYSTACK_PUBLIC_KEY: str = None
    PAYSTACK_API_URL: str = "https://api.paystack.co"
    CALLBACK_URL: str = "http://localhost:3000/payment/callback"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def get_settings() -> Settings:
    return Settings()
