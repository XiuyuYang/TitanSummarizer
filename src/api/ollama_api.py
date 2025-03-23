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
        """
        检查Ollama服务是否正在运行
        
        Returns:
            布尔值，表示服务是否运行
        """
        try:
            response = requests.get(f"{OLLAMA_API}/api/tags")
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False
            
    def _start_ollama(self):
        """
        启动Ollama服务
        
        Returns:
            布尔值，表示是否成功启动
        """
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
        
    def find_all_models(self, search_paths=None):
        """
        查找所有支持的模型文件
        
        Args:
            search_paths: 可选的搜索路径列表，如果为None则使用默认路径
            
        Returns:
            模型信息列表，每个元素包含path、name和series字段
        """
        all_models = []
        
        # 如果没有指定搜索路径，使用默认路径和D:\Work\AI_Models目录
        if search_paths is None:
            search_paths = [MODELS_ROOT]
            # 添加D:\Work\AI_Models目录作为搜索路径
            ai_models_path = r"D:\Work\AI_Models"
            if os.path.exists(ai_models_path) and os.path.isdir(ai_models_path):
                search_paths.append(ai_models_path)
                logger.info(f"添加额外搜索路径: {ai_models_path}")
        
        # 在每个搜索路径中查找模型
        for search_path in search_paths:
            if not os.path.exists(search_path) or not os.path.isdir(search_path):
                logger.warning(f"搜索路径不存在或不是目录: {search_path}")
                continue
                
            logger.info(f"在路径中搜索模型: {search_path}")
            
            # 遍历所有子目录
            for ext in SUPPORTED_EXTENSIONS:
                # 使用glob递归搜索所有匹配扩展名的文件
                pattern = os.path.join(search_path, f"**/*{ext}")
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
        
        logger.info(f"共找到 {len(model_info)} 个模型文件")
        return model_info
        
    def _get_model_series(self, model_path):
        """
        根据模型路径猜测模型系列
        
        Args:
            model_path: 模型文件路径
            
        Returns:
            推测的模型系列
        """
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
        """
        根据模型路径生成唯一的模型名称
        
        Args:
            model_path: 模型文件路径
            
        Returns:
            生成的Ollama模型名称
        """
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
            
            # 检查文件是否有效的GGUF/GGML模型文件
            file_ext = os.path.splitext(model_path)[1].lower()
            if file_ext not in ['.gguf', '.ggml', '.bin']:
                error_msg = f"不支持的模型文件格式: {file_ext}，需要.gguf、.ggml或.bin格式"
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
            
            # 将Windows路径转换为正斜杠格式，这在Modelfile中是必需的
            posix_path = model_path.replace('\\', '/')
            
            # 创建基本Modelfile
            modelfile_content = f"""
FROM {posix_path}
PARAMETER temperature 0.7
PARAMETER top_k 40
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
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
                # 使用更长的超时时间，确保大型模型有足够时间加载
                result = subprocess.run(
                    cmd, 
                    shell=False,  # 不使用shell以避免安全风险
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    encoding='utf-8',
                    errors='replace',
                    text=True,
                    timeout=300  # 增加超时时间至5分钟
                )
                
                # 输出加载过程信息
                if result.stdout:
                    logger.info(f"加载模型输出: {result.stdout}")
                
                if result.stderr:
                    logger.info(f"加载过程信息: {result.stderr}")
                    
                # 检查是否加载成功
                if result.returncode == 0:
                    logger.info(f"成功加载模型到Ollama: {model_name}")
                    self.current_model = model_name
                    self.model_loaded = True
                    return model_name
                else:
                    logger.error(f"加载模型失败: {result.stderr}")
                    return None
                    
            except subprocess.TimeoutExpired:
                logger.error("加载模型超时（5分钟）")
                return None
            except Exception as e:
                logger.error(f"执行加载模型命令时出错: {e}")
                return None
                
        except Exception as e:
            error_msg = f"加载模型过程中出错: {e}"
            logger.error(error_msg)
            return None
        
    def summarize_text(self, text, max_length=None, temperature=0.7):
        """
        使用当前加载的模型生成文本摘要
        
        Args:
            text: 需要摘要的文本
            max_length: 摘要的最大长度，None表示不限制
            temperature: 生成随机性参数，越高越随机
            
        Returns:
            生成的摘要文本
        """
        if not self.model_loaded or not self.current_model:
            error_msg = "尚未加载模型，无法执行摘要任务"
            logger.error(error_msg)
            return error_msg
            
        try:
            logger.info(f"使用Ollama模型 {self.current_model} 生成摘要")
            
            # 设置请求URL
            url = f"{OLLAMA_API}/api/generate"
            
            # 构建包含上下文的提示
            prompt = f"""请根据以下文本生成一份精简的摘要，保留关键信息和主要情节:

