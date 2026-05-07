# ProjectAnalyzer 项目规格说明书

## 一、项目概述

| 项目 | 内容 |
|------|------|
| 项目名称 | ProjectAnalyzer |
| 项目类型 | Python 命令行工具 |
| 核心功能 | 接受软件项目路径，分析项目结构，调用大模型生成项目总结文档；支持 `--diff` 增量模式 |
| 目标用户 | 大模型（AI Agent）、自动化工具 |

## 二、跨平台支持

- Windows
- Linux
- macOS

## 三、配置文件

**文件名**: `project_analyzer_config.yaml`

**配置内容**:

```yaml
# 大模型 API 配置
model:
  provider: "openai"            # 大模型提供商
  api_key: "your-api-key"      # API 密钥
  model_name: "gpt-4"          # 模型名称
  base_url: ""                 # API 地址（可选）

# 并发线程配置
threading:
  max_workers: 4              # 最大并发工作线程数

# 提示词配置
prompts:
  file_analysis: |
    请分析以下文件内容：
    {content}
    要求：
    1. 一句话总结文件功能，不超过200字
    2. 列出该文件对外暴露的接口或外部调用（如果有）

  directory_analysis: |
    请分析以下目录的组件总结：
    {content}
    要求：
    1. 对目录下的项目组件进行总结，简述其核心逻辑，不超过500字
    2. 列出该目录对外暴露的接口或外部调用（如果有）

  project_summary: |
    请对整个项目进行总结：
    {content}
    要求：
    简述其核心功能、流程逻辑，不超过1000字

# 快照配置（--diff 增量模式使用）
snapshot:
  path: ".project_snapshot.json"    # 快照文件路径
  hash_algorithm: "md5"             # 哈希算法 (md5/sha256)

# 级联更新配置（--diff 增量模式使用）
cascade:
  enabled: true                     # 是否启用级联更新

# 排除配置
exclude:
  directories:
    - ".git"
    - "__pycache__"
    - "node_modules"
    - ".idea"
    - ".vscode"
    - "dist"
    - "build"

  file_patterns:
    - "*.pyo"
    - "*.so"
    - "*.dll"
    - "*.exe"
    - "*.log"
    - "ana_*.md"
    - "model_*.md"
    - "analyse_report.md"
```

## 四、命令行接口

```bash
project-analyzer <项目路径> [选项]

选项：
  --config <文件>     指定配置文件路径（默认: ./project_analyzer_config.yaml）
  --diff              激活增量对比模式（无快照时自动全量分析）
  --dry-run           仅显示变化，不执行分析（需配合 --diff）
  --step <步骤号>     指定只执行某个步骤 (2-7)
  -h, --help          显示帮助信息（包含配置文件格式说明）
  --version           显示版本信息
```

## 五、工作流程

### 5.1 全量模式（默认，无 --diff）

| 步骤 | 内容 | 输出 |
|------|------|------|
| 0 | 读取配置文件 | 加载 model/threading/prompts/exclude/snapshot/cascade 配置 |
| 1 | 接收命令行参数 | 解析项目路径、配置文件路径 |
| 2 | 扫描项目结构 | 输出即时总结（目录数/文件数）到屏幕和文件 |
| 3 | 多线程文件分析 | 生成 `ana_{filename}.md` 文件 |
| 4 | 多线程目录分析 | 生成 `model_{dirname}.md` 文件 |
| 5 | 项目总结 | 生成 `analyse_report.md` 文件 |
| 6 | 保存快照 | 保存 `.project_snapshot.json` |
| 7 | 清理临时文件 | 删除所有 `ana_*.md` 和 `model_*.md` |

### 5.2 增量模式（--diff）

| 步骤 | 内容 | 输出 |
|------|------|------|
| 2 | 检测文件变化 | 对比快照，识别新增/修改/删除文件，生成差异报告 |
| 3 | 增量文件分析 | 仅对变化文件重新分析，强制覆盖已有 `ana_*.md` |
| 4 | 增量目录分析 | 仅对受影响目录重新分析，强制覆盖已有 `model_*.md` |
| 5 | 更新项目总结 | 更新 `analyse_report.md` |
| 6 | 保存快照 | 保存更新后的 `.project_snapshot.json` |
| 7 | 清理临时文件 | 删除所有 `ana_*.md` 和 `model_*.md` |

**首次运行自动全量**: 当 `--diff` 模式下无现有快照时，自动退化为全量分析，所有文件标记为新增，分析完成后保存快照。

### 各步骤详细说明

