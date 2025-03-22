#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Ollama API 模块
用于加载和使用本地GGUF大模型进行摘要生成
"""

import os
import subprocess
import requests
import json
import time
import glob
import re
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ollama服务地址
OLLAMA_API = "http://localhost:11434"

# 模型存储根目录
MODELS_ROOT = r"D:\Work\AI_Models"

# 支持的模型文件扩展名
SUPPORTED_EXTENSIONS = ['.gguf', '.bin', '.ggml']

class OllamaAPI:
    def __init__(self, use_model=None):
        """
        初始化Ollama API客户端
        
        Args:
            use_model: 指定要使用的模型名称，如果为None则需要手动加载模型
        """
        self.current_model = use_model
        self.model_loaded = False
        
        # 启动Ollama服务(如果未运行)
        if not self._check_ollama_running():
            self._start_ollama()
            
    def _check_ollama_running(self):
        """检查Ollama服务是否正在运行"""
        try:
            response = requests.get(f"{OLLAMA_API}/api/tags")
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False
            
    def _start_ollama(self):
        """启动Ollama服务"""
        logger.info("正在启动Ollama服务...")
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
                return True
            logger.info("等待Ollama服务启动...")
            time.sleep(2)
            attempts += 1
        
        logger.error("无法启动Ollama服务")
        return False
        
    def find_all_models(self):
        """查找所有支持的模型文件"""
        all_models = []
        
        # 遍历所有子目录
        for ext in SUPPORTED_EXTENSIONS:
            # 使用glob递归搜索所有匹配扩展名的文件
            pattern = os.path.join(MODELS_ROOT, f"**/*{ext}")
            model_files = glob.glob(pattern, recursive=True)
            all_models.extend(model_files)
        
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
        
    def _get_model_series(self, model_path):
        """根据模型路径猜测模型系列"""
        model_name = os.path.basename(model_path).lower()
        
        if "qwen" in model_name:
            return "qwen"
        elif "llama" in model_name:
            return "llama"
        elif "mistral" in model_name:
            return "mistral"
        elif "phi" in model_name:
            return "phi"
        elif "yi" in model_name:
            return "yi"
        elif "gemma" in model_name:
            return "gemma"
        else:
            return "default"
            
    def _generate_model_name(self, model_path):
        """根据模型路径生成唯一的模型名称"""
        # 提取文件名并去除扩展名
        base_name = os.path.basename(model_path)
        name_without_ext = os.path.splitext(base_name)[0]
        
        # 模型名称只能包含小写字母、数字和短横线
        # 先将下划线替换为短横线
        clean_name = name_without_ext.replace('_', '-')
        
        # 移除所有其他不允许的字符
        clean_name = re.sub(r'[^a-z0-9-]', '-', clean_name.lower())
        
        # 确保名称不以短横线开头
        if clean_name.startswith('-'):
            clean_name = 'model' + clean_name
        
        # 不允许连续短横线
        clean_name = re.sub(r'-+', '-', clean_name)
        
        # 移除结尾的短横线
        clean_name = clean_name.rstrip('-')
        
        # 限制长度
        if len(clean_name) > 40:
            clean_name = clean_name[:40]
        
        # 确保名称不为空
        if not clean_name:
            clean_name = 'model-' + str(int(time.time()))
        
        logger.info(f"原始模型文件名: {base_name} -> 生成的模型名称: {clean_name}")
        return clean_name
        
    def load_model(self, model_path):
        """
        加载本地GGUF模型到Ollama
        
        Args:
            model_path: 模型文件的完整路径
            
        Returns:
            str: 加载成功返回模型名称，失败返回None
        """
        try:
            if not os.path.exists(model_path):
                error_msg = f"模型文件不存在: {model_path}"
                logger.error(error_msg)
                return None
            
            logger.info(f"准备加载模型，路径: {model_path}")
            model_name = self._generate_model_name(model_path)
            logger.info(f"生成的Ollama模型名称: {model_name}")
            
            # 检查模型是否已加载
            try:
                response = requests.get(f"{OLLAMA_API}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    for model in models:
                        logger.debug(f"已加载模型: {model.get('name')}")
                        
                    if any(model.get("name") == model_name for model in models):
                        logger.info(f"模型 {model_name} 已加载到Ollama中")
                        self.current_model = model_name
                        self.model_loaded = True
                        return model_name
            except Exception as e:
                logger.error(f"检查模型时出错: {e}")
                logger.error("将尝试重新加载模型")
            
            # 创建Modelfile，告诉Ollama如何加载本地模型
            modelfile_content = f"""
