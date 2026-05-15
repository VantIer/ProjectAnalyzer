"""Main CLI entry point for ShadowCopyer."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shadow_copyer.config import Config
from shadow_copyer.logger import Logger
from shadow_copyer.shadow_syncer import ShadowSyncer


CONFIG_HELP = """
工作流程:
  步骤1: 读取配置，确定项目路径和影子目录路径
  步骤2: 扫描项目目录中所有说明文档
  步骤3: 在影子目录中创建对应的目录结构
  步骤4: 对比文档差异，执行增量拷贝
  步骤5: 清理影子目录中的孤立文件
  步骤6: 生成同步报告并保存状态

可用选项:
  --shadow-dir DIR   指定影子文档目录路径
  --full             全量同步，忽略增量状态
  --clean            清理影子目录中多余的文件
  --dry-run          仅显示将要执行的操作，不实际执行
"""


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="shadow-copyer",
        description="将项目说明文档镜像拷贝到独立的影子文档目录",
        epilog=CONFIG_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("project_path", help="要同步的项目路径")
    parser.add_argument(
        "--config",
        default="shadow_copyer_config.yaml",
        help="配置文件路径 (默认: shadow_copyer_config.yaml)",
    )
    parser.add_argument(
        "--shadow-dir",
        help="指定影子文档目录路径（覆盖配置文件中的设置）",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="全量同步，忽略增量状态",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="清理影子目录中多余的文件",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅显示将要执行的操作，不实际执行",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    return parser.parse_args()


def resolve_shadow_path(project_path: Path, config, args) -> Path:
    """Resolve the shadow directory path from config or CLI args."""
    if args.shadow_dir:
        return Path(args.shadow_dir).resolve()

    # Use config-based path
    root_dir = config.shadow_root_dir
    naming = config.shadow_naming

    # Replace {project} placeholder in naming template
    shadow_name = naming.replace("{project}", project_path.name)
    shadow_path = Path(root_dir) / shadow_name

    # If root_dir is relative, resolve relative to project parent
    if not Path(root_dir).is_absolute():
        shadow_path = project_path.parent / shadow_path

    return shadow_path.resolve()


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

    # Override config with CLI args
    if args.full:
        config._config.setdefault("sync", {})["incremental"] = False

    if args.clean:
        config._config.setdefault("sync", {})["clean_orphan"] = True

    shadow_path = resolve_shadow_path(project_path, config, args)

    logger = Logger(project_path)
    logger.info("=" * 50)
    logger.info("ShadowCopyer 启动")
    logger.info("=" * 50)
    logger.info(f"项目路径: {project_path}")
    logger.info(f"影子目录: {shadow_path}")

    syncer = ShadowSyncer(project_path, shadow_path, config, logger)

    logger.info("开始同步...")
    stats = syncer.sync(dry_run=args.dry_run)

    # Generate and display sync report
    report = syncer.generate_sync_report(stats)

    print("\n" + "=" * 50)
    print("影子文档同步报告")
    print("=" * 50)
    print(f"项目路径: {project_path}")
    print(f"影子目录: {shadow_path}")
    print(f"新增拷贝: {stats['copied']}")
    print(f"更新覆盖: {stats['updated']}")
    print(f"跳过(未变化): {stats['skipped']}")
    print(f"删除孤立: {stats['deleted']}")
    print(f"错误: {stats['errors']}")
    print("=" * 50 + "\n")

    # Save sync report to shadow directory
    if not args.dry_run:
        report_path = shadow_path / "sync_report.md"
        shadow_path.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"Sync report saved to: {report_path}")

    logger.info("=" * 50)
    logger.info("ShadowCopyer 完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
