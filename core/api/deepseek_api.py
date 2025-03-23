#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DeepSeek API 客户端
提供与DeepSeek大模型API的交互能力
"""

import os
import json
import time
import random
import requests
import logging
from typing import Optional, Dict, Any

from core.api.base_api import BaseModelAPI

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API密钥默认值（请在实际使用时替换为有效密钥）
DEFAULT_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-46666666666666666666666666666666")

class DeepSeekAPI(BaseModelAPI):
    """DeepSeek API客户端"""
    
    def __init__(self, api_key: Optional[str] = None, use_mock: bool = True):
        """
        初始化DeepSeek API客户端
        
        Args:
            api_key: API密钥，如果为None则使用环境变量或默认值
            use_mock: 是否使用模拟模式（不实际调用API）
        """
        self.api_key = api_key or DEFAULT_API_KEY
        self.api_base = "https://api.deepseek.com/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self.use_mock = use_mock
        
        if self.use_mock:
            logger.info("注意: 使用模拟API模式，非实际API调用")
            print("注意: 使用模拟API模式，非实际API调用")
    
    def summarize_text(self, text: str, max_length: Optional[int] = None, 
                      temperature: float = 0.7) -> str:
        """
        使用DeepSeek API对文本进行摘要
        
        Args:
            text: 需要摘要的文本
            max_length: 摘要的最大长度，可选
            temperature: 生成随机性，值越大随机性越高
            
        Returns:
            摘要文本
        """
        # 如果使用模拟模式，则不实际调用API
        if self.use_mock:
            return self._mock_summarize(text, max_length)
            
        url = f"{self.api_base}/chat/completions"
        
        # 构建提示词来指导模型进行文本摘要
        prompt = f"请将以下文本缩写为简洁的摘要，保留关键信息：\n\n{text}"
        
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature
        }
        
        if max_length:
            payload["max_tokens"] = max_length
        
        try:
            logger.info("发送API请求到DeepSeek")
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()  # 抛出HTTP错误
            
            result = response.json()
            summary = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.info(f"摘要生成成功，长度: {len(summary)}")
            return summary
        
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求错误: {e}")
            print(f"API请求错误: {e}")
            # 如果API请求失败，切换到模拟模式
            logger.info("API调用失败，切换到模拟模式")
            print("API调用失败，切换到模拟模式")
            return self._mock_summarize(text, max_length)
    
    def translate_text(self, text: str, target_language: str = "English", 
                     temperature: float = 0.7) -> str:
        """
        文本翻译
        
        Args:
            text: 需要翻译的原文
            target_language: 目标语言
            temperature: 生成随机性，值越大随机性越高
            
        Returns:
            翻译后的文本
        """
        # 如果使用模拟模式，则不实际调用API
        if self.use_mock:
            return self._mock_translate(text, target_language)
            
        url = f"{self.api_base}/chat/completions"
        
        # 构建提示词来指导模型进行文本翻译
        prompt = f"请将以下文本翻译成{target_language}：\n\n{text}"
        
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature
        }
        
        try:
            logger.info(f"发送翻译请求到DeepSeek (目标语言: {target_language})")
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()  # 抛出HTTP错误
            
            result = response.json()
            translation = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.info(f"翻译成功，长度: {len(translation)}")
            return translation
        
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求错误: {e}")
            print(f"API请求错误: {e}")
            return self._mock_translate(text, target_language)
    
    def _mock_summarize(self, text: str, max_length: Optional[int] = None) -> str:
        """
        模拟API摘要功能，用于测试
        
        Args:
            text: 需要摘要的文本
            max_length: 摘要的最大长度，可选
            
        Returns:
            摘要文本
        """
        logger.info("使用模拟API生成摘要")
        
        # 简单的摘要模拟算法：提取第一句话，然后随机选择其他几个关键句子
        sentences = text.split('。')
        sentences = [s + '。' for s in sentences if s.strip()]
        
        if not sentences:
            return "无法生成摘要：文本格式不正确"
            
        # 始终包含第一句
        summary_sentences = [sentences[0]]
        
        # 计算要选择的句子数量 (大约是原文的20-30%)
        select_count = max(1, min(len(sentences) // 4, 3))
        
        # 如果原文够长，随机挑选其他句子
        if len(sentences) > 2:
            selected = random.sample(sentences[1:], min(select_count, len(sentences)-1))
            summary_sentences.extend(selected)
        
        # 确保句子顺序与原文一致
        summary_sentences.sort(key=lambda s: text.index(s))
        
        summary = ''.join(summary_sentences)
        
        # 如果指定了max_length并且超出限制，截断
        if max_length and len(summary) > max_length:
            summary = summary[:max_length] + "..."
            
        # 模拟API延迟
        time.sleep(1)
        
        logger.info(f"模拟摘要生成完成，长度: {len(summary)}")
        return summary
        
    def _mock_translate(self, text: str, target_language: str) -> str:
        """
        模拟API翻译功能，用于测试
        
        Args:
            text: 需要翻译的文本
            target_language: 目标语言
            
        Returns:
            翻译后的文本
        """
        logger.info(f"使用模拟API翻译到{target_language}")
        
        # 简单的翻译模拟
        if target_language.lower() in ["english", "英语", "英文"]:
            # 中文 -> 英文的简单模拟
            prefix = "This is a mock translation. "
            suffix = " (Translated by Mock API)"
            translated = prefix + text[:min(20, len(text))] + "..." + suffix
        else:
            # 假设翻译到其他语言
            prefix = f"这是模拟翻译到{target_language}的结果。"
            suffix = "（由模拟API翻译）"
            translated = prefix + text[:min(20, len(text))] + "..." + suffix
            
        # 模拟API延迟
        time.sleep(1)
        
        logger.info(f"模拟翻译完成，长度: {len(translated)}")
        return translated