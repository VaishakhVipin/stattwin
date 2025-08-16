import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings and configuration."""
    
    # FBRef API Configuration
    FBREF_API_BASE_URL: str = "https://fbrapi.com"
    FBREF_API_KEY: Optional[str] = None
    
    # Rate Limiting (FBRef allows 1 request every 3 seconds)
    FBREF_RATE_LIMIT_PER_MINUTE: int = 20  # 60 seconds / 3 seconds = 20 requests per minute
    FBREF_RATE_LIMIT_PER_HOUR: int = 1200   # 20 per minute * 60 minutes
    
    # Data Storage
    DATA_RAW_DIR: str = "backend/data/raw"
    DATA_PROCESSED_DIR: str = "backend/data/processed"
    DATA_METADATA_DIR: str = "backend/data/metadata"
    
    # Cache Settings
    CACHE_TTL_HOURS: int = 24  # Cache data for 24 hours
    
    # API Settings
    API_TITLE: str = "StatTwin API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Find your player's statistical twin"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
