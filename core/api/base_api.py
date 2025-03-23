#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基础API抽象类
定义所有AI模型API必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any

class BaseModelAPI(ABC):
    """所有模型API的基类，定义统一接口"""
    
    @abstractmethod
    def __init__(self, **kwargs):
        """初始化API"""
        pass
        
    @abstractmethod
    def summarize_text(self, text: str, max_length: Optional[int] = None, 
                      temperature: float = 0.7) -> str:
        """
        生成文本摘要
        
        Args:
            text: 需要摘要的原文
            max_length: 摘要的最大长度，可选
            temperature: 生成随机性，值越大随机性越高
            
        Returns:
            摘要文本
        """
        pass
        
    @abstractmethod
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
        pass
        
    def is_available(self) -> bool:
        """
        检查API是否可用
        
        Returns:
            布尔值，表示API是否可用
        """
        try:
            # 基本实现：尝试生成一个简单的摘要
            test_text = "这是一个测试。API是否正常工作？"
            self.summarize_text(test_text, max_length=10)
            return True
        except Exception:
            return False