#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
模型工厂单元测试
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# 确保src目录在路径中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.factory import SummarizerFactory

class TestSummarizerFactory(unittest.TestCase):
    """摘要模型工厂单元测试类"""
    
    def test_get_available_models(self):
        """测试获取可用模型"""
        models = SummarizerFactory.get_available_models()
        
        # 验证返回的模型字典
        self.assertIsInstance(models, dict)
        self.assertIn("deepseek-api", models)
        self.assertIn("ollama-local", models)
        
    @patch('src.models.deepseek_summarizer.DeepSeekSummarizer.__init__', return_value=None)
    @patch('src.models.deepseek_summarizer.DeepSeekSummarizer.__new__', return_value=MagicMock())
    def test_create_deepseek_summarizer(self, mock_new, mock_init):
        """测试创建DeepSeek摘要器"""
        # 创建工厂实例
        factory = SummarizerFactory()
        
        # 测试创建摘要器
        api_key = "test-api-key"
        progress_callback = MagicMock()
        
        summarizer = factory.create_summarizer(
            model_type="deepseek-api",
            api_key=api_key,
            use_mock=True,
            progress_callback=progress_callback
        )
        
        # 验证摘要器创建和参数传递
        mock_init.assert_called_once_with(
            api_key=api_key,
            use_mock=True,
            progress_callback=progress_callback
        )
        
    @patch('src.models.ollama_summarizer.OllamaSummarizer.__init__', return_value=None)
    @patch('src.models.ollama_summarizer.OllamaSummarizer.__new__', return_value=MagicMock())
    def test_create_ollama_summarizer(self, mock_new, mock_init):
        """测试创建Ollama摘要器"""
        # 创建工厂实例
        factory = SummarizerFactory()
        
        # 测试创建摘要器
        model_path = "D:\\Models\\test-model.gguf"
        progress_callback = MagicMock()
        
        summarizer = factory.create_summarizer(
            model_type="ollama-local",
            model_path=model_path,
            progress_callback=progress_callback
        )
        
        # 验证参数传递
        mock_init.assert_called_once_with(
            model_path=model_path,
            progress_callback=progress_callback
        )
    
    def test_unsupported_model_type(self):
        """测试不支持的模型类型"""
        factory = SummarizerFactory()
        
        # 验证抛出异常
        with self.assertRaises(ValueError):
            factory.create_summarizer("unsupported-model")
    
    @patch('src.models.factory.BaseSummarizer')
    def test_register_model(self, MockBaseSummarizer):
        """测试注册新的模型类型"""
        # 注册新模型类型
        SummarizerFactory.register_model("test-model", MockBaseSummarizer)
        
        # 验证模型已注册
        self.assertIn("test-model", SummarizerFactory._models)
        self.assertEqual(SummarizerFactory._models["test-model"], MockBaseSummarizer)
        
        # 清理，移除测试用的模型类型
        if "test-model" in SummarizerFactory._models:
            del SummarizerFactory._models["test-model"]

if __name__ == "__main__":
    unittest.main() 