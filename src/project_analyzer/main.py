"""Main CLI entry point for ProjectAnalyzer."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from project_analyzer.config import Config
from project_analyzer.logger import Logger
from project_analyzer.scanner import ProjectScanner
from project_analyzer.file_analyzer import FileAnalyzer
from project_analyzer.dir_analyzer import DirectoryAnalyzer
from project_analyzer.project_summarizer import ProjectSummarizer
from project_analyzer.utils import get_regular_files


CONFIG_HELP = """
工作流程:
  步骤2: 扫描项目结构
  步骤3: 文件分析 (分析每个源文件)
  步骤4: 目录分析 (汇总目录级分析)
  步骤5: 生成项目总结
  步骤6: 清理临时文件

可用选项:
  --step STEP   指定只执行某个步骤 (2-6)
"""


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="project-analyzer",
        description="分析软件项目并生成项目总结文档",
        epilog=CONFIG_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("project_path", help="要分析的项目路径")
    parser.add_argument(
        "--config",
        default="project_analyzer_config.yaml",
        help="配置文件路径 (默认: project_analyzer_config.yaml)",
    )
    parser.add_argument(
        "--step",
        type=int,
        choices=[2, 3, 4, 5, 6],
        help="指定只执行某个步骤 (2:扫描, 3:文件分析, 4:目录分析, 5:总结, 6:清理)",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    return parser.parse_args()


def cleanup_temp_files(project_path: Path, config, logger):
    """Clean up temporary ana_*.md and model_*.md files based on config."""
    logger.info("Cleaning up temporary files...")

    cleaned = 0

    if config.file_analysis_clear:
        for file_path in project_path.rglob("ana_*.md"):
            try:
                file_path.unlink()
                cleaned += 1
            except Exception as e:
                logger.error(f"Failed to delete {file_path}: {e}")

    if config.directory_analysis_clear:
        for file_path in project_path.rglob("model_*.md"):
            try:
                file_path.unlink()
                cleaned += 1
            except Exception as e:
                logger.error(f"Failed to delete {file_path}: {e}")

    logger.info(f"Cleaned up {cleaned} temporary files")


def main():
    """Main entry point."""
    args = parse_args()

    project_path = Path(args.project_path).resolve()

    if not project_path.exists():
        print(f"Error: 路径不存在: {project_path}")
        sys.exit(1)

    if not project_path.is_dir():
        print(f"Error: 路径不是有效目录: {project_path}")
        sys.exit(1)
    
    config_path = Path(args.config)
    config = Config(config_path)

    logger = Logger(project_path)
    logger.info("=" * 50)
    logger.info("ProjectAnalyzer 启动")
    logger.info("=" * 50)

    scanner = ProjectScanner(project_path, logger)

    if not args.step or args.step == 2:
        logger.info("步骤 2: 扫描项目结构...")
        all_files, dir_count, file_count = scanner.scan()
        logger.info(f"扫描完成: {dir_count} 个目录, {file_count} 个文件")

        summary = scanner.generate_summary(dir_count, file_count)

        print("\n" + "=" * 50)
        print("项目结构扫描总结")
        print("=" * 50)
        print(f"项目路径: {project_path}")
        print(f"目录总数: {dir_count}")
        print(f"文件总数: {file_count}")
        print("=" * 50 + "\n")

        summary_path = scanner.save_summary(summary)
        print(f"详细总结已保存到: {summary_path}\n")

    if not args.step or args.step == 3:
        logger.info("步骤 3: 开始文件分析...")
        regular_files = get_regular_files(project_path, config.exclude_config)
        logger.info(f"找到 {len(regular_files)} 个需要分析的文件")

        file_analyzer = FileAnalyzer(project_path, config, logger)
        file_results = file_analyzer.analyze_files(regular_files)

    if not args.step or args.step == 4:
        logger.info("步骤 4: 开始目录分析...")
        dir_analyzer = DirectoryAnalyzer(project_path, config, logger)
        dir_results = dir_analyzer.analyze_directories()

    if not args.step or args.step == 5:
        logger.info("步骤 5: 生成项目总结...")
        summarizer = ProjectSummarizer(project_path, config, logger)
        success = summarizer.summarize()

        if not success:
            logger.fatal("项目总结生成失败")

    if not args.step or args.step == 6:
        logger.info("步骤 6: 清理临时文件...")
        cleanup_temp_files(project_path, config, logger)

    logger.info("=" * 50)
    logger.info("ProjectAnalyzer 完成")
    logger.info(f"最终报告: {project_path / 'analyse_report.md'}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()