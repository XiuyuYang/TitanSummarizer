#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试文件读取功能
"""

from src.utils.file_utils import read_text_file

# 测试自动检测编码
content = read_text_file("test_gbk_encoded.txt")
print("自动检测编码读取结果：")
print(content)
print("-" * 50)

# 测试指定编码
content = read_text_file("test_gbk_encoded.txt", encoding="gbk")
print("指定GBK编码读取结果：")
print(content)
print("-" * 50)

# 测试错误编码处理
content = read_text_file("test_gbk_encoded.txt", encoding="ascii")
print("指定ASCII编码读取结果（应该自动修正）：")
print(content) 