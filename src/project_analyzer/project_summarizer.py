"""Project summarizer module for ProjectAnalyzer - Step 5: Generate final project summary."""

import re
from pathlib import Path
from typing import Set, List

from openai import OpenAI


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting tags and :emoji: tags from text."""
    stripped = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    stripped = re.sub(r':[^:]+:', '', stripped)
    return stripped.strip()


class ProjectSummarizer:
    """Generates final project summary from directory analyses using bottom-up hierarchy."""

    def __init__(self, project_path: Path, config, logger):
        self.project_path = project_path
        self.config = config
        self.logger = logger

    def _create_client(self) -> OpenAI:
        """Create a new OpenAI client instance."""
        api_key = self.config.get("model.api_key")
        base_url = self.config.get("model.base_url") or None
        return OpenAI(api_key=api_key, base_url=base_url)

    def summarize(self) -> bool:
        """Generate project summary using bottom-up hierarchical approach."""
        try:
            self.logger.info("Starting hierarchical project summary generation...")
            self._process_directory(self.project_path)
            self.logger.info("Project summary generation completed")
            return True
        except Exception as e:
            self.logger.error(f"Failed to generate project summary: {e}")
            return False
        finally:
            # Ensure tmp files are always cleaned up, even on error
            self._cleanup_tmp_files(self.project_path)

    def _process_directory(self, dir_path: Path) -> None:
        """Process directory using post-order traversal (children first, then parent)."""
        subdirs = [d for d in dir_path.iterdir() if d.is_dir()]

        # First, recursively process all subdirectories
        for subdir in subdirs:
            try:
                self._process_directory(subdir)
            except Exception as e:
                self.logger.error(f"Failed to process subdirectory {subdir}: {e}")
                continue

        # Then, process current directory
        if not subdirs:
            # Leaf directory: copy model_*.md to parent's tmp_model_*.md
            self._process_leaf_directory(dir_path)
        else:
            # Non-leaf directory: generate summary from children and current
            self._process_non_leaf_directory(dir_path)

    def _process_leaf_directory(self, dir_path: Path) -> None:
        """Leaf directory: directly copy model_*.md to parent's tmp_model_*.md."""
        if dir_path == self.project_path:
            return

        model_file = dir_path / f"model_{dir_path.name}.md"
        if not model_file.exists():
            self.logger.debug(f"No model file for leaf directory: {dir_path}")
            return

        parent = dir_path.parent
        tmp_file = parent / f"tmp_model_{dir_path.name}.md"

        try:
            with open(model_file, "r", encoding="utf-8") as f:
                content = f.read()
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(content)
            self.logger.debug(f"Copied leaf summary: {model_file} -> {tmp_file}")
        except Exception as e:
            self.logger.error(f"Failed to copy leaf summary: {e}")

    def _get_processed_subdirs(self, dir_path: Path) -> Set[str]:
        """Extract processed subdirectory names from tmp_model_*.md filenames."""
        processed = set()
        for f in dir_path.iterdir():
            if f.is_file() and f.name.startswith("tmp_model_") and f.name.endswith(".md"):
                # Extract dirname: tmp_model_SRC.md -> SRC
                name = f.name[9:-3]  # Remove "tmp_model_" prefix and ".md" suffix
                processed.add(name)
        return processed

    def _is_all_subdirs_processed(self, dir_path: Path) -> bool:
        """Check if all subdirectories have been processed."""
        subdirs = {d.name for d in dir_path.iterdir() if d.is_dir()}
        processed = self._get_processed_subdirs(dir_path)
        return subdirs == processed

    def _process_non_leaf_directory(self, dir_path: Path) -> None:
        """Non-leaf directory: generate summary from children tmp files and current model."""
        if dir_path == self.project_path:
            # Root directory: generate final analyse_report.md
            self._generate_root_summary(dir_path)
            return

        # Check if all subdirs are processed
        if not self._is_all_subdirs_processed(dir_path):
            self.logger.debug(f"Not all subdirs processed yet for: {dir_path}")
            return

        # Generate summary for this directory
        self._generate_directory_summary(dir_path)

    def _generate_root_summary(self, dir_path: Path) -> bool:
        """Generate final project summary for root directory."""
        client = self._create_client()
        success = False

        try:
            # Collect all tmp_model_*.md files in root
            tmp_files = list(dir_path.glob("tmp_model_*.md"))
            if not tmp_files:
                self.logger.error("No tmp_model files found for root summary")
                return False

            self.logger.info(f"Generating root summary from {len(tmp_files)} tmp files")

            combined_content = ""
            for tmp_file in sorted(tmp_files):
                with open(tmp_file, "r", encoding="utf-8") as f:
                    combined_content += f"\n\n# {tmp_file.stem[9:]}\n\n"  # Remove tmp_model_ prefix
                    combined_content += f.read()

            prompt_template = self.config.project_summary_prompt
            prompt = prompt_template.replace("{content}", combined_content)

            self.logger.info("Generating final project summary...")
            response = client.chat.completions.create(
                model=self.config.get("model.model_name", "gpt-4"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
            )

            summary = response.choices[0].message.content
            clean_summary = _strip_markdown(summary)

            output_path = dir_path / "analyse_report.md"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"# 项目分析报告\n\n")
                f.write(f"**项目路径:** {dir_path}\n\n")
                f.write(clean_summary)

            self.logger.info(f"Final project summary saved to: {output_path}")
            success = True
            return True

        except Exception as e:
            self.logger.error(f"Failed to generate root summary: {e}")
            return False
        finally:
            # Always cleanup tmp files in root, regardless of success or failure
            self._cleanup_tmp_files(dir_path)

    def _generate_directory_summary(self, dir_path: Path) -> bool:
        """Generate summary for a non-leaf directory and save to parent's tmp file."""
        client = self._create_client()

        try:
            # Get all tmp_model_*.md files (from subdirectories)
            tmp_files = list(dir_path.glob("tmp_model_*.md"))
            model_file = dir_path / f"model_{dir_path.name}.md"

            combined_content = ""

            # Add subdirectory summaries
            for tmp_file in sorted(tmp_files):
                with open(tmp_file, "r", encoding="utf-8") as f:
                    combined_content += f"\n\n## 子目录: {tmp_file.stem[9:]}\n\n"
                    combined_content += f.read()

            # Add current directory's own analysis
            if model_file.exists():
                with open(model_file, "r", encoding="utf-8") as f:
                    combined_content += f"\n\n## 当前目录分析\n\n"
                    combined_content += f.read()

            prompt_template = self.config.project_summary_prompt
            prompt = prompt_template.replace("{content}", combined_content)

            self.logger.info(f"Generating summary for directory: {dir_path.name}")
            response = client.chat.completions.create(
                model=self.config.get("model.model_name", "gpt-4"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
            )

            summary = response.choices[0].message.content
            clean_summary = _strip_markdown(summary)

            # Save to parent's tmp_model_*.md
            parent = dir_path.parent
            parent_tmp_file = parent / f"tmp_model_{dir_path.name}.md"
            with open(parent_tmp_file, "w", encoding="utf-8") as f:
                f.write(f"{dir_path.name}\n\n")
                f.write(clean_summary)

            self.logger.debug(f"Directory summary saved to: {parent_tmp_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to generate directory summary for {dir_path}: {e}")
            return False
        finally:
            # Always cleanup tmp files in current directory, regardless of success or failure
            self._cleanup_tmp_files(dir_path)

    def _cleanup_tmp_files(self, dir_path: Path) -> None:
        """Clean up all tmp_* files recursively in the specified directory tree."""
        for tmp_file in dir_path.rglob("tmp_*"):
            if tmp_file.is_file():
                try:
                    tmp_file.unlink()
                    self.logger.debug(f"Cleaned up tmp file: {tmp_file}")
                except Exception as e:
                    self.logger.error(f"Failed to delete tmp file {tmp_file}: {e}")
