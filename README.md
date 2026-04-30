# ProjectAnalyzer

一个跨平台命令行工具，用于分析软件项目并生成项目总结文档。

## 功能特性

- 分析软件项目结构
- 调用大模型（OpenAI GPT）进行深度分析
- 多线程并发处理
- 生成 Markdown 格式的项目总结报告
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
    请分析以下目录的组件总结：
    {content}
    要求：
    1. 根据功能描述与引用关系，对目录下的项目组件进行总结，简述其核心逻辑，不超过1000字
    2. 列出该目录对外暴露的接口或外部调用（如果有）
    3. 列出该目录的外部引用（如果有）

  project_summary: |
    根据以下功能描述与引用关系，请对整个项目进行总结：
    {content}
    要求：
    简述其核心功能、流程逻辑

# 清理配置
cleanup:
  file_analysis_clear: false        # 是否删除文件分析结果 (ana_*.md)
  directory_analysis_clear: true    # 是否删除目录分析结果 (model_*.md)

# 排除配置，注意claude写的代码很傻，只能匹配一个通配符，然后头尾分别匹配，多通配符是实现不了的
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
```

## 使用方法

```bash
project-analyzer /path/to/project
project-analyzer /path/to/project --config /path/to/config.yaml
```

### 单步执行

可以使用 `--step` 参数只执行特定步骤：

```bash
project-analyzer /path/to/project --step 2  # 仅扫描项目结构
project-analyzer /path/to/project --step 3  # 仅执行文件分析
project-analyzer /path/to/project --step 4  # 仅执行目录分析
project-analyzer /path/to/project --step 5  # 仅生成项目总结
project-analyzer /path/to/project --step 6  # 仅清理临时文件
```

## 输出文件

| 文件 | 内容 | 位置 |
|------|------|------|
| `{项目名}_scan_summary.md` | 项目结构扫描总结（步骤2） | 项目根目录 |
| `ana_{filename}.md` | 单个文件分析结果（步骤3） | 与源文件同目录 |
| `model_{dirname}.md` | 目录分析结果（步骤4） | 对应目录下 |
| `tmp_model_{dirname}.md` | 临时汇总文件（步骤5层级汇总） | 对应目录下 |
| `analyse_report.md` | 最终项目总结报告（步骤5） | 项目根目录 |
| `{项目名}.log` | 详细运行日志 | 项目根目录 |

## 项目架构

```
project-analyzer/
├── src/
│   └── project_analyzer/
│       ├── __init__.py           # 包初始化，版本定义
│       ├── main.py               # CLI入口，流程编排
│       ├── config.py             # 配置管理
│       ├── logger.py             # 日志管理
│       ├── scanner.py            # 项目结构扫描
│       ├── file_analyzer.py      # 文件分析（多线程）
│       ├── dir_analyzer.py       # 目录分析（多线程）
│       ├── project_summarizer.py # 项目总结生成
│       └── utils.py              # 工具函数
├── tests/
│   └── test_project_analyzer.py  # 单元测试
├── pyproject.toml                 # 项目配置
└── README.md
```

## 工作流程详解

项目分析分为 **6 个步骤**，按顺序执行：

### 步骤 2：项目结构扫描

```
输入: 项目路径
输出: 目录数、文件数、scan_summary.md

流程:
1. 递归遍历项目目录下所有文件和子目录
2. 排除 .git, __pycache__, node_modules 等目录
3. 统计目录总数和文件总数
4. 生成结构扫描报告并保存
```

### 步骤 3：文件分析（多线程）

```
输入: 所有待分析文件列表
输出: ana_{filename}.md（每个文件一个）

流程:
1. 获取所有需要分析的文件（根据排除配置过滤）
2. 创建线程池（默认4个worker，可配置）
3. 为每个文件分配一个工作线程
4. 每个线程：
   a. 读取文件内容
   b. 替换提示词模板中的 {content} 占位符
   c. 调用 OpenAI API 进行分析
   d. 保存分析结果到 ana_{filename}.md
5. 批量更新进度显示
```

**文件分析提示词模板变量：**
- `{content}` - 文件的完整内容

**文件分析输出格式：**
- 文件功能一句话总结（不超过200字）
- 文件对外暴露的接口或外部调用列表

### 步骤 4：目录分析（多线程）

```
输入: 项目中所有目录
输出: model_{dirname}.md（每个目录一个）

