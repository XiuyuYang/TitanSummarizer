#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
修复设置文件
"""

import json
import os

settings_file = "settings.json"

if os.path.exists(settings_file):
    try:
        # 读取当前设置
        with open(settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)
        
        # 修改默认长度为200
        old_length = settings.get("default_length", 500)
        settings["default_length"] = 200
        
        # 保存更新后的设置
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        
        print(f"已将默认摘要长度从 {old_length} 修改为 200")
    except Exception as e:
        print(f"修改设置文件失败: {e}")
else:
    # 创建新的设置文件
    default_settings = {
        "default_model": "deepseek-api",
        "default_length": 200,
        "api_key": None,
        "theme": "clam"
    }
    
    try:
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(default_settings, f, indent=4)
        print("已创建新的设置文件，默认摘要长度为 200")
    except Exception as e:
        print(f"创建设置文件失败: {e}") 