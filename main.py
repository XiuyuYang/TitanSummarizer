#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TitanSummarizer主程序入口点
可以通过命令行参数选择运行主程序或测试

使用示例:
    # 运行图形界面
    python main.py

    # 运行命令行界面，处理文本
    python main.py --cli --text "要摘要的文本内容" --summary-type extractive

    # 运行命令行界面，处理文件
    python main.py --cli --file path/to/file.txt --output path/to/output.md

    # 运行命令行界面，处理目录
    python main.py --cli --dir path/to/directory --output path/to/output_dir

    # 指定使用的模型
    python main.py --cli --file path/to/file.txt --model deepseek-api --api-key your_api_key

    # 指定本地GGUF模型文件路径
    python main.py --cli --file path/to/file.txt --model ollama-local --model-path D:/Work/AI_Models/your_model.gguf

    # 运行测试
    python main.py --mode test
"""

import os
import sys
import argparse

def run_main_program():
    """运行Titan摘要器主程序"""
    print("=" * 70)
    print("启动Titan摘要器主程序")
    print("=" * 70)
    
    # 导入并运行src模块的main函数
    from src.__main__ import main
    main()

def run_tests():
    """运行单元测试"""
    # 导入并运行测试模块的run_all_tests函数
    from tests.run_tests import run_all_tests
    success = run_all_tests()
    
    # 退出码反映测试结果
    sys.exit(0 if success else 1)

def main():
    """主函数，解析命令行参数并运行相应功能"""
    parser = argparse.ArgumentParser(
        description="Titan摘要器 - 文本摘要工具",
        epilog="""
示例：
  # 运行图形界面
  python main.py

  # 运行命令行界面，处理文本
  python main.py --cli --text "要摘要的文本内容" --summary-type extractive

  # 指定本地GGUF模型文件路径
  python main.py --cli --file path/to/file.txt --model ollama-local --model-path D:/Work/AI_Models/your_model.gguf

  # 运行测试
  python main.py --mode test
"""
    )
    
    # 基本操作模式
    parser.add_argument("--mode", choices=["run", "test"], default="run",
                       help="运行模式：'run'运行主程序，'test'运行测试套件")
    
    # 主程序参数（当mode=run时使用）
    parser.add_argument("--cli", action="store_true", help="使用命令行界面而不是图形界面")
    parser.add_argument("--text", type=str, help="要摘要的文本")
    parser.add_argument("--file", type=str, help="要摘要的文件路径")
    parser.add_argument("--dir", type=str, help="要摘要的目录路径")
    parser.add_argument("--output", type=str, help="输出文件或目录的路径")
    parser.add_argument("--model", type=str, help="使用的模型类型（deepseek-api或ollama-local）")
    parser.add_argument("--api-key", type=str, help="API密钥（用于DeepSeek API）")
    parser.add_argument("--model-path", type=str, help="本地模型文件路径（用于ollama-local模型）")
    parser.add_argument("--max-length", type=int, default=200, help="摘要的最大长度")
    parser.add_argument("--summary-type", choices=["extractive", "generative"], 
                       help="摘要模式（extractive或generative）")
    
    # 测试参数（当mode=test时使用）
    parser.add_argument("--test-pattern", type=str, default="test_*.py",
                       help="测试文件匹配模式")
    
    args = parser.parse_args()
    
    # 如果指定了与主程序相关的任何参数，则默认为运行模式
    if any([args.cli, args.text, args.file, args.dir, args.output, args.model, 
            args.api_key, args.max_length, args.summary_type, args.model_path]):
        args.mode = "run"
    
    # 根据模式运行相应功能
    if args.mode == "run":
        # 注意：先清除已处理的sys.argv，避免参数重复
        sys.argv = [sys.argv[0]]
        
        # 将参数传递给src模块
        if args.cli:
            sys.argv.append("--cli")
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
        if args.summary_type:
            sys.argv.extend(["--mode", args.summary_type])
            
        run_main_program()
    else:
        run_tests()

if __name__ == "__main__":
    main() 