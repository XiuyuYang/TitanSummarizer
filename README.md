# TitanSummarizer - 大文本摘要系统

这是一个基于TextRank和TF-IDF算法的大文本摘要系统，专为中文小说等长文本设计，支持分块处理超长文本。

## 功能特点

- 支持超长文本的摘要生成（通过分块处理）
- 提供TextRank和TF-IDF两种抽取式摘要算法
- 支持单文件处理和批量处理模式
- 自动提取文本关键词
- 自动处理中文文本分割和分词
- 支持多种文件编码（UTF-8、GBK、GB18030）
- 完整的日志记录功能

## 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/TitanSummarizer.git
cd TitanSummarizer

# 安装依赖
pip install -r requirements.txt
```

## 使用方法

### 单文件处理

```bash
# 使用TextRank算法（默认）
python titan_summarizer.py --file_path path/to/novel.txt --ratio 0.05

# 使用TF-IDF算法
python titan_summarizer.py --file_path path/to/novel.txt --ratio 0.05 --algorithm tfidf
```

### 批量处理

```bash
# 批量处理目录下的所有txt文件
python titan_summarizer.py --batch --input_dir path/to/novels --output_dir path/to/summaries --ratio 0.05

# 指定文件匹配模式
python titan_summarizer.py --batch --input_dir path/to/novels --output_dir path/to/summaries --file_pattern "novel_*.txt"
```

## 参数说明

- `--file_path` - 小说文件路径（单文件处理模式）
- `--input_dir` - 输入目录（批量处理模式）
- `--output_dir` - 输出目录（批量处理模式）
- `--ratio` - 摘要占原文的比例，默认为0.05（5%）
- `--algorithm` - 摘要算法，可选 "textrank" 或 "tfidf"，默认为 "textrank"
- `--batch` - 批量处理模式
- `--file_pattern` - 文件匹配模式，默认为 "*.txt"（批量处理模式）

## 项目结构

- `titan_summarizer.py` - 主程序
- `examples/` - 示例和工具
  - `simple_chinese_summarizer.py` - 简化版中文小说摘要器
  - `batch_summarize.py` - 批量处理脚本
  - `fanren_sample.txt` - 《凡人修仙传》样本
- `log/` - 日志文件目录

## 日志功能

系统会自动在`log`目录下生成日志文件，记录处理过程中的各种信息，包括：

- 参数设置
- 文件读取信息
- 关键词提取结果
- 摘要生成过程
- 性能统计（处理时间、压缩比等）

## 示例

使用TextRank算法对《凡人修仙传》样本进行摘要（比例5%）：

```bash
python titan_summarizer.py --file_path examples/fanren_sample.txt --ratio 0.05
```

批量处理多个小说文件：

```bash
python titan_summarizer.py --batch --input_dir examples/novels --output_dir examples/summaries --ratio 0.05
``` 