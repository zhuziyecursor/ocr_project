from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment or config.yaml"""

    # Application
    APP_NAME: str = "审计文档处理系统"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://ocr_user:ocr_password@localhost:5432/ocr_services"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "documents"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # File upload
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB
    ALLOWED_EXTENSIONS: set = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".docx", ".xlsx"}

    # Processing
    SMALL_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB
    SMALL_FILE_PAGES: int = 10
    CHUNK_SIZE: int = 50  # pages per chunk

    # OpenDataLoader
    OPENDATALOADER_HOST: str = "localhost"
    OPENDATALOADER_PORT: int = 5002

    # Storage
    STORAGE_TYPE: str = "local"  # "local" or "minio"
    LOCAL_STORAGE_PATH: str = "/data/recognition_results"

    # Default admin account
    DEFAULT_ADMIN_USER: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"

    # LLM (豆包大模型)
    LLM_API_KEY: str = "ark-61add44d-80bc-4fe5-868e-d66b81c9554f-afd44"
    LLM_MODEL: str = "doubao-coder"

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
