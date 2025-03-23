#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文本处理工具模块
提供各种文本预处理、分析和格式化功能
"""

import re
import os
import logging
from typing import List, Dict, Any, Optional, Tuple

# 设置日志
logger = logging.getLogger(__name__)

def split_text_into_chunks(text: str, max_chunk_size: int = 2000, 
                         overlap: int = 200) -> List[str]:
    """
    将长文本分割成多个重叠的小块
    
    Args:
        text: 要分割的文本
        max_chunk_size: 每个块的最大大小（字符数）
        overlap: 相邻块之间的重叠字符数
        
    Returns:
        文本块列表
    """
    if len(text) <= max_chunk_size:
        return [text]
        
    # 尝试在句子边界分割
    chunks = []
    start = 0
    
    while start < len(text):
        # 确定当前块的结束位置
        end = min(start + max_chunk_size, len(text))
        
        # 如果不是文本末尾，尝试找到句子边界
        if end < len(text):
            # 在当前块中查找最后一个句子结束符
            sentence_ends = [match.end() for match in re.finditer(r'[。！？.!?]', text[start:end])]
            
            if sentence_ends:
                # 使用最后一个句子结束符作为分割点
                end = start + sentence_ends[-1]
            else:
                # 如果没有找到句子结束符，至少尝试在词语边界分割
                space_positions = [match.start() for match in re.finditer(r'\s+', text[end-100:end])]
                if space_positions:
                    end = end - 100 + space_positions[-1]
        
        # 添加当前块
        chunks.append(text[start:end])
        
        # 更新下一个块的起始位置，考虑重叠
        start = max(0, end - overlap)
    
    return chunks

def detect_text_language(text: str) -> str:
    """
    检测文本的语言
    
    Args:
        text: 要检测的文本
        
    Returns:
        检测到的语言代码
    """
    # 基本的语言检测逻辑
    # 检测是否包含中文字符
    if re.search(r'[\u4e00-\u9fff]', text):
        return "中文"
        
    # 检测是否包含日文特有字符
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
        return "日文"
        
    # 检测是否包含韩文字符
    if re.search(r'[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F\uA960-\uA97F\uD7B0-\uD7FF]', text):
        return "韩文"
        
    # 默认假设是英文
    return "英文"

def count_words(text: str) -> int:
    """
    统计文本中的词数
    
    Args:
        text: 要统计的文本
        
    Returns:
        词数
    """
    # 检测文本语言
    language = detect_text_language(text)
    
    if language == "中文":
        # 中文按字符计数（粗略估计）
        # 移除标点和空格
        cleaned_text = re.sub(r'[^\u4e00-\u9fff]', '', text)
        return len(cleaned_text)
    else:
        # 其他语言按空格分词
        words = text.split()
        return len(words)

def clean_text(text: str) -> str:
    """
    清理文本，移除多余空白，规范化标点等
    
    Args:
        text: 要清理的文本
        
    Returns:
        清理后的文本
    """
    # 替换连续多个空白为单个空格
    text = re.sub(r'\s+', ' ', text)
    
    # 移除行首和行尾的空白
    text = text.strip()
    
    # 规范化标点（中文标点统一）
    text = text.replace('，', '，').replace('。', '。').replace('；', '；')
    text = text.replace('：', '：').replace('？', '？').replace('！', '！')
    
    return text

def extract_title_from_text(text: str) -> Optional[str]:
    """
    从文本中提取可能的标题
    
    Args:
        text: 要分析的文本
        
    Returns:
        提取的标题，如果无法提取则返回None
    """
    # 移除开头的空白
    text = text.lstrip()
    
    # 尝试获取第一行作为标题
    lines = text.split('\n')
    first_line = lines[0].strip() if lines else ""
    
    # 如果第一行太长，可能不是标题
    if first_line and len(first_line) < 50:
        return first_line
        
    # 尝试查找明显的标题模式
    title_patterns = [
        r'^第.+章\s*(.+)',  # 小说章节格式
        r'^Chapter\s+\d+[:\.\s]+(.+)',  # 英文章节格式
        r'^标题[：:]\s*(.+)',  # 显式标题标记
        r'^Title[:\s]+(.+)'   # 英文显式标题标记
    ]
    
    for pattern in title_patterns:
        match = re.search(pattern, text[:200])
        if match:
            return match.group(1).strip()
    
    # 无法找到明确的标题
    return None

def load_text_from_file(file_path: str) -> Tuple[str, Optional[str]]:
    """
    从文件加载文本内容
    
    Args:
        file_path: 文件路径
        
    Returns:
        元组 (文本内容, 可能的标题)
    """
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return "", None
        
    try:
        # 尝试用不同编码读取文件
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']
        text = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    text = f.read()
                logger.info(f"成功以{encoding}编码读取文件")
                break
            except UnicodeDecodeError:
                continue
        
        if text is None:
            logger.error(f"无法解码文件: {file_path}")
            return "", None
            
        # 清理文本
        text = clean_text(text)
        
        # 尝试提取标题
        title = extract_title_from_text(text)
        
        return text, title
        
    except Exception as e:
        logger.error(f"读取文件时出错: {str(e)}")
        return "", None