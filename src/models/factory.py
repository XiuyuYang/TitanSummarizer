#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
摘要模型工厂
用于创建和管理不同类型的摘要模型
"""

import logging
from typing import Optional, Callable, Dict, Type, Any

from src.models.summarizer import BaseSummarizer, get_model_name
from src.models.deepseek_summarizer import DeepSeekSummarizer
from src.models.ollama_summarizer import OllamaSummarizer

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SummarizerFactory:
    """
    摘要模型工厂类，负责创建不同类型的摘要模型实例
    """
    
    # 注册的摘要模型类
    _models: Dict[str, Type[BaseSummarizer]] = {
        "deepseek-api": DeepSeekSummarizer,
        "ollama-local": OllamaSummarizer
    }
    
    def create_summarizer(
        self,
        model_type: str,
        model_path: Optional[str] = None,
        api_key: Optional[str] = None,
        use_mock: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> BaseSummarizer:
        """
        创建摘要器实例
        
        Args:
            model_type: 模型类型名称
            model_path: 模型路径(用于Ollama本地模型)
            api_key: API密钥(用于DeepSeek API)
            use_mock: 是否使用模拟模式
            progress_callback: 进度回调函数
            
        Returns:
            BaseSummarizer实例
        """
        # 记录正在创建的模型类型
        logger.info(f"创建摘要模型: {model_type}")
        
        if model_type not in self._models:
            raise ValueError(f"不支持的模型类型: {model_type}，可用类型: {list(self._models.keys())}")
            
        model_class = self._models[model_type]
        
        # 根据模型类型创建对应的实例
        if model_type == "deepseek-api":
            return model_class(
                api_key=api_key,
                use_mock=use_mock,
                progress_callback=progress_callback
            )
        elif model_type == "ollama-local":
            return model_class(
                model_path=model_path,
                progress_callback=progress_callback
            )
        else:
            # 默认情况下传递所有参数
            return model_class(
                progress_callback=progress_callback
            )
    
    @classmethod
    def register_model(cls, model_name: str, model_class: Type[BaseSummarizer]) -> None:
        """
        注册新的摘要模型类型
        
        Args:
            model_name: 模型类型名称
            model_class: 模型类
        """
        cls._models[model_name] = model_class
        logger.info(f"注册摘要模型类型: {model_name}")
    
    @classmethod
    def get_available_models(cls) -> Dict[str, str]:
        """
        获取所有可用的模型类型
        
        Returns:
            模型类型字典，键为模型ID，值为模型显示名称
        """
        return {
            "deepseek-api": "DeepSeek API(在线)",
            "ollama-local": "Ollama(本地模型)"
        }

# 测试代码
def test_summarizer_factory():
    """测试摘要模型工厂"""
    
    print("===== 摘要模型工厂测试 =====")
    
    # 获取可用模型类型
    available_models = SummarizerFactory.get_available_models()
    print("可用的模型类型:")
    for model_id, model_name in available_models.items():
        print(f"- {model_id}: {model_name}")
    
    # 创建DeepSeek API模型
    print("\n创建DeepSeek API模型...")
    deepseek_summarizer = SummarizerFactory.create_summarizer(
        model_type="deepseek-api",
        use_mock=True
    )
    print(f"创建的模型类型: {type(deepseek_summarizer).__name__}")
    
    # 创建Ollama本地模型
    print("\n创建Ollama本地模型...")
    ollama_summarizer = SummarizerFactory.create_summarizer(
        model_type="ollama-local"
    )
    print(f"创建的模型类型: {type(ollama_summarizer).__name__}")
    
    # 测试摘要生成
    test_text = "人工智能(AI)是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。"
    
    print("\n使用DeepSeek API生成摘要:")
    summary = deepseek_summarizer.generate_summary(test_text, max_length=50)
    print(f"摘要: {summary}")

if __name__ == "__main__":
    test_summarizer_factory() 