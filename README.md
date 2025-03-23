# TitanSummarizer - 文本摘要工具

TitanSummarizer是一个功能强大的文本摘要工具，支持多种摘要模式和模型。

## 主要特性

- 支持生成式摘要和提取式摘要
- 支持多种大语言模型：
  - DeepSeek API在线模型
  - Ollama本地GGUF模型
- 图形用户界面和命令行接口
- 批量处理功能
- 自动扫描D:\Work\AI_Models目录下的GGUF模型
- 默认加载小说《凡人修仙传》，方便测试

## 快速开始

### Windows

双击`run.bat`启动图形界面。

### 命令行

```bash
# 运行图形界面
python main.py

# 使用命令行接口处理文本
python main.py --cli --text "要摘要的文本内容" --summary-type extractive

# 使用命令行接口处理文件
python main.py --cli --file path/to/file.txt --output path/to/output.md

# 使用命令行接口处理目录
python main.py --cli --dir path/to/directory --output path/to/output_dir

# 指定使用的模型
python main.py --cli --file path/to/file.txt --model deepseek-api --api-key your_api_key

# 指定本地GGUF模型文件路径
python main.py --cli --file path/to/file.txt --model ollama-local --model-path D:/Work/AI_Models/your_model.gguf
```

## 自定义设置

- 默认摘要长度：200字符
- 默认模型：DeepSeek API
- 模型文件目录：自动扫描`D:\Work\AI_Models`目录下的所有GGUF模型

## 运行测试

运行`run_tests.bat`或使用以下命令执行测试：

```bash
python main.py --mode test
```

## 功能特性

- **多种摘要模式**：支持生成式（AI生成）和提取式（关键句提取）摘要
- **多种模型支持**：
  - DeepSeek API（在线模型，需要API密钥）
  - Ollama本地模型（离线运行，支持多种开源模型）
- **多种输入格式**：支持处理单个文件、整个目录或直接输入文本
- **批量处理**：可一次性处理整个目录中的所有文本文件
- **友好的界面**：提供图形用户界面和命令行界面两种使用方式
- **进度显示**：实时显示处理进度
- **自动保存**：摘要结果可以保存为Markdown或文本文件

## 安装指南

### 环境要求

- Python 3.8+
- 依赖包：详见requirements.txt

### 安装步骤

1. 克隆仓库：

```bash
git clone https://github.com/yourusername/TitanSummarizer.git
cd TitanSummarizer
```

2. 创建并激活虚拟环境（可选）：

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/MacOS
source .venv/bin/activate
```

3. 安装依赖：

```bash
pip install -r requirements.txt
```

## 使用方法

### 图形界面模式

启动图形界面：

```bash
python -m src
```

在图形界面中，您可以：
- 选择要摘要的文件或目录
- 选择模型类型和摘要模式
- 设置摘要长度
- 生成并保存摘要

### 命令行模式

命令行模式适合批处理或集成到其他工作流中：

```bash
# 摘要单个文件
python -m src --cli --file path/to/your/file.txt --output path/to/output.md

# 摘要目录中的所有文件
python -m src --cli --dir path/to/directory --output path/to/output_dir

# 直接摘要文本
python -m src --cli --text "这是要摘要的长文本..." --output path/to/output.md

# 使用特定模型和模式
python -m src --cli --file path/to/file.txt --model deepseek-api --mode generative --max-length 300
```

## 模型配置

### DeepSeek API

使用DeepSeek API需要设置API密钥：
1. 在图形界面中：选择"模型" > "设置API密钥"
2. 在命令行中：使用`--api-key`参数

### Ollama本地模型

使用Ollama本地模型需要安装Ollama：
1. 安装Ollama：[https://ollama.ai/](https://ollama.ai/)
2. 下载你想要使用的模型，例如：`ollama pull qwen:4b`
3. 在应用中选择Ollama本地模型，并选择模型路径

## 项目结构

```
TitanSummarizer/
├── src/                 # 源代码目录
│   ├── api/             # API客户端模块
│   │   ├── deepseek_api.py  # DeepSeek API客户端
│   │   └── ollama_api.py    # Ollama API客户端
│   ├── models/          # 摘要模型模块
│   │   ├── summarizer.py    # 基础摘要器
│   │   ├── deepseek_summarizer.py
│   │   ├── ollama_summarizer.py
│   │   └── factory.py       # 模型工厂
│   ├── utils/           # 工具函数
│   │   ├── file_utils.py    # 文件处理工具
│   │   └── text_utils.py    # 文本处理工具
│   ├── ui/              # 用户界面
│   │   ├── main_ui.py       # 主UI
│   │   └── progress_bar.py  # 进度条组件
│   ├── __main__.py      # 程序入口
│   └── titan_summarizer.py  # 主模块
├── novels/              # 示例小说目录
├── requirements.txt     # 依赖项列表
└── README.md            # 项目说明
```

## 示例用例

- **研究文献摘要**：快速了解学术论文的主要内容
- **小说章节摘要**：为长篇小说生成章节摘要，便于回顾
- **新闻摘要**：从新闻文章中提取关键信息
- **文档摘要**：总结长篇技术文档或报告

## 常见问题

1. **为什么选择生成式摘要？**
   - 生成式摘要使用AI生成更流畅、自然的摘要内容，质量通常更高

2. **为什么选择提取式摘要？**
   - 提取式摘要速度更快，不需要AI模型，适合快速获取关键句子

3. **遇到"模型加载失败"怎么办？**
   - 检查您的网络连接
   - 确认API密钥是否正确
   - 对于本地模型，确认Ollama服务是否正在运行

## 许可协议

此项目使用MIT许可证 - 详情请参见[LICENSE](LICENSE)文件。

## 贡献指南

欢迎贡献代码、报告问题或提出新功能建议。请通过GitHub Issues或Pull Requests参与项目。 