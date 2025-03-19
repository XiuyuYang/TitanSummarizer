#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TitanSummarizer - 大文本摘要系统
支持中文小说等长文本的摘要生成
"""

import os
import logging
import torch
import time
import sys
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig, AutoModel
from transformers.utils import logging as transformers_logging
from pathlib import Path
from typing import Optional, List, Dict, Callable, Tuple
from tqdm import tqdm
import re

# 导入模型名称映射
from get_model_name import MODELS, get_model_name

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("TitanSummarizer")

# 设置transformers的日志级别
transformers_logging.set_verbosity_info()

class TitanSummarizer:
    def __init__(
        self,
        model_size: str = "medium",
        device: str = "cpu",
        progress_callback: Optional[Callable[[float, str, Optional[float]], None]] = None
    ) -> None:
        """
        初始化TitanSummarizer类
        
        Args:
            model_size: 模型大小 (small/medium/large 或 1.5B/6B/7B/13B)
            device: 设备 (cpu/cuda)
            progress_callback: 进度回调函数，接收三个参数：进度(0-1)，消息，文件进度(0-100或None)
        """
        self.model_size = model_size
        self.device = device
        self.progress_callback = progress_callback
        
        # 设置模型下载位置 - 确保下载到当前目录的models文件夹
        models_dir = os.path.join(os.getcwd(), "models")
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)
            logger.info(f"创建模型目录: {models_dir}")
            
        # 设置环境变量指定下载位置
        os.environ["TRANSFORMERS_CACHE"] = models_dir
        os.environ["HF_HOME"] = models_dir
        os.environ["HF_DATASETS_CACHE"] = os.path.join(models_dir, "datasets")
        os.environ["HUGGINGFACE_HUB_CACHE"] = os.path.join(models_dir, "hub")
        logger.info(f"设置模型下载路径: {models_dir}")
        
        # 确定模型名称 - 使用get_model_name函数
        self.model_name = get_model_name(model_size)
        logger.info(f"使用模型: {self.model_name} (来自参数: {model_size})")
        
        self.tokenizer = None
        self.model = None
        
        # 初始化模型和分词器
        self._init_model()
        
    def _init_model(self) -> None:
        """初始化大语言模型和分词器"""
        try:
            # 设置缓存目录
            models_dir = os.path.join(os.getcwd(), "models")
            cache_dir = models_dir
            
            # 直接回调进度信息
            def send_to_callback(message):
                if self.progress_callback:
                    self.progress_callback(None, message, None)
            
            # 报告开始加载
            if self.progress_callback:
                self.progress_callback(0.01, "开始加载模型和分词器...", None)
            
            # 加载分词器
            logger.info(f"从 {self.model_name} 加载分词器")
            
            # 加载分词器时把所有输出都发给回调函数
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                cache_dir=cache_dir
            )
            
            # 检查分词器类型
            tokenizer_class = type(self.tokenizer).__name__
            if self.progress_callback:
                self.progress_callback(0.15, f"加载的分词器类型: {tokenizer_class}", None)
                
            # 加载模型配置
            if self.progress_callback:
                self.progress_callback(0.2, "加载模型配置...", None)
                
            # 获取模型配置
            logger.info(f"从 {self.model_name} 加载模型配置")
            model_config = AutoConfig.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                cache_dir=cache_dir
            )
                
            # 尝试加载模型
            try:
                # 报告开始加载模型权重
                if self.progress_callback:
                    self.progress_callback(0.3, "加载模型权重...", None)
                    
                logger.info(f"从 {self.model_name} 加载模型")
                
                # 定义进度回调函数
                def progress_callback_fn(progress, message):
                    # 如果已经有progress_callback，直接传递消息
                    if self.progress_callback:
                        # 计算总体进度：30% + (下载进度 * 60%)
                        if isinstance(progress, float) and 0 <= progress <= 1:
                            overall_progress = 0.3 + progress * 0.6
                        else:
                            overall_progress = None
                            
                        # 发送消息，可能包含进度条
                        return self.progress_callback(overall_progress, message, None)
                    return False
                
                # 加载模型 - 尝试使用progress_callback参数
                self.model = AutoModel.from_pretrained(
                    self.model_name,
                    config=model_config,
                    trust_remote_code=True,
                    torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                    device_map=self.device,
                    cache_dir=cache_dir,
                    progress_callback=progress_callback_fn
                )
            except Exception as e:
                if "unexpected keyword argument 'progress_callback'" in str(e):
                    # 如果不支持进度回调，显示警告并重新加载
                    warning_msg = f"模型 {self.model_name} 不支持进度回调参数: {str(e)}"
                    logger.warning(warning_msg)
                    if self.progress_callback:
                        self.progress_callback(0.3, warning_msg, None)
                    
                    # 通知将使用标准方式加载模型
                    if self.progress_callback:
                        self.progress_callback(0.31, "使用标准方式加载模型...", None)
                    
                    # 重新加载模型，不使用进度回调
                    self.model = AutoModel.from_pretrained(
                        self.model_name,
                        config=model_config,
                        trust_remote_code=True,
                        torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                        device_map=self.device,
                        cache_dir=cache_dir
                    )
                else:
                    # 其它错误直接抛出
                    raise e
                
            # 模型加载完成
            if self.progress_callback:
                self.progress_callback(0.95, "模型加载完成，进行最终设置...", None)
                
            # 设置为评估模式
            self.model.eval()
            
            # 完成初始化
            if self.progress_callback:
                self.progress_callback(1.0, "模型加载完成!", None)
                
            logger.info("模型加载成功")
            
        except Exception as e:
            error_msg = f"初始化模型失败: {str(e)}"
            logger.error(error_msg)
            if hasattr(self, 'progress_callback') and self.progress_callback:
                self.progress_callback(0, error_msg, None)
            raise Exception(error_msg)
            
    def _ensure_tokenizer_compatibility(self):
        """确保分词器兼容性"""
        logger.info("分词器兼容性检查完成")
        return
            
    def generate_summary(
        self,
        text: str,
        max_length: int = 20,
        callback: Optional[Callable[[str], None]] = None,
        file_percentage: int = 0
    ) -> str:
        """
        生成文本摘要
        
        Args:
            text: 输入文本
            max_length: 摘要最大长度
            callback: 实时回调函数
            file_percentage: 当前文件处理进度百分比
            
        Returns:
            生成的摘要
        """
        try:
            # 构建输入
            prompt = f"请为以下文本生成一个{max_length}字以内的摘要：\n\n{text}\n\n摘要："
            
            if self.progress_callback:
                self.progress_callback(0.1, "正在处理文本...", file_percentage)
                
            # 编码输入
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            
            if self.progress_callback:
                self.progress_callback(0.3, "正在生成摘要...", file_percentage)
        
            # 生成摘要
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=max_length * 2,  # 考虑中文编码
                    num_beams=4,
                    length_penalty=1.5,
                    repetition_penalty=1.8,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
                
            if self.progress_callback:
                self.progress_callback(0.7, "正在处理输出...", file_percentage)
                
            # 解码输出
            summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # 如果有回调，实时更新输出
            if callback:
                callback(summary)
                
            # 尝试提取摘要部分
            if "摘要：" in summary:
                summary = summary.split("摘要：")[1].strip()
                
            # 限制长度
            if len(summary) > max_length * 3:  # 考虑中文字符可能导致的较长输出
                summary = summary[:max_length * 3] + "..."
                
            if self.progress_callback:
                self.progress_callback(1.0, "摘要生成完成", file_percentage)
                
            return summary
            
        except Exception as e:
            error_msg = f"生成摘要失败: {str(e)}"
            logger.error(error_msg)
            if self.progress_callback:
                self.progress_callback(0, error_msg, file_percentage)
            return f"摘要生成失败: {str(e)}"
            
    def translate_text(
        self,
        text: str,
        target_language: str = "English",
        callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        翻译文本
        
        Args:
            text: 输入文本
            target_language: 目标语言
            callback: 实时回调函数
            
        Returns:
            翻译后的文本
        """
        try:
            # 构建输入
            prompt = f"请将以下中文文本翻译为{target_language}：\n\n{text}\n\n翻译："
            
            # 编码输入
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            
            # 生成摘要
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=len(text) * 2,  # 翻译后文本可能变长
                    num_beams=4,
                    length_penalty=0.6,
                    repetition_penalty=1.2,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
                
            # 解码输出
            translation = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # 如果有回调，实时更新输出
            if callback:
                callback(translation)
                
            # 尝试提取翻译部分
            if "翻译：" in translation:
                translation = translation.split("翻译：")[1].strip()
                
            return translation
            
        except Exception as e:
            error_msg = f"翻译文本失败: {str(e)}"
            logger.error(error_msg)
            return f"翻译失败: {str(e)}"
            
