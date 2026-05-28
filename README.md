# ProjectAnalyzer

一个跨平台命令行工具，用于分析软件项目并生成项目总结文档。支持全量分析和 `--diff` 增量对比两种模式。

## 功能特性

- 分析软件项目结构
- 调用大模型（OpenAI 兼容 API）进行深度分析
- 多线程并发处理
- 生成 Markdown 格式的项目总结报告
- `--diff` 增量模式：基于文件哈希快照，仅分析变化部分
- `--diff-init` 快照初始化：仅生成快照，不执行分析
- `--step` 单步执行：支持从中断处续跑
- 支持 Windows、Linux、macOS

## 安装

```bash
pip install -e .
```

## 配置

在项目根目录创建 `project_analyzer_config.yaml` 配置文件：

```yaml
# 大模型 API 配置
model:
  provider: "openai"
  api_key: "your-api-key"
  model_name: "gpt-4"
  base_url: ""

# 并发线程配置
threading:
  max_workers: 4

# 提示词配置，{content}将被替换为实际分析的内容
# 修改提示词，就可以实现不同的分析、过滤、蒸馏效果，可自由发挥
prompts:
  file_analysis: |
    请分析以下文件内容：
    {content}
    要求：
    1. 一句话总结文件功能，不超过500字
    2. 列出该文件对外暴露的接口（如果有）
    3. 列出该文件的外部引用（如果有）

  directory_analysis: |
    请分析以下目录的代码功能总结内容：
    {content}
    要求：
    1. 根据功能描述与引用关系，对目录下的代码功能进行总结，简述其核心逻辑，不超过1000字
    2. 列出该目录中代码对外暴露的接口或外部调用（如果有）
    3. 列出该目录中代码的外部引用（如果有）

  model_analysis: |
    根据以下各个子模块功能分析内容，请对本模块进行功能分析：
    {content}
    要求：
    1. 根据功能描述与引用关系，对本模块功能进行总结，简述其核心逻辑，并描述该目录内各组件之间的关系，不超过1000字
    2. 列出本模块对外暴露的接口或外部调用（如果有）
    3. 列出本模块的外部引用（如果有）

  project_summary: |
    根据以下功能描述与引用关系，请对整个项目进行总结：
    {content}
    要求：
    1. 详细描述核心功能
    2. 详述该目录内各组件之间的关系
    3. 详细描述流程逻辑
    4. 根据其流程逻辑，绘制详细流程图
    5. 详细展示各个文件、模块在流程中的功能与流程关系

# 快照配置（--diff 增量模式使用）
snapshot:
  path: ".project_snapshot.json"
  hash_algorithm: "md5"

# 级联更新配置（--diff 增量模式使用）
cascade:
  enabled: true

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
    - "src_scan_summary.md"

# 清理配置
cleanup:
  file_analysis_clear: false        # 是否删除文件分析结果 (ana_*.md)
  directory_analysis_clear: true    # 是否删除目录分析结果 (model_*.md)
  model_analysis_clear: true        # 是否删除模块汇总文件 (tmp_*.md)
```

## 使用方法

### 全量模式（默认）

```bash
python -m src.main /path/to/project --config /path/to/config.yaml
```

### 增量模式

```bash
# 首次使用增量模式前，先用 --diff-init 生成快照
python -m src.main /path/to/project --diff-init

# 或者先运行全量分析（步骤6会自动保存快照），之后使用增量模式
python -m src.main /path/to/project --diff
```

### 快照初始化

```bash
# 仅扫描文件并生成快照，不执行任何分析
python -m src.main /path/to/project --diff-init
```

### 预览变化

```bash
# 仅检测变化，不执行分析（使用步骤2）
python -m src.main /path/to/project --diff --step 2
```

### 单步执行

支持中断续跑，已完成的步骤会自动跳过（全量模式下已有 `ana_*.md` / `model_*.md` 不会被覆盖）：

```bash
python -m src.main /path/to/project --step 2  # 仅扫描项目结构
python -m src.main /path/to/project --step 3  # 仅执行文件分析
python -m src.main /path/to/project --step 4  # 仅执行目录分析
python -m src.main /path/to/project --step 5  # 仅生成项目总结
python -m src.main /path/to/project --step 6  # 仅保存快照
python -m src.main /path/to/project --step 7  # 仅清理临时文件
```

增量模式也支持单步执行（会自动检测变化）：

```bash
python -m src.main /path/to/project --diff --step 3  # 增量文件分析
python -m src.main /path/to/project --diff --step 4  # 增量目录分析
```

## 输出文件

