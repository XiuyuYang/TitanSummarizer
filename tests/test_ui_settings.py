#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UI设置单元测试
"""

import os
import sys
import unittest
import tkinter as tk
from unittest.mock import patch, MagicMock

# 确保src目录在路径中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestUISettings(unittest.TestCase):
    """UI设置单元测试类"""
    
    @patch('src.ui.main_ui.os.path.exists')
    @patch('src.ui.main_ui.read_text_file')
    def test_default_summary_length(self, mock_read_text_file, mock_exists):
        """测试默认摘要长度是否为200"""
        # 导入UI类
        from src.ui.main_ui import TitanUI
        
        # 模拟文件存在检查
        mock_exists.return_value = True
        mock_read_text_file.return_value = "测试内容"
        
        # 创建Tkinter根窗口
        root = tk.Tk()
        try:
            # 创建UI实例
            ui = TitanUI(root)
            
            # 检查默认摘要长度值
            self.assertEqual(ui.summary_length_var.get(), "200")
            
            # 验证设置中的默认长度
            self.assertEqual(ui.settings.get("default_length"), 200)
            
        finally:
            # 清理窗口
            root.destroy()
    
    @patch('src.ui.main_ui.messagebox.showwarning')
    def test_validate_length(self, mock_showwarning):
        """测试摘要长度验证"""
        # 导入UI类
        from src.ui.main_ui import TitanUI
        
        # 创建Tkinter根窗口
        root = tk.Tk()
        try:
            # 创建UI实例
            ui = TitanUI(root)
            
            # 测试有效长度
            ui.summary_length_var.set("300")
            ui.validate_length(None)
            self.assertEqual(ui.summary_length_var.get(), "300")
            
            # 测试无效长度（负数）
            ui.summary_length_var.set("-100")
            ui.validate_length(None)
            self.assertEqual(ui.summary_length_var.get(), "100")
            
            # 测试超过最大值
            ui.summary_length_var.set("3000")
            ui.validate_length(None)
            self.assertEqual(ui.summary_length_var.get(), "2000")
            mock_showwarning.assert_called_once()
            
            # 测试非数字
            mock_showwarning.reset_mock()
            ui.summary_length_var.set("abc")
            ui.validate_length(None)
            self.assertEqual(ui.summary_length_var.get(), "500")
            mock_showwarning.assert_called_once()
            
        finally:
            # 清理窗口
            root.destroy()
    
    @patch('src.ui.main_ui.os.path.exists')
    @patch('src.ui.main_ui.json.load')
    @patch('builtins.open')
    def test_load_settings(self, mock_open, mock_json_load, mock_exists):
        """测试加载设置"""
        # 导入UI类
        from src.ui.main_ui import TitanUI
        
        # 模拟设置文件存在
        mock_exists.return_value = True
        
        # 模拟JSON加载
        mock_settings = {
            "default_model": "ollama-local",
            "default_length": 200,
            "api_key": "test-key",
            "theme": "clam"
        }
        mock_json_load.return_value = mock_settings
        
        # 创建Tkinter根窗口
        root = tk.Tk()
        try:
            # 创建UI实例
            ui = TitanUI(root)
            
            # 验证设置是否正确加载
            self.assertEqual(ui.settings, mock_settings)
            self.assertEqual(ui.settings.get("default_length"), 200)
            
        finally:
            # 清理窗口
            root.destroy()
    
    @patch('src.ui.main_ui.os.path.exists')
    @patch('src.ui.main_ui.logging.warning')
    def test_load_settings_fallback(self, mock_warning, mock_exists):
        """测试设置加载失败时的默认值"""
        # 导入UI类
        from src.ui.main_ui import TitanUI
        
        # 模拟设置文件不存在
        mock_exists.return_value = False
        
        # 创建Tkinter根窗口
        root = tk.Tk()
        try:
            # 创建UI实例
            ui = TitanUI(root)
            
            # 验证使用了默认设置
            self.assertEqual(ui.settings.get("default_model"), "deepseek-api")
            self.assertEqual(ui.settings.get("default_length"), 200)
            self.assertIsNone(ui.settings.get("api_key"))
            
            # 验证发出了警告日志
            mock_warning.assert_called_once()
            
        finally:
            # 清理窗口
            root.destroy()

if __name__ == "__main__":
    unittest.main() 