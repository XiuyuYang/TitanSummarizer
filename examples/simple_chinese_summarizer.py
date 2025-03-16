#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简化版中文小说抽取式摘要器
不依赖PyTorch和Transformers，只使用jieba和numpy
"""

import os
import re
import sys
import time
import argparse
import numpy as np
import logging
from typing import List, Dict, Tuple
from datetime import datetime

# 配置日志
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "log")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"summarizer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SimpleChineseSummarizer")

# 尝试导入jieba
try:
    import jieba
    import jieba.analyse
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("未安装jieba分词库，将使用字符级别的分词，可能影响摘要质量")
    logger.warning("建议安装jieba: pip install jieba")

def is_chinese_text(text: str, threshold: float = 0.3) -> bool:
    """判断文本是否为中文"""
    chinese_char_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    return chinese_char_count / len(text) > threshold

def split_chinese_sentences(text: str) -> List[str]:
    """分割中文句子"""
    # 使用正则表达式分割中文句子
    # 按照句号、问号、感叹号、分号等标点符号分割
    pattern = r'[。！？；!?;]+'
    sentences = re.split(pattern, text)
    # 过滤空句子
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences

def get_chinese_stopwords() -> List[str]:
    """获取中文停用词"""
    return [
        "的", "了", "和", "是", "就", "都", "而", "及", "与", "这", "那", "你", "我", "他", "她", "它",
        "们", "个", "上", "下", "在", "有", "人", "我们", "时候", "没有", "什么", "一个", "这个", "那个",
        "不", "也", "很", "但", "还", "又", "只", "要", "不要", "自己", "一", "两", "三", "来", "去",
        "到", "会", "可以", "能", "好", "这样", "那样", "如此", "一些", "一样", "一起", "所以", "因为",
        "因此", "为了", "可是", "但是", "然而", "而且", "并且", "不过", "如果", "的话", "就是", "是否"
    ]

def textrank_summarize(text: str, ratio: float = 0.05, use_textrank: bool = True, max_sentences: int = 10000) -> str:
    """
    使用TextRank算法生成抽取式摘要
    
    Args:
        text: 输入文本
        ratio: 摘要占原文的比例
        use_textrank: 是否使用TextRank算法，否则使用TF-IDF
        max_sentences: 最大处理句子数，超过此数量将分块处理
        
    Returns:
        生成的摘要文本
    """
    # 检查是否为中文文本
    if not is_chinese_text(text):
        logger.warning("输入文本可能不是中文，摘要效果可能不佳")
    
    # 分割句子
    sentences = split_chinese_sentences(text)
    logger.info(f"分割得到 {len(sentences)} 个句子")
    
    # 如果句子数量太少，直接返回原文
    if len(sentences) <= 3:
        logger.warning("句子数量太少，直接返回原文")
        return text
    
    # 计算要选择的句子数量
    num_sentences = max(3, int(len(sentences) * ratio))
    logger.info(f"将选择 {num_sentences} 个句子作为摘要")
    
    # 获取停用词
    stop_words = get_chinese_stopwords()
    
    # 对句子进行分词
    if JIEBA_AVAILABLE:
        processed_sentences = [" ".join(jieba.cut(s)) for s in sentences]
    else:
        # 如果没有安装jieba，则使用字符级别的分词
        processed_sentences = [" ".join(list(s)) for s in sentences]
    
    # 检查是否需要分块处理
    if len(sentences) > max_sentences:
        logger.info(f"句子数量超过{max_sentences}，将进行分块处理")
        return _chunk_summarize(sentences, processed_sentences, num_sentences, stop_words, use_textrank)
    
    if use_textrank:
        # 使用TextRank算法
        logger.info("使用TextRank算法选择重要句子")
        selected_indices = _textrank(processed_sentences, num_sentences, stop_words)
    else:
        # 使用TF-IDF算法
        logger.info("使用TF-IDF算法选择重要句子")
        selected_indices = _tfidf_rank(processed_sentences, num_sentences, stop_words)
    
    # 按原始顺序排序选中的句子
    selected_indices.sort()
    
    # 合并选中的句子
    summary = "\n".join([sentences[i] for i in selected_indices])
    
    return summary

def _chunk_summarize(sentences: List[str], processed_sentences: List[str], 
                    num_sentences: int, stop_words: List[str], use_textrank: bool) -> str:
    """分块处理大文本"""
    chunk_size = 5000  # 每块的句子数
    overlap = 500  # 重叠的句子数
    
    # 计算每块要选择的句子数
    sentences_per_chunk = max(1, int(num_sentences * chunk_size / len(sentences)))
    
    # 分块处理
    chunks = []
    selected_indices_all = []
    
    for i in range(0, len(sentences), chunk_size - overlap):
        chunk_end = min(i + chunk_size, len(sentences))
        chunk_sentences = processed_sentences[i:chunk_end]
        
        logger.info(f"处理第{i//chunk_size+1}块，句子数: {len(chunk_sentences)}")
        
        # 处理当前块
        if use_textrank:
            selected_indices = _textrank(chunk_sentences, sentences_per_chunk, stop_words)
        else:
            selected_indices = _tfidf_rank(chunk_sentences, sentences_per_chunk, stop_words)
        
        # 调整索引
        selected_indices = [idx + i for idx in selected_indices]
        selected_indices_all.extend(selected_indices)
    
    # 去重并排序
    selected_indices_all = sorted(set(selected_indices_all))
    
    # 如果选择的句子数超过目标数，进行截断
    if len(selected_indices_all) > num_sentences:
        logger.info(f"选择的句子数({len(selected_indices_all)})超过目标数({num_sentences})，进行截断")
        # 均匀采样
        step = len(selected_indices_all) / num_sentences
        new_indices = []
        for i in range(num_sentences):
            idx = int(i * step)
            if idx < len(selected_indices_all):
                new_indices.append(selected_indices_all[idx])
        selected_indices_all = sorted(new_indices)
    
    # 合并选中的句子
    summary = "\n".join([sentences[i] for i in selected_indices_all])
    
    return summary

def _tfidf_rank(sentences: List[str], num_sentences: int, stop_words: List[str]) -> List[int]:
    """使用TF-IDF算法选择重要句子"""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        logger.error("未安装scikit-learn，请使用pip install scikit-learn安装")
        sys.exit(1)
    
    # 创建TF-IDF向量化器
    vectorizer = TfidfVectorizer(stop_words=stop_words)
    
    # 转换句子为TF-IDF特征
    tfidf_matrix = vectorizer.fit_transform(sentences)
    
    # 计算每个句子的得分（TF-IDF值之和）
    sentence_scores = np.array([tfidf_matrix[i].sum() for i in range(len(sentences))])
    
    # 选择得分最高的句子
    top_indices = sentence_scores.argsort()[-num_sentences:][::-1]
    
    return list(top_indices)

def _textrank(sentences: List[str], num_sentences: int, stop_words: List[str]) -> List[int]:
    """使用TextRank算法选择重要句子"""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        logger.error("未安装scikit-learn，请使用pip install scikit-learn安装")
        sys.exit(1)
    
    # 创建TF-IDF向量化器
    vectorizer = TfidfVectorizer(stop_words=stop_words)
    
    # 转换句子为TF-IDF特征
    tfidf_matrix = vectorizer.fit_transform(sentences)
    
    # 计算句子之间的相似度矩阵
    similarity_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix)
    
    # 将相似度矩阵转换为图的邻接矩阵
    np.fill_diagonal(similarity_matrix, 0)  # 将对角线设为0，避免自环
    
    # 归一化邻接矩阵
    row_sums = similarity_matrix.sum(axis=1, keepdims=True)
    # 避免除以0
    row_sums[row_sums == 0] = 1
    transition_matrix = similarity_matrix / row_sums
    
    # 初始化TextRank得分
    scores = np.ones(len(sentences)) / len(sentences)
    
    # 迭代计算TextRank得分
    damping = 0.85  # 阻尼系数
    epsilon = 1e-6  # 收敛阈值
    max_iter = 100  # 最大迭代次数
    
    for i in range(max_iter):
        prev_scores = scores.copy()
        scores = (1 - damping) + damping * (transition_matrix.T @ scores)
        
        # 检查是否收敛
        if np.abs(scores - prev_scores).sum() < epsilon:
            logger.info(f"TextRank算法在第{i+1}次迭代后收敛")
            break
    
    # 选择得分最高的句子
    top_indices = scores.argsort()[-num_sentences:][::-1]
    
    return list(top_indices)

def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """提取文本关键词"""
    if JIEBA_AVAILABLE:
        return jieba.analyse.extract_tags(text, topK=top_n)
    else:
        # 如果没有安装jieba，则使用简单的词频统计
        # 中文停用词
        stop_words = get_chinese_stopwords()
        
        # 按字符分割
        chars = list(text)
        
        # 去除停用词和标点符号
        filtered_chars = [char for char in chars if char.strip() and char not in stop_words and not re.match(r'[^\w\u4e00-\u9fff]', char)]
        
        # 计算字符频率
        from collections import Counter
        char_freq = Counter(filtered_chars)
        
        # 返回频率最高的top_n个字符
        return [char for char, _ in char_freq.most_common(top_n)]

def read_file(file_path: str) -> str:
    """读取文件内容，自动处理编码"""
    encodings = ['utf-8', 'gbk', 'gb18030']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
                logger.info(f"成功使用{encoding}编码读取文件")
                return content
        except UnicodeDecodeError:
            continue
    
    logger.error(f"无法读取文件{file_path}，请检查文件编码")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='简化版中文小说抽取式摘要器')
    parser.add_argument('--file_path', type=str, required=True, help='小说文件路径')
    parser.add_argument('--ratio', type=float, default=0.05, help='摘要占原文的比例')
    parser.add_argument('--algorithm', type=str, default="textrank", choices=["textrank", "tfidf"], help='摘要算法')
    parser.add_argument('--output_path', type=str, help='输出文件路径，默认为原文件名_summary.txt')
    
    args = parser.parse_args()
    
    # 记录参数
    logger.info(f"参数: file_path={args.file_path}, ratio={args.ratio}, algorithm={args.algorithm}")
    
    # 读取小说内容
    logger.info(f"正在读取小说文件: {args.file_path}")
    content = read_file(args.file_path)
    logger.info(f"小说总长度: {len(content)} 字符")
    
    # 提取关键词
    logger.info("提取关键词...")
    keywords = extract_keywords(content, top_n=20)
    logger.info(f"关键词: {', '.join(keywords)}")
    
    # 生成摘要
    logger.info(f"使用 {args.algorithm} 算法生成摘要，比例: {args.ratio}...")
    start_time = time.time()
    
    summary = textrank_summarize(
        content, 
        ratio=args.ratio, 
        use_textrank=(args.algorithm == "textrank")
    )
    
    elapsed_time = time.time() - start_time
    
    logger.info(f"摘要生成完成!")
    logger.info(f"摘要长度: {len(summary)} 字符")
    logger.info(f"压缩比: {len(summary) / len(content):.2%}")
    logger.info(f"耗时: {elapsed_time:.2f} 秒")
    logger.info(f"处理速度: {len(content) / elapsed_time:.2f} 字符/秒")
    
    # 保存摘要
    if args.output_path:
        output_path = args.output_path
    else:
        output_path = os.path.join(os.path.dirname(args.file_path), 
                                  f"{os.path.basename(args.file_path)}_summary_{args.algorithm}.txt")
    
    with open(output_path, 'w', encoding='utf-8-sig') as f:
        f.write(summary)
    
    logger.info(f"摘要已保存到: {output_path}")
    
    # 打印摘要预览
    preview_length = min(500, len(summary))
    logger.info(f"摘要预览: {summary[:preview_length]}...")

if __name__ == "__main__":
    main() 