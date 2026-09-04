import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Contract Service"

    # Database
    DATABASE_URL: str = (
        "postgresql://admin:password123@postgres-contract:5432/db_contract"
    )

    # Redis
    REDIS_URL: str = "redis://redis-cache:6379/0"
    REDIS_HOST: str = "redis-cache"
    REDIS_PORT: int = 6379

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_CONTRACT_TOPIC: str = "contract.events"

    CONTRACT_TIMEZONE: str = "Asia/Ho_Chi_Minh"
    CONTRACT_LIFECYCLE_INTERVAL_SECONDS: int = 15

    # JWT Authentication
    JWT_SECRET: str = "your_jwt_secret_key"
    JWT_ALGORITHM: str = "HS256"
    
    ATTACHMENT_STORAGE_PATH: str = os.getenv(
    "ATTACHMENT_STORAGE_PATH",
    "/app/storage/attachments",
)

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
