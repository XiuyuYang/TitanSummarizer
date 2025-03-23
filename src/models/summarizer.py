#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
摘要生成模型基类
定义摘要生成的核心接口和共享功能
"""

import os
import logging
import time
from typing import Optional, List, Dict, Callable, Tuple, Union
from tqdm import tqdm
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义可用模型类型
MODEL_TYPES = {
    "deepseek-api": "deepseek-api",  # DeepSeek API
    "ollama-local": "ollama-local",  # Ollama本地模型
}

def get_model_name(model_type):
    """
    获取模型名称
    
    Args:
        model_type: 模型类型
        
    Returns:
        模型名称
    """
    if model_type in MODEL_TYPES:
        return MODEL_TYPES[model_type]
    
    # 默认使用DeepSeek API
    return "deepseek-api"

def available_devices():
    """
    返回可用的设备列表
    
    Returns:
        设备列表
    """
    # 由于使用API，设备选择不再重要
    return ["cpu"]

class BaseSummarizer:
    """摘要生成模型的基类，定义共同接口"""
    
    def __init__(
        self,
        progress_callback: Optional[Callable[[float, str, Optional[float]], None]] = None
    ):
        """
        初始化摘要模型基类
        
        Args:
            progress_callback: 进度回调函数，接收三个参数：进度(0-1)，消息，文件进度(0-100或None)
        """
        self.progress_callback = progress_callback
        
    def generate_summary(
        self,
        text: str,
        max_length: int = 200,
        callback: Optional[Callable[[str], None]] = None,
        file_percentage: int = 0,
        summary_mode: str = "generative"  # 默认为生成式
    ) -> str:
        """
        生成文本摘要
        
        Args:
            text: 需要摘要的原始文本
            max_length: 摘要的最大长度
            callback: 回调函数，用于接收生成的部分摘要
            file_percentage: 当前处理进度百分比
            summary_mode: 摘要模式，"generative"或"extractive"
        
        Returns:
            生成的摘要文本
        """
        if not text or not text.strip():
            return "无法生成摘要：文本为空"
            
        # 根据模式选择不同的摘要方法
        if summary_mode == "extractive":
            logger.info("使用提取式摘要")
            return self._extractive_summarize(text, max_length)
        else:
            logger.info("使用生成式摘要")
            return self._generative_summarize(text, max_length, callback, file_percentage)
    
    def _extractive_summarize(self, text: str, max_length: int = 200) -> str:
        """
        使用提取式方法生成摘要
        
        Args:
            text: 需要摘要的文本
            max_length: 摘要的最大长度
            
        Returns:
            提取式摘要
        """
        # 分句
        sentences = self._split_sentences(text)
        if not sentences:
            return "无法生成摘要：文本格式不正确"
            
        # 如果句子数量很少，直接返回前几句
        if len(sentences) <= 3:
            summary = ''.join(sentences)
            if len(summary) > max_length:
                return summary[:max_length] + "..."
            return summary
            
        try:
            # 创建TF-IDF向量化器
            vectorizer = TfidfVectorizer(lowercase=False, token_pattern=r"(?u)\b\w+\b")
            # 计算句子的TF-IDF矩阵
            tfidf_matrix = vectorizer.fit_transform(sentences)
            
            # 计算句子相似度
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            # 计算每个句子的重要性得分
            scores = np.sum(similarity_matrix, axis=1)
            
            # 获取重要性排名
            ranked_indices = np.argsort(scores)[::-1]
            
            # 选择重要的句子，但保持原文顺序
            top_indices = sorted(ranked_indices[:min(5, len(ranked_indices))])
            
            # 限制总长度
            selected_sentences = []
            current_length = 0
            
            for idx in top_indices:
                sentence = sentences[idx]
                if current_length + len(sentence) <= max_length:
                    selected_sentences.append(sentence)
                    current_length += len(sentence)
                else:
                    # 如果第一句就超过了最大长度，截断它
                    if not selected_sentences:
                        return sentence[:max_length] + "..."
                    break
                    
            summary = ''.join(selected_sentences)
            
            # 最终检查长度
            if len(summary) > max_length:
                return summary[:max_length] + "..."
                
            return summary
            
        except Exception as e:
            logger.error(f"提取式摘要生成错误: {e}")
            # 如果失败，返回文本的前几句话
            fallback = ''.join(sentences[:3])
            if len(fallback) > max_length:
                return fallback[:max_length] + "..."
            return fallback
    
    def _generative_summarize(
        self,
        text: str,
        max_length: int = 200,
        callback: Optional[Callable[[str], None]] = None,
        file_percentage: int = 0
    ) -> str:
        """
        使用生成式方法生成摘要，此方法由子类实现
        
        Args:
            text: 需要摘要的文本
            max_length: 摘要的最大长度
            callback: 回调函数
            file_percentage: 处理进度百分比
            
        Returns:
            生成的摘要
        """
        # 这是一个抽象方法，应该由子类实现
        raise NotImplementedError("子类必须实现_generative_summarize方法")
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        将文本分割成句子
        
        Args:
            text: 输入文本
            
        Returns:
            句子列表
        """
        # 使用正则表达式分割句子
        # 考虑中文的句号、问号、叹号等
        pattern = r'([。！？\!\?])'
        # 分割文本
        sentences = []
        segments = re.split(pattern, text)
        
        # 重新组合句子
        for i in range(0, len(segments)-1, 2):
            if i+1 < len(segments):
                sentences.append(segments[i] + segments[i+1])
            else:
                sentences.append(segments[i])
                
        # 处理剩余可能的最后一个段落
        if len(segments) % 2 == 1:
            sentences.append(segments[-1])
            
        # 过滤空句
        return [s for s in sentences if s.strip()]
    
    def translate_text(
        self,
        text: str,
        target_language: str = "English",
        callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        翻译文本到目标语言
        
        Args:
            text: 需要翻译的文本
            target_language: 目标语言
            callback: 回调函数
            
        Returns:
            翻译后的文本
        """
        # 这是一个示例实现，实际翻译功能应由子类实现
        logger.warning("BaseSummarizer不提供翻译功能，请使用具体的API实现")
        return f"[翻译到{target_language}功能未实现]"
    
    def is_model_loaded(self) -> bool:
        """
        检查模型是否已加载
        
        Returns:
            布尔值，表示模型是否已加载
        """
        # 基类默认认为模型已加载
        return True 