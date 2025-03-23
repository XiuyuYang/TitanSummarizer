#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文本处理工具模块
提供文本分析、清理和转换的实用函数
"""

import re
import logging
import nltk
from typing import List, Dict, Tuple, Optional, Any, Set
import numpy as np

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 确保nltk数据已下载
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    try:
        logger.info("下载NLTK punkt模型...")
        nltk.download('punkt', quiet=True)
    except Exception as e:
        logger.warning(f"无法下载NLTK资源: {e}")

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    try:
        logger.info("下载NLTK stopwords模型...")
        nltk.download('stopwords', quiet=True)
    except Exception as e:
        logger.warning(f"无法下载NLTK资源: {e}")

# 加载停用词
try:
    from nltk.corpus import stopwords
    STOPWORDS = set(stopwords.words('english'))
except Exception:
    logger.warning("无法加载NLTK停用词，使用简化版本")
    STOPWORDS = set([
        'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours',
        'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers',
        'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves',
        'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are',
        'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does',
        'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until',
        'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into',
        'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down',
        'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here',
        'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
        'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
        'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now'
    ])

# 中文停用词 - 简单版本
CHINESE_STOPWORDS = set([
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', 
    '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '这个', '来', '他', '时候', '才', '么', '但', '下', '可以', 
    '她', '里', '最', '他们', '些', '什么', '还', '可', '能', '被', '那', '所以', '为', '却', '吗', '让', '更', '知道', 
    '两', '中', '做', '它', '呢', '再', '想', '对', '已', '把', '则', '从', '应', '向', '地', '给', '起', '真', '很多'
])

def split_sentences(text: str) -> List[str]:
    """
    将文本分割成句子
    
    Args:
        text: 要分割的文本
        
    Returns:
        句子列表
    """
    # 首先检测文本主要是中文还是英文
    chinese_char_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_char_count = max(1, len(text.strip()))
    
    # 如果中文字符占比超过30%，使用中文分句规则
    if chinese_char_count / total_char_count > 0.3:
        # 中文分句模式
        pattern = r'(?<=[。！？…\.\!\?])\s*'
        sentences = re.split(pattern, text)
        # 过滤空句子并修剪空白
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    # 对于英文，尝试使用NLTK
    try:
        sentences = nltk.sent_tokenize(text)
        return [s.strip() for s in sentences if s.strip()]
    except Exception as e:
        logger.warning(f"NLTK分句失败: {e}，使用简单正则表达式分句")
        # 简单英文分句备用方案
        pattern = r'(?<=[.!?])\s+'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

def clean_text(text: str) -> str:
    """
    清理文本，移除多余空白和特殊字符
    
    Args:
        text: 要清理的文本
        
    Returns:
        清理后的文本
    """
    # 替换多个空白字符为单个空格
    text = re.sub(r'\s+', ' ', text)
    
    # 移除URL
    text = re.sub(r'https?://\S+', '', text)
    
    # 移除HTML标签
    text = re.sub(r'<.*?>', '', text)
    
    # 替换重复标点
    text = re.sub(r'([.!?])[.!?]+', r'\1', text)
    
    # 替换重复中文标点
    text = re.sub(r'([。！？])[。！？]+', r'\1', text)
    
    return text.strip()

def is_chinese_sentence(sentence: str) -> bool:
    """
    检查句子是否主要是中文
    
    Args:
        sentence: 要检查的句子
        
    Returns:
        如果句子主要是中文，返回True，否则返回False
    """
    chinese_char_count = len(re.findall(r'[\u4e00-\u9fff]', sentence))
    total_char_count = max(1, len(sentence.strip()))
    return chinese_char_count / total_char_count > 0.5

def tokenize(sentence: str, remove_stopwords: bool = True) -> List[str]:
    """
    对句子进行分词
    
    Args:
        sentence: 要分词的句子
        remove_stopwords: 是否移除停用词
        
    Returns:
        分词列表
    """
    # 检查是否为中文句子
    if is_chinese_sentence(sentence):
        # 如果是中文，使用字符级分词
        words = list(sentence)
        if remove_stopwords:
            words = [w for w in words if w not in CHINESE_STOPWORDS]
    else:
        # 如果是英文，使用NLTK分词
        try:
            words = nltk.word_tokenize(sentence.lower())
            # 移除标点和数字
            words = [w for w in words if w.isalpha()]
            if remove_stopwords:
                words = [w for w in words if w not in STOPWORDS]
        except Exception as e:
            logger.warning(f"NLTK分词失败: {e}，使用简单空格分词")
            # 简单分词备用方案
            words = sentence.lower().split()
            words = [w.strip('.,!?;:()[]{}"\'-') for w in words]
            words = [w for w in words if w.isalpha()]
            if remove_stopwords:
                words = [w for w in words if w not in STOPWORDS]
                
    return words

def calculate_word_frequencies(sentences: List[str]) -> Dict[str, float]:
    """
    计算文本中单词的频率
    
    Args:
        sentences: 句子列表
        
    Returns:
        单词频率字典
    """
    word_frequencies = {}
    
    for sentence in sentences:
        for word in tokenize(sentence):
            if word not in word_frequencies:
                word_frequencies[word] = 1
            else:
                word_frequencies[word] += 1
    
    # 归一化频率
    if word_frequencies:
        max_frequency = max(word_frequencies.values())
        if max_frequency > 0:
            for word in word_frequencies:
                word_frequencies[word] /= max_frequency
    
    return word_frequencies

def calculate_sentence_scores(
    sentences: List[str],
    word_frequencies: Dict[str, float]
) -> Dict[str, float]:
    """
    计算句子得分
    
    Args:
        sentences: 句子列表
        word_frequencies: 单词频率字典
        
    Returns:
        句子得分字典
    """
    sentence_scores = {}
    
    for sentence in sentences:
        # 长度处理：忽略太短的句子
        if len(sentence.split()) <= 2:
            continue
            
        # 计算句子中单词的频率总和
        score = 0
        words = tokenize(sentence)
        
        if not words:
            continue
            
        for word in words:
            if word in word_frequencies:
                score += word_frequencies[word]
        
        # 归一化得分（除以单词数量）
        sentence_scores[sentence] = score / len(words)
    
    return sentence_scores

def tf_idf_vectorize(sentences: List[str]) -> Tuple[np.ndarray, List[str]]:
    """
    使用TF-IDF向量化句子
    
    Args:
        sentences: 句子列表
        
    Returns:
        (向量化结果矩阵, 特征词列表)
    """
    # 将句子分词
    tokenized_sentences = [tokenize(sentence) for sentence in sentences]
    
    # 创建单词集合
    vocabulary = set()
    for tokens in tokenized_sentences:
        vocabulary.update(tokens)
    
    vocabulary = list(vocabulary)
    
    # 计算TF (Term Frequency)
    tf_matrix = np.zeros((len(sentences), len(vocabulary)))
    
    for i, tokens in enumerate(tokenized_sentences):
        for token in tokens:
            tf_matrix[i, vocabulary.index(token)] += 1
    
    # 对TF值进行归一化
    row_sums = tf_matrix.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1  # 避免除以0
    tf_matrix = tf_matrix / row_sums
    
    # 计算IDF (Inverse Document Frequency)
    df = np.sum(tf_matrix > 0, axis=0)
    idf = np.log(len(sentences) / (df + 1)) + 1  # 添加1平滑
    
    # 计算TF-IDF
    tfidf_matrix = tf_matrix * idf
    
    return tfidf_matrix, vocabulary

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    计算两个向量的余弦相似度
    
    Args:
        vec1: 第一个向量
        vec2: 第二个向量
        
    Returns:
        余弦相似度（0到1之间）
    """
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0
    
    return np.dot(vec1, vec2) / (norm1 * norm2)

