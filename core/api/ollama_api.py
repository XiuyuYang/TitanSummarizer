#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Ollama API 模块
用于与本地Ollama服务通信，加载和使用本地GGUF大模型
"""

import os
import subprocess
import requests
import json
import time
import glob
import re
import logging
from typing import Optional, Dict, List, Any, Tuple

from core.api.base_api import BaseModelAPI

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ollama服务地址
OLLAMA_API = "http://localhost:11434"

# 默认模型存储根目录
DEFAULT_MODELS_ROOT = os.environ.get("TITAN_MODELS_DIR", r"D:\Work\AI_Models")

# 支持的模型文件扩展名
SUPPORTED_EXTENSIONS = ['.gguf', '.bin', '.ggml']

class OllamaAPI(BaseModelAPI):
    """Ollama API客户端"""
    
    def __init__(self, 
                 models_root: Optional[str] = None, 
                 use_model: Optional[str] = None,
                 **kwargs):
        """
        初始化Ollama API客户端
        
        Args:
            models_root: 模型文件存储根目录，默认使用环境变量或预设值
            use_model: 指定要使用的模型名称，如果为None则需要手动加载模型
        """
        self.models_root = models_root or DEFAULT_MODELS_ROOT
        self.current_model = use_model
        self.model_loaded = False
        
        # 启动Ollama服务(如果未运行)
        if not self._check_ollama_running():
            self._start_ollama()
        
        # 如果指定了模型，尝试加载
        if use_model:
            logger.info(f"尝试使用指定模型: {use_model}")
            self._try_load_model_by_name(use_model)
    
    def _check_ollama_running(self) -> bool:
        """
        检查Ollama服务是否正在运行
        
        Returns:
            布尔值，表示服务是否在运行
        """
        try:
            response = requests.get(f"{OLLAMA_API}/api/tags")
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            logger.warning("Ollama服务未运行")
            return False
    
    def _start_ollama(self) -> bool:
        """
        启动Ollama服务
        
        Returns:
            布尔值，表示是否成功启动服务
        """
        logger.info("正在启动Ollama服务...")
        print("正在启动Ollama服务...")
        
        try:
            # 非阻塞方式启动Ollama，使用UTF-8编码
            subprocess.Popen(["ollama", "serve"], 
                            shell=True, 
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            encoding='utf-8',
                            errors='replace')
            
            # 等待服务启动
            attempts = 0
            while attempts < 10:
                if self._check_ollama_running():
                    logger.info("Ollama服务已启动")
                    print("Ollama服务已启动")
                    return True
                logger.info("等待Ollama服务启动...")
                print(f"等待Ollama服务启动... (尝试 {attempts+1}/10)")
                time.sleep(2)
                attempts += 1
            
            logger.error("无法启动Ollama服务")
            print("无法启动Ollama服务，请检查Ollama是否正确安装")
            return False
            
        except Exception as e:
            logger.error(f"启动Ollama时出错: {str(e)}")
            print(f"启动Ollama服务失败: {str(e)}")
            return False
    
    def find_all_models(self) -> List[Dict[str, str]]:
        """
        查找所有支持的模型文件
        
        Returns:
            模型信息列表，每个元素包含path、name和series字段
        """
        all_models = []
        
        # 遍历所有子目录
        for ext in SUPPORTED_EXTENSIONS:
            # 使用glob递归搜索所有匹配扩展名的文件
            pattern = os.path.join(self.models_root, f"**/*{ext}")
            try:
                model_files = glob.glob(pattern, recursive=True)
                all_models.extend(model_files)
            except Exception as e:
                logger.error(f"搜索模型文件时出错: {str(e)}")
        
        # 排序模型文件
        all_models.sort()
        
        # 创建模型信息列表，包含模型路径和推测的模型系列
        model_info = []
        for path in all_models:
            model_series = self._get_model_series(path)
            model_info.append({
                "path": path,
                "name": os.path.basename(path),
                "series": model_series
            })
        
        return model_info
    
    def _get_model_series(self, model_path: str) -> str:
        """
        根据文件名推测模型系列
        
        Args:
            model_path: 模型文件路径
            
        Returns:
            推测的模型系列名称
        """
        filename = os.path.basename(model_path).lower()
        
        if "llama" in filename:
            return "llama"
        elif "mistral" in filename:
            return "mistral"
        elif "qwen" in filename or "qwen" in filename:
            return "qwen"
        elif "yi" in filename:
            return "yi"
        elif "phi" in filename:
            return "phi"
        elif "baichuan" in filename:
            return "baichuan"
        elif "wizard" in filename:
            return "wizard"
        else:
            return "unknown"
    
    def _generate_model_name(self, model_path: str) -> str:
        """
        为模型生成一个有效的名称供Ollama使用
        
        Args:
            model_path: 模型文件路径
            
        Returns:
            模型名称
        """
        # 从路径中提取文件名
        filename = os.path.basename(model_path)
        
        # 移除文件扩展名
        model_name = os.path.splitext(filename)[0]
        
        # 转换为小写
        model_name = model_name.lower()
        
        # 替换非法字符为'-'
        model_name = re.sub(r'[^a-z0-9-]', '-', model_name)
        
        # 确保名称有效 (以字母开头，只包含字母、数字、连字符，不以连字符结尾)
        model_name = re.sub(r'^[^a-z]+', '', model_name)  # 确保以字母开头
        model_name = re.sub(r'-+$', '', model_name)       # 移除尾部连字符
        model_name = re.sub(r'-+', '-', model_name)       # 合并连续连字符
        
        # 如果经过处理后名称为空，设置为默认名称
        if not model_name:
            model_series = self._get_model_series(model_path)
            model_name = f"{model_series}-model"
        
        return model_name
    
    def load_model(self, model_path: str) -> Optional[str]:
        """
        加载指定的模型文件到Ollama
        
        Args:
            model_path: 模型文件路径
            
        Returns:
            成功时返回模型名称，失败时返回None
        """
        if not os.path.exists(model_path):
            logger.error(f"模型文件不存在: {model_path}")
            return None
        
        # 生成模型名称
        model_name = self._generate_model_name(model_path)
        logger.info(f"使用模型名称: {model_name}")
        
        # 检查Modelfile是否存在，不存在则创建
        modelfile_path = self._create_modelfile(model_path, model_name)
        if not modelfile_path:
            logger.error("创建Modelfile失败")
            return None
        
        # 创建模型
        try:
            logger.info(f"正在使用Modelfile创建模型: {model_name}")
            
            # 构建创建命令
            create_command = f'ollama create {model_name} -f "{modelfile_path}"'
            
            # 执行命令
            result = subprocess.run(
                create_command, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='replace'
            )
            
            # 检查结果
            if result.returncode != 0:
                logger.error(f"创建模型失败: {result.stderr}")
                return None
            
            logger.info(f"模型创建成功: {model_name}")
            self.current_model = model_name
            self.model_loaded = True
            return model_name
            
        except Exception as e:
            logger.error(f"创建模型时出错: {str(e)}")
            return None
    
    def _create_modelfile(self, model_path: str, model_name: str) -> Optional[str]:
        """
        创建Modelfile
        
        Args:
            model_path: 模型文件路径
            model_name: 模型名称
            
        Returns:
            成功时返回Modelfile路径，失败时返回None
        """
        try:
            # 在当前目录创建Modelfile
            modelfile_path = "Modelfile"
            
            # 创建Modelfile内容
            content = f"""FROM {model_path}
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER stop "Human:"
"""
            
            # 写入文件
            with open(modelfile_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            logger.info(f"Modelfile创建成功: {modelfile_path}")
            return modelfile_path
            
        except Exception as e:
            logger.error(f"创建Modelfile时出错: {str(e)}")
            return None
    
    def _try_load_model_by_name(self, model_name: str) -> bool:
        """
        尝试直接加载已在Ollama中存在的模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            布尔值，表示是否成功加载
        """
        try:
            # 检查模型是否已存在
            response = requests.get(f"{OLLAMA_API}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_exists = any(m.get("name") == model_name for m in models)
                
                if model_exists:
                    logger.info(f"模型已存在于Ollama中: {model_name}")
                    self.current_model = model_name
                    self.model_loaded = True
                    return True
                else:
                    logger.warning(f"模型不存在于Ollama中: {model_name}")
            
            return False
            
        except Exception as e:
            logger.error(f"检查模型时出错: {str(e)}")
            return False
    
    def summarize_text(self, text: str, max_length: Optional[int] = None, 
                      temperature: float = 0.7) -> str:
        """
        使用Ollama生成文本摘要
        
        Args:
            text: 需要摘要的文本
            max_length: 摘要的最大长度，可选
            temperature: 生成随机性，值越大随机性越高
            
        Returns:
            摘要文本
        """
        if not self.is_model_loaded():
            logger.error("模型未加载，无法生成摘要")
            return "错误：模型未加载，请先加载模型"
        
        # 构建提示词来指导模型进行文本摘要
        prompt = f"请对以下文本生成一个简洁清晰的摘要，保留关键信息和核心内容：\n\n{text}"
        
        # 构建API请求
        payload = {
            "model": self.current_model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False
        }
        
        if max_length:
            payload["max_tokens"] = max_length
        
        try:
            # 发送请求
            logger.info(f"发送摘要请求到Ollama (模型: {self.current_model})")
            response = requests.post(f"{OLLAMA_API}/api/generate", json=payload)
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            summary = result.get("response", "")
            
            # 清理摘要（移除可能的提示词前缀）
            summary = self._clean_response(summary)
            
            logger.info(f"摘要生成成功，长度: {len(summary)}")
            return summary
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Ollama API请求错误: {str(e)}"
            logger.error(error_msg)
            return f"错误：{error_msg}"
        except Exception as e:
            error_msg = f"生成摘要时出错: {str(e)}"
            logger.error(error_msg)
            return f"错误：{error_msg}"
    
    def translate_text(self, text: str, target_language: str = "English", 
                     temperature: float = 0.7) -> str:
        """
        使用Ollama翻译文本
        
        Args:
            text: 需要翻译的文本
            target_language: 目标语言
            temperature: 生成随机性，值越大随机性越高
            
        Returns:
            翻译后的文本
        """
        if not self.is_model_loaded():
            logger.error("模型未加载，无法翻译文本")
            return "错误：模型未加载，请先加载模型"
        
        # 构建提示词来指导模型进行文本翻译
        prompt = f"请将以下文本翻译成{target_language}，保持原文的意思和风格：\n\n{text}"
        
        # 构建API请求
        payload = {
            "model": self.current_model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False
        }
        
        try:
            # 发送请求
            logger.info(f"发送翻译请求到Ollama (目标语言: {target_language})")
            response = requests.post(f"{OLLAMA_API}/api/generate", json=payload)
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            translation = result.get("response", "")
            
            # 清理翻译（移除可能的提示词前缀）
            translation = self._clean_response(translation)
            
            logger.info(f"翻译成功，长度: {len(translation)}")
            return translation
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Ollama API请求错误: {str(e)}"
            logger.error(error_msg)
            return f"错误：{error_msg}"
        except Exception as e:
            error_msg = f"翻译文本时出错: {str(e)}"
            logger.error(error_msg)
            return f"错误：{error_msg}"
    
    def _clean_response(self, response: str) -> str:
        """
        清理模型响应，移除可能的提示词前缀
        
        Args:
            response: 原始响应文本
            
        Returns:
            清理后的文本
        """
        # 移除可能的前缀
        prefixes_to_remove = [
            "以下是摘要：", "摘要：", "文本摘要：", "摘要是：", 
            "Here's a summary:", "Summary:", "The summary is:",
            "翻译：", "翻译结果：", "以下是翻译：",
            "Translation:", "Here's the translation:", "Translated text:"
        ]
        
        cleaned_text = response
        for prefix in prefixes_to_remove:
            if cleaned_text.startswith(prefix):
                cleaned_text = cleaned_text[len(prefix):].lstrip()
        
        return cleaned_text
    
    def is_model_loaded(self) -> bool:
        """
        检查模型是否已加载
        
        Returns:
            布尔值，表示模型是否已加载
        """
        # 先检查内部状态
        if self.model_loaded and self.current_model:
            return True
        
        # 尝试通过API检查
        try:
            # 查询已加载的模型
            response = requests.get(f"{OLLAMA_API}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                
                # 如果有当前模型名称，检查是否在加载的模型中
                if self.current_model:
                    return any(m.get("name") == self.current_model for m in models)
                    
                # 如果有任何模型，也可以认为已加载模型
                return len(models) > 0
            
            return False
            
        except Exception as e:
            logger.error(f"检查模型状态时出错: {str(e)}")
            return False