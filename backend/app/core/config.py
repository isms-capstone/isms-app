from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "ISMS API"
    APP_ENV: str = "local"
    PORT: int = 3000

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "isms_user"
    DB_PASSWORD: str = "isms_password"
    DB_NAME: str = "isms_db"

    JWT_SECRET_KEY: str = "dev_secret_key_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
