#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试运行器
用于运行所有单元测试
"""

import os
import sys
import unittest
import importlib
import logging
import argparse

# 确保src目录在路径中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_runner")

def discover_tests(test_pattern="test_*.py", skip_modules=None):
    """
    发现测试模块
    
    Args:
        test_pattern: 测试文件匹配模式
        skip_modules: 需要跳过的模块列表
        
    Returns:
        测试模块列表
    """
    if skip_modules is None:
        skip_modules = ["test_deepseek_api.py", "test_deepseek_summarizer.py"]
        
    # 获取测试目录
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 查找所有测试文件
    test_files = []
    for file in os.listdir(test_dir):
        if file.endswith(".py") and file.startswith("test_"):
            if file not in skip_modules:
                test_files.append(file)
                
    logger.info(f"发现 {len(test_files)} 个测试文件")
    return test_files

def run_all_tests(skip_modules=None):
    """
    运行所有单元测试
    
    Args:
        skip_modules: 需要跳过的模块列表
        
    Returns:
        布尔值，表示测试是否全部通过
    """
    # 发现测试文件
    test_files = discover_tests(skip_modules=skip_modules)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试模块到套件
    for test_file in test_files:
        module_name = test_file[:-3]  # 移除.py扩展名
        
        try:
            # 导入测试模块
            module = importlib.import_module(f"tests.{module_name}")
            
            # 加载测试
            tests = unittest.defaultTestLoader.loadTestsFromModule(module)
            test_suite.addTest(tests)
            
            logger.info(f"已加载测试模块: {module_name}")
        except Exception as e:
            logger.error(f"加载测试模块 {module_name} 失败: {str(e)}")
    
    # 运行测试
    print("=" * 70)
    print("开始运行单元测试")
    print("=" * 70)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 输出测试结果
    print("\n" + "=" * 70)
    print(f"测试结果: 运行 {result.testsRun} 个测试")
    print(f"通过: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 70)
    
    # 输出失败的测试
    if result.failures:
        print("\n失败的测试:")
        for test, trace in result.failures:
            print(f"- {test}")
    
    # 输出错误的测试
    if result.errors:
        print("\n错误的测试:")
        for test, trace in result.errors:
            print(f"- {test}")
    
    # 返回是否全部通过
    return (len(result.failures) + len(result.errors)) == 0

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="运行Titan摘要器单元测试")
    parser.add_argument("--skip-modules", type=str, default="test_deepseek_api.py,test_deepseek_summarizer.py",
                        help="要跳过的测试模块列表，用逗号分隔")
    
    args = parser.parse_args()
    
    # 获取要跳过的模块列表
    skip_modules = args.skip_modules.split(",") if args.skip_modules else None
    
    # 运行测试
    success = run_all_tests(skip_modules=skip_modules)
    
    # 退出码反映测试结果
    sys.exit(0 if success else 1) 