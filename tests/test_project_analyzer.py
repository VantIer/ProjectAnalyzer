"""Tests for ProjectAnalyzer."""

import pytest
from pathlib import Path
import tempfile
import os


class TestUtils:
    """Tests for utility functions."""

    def test_get_project_files(self, tmp_path):
        """Test project file scanning."""
        from project_analyzer.utils import get_project_files

        (tmp_path / "file1.py").touch()
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file2.py").touch()

        files, dirs, count = get_project_files(tmp_path)
        assert count == 2

    def test_get_regular_files(self, tmp_path):
        """Test regular file filtering."""
        from project_analyzer.utils import get_regular_files

        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "data.txt").write_text("data")
        (tmp_path / ".hidden").write_text("hidden")
        (tmp_path / "ana_test.md").write_text("temp")

        files = get_regular_files(tmp_path)
        filenames = [f.name for f in files]

        assert "main.py" in filenames
        assert "data.txt" in filenames
        assert ".hidden" not in filenames
        assert "ana_test.md" not in filenames


class TestConfig:
    """Tests for configuration loading."""

    def test_load_config(self, tmp_path):
        """Test configuration file loading."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
model:
  api_key: "test-key"
  model_name: "gpt-4"

threading:
  max_workers: 8

prompts:
  file_analysis: "test prompt {content}"
""")

        from project_analyzer.config import Config
        config = Config(str(config_file))

        assert config.get("model.api_key") == "test-key"
        assert config.max_workers == 8
        assert "test prompt" in config.file_analysis_prompt


class TestScanner:
    """Tests for project scanner."""

    def test_scan_summary_generation(self, tmp_path):
        """Test summary report generation."""
        from project_analyzer.scanner import ProjectScanner

        logger = type('Logger', (), {'info': lambda self, x: None})()

        scanner = ProjectScanner(tmp_path, logger)
        summary = scanner.generate_summary(10, 25)

        assert "10" in summary
        assert "25" in summary
        assert str(tmp_path) in summary