"""File analyzer module for ProjectAnalyzer - Step 3: Multi-threaded file analysis."""

import math
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict

from openai import OpenAI

from .utils import safe_read_file


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting tags and :emoji: tags from text."""
    stripped = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    stripped = re.sub(r':[^:]+:', '', stripped)
    return stripped.strip()


class FileAnalyzer:
    """Analyzes individual files using LLM in multi-threaded manner."""

    def __init__(self, project_path: Path, config, logger):
        self.project_path = project_path
        self.config = config
        self.logger = logger
        self.max_workers = config.max_workers
        self.force_overwrite = False  # When True, delete existing analysis before re-analyzing

    def _create_client(self) -> OpenAI:
        """Create a new OpenAI client instance."""
        api_key = self.config.get("model.api_key")
        base_url = self.config.get("model.base_url") or None

        if not api_key:
            self.logger.fatal("API key not configured")

        return OpenAI(api_key=api_key, base_url=base_url)

    def analyze_files(self, files: List[Path]) -> Dict[str, bool]:
        """
        Analyze all files using multi-threading.

        Returns:
            Dict mapping file path to success status
        """
        total_files = len(files)
        self.logger.info(f"Starting file analysis: {total_files} files")

        results = {}
        completed = 0
        batch_size = max(1, min(10, total_files // 20))

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self._analyze_single_file, f): f for f in files
            }

            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    success = future.result()
                    results[str(file_path)] = success
                    completed += 1

                    if completed % batch_size == 0 or completed == total_files:
                        self.logger.info(f"[进度] 已处理 {completed}/{total_files} 个文件")
                except Exception as e:
                    self.logger.error(f"处理文件失败 {file_path}: {e}")
                    results[str(file_path)] = False
                    completed += 1

        success_count = sum(1 for v in results.values() if v)
        self.logger.info(f"File analysis completed: {success_count}/{total_files} successful")
        return results

    def _analyze_single_file(self, file_path: Path) -> bool:
        """Analyze a single file with its own API session."""
        output_path = file_path.parent / f"ana_{file_path.name}.md"

        if output_path.exists():
            if self.force_overwrite:
                # In diff mode, force re-analysis by removing existing result
                try:
                    output_path.unlink()
                    self.logger.debug(f"Removed old analysis for re-analysis: {output_path}")
                except Exception as e:
                    self.logger.error(f"Failed to remove old analysis {output_path}: {e}")
            else:
                self.logger.info(f"跳过已存在的分析结果: {output_path}")
                return True

        self.logger.info(f"正在分析文件: {file_path}")

        client = self._create_client()

        try:
            content = safe_read_file(file_path)
            if not content or content == "[Unable to read file]":
                return self._save_empty_analysis(file_path, "Unable to read file")

            prompt_template = self.config.file_analysis_prompt
            prompt = prompt_template.replace("{content}", content)

            response = client.chat.completions.create(
                model=self.config.get("model.model_name", "gpt-4"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
            )

            analysis = response.choices[0].message.content
            clean_analysis = _strip_markdown(analysis)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"# {file_path.name}\n\n")
                f.write(f"**Source:** {file_path}\n\n")
                f.write(clean_analysis)

            return True

        except Exception as e:
            self.logger.error(f"Failed to analyze {file_path}: {e}")
            return self._save_empty_analysis(file_path, str(e))

    def _save_empty_analysis(self, file_path: Path, reason: str) -> bool:
        """Save empty analysis result when file cannot be analyzed."""
        output_path = file_path.parent / f"ana_{file_path.name}.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"[Analysis failed: {reason}]\n")
        return False