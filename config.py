from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    WHATSAPP_TOKEN: str
    WHATSAPP_PHONE_NUMBER_ID: str
    GEMINI_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()