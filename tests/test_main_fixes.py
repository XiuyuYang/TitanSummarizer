#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试我们修复的关键问题
"""

import os
import sys
import unittest
import tkinter as tk
from unittest.mock import patch, MagicMock

# 确保src目录在路径中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestMainFixes(unittest.TestCase):
    """测试我们修复的关键问题"""
    
    @patch('src.ui.main_ui.os.path.exists')
    @patch('src.ui.main_ui.os.path.basename')
    @patch('src.ui.main_ui.read_text_file')
    def test_chapter_list_label(self, mock_read_text, mock_basename, mock_exists):
        """测试章节列表标签是否更改为'章节列表'"""
        from src.ui.main_ui import TitanUI
        
        # 模拟文件存在和读取
        mock_exists.return_value = True
        mock_basename.return_value = "test.txt"
        mock_read_text.return_value = "测试内容"
        
        # 创建Tkinter根窗口
        root = tk.Tk()
        try:
            # 创建UI实例
            ui = TitanUI(root)
            
            # 获取所有LabelFrame
            all_frames = root.winfo_children()
            label_frames = []
            
            # 递归查找所有LabelFrame
            def find_labelframes(widget):
                if widget.winfo_class() == 'TLabelframe':
                    label_frames.append(widget)
                for child in widget.winfo_children():
                    find_labelframes(child)
            
            for widget in all_frames:
                find_labelframes(widget)
            
            # 检查是否有标签为"章节列表"的LabelFrame
            chapter_list_frame = None
            for frame in label_frames:
                label_text = frame.cget('text')
                if label_text == "章节列表":
                    chapter_list_frame = frame
                    break
            
            # 验证找到了章节列表框架
            self.assertIsNotNone(chapter_list_frame, "未找到'章节列表'标签的框架")
            
        finally:
            # 清理窗口
            root.destroy()
    
    @patch('src.ui.main_ui.os.path.exists')
    @patch('src.ui.main_ui.read_text_file')
    def test_default_summary_length(self, mock_read_text, mock_exists):
        """测试默认摘要长度是否为200"""
        from src.ui.main_ui import TitanUI
        
        # 模拟文件不存在，以使用默认设置
        mock_exists.return_value = False
        mock_read_text.return_value = "测试内容"
        
        # 创建Tkinter根窗口
        root = tk.Tk()
        try:
            # 创建UI实例
            ui = TitanUI(root)
            
            # 验证默认摘要长度为200
            self.assertEqual(ui.summary_length_var.get(), "200", "默认摘要长度不是200")
            self.assertEqual(ui.settings.get("default_length"), 200, "设置中的默认长度不是200")
            
        finally:
            # 清理窗口
            root.destroy()
    
    def test_file_encoding(self):
        """测试文件编码处理"""
        from src.utils.file_utils import read_text_file
        
        # 创建一个临时的UTF-8编码文件和GBK编码文件
        import tempfile
        import os
        
        temp_dir = tempfile.mkdtemp()
        try:
            # UTF-8文件
            utf8_file = os.path.join(temp_dir, "utf8_test.txt")
            with open(utf8_file, 'w', encoding='utf-8') as f:
                f.write("这是UTF-8编码的测试文件")
            
            # GBK文件
            gbk_file = os.path.join(temp_dir, "gbk_test.txt")
            with open(gbk_file, 'w', encoding='gbk') as f:
                f.write("这是GBK编码的测试文件")
            
            # 测试UTF-8文件读取
            content_utf8 = read_text_file(utf8_file)
            self.assertEqual(content_utf8, "这是UTF-8编码的测试文件", "UTF-8文件读取失败")
            
            # 测试GBK文件读取
            content_gbk = read_text_file(gbk_file)
            self.assertEqual(content_gbk, "这是GBK编码的测试文件", "GBK文件读取失败")
            
            # 测试明确指定编码
            content_utf8_explicit = read_text_file(utf8_file, encoding='utf-8')
            self.assertEqual(content_utf8_explicit, "这是UTF-8编码的测试文件", "明确指定UTF-8编码读取失败")
            
            content_gbk_explicit = read_text_file(gbk_file, encoding='gbk')
            self.assertEqual(content_gbk_explicit, "这是GBK编码的测试文件", "明确指定GBK编码读取失败")
            
        finally:
            # 清理临时目录
            import shutil
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    unittest.main() 