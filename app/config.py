import os

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General Settings
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "Expense Tracker API"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    API_V2_STR: str = "/api/v2"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60

    # Security
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    OPENAPI_ENABLED: bool = True
    TRUSTED_HOSTS: str = "localhost,127.0.0.1,api"

    # Primary Database (Write)
    DB_HOST: str = "postgres"
    DB_PORT: int = 5432
    DB_USER: str = "expense_user"
    DB_PASSWORD: str
    DB_NAME: str = "expense_tracker"

    # Read Replica Database (Optional)
    DB_READ_HOST: str | None = None
    DB_READ_PORT: int | None = None
    DB_READ_USER: str | None = None
    DB_READ_PASSWORD: str | None = None
    DB_READ_NAME: str | None = None

    # Redis Config
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str

    # Observability
    GRAFANA_PASSWORD: str = "grafana_secure_pass_123"
    OTEL_EXPORTER_ENDPOINT: str = "http://jaeger:4317"

    # SMTP Configurations
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str = "noreply@expensetracker.com"
    SMTP_FROM_NAME: str = "Expense Tracker API"

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """Construct SQLAlchemy Async database connection string."""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @computed_field
    @property
    def DATABASE_READ_URL(self) -> str:
        """Construct SQLAlchemy Async read-replica connection string."""
        host = self.DB_READ_HOST or self.DB_HOST
        port = self.DB_READ_PORT or self.DB_PORT
        user = self.DB_READ_USER or self.DB_USER
        password = self.DB_READ_PASSWORD or self.DB_PASSWORD
        name = self.DB_READ_NAME or self.DB_NAME
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"

    @computed_field
    @property
    def REDIS_URL(self) -> str:
        """Construct Redis connection string."""
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @computed_field
    @property
    def CELERY_BROKER_URL(self) -> str:
        """Celery broker url using Redis."""
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/1"

    @computed_field
    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        """Celery result backend using Redis."""
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/2"

    @property
    def is_dev(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"

    @property
    def is_prod(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_test(self) -> bool:
        return self.ENVIRONMENT.lower() == "testing"

    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT.lower() == "staging"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        insecure = {
            "generate_a_secure_random_key_here_for_jwt_signing",
            "changeme",
            "dev_secret",
        }
        if value.lower() in insecure or len(value) < 32:
            env = os.getenv("ENVIRONMENT", "development").lower()
            if env in {"production", "staging"}:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters and not a default placeholder "
                    "in production or staging environments."
                )
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        if self.is_prod or self.is_staging:
            if not origins or origins == ["*"]:
                raise ValueError(
                    "CORS_ORIGINS must be an explicit comma-separated list in staging/production."
                )
        if origins == ["*"]:
            return ["*"]
        return origins

    @property
    def trusted_hosts_list(self) -> list[str]:
        return [host.strip() for host in self.TRUSTED_HOSTS.split(",") if host.strip()]

settings = Settings()
