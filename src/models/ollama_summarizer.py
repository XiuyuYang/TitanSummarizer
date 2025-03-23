#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基于Ollama的摘要生成模型
使用本地Ollama模型进行文本摘要
"""

import time
import logging
from typing import Optional, Callable, List, Dict

from src.models.summarizer import BaseSummarizer
from src.api.ollama_api import OllamaAPI

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaSummarizer(BaseSummarizer):
    """
    使用本地Ollama模型的摘要生成器
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str, Optional[float]], None]] = None
    ):
        """
        初始化Ollama摘要生成器
        
        Args:
            model_path: 模型文件路径，如果为None则需要手动加载模型
            progress_callback: 进度回调函数
        """
        super().__init__(progress_callback)
        
        # 初始化Ollama API客户端
        logger.info("初始化Ollama API客户端")
        self.api = OllamaAPI()
        self.model_loaded = False
        self.local_model_path = model_path
        
        # 如果提供了模型路径，尝试加载模型
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: str) -> bool:
        """
        加载指定的模型
        
        Args:
            model_path: 模型文件路径
            
        Returns:
            布尔值，表示是否成功加载
        """
        logger.info(f"加载Ollama模型: {model_path}")
        
        # 通知进度开始
        if self.progress_callback:
            self.progress_callback(0.1, f"正在加载本地模型: {model_path}", None)
        
        try:
            # 调用API加载模型
            model_name = self.api.load_model(model_path)
            
            if model_name:
                logger.info(f"成功加载模型: {model_name}")
                self.model_loaded = True
                self.local_model_path = model_path
                
                # 通知进度完成
                if self.progress_callback:
                    self.progress_callback(1.0, f"模型加载成功: {model_name}", None)
                
                return True
            else:
                error_msg = "模型加载失败，返回了空的模型名称"
                logger.error(error_msg)
                
                # 通知进度失败
                if self.progress_callback:
                    self.progress_callback(1.0, error_msg, None)
                
                return False
                
        except Exception as e:
            error_msg = f"加载模型时出错: {str(e)}"
            logger.error(error_msg)
            
            # 通知进度失败
            if self.progress_callback:
                self.progress_callback(1.0, error_msg, None)
            
            return False
    
    def find_all_models(self) -> List[Dict]:
        """
        查找所有可用的本地模型
        
        Returns:
            模型信息列表
        """
        return self.api.find_all_models()
    
    def _generative_summarize(
        self,
        text: str,
        max_length: int = 200,
        callback: Optional[Callable[[str], None]] = None,
        file_percentage: int = 0
    ) -> str:
        """
        使用Ollama模型生成摘要
        
        Args:
            text: 需要摘要的文本
            max_length: 摘要的最大长度
            callback: 回调函数
            file_percentage:.文件处理进度
            
        Returns:
            生成的摘要
        """
        # 检查模型是否已加载
        if not self.is_model_loaded():
            error_msg = "尚未加载模型，无法生成摘要"
            logger.error(error_msg)
            
            # 使用提取式摘要作为备选
            logger.info("使用提取式摘要作为备选")
            return self._extractive_summarize(text, max_length)
            
        try:
            # 通知进度开始
            if self.progress_callback:
                self.progress_callback(0.0, "正在使用Ollama模型生成摘要...", file_percentage)
            
            # 调用API生成摘要
            start_time = time.time()
            summary = self.api.summarize_text(text, max_length=max_length)
            end_time = time.time()
            
            # 记录生成时间
            logger.info(f"Ollama摘要生成完成，耗时: {end_time - start_time:.2f}秒")
            
            # 通知进度完成
            if self.progress_callback:
                self.progress_callback(1.0, "摘要生成完成", file_percentage)
            
            # 如果有回调函数，调用它
            if callback:
                callback(summary)
                
            return summary
            
        except Exception as e:
            error_msg = f"Ollama摘要生成失败: {str(e)}"
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
        # 检查模型是否已加载
        if not self.is_model_loaded():
            error_msg = "尚未加载模型，无法进行翻译"
            logger.error(error_msg)
            return f"[翻译失败: {error_msg}]"
            
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
        # 先检查实例变量
        if not hasattr(self, 'model_loaded') or not self.model_loaded:
            logger.info("模型未加载 (实例状态)")
            return False
            
        # 再检查API
        try:
            is_loaded = self.api.is_model_loaded()
            if not is_loaded:
                logger.warning("API报告模型未加载")
                # 更新实例状态
                self.model_loaded = False
            return is_loaded
        except Exception as e:
            logger.error(f"检查模型加载状态时出错: {str(e)}")
            return False

# 测试代码
def test_ollama_summarizer():
    """测试Ollama摘要生成器"""
    
    # 创建摘要器实例
    summarizer = OllamaSummarizer()
    
    print("===== Ollama摘要生成器测试 =====")
    
    # 找到可用的模型
    models = summarizer.find_all_models()
    
    if not models:
        print("没有找到可用的本地模型，无法进行测试")
        return
        
    print(f"找到 {len(models)} 个本地模型:")
    for i, model in enumerate(models, 1):
        print(f"{i}. {model['name']} ({model['series']})")
    
    # 加载第一个模型
    print(f"\n正在加载模型: {models[0]['name']}...")
    if not summarizer.load_model(models[0]['path']):
        print("模型加载失败，无法进行测试")
        return
        
    print(f"模型加载成功: {models[0]['name']}")
    
    # 测试文本
    test_text = """人工智能(AI)是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。人工智能是研究、开发用于模拟、延伸和扩展人的智能的理论、方法、技术及应用系统的一门新的技术科学。"""
    
    print(f"\n原文 ({len(test_text)}字符):\n{test_text}\n")
    
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
    test_ollama_summarizer() 