#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
获取模型名称的辅助函数
"""

# 模型映射配置
MODELS = {
    "small": "deepseek-ai/deepseek-coder-1.3b-base",
    "medium": "deepseek-ai/deepseek-coder-6.7b-base", 
    "large": "deepseek-ai/deepseek-coder-33b-base",
    # 兼容旧的模型大小参数
    "1.5B": "deepseek-ai/deepseek-coder-1.3b-base",
    "6B": "deepseek-ai/deepseek-coder-6.7b-base",
    "7B": "deepseek-ai/deepseek-coder-6.7b-base",
    "13B": "deepseek-ai/deepseek-coder-33b-base"
}

def get_model_name(model_size: str) -> str:
    """
    根据模型大小参数获取模型名称
    
    Args:
        model_size: 模型大小参数 (small/medium/large 或 1.5B/6B/7B/13B)
        
    Returns:
        对应的模型名称
    """
    return MODELS.get(model_size, MODELS["medium"])
    
def get_model_display_name(model_name: str) -> str:
    """
    获取模型的显示名称
    
    Args:
        model_name: 模型名称 (如 deepseek-ai/deepseek-coder-6.7b-base)
        
    Returns:
        用户友好的显示名称
    """
    model_display_names = {
        "deepseek-ai/deepseek-coder-1.3b-base": "DeepSeek-Coder-1.3B (轻量版)",
        "deepseek-ai/deepseek-coder-6.7b-base": "DeepSeek-Coder-6.7B (标准版)",
        "deepseek-ai/deepseek-coder-33b-base": "DeepSeek-Coder-33B (增强版)",
    }
    return model_display_names.get(model_name, model_name.split("/")[-1])

def get_folder_size(path):
    """
    获取文件夹大小
    
    Args:
        path: 文件夹路径
        
    Returns:
        文件夹大小（字节）
    """
    import os
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    return total_size

def get_readable_size(size_bytes):
    """
    将字节大小转换为人类可读格式
    
    Args:
        size_bytes: 字节大小
        
    Returns:
        人类可读的大小字符串
    """
    import math
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}" 