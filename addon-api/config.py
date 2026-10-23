"""
Configuration management for the Addon Generator API.
Uses pydantic-settings for type-safe environment variable loading.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    APP_NAME: str = "Addon Generator API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # -------------------------------------------------------------------------
    # Server
    # -------------------------------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1

    # -------------------------------------------------------------------------
    # Database (PostgreSQL via asyncpg)
    # -------------------------------------------------------------------------
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/addon_generator"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # -------------------------------------------------------------------------
    # Redis (for queue, caching, rate limiting)
    # -------------------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 20

    # -------------------------------------------------------------------------
    # LLM Providers - API Keys
    # -------------------------------------------------------------------------
    # OpenRouter (gateway to GPT-4o, Claude, DeepSeek, Gemini, Llama, etc.)
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_DEFAULT_MODEL: str = "openai/gpt-4o-mini"
    OPENROUTER_FREE_MODEL: str = "deepseek/deepseek-chat:free"

    # Groq (fast, free tier)
    GROQ_API_KEY: Optional[str] = None
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_DEFAULT_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_FAST_MODEL: str = "llama-3.1-8b-instant"

    # Together AI (free tier, FLUX for images)
    TOGETHER_API_KEY: Optional[str] = None
    TOGETHER_BASE_URL: str = "https://api.together.xyz/v1"
    TOGETHER_DEFAULT_MODEL: str = "meta-llama/Llama-3.1-405B-Instruct-Turbo"
    TOGETHER_FLUX_MODEL: str = "black-forest-labs/FLUX.1-schnell-Free"

    # Google AI Studio (Gemini, free tier)
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_DEFAULT_MODEL: str = "gemini-1.5-flash"
    GOOGLE_PRO_MODEL: str = "gemini-1.5-pro"

    # Direct OpenAI (optional, if you have key)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_DEFAULT_MODEL: str = "gpt-4o-mini"

    # Direct Anthropic (optional, if you have key)
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_DEFAULT_MODEL: str = "claude-3-5-sonnet-20241022"

    # Direct DeepSeek (optional, cheap)
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_DEFAULT_MODEL: str = "deepseek-chat"

    # Local Ollama (optional, for privacy)
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_DEFAULT_MODEL: str = "llama3.3:70b"

    # -------------------------------------------------------------------------
    # LLM Router Configuration
    # -------------------------------------------------------------------------
    # Default provider for each task type
    ROUTER_DEFAULT_PROVIDER: Literal[
        "openrouter", "groq", "together", "google", "openai", "anthropic", "deepseek", "ollama"
    ] = "groq"

    # Enable/disable providers
    ENABLE_OPENROUTER: bool = True
    ENABLE_GROQ: bool = True
    ENABLE_TOGETHER: bool = True
    ENABLE_GOOGLE: bool = True
    ENABLE_OPENAI: bool = False
    ENABLE_ANTHROPIC: bool = False
    ENABLE_DEEPSEEK: bool = False
    ENABLE_OLLAMA: bool = False

    # Rate limiting (requests per minute per provider)
    RATE_LIMIT_GROQ: int = 30
    RATE_LIMIT_TOGETHER: int = 60
    RATE_LIMIT_OPENROUTER: int = 20
    RATE_LIMIT_GOOGLE: int = 15
    RATE_LIMIT_OPENAI: int = 10
    RATE_LIMIT_ANTHROPIC: int = 10
    RATE_LIMIT_DEEPSEEK: int = 30
    RATE_LIMIT_OLLAMA: int = 100

    # -------------------------------------------------------------------------
    # Image Generation
    # -------------------------------------------------------------------------
    # Together AI FLUX
    TOGETHER_IMAGE_MODEL: str = "black-forest-labs/FLUX.1-schnell-Free"
    TOGETHER_IMAGE_STEPS: int = 4
    TOGETHER_IMAGE_WIDTH: int = 1024
    TOGETHER_IMAGE_HEIGHT: int = 1024

    # Replicate (optional)
    REPLICATE_API_TOKEN: Optional[str] = None

    # Hugging Face (optional)
    HF_API_TOKEN: Optional[str] = None

    # -------------------------------------------------------------------------
    # 3D Generation
    # -------------------------------------------------------------------------
    HUNYUAN3D_API_URL: str = "https://api.hunyuan3d.com/v1"
    HUNYUAN3D_API_KEY: Optional[str] = None
    TRIPO3D_API_URL: str = "https://api.tripo3d.ai/v1"
    TRIPO3D_API_KEY: Optional[str] = None
    MESHY_API_URL: str = "https://api.meshy.ai/v1"
    MESHY_API_KEY: Optional[str] = None

    # -------------------------------------------------------------------------
    # Audio Generation
    # -------------------------------------------------------------------------
    ELEVENLABS_API_KEY: Optional[str] = None
    BARK_API_URL: str = "https://api.bark.suno.ai/v1"

    # -------------------------------------------------------------------------
    # Minecraft Specific
    # -------------------------------------------------------------------------
    MINECRAFT_MIN_VERSION: str = "26.40"
    SUPPORTED_EDITIONS: list[str] = ["bedrock", "java", "both"]
    DEFAULT_EDITION: str = "bedrock"

    # Bedrock JSON Schemas (for validation)
    BEDROCK_SCHEMAS_URL: str = "https://raw.githubusercontent.com/bedrock-studio/bedrock-json-schemas/main/schemas"

    # -------------------------------------------------------------------------
    # File Storage / Output
    # -------------------------------------------------------------------------
    OUTPUT_DIR: str = "./output"
    TEMP_DIR: str = "./temp"
    MAX_FILE_SIZE_MB: int = 100

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:3001", "*"]
    )

    # -------------------------------------------------------------------------
    # Task Queue (Celery-like using Redis)
    # -------------------------------------------------------------------------
    TASK_QUEUE_NAME: str = "addon_tasks"
    TASK_RESULT_TTL: int = 86400  # 24 hours
    TASK_TIMEOUT: int = 1800  # 30 minutes

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("SUPPORTED_EDITIONS", mode="before")
    @classmethod
    def parse_editions(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [e.strip() for e in v.split(",")]
        return v

    # -------------------------------------------------------------------------
    # Helper Properties
    # -------------------------------------------------------------------------
    @property
    def has_openrouter(self) -> bool:
        return self.ENABLE_OPENROUTER and bool(self.OPENROUTER_API_KEY)

    @property
    def has_groq(self) -> bool:
        return self.ENABLE_GROQ and bool(self.GROQ_API_KEY)

    @property
    def has_together(self) -> bool:
        return self.ENABLE_TOGETHER and bool(self.TOGETHER_API_KEY)

    @property
    def has_google(self) -> bool:
        return self.ENABLE_GOOGLE and bool(self.GOOGLE_API_KEY)

    @property
    def has_openai(self) -> bool:
        return self.ENABLE_OPENAI and bool(self.OPENAI_API_KEY)

    @property
    def has_anthropic(self) -> bool:
        return self.ENABLE_ANTHROPIC and bool(self.ANTHROPIC_API_KEY)

    @property
    def has_deepseek(self) -> bool:
        return self.ENABLE_DEEPSEEK and bool(self.DEEPSEEK_API_KEY)

    @property
    def has_ollama(self) -> bool:
        return self.ENABLE_OLLAMA

    @property
    def available_providers(self) -> list[str]:
        providers = []
        if self.has_openrouter:
            providers.append("openrouter")
        if self.has_groq:
            providers.append("groq")
        if self.has_together:
            providers.append("together")
        if self.has_google:
            providers.append("google")
        if self.has_openai:
            providers.append("openai")
        if self.has_anthropic:
            providers.append("anthropic")
        if self.has_deepseek:
            providers.append("deepseek")
        if self.has_ollama:
            providers.append("ollama")
        return providers


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export for easy imports
settings = get_settings()
