import os

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://admin:password123@localhost:5434/db_production")
    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6380')}/0",
    )
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super_secret_jwt_key")
    ALGORITHM: str = "HS256"

settings = Settings()
