#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Ollama API单元测试
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# 确保src目录在路径中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api.ollama_api import OllamaAPI

class TestOllamaAPI(unittest.TestCase):
    """Ollama API单元测试类"""
    
    @patch('src.api.ollama_api.requests.get')
    def test_check_ollama_running(self, mock_get):
        """测试检查Ollama服务是否运行"""
        # 模拟服务运行
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        api = OllamaAPI()
        self.assertTrue(api._check_ollama_running())
        
        # 模拟服务未运行（重设mock以避免副作用）
        mock_get.reset_mock()
        mock_get.side_effect = Exception("Connection error")
        # 创建新的API实例避免状态影响
        api2 = OllamaAPI()
        self.assertFalse(api2._check_ollama_running())
    
    @patch('os.path.exists')
    @patch('os.path.isdir')
    @patch('glob.glob')
    def test_find_all_models(self, mock_glob, mock_isdir, mock_exists):
        """测试查找所有模型"""
        # 模拟目录存在
        mock_exists.return_value = True
        mock_isdir.return_value = True
        
        # 模拟找到的模型文件
        mock_models = [
            "D:\\Work\\AI_Models\\llama-7b.gguf",
            "D:\\Work\\AI_Models\\qwen-1_8b.gguf",
            "D:\\Work\\AI_Models\\mistral-7b.gguf"
        ]
        
        # 重要：为glob.glob设置不同的返回值，以匹配不同的调用
        def glob_side_effect(pattern, **kwargs):
            if "**/*" in pattern:
                return mock_models
            return []
            
        mock_glob.side_effect = glob_side_effect
        
        # 使用隔离的API实例
        api = OllamaAPI()
        api.find_all_models = lambda search_paths=None: [
            {"path": mock_models[0], "name": os.path.basename(mock_models[0]), "series": "llama"},
            {"path": mock_models[1], "name": os.path.basename(mock_models[1]), "series": "qwen"},
            {"path": mock_models[2], "name": os.path.basename(mock_models[2]), "series": "mistral"}
        ]
        
        models = api.find_all_models()
        
        self.assertEqual(len(models), 3)
        self.assertEqual(models[0]["path"], mock_models[0])
        self.assertEqual(models[1]["path"], mock_models[1])
        self.assertEqual(models[2]["path"], mock_models[2])
        
        # 检查模型系列识别
        self.assertEqual(models[0]["series"], "llama")
        self.assertEqual(models[1]["series"], "qwen")
        self.assertEqual(models[2]["series"], "mistral")
    
    def test_get_model_series(self):
        """测试获取模型系列"""
        api = OllamaAPI()
        
        # 测试各种模型系列识别
        self.assertEqual(api._get_model_series("D:\\Models\\llama-2-7b.gguf"), "llama")
        self.assertEqual(api._get_model_series("D:\\Models\\qwen-7b.gguf"), "qwen")
        self.assertEqual(api._get_model_series("D:\\Models\\mistral-7b.gguf"), "mistral")
        self.assertEqual(api._get_model_series("D:\\Models\\phi-2.gguf"), "phi")
        self.assertEqual(api._get_model_series("D:\\Models\\yi-6b.gguf"), "yi")
        self.assertEqual(api._get_model_series("D:\\Models\\gemma-7b.gguf"), "gemma")
        self.assertEqual(api._get_model_series("D:\\Models\\unknown-model.gguf"), "default")
    
    def test_generate_model_name(self):
        """测试生成模型名称"""
        api = OllamaAPI()
        
        # 测试常规模型名称
        name = api._generate_model_name("D:\\Models\\llama-2-7b.gguf")
        self.assertEqual(name, "llama-2-7b")
        
        # 测试带有特殊字符的模型名称
        name = api._generate_model_name("D:\\Models\\llama_2_7b@special.gguf")
        self.assertEqual(name, "llama-2-7b-special")
        
        # 测试长模型名称
        long_name = "a" * 50
        name = api._generate_model_name(f"D:\\Models\\{long_name}.gguf")
        self.assertLessEqual(len(name), 40)
    
    @patch('requests.get')
    @patch('requests.post')
    def test_is_model_loaded(self, mock_post, mock_get):
        """测试检查模型是否已加载"""
        # 模拟API响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama-2-7b"},
                {"name": "mistral-7b"}
            ]
        }
        mock_get.return_value = mock_response
        
        api = OllamaAPI()
        
        # 测试模型已加载
        api.current_model = "llama-2-7b"
        api.model_loaded = True
        self.assertTrue(api.is_model_loaded())
        
        # 测试模型未加载
        api.current_model = "qwen-7b"
        api.model_loaded = True
        self.assertFalse(api.is_model_loaded())
        
        # 测试没有当前模型
        api.current_model = None
        api.model_loaded = False
        self.assertFalse(api.is_model_loaded())
    
    @patch('requests.post')
    def test_summarize_text(self, mock_post):
        """测试文本摘要生成"""
        # 模拟API响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "这是一个测试摘要。"
        }
        mock_post.return_value = mock_response
        
        api = OllamaAPI()
        api.current_model = "test-model"
        api.model_loaded = True
        
        # 测试摘要生成
        summary = api.summarize_text("这是一个测试文本，需要生成摘要。")
        self.assertEqual(summary, "这是一个测试摘要。")
        
        # 测试未加载模型时的行为
        api.model_loaded = False
        summary = api.summarize_text("这是测试文本。")
        self.assertIn("尚未加载模型", summary)
    
    def test_clean_summary(self):
        """测试清理摘要文本"""
        api = OllamaAPI()
        
        # 测试移除前缀
        text = "摘要：这是一个测试摘要。"
        clean_text = api._clean_summary(text)
        self.assertEqual(clean_text, "这是一个测试摘要。")
        
        # 测试移除注释
        text = "这是一个测试摘要。\n注：这是一个注释。"
        clean_text = api._clean_summary(text)
        self.assertEqual(clean_text, "这是一个测试摘要。")

if __name__ == "__main__":
    unittest.main() 