# 进度处理类
class ProgressHandler:
    def __init__(self, callback=None):
        """初始化进度处理器"""
        self.callback = callback
        self.current_file = None
        self.current_file_percentage = 0
        
    def __call__(self, progress, message, file_progress=None):
        """处理进度更新"""
        # 如果有文件进度信息，更新当前文件
        if isinstance(message, str):
            # 检查是否是下载消息
            if message.startswith("Downloading "):
                try:
                    # 提取文件名
                    filename = message.split("Downloading ")[1].split()[0]
                    if filename != self.current_file:
                        self.current_file = filename
                        logger.info(f"正在下载: {filename}")
                        
                    # 检查文件进度
                    if isinstance(file_progress, (int, float)):
                        self.current_file_percentage = file_progress
                        # 整体进度：30%基础进度 + 当前文件进度的50%
                        overall_progress = 0.3 + (file_progress / 100.0) * 0.5
                        
                        # 调用回调函数
                        if self.callback:
                            return self.callback(overall_progress, message, file_progress)
                except Exception as e:
                    logger.error(f"处理下载进度信息失败: {e}")
                
            # 处理模型加载消息
            elif "加载模型" in message:
                if self.callback:
                    return self.callback(0.8, message, None)
            
            # 其他消息直接传递
            elif self.callback:
                return self.callback(progress, message, None)
                
        return False  # 默认不中断处理

