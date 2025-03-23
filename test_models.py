#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试TitanSummarizer能够找到的模型文件
"""

from src.api.ollama_api import OllamaAPI

def main():
    """主函数"""
    print("正在搜索模型文件...")
    api = OllamaAPI()
    models = api.find_all_models()
    
    print(f"\n找到 {len(models)} 个模型文件：")
    for i, model in enumerate(models[:10], 1):  # 只显示前10个
        print(f"{i}. {model['name']} - {model['path']}")
    
    print("\n测试成功完成！")

if __name__ == "__main__":
    main() 