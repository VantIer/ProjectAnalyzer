"""Scanner module for ProjectAnalyzer - Step 2: Project structure scanning."""

from pathlib import Path
from typing import List, Tuple

from project_analyzer.utils import get_project_files


class ProjectScanner:
    """Scans project directory and generates structure summary."""

    def __init__(self, project_path: Path, logger):
        self.project_path = project_path
        self.logger = logger

    def scan(self) -> Tuple[List[Path], int, int]:
        """
        Scan project directory.

        Returns:
            Tuple of (file_paths, directory_count, file_count)
        """
        self.logger.info(f"Scanning project: {self.project_path}")
        files, dir_count, file_count = get_project_files(self.project_path)
        self.logger.info(f"Found {dir_count} directories and {file_count} files")
        return files, dir_count, file_count

    def generate_summary(self, dir_count: int, file_count: int) -> str:
        """Generate project structure summary in markdown format."""
        summary = f"""# 项目结构扫描总结

## 基本信息
- 项目路径: {self.project_path}
- 目录总数: {dir_count}
- 文件总数: {file_count}
- 分析时间: (generated during scan)

"""
        return summary

    def save_summary(self, summary: str, output_path: Path = None):
        """Save summary to file."""
        if output_path is None:
            output_path = self.project_path / f"{self.project_path.name}_scan_summary.md"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary)

        self.logger.info(f"Summary saved to: {output_path}")
        return output_path