"""
College Admission Assistant — Application Configuration
========================================================
Loads environment variables from a .env file and exposes
them as typed Python attributes consumed by Flask's
app.config.from_object() call.

Add new configuration blocks here as the application grows
(e.g., database, caching, email) so every setting has a
single, documented home.
"""

import os
from dotenv import load_dotenv

# Load .env file from the project root (one level up from config.py if needed)
load_dotenv()


class Config:
    """Base configuration — shared across all environments."""

    # ------------------------------------------------------------------
    # Flask core
    # ------------------------------------------------------------------
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "change-me-in-production-please")
    DEBUG: bool = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    TESTING: bool = False

    # ------------------------------------------------------------------
    # Application metadata
    # ------------------------------------------------------------------
    APP_NAME: str = "College Admission Assistant"
    APP_VERSION: str = "1.0.0"

    # ------------------------------------------------------------------
    # IBM Watsonx AI — configuration prepared, integration pending
    # ------------------------------------------------------------------
    WATSONX_API_KEY: str = os.environ.get("WATSONX_API_KEY", "")
    WATSONX_PROJECT_ID: str = os.environ.get("WATSONX_PROJECT_ID", "")
    WATSONX_URL: str = os.environ.get(
        "WATSONX_URL", "https://us-south.ml.cloud.ibm.com"
    )
    WATSONX_MODEL_ID: str = os.environ.get(
        "WATSONX_MODEL_ID", "ibm/granite-4-h-small"
    )

    # ------------------------------------------------------------------
    # Dataset
    # ------------------------------------------------------------------
    DATASET_PATH: str = os.environ.get(
        "DATASET_PATH", os.path.join(os.path.dirname(__file__), "dataset", "college_dataset.csv")
    )


class DevelopmentConfig(Config):
    """Development-specific overrides."""
    DEBUG: bool = True


class ProductionConfig(Config):
    """Production-specific overrides."""
    DEBUG: bool = False
    TESTING: bool = False


class TestingConfig(Config):
    """Testing-specific overrides."""
    TESTING: bool = True
    DEBUG: bool = True
    SECRET_KEY: str = "test-secret-key"


# Convenience mapping used by FLASK_ENV / APP_ENV environment variable
config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "testing":     TestingConfig,
}
