# Titan小说摘要器

一个强大的小说章节摘要工具，支持生成式和提取式摘要，自动保存和加载摘要数据。

## 功能特点

- **多种摘要模式**：
  - 生成式摘要：使用AI模型生成高质量摘要
  - 提取式摘要：快速从原文提取关键句子作为摘要，无需模型
  
- **多种AI模型支持**：
  - DeepSeek API支持（在线API）
  - Ollama本地模型支持
  - 支持自定义本地GGUF模型
  
- **摘要管理**：
  - 自动保存摘要到JSON文件（以小说名_sum.json命名）
  - 读取时优先从内存读取，内存中没有则从JSON文件加载
  - 支持导出摘要到单独文件
  
- **小说处理**：
  - 自动检测和分割章节
  - 支持单文件小说和目录结构小说
  - 自动处理不同编码的文本文件
  
- **用户友好界面**：
  - 章节列表显示
  - 进度指示
  - 错误处理和日志
  - 设置保存与加载

## 安装和使用

### 系统要求

- Python 3.8+
- tkinter (Python GUI库)
- 推荐Windows 10/11，也支持Linux和macOS

### 安装步骤

1. 克隆或下载本仓库
2. 安装依赖：
   ```
   pip install -r requirements.txt
   ```
3. 如果需要使用本地AI模型，请安装Ollama：
   - 从[Ollama官网](https://ollama.ai/download)下载并安装

### 运行方法

启动程序：
```
python titan_ui.py
```

### 使用流程

1. **加载小说**：
   - 点击"文件"→"打开文件"或"浏览小说"选择小说文件

2. **选择摘要模式**：
   - 生成式摘要：需要加载AI模型
   - 提取式摘要：无需模型，速度快

3. **生成摘要**：
   - 在左侧章节列表中选择需要摘要的章节
   - 设置摘要长度
   - 点击"生成摘要"按钮

4. **导出摘要**：
   - 摘要会自动保存到`<小说名>_sum.json`文件
   - 可通过"文件"→"导出摘要到单个文件"导出到其他位置

## 项目结构

### 文件结构

- `titan_ui.py`：主程序和用户界面
- `titan_summarizer.py`：摘要生成核心逻辑
- `ollama_api.py`：Ollama本地模型API接口
- `deepseek_api.py`：DeepSeek云API接口 
- `novels/`：存放小说文件的目录
- `settings.json`：保存用户设置

### 模块说明

#### titan_ui.py

主程序和用户界面，包含以下主要功能：
- `TitanUI`类：主界面类，管理整个应用程序的UI和逻辑
- 文件操作：打开、加载小说文件
- 章节处理：检测和显示章节列表
- 摘要生成：处理摘要请求，调用摘要引擎
- 摘要管理：保存、加载和导出摘要
- 设置管理：保存和加载用户设置

#### titan_summarizer.py

摘要生成引擎，包含以下主要功能：
- `TitanSummarizer`类：摘要生成核心类
- 模型管理：加载和管理AI模型
- 摘要生成：处理生成式和提取式摘要请求
- API封装：封装DeepSeek和Ollama API的调用

#### ollama_api.py

Ollama本地模型API封装，提供以下功能：
- 查找和列出本地模型
- 加载模型
- 处理生成请求
- 管理模型状态

#### deepseek_api.py

DeepSeek云端API封装，提供以下功能：
- API认证和调用
- 错误处理
- 模拟模式支持

## 技术实现

### 摘要生成

- **提取式摘要**：使用文本排名算法（类似TextRank）提取关键句子
- **生成式摘要**：使用AI大模型生成摘要，支持DeepSeek-API和Ollama本地模型

### 章节检测

使用正则表达式和启发式算法自动检测小说章节

### 数据存储

- 摘要数据使用JSON格式保存
- 支持批量导出和单文件导出

## 最近优化

### 2024-03-23代码优化
1. **移除未使用文件**：删除了`get_model_name.py`，将其功能集成到`titan_summarizer.py`中
2. **简化导入结构**：优化了导入结构，移除了未使用的模块引用
3. **精简依赖管理**：更新`requirements.txt`，只保留实际使用的依赖
4. **文档更新**：
   - 添加了详细的模块说明
   - 更新了技术实现描述
   - 添加了更新日志
5. **代码可读性**：
   - 添加了更多的注释和文档字符串
   - 统一了命名规范和格式

## 许可证

MIT

## 贡献者

- 欢迎提交Pull Request或Issue 

## 更新日志

### v1.0.0 (2023-12-01)
- 初始版本发布

### v1.1.0 (2024-01-15)
- 添加提取式摘要功能
- 优化UI交互

### v1.2.0 (2024-03-22)
- 改进摘要存储方式为JSON格式
- 优化代码结构
- 修复已知bug 