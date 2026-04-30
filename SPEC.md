# ProjectAnalyzer 项目规格说明书

## 一、项目概述

| 项目 | 内容 |
|------|------|
| 项目名称 | ProjectAnalyzer |
| 项目类型 | Python 命令行工具 |
| 核心功能 | 接受软件项目路径，分析项目结构，调用大模型生成项目总结文档 |
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
  -h, --help          显示帮助信息（包含配置文件格式说明）
  --version           显示版本信息
```

## 五、工作流程（共8步）

| 步骤 | 内容 | 输出 |
|------|------|------|
| 0 | 读取配置文件 | 加载 model/threading/prompts/exclude 配置 |
| 1 | 接收命令行参数 | 解析项目路径、配置文件路径 |
| 2 | 扫描项目结构 | 输出即时总结（目录数/文件数）到屏幕和文件 |
| 3 | 多线程文件分析 | 生成 `ana_{filename}.md` 文件 |
| 4 | 多线程目录分析 | 生成 `model_{dirname}.md` 文件 |
| 5 | 项目总结 | 生成 `analyse_report.md` 文件 |
| 6 | 清理临时文件 | 删除所有 `ana_*.md` 和 `model_*.md` |
| 7 | 结束 | 正常退出 |

### 各步骤详细说明

**步骤2 - 项目结构扫描总结**:
- 递归遍历项目目录下所有文件和子目录
- 输出项目路径、目录总数、文件总数
- 同时输出到屏幕和总结报告文件

**步骤3 - 文件分析（多线程）**:
- 遍历项目中的常规文件（代码/文档/脚本/工具等）
- 为每个文件新建工作线程，调用大模型分析
- 输出：一句话总结（不超过200字）、接口/调用列表
- 保存到 `ana_{filename}.md`
- 进度显示：批量更新，以文件为单位

**步骤4 - 目录分析（多线程）**:
- 读取该目录下所有 `ana_*.md` 文件
- 为每个目录新建工作线程，调用大模型总结
- 输出：目录组件总结（不超过500字）、接口/调用列表
- 保存到 `model_{dirname}.md`
- 进度显示：批量更新，以目录为单位

**步骤5 - 项目总结**:
- 读取所有 `model_*.md` 文件
- 调用大模型进行项目总结
- 输出：核心功能、流程逻辑（不超过1000字）
- 保存到 `analyse_report.md`

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
| `{项目名}_scan_summary.md` | 项目结构扫描总结（步骤2） | 项目根目录 |
| `ana_{filename}.md` | 单个文件分析结果（步骤3） | 与源文件同目录 |
| `model_{dirname}.md` | 目录分析结果（步骤4） | 对应目录下 |
| `analyse_report.md` | 最终项目总结报告（步骤5） | 项目根目录 |
| `{项目名}.log` | 详细运行日志 | 项目根目录 |

## 八、技术架构

```
project-analyzer/
├── src/
│   └── project_analyzer/
│       ├── __init__.py
│       ├── main.py           # CLI 入口
│       ├── config.py         # 配置文件读取
│       ├── scanner.py        # 项目结构扫描
│       ├── file_analyzer.py  # 文件分析（多线程）
│       ├── dir_analyzer.py   # 目录分析（多线程）
│       ├── project_summarizer.py  # 项目总结生成
│       ├── logger.py         # 日志管理
│       └── utils.py          # 工具函数
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
5. 步骤2输出项目扫描总结（目录数/文件数）
6. 步骤3-5 多线程调用大模型进行分析
7. 步骤5生成最终报告 `analyse_report.md`
8. 步骤6清理所有临时文件
9. 详细日志保存到 `{项目目录名}.log`
10. 进度显示：批量更新，以文件/目录为单位
11. 错误处理：屏幕显示 + 日志记录 + 程序退出
12. 跨平台支持（Windows/Linux/macOS）

## 十一、注意事项

- 提示词中的 `{content}` 占位符会在运行时替换为实际内容
- 最大并发线程数由 `threading.max_workers` 配置
- 大模型 API 配置必须正确，否则无法完成分析