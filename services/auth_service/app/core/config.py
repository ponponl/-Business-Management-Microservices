import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Auth Service"
    
    # Đọc DATABASE_URL từ compose: postgresql://admin:password123@postgres-auth:5432/db_auth
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://admin:password123@localhost:5431/db_auth")
    
    # Đọc REDIS_URL từ compose: redis://redis:6379/0
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6380/0")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    
    # Mặc định kết nối tới Kafka service tên 'kafka' ở cổng internal '29092'
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    
    # Đọc JWT_SECRET từ compose
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET", "super_secret_jwt_key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()