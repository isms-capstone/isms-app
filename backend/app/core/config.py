from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "ISMS Backend"
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "SUPER_SECRET_KEY_ISMS_2026_CHANGE_IN_PROD"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database Configuration
    MARIADB_SERVER: str = "db"
    MARIADB_PORT: int = 3306
    MARIADB_USER: str = "isms_user"
    MARIADB_PASSWORD: str = "isms_password"
    MARIADB_DB: str = "isms_db"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://"
            f"{self.MARIADB_USER}:{self.MARIADB_PASSWORD}"
            f"@{self.MARIADB_SERVER}:{self.MARIADB_PORT}"
            f"/{self.MARIADB_DB}"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()