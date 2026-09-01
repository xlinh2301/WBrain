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
    log_path: Path = Path("/var/log/wbrain/app.log")
    log_max_bytes: int = 10 * 1024 * 1024
    log_backup_count: int = 5
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.device.lower() != "cpu":
        raise ValueError("WBrain currently supports CPU only; set DEVICE=cpu")
    return settings
