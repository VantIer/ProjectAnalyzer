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
from project_analyzer.snapshot import FileSnapshot
from project_analyzer.utils import get_regular_files


CONFIG_HELP = """
工作流程 (全量模式, 默认):
  步骤2: 扫描项目结构
  步骤3: 文件分析 (分析每个源文件)
  步骤4: 目录分析 (汇总目录级分析)
  步骤5: 生成项目总结
  步骤6: 保存快照
  步骤7: 清理临时文件

工作流程 (--diff 增量模式):
  步骤2: 检测文件变化 (对比快照)
  步骤3: 增量文件分析 (仅分析变化的文件)
  步骤4: 增量目录分析 (仅分析受影响的目录)
  步骤5: 级联更新项目总结
  步骤6: 保存快照
  步骤7: 清理临时文件

工作流程 (--diff-init 快照初始化模式):
  扫描所有文件并生成快照，不执行任何分析
  适用于全量分析完成后补建快照，以便后续使用 --diff 增量模式

可用选项:
  --diff        激活增量对比模式（无快照时自动退化为全量分析）
  --diff-init   仅生成快照文件，不执行分析
  --step STEP   指定只执行某个步骤 (2-7)
"""


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="project-analyzer",
        description="分析软件项目并生成项目总结文档（支持全量和增量模式）",
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
        "--diff",
        action="store_true",
        help="激活增量对比模式：检查/生成快照，仅更新变化部分（无快照时自动全量分析）",
    )
    parser.add_argument(
        "--diff-init",
        action="store_true",
        help="仅扫描项目文件并生成快照，不执行任何分析",
    )
    parser.add_argument(
        "--step",
        type=int,
        choices=[2, 3, 4, 5, 6, 7],
        help="指定只执行某个步骤 (2:扫描/变化检测, 3:文件分析, 4:目录分析, 5:总结, 6:保存快照, 7:清理)",
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


def run_full_mode(args, project_path, config, logger):
    """Run in full analysis mode (original behavior)."""
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
        logger.info("步骤 6: 保存快照...")
        snapshot = FileSnapshot(project_path, config, logger)
        current_state = snapshot.build_current_state()
        snapshot.save(current_state)

    if not args.step or args.step == 7:
        logger.info("步骤 7: 清理临时文件...")
        cleanup_temp_files(project_path, config, logger)


def run_diff_init_mode(project_path, config, logger):
    """Run in diff-init mode: scan all files and create a snapshot without any analysis."""
    snapshot = FileSnapshot(project_path, config, logger)

    logger.info("扫描项目文件并生成快照...")

    existing_snapshot = snapshot.load()
    current_state = snapshot.build_current_state()

    if existing_snapshot:
        old_count = len(existing_snapshot.get("files", {}))
        logger.info(f"已存在快照 ({old_count} 个文件)，将覆盖更新")

    snapshot.save(current_state)

    file_count = len(current_state)
    print("\n" + "=" * 50)
    print("快照初始化完成")
    print("=" * 50)
    print(f"项目路径: {project_path}")
    print(f"快照文件: {snapshot.snapshot_file}")
    print(f"文件总数: {file_count}")
    print("=" * 50 + "\n")


def _detect_diff_state(snapshot: FileSnapshot) -> tuple:
    """
    Detect diff state from snapshot. Returns a tuple of:
    (changed_files, deleted_files, has_snapshot)

    Used to avoid redundant snapshot.load() calls and ensure
    all single-step executions have the required state.
    """
    old_snapshot = snapshot.load()
    has_snapshot = old_snapshot is not None

    new_files, modified_files, deleted_files, _ = snapshot.detect_changes()
    changed_files = new_files | modified_files

    return changed_files, deleted_files, has_snapshot


def run_diff_mode(args, project_path, config, logger):
    """Run in incremental diff mode."""
    snapshot = FileSnapshot(project_path, config, logger)
    changed_files = set()
    deleted_files = set()

    # Step 2: Detect changes
    if not args.step or args.step == 2:
        logger.info("步骤 2: 检测文件变化...")

        changed_files, deleted_files, has_snapshot = _detect_diff_state(snapshot)

        print("\n" + "=" * 50)
        if has_snapshot:
            print("项目变化检测总结 (增量模式)")
        else:
            print("首次分析 (无快照，执行全量分析)")
        print("=" * 50)
        print(f"新增+修改文件: {len(changed_files)}")
        print(f"删除文件: {len(deleted_files)}")
        print("=" * 50 + "\n")

        if not changed_files and not deleted_files:
            logger.info("没有检测到任何变化")
            # Still save snapshot to update timestamp
            current_state = snapshot.build_current_state()
            snapshot.save(current_state)
            return

        # Clean up documents for deleted files
        if deleted_files:
            cleaned = snapshot.cleanup_deleted_docs(deleted_files)
            logger.info(f"Cleaned up {cleaned} analysis docs for deleted files")

    # Step 3: Incremental file analysis
    if not args.step or args.step == 3:
        # If step 2 was skipped, detect changes now
        if args.step == 3:
            changed_files, deleted_files, _ = _detect_diff_state(snapshot)
            # Clean up docs for deleted files (normally done in step 2)
            if deleted_files:
                cleaned = snapshot.cleanup_deleted_docs(deleted_files)
                logger.info(f"Cleaned up {cleaned} analysis docs for deleted files")

        if changed_files:
            logger.info(f"步骤 3: 增量文件分析 ({len(changed_files)} 个变化文件)...")
            file_analyzer = FileAnalyzer(project_path, config, logger)
            file_analyzer.force_overwrite = True  # Force re-analysis for changed files
            # Filter to only existing files (deleted files won't exist)
            file_paths = [project_path / p for p in changed_files]
            file_paths = [p for p in file_paths if p.exists()]
            file_results = file_analyzer.analyze_files(file_paths)
        else:
            logger.info("步骤 3: 无变化文件需要分析")

    # Step 4: Incremental directory analysis
    if not args.step or args.step == 4:
        # If both step 2 and 3 were skipped, detect changes now
        if args.step == 4:
            changed_files, _, _ = _detect_diff_state(snapshot)

        if changed_files:
            affected_dirs = snapshot.get_affected_directories(changed_files)
            logger.info(f"步骤 4: 增量目录分析 ({len(affected_dirs)} 个受影响目录)...")

            dir_analyzer = DirectoryAnalyzer(project_path, config, logger)
            dir_analyzer.force_overwrite = True  # Force re-analysis for affected directories
            dir_results = dir_analyzer.analyze_directories(affected_dirs)
        else:
            logger.info("步骤 4: 无受影响目录需要分析")

    # Step 5: Cascade update project summary
    if not args.step or args.step == 5:
        logger.info("步骤 5: 更新项目总结...")
        summarizer = ProjectSummarizer(project_path, config, logger)
        success = summarizer.summarize()

        if not success:
            logger.fatal("项目总结更新失败")

    # Step 6: Save snapshot
    if not args.step or args.step == 6:
        logger.info("步骤 6: 保存快照...")
        current_state = snapshot.build_current_state()
        snapshot.save(current_state)

    # Step 7: Cleanup
    if not args.step or args.step == 7:
        logger.info("步骤 7: 清理临时文件...")
        cleanup_temp_files(project_path, config, logger)


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
    if args.diff_init:
        mode = "快照初始化"
    elif args.diff:
        mode = "增量对比"
    else:
        mode = "全量分析"
    logger.info(f"运行模式: {mode}")
    logger.info("=" * 50)

    if args.diff_init:
        run_diff_init_mode(project_path, config, logger)
    elif args.diff:
        run_diff_mode(args, project_path, config, logger)
    else:
        run_full_mode(args, project_path, config, logger)

    logger.info("=" * 50)
    logger.info("ProjectAnalyzer 完成")
    logger.info(f"最终报告: {project_path / 'analyse_report.md'}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
