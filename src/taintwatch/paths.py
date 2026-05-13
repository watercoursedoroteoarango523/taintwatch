"""Platform-aware paths for config, state, and reports."""
from __future__ import annotations

from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

APP_NAME = "taintwatch"


def config_dir() -> Path:
    return Path(user_config_dir(APP_NAME, appauthor=False, roaming=False))


def config_path() -> Path:
    return config_dir() / "config.toml"


def state_dir() -> Path:
    return Path(user_data_dir(APP_NAME, appauthor=False, roaming=False))


def state_db_path() -> Path:
    return state_dir() / "state.db"


def default_report_dir() -> Path:
    return state_dir() / "reports"


def feeds_cache_dir() -> Path:
    return state_dir() / "feeds-cache"
