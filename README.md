# Titan小说摘要器 / Titan Novel Summarizer

[English Version](#english-version)

## 项目简介

Titan小说摘要器是一个专为中文小说和长文本设计的AI摘要工具，可以快速生成高质量的内容摘要。项目支持使用DeepSeek API（云端服务）或本地Ollama模型进行摘要生成，支持批量处理、多种摘要模式以及文本翻译等功能。

程序采用MVC架构设计，拥有友好的图形界面，适合各类用户使用。无论您是需要快速了解小说内容、整理学习资料，还是处理大量文本数据，Titan小说摘要器都能满足您的需求。

![Titan小说摘要器界面](https://example.com/screenshot.png)

## 主要功能

- **多种摘要模式**：支持生成式摘要（AI生成）、提取式摘要（关键句提取）和混合式摘要
- **批量处理**：支持一次性处理整部小说或多个章节
- **本地模型支持**：可使用本地Ollama服务运行开源大语言模型
- **云API支持**：可使用DeepSeek API（支持离线模拟模式）
- **多种文件格式**：支持TXT等常见文本文件格式
- **文件管理**：内置文件浏览器，便于管理小说文件
- **摘要导出**：支持将摘要结果导出为单独文件
- **自动分章**：智能检测和分割小说章节
- **文本翻译**：支持将文本翻译为其他语言
- **自定义配置**：可调整摘要长度、模型参数等

## 安装指南

### 系统要求

- Python 3.8或更高版本
- Windows/macOS/Linux操作系统
- 若使用本地模型，需要安装[Ollama](https://ollama.ai/)

### 安装步骤

1. 克隆或下载本仓库：
   ```bash
   git clone https://github.com/yourusername/TitanSummarizer.git
   cd TitanSummarizer
   ```

2. 安装依赖包：
   ```bash
   pip install -r requirements.txt
   ```

3. 如需使用本地模型，请安装[Ollama](https://ollama.ai/)并下载您需要的模型。

## 使用方法

### 启动程序

```bash
python titan_app.py
```

### 基本操作流程

1. **选择API类型**：
   - 在菜单中选择`设置` > `API类型`，选择DeepSeek API或Ollama
   - 使用Ollama时，需要在应用中加载本地模型

2. **添加小说文件**：
   - 点击`打开`按钮或菜单中的`文件` > `打开`
   - 选择TXT格式的小说文件
   - 程序会自动识别章节并显示在章节列表中

3. **生成摘要**：
   - 选择一个章节
   - 设置摘要长度
   - 选择摘要模式（生成式/提取式/混合式）
   - 点击`生成摘要`按钮
   - 等待摘要生成完成

4. **批量处理**：
   - 点击`批量摘要`按钮
   - 设置批处理参数
   - 点击确认开始批量生成摘要

5. **导出摘要**：
   - 点击`导出摘要`按钮
   - 选择导出为单个文件或多个文件
   - 选择保存位置

### 使用本地模型

1. 确保Ollama服务已经安装并能正常运行
2. 在应用菜单中选择`模型` > `选择本地模型`
3. 浏览并选择模型文件（支持.gguf、.bin、.ggml格式）
4. 等待模型加载完成
5. 加载完成后，即可使用本地模型生成摘要

## 配置说明

配置文件位于`config/settings.json`，支持以下配置项：

```json
{
  "api_type": "deepseek",        // API类型: deepseek 或 ollama
  "max_length": 200,             // 摘要最大长度
  "temperature": 0.7,            // 生成随机性参数
  "summary_mode": "generative",  // 摘要模式: generative, extractive, mixed
  "models_dir": "D:\\Work\\AI_Models",  // 模型文件存储目录
  "history_limit": 10,           // 历史记录最大条数
  "default_target_language": "English",  // 默认翻译目标语言
  "last_used_model": "",         // 上次使用的模型
  "ui": {
    "theme": "light",            // 界面主题: light 或 dark
    "font_size": 12,             // 字体大小
    "window_size": [800, 600]    // 窗口大小
  }
}
```

## 项目架构

Titan小说摘要器采用MVC架构设计，目录结构如下：

```
TitanSummarizer/
│
├── core/                   # 核心功能模块
│   ├── api/                # API接口模块
│   │   ├── base_api.py     # API基类，定义接口规范
│   │   ├── deepseek_api.py # DeepSeek API实现
│   │   └── ollama_api.py   # Ollama API实现
│   │
│   ├── utils/              # 工具模块
│   │   ├── text_utils.py   # 文本处理工具
│   │   └── config_manager.py # 配置管理工具
│   │
│   └── summarizer.py       # 核心摘要功能实现
│
├── models/                 # 模型相关文件目录
│
├── config/                 # 配置目录
│   └── settings.json       # 配置文件
│
├── titan_ui.py             # UI界面实现
├── titan_app.py            # 应用入口文件
├── requirements.txt        # 依赖包列表
└── README.md               # 使用说明文档
```

## 注意事项

- DeepSeek API需要有效的API密钥才能正常使用。在mock模式下，将使用简单算法模拟API结果。
- 使用本地模型时，确保您的计算机有足够的内存和处理能力。
- 处理超大文件时可能需要较长时间，请耐心等待。
- 首次加载模型可能需要较长时间，这取决于模型大小和您的计算机性能。

## 许可证

本项目采用MIT许可证。

## 致谢

感谢所有开源项目和贡献者，特别是：
- [DeepSeek](https://deepseek.com/) - 提供高质量AI API服务
- [Ollama](https://ollama.ai/) - 简化本地大语言模型部署
- [TKinter](https://docs.python.org/3/library/tkinter.html) - Python标准GUI库

---

# English Version

## Project Introduction

Titan Novel Summarizer is an AI-powered summarization tool designed specifically for Chinese novels and long texts. It quickly generates high-quality content summaries. The project supports using DeepSeek API (cloud service) or local Ollama models for summary generation, and includes batch processing, multiple summarization modes, and text translation features.

The program uses an MVC architecture with a user-friendly graphical interface suitable for all types of users. Whether you need to quickly understand novel content, organize study materials, or process large amounts of text data, Titan Novel Summarizer can meet your needs.

![Titan Novel Summarizer Interface](https://example.com/screenshot.png)

## Key Features

- **Multiple Summarization Modes**: Supports generative summarization (AI-generated), extractive summarization (key sentence extraction), and mixed mode
- **Batch Processing**: Process an entire novel or multiple chapters at once
- **Local Model Support**: Use local Ollama service to run open-source large language models
- **Cloud API Support**: Use DeepSeek API (with offline simulation mode support)
- **Multiple File Formats**: Support for TXT and other common text file formats
- **File Management**: Built-in file browser for convenient novel file management
- **Summary Export**: Export summary results to separate files
- **Automatic Chapter Detection**: Intelligent detection and division of novel chapters
- **Text Translation**: Support for translating text to other languages
- **Custom Configuration**: Adjust summary length, model parameters, and more

## Installation Guide

### System Requirements

- Python 3.8 or higher
- Windows/macOS/Linux operating system
- [Ollama](https://ollama.ai/) installation required for local model usage

### Installation Steps

1. Clone or download this repository:
   ```bash
   git clone https://github.com/yourusername/TitanSummarizer.git
   cd TitanSummarizer
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. If you wish to use local models, install [Ollama](https://ollama.ai/) and download your required models.

## Usage Guide

### Starting the Program

```bash
python titan_app.py
```

### Basic Workflow

1. **Select API Type**:
   - In the menu, select `Settings` > `API Type`, choose DeepSeek API or Ollama
   - When using Ollama, you need to load a local model in the application

2. **Add Novel Files**:
   - Click the `Open` button or select `File` > `Open` in the menu
   - Choose a novel file in TXT format
   - The program will automatically recognize chapters and display them in the chapter list

3. **Generate Summary**:
   - Select a chapter
   - Set the summary length
   - Choose the summary mode (generative/extractive/mixed)
   - Click the `Generate Summary` button
   - Wait for the summary generation to complete

4. **Batch Processing**:
   - Click the `Batch Summary` button
   - Set batch processing parameters
   - Click confirm to start batch summary generation

5. **Export Summaries**:
   - Click the `Export Summary` button
   - Choose to export as a single file or multiple files
   - Select the save location

### Using Local Models

1. Ensure the Ollama service is installed and running properly
2. In the application menu, select `Model` > `Select Local Model`
3. Browse and select the model file (supports .gguf, .bin, .ggml formats)
4. Wait for the model to load
5. Once loaded, you can use the local model to generate summaries

## Configuration

The configuration file is located at `config/settings.json` and supports the following options:

```json
{
  "api_type": "deepseek",        // API type: deepseek or ollama
  "max_length": 200,             // Maximum summary length
  "temperature": 0.7,            // Generation randomness parameter
  "summary_mode": "generative",  // Summary mode: generative, extractive, mixed
  "models_dir": "D:\\Work\\AI_Models",  // Model file storage directory
  "history_limit": 10,           // Maximum number of history records
  "default_target_language": "English",  // Default translation target language
  "last_used_model": "",         // Last used model
  "ui": {
    "theme": "light",            // Interface theme: light or dark
    "font_size": 12,             // Font size
    "window_size": [800, 600]    // Window size
  }
}
```

## Project Architecture

Titan Novel Summarizer uses an MVC architecture with the following directory structure:

```
TitanSummarizer/
│
├── core/                   # Core functionality modules
│   ├── api/                # API interface modules
│   │   ├── base_api.py     # API base class, defining interface standards
│   │   ├── deepseek_api.py # DeepSeek API implementation
│   │   └── ollama_api.py   # Ollama API implementation
│   │
│   ├── utils/              # Utility modules
│   │   ├── text_utils.py   # Text processing tools
│   │   └── config_manager.py # Configuration management tools
│   │
│   └── summarizer.py       # Core summarization functionality
│
├── models/                 # Model-related files directory
│
├── config/                 # Configuration directory
│   └── settings.json       # Configuration file
│
├── titan_ui.py             # UI implementation
├── titan_app.py            # Application entry point
├── requirements.txt        # Dependency list
└── README.md               # Documentation
```

## Notes

- DeepSeek API requires a valid API key for normal use. In mock mode, a simple algorithm will simulate API results.
- When using local models, ensure your computer has sufficient memory and processing power.
- Processing very large files may take a significant amount of time; please be patient.
- Loading a model for the first time may take longer, depending on the model size and your computer's performance.

## License

This project is licensed under the MIT License.

## Acknowledgements

Thanks to all open-source projects and contributors, especially:
- [DeepSeek](https://deepseek.com/) - Providing high-quality AI API services
- [Ollama](https://ollama.ai/) - Simplifying local large language model deployment
- [TKinter](https://docs.python.org/3/library/tkinter.html) - Python's standard GUI library