"""
Centralized configuration for fraud detection API
Loads from environment variables with sensible defaults
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment"""

    # Database configuration
    COGNODB_URI: str = os.getenv("COGNODB_URI", "bolt+s://localhost:7687")
    COGNODB_USERNAME: str = os.getenv("COGNODB_USERNAME", "cognodb")
    COGNODB_PASSWORD: str = os.getenv("COGNODB_PASSWORD", "password")

    # API configuration
    API_PORT: int = int(os.getenv("API_PORT", 8000))

    # Auto-seeding configuration
    # Set to "false", "0", "no" to disable auto-seeding on startup
    # Useful for keeping manual control in CI/CD or production environments
    AUTO_SEED_ON_STARTUP: bool = os.getenv("AUTO_SEED_ON_STARTUP", "true").lower() in (
        "true",
        "1",
        "yes",
        "on",
    )

    # CORS configuration
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")


# Global settings instance
settings = Settings()