def test_summarizer():
    """测试摘要生成器"""
    # 测试文本
    test_text = """
    金庸的武侠小说《射雕英雄传》塑造了郭靖、黄蓉、洪七公、欧阳锋等经典人物。
    故事从郭靖出生写起，写到郭靖黄蓉大婚为止。
    主人公郭靖系金国将领郭啸天与包惜弱之子，郭啸天遭奸人所害，包惜弱带着未出世的儿子返回大宋。
    郭靖自幼勤奋好学、倔强木讷，得到江南七怪、马钰、洪七公等人的传授武功。
    他与聪明狡黠的黄蓉相知相爱，从桃花岛主黄药师处学得武功，闯荡江湖。
    在他们闯荡江湖的同时，郭靖逐渐从一个懵懂少年变成了一个有理想有道德的侠士，终成一代英雄。
    """
    
    # 创建摘要生成器
    summarizer = TitanSummarizer(model_size="1.5B")
    
    # 生成摘要
    def progress_callback(progress, message, file_progress):
        """进度回调函数"""
        if isinstance(progress, (int, float)):
            print(f"进度: {progress * 100:.1f}%")
        if message:
            print(f"消息: {message}")
        if file_progress:
            print(f"文件进度: {file_progress:.1f}%")
        return False  # 不中断处理
        
    summary = summarizer.generate_summary(test_text, callback=lambda x: print(f"生成: {x}"))
    
    # 打印摘要
    print("\n最终摘要:")
    print(summary)

if __name__ == "__main__":
    test_summarizer() 