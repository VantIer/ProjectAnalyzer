"""Logger module for ProjectAnalyzer."""

import logging
import sys
from datetime import datetime
from pathlib import Path


class Logger:
    """Logger class that writes to both file and console."""

    def __init__(self, project_path: Path):
        self.project_name = project_path.name
        self.log_file = project_path / f"{self.project_name}.log"
        self._setup_logger()

    def _setup_logger(self):
        self.logger = logging.getLogger("ProjectAnalyzer")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()

        file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    def info(self, message: str):
        self.logger.info(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def error(self, message: str):
        self.logger.error(message)

    def fatal(self, message: str):
        self.logger.error(message)
        sys.exit(1)