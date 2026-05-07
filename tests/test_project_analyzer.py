"""Tests for ProjectAnalyzer."""

import json
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

    def test_compute_file_hash(self, tmp_path):
        """Test file hash computation."""
        from project_analyzer.utils import compute_file_hash

        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')", encoding="utf-8")

        hash1 = compute_file_hash(test_file, "md5")
        assert hash1 != ""
        assert len(hash1) == 32  # MD5 hex digest length

    def test_compute_file_hash_consistency(self, tmp_path):
        """Test that same content produces same hash."""
        from project_analyzer.utils import compute_file_hash

        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        content = "same content here"
        file1.write_text(content, encoding="utf-8")
        file2.write_text(content, encoding="utf-8")

        assert compute_file_hash(file1, "md5") == compute_file_hash(file2, "md5")

    def test_compute_file_hash_different(self, tmp_path):
        """Test that different content produces different hash."""
        from project_analyzer.utils import compute_file_hash

        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("content A", encoding="utf-8")
        file2.write_text("content B", encoding="utf-8")

        assert compute_file_hash(file1, "md5") != compute_file_hash(file2, "md5")


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

    def test_snapshot_config_defaults(self, tmp_path):
        """Test snapshot configuration defaults."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
model:
  api_key: "test-key"
  model_name: "gpt-4"
prompts:
  file_analysis: "test {content}"
""")

        from project_analyzer.config import Config
        config = Config(str(config_file))

        assert config.snapshot_path == ".project_snapshot.json"
        assert config.hash_algorithm == "md5"
        assert config.cascade_enabled is True

    def test_snapshot_config_custom(self, tmp_path):
        """Test snapshot configuration with custom values."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
model:
  api_key: "test-key"
  model_name: "gpt-4"
prompts:
  file_analysis: "test {content}"
snapshot:
  path: "custom_snapshot.json"
  hash_algorithm: "sha256"
cascade:
  enabled: false
""")

        from project_analyzer.config import Config
        config = Config(str(config_file))

        assert config.snapshot_path == "custom_snapshot.json"
        assert config.hash_algorithm == "sha256"
        assert config.cascade_enabled is False


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


class TestFileSnapshot:
    """Tests for FileSnapshot module."""

    def _make_config(self, snapshot_path=".project_snapshot.json"):
        """Create a mock config object."""
        class MockConfig:
            snapshot_path_val = snapshot_path
            hash_algorithm = "md5"
            exclude_config = {
                "directories": [".git", "__pycache__"],
                "file_patterns": ["*.pyc", "ana_*.md", "model_*.md"]
            }

            @property
            def snapshot_path(self):
                return self.snapshot_path_val

        return MockConfig()

    def _make_logger(self):
        """Create a mock logger."""
        return type('Logger', (), {
            'info': lambda self, x: None,
            'debug': lambda self, x: None,
            'error': lambda self, x: None,
        })()

    def test_save_and_load_snapshot(self, tmp_path):
        """Test snapshot save and load cycle."""
        from project_analyzer.snapshot import FileSnapshot

        config = self._make_config()
        logger = self._make_logger()
        snapshot = FileSnapshot(tmp_path, config, logger)

        files_info = {
            "src/main.py": {"hash": "abc123", "mtime": 1000.0, "size": 100},
            "src/utils.py": {"hash": "def456", "mtime": 1001.0, "size": 200},
        }
        snapshot.save(files_info)

        loaded = snapshot.load()
        assert loaded is not None
        assert loaded["files"]["src/main.py"]["hash"] == "abc123"
        assert loaded["files"]["src/utils.py"]["size"] == 200

    def test_load_nonexistent_snapshot(self, tmp_path):
        """Test loading a nonexistent snapshot returns None."""
        from project_analyzer.snapshot import FileSnapshot

        config = self._make_config()
        logger = self._make_logger()
        snapshot = FileSnapshot(tmp_path, config, logger)

        result = snapshot.load()
        assert result is None

    def test_detect_changes_new_files(self, tmp_path):
        """Test detecting new files (no previous snapshot)."""
        from project_analyzer.snapshot import FileSnapshot

        config = self._make_config()
        logger = self._make_logger()
        snapshot = FileSnapshot(tmp_path, config, logger)

        (tmp_path / "main.py").write_text("print('hello')")

        new, modified, deleted, unchanged = snapshot.detect_changes()
        assert len(new) == 1
        assert len(modified) == 0
        assert len(deleted) == 0

    def test_detect_changes_modified_files(self, tmp_path):
        """Test detecting modified files."""
        from project_analyzer.snapshot import FileSnapshot

        config = self._make_config()
        logger = self._make_logger()
        snapshot = FileSnapshot(tmp_path, config, logger)

        # Create initial file and save snapshot
        (tmp_path / "main.py").write_text("original")
        state = snapshot.build_current_state()
        snapshot.save(state)

        # Modify the file
        (tmp_path / "main.py").write_text("modified")

        new, modified, deleted, unchanged = snapshot.detect_changes()
        assert len(modified) == 1
        assert len(new) == 0
        assert len(deleted) == 0

    def test_detect_changes_deleted_files(self, tmp_path):
        """Test detecting deleted files."""
        from project_analyzer.snapshot import FileSnapshot

        config = self._make_config()
        logger = self._make_logger()
        snapshot = FileSnapshot(tmp_path, config, logger)

        # Create files and save snapshot
        (tmp_path / "main.py").write_text("keep")
        (tmp_path / "temp.py").write_text("delete")
        state = snapshot.build_current_state()
        snapshot.save(state)

        # Delete one file
        (tmp_path / "temp.py").unlink()

        new, modified, deleted, unchanged = snapshot.detect_changes()
        assert len(deleted) == 1
        assert "temp.py" in deleted

    def test_get_affected_directories(self, tmp_path):
        """Test getting affected directories from changed files."""
        from project_analyzer.snapshot import FileSnapshot

        config = self._make_config()
        logger = self._make_logger()
        snapshot = FileSnapshot(tmp_path, config, logger)

        # Create nested structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("code")

        changed = {"src/main.py"}
        affected = snapshot.get_affected_directories(changed)

        assert tmp_path / "src" in affected