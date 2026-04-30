"""Utility functions for ProjectAnalyzer."""

import os
from pathlib import Path
from typing import List, Tuple


def get_project_files(project_path: Path) -> Tuple[List[Path], int, int]:
    """
    Recursively scan project directory and return all file paths.

    Returns:
        Tuple of (file_paths, directory_count, file_count)
    """
    files = []
    dir_count = 0
    file_count = 0

    for root, dirs, filenames in os.walk(project_path):
        root_path = Path(root)

        if ".git" in dirs:
            dirs.remove(".git")
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
        if "node_modules" in dirs:
            dirs.remove("node_modules")

        dir_count += len(dirs)

        for filename in filenames:
            file_path = root_path / filename
            files.append(file_path)
            file_count += 1

    return files, dir_count, file_count


def _matches_pattern(filename: str, pattern: str) -> bool:
    """Check if filename matches the exclude pattern."""
    if "*" not in pattern:
        return filename == pattern

    prefix, suffix = pattern.split("*", 1)
    if prefix and not filename.startswith(prefix):
        return False
    if suffix and not filename.endswith(suffix):
        return False
    return True


def get_regular_files(project_path: Path, exclude_config: dict = None) -> List[Path]:
    """
    Get all regular files that should be analyzed.

    Args:
        project_path: Project directory path
        exclude_config: Dictionary with exclude directories and file_patterns from config
    """
    if exclude_config is None:
        exclude_config = {}

    exclude_dirs = set(exclude_config.get("directories", [
        ".git", "__pycache__", "node_modules", ".idea", ".vscode", "dist", "build"
    ]))

    exclude_files = set(exclude_config.get("file_patterns", [
        "*.pyc", "*.pyo", "*.so", "*.dll", "*.exe", "*.log",
        "ana_*.md", "model_*.md", "analyse_report.md"
    ]))

    files = []
    for root, dirs, filenames in os.walk(project_path):
        root_path = Path(root)

        dirs[:] = [d for d in dirs if not any(_matches_pattern(d, pat) for pat in exclude_dirs)]

        for filename in filenames:
            if filename.startswith("."):
                continue
            if any(_matches_pattern(filename, pat) for pat in exclude_files):
                continue

            file_path = root_path / filename
            files.append(file_path)

    return files


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def safe_read_file(file_path: Path, max_size: int = 1024 * 1024) -> str:
    """Safely read file content with size limit."""
    try:
        if file_path.stat().st_size > max_size:
            return f"[File too large: {format_file_size(file_path.stat().st_size)}]"
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return "[Unable to read file]"