**步骤2 - 项目结构扫描 / 变化检测**:
- 全量模式：递归遍历项目目录下所有文件和子目录，输出目录总数、文件总数
- 增量模式：加载快照对比当前文件哈希，识别新增/修改/删除，生成差异报告
  - 无快照时：自动执行全量分析

**步骤3 - 文件分析（多线程）**:
- 全量模式：遍历项目中的常规文件，为每个文件新建工作线程调用大模型分析
- 增量模式：仅对变化文件重新分析，强制覆盖已有 `ana_*.md`
- 保存到 `ana_{filename}.md`
- 进度显示：批量更新，以文件为单位

**步骤4 - 目录分析（多线程）**:
- 全量模式：读取每个目录下所有 `ana_*.md` 文件，调用大模型总结
- 增量模式：仅对受影响目录重新分析，强制覆盖已有 `model_*.md`
- 保存到 `model_{dirname}.md`
- 进度显示：批量更新，以目录为单位

**步骤5 - 项目总结**:
- 读取所有 `model_*.md` 文件，调用大模型进行项目总结
- 保存到 `analyse_report.md`

**步骤6 - 保存快照**:
- 扫描当前项目所有文件，计算文件哈希
- 保存到 `.project_snapshot.json`，供下次 `--diff` 使用

## 六、日志与错误处理

| 项目 | 内容 |
|------|------|
| 日志文件 | `{项目目录名}.log`，保存在项目根目录 |
| 日志格式 | 包含时间戳 |
| 错误显示 | 屏幕显示详细信息 |
| 错误日志 | 同时写入日志文件 |
| 程序退出 | 任何错误发生时，程序退出 |

## 七、输出文件说明

| 文件 | 内容 | 位置 |
|------|------|------|
| `{项目名}_scan_summary.md` | 项目结构扫描总结（全量模式步骤2） | 项目根目录 |
| `{项目名}_diff_report.md` | 差异分析报告（增量模式步骤2） | 项目根目录 |
| `ana_{filename}.md` | 单个文件分析结果（步骤3） | 与源文件同目录 |
| `model_{dirname}.md` | 目录分析结果（步骤4） | 对应目录下 |
| `analyse_report.md` | 最终项目总结报告（步骤5） | 项目根目录 |
| `.project_snapshot.json` | 文件状态快照（步骤6） | 项目根目录 |
| `{项目名}.log` | 详细运行日志 | 项目根目录 |

## 八、技术架构

```
project-analyzer/
├── src/
│   └── project_analyzer/
│       ├── __init__.py
│       ├── main.py               # CLI 入口，全量/增量流程编排
│       ├── config.py             # 配置文件读取（含snapshot/cascade配置）
│       ├── scanner.py            # 项目结构扫描
│       ├── file_analyzer.py      # 文件分析（多线程，支持强制覆盖）
│       ├── dir_analyzer.py       # 目录分析（多线程，支持增量模式）
│       ├── project_summarizer.py # 项目总结生成（层级汇总）
│       ├── snapshot.py           # 快照管理（变化检测）
│       ├── logger.py             # 日志管理
│       └── utils.py              # 工具函数（含哈希计算）
├── tests/
├── pyproject.toml
├── project_analyzer_config.yaml.example
└── README.md
```

## 九、开发依赖

- Python >= 3.8
- `openai` SDK（用于调用大模型 API）
- `PyYAML`（用于读取配置文件）

## 十、验收标准

1. 工具可通过 `project-analyzer --help` 显示帮助信息
2. 支持 `--config` 指定配置文件路径
3. 配置文件格式为 YAML
4. 对不存在/无效路径输出错误并退出
5. 全量模式下步骤2输出项目扫描总结（目录数/文件数）
6. 步骤3-5 多线程调用大模型进行分析
7. 步骤5生成最终报告 `analyse_report.md`
8. 步骤6保存文件快照 `.project_snapshot.json`
9. 步骤7清理所有临时文件
10. `--diff` 模式下检测文件变化，仅分析变化部分
11. `--diff` 模式无快照时自动退化为全量分析
12. `--dry-run` 仅显示变化不执行分析
13. 详细日志保存到 `{项目目录名}.log`
14. 进度显示：批量更新，以文件/目录为单位
15. 错误处理：屏幕显示 + 日志记录 + 程序退出
16. 跨平台支持（Windows/Linux/macOS）

## 十一、注意事项

- 提示词中的 `{content}` 占位符会在运行时替换为实际内容
- 最大并发线程数由 `threading.max_workers` 配置
- 大模型 API 配置必须正确，否则无法完成分析
- `--diff` 模式依赖快照文件，首次运行自动全量分析并保存快照
- 快照文件 `.project_snapshot.json` 记录文件哈希，删除后将导致下次全量分析
