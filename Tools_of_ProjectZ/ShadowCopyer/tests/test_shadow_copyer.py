"""Tests for ShadowCopyer."""

import json
import pytest
from pathlib import Path
import os

from shadow_copyer.utils import (
    compute_file_hash,
    matches_any_pattern,
    scan_project_documents,
    get_relative_path,
    copy_file_with_hash,
)
from shadow_copyer.sync_state import SyncState
from shadow_copyer.shadow_syncer import ShadowSyncer


class TestUtils:
    """Tests for utility functions."""

    def test_compute_file_hash(self, tmp_path):
        """Test file hash computation."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Hello", encoding="utf-8")
        h = compute_file_hash(test_file)
        assert len(h) == 32  # MD5 hex digest

    def test_matches_any_pattern(self):
        """Test pattern matching."""
        assert matches_any_pattern("ana_main.py.md", ["ana_*.md"]) is True
        assert matches_any_pattern("model_src.md", ["model_*.md"]) is True
        assert matches_any_pattern("analyse_report.md", ["analyse_report.md"]) is True
        assert matches_any_pattern("main.py", ["ana_*.md"]) is False

    def test_get_relative_path(self, tmp_path):
        """Test relative path computation."""
        file_path = tmp_path / "src" / "main.py"
        assert get_relative_path(file_path, tmp_path) == os.path.join("src", "main.py")

    def test_copy_file_with_hash(self, tmp_path):
        """Test file copy and hash."""
        src = tmp_path / "src.md"
        dst = tmp_path / "shadow" / "src.md"
        src.write_text("# Test Content", encoding="utf-8")

        success, result = copy_file_with_hash(src, dst)
        assert success is True
        assert len(result) == 32  # MD5 hash
        assert dst.exists()
        assert dst.read_text(encoding="utf-8") == "# Test Content"

    def test_scan_project_documents(self, tmp_path):
        """Test scanning project for documentation files."""
        (tmp_path / "ana_main.py.md").write_text("file analysis")
        (tmp_path / "model_src.md").write_text("dir analysis")
        (tmp_path / "analyse_report.md").write_text("report")
        (tmp_path / "main.py").write_text("source code")

        docs = scan_project_documents(tmp_path, ["ana_*.md", "model_*.md", "analyse_report.md"])
        names = [d.name for d in docs]

        assert "ana_main.py.md" in names
        assert "model_src.md" in names
        assert "analyse_report.md" in names
        assert "main.py" not in names


class TestSyncState:
    """Tests for SyncState."""

    def _make_config(self):
        class MockConfig:
            sync_state_path = ".shadow_sync_state.json"
        return MockConfig()

    def _make_logger(self):
        return type('Logger', (), {
            'info': lambda self, x: None,
            'debug': lambda self, x: None,
            'error': lambda self, x: None,
        })()

    def test_save_and_load_state(self, tmp_path):
        """Test sync state save and load."""
        shadow_path = tmp_path / "shadow"
        shadow_path.mkdir()
        config = self._make_config()
        logger = self._make_logger()

        state = SyncState(tmp_path, shadow_path, config, logger)
        files_state = {
            "src/ana_main.md": {"hash": "abc123", "synced_at": "2024-01-01T00:00:00"},
        }
        state.save(files_state)

        loaded = state.load()
        assert loaded is not None
        assert "src/ana_main.md" in loaded["files"]

    def test_is_file_synced(self, tmp_path):
        """Test checking if a file is synced."""
        shadow_path = tmp_path / "shadow"
        shadow_path.mkdir()
        config = self._make_config()
        logger = self._make_logger()

        state = SyncState(tmp_path, shadow_path, config, logger)
        files_state = {
            "src/ana_main.md": {"hash": "abc123", "synced_at": "2024-01-01T00:00:00"},
        }
        state.save(files_state)

        assert state.is_file_synced("src/ana_main.md", "abc123") is True
        assert state.is_file_synced("src/ana_main.md", "different") is False
        assert state.is_file_synced("nonexistent.md", "abc123") is False


class TestShadowSyncer:
    """Tests for ShadowSyncer."""

    def _make_config(self):
        class MockConfig:
            document_patterns = ["ana_*.md", "model_*.md", "analyse_report.md", "*_scan_summary.md"]
            exclude_config = {"directories": [".git", "__pycache__"]}
            incremental = True
            clean_orphan = True
            verify_hash = True
            sync_state_path = ".shadow_sync_state.json"

        return MockConfig()

    def _make_logger(self):
        return type('Logger', (), {
            'info': lambda self, x: None,
            'debug': lambda self, x: None,
            'error': lambda self, x: None,
        })()

    def test_sync_copies_files(self, tmp_path):
        """Test that sync copies documentation files."""
        # Create project docs
        (tmp_path / "ana_main.py.md").write_text("file analysis")
        (tmp_path / "model_src.md").write_text("dir analysis")
        (tmp_path / "main.py").write_text("source code")  # not a doc

        shadow_path = tmp_path / "shadow"
        config = self._make_config()
        logger = self._make_logger()

        syncer = ShadowSyncer(tmp_path, shadow_path, config, logger)
        stats = syncer.sync()

        assert stats["copied"] >= 2  # ana + model
        assert (shadow_path / "ana_main.py.md").exists()
        assert (shadow_path / "model_src.md").exists()
        assert not (shadow_path / "main.py").exists()

    def test_sync_incremental_skips_unchanged(self, tmp_path):
        """Test that incremental sync skips unchanged files."""
        (tmp_path / "ana_main.py.md").write_text("file analysis")

        shadow_path = tmp_path / "shadow"
        config = self._make_config()
        logger = self._make_logger()

        syncer = ShadowSyncer(tmp_path, shadow_path, config, logger)

        # First sync
        stats1 = syncer.sync()
        assert stats1["copied"] >= 1

        # Second sync (no changes)
        syncer2 = ShadowSyncer(tmp_path, shadow_path, config, logger)
        stats2 = syncer2.sync()
        assert stats2["skipped"] >= 1

    def test_sync_dry_run(self, tmp_path):
        """Test that dry-run doesn't create files."""
        (tmp_path / "ana_main.py.md").write_text("file analysis")

        shadow_path = tmp_path / "shadow"
        config = self._make_config()
        logger = self._make_logger()

        syncer = ShadowSyncer(tmp_path, shadow_path, config, logger)
        stats = syncer.sync(dry_run=True)

        assert not (shadow_path / "ana_main.py.md").exists()
        assert stats["copied"] >= 1  # Counts as would-be-copied

    def test_sync_cleans_orphans(self, tmp_path):
        """Test that orphan files in shadow directory are cleaned."""
        shadow_path = tmp_path / "shadow"
        shadow_path.mkdir()
        (shadow_path / "old_doc.md").write_text("old file")  # orphan

        config = self._make_config()
        logger = self._make_logger()

        syncer = ShadowSyncer(tmp_path, shadow_path, config, logger)
        stats = syncer.sync()

        assert stats["deleted"] >= 1
        assert not (shadow_path / "old_doc.md").exists()
