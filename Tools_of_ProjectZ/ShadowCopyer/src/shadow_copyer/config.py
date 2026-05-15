"""Configuration module for ShadowCopyer."""

import sys
from pathlib import Path
from typing import Any

import yaml


class Config:
    """Configuration manager that loads settings from YAML file."""

    def __init__(self, config_path: str = "shadow_copyer_config.yaml"):
        self.config_path = Path(config_path)
        self._load_config()

    def _load_config(self):
        if not self.config_path.exists():
            print(f"Error: Configuration file not found: {self.config_path}")
            sys.exit(1)

        with open(self.config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    @property
    def shadow_config(self) -> dict:
        return self._config.get("shadow", {})

    @property
    def shadow_root_dir(self) -> str:
        return self.shadow_config.get("root_dir", "./docs")

    @property
    def shadow_naming(self) -> str:
        return self.shadow_config.get("naming", "{project}_shadow")

    @property
    def sync_config(self) -> dict:
        return self._config.get("sync", {})

    @property
    def incremental(self) -> bool:
        return self.sync_config.get("incremental", True)

    @property
    def clean_orphan(self) -> bool:
        return self.sync_config.get("clean_orphan", True)

    @property
    def verify_hash(self) -> bool:
        return self.sync_config.get("verify_hash", True)

    @property
    def document_patterns(self) -> list:
        return self._config.get("documents", {}).get("patterns", [
            "ana_*.md",
            "model_*.md",
            "analyse_report.md",
            "*_scan_summary.md",
            "*.log",
        ])

    @property
    def exclude_config(self) -> dict:
        return self._config.get("exclude", {})

    @property
    def sync_state_path(self) -> str:
        return self.get("sync.state_path", ".shadow_sync_state.json")
