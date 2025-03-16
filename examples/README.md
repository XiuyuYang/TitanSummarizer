# 简化版中文小说摘要器

本目录包含了用于处理中文小说的简化版摘要器和相关测试文件。

## 文件说明

- `fanren_sample.txt` - 《凡人修仙传》小说样本
- `simple_chinese_summarizer.py` - 简化版中文小说摘要器
- `chinese_novel_test.py` - 中文小说测试脚本
- `test_fanren.py` - 《凡人修仙传》测试脚本
- `test_fanren_complete.py` - 《凡人修仙传》完整版测试脚本
- `auto_summarize.py` - 自动摘要生成脚本
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

## 自动摘要生成器

`auto_summarize.py` 是一个自动化摘要生成工具，无需每次都通过命令行控制参数，可以自动处理多个文件并选择合适的算法和参数。

### 特点

- 自动批量处理多个文件
- 根据文件大小自动调整摘要比例
- 支持同时使用多种算法并比较结果
- 自动生成详细的摘要报告
- 支持通过配置文件自定义处理参数

### 使用方法

基本用法（使用默认配置）：

```bash
python auto_summarize.py
```

使用配置文件：

```bash
python auto_summarize.py --config config.json
```

保存默认配置到文件：

```bash
python auto_summarize.py --save-config my_config.json
```

指定小说目录和输出目录：

```bash
python auto_summarize.py --novels-dir my_novels --output-dir my_summaries
```

只使用特定算法：

```bash
python auto_summarize.py --algorithm textrank
```

使用两种算法并比较：

```bash
python auto_summarize.py --algorithm both
```

指定固定摘要比例（禁用自动比例）：

```bash
python auto_summarize.py --ratio 0.01 --no-auto-ratio
```

### 配置文件说明

配置文件使用 JSON 格式，包含以下字段：

```json
{
    "novels_dir": "novels",             // 小说目录
    "output_dir": "summaries",          // 输出目录
    "algorithms": ["textrank", "tfidf"], // 使用的算法
    "default_ratio": 0.01,              // 默认摘要比例
    "large_file_threshold": 1000000,    // 大文件阈值（字节）
    "chunk_size": 200000,               // 分块大小（字符）
    "max_sentences": 5000,              // 每块最大句子数
    "file_patterns": ["*.txt"],         // 文件匹配模式
    "auto_ratio": true,                 // 是否自动调整比例
    "compare_algorithms": true,         // 是否比较算法
    "save_keywords": true,              // 是否保存关键词
    "generate_report": true             // 是否生成报告
}
```

### 性能比较

在处理完整版《凡人修仙传》（约 6.5MB 文本）时：

- TextRank 算法：
  - 处理时间：约 105 秒
  - 压缩比：0.50%
  - 摘要大小：约 32KB
  - 处理速度：约 62,679 字符/秒

- TF-IDF 算法：
  - 处理时间：约 59 秒
  - 压缩比：1.43%
  - 摘要大小：约 94KB
  - 处理速度：约 110,838 字符/秒

TF-IDF 算法处理速度更快，但生成的摘要更长；TextRank 算法生成的摘要更简洁，但处理时间更长。

## 示例结果

TextRank 算法生成的摘要示例（《凡人修仙传》）：

```
冷冷的师兄冷哼了一声，似乎心里也有些顾忌，便不再言语了，韩立这时才知道这位冷冷的师兄叫张均
走出墨大夫的屋子，韩立不禁轻轻的松了一口气，刚才在屋里不知为什么，自己连大气也不敢喘一下，脑袋也绷得紧紧的，现在出来后马上就轻松起来，自己也恢复了正常
很奇怪，不知为什么武功很高的墨大夫无法察知韩立修炼的详细情况，只能从给他把脉中，得知他进度的一二，所以这些日子里一直不知道韩立所面临的困境
``` 