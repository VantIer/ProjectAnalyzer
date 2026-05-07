"""Snapshot module for ProjectAnalyzer - Manages file state snapshots for change detection."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

from project_analyzer.utils import compute_file_hash, get_regular_files


class FileSnapshot:
    """Manages project file state snapshots for detecting changes."""

    def __init__(self, project_path: Path, config, logger):
        self.project_path = project_path
        self.config = config
        self.logger = logger
        self.snapshot_file = project_path / config.snapshot_path
        self.hash_algorithm = config.hash_algorithm

    def load(self) -> Optional[Dict]:
        """Load existing snapshot from file."""
        if not self.snapshot_file.exists():
            self.logger.info("No existing snapshot found, will perform full analysis")
            return None

        try:
            with open(self.snapshot_file, "r", encoding="utf-8") as f:
                snapshot = json.load(f)
            self.logger.info(f"Loaded snapshot from {self.snapshot_file} "
                             f"(created: {snapshot.get('timestamp', 'unknown')})")
            return snapshot
        except Exception as e:
            self.logger.error(f"Failed to load snapshot: {e}")
            return None

    def save(self, files_info: Dict[str, Dict]) -> None:
        """Save current file states as a new snapshot."""
        snapshot = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "project_path": str(self.project_path),
            "hash_algorithm": self.hash_algorithm,
            "files": files_info,
        }

        try:
            with open(self.snapshot_file, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Snapshot saved to {self.snapshot_file} "
                             f"({len(files_info)} files)")
        except Exception as e:
            self.logger.error(f"Failed to save snapshot: {e}")

    def build_current_state(self) -> Dict[str, Dict]:
        """Build current file state by scanning the project."""
        files_info = {}
        regular_files = get_regular_files(self.project_path, self.config.exclude_config)

        self.logger.info(f"Scanning current state: {len(regular_files)} files")

        for file_path in regular_files:
            try:
                relative_path = str(file_path.relative_to(self.project_path))
                file_hash = compute_file_hash(file_path, self.hash_algorithm)
                stat = file_path.stat()
                files_info[relative_path] = {
                    "hash": file_hash,
                    "mtime": stat.st_mtime,
                    "size": stat.st_size,
                }
            except Exception as e:
                self.logger.error(f"Failed to stat {file_path}: {e}")

        return files_info

    def detect_changes(self) -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
        """
        Detect changes between the last snapshot and current state.

        Returns:
            Tuple of (new_files, modified_files, deleted_files, unchanged_files)
            Each set contains relative file paths.
        """
        old_snapshot = self.load()

        if old_snapshot is None:
            # No snapshot exists - treat all files as new (first run)
            current_state = self.build_current_state()
            all_paths = set(current_state.keys())
            self.logger.info(f"Full analysis required: {len(all_paths)} files (no previous snapshot)")
            return all_paths, set(), set(), set()

        old_files = old_snapshot.get("files", {})
        current_state = self.build_current_state()

        old_paths = set(old_files.keys())
        current_paths = set(current_state.keys())

        new_files = current_paths - old_paths
        deleted_files = old_paths - current_paths
        common_files = current_paths & old_paths

        modified_files = set()
        unchanged_files = set()

        for path in common_files:
            if current_state[path]["hash"] != old_files[path]["hash"]:
                modified_files.add(path)
            else:
                unchanged_files.add(path)

        self.logger.info(f"Changes detected: "
                         f"{len(new_files)} new, "
                         f"{len(modified_files)} modified, "
                         f"{len(deleted_files)} deleted, "
                         f"{len(unchanged_files)} unchanged")

        return new_files, modified_files, deleted_files, unchanged_files

    def get_affected_directories(self, changed_files: Set[str]) -> Set[Path]:
        """
        Get all directories affected by file changes.

        Returns the set of directories that contain changed files,
        plus all ancestor directories up to the project root.
        """
        affected_dirs = set()

        for relative_path in changed_files:
            file_path = self.project_path / relative_path
            parent_dir = file_path.parent
            affected_dirs.add(parent_dir)

            # Add all ancestor directories
            current = parent_dir
            while current != self.project_path and current.parent != current:
                current = current.parent
                affected_dirs.add(current)

        return affected_dirs

    def cleanup_deleted_docs(self, deleted_files: Set[str]) -> int:
        """Remove analysis documents for deleted source files."""
        cleaned = 0
        for relative_path in deleted_files:
            file_path = self.project_path / relative_path
            ana_file = file_path.parent / f"ana_{file_path.name}.md"

            if ana_file.exists():
                try:
                    ana_file.unlink()
                    cleaned += 1
                    self.logger.info(f"Removed analysis for deleted file: {ana_file}")
                except Exception as e:
                    self.logger.error(f"Failed to remove {ana_file}: {e}")

        return cleaned
