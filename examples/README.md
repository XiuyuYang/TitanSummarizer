# TitanSummarizer 中文小说摘要工具

本目录包含了用于处理中文小说的简化版摘要器和相关测试文件。

## 文件说明

- `fanren_sample.txt` - 《凡人修仙传》小说样本
- `simple_chinese_summarizer.py` - 简化版中文小说摘要器
- `chinese_novel_test.py` - 中文小说测试脚本
- `test_fanren.py` - 《凡人修仙传》测试脚本
- `test_fanren_complete.py` - 《凡人修仙传》完整版测试脚本
- `auto_summarize.py` - 自动摘要生成脚本
- `batch_summarize.py` - 批量摘要生成脚本
- `config.json` - 自动摘要生成器配置文件

## 简化版中文小说摘要器

`simple_chinese_summarizer.py` 是一个轻量级的中文小说摘要工具，主要依赖 `numpy`、`scikit-learn` 和 `jieba` 库，无需依赖大型库如 PyTorch。

### 特点

- 支持 TextRank 和 TF-IDF 两种摘要算法
- 自动提取关键词
- 可自定义摘要比例
- 自动处理各种文件编码
- 针对中文文本优化的句子分割

### 使用方法

使用 TextRank 算法生成摘要：

```bash
python simple_chinese_summarizer.py --file_path novels/fanren_sample.txt --ratio 0.3
```

使用 TF-IDF 算法生成摘要：

```bash
python simple_chinese_summarizer.py --file_path novels/fanren_sample.txt --ratio 0.3 --algorithm tfidf
```

指定输出文件：

```bash
python simple_chinese_summarizer.py --file_path novels/fanren_sample.txt --ratio 0.3 --output_path my_summary.txt
```

### 参数说明

- `--file_path`：小说文件路径（必需）
- `--ratio`：摘要比例，默认为 0.05
- `--algorithm`：摘要算法，可选 "textrank" 或 "tfidf"，默认为 "textrank"
- `--output_path`：输出文件路径（可选）

## 自动摘要功能

`auto_summarize.py` 是一个功能强大的自动摘要生成脚本，支持按章节处理长篇小说。

### 特点

- 支持按章节自动分割和摘要
- 自动提取和保存关键词
- 根据文件大小自动调整摘要比例
- 生成详细的摘要报告
- 通过配置文件控制所有参数

### 使用方法

```bash
# 使用默认配置文件运行
python auto_summarize.py

# 指定配置文件
python auto_summarize.py --config my_config.json
```

### 配置文件说明

`config.json` 包含以下配置项：

```json
{
    "novels_dir": "novels",           // 小说目录
    "output_dir": "summaries",        // 输出目录
    "algorithms": ["textrank"],       // 使用的算法
    "default_ratio": 0.01,            // 默认摘要比例
    "auto_ratio": true,               // 是否自动调整比例
    "by_chapter": true,               // 是否按章节处理
    "chapter_pattern": "第[一二三四五六七八九十百千万0-9１２３４５６７８９０]+[章回节]", // 章节匹配模式
    "save_keywords": true,            // 是否保存关键词
    "generate_report": true           // 是否生成报告
}
```

### 输出示例

摘要输出目录包含：
- 小说摘要文件（`小说名_summary_算法.txt`）
- 关键词文件（`小说名_keywords.txt`）
- 摘要报告（`auto_summarize_report_日期时间.txt`）

## 批量摘要功能

`batch_summarize.py` 支持批量处理多个小说文件，适合大规模摘要生成。

### 使用方法

```bash
# 处理指定目录下的所有小说
python batch_summarize.py --input_dir novels --output_dir summaries
```

## 完整版摘要器

`chinese_novel_test.py` 是完整版摘要器，支持多种摘要策略，但需要 PyTorch。

## 测试不同策略

`test_fanren.py` 脚本可用于测试不同摘要策略在《凡人修仙传》样本上的效果。

## 处理完整版《凡人修仙传》

`test_fanren_complete.py` 脚本专门用于处理完整版《凡人修仙传》，支持分块处理大型文本。

### 使用方法

使用 TextRank 算法处理完整版小说：

```bash
python test_fanren_complete.py --ratio 0.005 --algorithm textrank --chunk_size 200000
```

使用 TF-IDF 算法处理完整版小说：

```bash
python test_fanren_complete.py --ratio 0.005 --algorithm tfidf --chunk_size 200000
```

### 参数说明

- `--file_path`：小说文件路径，默认为 `novels/凡人修仙传_完整版.txt`
- `--output_dir`：输出目录，默认为 `summaries`
- `--ratio`：摘要比例，默认为 0.01
- `--algorithm`：摘要算法，可选 "textrank" 或 "tfidf"，默认为 "textrank"
- `--chunk_size`：分块大小（字符数），默认为 100000
- `--max_sentences`：每块最大句子数，默认为 5000

## 示例结果

TextRank 算法生成的摘要示例（《凡人修仙传》）：

```
冷冷的师兄冷哼了一声，似乎心里也有些顾忌，便不再言语了，韩立这时才知道这位冷冷的师兄叫张均
走出墨大夫的屋子，韩立不禁轻轻的松了一口气，刚才在屋里不知为什么，自己连大气也不敢喘一下，脑袋也绷得紧紧的，现在出来后马上就轻松起来，自己也恢复了正常
很奇怪，不知为什么武功很高的墨大夫无法察知韩立修炼的详细情况，只能从给他把脉中，得知他进度的一二，所以这些日子里一直不知道韩立所面临的困境
``` 