| 文件                       | 内容              | 位置      | 清理        |
| ------------------------ | --------------- | ------- | --------- |
| `{项目名}_scan_summary.md`  | 项目结构扫描总结（步骤2）   | 项目根目录   | 否         |
| `ana_{filename}.md`      | 单个文件分析结果（步骤3）   | 与源文件同目录 | 根据配置      |
| `model_{dirname}.md`     | 目录分析结果（步骤4）     | 对应目录下   | 根据配置      |
| `tmp_model_{dirname}.md` | 临时汇总文件（步骤5层级汇总） | 对应目录下   | 是（步骤5结束时） |
| `analyse_report.md`      | 最终项目总结报告（步骤5）   | 项目根目录   | 否         |
| `.project_snapshot.json` | 文件状态快照（步骤6）     | 项目根目录   | 否         |
| `{项目名}.log`              | 详细运行日志          | 项目根目录   | 否         |

## 项目架构

```
project-analyzer/
├── src/
│   ├── __init__.py           # 包初始化，版本定义
│   ├── main.py               # CLI入口，全量/增量/快照初始化流程编排
│   ├── config.py             # 配置管理（含snapshot/cascade配置）
│   ├── logger.py             # 日志管理
│   ├── scanner.py            # 项目结构扫描
│   ├── file_analyzer.py      # 文件分析（多线程，支持force_overwrite）
│   ├── dir_analyzer.py       # 目录分析（多线程，支持增量模式）
│   ├── project_summarizer.py # 项目总结生成（层级汇总）
│   ├── snapshot.py           # 快照管理（变化检测、受影响目录计算）
│   └── utils.py              # 工具函数（含哈希计算）
├── tests/
│   └── test_project_analyzer.py  # 单元测试
├── pyproject.toml                # 项目配置
├── project_analyzer.spec         # PyInstaller 打包配置
└── README.md
```

## 工作流程详解

### 模式总览

| 模式    | 命令                                                                | 说明                    |
| ----- | ----------------------------------------------------------------- | --------------------- |
| 全量模式  | `python -m src.main <path>`                                       | 分析所有文件，跳过已有结果（支持中断续跑） |
| 增量模式  | `python -m src.main <path> --diff`                                | 基于快照对比，仅分析变化部分，强制覆盖   |
| 快照初始化 | `project-analyzer <path> --diff-init` | 仅生成快照，不执行分析           |

### 全量模式（7 个步骤）

#### 步骤 2：项目结构扫描

```
输入: 项目路径
输出: 目录数、文件数、scan_summary.md
流程:
1. 递归遍历项目目录下所有文件和子目录
2. 排除配置中指定的目录和文件模式
3. 统计目录总数和文件总数
4. 生成结构扫描报告并保存
```

#### 步骤 3：文件分析（多线程）

```
输入: 所有待分析文件列表
输出: ana_{filename}.md（每个文件一个）
流程:
1. 获取所有需要分析的文件（根据排除配置过滤）
2. 创建线程池（默认4个worker，可配置）
3. 为每个文件分配一个工作线程
4. 每个线程：
   a. 检查 ana_{filename}.md 是否已存在 → 跳过（支持中断续跑）
   b. 读取文件内容
   c. 替换提示词模板中的 {content} 占位符
   d. 调用 OpenAI API 进行分析
   e. 保存分析结果到 ana_{filename}.md
```

#### 步骤 4：目录分析（多线程）

```
输入: 项目中所有目录
输出: model_{dirname}.md（每个目录一个）
流程:
1. 获取项目中所有唯一目录（排除配置中的目录）
2. 创建线程池
3. 为每个目录分配一个工作线程
4. 每个线程：
   a. 检查 model_{dirname}.md 是否已存在 → 跳过（支持中断续跑）
   b. 查找目录下所有 ana_*.md 文件
   c. 合并这些文件的内容
   d. 调用 OpenAI API 进行目录级别总结
   e. 保存结果到 model_{dirname}.md
```

#### 步骤 5：项目总结生成（层级汇总）

```
输入: 所有 model_*.md 文件
输出: analyse_report.md
核心算法: 自底向上层级汇总（后序遍历）

流程:
1. 从项目根目录开始递归
2. 对每个目录（后序：子目录先处理）：
   a. 叶子目录：复制 model_*.md → 父目录/tmp_model_*.md
   b. 非叶子非根目录：合并子目录tmp文件 + 自身model_*.md → model_analysis提示词 → LLM → 父目录/tmp_model_*.md
   c. 根目录：合并子目录tmp文件 + 自身model_*.md（如有） → project_summary提示词 → LLM → analyse_report.md
3. 清理所有 tmp_model_* 临时文件（根据 model_analysis_clear 配置）
```

**提示词区分：**

- `model_analysis`：用于非根目录的层级递归汇总（简洁概括）
- `project_summary`：用于根目录最终报告生成（详细全面）

**层级汇总示意图：**

