"""Configuration module for ProjectAnalyzer."""

import sys
from pathlib import Path
from typing import Any

import yaml


class Config:
    """Configuration manager that loads settings from YAML file."""

    def __init__(self, config_path: str = "project_analyzer_config.yaml"):
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
    def model_config(self) -> dict:
        return self._config.get("model", {})

    @property
    def threading_config(self) -> dict:
        return self._config.get("threading", {})

    @property
    def prompts_config(self) -> dict:
        return self._config.get("prompts", {})

    @property
    def max_workers(self) -> int:
        return self.threading_config.get("max_workers", 4)

    @property
    def file_analysis_prompt(self) -> str:
        return self.prompts_config.get("file_analysis", "")

    @property
    def directory_analysis_prompt(self) -> str:
        return self.prompts_config.get("directory_analysis", "")

    @property
    def project_summary_prompt(self) -> str:
        return self.prompts_config.get("project_summary", "")

    @property
    def model_analysis_prompt(self) -> str:
        return self.prompts_config.get("model_analysis", "")

    @property
    def exclude_config(self) -> dict:
        return self._config.get("exclude", {})

    @property
    def file_analysis_clear(self) -> bool:
        return self.get("cleanup.file_analysis_clear", True)

    @property
    def directory_analysis_clear(self) -> bool:
        return self.get("cleanup.directory_analysis_clear", True)

    @property
    def model_analysis_clear(self) -> bool:
        return self.get("cleanup.model_analysis_clear", True)

    @property
    def snapshot_config(self) -> dict:
        return self._config.get("snapshot", {})

    @property
    def snapshot_path(self) -> str:
        return self.snapshot_config.get("path", ".project_snapshot.json")

    @property
    def hash_algorithm(self) -> str:
        return self.snapshot_config.get("hash_algorithm", "md5")

    @property
    def cascade_enabled(self) -> bool:
        return self.get("cascade.enabled", True)