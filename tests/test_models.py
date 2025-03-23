#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
摘要模型测试模块
测试各种摘要模型的功能
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# 添加src目录到path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入测试目标
from src.models.summarizer import BaseSummarizer
from src.models.deepseek_summarizer import DeepSeekSummarizer
from src.models.ollama_summarizer import OllamaSummarizer
from src.models.factory import SummarizerFactory

class TestBaseSummarizer(unittest.TestCase):
    """测试摘要器基类"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 创建一个BaseSummarizer的子类以便测试
        class TestSummarizer(BaseSummarizer):
            def _generative_summarize(self, text, max_length=200, callback=None, file_percentage=0):
                return f"生成式摘要: {text[:50]}..."
                
        self.summarizer = TestSummarizer()
        
    def test_extractive_summarize(self):
        """测试提取式摘要功能"""
        test_text = "这是第一句测试文本。这是第二句测试文本。这是第三句测试文本。这是第四句测试文本。"
        summary = self.summarizer._extractive_summarize(test_text, max_length=100)
        
        # 确保生成了摘要
        self.assertIsNotNone(summary)
        self.assertGreater(len(summary), 0)
        self.assertLessEqual(len(summary), 100)
        
    def test_generate_summary_extractive(self):
        """测试生成提取式摘要"""
        test_text = "这是第一句测试文本。这是第二句测试文本。这是第三句测试文本。"
        summary = self.summarizer.generate_summary(test_text, max_length=100, summary_mode="extractive")
        
        # 确保生成了摘要
        self.assertIsNotNone(summary)
        self.assertGreater(len(summary), 0)
        self.assertLessEqual(len(summary), 100)
        
    def test_generate_summary_generative(self):
        """测试生成生成式摘要"""
        test_text = "这是测试文本，用于测试生成式摘要功能。"
        summary = self.summarizer.generate_summary(test_text, max_length=100, summary_mode="generative")
        
        # 确保生成了摘要
        self.assertIsNotNone(summary)
        self.assertGreater(len(summary), 0)
        self.assertLessEqual(len(summary), 100)
        self.assertTrue(summary.startswith("生成式摘要:"))
        
    def test_empty_text(self):
        """测试空文本的处理"""
        summary = self.summarizer.generate_summary("", max_length=100)
        self.assertEqual(summary, "无法生成摘要：文本为空")
        
        summary = self.summarizer.generate_summary("   ", max_length=100)
        self.assertEqual(summary, "无法生成摘要：文本为空")

class TestDeepSeekSummarizer(unittest.TestCase):
    """测试DeepSeek摘要器"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 创建一个模拟的API类
        self.mock_api = MagicMock()
        self.mock_api.summarize_text.return_value = "这是模拟的摘要结果"
        
        # 使用模拟API类创建摘要器
        with patch('src.models.deepseek_summarizer.DeepSeekAPI', return_value=self.mock_api):
            self.summarizer = DeepSeekSummarizer(use_mock=True)
    
    def test_generative_summarize(self):
        """测试生成式摘要功能"""
        test_text = "这是测试文本，用于测试DeepSeek摘要器的生成式摘要功能。"
        summary = self.summarizer._generative_summarize(test_text, max_length=100)
        
        # 确保API被正确调用
        self.mock_api.summarize_text.assert_called_once()
        # 确保返回了模拟的摘要结果
        self.assertEqual(summary, "这是模拟的摘要结果")
        
    def test_translate_text(self):
        """测试翻译功能"""
        test_text = "你好，这是测试文本。"
        # 设置模拟返回值
        self.mock_api.summarize_text.return_value = "Hello, this is test text."
        
        translated = self.summarizer.translate_text(test_text, target_language="English")
        
        # 确保API被正确调用
        self.mock_api.summarize_text.assert_called()
        # 确保返回了模拟的翻译结果
        self.assertEqual(translated, "Hello, this is test text.")

class TestSummarizerFactory(unittest.TestCase):
    """测试摘要器工厂"""
    
    def test_create_deepseek_summarizer(self):
        """测试创建DeepSeek摘要器"""
        with patch('src.models.factory.DeepSeekSummarizer') as mock_deepseek:
            # 设置模拟返回值
            mock_instance = MagicMock()
            mock_deepseek.return_value = mock_instance
            
            # 创建摘要器
            summarizer = SummarizerFactory.create_summarizer(model_type="deepseek-api", use_mock=True)
            
            # 确保正确创建了DeepSeek摘要器
            mock_deepseek.assert_called_once()
            self.assertEqual(summarizer, mock_instance)
    
    def test_create_ollama_summarizer(self):
        """测试创建Ollama摘要器"""
        with patch('src.models.factory.OllamaSummarizer') as mock_ollama:
            # 设置模拟返回值
            mock_instance = MagicMock()
            mock_ollama.return_value = mock_instance
            
            # 创建摘要器
            summarizer = SummarizerFactory.create_summarizer(
                model_type="ollama-local", 
                model_path="test/model/path"
            )
            
            # 确保正确创建了Ollama摘要器
            mock_ollama.assert_called_once()
            self.assertEqual(summarizer, mock_instance)
    
    def test_unsupported_model_type(self):
        """测试不支持的模型类型"""
        with patch('src.models.factory.DeepSeekSummarizer') as mock_deepseek:
            # 设置模拟返回值
            mock_instance = MagicMock()
            mock_deepseek.return_value = mock_instance
            
            # 创建摘要器，使用不支持的类型
            summarizer = SummarizerFactory.create_summarizer(model_type="unsupported-model")
            
            # 确保默认使用DeepSeek摘要器
            mock_deepseek.assert_called_once()
            self.assertEqual(summarizer, mock_instance)
    
    def test_get_available_models(self):
        """测试获取可用模型列表"""
        models = SummarizerFactory.get_available_models()
        
        # 确保返回了预期的模型列表
        self.assertIn("deepseek-api", models)
        self.assertIn("ollama-local", models)
        self.assertEqual(models["deepseek-api"], "DeepSeek API(在线)")
        self.assertEqual(models["ollama-local"], "Ollama(本地模型)")

if __name__ == '__main__':
    unittest.main() 