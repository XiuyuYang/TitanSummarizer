# TitanSummarizer - 基于Transformer的小说摘要生成器

TitanSummarizer是一个强大的中文小说摘要生成工具，使用最先进的Transformer深度学习模型自动生成高质量摘要。

## 功能特点

- **基于Transformer的摘要生成**：使用预训练的BART、T5等模型生成高质量摘要
- **章节自动检测**：智能识别小说章节，支持多种章节标记格式
- **两种摘要模式**：支持按章节摘要和全文摘要
- **GPU加速**：支持CUDA加速，大幅提高处理速度
- **友好的图形界面**：简洁直观的用户界面，易于操作
- **详细的处理日志**：实时显示处理进度和结果
- **自动保存结果**：自动保存摘要和详细信息

## 安装

### 环境要求

- Python 3.7+
- PyTorch 1.7+
- Transformers 4.0+
- PyQt5

### 安装步骤

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/TitanSummarizer.git
cd TitanSummarizer
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

### 图形界面

启动图形界面：

```bash
python transformer_ui.py
```

界面操作：
1. 点击"浏览..."选择小说文件
2. 选择预训练模型
3. 设置摘要长度
4. 选择摘要模式（按章节或全文）
5. 选择计算设备（CPU或GPU）
6. 点击"开始生成摘要"

### 命令行使用

也可以通过命令行直接使用：

```bash
python transformer_summarizer.py --file_path 小说文件路径 --model bart-base-chinese --by_chapter --max_summary_length 150
```

参数说明：
- `--file_path`：小说文件路径（必需）
- `--model`：预训练模型，可选值：bart-base-chinese, mt5-small-chinese, cpt-base
- `--by_chapter`：按章节生成摘要（默认为全文摘要）
- `--max_summary_length`：摘要最大长度（默认150）
- `--output_path`：输出文件路径（可选）
- `--device`：计算设备，可选值：cpu, cuda

## 支持的模型

目前支持以下预训练模型：

- **bart-base-chinese**：中文BART模型，适合一般中文小说
- **mt5-small-chinese**：多语言T5模型，支持中文
- **cpt-base**：中文预训练Transformer模型

## 输出文件

程序会在小说文件所在目录下创建`summaries`文件夹，并生成以下文件：

- `小说名_transformer_summary.txt`：生成的摘要文本
- `小说名_transformer_summary_detail.json`：详细的摘要信息，包括每章节的原文长度、摘要长度、压缩比等

## 示例

以《凡人修仙传》为例：

```bash
python transformer_summarizer.py --file_path novels/凡人修仙传_完整版.txt --model bart-base-chinese --by_chapter
```

## 常见问题

**Q: 程序运行很慢怎么办？**  
A: 建议使用GPU加速。如果没有GPU，可以选择较小的模型如mt5-small-chinese，或减少摘要长度。

**Q: 如何提高摘要质量？**  
A: 可以尝试不同的预训练模型，或调整摘要长度参数。

**Q: 支持哪些文件格式？**  
A: 目前主要支持txt文本文件，程序会自动检测文件编码。

## 许可证

MIT License 