#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Titan小说摘要器 - 启动脚本

使用MVC架构重构后的启动入口，加载UI和功能模块
"""

import tkinter as tk
import sys
import os

# 检查必要的依赖模块是否存在
required_modules = [
    "titan_ui", 
    "core.summarizer",
    "core.api.ollama_api",
    "core.api.deepseek_api"
]

missing_modules = []
for module in required_modules:
    try:
        __import__(module)
    except ImportError:
        missing_modules.append(module)

if missing_modules:
    print(f"错误: 缺少以下必要模块: {', '.join(missing_modules)}")
    print("请确保所有必要的模块文件都在当前目录中")
    sys.exit(1)

# 导入主UI类
from titan_ui import TitanUI

def main():
    """主函数"""
    # 创建主窗口
    root = tk.Tk()
    
    # 设置窗口图标（如果存在）
    if os.path.exists("icon.ico"):
        root.iconbitmap("icon.ico")
    
    # 创建应用实例
    app = TitanUI(root)
    
    # 进入主循环
    root.mainloop()

if __name__ == "__main__":
    main()