def calculate_sentence_similarity_matrix(
    tfidf_matrix: np.ndarray
) -> np.ndarray:
    """
    计算句子相似度矩阵
    
    Args:
        tfidf_matrix: TF-IDF向量化的结果
        
    Returns:
        相似度矩阵
    """
    n_sentences = tfidf_matrix.shape[0]
    similarity_matrix = np.zeros((n_sentences, n_sentences))
    
    for i in range(n_sentences):
        for j in range(n_sentences):
            if i == j:
                similarity_matrix[i, j] = 1
            else:
                similarity_matrix[i, j] = cosine_similarity(
                    tfidf_matrix[i], tfidf_matrix[j]
                )
    
    return similarity_matrix

def create_extractive_summary(
    sentences: List[str],
    sentence_scores: Dict[str, float],
    summary_length: int = 3
) -> str:
    """
    创建提取式摘要
    
    Args:
        sentences: 原始句子列表
        sentence_scores: 句子得分字典
        summary_length: 摘要中句子的数量
        
    Returns:
        摘要文本
    """
    # 按得分排序句子
    sorted_sentences = sorted(
        sentence_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    # 选择得分最高的n个句子
    summary_sentences = [sentence for sentence, _ in sorted_sentences[:summary_length]]
    
    # 按原始顺序重新排列句子
    original_order_summary = [s for s in sentences if s in summary_sentences]
    
    # 组合成摘要
    summary = ' '.join(original_order_summary)
    
    return summary

def truncate_text(text: str, max_length: int = 8000) -> str:
    """
    将文本截断到指定长度，保持完整句子
    
    Args:
        text: 要截断的文本
        max_length: 最大长度
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    
    # 分割成句子
    sentences = split_sentences(text)
    
    # 逐句添加，直到达到最大长度
    truncated_text = ""
    for sentence in sentences:
        if len(truncated_text) + len(sentence) + 1 <= max_length:
            if truncated_text:
                truncated_text += " " + sentence
            else:
                truncated_text = sentence
        else:
            break
    
    return truncated_text

def detect_language(text: str) -> str:
    """
    检测文本语言
    
    Args:
        text: 文本内容
        
    Returns:
        语言代码："zh"(中文)，"en"(英文)，"other"(其他)
    """
    # 计算中文字符比例
    chinese_char_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    # 计算英文字母比例
    english_char_count = len(re.findall(r'[a-zA-Z]', text))
    
    total_length = max(1, len(text.strip()))
    
    chinese_ratio = chinese_char_count / total_length
    english_ratio = english_char_count / total_length
    
    if chinese_ratio > 0.3:
        return "zh"
    elif english_ratio > 0.5:
        return "en"
    else:
        return "other"

def format_text_chunks(text: str, chunk_size: int = 4000) -> List[str]:
    """
    将长文本分割成大小合适的块
    
    Args:
        text: 要分割的文本
        chunk_size: 每个块的最大长度
        
    Returns:
        文本块列表
    """
    chunks = []
    sentences = split_sentences(text)
    
    current_chunk = ""
    for sentence in sentences:
        # 如果当前句子加上当前块超出了块大小
        if len(current_chunk) + len(sentence) + 1 > chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
    
    # 添加最后一个块
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def count_tokens(text: str) -> int:
    """
    估计文本中的标记数量
    
    Args:
        text: 要计数的文本
        
    Returns:
        估计的标记数量
    """
    # 检测语言
    language = detect_language(text)
    
    if language == "zh":
        # 中文：每个字符大约是一个标记
        return len(text)
    else:
        # 英文：粗略估计为单词数的1.3倍
        words = text.split()
        return int(len(words) * 1.3)

# 测试代码
def test_text_utils():
    """测试文本处理工具"""
    print("===== 文本处理工具测试 =====")
    
    # 测试句子分割
    test_text_en = """This is a test paragraph. It contains several sentences! 
    Each sentence should be properly identified. Do you think it works? I hope so."""
    
    test_text_zh = """这是一个测试段落。它包含了几个句子！
    每个句子都应该被正确识别。你认为它有效吗？我希望如此。"""
    
    print("\n测试英文句子分割:")
    sentences_en = split_sentences(test_text_en)
    for i, sentence in enumerate(sentences_en, 1):
        print(f"{i}. {sentence}")
    
    print("\n测试中文句子分割:")
    sentences_zh = split_sentences(test_text_zh)
    for i, sentence in enumerate(sentences_zh, 1):
        print(f"{i}. {sentence}")
    
    # 测试文本清理
    dirty_text = """This    is a   messy  text     with   extra    spaces
    and a https://example.com URL and <b>some HTML</b> tags!!!"""
    
    print("\n测试文本清理:")
    clean = clean_text(dirty_text)
    print(f"原始文本: {dirty_text}")
    print(f"清理后: {clean}")
    
    # 测试分词
    test_sentence = "This is a simple test sentence with stopwords."
    print("\n测试分词:")
    tokens = tokenize(test_sentence)
    print(f"原始句子: {test_sentence}")
    print(f"分词结果 (移除停用词): {tokens}")
    
    # 测试提取式摘要
    print("\n测试提取式摘要:")
    word_freqs = calculate_word_frequencies(sentences_en)
    sentence_scores = calculate_sentence_scores(sentences_en, word_freqs)
    summary = create_extractive_summary(sentences_en, sentence_scores, 2)
    print(f"原始文本: {test_text_en}")
    print(f"提取式摘要: {summary}")
    
    # 测试语言检测
    print("\n测试语言检测:")
    print(f"英文文本检测结果: {detect_language(test_text_en)}")
    print(f"中文文本检测结果: {detect_language(test_text_zh)}")
    
    # 测试文本分块
    long_text = test_text_en * 5
    print("\n测试文本分块:")
    chunks = format_text_chunks(long_text, 100)
    print(f"分割为 {len(chunks)} 个块:")
    for i, chunk in enumerate(chunks, 1):
        print(f"块 {i} ({len(chunk)} 字符): {chunk[:30]}...")
    
    # 测试标记计数
    print("\n测试标记计数:")
    print(f"英文文本标记数: {count_tokens(test_text_en)}")
    print(f"中文文本标记数: {count_tokens(test_text_zh)}")

if __name__ == "__main__":
    test_text_utils() 