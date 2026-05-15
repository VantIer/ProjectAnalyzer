"""Utility functions for ShadowCopyer."""

import hashlib
import fnmatch
import os
from pathlib import Path
from typing import List, Dict, Tuple


def compute_file_hash(file_path: Path) -> str:
    """Compute MD5 hash of file content."""
    hash_func = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception:
        return ""


def matches_any_pattern(filename: str, patterns: List[str]) -> bool:
    """Check if filename matches any of the given glob patterns."""
    for pattern in patterns:
        if fnmatch.fnmatch(filename, pattern):
            return True
    return False


def scan_project_documents(project_path: Path, patterns: List[str],
                           exclude_config: dict = None) -> List[Path]:
    """
    Scan project directory for documentation files matching the given patterns.

    Returns list of absolute paths to matching files.
    """
    if exclude_config is None:
        exclude_config = {}

    exclude_dirs = set(exclude_config.get("directories", [
        ".git", "__pycache__", "node_modules", ".idea", ".vscode", "dist", "build"
    ]))

    doc_files = []
    for root, dirs, filenames in os.walk(project_path):
        # Filter excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for filename in filenames:
            if matches_any_pattern(filename, patterns):
                doc_files.append(Path(root) / filename)

    return doc_files


def get_relative_path(file_path: Path, base_path: Path) -> str:
    """Get relative path as string, handling cross-platform path separators."""
    try:
        return str(file_path.relative_to(base_path))
    except ValueError:
        return str(file_path)


def ensure_directory(file_path: Path) -> None:
    """Ensure the parent directory of a file exists."""
    file_path.parent.mkdir(parents=True, exist_ok=True)


def copy_file_with_hash(src: Path, dst: Path) -> Tuple[bool, str]:
    """
    Copy file from src to dst and return (success, hash).

    Returns:
        Tuple of (success_status, file_hash)
    """
    import shutil

    try:
        ensure_directory(dst)
        shutil.copy2(src, dst)
        file_hash = compute_file_hash(dst)
        return True, file_hash
    except Exception as e:
        return False, str(e)


def scan_shadow_directory(shadow_path: Path) -> List[Path]:
    """Scan the shadow directory and return all files in it."""
    if not shadow_path.exists():
        return []

    files = []
    for root, _, filenames in os.walk(shadow_path):
        for filename in filenames:
            files.append(Path(root) / filename)

    return files
