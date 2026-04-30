"""Directory analyzer module for ProjectAnalyzer - Step 4: Multi-threaded directory analysis."""

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Set

from openai import OpenAI


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting tags and :emoji: tags from text."""
    stripped = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    stripped = re.sub(r':[^:]+:', '', stripped)
    return stripped.strip()


class DirectoryAnalyzer:
    """Analyzes directories by summarizing file analyses using LLM."""

    def __init__(self, project_path: Path, config, logger):
        self.project_path = project_path
        self.config = config
        self.logger = logger
        self.max_workers = config.max_workers

    def _create_client(self) -> OpenAI:
        """Create a new OpenAI client instance."""
        api_key = self.config.get("model.api_key")
        base_url = self.config.get("model.base_url") or None
        return OpenAI(api_key=api_key, base_url=base_url)

    def get_all_directories(self) -> List[Path]:
        """Get all unique directories from the project."""
        directories = set()
        exclude_config = self.config.exclude_config
        exclude_dirs = exclude_config.get("directories", []) if exclude_config else []

        for root, dirs, _ in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            directories.add(Path(root))
        return sorted(list(directories))

    def get_ana_files_for_dir(self, directory: Path) -> List[Path]:
        """Get all ana_*.md files in a directory."""
        ana_files = []
        for f in directory.iterdir():
            if f.is_file() and f.name.startswith("ana_") and f.name.endswith(".md"):
                ana_files.append(f)
        return ana_files

    def analyze_directories(self) -> Dict[str, bool]:
        """
        Analyze all directories using multi-threading.

        Returns:
            Dict mapping directory path to success status
        """
        directories = self.get_all_directories()
        total_dirs = len(directories)
        self.logger.info(f"Starting directory analysis: {total_dirs} directories")

        results = {}
        completed = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_dir = {
                executor.submit(self._analyze_single_directory, d): d for d in directories
            }

            for future in as_completed(future_to_dir):
                directory = future_to_dir[future]
                try:
                    success = future.result()
                    results[str(directory)] = success
                    completed += 1
                    self.logger.info(f"[进度] 已处理 {completed}/{total_dirs} 个目录")
                except Exception as e:
                    self.logger.error(f"处理目录失败 {directory}: {e}")
                    results[str(directory)] = False
                    completed += 1

        success_count = sum(1 for v in results.values() if v)
        self.logger.info(f"Directory analysis completed: {success_count}/{total_dirs} successful")
        return results

    def _analyze_single_directory(self, directory: Path) -> bool:
        """Analyze a single directory with its own API session."""
        output_path = directory / f"model_{directory.name}.md"

        if output_path.exists():
            self.logger.info(f"跳过已存在的分析结果: {output_path}")
            return True

        self.logger.info(f"正在分析目录: {directory}")

        client = self._create_client()

        try:
            ana_files = self.get_ana_files_for_dir(directory)
            if not ana_files:
                self.logger.debug(f"No ana files in {directory}, skipping")
                return True

            combined_content = ""
            for ana_file in ana_files:
                with open(ana_file, "r", encoding="utf-8") as f:
                    combined_content += f"\n\n# {ana_file.name}\n\n"
                    combined_content += f.read()

            prompt_template = self.config.directory_analysis_prompt
            prompt = prompt_template.replace("{content}", combined_content)

            response = client.chat.completions.create(
                model=self.config.get("model.model_name", "gpt-4"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
            )

            analysis = response.choices[0].message.content
            clean_analysis = _strip_markdown(analysis)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"# {directory.name}\n\n")
                f.write(f"**Directory:** {directory}\n\n")
                f.write(clean_analysis)

            return True

        except Exception as e:
            self.logger.error(f"Failed to analyze directory {directory}: {e}")
            return self._save_empty_analysis(directory, str(e))

    def _save_empty_analysis(self, directory: Path, reason: str) -> bool:
        """Save empty analysis result when directory cannot be analyzed."""
        output_path = directory / f"model_{directory.name}.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"[Analysis failed: {reason}]\n")
        return False