流程:
1. 获取项目中所有唯一目录
2. 创建线程池
3. 为每个目录分配一个工作线程
4. 每个线程：
   a. 查找目录下所有 ana_*.md 文件
   b. 合并这些文件的内容
   c. 调用 OpenAI API 进行目录级别总结
   d. 保存结果到 model_{dirname}.md
5. 批量更新进度显示
```

**目录分析提示词模板变量：**
- `{content}` - 该目录下所有 ana_*.md 文件的合并内容

**目录分析输出格式：**
- 目录组件总结（不超过500字）
- 目录对外暴露的接口或调用列表

### 步骤 5：项目总结生成（层级汇总）

```
输入: 所有 model_*.md 文件
输出: analyse_report.md

核心算法: 自底向上层级汇总

流程（后序遍历）:
1. 从项目根目录开始递归
2. 对每个目录：
   a. 先递归处理所有子目录（确保子目录先完成）
   b. 如果是叶子目录：直接复制 model_*.md 到父目录的 tmp_model_*.md
   c. 如果是非叶子目录：等待所有子目录处理完成后，合并子目录的 tmp_model_* 和自身的 model_*，调用 LLM 生成新的总结，保存到父目录的 tmp_model_*.md
3. 根目录汇总完成后，生成最终 analyse_report.md
4. 清理所有 tmp_model_* 临时文件
```

**层级汇总示意图：**

```
项目根目录/
├── src/
│   ├── main.py        → ana_main.py
│   └── utils.py       → ana_utils.py
│   → model_src.md (由 ana_main.py + ana_utils.py 生成)
├── tests/
│   └── test_main.py  → ana_test_main.py
│   → model_tests.md (由 ana_test_main.py 生成)
│
→ 自底向上汇总：
  1. src/ 的 model_src.md → tmp_model_src.md
  2. tests/ 的 model_tests.md → tmp_model_tests.md
  3. 根目录：合并 tmp_model_src.md + tmp_model_tests.md → analyse_report.md
```

### 步骤 6：临时文件清理

```
清理对象:
- 所有 ana_*.md 文件
- 所有 model_*.md 文件
- 所有 tmp_model_*.md 文件

注：最终报告 analyse_report.md 和日志文件会被保留
```

## 核心模块设计

### Config（配置管理）

```python
class Config:
    # 加载 YAML 配置文件
    # 提供 get(key) 方法支持点号路径访问
    # 属性：model_config, threading_config, prompts_config, exclude_config
```

### Logger（日志管理）

```python
class Logger:
    # 双输出：文件（DEBUG级别）+ 控制台（INFO级别）
    # 日志格式：时间戳 - 级别 - 消息
    # 方法：info(), debug(), error(), fatal()
```

### FileAnalyzer（文件分析）

```python
class FileAnalyzer:
    # 多线程并发分析
    # 每次分析创建独立的 OpenAI 客户端
    # 支持跳过已存在的分析结果
    # 方法：analyze_files(), _analyze_single_file()
```

### DirectoryAnalyzer（目录分析）

```python
class DirectoryAnalyzer:
    # 多线程并发分析
    # 读取目录下所有 ana_*.md 文件进行汇总
    # 使用后序遍历确保依赖顺序
```

### ProjectSummarizer（项目总结）

```python
class ProjectSummarizer:
    # 自底向上层级汇总
    # 处理临时文件和最终报告生成
    # 方法：summarize(), _process_directory()
```

## 并发模型

```
线程池配置: ThreadPoolExecutor(max_workers=4)

文件分析并发:
  ┌─────────────────────────────────────────┐
  │  ThreadPoolExecutor (max_workers=4)    │
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

| 场景 | 处理方式 |
|------|----------|
| 配置文件不存在 | 输出错误，程序退出 |
| 项目路径无效 | 输出错误，程序退出 |
| API 调用失败 | 记录错误，保存失败标记，继续处理其他文件 |
| 文件读取失败 | 跳过文件，保存失败标记 |
| 汇总失败 | 记录错误，清理临时文件，程序退出 |

## 开发

```bash
git clone <repo>
cd project-analyzer
pip install -e .
pip install -r requirements-dev.txt
pytest
```

## 依赖

- Python >= 3.8
- `openai` - OpenAI API 客户端
- `pyyaml` - YAML 配置文件解析