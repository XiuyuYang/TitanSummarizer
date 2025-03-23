#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Titan摘要器 - 程序入口模块
"""

import os
import sys
import argparse
import logging
import tkinter as tk

# 确保src目录在路径中
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("titan.log", encoding="utf-8", mode="w"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("titan")

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Titan摘要器 - 文本摘要工具")
    
    parser.add_argument("--cli", action="store_true", help="使用命令行界面而不是图形界面")
    parser.add_argument("--text", type=str, help="要摘要的文本")
    parser.add_argument("--file", type=str, help="要摘要的文件路径")
    parser.add_argument("--dir", type=str, help="要摘要的目录路径")
    parser.add_argument("--output", type=str, help="输出文件或目录的路径")
    parser.add_argument("--model", type=str, default="deepseek-api", 
                       help="使用的模型类型 (deepseek-api 或 ollama-local)")
    parser.add_argument("--api-key", type=str, help="API密钥（用于DeepSeek API）")
    parser.add_argument("--model-path", type=str, help="本地模型文件路径（用于ollama-local模型）")
    parser.add_argument("--max-length", type=int, default=200, help="摘要的最大长度")
    parser.add_argument("--mode", type=str, default="generative", 
                       choices=["extractive", "generative"], help="摘要模式")
    
    return parser.parse_args()

def run_cli_mode(args):
    """运行命令行模式"""
    from titan_summarizer import main
    logger.info("启动命令行模式")
    sys.argv = [sys.argv[0]]  # 清除已处理的参数
    
    # 添加必要的参数
    if args.text:
        sys.argv.extend(["--text", args.text])
    if args.file:
        sys.argv.extend(["--file", args.file])
    if args.dir:
        sys.argv.extend(["--dir", args.dir])
    if args.output:
        sys.argv.extend(["--output", args.output])
    if args.model:
        sys.argv.extend(["--model", args.model])
    if args.api_key:
        sys.argv.extend(["--api-key", args.api_key])
    if args.model_path:
        sys.argv.extend(["--model-path", args.model_path])
    if args.max_length:
        sys.argv.extend(["--max-length", str(args.max_length)])
    if args.mode:
        sys.argv.extend(["--mode", args.mode])
        
    # 运行命令行模式
    main()

def run_gui_mode():
    """运行图形界面模式"""
    logger.info("启动图形界面模式")
    from ui.main_ui import TitanUI
    
    root = tk.Tk()
    app = TitanUI(root)
    root.mainloop()

def main():
    """主函数"""
    logger.info("Titan摘要器启动")
    
    # 解析命令行参数
    args = parse_args()
    
    # 根据参数决定运行模式
    if args.cli or args.text or args.file or args.dir:
        run_cli_mode(args)
    else:
        run_gui_mode()

if __name__ == "__main__":
    main() 