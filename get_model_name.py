#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
模型名称映射模块
提供模型名称的映射和处理功能
"""

# 模型名称到实际模型位置的映射
MODELS = {
    # 中文ALBERT模型
    "tiny": "clue/albert_chinese_tiny",
    "small": "clue/albert_chinese_small",
    "base": "clue/albert_chinese_base",
    
    # GPT系列模型
    "gpt2-small": "distilgpt2",
    
    # MT5模型
    "mt5-small": "google/mt5-small",
    "mt5-base": "google/mt5-base",
    
    # 常用中文大模型
    "chatglm2-6b": "THUDM/chatglm2-6b",
    "chatglm3-6b": "THUDM/chatglm3-6b",
    "baichuan-7b": "Baichuan-Inc/Baichuan2-7B-Chat",
    "deepseek-7b": "deepseek-ai/deepseek-llm-7b-chat",
    
    # 添加DeepSeek API模型
    "deepseek-api": "deepseek-api",
    
    # 添加Ollama本地模型
    "ollama-local": "ollama-local"
}

# 反向映射，用于显示名称
DISPLAY_NAMES = {
    "clue/albert_chinese_tiny": "ALBERT-Tiny (中文)",
    "clue/albert_chinese_small": "ALBERT-Small (中文)",
    "clue/albert_chinese_base": "ALBERT-Base (中文)",
    "distilgpt2": "DistilGPT2 (英文)",
    "google/mt5-small": "MT5-Small (多语言)",
    "google/mt5-base": "MT5-Base (多语言)",
    "THUDM/chatglm2-6b": "ChatGLM2-6B (中文)",
    "THUDM/chatglm3-6b": "ChatGLM3-6B (中文)",
    "Baichuan-Inc/Baichuan2-7B-Chat": "Baichuan2-7B (中文)",
    "deepseek-ai/deepseek-llm-7b-chat": "DeepSeek-7B (中文)",
    "deepseek-api": "DeepSeek API (云端)",
    "ollama-local": "Ollama 本地模型"
}

def get_model_name(model_identifier: str) -> str:
    """
    获取模型的全名
    
    Args:
        model_identifier: 模型标识符 (tiny/small/base/medium/large 或 huggingface模型名)
        
    Returns:
        模型的全名
    """
    # 处理空值或None
    if not model_identifier:
        return "ollama-local"  # 默认使用本地模型
        
    # 如果是简写，查找对应的模型
    if model_identifier.lower() in MODELS:
        return MODELS[model_identifier.lower()]
    
    # 如果找不到映射，直接返回原名称
    return model_identifier

def get_model_display_name(model_name: str) -> str:
    """
    获取模型的显示名称
    
    Args:
        model_name: 完整的模型名称
        
    Returns:
        用于显示的友好名称
    """
    # 如果在反向映射中，返回对应的显示名称
    if model_name in DISPLAY_NAMES:
        return DISPLAY_NAMES[model_name]
    
    # 尝试查找更短的匹配
    for key, display_name in DISPLAY_NAMES.items():
        if key in model_name:
            return display_name
    
    # 默认返回原名称
    return model_name

if __name__ == "__main__":
    # 测试代码
    test_names = ["tiny", "small", "THUDM/chatglm3-6b", "unknown-model", "ollama-local"]
    for name in test_names:
        full_name = get_model_name(name)
        display_name = get_model_display_name(full_name)
        print(f"{name} -> {full_name} -> {display_name}") 