{text}

请输出简洁的摘要："""
            
            # 准备请求参数
            params = {
                "model": self.current_model,
                "prompt": prompt,
                "temperature": temperature,
                "stream": False
            }
            
            # 如果指定了最大长度
            if max_length:
                # Ollama使用num_predict参数控制生成的token数
                params["num_predict"] = max(50, min(max_length // 2, 500))  # 根据字符数估算token数
            
            # 发送请求到Ollama API
            response = requests.post(url, json=params, timeout=60)
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            summary = result.get("response", "")
            
            # 清理摘要中的无关文本
            summary = self._clean_summary(summary)
            
            # 如果指定了最大长度且超过，进行截断
            if max_length and len(summary) > max_length:
                summary = summary[:max_length] + "..."
            
            return summary
            
        except requests.exceptions.RequestException as e:
            error_msg = f"请求Ollama API时出错: {str(e)}"
            logger.error(error_msg)
            return f"生成摘要失败: {error_msg}"
        
        except Exception as e:
            error_msg = f"生成摘要时出错: {str(e)}"
            logger.error(error_msg)
            return f"生成摘要失败: {error_msg}"
            
    def _clean_summary(self, text):
        """
        清理模型生成的摘要，移除无关文本
        
        Args:
            text: 原始摘要文本
            
        Returns:
            清理后的摘要
        """
        # 移除可能的前缀
        prefixes = [
            "以下是摘要：", "摘要：", "简短摘要：", "文本摘要：",
            "以下是文本摘要：", "以下是对文本的摘要："
        ]
        
        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        
        # 移除注释和说明类文本
        lines = text.split('\n')
        filtered_lines = []
        
        for line in lines:
            # 排除明显是注释的行
            if line.startswith("注：") or line.startswith("注意：") or line.startswith("备注："):
                continue
                
            filtered_lines.append(line)
            
        return "\n".join(filtered_lines).strip()
            
    def is_model_loaded(self):
        """
        检查是否有模型已加载
        
        Returns:
            布尔值，表示模型是否已加载
        """
        # 优先检查实例变量
        if not hasattr(self, 'model_loaded') or not self.model_loaded:
            logger.info("模型加载状态检查：未加载")
            return False
            
        # 如果实例变量显示已加载，再通过API验证
        try:
            if not self.current_model:
                logger.info("模型名称为空，视为未加载")
                return False
                
            response = requests.get(f"{OLLAMA_API}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                
                # 检查当前模型是否在已加载列表中
                model_exists = any(model.get("name") == self.current_model for model in models)
                
                if model_exists:
                    logger.info(f"确认模型 {self.current_model} 已加载")
                    return True
                else:
                    logger.warning(f"模型 {self.current_model} 不在Ollama已加载列表中")
                    # 更新实例状态
                    self.model_loaded = False
                    return False
            else:
                logger.error(f"检查模型状态时API返回非200状态: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"检查模型加载状态时出错: {str(e)}")
            return False
            
        return self.model_loaded

def test_ollama_api():
    """测试Ollama API功能"""
    api = OllamaAPI()
    
    print("======= Ollama API 测试 =======")
    
    # 1. 检查Ollama服务是否运行
    if api._check_ollama_running():
        print("✓ Ollama服务正在运行")
    else:
        print("✗ Ollama服务未运行，尝试启动...")
        if api._start_ollama():
            print("✓ Ollama服务已成功启动")
        else:
            print("✗ 无法启动Ollama服务，测试终止")
            return
    
    # 2. 列出可用的本地模型
    print("\n正在查找本地模型...")
    local_models = api.find_all_models()
    
    if not local_models:
        print("未找到本地模型文件")
        return
        
    print(f"找到 {len(local_models)} 个本地模型:")
    for i, model in enumerate(local_models, 1):
        print(f"{i}. {model['name']} ({model['series']})")
        
    # 3. 加载第一个模型
    if local_models:
        test_model = local_models[0]
        print(f"\n正在加载模型: {test_model['name']}...")
        
        model_name = api.load_model(test_model['path'])
        if model_name:
            print(f"✓ 模型加载成功: {model_name}")
            
            # 4. 测试摘要生成
            test_text = """人工智能(AI)是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。人工智能是研究、开发用于模拟、延伸和扩展人的智能的理论、方法、技术及应用系统的一门新的技术科学。"""
            
            print("\n测试文本摘要生成...")
            print(f"原文: {test_text}\n")
            
            summary = api.summarize_text(test_text, max_length=100)
            print(f"生成的摘要: {summary}\n")
            
        else:
            print(f"✗ 模型加载失败")

if __name__ == "__main__":
    test_ollama_api() 