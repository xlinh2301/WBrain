from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    yolo_model_path: Path | None = None
    editctc_model_path: Path | None = None
    editctc_config_path: Path | None = None
    editctc_dict_path: Path | None = None
    editctc_code_dir: Path | None = None
    device: str = "cpu"
    yolo_confidence: float = 0.35
    max_image_bytes: int = 10 * 1024 * 1024
    log_path: Path = Path("logs/app.log")
    log_max_bytes: int = 10 * 1024 * 1024
    log_backup_count: int = 5
    database_path: Path = Path("data/wbrain.db")
    image_storage_dir: Path = Path("data/images")
    persistence_enabled: bool = True
    store_images: bool = False
    api_key: str | None = None
    review_confidence_threshold: float = 0.70
    model_version: str = "unversioned"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.device.lower() != "cpu":
        raise ValueError("WBrain currently supports CPU only; set DEVICE=cpu")
    return settings
