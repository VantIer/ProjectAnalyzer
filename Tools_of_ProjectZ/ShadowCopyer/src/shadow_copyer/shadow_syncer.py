"""Shadow syncer module for ShadowCopyer - Core synchronization logic."""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Set

from shadow_copyer.utils import (
    compute_file_hash,
    scan_project_documents,
    get_relative_path,
    copy_file_with_hash,
    scan_shadow_directory,
    matches_any_pattern,
)
from shadow_copyer.sync_state import SyncState


class ShadowSyncer:
    """Handles synchronization between project documentation and shadow directory."""

    def __init__(self, project_path: Path, shadow_path: Path, config, logger):
        self.project_path = project_path
        self.shadow_path = shadow_path
        self.config = config
        self.logger = logger
        self.sync_state = SyncState(project_path, shadow_path, config, logger)

    def sync(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Perform synchronization from project docs to shadow directory.

        Args:
            dry_run: If True, only show what would be done without actually doing it.

        Returns:
            Dict with counts: {copied, updated, skipped, deleted, errors}
        """
        stats = {"copied": 0, "updated": 0, "skipped": 0, "deleted": 0, "errors": 0}

        # Step 1: Scan project for documentation files
        self.logger.info("Scanning project documentation files...")
        doc_files = scan_project_documents(
            self.project_path,
            self.config.document_patterns,
            self.config.exclude_config,
        )
        self.logger.info(f"Found {len(doc_files)} documentation files in project")

        # Step 2: Ensure shadow directory exists
        if not dry_run:
            self.shadow_path.mkdir(parents=True, exist_ok=True)

        # Step 3: Build current state and determine sync actions
        current_state = {}
        project_relative_paths = set()

        for doc_file in doc_files:
            relative_path = get_relative_path(doc_file, self.project_path)
            project_relative_paths.add(relative_path)

            src_hash = compute_file_hash(doc_file)
            current_state[relative_path] = {"hash": src_hash, "path": str(doc_file)}

            # Determine action
            shadow_file = self.shadow_path / relative_path

            if self.config.incremental and self.sync_state.is_file_synced(relative_path, src_hash):
                # File is already synced
                stats["skipped"] += 1
                self.logger.debug(f"Skip (unchanged): {relative_path}")
                continue

            if shadow_file.exists() and not self.config.incremental:
                # Full sync - overwrite
                action = "update"
            elif shadow_file.exists():
                # Incremental - file changed
                action = "update"
            else:
                # New file
                action = "copy"

            if dry_run:
                self.logger.info(f"[DRY-RUN] Would {action}: {relative_path}")
                if action == "copy":
                    stats["copied"] += 1
                else:
                    stats["updated"] += 1
                continue

            # Perform the copy
            success, result = copy_file_with_hash(doc_file, shadow_file)

            if success:
                if action == "copy":
                    stats["copied"] += 1
                    self.logger.info(f"Copied: {relative_path}")
                else:
                    stats["updated"] += 1
                    self.logger.info(f"Updated: {relative_path}")
            else:
                stats["errors"] += 1
                self.logger.error(f"Failed to copy {relative_path}: {result}")

        # Step 4: Clean orphan files in shadow directory
        if self.config.clean_orphan:
            orphans = self._find_orphan_files(project_relative_paths)
            for orphan_rel_path in orphans:
                orphan_file = self.shadow_path / orphan_rel_path
                if dry_run:
                    self.logger.info(f"[DRY-RUN] Would delete orphan: {orphan_rel_path}")
                    stats["deleted"] += 1
                    continue

                try:
                    orphan_file.unlink()
                    stats["deleted"] += 1
                    self.logger.info(f"Deleted orphan: {orphan_rel_path}")
                except Exception as e:
                    stats["errors"] += 1
                    self.logger.error(f"Failed to delete orphan {orphan_rel_path}: {e}")

            # Clean empty directories
            if not dry_run:
                self._clean_empty_dirs()

        # Step 5: Save sync state
        if not dry_run:
            files_state = {}
            for rel_path, info in current_state.items():
                files_state[rel_path] = {
                    "hash": info["hash"],
                    "synced_at": datetime.now().isoformat(),
                }
            self.sync_state.save(files_state)

        return stats

    def _find_orphan_files(self, project_relative_paths: Set[str]) -> List[str]:
        """Find files in shadow directory that no longer exist in project."""
        orphans = []

        if not self.shadow_path.exists():
            return orphans

        shadow_files = scan_shadow_directory(self.shadow_path)

        for shadow_file in shadow_files:
            # Skip the sync state file itself
            if shadow_file.name == self.config.sync_state_path:
                continue

            relative_path = get_relative_path(shadow_file, self.shadow_path)

            if relative_path not in project_relative_paths:
                orphans.append(relative_path)

        return orphans

    def _clean_empty_dirs(self) -> int:
        """Remove empty directories in shadow directory."""
        cleaned = 0
        if not self.shadow_path.exists():
            return cleaned

        # Walk bottom-up to remove empty directories
        for root, dirs, files in os.walk(self.shadow_path, topdown=False):
            root_path = Path(root)
            if root_path == self.shadow_path:
                continue
            try:
                if not any(root_path.iterdir()):
                    root_path.rmdir()
                    cleaned += 1
                    self.logger.debug(f"Removed empty directory: {root_path}")
            except Exception as e:
                self.logger.error(f"Failed to remove directory {root_path}: {e}")

        return cleaned

    def generate_sync_report(self, stats: Dict[str, int]) -> str:
        """Generate a sync report in markdown format."""
        report = f"""# 影子文档同步报告

## 基本信息
- 项目路径: {self.project_path}
- 影子目录: {self.shadow_path}
- 同步时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 同步统计

| 操作 | 数量 |
|------|------|
| 新增拷贝 | {stats.get('copied', 0)} |
| 更新覆盖 | {stats.get('updated', 0)} |
| 跳过(未变化) | {stats.get('skipped', 0)} |
| 删除孤立文件 | {stats.get('deleted', 0)} |
| 错误 | {stats.get('errors', 0)} |

"""
        return report
