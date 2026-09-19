from pathlib import Path
import os
from typing import Optional
from pydantic_settings import BaseSettings

# Absolute path to the server directory
SERVER_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = f"sqlite:///{SERVER_DIR}/data/crop_insurance.db"
    VISION_MODEL_PATH: str = str(SERVER_DIR / "models_saved" / "vision_model.h5")
    FRAUD_MODEL_PATH: str = str(SERVER_DIR / "models_saved" / "xgboost_fraud.pkl")
    SHAP_EXPLAINER_PATH: str = str(SERVER_DIR / "models_saved" / "shap_explainer.pkl")
    UPLOADS_DIR: str = str(SERVER_DIR / "data" / "uploads")

    # Satellite Remote Sensing (loaded dynamically from .env file)
    SENTINEL_STAC_URL: Optional[str] = None
    SENTINEL_COLLECTION: Optional[str] = None
    SENTINEL_API_KEY: Optional[str] = None

    class Config:
        env_file = str(SERVER_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Resolve paths to absolute if relative paths are provided via .env
def get_resolved_path(file_path: str) -> Path:
    p = Path(file_path)
    if not p.is_absolute():
        p = SERVER_DIR / p
    return p

# Ensure necessary data directories exist
def ensure_directories():
    uploads_path = get_resolved_path(settings.UPLOADS_DIR)
    uploads_path.mkdir(parents=True, exist_ok=True)
    db_dir = SERVER_DIR / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
