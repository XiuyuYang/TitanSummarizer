#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
创建一个GBK编码的文件
"""

content = """这是GBK编码的测试文件。
这里包含一些中文字符：你好，世界！
测试文件编码：GBK"""

with open("test_gbk_encoded.txt", "w", encoding="gbk") as f:
    f.write(content)

print("已成功创建GBK编码的测试文件：test_gbk_encoded.txt") 