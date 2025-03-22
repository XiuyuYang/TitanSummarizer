#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TitanSummarizer - 大文本摘要系统
支持中文小说等长文本的摘要生成
使用DeepSeek API或本地Ollama模型进行摘要
"""

import os
import logging
import time
import sys
import io
import re
from typing import Optional, List, Dict, Callable, Tuple
from tqdm import tqdm

# 导入DeepSeek API
from deepseek_api import DeepSeekAPI

# 导入Ollama API
from ollama_api import OllamaAPI

# 导入辅助函数
from get_model_name import MODELS, get_model_name

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def available_devices():
    """返回可用的设备列表"""
    # 由于使用API，设备选择不再重要
    return ["cpu"]

class TitanSummarizer:
    def __init__(
        self,
        model_size: str = "deepseek-api",
        device: str = "cpu",
        progress_callback: Optional[Callable[[float, str, Optional[float]], None]] = None
    ) -> None:
        """
        初始化TitanSummarizer类
        
        Args:
            model_size: 模型大小 (默认为deepseek-api)
            device: 设备 (不再使用)
            progress_callback: 进度回调函数，接收三个参数：进度(0-1)，消息，文件进度(0-100或None)
        """
        self.model_size = model_size
        self.device = device
        self.progress_callback = progress_callback
        self.model_loaded = False
        self.local_model_path = None  # 存储选中的本地模型路径
        
        # 确定模型名称 - 使用get_model_name函数
        self.model_name = get_model_name(model_size)
        logger.info(f"使用模型: {self.model_name} (来自参数: {model_size})")
        
        # 初始化API客户端 (DeepSeek或Ollama)
        self._init_api()
        
    def _init_api(self) -> None:
        """初始化API客户端 (DeepSeek或Ollama)"""
        try:
            # 根据模型名称选择不同的API客户端
            if self.model_name == "ollama-local":
                # 使用Ollama本地模型
                print("正在初始化Ollama客户端...")
                logger.info("初始化Ollama客户端")
                self.api = OllamaAPI()
                self.api_type = "ollama"
                # 注意：此时还未加载具体的模型文件，需要后续选择和加载
                self.model_loaded = False
            else:
                # 默认使用DeepSeek API
                print("正在初始化DeepSeek API客户端...")
                logger.info("初始化DeepSeek API客户端")
                
                # 如果使用的不是deepseek-api，给出警告
                if self.model_name != "deepseek-api":
                    logger.warning(f"注意：指定的模型 '{self.model_name}' 不是DeepSeek API，将被忽略")
                    print(f"注意：指定的模型 '{self.model_name}' 不是DeepSeek API，将被忽略")
                    
                # 创建API客户端，默认使用模拟模式
                self.api = DeepSeekAPI(use_mock=True)
                self.api_type = "deepseek"
                
                # 模拟短暂延迟，以保持与原代码的使用体验一致
                time.sleep(1)
                
                # 初始化完成
                self.model_loaded = True
            
            # 初始化完成
            print(f"{self.api_type.capitalize()} 客户端初始化完成!")
            logger.info(f"{self.api_type.capitalize()} 客户端初始化完成")
            
        except Exception as e:
            error_msg = f"初始化API客户端失败: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
            raise Exception(error_msg)
    
    def get_all_local_models(self) -> List[Dict]:
        """
        获取所有可用的本地模型列表
        
        Returns:
            模型信息列表，每个元素包含path、name和series字段
        """
        if not hasattr(self, 'api') or self.api_type != "ollama":
            logger.warning("当前未使用Ollama API，无法获取本地模型列表")
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
        if not hasattr(self, 'api') or self.api_type != "ollama":
            error_msg = "当前未使用Ollama API，无法加载本地模型"
            logger.error(error_msg)
            print(error_msg)
            return False
            
        logger.info(f"尝试加载本地模型: {model_path}")
        print(f"正在加载本地模型: {os.path.basename(model_path)}")
        
        try:
            if self.progress_callback:
                # 确保progress和total都是数字
                progress_value = 0.1
                total_value = 1.0
                message = f"正在加载本地模型: {os.path.basename(model_path)}"
                self.progress_callback(progress_value, total_value, message)
                
            # 尝试加载模型
            model_name = self.api.load_model(model_path)
            
            if model_name:
                self.model_loaded = True
                self.local_model_path = model_path
                logger.info(f"本地模型加载成功: {model_name}")
                print(f"本地模型加载成功: {model_name}")
                
                if self.progress_callback:
                    self.progress_callback(1.0, 1.0, f"本地模型加载成功: {model_name}")
                    
                return True
            else:
                error_msg = f"本地模型加载失败: {os.path.basename(model_path)}"
                logger.error(error_msg)
                print(error_msg)
                
                if self.progress_callback:
                    self.progress_callback(1.0, 1.0, error_msg)
                    
                return False
                
        except Exception as e:
            error_msg = f"加载本地模型时出错: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
            
            if self.progress_callback:
                self.progress_callback(1.0, 1.0, error_msg)
                
            return False
            
    def is_model_loaded(self) -> bool:
        """
        检查模型是否已加载完成
        
        Returns:
            布尔值，表示API客户端是否已初始化完成并且模型已加载
        """
        # 对于Ollama API，需要检查具体模型是否已加载
        if hasattr(self, 'api_type') and self.api_type == "ollama":
            return self.model_loaded and self.api.is_model_loaded()
        return self.model_loaded
            
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
            text: 输入文本
            max_length: 摘要最大长度
            callback: 实时回调函数
            file_percentage: 当前文件处理进度百分比
            summary_mode: 摘要模式，支持"extractive"(提取式)和"generative"(生成式)
            
        Returns:
            生成的摘要
        """
        try:
            # 检查API客户端是否已初始化完成
            if not self.is_model_loaded():
                error_msg = "模型尚未加载完成，无法生成摘要"
                logger.error(error_msg)
                if self.progress_callback:
                    self.progress_callback(0.0, error_msg, file_percentage)
                return error_msg
            
            if self.progress_callback:
                self.progress_callback(0.1, "正在处理文本...", file_percentage)
            
            # 使用extractive模式时，尝试实现简单的提取式摘要
            if summary_mode == "extractive":
                # 简单的提取式摘要实现
                summary = self._extractive_summarize(text, max_length)
            else:
                # 根据不同的API类型生成摘要
                if hasattr(self, 'api_type'):
                    if self.api_type == "ollama":
                        # 使用Ollama API生成摘要
                        if self.progress_callback:
                            self.progress_callback(0.3, "正在通过本地模型生成摘要...", file_percentage)
                        
                        try:
                            # 调用Ollama API生成摘要
                            summary = self.api.summarize_text(text, max_length=max_length)
                            
                            # 如果API返回失败，使用提取式摘要作为备选
                            if not summary or "错误" in summary:
                                logger.warning("本地模型摘要生成失败，切换到提取式摘要")
                                if self.progress_callback:
                                    self.progress_callback(0.5, "本地模型摘要生成失败，切换到提取式摘要...", file_percentage)
                                summary = self._extractive_summarize(text, max_length)
                        except Exception as e:
                            logger.error(f"本地模型摘要生成错误: {str(e)}")
                            if self.progress_callback:
                                self.progress_callback(0.5, f"本地模型摘要生成错误: {str(e)}", file_percentage)
                            summary = self._extractive_summarize(text, max_length)
                    else:
                        # 使用DeepSeek API生成摘要
                        if self.progress_callback:
                            self.progress_callback(0.3, "正在通过DeepSeek API生成摘要...", file_percentage)
                        
                        try:
                            # 调用API生成摘要
                            summary = self.api.summarize_text(text, max_length=max_length)
                            
                            # 如果API返回失败，使用提取式摘要作为备选
                            if not summary:
                                logger.warning("API摘要生成失败，切换到提取式摘要")
                                if self.progress_callback:
                                    self.progress_callback(0.5, "API摘要生成失败，切换到提取式摘要...", file_percentage)
                                summary = self._extractive_summarize(text, max_length)
                        except Exception as e:
                            logger.error(f"API摘要生成错误: {str(e)}")
                            if self.progress_callback:
                                self.progress_callback(0.5, f"API摘要生成错误: {str(e)}", file_percentage)
                            summary = self._extractive_summarize(text, max_length)
                else:
                    # 使用默认的DeepSeek API
                    summary = self.api.summarize_text(text, max_length=max_length)
            
            if self.progress_callback:
                self.progress_callback(1.0, "摘要生成完成", file_percentage)
                
            return summary
            
        except Exception as e:
            error_msg = f"摘要生成失败: {str(e)}"
            logger.error(error_msg)
            if self.progress_callback:
                self.progress_callback(1.0, error_msg, file_percentage)
            return error_msg
            
    def _extractive_summarize(self, text: str, max_length: int = 200) -> str:
        """简单的提取式摘要算法"""
        # 这是一个非常简单的算法，仅作为备选方案
        if not text:
            return ""
            
        # 按句子分割文本
        sentences = re.split(r'[。！？.!?]', text)
        sentences = [s.strip() + "。" for s in sentences if s.strip()]
        
        if not sentences:
            return "无法生成摘要：文本没有明显的句子结构"
            
        # 简单选择：第一句 + 每隔一定间隔选一句
        summary_sentences = [sentences[0]]  # 始终包含第一句
        
        # 计算应该选择多少句才能大致满足长度要求
        avg_length = sum(len(s) for s in sentences) / len(sentences)
        target_sentences = max(2, min(int(max_length / avg_length), len(sentences) // 3))
        
        # 如果文本很短，直接返回原文
        if len(sentences) <= 3 or sum(len(s) for s in sentences) <= max_length * 1.2:
            return text[:max_length]
            
        # 选择有代表性的句子
        if len(sentences) > 3:
            step = max(1, len(sentences) // target_sentences)
            for i in range(1, len(sentences), step):
                if i < len(sentences):
                    summary_sentences.append(sentences[i])
                    if sum(len(s) for s in summary_sentences) >= max_length:
                        break
        
        # 如果还不够长，添加中间部分的一些句子
        middle_index = len(sentences) // 2
        if sum(len(s) for s in summary_sentences) < max_length * 0.7 and middle_index > 0:
            summary_sentences.append(sentences[middle_index])
            
        # 将句子按原文顺序排序
        summary_sentences.sort(key=lambda s: text.index(s) if s in text else 999999)
        
        # 合并成摘要文本
        summary = ''.join(summary_sentences)
        
        # 如果超过长度限制，截断
        if len(summary) > max_length:
            # 尝试在句子边界截断
            last_period = summary[:max_length].rfind("。")
            if last_period > max_length * 0.8:  # 如果断点至少包含80%的长度
                summary = summary[:last_period+1]
            else:
                # 直接截断并添加省略号
                summary = summary[:max_length-3] + "..."
                
        return summary
            
    def translate_text(
        self,
        text: str,
        target_language: str = "English",
        callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """翻译文本（仅DeepSeek API支持）"""
        if not hasattr(self, 'api_type') or self.api_type != "deepseek":
            return f"错误：当前使用的 {getattr(self, 'api_type', '未知')} API 不支持翻译功能"
            
        try:
            if self.progress_callback:
                self.progress_callback(0.1, f"正在将文本翻译为{target_language}...", None)
                
            prompt = f"请将以下文本翻译成{target_language}：\n\n{text}"
            
            if hasattr(self.api, 'translate_text'):
                translation = self.api.translate_text(text, target_language)
            else:
                # 使用summarize_text方法模拟翻译功能
                translation = self.api.summarize_text(prompt)
                
            if self.progress_callback:
                self.progress_callback(1.0, "翻译完成", None)
                
            return translation
            
        except Exception as e:
            error_msg = f"翻译失败: {str(e)}"
            logger.error(error_msg)
            if self.progress_callback:
                self.progress_callback(1.0, error_msg, None)
            return error_msg

# 测试代码
def test_summarizer():
    summarizer = TitanSummarizer(model_size="deepseek-api")
    test_text = """
    这是一个测试文本，用于测试摘要功能。这个文本包含多个句子，每个句子都有不同的内容。
    这是第二段文本，用于测试多段落的摘要生成。我们希望摘要系统能够提取出最重要的信息。
    """
    summary = summarizer.generate_summary(test_text, max_length=50)
    print(f"生成的摘要: {summary}")
    
if __name__ == "__main__":
    test_summarizer() 
