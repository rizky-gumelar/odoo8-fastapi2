from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ODOO_URL: str
    ODOO_DB: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60

    class Config:
        env_file = ".env"

settings = Settings()