```
项目根目录/
├── src/
│   ├── utils/
│   │   ├── helper.py    → ana_helper.py.md
│   │   └── converter.py → ana_converter.py.md
│   │   └── model_utils.md
│   ├── core/
│   │   └── engine.py    → ana_engine.py.md
│   │   └── model_core.md
│   └── main.py          → ana_main.py.md
│   └── model_src.md
└── tests/
    └── test_main.py     → ana_test_main.py.md
    └── model_tests.md

后序遍历执行顺序：
  1. src/utils/  (叶子) → 复制 model_utils.md  → src/tmp_model_utils.md
  2. src/core/   (叶子) → 复制 model_core.md   → src/tmp_model_core.md
  3. src/        (非叶子) → 合并tmp+model_src.md → LLM → tmp_model_src.md
  4. tests/      (叶子) → 复制 model_tests.md  → tmp_model_tests.md
  5. 根目录       (根)   → 合并tmp文件+model_*.md(如有) → LLM → analyse_report.md
```

#### 步骤 6：保存快照

```
扫描当前项目所有文件，计算文件哈希
保存到 .project_snapshot.json，供 --diff 增量模式使用
```

#### 步骤 7：临时文件清理

```
根据配置决定是否删除：
- 所有 ana_*.md 文件（file_analysis_clear）
- 所有 model_*.md 文件（directory_analysis_clear）
- 所有 tmp_*.md 文件（model_analysis_clear）
注：analyse_report.md、.project_snapshot.json 和日志文件始终保留
```

### 增量模式（--diff）

| 步骤  | 内容     | 与全量模式的区别                                  |
| --- | ------ | ----------------------------------------- |
| 2   | 检测文件变化 | 对比快照哈希，识别新增/修改/删除                         |
| 3   | 增量文件分析 | 仅分析变化文件，`force_overwrite=True`            |
| 4   | 增量目录分析 | 仅分析受影响目录（变化文件祖先目录），`force_overwrite=True` |
| 5   | 更新项目总结 | 逻辑与全量相同（完整后序遍历）                           |
| 6   | 保存快照   | 保存更新后的快照                                  |
| 7   | 清理临时文件 | 同全量模式                                     |

**增量模式关键机制：**

- **快照对比**：`.project_snapshot.json` 记录每个文件的 MD5 哈希，运行时重新计算并对比
- **受影响目录**：变化文件的直接父目录 + 所有祖先目录（向上冒泡到项目根）
- **首次运行自动全量**：无快照时，所有文件标记为"新增"，自动执行全量分析并保存快照
- **删除文件清理**：自动删除已删除文件对应的 `ana_*.md`
- **单步执行支持**：每个步骤可独立运行，自动通过 `_detect_diff_state()` 检测变化

### 快照初始化模式（--diff-init）

```
扫描所有文件并生成快照，不执行任何分析
适用于全量分析完成后补建快照，以便后续使用 --diff 增量模式
```

## 中断续跑机制

全量模式下，步骤 3 和步骤 4 默认 `force_overwrite=False`：

- 已有 `ana_*.md` 的文件 → 跳过，不重新调用 LLM
- 已有 `model_*.md` 的目录 → 跳过，不重新调用 LLM

这意味着如果分析过程中断，重新运行全量模式时，已完成的文件/目录分析不会重复执行，从中断处继续。

增量模式下 `force_overwrite=True`，变化文件的已有分析会被强制覆盖更新。

## 并发模型

```
线程池配置: ThreadPoolExecutor(max_workers=4)

文件分析并发:
  ┌─────────────────────────────────────────┐
  │  ThreadPoolExecutor (max_workers=4)      │
  │                                         │
  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐       │
  │  │ T1  │ │ T2  │ │ T3  │ │ T4  │       │
  │  │file1│ │file2│ │file3│ │file4│       │
  │  └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘       │
  │     └────────┴────────┴────────┘       │
  │              ↓                          │
  │       as_completed()                    │
  └─────────────────────────────────────────┘

目录分析并发: 同上
层级汇总: 串行执行（后序遍历依赖）
```

## 错误处理

| 场景       | 处理方式                 |
| -------- | -------------------- |
| 配置文件不存在  | 输出错误，程序退出            |
| 项目路径无效   | 输出错误，程序退出            |
| API 调用失败 | 记录错误，保存失败标记，继续处理其他文件 |
| 文件读取失败   | 跳过文件，保存失败标记          |
| 汇总失败     | 记录错误，清理临时文件，程序退出     |

## 打包

使用 PyInstaller 打包为可执行文件：

```bash
pip install pyinstaller
pyinstaller project_analyzer.spec
```

产物在 `dist/ProjectAnalyzer/` 目录下。

## 开发

```bash
pip install -e .
pip install -r requirements.txt
pytest
```

## 依赖

- Python >= 3.8
- `openai` - OpenAI API 客户端
- `pyyaml` - YAML 配置文件解析
