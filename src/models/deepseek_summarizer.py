#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于DeepSeek API的摘要生成模型
使用DeepSeek API进行文本摘要和翻译
"""

import time
import logging
from typing import Optional, Callable

from src.models.summarizer import BaseSummarizer
from src.api.deepseek_api import DeepSeekAPI

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepSeekSummarizer(BaseSummarizer):
    """
    使用DeepSeek API的摘要生成器
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        use_mock: bool = True,
        progress_callback: Optional[Callable[[float, str, Optional[float]], None]] = None
    ):
        """
        初始化DeepSeek摘要生成器
        
        Args:
            api_key: DeepSeek API密钥，如果为None则使用默认值
            use_mock: 是否使用模拟模式
            progress_callback: 进度回调函数
        """
        super().__init__(progress_callback)
        
        # 初始化API客户端
        logger.info("初始化DeepSeek API客户端")
        self.api = DeepSeekAPI(api_key=api_key, use_mock=use_mock)
        self.model_loaded = True  # API模式下始终认为模型已加载
        
        if use_mock:
            logger.info("使用模拟API模式")
    
    def _generative_summarize(
        self,
        text: str,
        max_length: int = 200,
        callback: Optional[Callable[[str], None]] = None,
        file_percentage: int = 0
    ) -> str:
        """
        使用DeepSeek API生成摘要
        
        Args:
            text: 需要摘要的文本
            max_length: 摘要的最大长度
            callback: 回调函数
            file_percentage: 文件处理进度
            
        Returns:
            生成的摘要
        """
        try:
            # 通知进度开始
            if self.progress_callback:
                self.progress_callback(0.0, "正在使用DeepSeek API生成摘要...", file_percentage)
            
            # 调用API生成摘要
            start_time = time.time()
            summary = self.api.summarize_text(text, max_length=max_length)
            end_time = time.time()
            
            # 记录生成时间
            logger.info(f"DeepSeek API摘要生成完成，耗时: {end_time - start_time:.2f}秒")
            
            # 通知进度完成
            if self.progress_callback:
                self.progress_callback(1.0, "摘要生成完成", file_percentage)
            
            # 如果有回调函数，调用它
            if callback:
                callback(summary)
                
            return summary
            
        except Exception as e:
            error_msg = f"DeepSeek API摘要生成失败: {str(e)}"
            logger.error(error_msg)
            
            # 出错时使用提取式摘要作为备选
            logger.info("使用提取式摘要作为备选")
            return self._extractive_summarize(text, max_length)
    
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
        try:
            # 通知进度开始
            if self.progress_callback:
                self.progress_callback(0.0, f"正在将文本翻译为{target_language}...", None)
            
            # 构建翻译提示词
            prompt = f"请将以下文本翻译为{target_language}，保持原文的意思和风格：\n\n{text}"
            
            # 调用API进行翻译
            # 注意：这里借用summarize_text方法进行翻译
            translated = self.api.summarize_text(prompt, max_length=len(text) * 2)
            
            # 通知进度完成
            if self.progress_callback:
                self.progress_callback(1.0, "翻译完成", None)
            
            # 如果有回调函数，调用它
            if callback:
                callback(translated)
                
            return translated
            
        except Exception as e:
            error_msg = f"翻译失败: {str(e)}"
            logger.error(error_msg)
            return f"[翻译失败: {error_msg}]"
    
    def is_model_loaded(self) -> bool:
        """
        检查模型是否已加载
        
        Returns:
            布尔值，表示模型是否已加载
        """
        # API模式始终返回True
        return True

# 测试代码
def test_deepseek_summarizer():
    """测试DeepSeek摘要生成器"""
    
    # 创建摘要器实例，使用模拟模式
    summarizer = DeepSeekSummarizer(use_mock=True)
    
    # 测试文本
    test_text = """中国是世界上最大的发展中国家，拥有超过14亿人口。自1978年改革开放以来，中国经济快速发展，现已成为世界第二大经济体。中国有着悠久的历史和灿烂的文化，是四大文明古国之一。北京是中国的首都，上海是其最大的城市和金融中心。中国地形多样，包括山脉、高原、盆地和平原等。中国是联合国安理会五个常任理事国之一，在全球事务中扮演着越来越重要的角色。"""
    
    print("===== DeepSeek摘要生成器测试 =====")
    print(f"原文 ({len(test_text)}字符):\n{test_text}\n")
    
    # 测试生成式摘要
    print("生成式摘要测试:")
    gen_summary = summarizer.generate_summary(test_text, max_length=100, summary_mode="generative")
    print(f"生成式摘要 ({len(gen_summary)}字符):\n{gen_summary}\n")
    
    # 测试提取式摘要
    print("提取式摘要测试:")
    ext_summary = summarizer.generate_summary(test_text, max_length=100, summary_mode="extractive")
    print(f"提取式摘要 ({len(ext_summary)}字符):\n{ext_summary}\n")
    
    # 测试翻译
    print("翻译测试:")
    translated = summarizer.translate_text("你好，我是一个人工智能助手。", "English")
    print(f"翻译结果: {translated}")

if __name__ == "__main__":
    test_deepseek_summarizer() 