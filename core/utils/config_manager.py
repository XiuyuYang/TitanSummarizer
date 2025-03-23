#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置管理模块
提供配置的加载、保存和管理功能
"""

import json
import os
import logging
from typing import Dict, Any, Optional

# 设置日志
logger = logging.getLogger(__name__)

# 默认配置文件路径
DEFAULT_CONFIG_FILE = "config/settings.json"

# 默认配置
DEFAULT_CONFIG = {
    "api_type": "deepseek",        # API类型: deepseek 或 ollama
    "max_length": 200,             # 摘要最大长度
    "temperature": 0.7,            # 生成随机性参数
    "summary_mode": "generative",  # 摘要模式: generative, extractive, mixed
    "models_dir": os.environ.get("TITAN_MODELS_DIR", r"D:\Work\AI_Models"),  # 模型目录
    "history_limit": 10,           # 历史记录最大条数
    "default_target_language": "English",  # 默认翻译目标语言
    "last_used_model": "",         # 上次使用的模型
    "ui": {
        "theme": "light",          # 界面主题: light 或 dark
        "font_size": 12,           # 字体大小
        "window_size": [800, 600]  # 窗口大小
    }
}

class ConfigManager:
    """配置管理类"""
    
    def __init__(self, config_file: str = DEFAULT_CONFIG_FILE):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = DEFAULT_CONFIG.copy()
        
        # 确保配置目录存在
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # 加载配置
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            配置字典
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    
                # 更新默认配置
                self._update_config_recursive(self.config, user_config)
                logger.info(f"从 {self.config_file} 加载配置成功")
            else:
                logger.info(f"配置文件 {self.config_file} 不存在，使用默认配置")
                # 创建默认配置文件
                self.save_config()
                
        except Exception as e:
            logger.error(f"加载配置时出错: {str(e)}")
            logger.info("使用默认配置")
            
        return self.config
    
    def _update_config_recursive(self, base_config: Dict[str, Any], 
                               user_config: Dict[str, Any]) -> None:
        """
        递归更新配置字典
        
        Args:
            base_config: 基础配置字典
            user_config: 用户配置字典
        """
        for key, value in user_config.items():
            if key in base_config and isinstance(base_config[key], dict) and isinstance(value, dict):
                # 如果都是字典，递归合并
                self._update_config_recursive(base_config[key], value)
            else:
                # 直接更新值
                base_config[key] = value
    
    def save_config(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            是否成功保存
        """
        try:
            # 确保配置目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
                
            logger.info(f"配置已保存到 {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置时出错: {str(e)}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            key: 配置项键名，支持点分隔的路径
            default: 默认值
            
        Returns:
            配置项的值
        """
        # 处理点分隔的路径
        if '.' in key:
            parts = key.split('.')
            current = self.config
            
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return default
                    
            return current
        
        # 直接获取顶级键
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置项
        
        Args:
            key: 配置项键名，支持点分隔的路径
            value: 要设置的值
        """
        # 处理点分隔的路径
        if '.' in key:
            parts = key.split('.')
            current = self.config
            
            # 遍历路径中除最后一个部分
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # 设置值
            current[parts[-1]] = value
        else:
            # 直接设置顶级键
            self.config[key] = value