FROM {model_path}
PARAMETER temperature 0.7
PARAMETER top_k 40
PARAMETER top_p 0.9
PARAMETER num_ctx 2048
"""
            
            logger.info(f"准备加载本地模型 [{os.path.basename(model_path)}]")
            logger.info(f"写入Modelfile配置")
            
            modelfile_path = "Modelfile"
            with open(modelfile_path, "w") as f:
                f.write(modelfile_content)
            
            # 告诉Ollama加载本地模型文件，避免使用shell=True
            logger.info(f"正在将本地模型加载到Ollama，模型名称: {model_name}...")
            
            # 检查系统平台
            if os.name == 'nt':  # Windows
                cmd = ["ollama.exe", "create", model_name, "-f", modelfile_path]
            else:  # Linux/Mac
                cmd = ["ollama", "create", model_name, "-f", modelfile_path]
            
            logger.info(f"执行命令: {' '.join(cmd)}")
            
            try:
                result = subprocess.run(
                    cmd, 
                    shell=False,  # 不使用shell以避免安全风险
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    encoding='utf-8',
                    errors='replace',
                    text=True
                )
                
                # 输出加载过程信息
                if result.stdout:
                    logger.info(f"加载模型输出: {result.stdout}")
                
                if result.stderr:
                    logger.info(f"加载过程信息: {result.stderr}")
                    
                if result.returncode != 0:
                    logger.error(f"加载模型失败，返回码: {result.returncode}")
                    return None
            except Exception as e:
                logger.error(f"执行命令出错: {str(e)}", exc_info=True)
                return None
            
            # 等待模型加载完成
            logger.info("等待模型加载完成...")
            time.sleep(3)
            
            # 验证模型是否加载成功
            try:
                # 尝试进行一个简单的测试查询来验证模型
                headers = {"Content-Type": "application/json"}
                data = {"model": model_name, "prompt": "Hello", "stream": False}
                
                logger.info(f"验证模型 {model_name} 是否可用...")
                response = requests.post(
                    f"{OLLAMA_API}/api/generate",
                    headers=headers,
                    data=json.dumps(data)
                )
                
                if response.status_code == 200:
                    logger.info(f"模型 {model_name} 成功加载并可用")
                    self.current_model = model_name
                    self.model_loaded = True
                    return model_name
                else:
                    logger.error(f"模型验证失败: {response.status_code}")
                    logger.error(response.text)
            except Exception as e:
                logger.error(f"验证模型时出错: {e}")
            
            return None
        except Exception as e:
            logger.error(f"加载模型过程中发生异常: {str(e)}", exc_info=True)
            return None
        
    def summarize_text(self, text, max_length=None, temperature=0.7):
        """
        使用本地大模型对文本进行摘要
        
        Args:
            text: 需要摘要的文本
            max_length: 摘要最大长度(tokens)，默认None
            temperature: 生成随机性，数值越大随机性越高，默认0.7
            
        Returns:
            str: 生成的摘要
        """
        if not self.model_loaded or not self.current_model:
            return "错误：未加载模型，无法生成摘要"
            
        # 构建提示词
        prompt = f"""请对以下文本生成一个简洁的摘要，捕捉其中的关键信息、主要情节和重要人物。摘要应包含文本的主要内容，同时避免过多细节。控制在{max_length or 200}字以内。

文本内容：
{text}

摘要："""
            
        # 准备API请求
        headers = {"Content-Type": "application/json"}
        data = {
            "model": self.current_model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False
        }
        
        try:
            logger.info(f"正在使用模型 {self.current_model} 生成摘要...")
            response = requests.post(
                f"{OLLAMA_API}/api/generate",
                headers=headers,
                data=json.dumps(data)
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result.get("response", "")
                return summary
            else:
                error_msg = f"摘要生成失败: {response.status_code}"
                logger.error(error_msg)
                logger.error(response.text)
                return error_msg
        except Exception as e:
            error_msg = f"摘要生成过程中出错: {str(e)}"
            logger.error(error_msg)
            return error_msg
            
    def is_model_loaded(self):
        """
        检查模型是否已加载
        
        Returns:
            bool: 模型是否已加载并可用
        """
        return self.model_loaded and self.current_model is not None

# 测试代码
if __name__ == "__main__":
    # 初始化API
    api = OllamaAPI()
    
    # 查找所有模型
    models = api.find_all_models()
    print(f"找到 {len(models)} 个模型:")
    for i, model in enumerate(models, 1):
        print(f"{i}. [{model['series']}] {model['name']}")
        
    # 选择第一个模型进行加载(如果有)
    if models:
        model_path = models[0]["path"]
        print(f"\n尝试加载模型: {models[0]['name']}")
        model_name = api.load_model(model_path)
        
        if model_name:
            # 测试摘要生成
            test_text = "这是一个测试文本，用于验证摘要功能是否正常工作。这个文本不包含任何有价值的信息，仅作为功能测试使用。"
            summary = api.summarize_text(test_text, max_length=50)
            print(f"\n生成的摘要: {summary}")
        else:
            print("模型加载失败") 