from pydantic import model_validator
from pydantic_settings import BaseSettings

DEVELOPMENT_SECRET = "SUPER_SECRET_KEY_ISMS_2026_CHANGE_IN_PROD"
LOCAL_ENVIRONMENTS = {"local", "test", "development", "dev"}


class Settings(BaseSettings):
    PROJECT_NAME: str = "ISMS Backend"
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = "local"
    # Initial Admin password for an empty database. Local environments fall back
    # to a documented development password; other environments must set it.
    ISMS_ADMIN_PASSWORD: str | None = None
    # Self-service portal (POR-07..09): public web address used in sign-in e-mails,
    # session length and the account recorded as creator of customer-opened cases.
    PORTAL_BASE_URL: str = "http://localhost:3100"
    PORTAL_SESSION_HOURS: int = 8
    PORTAL_INTAKE_USER_ID: int | None = None

    # Security
    SECRET_KEY: str = DEVELOPMENT_SECRET
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database Configuration
    MARIADB_SERVER: str = "db"
    MARIADB_PORT: int = 3306
    MARIADB_USER: str = "isms_user"
    MARIADB_PASSWORD: str = "isms_password"
    MARIADB_DB: str = "isms_db"

    @property
    def is_local(self) -> bool:
        return self.APP_ENV.lower() in LOCAL_ENVIRONMENTS

    @model_validator(mode="after")
    def require_strong_secret_outside_local(self):
        # A guessable signing key lets anyone mint valid access tokens.
        if not self.is_local and (self.SECRET_KEY == DEVELOPMENT_SECRET or len(self.SECRET_KEY) < 32):
            raise ValueError("SECRET_KEY must be a random value of at least 32 characters outside local use")
        return self

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