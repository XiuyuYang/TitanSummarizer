#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Titan摘要器 - 核心功能模块
提供文本摘要、翻译等核心功能的实现
"""

import os
import logging
import time
import re
from typing import Optional, List, Dict, Callable, Tuple, Any
import importlib
from enum import Enum, auto

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("titan_summarizer.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 核心摘要器配置选项
DEFAULT_CONFIG = {
    "default_api": "deepseek",  # 默认使用的API类型
    "max_length": 200,          # 默认摘要最大长度
    "temperature": 0.7,         # 生成随机性参数
    "models_dir": os.environ.get("TITAN_MODELS_DIR", r"D:\Work\AI_Models")  # 模型目录
}

class ApiType(Enum):
    """API类型枚举"""
    DEEPSEEK = auto()
    OLLAMA = auto()

class SummaryMode(Enum):
    """摘要模式枚举"""
    GENERATIVE = auto()  # 生成式摘要（使用AI生成）
    EXTRACTIVE = auto()  # 提取式摘要（从原文提取关键句子）
    MIXED = auto()       # 混合模式（两种方法结合）

class TitanSummarizer:
    """Titan摘要器核心类"""
    
    def __init__(
        self,
        api_type: str = "deepseek",
        progress_callback: Optional[Callable[[float, str, Optional[float]], None]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        初始化TitanSummarizer类
        
        Args:
            api_type: API类型 ('deepseek' 或 'ollama')
            progress_callback: 进度回调函数，接收三个参数：进度(0-1)，消息，文件进度(0-100或None)
            config: 自定义配置，如果为None则使用默认配置
        """
        self.config = config or DEFAULT_CONFIG.copy()
        self.progress_callback = progress_callback
        self.api_type = api_type.lower()
        self.api = None
        self.model_loaded = False
        
        # 初始化API客户端
        self._init_api(self.api_type)
    
    def _init_api(self, api_type: str) -> None:
        """
        初始化API客户端
        
        Args:
            api_type: API类型 ('deepseek' 或 'ollama')
        """
        try:
            if self.progress_callback:
                self.progress_callback(0.1, f"正在初始化 {api_type} API...", None)
                
            logger.info(f"初始化API客户端: {api_type}")
            
            # 处理各种模型名称，映射到正确的API类型
            if api_type == "ollama-local" or api_type == "Ollama 本地模型":
                api_type = "ollama"
                logger.info(f"将 {api_type} 映射为 ollama")
            elif api_type == "deepseek-api" or api_type == "DeepSeek API":
                api_type = "deepseek"
                logger.info(f"将 {api_type} 映射为 deepseek")
            # 如果以.gguf结尾，自动使用ollama API
            elif api_type.endswith(".gguf"):
                logger.info(f"检测到GGUF模型文件名称: {api_type}，使用ollama API")
                api_type = "ollama"
            
            if api_type == "deepseek":
                # 动态导入DeepSeekAPI
                module = importlib.import_module("core.api.deepseek_api")
                DeepSeekAPI = getattr(module, "DeepSeekAPI")
                
                # 创建DeepSeekAPI实例
                self.api = DeepSeekAPI(use_mock=True)
                self.model_loaded = True
                
            elif api_type == "ollama":
                # 动态导入OllamaAPI
                module = importlib.import_module("core.api.ollama_api")
                OllamaAPI = getattr(module, "OllamaAPI")
                
                # 创建OllamaAPI实例
                models_dir = self.config.get("models_dir")
                self.api = OllamaAPI(models_root=models_dir)
                self.model_loaded = False  # Ollama需要明确加载模型
                
            else:
                raise ValueError(f"不支持的API类型: {api_type}")
                
            logger.info(f"{api_type} API初始化完成")
            
            if self.progress_callback:
                self.progress_callback(1.0, f"{api_type} API初始化完成", None)
                
        except Exception as e:
            error_msg = f"初始化API客户端失败: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
            
            if self.progress_callback:
                self.progress_callback(1.0, error_msg, None)
                
            raise Exception(error_msg)
    
    def get_all_local_models(self) -> List[Dict[str, str]]:
        """
        获取所有可用的本地模型列表
        
        Returns:
            模型信息列表，每个元素包含path、name和series字段
        """
        if not hasattr(self, 'api') or not hasattr(self.api, 'find_all_models'):
            logger.warning("当前API不支持获取本地模型列表")
            return []
            
        try:
            return self.api.find_all_models()
        except Exception as e:
            logger.error(f"获取本地模型列表失败: {str(e)}")
            return []
    
    def load_local_model(self, model_path: str) -> bool:
        """
        加载指定的本地模型
        
        Args:
            model_path: 模型文件路径
            
        Returns:
            是否成功加载
        """
        if not hasattr(self, 'api') or not hasattr(self.api, 'load_model'):
            error_msg = "当前API不支持加载本地模型"
            logger.error(error_msg)
            print(error_msg)
            return False
            
        logger.info(f"尝试加载本地模型: {model_path}")
        print(f"正在加载本地模型: {os.path.basename(model_path)}")
        
        try:
            if self.progress_callback:
                progress_value = 0.1
                message = f"正在加载本地模型: {os.path.basename(model_path)}"
                self.progress_callback(progress_value, message, None)
                
            # 尝试加载模型
            model_name = self.api.load_model(model_path)
            
            if model_name:
                self.model_loaded = True
                logger.info(f"本地模型加载成功: {model_name}")
                print(f"本地模型加载成功: {model_name}")
            else:
                error_msg = f"模型加载失败: {os.path.basename(model_path)}"
                logger.error(error_msg)
                print(error_msg)
                return False
                    
            if self.progress_callback:
                self.progress_callback(1.0, f"本地模型加载成功: {model_name}", None)
                    
            return True
                
        except Exception as e:
            error_msg = f"加载本地模型时出错: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
            
            if self.progress_callback:
                self.progress_callback(1.0, error_msg, None)
                
            return False
            
    def is_model_loaded(self) -> bool:
        """
        检查模型是否已加载完成
        
        Returns:
            布尔值，表示API客户端是否已初始化完成并且模型已加载
        """
        try:
            # 首先检查self.model_loaded属性
            if not hasattr(self, 'model_loaded') or not self.model_loaded:
                return False
                
            # 然后检查API是否实例化
            if not hasattr(self, 'api') or self.api is None:
                return False
                
            # 如果API支持is_model_loaded方法，则调用
            if hasattr(self.api, 'is_model_loaded'):
                return self.api.is_model_loaded()
                
            # 否则，返回当前的model_loaded状态
            return self.model_loaded
            
        except Exception as e:
            logger.error(f"检查模型加载状态时出错: {str(e)}")
            return False
            
    def generate_summary(
        self,
        text: str,
        max_length: int = 200,
        callback: Optional[Callable[[str], None]] = None,
        file_percentage: int = 0,
        summary_mode: str = "generative"  # 默认为生成式
    ) -> str:
        """
        生成文本摘要
        
        Args:
            text: 需要摘要的文本
            max_length: 摘要的最大长度
            callback: 回调函数，用于接收生成进度和结果
            file_percentage: 文件处理进度百分比
            summary_mode: 摘要模式 ("generative", "extractive", "mixed")
            
        Returns:
            生成的摘要文本
        """
        if not text.strip():
            return "错误：输入文本为空"
            
        # 检查模型是否已加载
        if not self.is_model_loaded():
            if self.api_type == "ollama":
                return "错误：Ollama模型未加载，请先加载模型"
            else:
                logger.warning("模型未加载，但DeepSeek API可能仍然可用")
        
        try:
            # 根据摘要模式选择不同的摘要方法
            summary_mode = summary_mode.lower()
            
            if summary_mode == "extractive":
                # 提取式摘要
                logger.info("使用提取式摘要")
                if callback:
                    callback("正在使用提取式摘要...")
                summary = self._extractive_summarize(text, max_length)
                
            elif summary_mode == "mixed":
                # 混合模式：先使用提取式摘要，然后使用生成式摘要进一步处理
                logger.info("使用混合式摘要")
                if callback:
                    callback("正在使用混合式摘要...")
                    
                # 首先进行提取式摘要
                extractive_summary = self._extractive_summarize(text, min(500, len(text)//2))
                
                # 然后对提取式摘要进行生成式处理
                if callback:
                    callback("正在对提取结果进行生成式摘要...")
                summary = self.api.summarize_text(
                    extractive_summary, 
                    max_length=max_length, 
                    temperature=self.config.get("temperature", 0.7)
                )
                
            else:  # generative或其他值
                # 生成式摘要（默认）
                logger.info("使用生成式摘要")
                if callback:
                    callback("正在使用AI生成摘要...")
                summary = self.api.summarize_text(
                    text, 
                    max_length=max_length, 
                    temperature=self.config.get("temperature", 0.7)
                )
            
            # 返回摘要
            if callback:
                callback("摘要生成完成")
                
            logger.info(f"摘要生成成功，长度: {len(summary)}")
            return summary
            
        except Exception as e:
            error_msg = f"生成摘要时出错: {str(e)}"
            logger.error(error_msg)
            
            if callback:
                callback(f"错误: {error_msg}")
                
            return f"错误：{error_msg}"
    
    def _extractive_summarize(self, text: str, max_length: int = 200) -> str:
        """
        提取式摘要方法
        
        Args:
            text: 需要摘要的文本
            max_length: 摘要的最大长度
            
        Returns:
            提取的摘要文本
        """
        logger.info("执行提取式摘要")
        
        # 分割句子
        sentences = re.split(r'(?<=[。！？.!?])', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return "无法生成摘要：文本不包含完整句子"
            
        # 如果句子数量少于4，直接返回原文
        if len(sentences) <= 4:
            return text
            
        # 计算每个句子的得分（简单实现：句子长度）
        # 在实际应用中，可以使用更复杂的算法如TF-IDF等
        sentence_scores = [(i, len(s)) for i, s in enumerate(sentences)]
        
        # 按得分排序（从高到低）
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 选择得分最高的句子，但保持原文顺序
        top_sentences = sorted(sentence_scores[:min(5, len(sentences)//3)], key=lambda x: x[0])
        selected_sentences = [sentences[i] for i, _ in top_sentences]
        
        # 如果第一句不在摘要中，添加第一句（通常包含主题）
        if 0 not in [i for i, _ in top_sentences]:
            selected_sentences.insert(0, sentences[0])
            
        # 将选择的句子组合成摘要
        summary = ''.join(selected_sentences)
        
        # 如果摘要超过最大长度，截断
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
            
        logger.info(f"提取式摘要完成，选择了{len(selected_sentences)}个句子，长度{len(summary)}")
        return summary
    
    def translate_text(
        self,
        text: str,
        target_language: str = "English",
        callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        翻译文本
        
        Args:
            text: 需要翻译的文本
            target_language: 目标语言
            callback: 回调函数，用于接收生成进度和结果
            
        Returns:
            翻译后的文本
        """
        if not text.strip():
            return "错误：输入文本为空"
            
        # 检查模型是否已加载
        if not self.is_model_loaded():
            if self.api_type == "ollama":
                return "错误：Ollama模型未加载，请先加载模型"
            else:
                logger.warning("模型未加载，但DeepSeek API可能仍然可用")
        
        try:
            if callback:
                callback(f"正在翻译为{target_language}...")
                
            # 调用API进行翻译
            translation = self.api.translate_text(
                text, 
                target_language=target_language,
                temperature=self.config.get("temperature", 0.7)
            )
            
            if callback:
                callback("翻译完成")
                
            logger.info(f"翻译成功，目标语言: {target_language}，长度: {len(translation)}")
            return translation
            
        except Exception as e:
            error_msg = f"翻译文本时出错: {str(e)}"
            logger.error(error_msg)
            
            if callback:
                callback(f"错误: {error_msg}")
                
            return f"错误：{error_msg}"