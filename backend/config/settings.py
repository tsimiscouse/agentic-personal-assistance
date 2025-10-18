"""
Configuration Settings for Personal Assistant WhatsApp Bot
Uses Pydantic Settings for environment variable management
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application Settings loaded from environment variables"""

    # ============================================
    # Backend API Configuration
    # ============================================
    backend_host: str = Field(default="0.0.0.0", env="BACKEND_HOST")
    backend_port: int = Field(default=8000, env="BACKEND_PORT")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")

    # ============================================
    # Groq API Configuration
    # ============================================
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.1-8b-instant", env="GROQ_MODEL")

    # ============================================
    # Database Configuration
    # ============================================
    database_url: str = Field(..., env="DATABASE_URL")
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")

    # ============================================
    # Vector Database (ChromaDB)
    # ============================================
    chroma_persist_directory: str = Field(
        default="../vector_store",
        env="CHROMA_PERSIST_DIRECTORY"
    )
    chroma_collection_name: str = Field(
        default="whatsapp_conversations",
        env="CHROMA_COLLECTION_NAME"
    )
    embedding_model: str = Field(
        default="sentence-transformers",
        env="EMBEDDING_MODEL"
    )
    embedding_model_name: str = Field(
        default="all-MiniLM-L6-v2",
        env="EMBEDDING_MODEL_NAME"
    )
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")

    # ============================================
    # Email Configuration
    # ============================================
    email_service: str = Field(default="gmail", env="EMAIL_SERVICE")
    email_user: str = Field(..., env="EMAIL_USER")
    email_password: str = Field(..., env="EMAIL_PASSWORD")
    smtp_host: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_tls: bool = Field(default=True, env="SMTP_TLS")
    # IMAP for reading emails
    imap_host: str = Field(default="imap.gmail.com", env="IMAP_HOST")
    imap_port: int = Field(default=993, env="IMAP_PORT")

    # ============================================
    # Calendar Integration (Google Calendar API)
    # ============================================
    google_calendar_credentials_file: str = Field(
        default="backend/config/google_credentials.json",
        env="GOOGLE_CALENDAR_CREDENTIALS_FILE"
    )
    google_calendar_id: str = Field(default="primary", env="GOOGLE_CALENDAR_ID")
    default_timezone: str = Field(default="UTC", env="DEFAULT_TIMEZONE")
    # Deprecated
    pipedream_calendar_endpoint: Optional[str] = Field(default=None, env="PIPEDREAM_CALENDAR_ENDPOINT")

    # ============================================
    # Logging Configuration
    # ============================================
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="../logs/app.log", env="LOG_FILE")
    log_max_bytes: int = Field(default=10485760, env="LOG_MAX_BYTES")
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")

    # ============================================
    # Security Configuration
    # ============================================
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30,
        env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # ============================================
    # CORS Configuration
    # ============================================
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        env="CORS_ORIGINS"
    )

    @validator("cors_origins")
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ============================================
    # Rate Limiting
    # ============================================
    rate_limit_per_user: int = Field(default=30, env="RATE_LIMIT_PER_USER")
    rate_limit_window_seconds: int = Field(
        default=60,
        env="RATE_LIMIT_WINDOW_SECONDS"
    )

    # ============================================
    # LangChain Agent Configuration
    # ============================================
    max_agent_iterations: int = Field(default=5, env="MAX_AGENT_ITERATIONS")
    max_response_tokens: int = Field(default=1000, env="MAX_RESPONSE_TOKENS")
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")

    # ============================================
    # Memory Configuration
    # ============================================
    short_term_memory_size: int = Field(
        default=10,
        env="SHORT_TERM_MEMORY_SIZE"
    )
    long_term_memory_retrieval_count: int = Field(
        default=5,
        env="LONG_TERM_MEMORY_RETRIEVAL_COUNT"
    )

    # ============================================
    # WhatsApp Configuration
    # ============================================
    whatsapp_session_name: str = Field(
        default="whatsapp-assistant-session",
        env="WHATSAPP_SESSION_NAME"
    )
    whatsapp_timeout: int = Field(default=180000, env="WHATSAPP_TIMEOUT")

    # Access Control - Allowed WhatsApp numbers (comma-separated)
    allowed_whatsapp_numbers: str = Field(
        default="",
        env="ALLOWED_WHATSAPP_NUMBERS"
    )

    class Config:
        """Pydantic Config"""
        # Look for .env in project root (parent of backend directory)
        env_file = str(Path(__file__).resolve().parent.parent.parent / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Allow extra fields in .env (like BACKEND_API_URL for frontend)
        extra = "ignore"

    def get_absolute_path(self, relative_path: str) -> Path:
        """Convert relative path to absolute path"""
        base_dir = Path(__file__).resolve().parent.parent.parent
        return base_dir / relative_path

    @property
    def chroma_path(self) -> Path:
        """Get absolute path for ChromaDB persistence"""
        return self.get_absolute_path(self.chroma_persist_directory)

    @property
    def log_path(self) -> Path:
        """Get absolute path for log file"""
        return self.get_absolute_path(self.log_file)


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get or create Settings singleton instance

    Returns:
        Settings: Configuration settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenience function for importing
settings = get_settings()
