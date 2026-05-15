"""Sync state module for ShadowCopyer - Manages synchronization state between project and shadow directory."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from shadow_copyer.utils import compute_file_hash


class SyncState:
    """Manages the synchronization state between project and shadow directory."""

    def __init__(self, project_path: Path, shadow_path: Path, config, logger):
        self.project_path = project_path
        self.shadow_path = shadow_path
        self.config = config
        self.logger = logger
        self.state_file = shadow_path / config.sync_state_path
        self._state = None

    def load(self) -> Optional[Dict]:
        """Load existing sync state."""
        if not self.state_file.exists():
            self.logger.info("No existing sync state found")
            return None

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            self._state = state
            self.logger.info(f"Loaded sync state (last sync: {state.get('last_sync', 'unknown')})")
            return state
        except Exception as e:
            self.logger.error(f"Failed to load sync state: {e}")
            return None

    def save(self, files_state: Dict[str, Dict]) -> None:
        """Save current sync state."""
        state = {
            "version": "1.0",
            "last_sync": datetime.now().isoformat(),
            "project_path": str(self.project_path),
            "shadow_path": str(self.shadow_path),
            "files": files_state,
        }

        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            self._state = state
            self.logger.info(f"Sync state saved ({len(files_state)} files)")
        except Exception as e:
            self.logger.error(f"Failed to save sync state: {e}")

    def get_file_hash(self, relative_path: str) -> Optional[str]:
        """Get the stored hash for a file."""
        if self._state is None:
            self.load()
        if self._state is None:
            return None
        return self._state.get("files", {}).get(relative_path, {}).get("hash")

    def is_file_synced(self, relative_path: str, current_hash: str) -> bool:
        """Check if a file is already synced with the given hash."""
        stored_hash = self.get_file_hash(relative_path)
        if stored_hash is None:
            return False
        return stored_hash == current_hash

    def get_synced_paths(self) -> set:
        """Get all relative paths that have been synced."""
        if self._state is None:
            self.load()
        if self._state is None:
            return set()
        return set(self._state.get("files", {}).keys())
