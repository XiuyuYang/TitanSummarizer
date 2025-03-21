#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TitanSummarizer - 大文本摘要系统
支持中文小说等长文本的摘要生成
使用DeepSeek API进行云端摘要
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
        
        # 确定模型名称 - 使用get_model_name函数
        self.model_name = get_model_name(model_size)
        logger.info(f"使用模型: {self.model_name} (来自参数: {model_size})")
        
        # 初始化API客户端
        self._init_api()
        
    def _init_api(self) -> None:
        """初始化DeepSeek API客户端"""
        try:
            # 报告开始初始化API
            print("正在初始化DeepSeek API客户端...")
            logger.info("初始化DeepSeek API客户端")
            
            # 如果使用的不是deepseek-api，给出警告
            if self.model_name != "deepseek-api":
                logger.warning(f"注意：指定的模型 '{self.model_name}' 不是DeepSeek API，将被忽略")
                print(f"注意：指定的模型 '{self.model_name}' 不是DeepSeek API，将被忽略")
                
            # 创建API客户端，默认使用模拟模式
            self.api = DeepSeekAPI(use_mock=True)
            
            # 模拟短暂延迟，以保持与原代码的使用体验一致
            time.sleep(1)
            
            # 初始化完成
            print("DeepSeek API客户端初始化完成!")
            logger.info("DeepSeek API客户端初始化完成")
            self.model_loaded = True
            
        except Exception as e:
            error_msg = f"初始化API客户端失败: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
            raise Exception(error_msg)
            
    def is_model_loaded(self) -> bool:
        """
        检查模型是否已加载完成
        
        Returns:
            布尔值，表示API客户端是否已初始化完成
        """
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
            if not self.model_loaded:
                error_msg = "API客户端尚未初始化完成，无法生成摘要"
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
                    logger.warning(f"API摘要生成出错，切换到提取式摘要: {str(e)}")
                    if self.progress_callback:
                        self.progress_callback(0.5, "API调用出错，切换到提取式摘要...", file_percentage)
                    summary = self._extractive_summarize(text, max_length)
            
            # 确保摘要长度不超过限制
            if len(summary) > max_length:
                summary = summary[:max_length] + "..."
                
            if self.progress_callback:
                self.progress_callback(1.0, "摘要生成完成", file_percentage)
                
            return summary
            
        except Exception as e:
            error_msg = f"生成摘要时发生错误: {str(e)}"
            logger.error(error_msg)
            if self.progress_callback:
                self.progress_callback(0.0, error_msg, file_percentage)
            return f"摘要生成失败: {str(e)}"
    
    def _extractive_summarize(self, text: str, max_length: int = 200) -> str:
        """
        简单的提取式摘要方法，作为API失败时的备选
        
        Args:
            text: 输入文本
            max_length: 摘要最大长度
            
        Returns:
            提取的摘要文本
        """
        # 分割文本为句子
        sentences = re.split(r'(?<=[。！？.!?])', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 如果句子太少，直接返回原文
        if len(sentences) <= 3:
            return text[:max_length] + ("..." if len(text) > max_length else "")
        
        # 计算每个句子的重要性分数 (简单实现：句子长度 + 位置因素)
        sentence_scores = []
        for i, sentence in enumerate(sentences):
            # 位置因素：开头和结尾的句子更重要
            position_score = 1.0
            if i < len(sentences) * 0.2:  # 开头20%的句子
                position_score = 1.5
            elif i > len(sentences) * 0.8:  # 结尾20%的句子
                position_score = 1.2
                
            # 长度因素：中等长度的句子更重要
            length_score = min(1.0, len(sentence) / 50)
            
            # 综合得分
            score = position_score * length_score
            sentence_scores.append((i, score))
        
        # 根据得分排序选择句子
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 估算要选择的句子数量
        avg_sentence_length = sum(len(s) for s in sentences) / len(sentences)
        estimated_count = max(1, int(max_length / avg_sentence_length * 0.8))
        
        # 选择最重要的句子，但不超过原文的1/3
        selected_count = min(estimated_count, len(sentences) // 3 + 1)
        selected_indices = [score_tuple[0] for score_tuple in sentence_scores[:selected_count]]
        selected_indices.sort()  # 按照原始顺序排列
        
        # 构建摘要
        summary_sentences = [sentences[i] for i in selected_indices]
        summary = "".join(summary_sentences)
        
        # 确保不超过最大长度
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
            
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
            text: 输入文本
            target_language: 目标语言
            callback: 回调函数
            
        Returns:
            翻译后的文本
        """
        try:
            # 检查API客户端是否已初始化完成
            if not self.model_loaded:
                error_msg = "API客户端尚未初始化完成，无法翻译文本"
                logger.error(error_msg)
                return error_msg
                
            # 构建翻译提示词
            prompt = f"请将以下文本翻译为{target_language}：\n\n{text}"
            
            # 调用API进行翻译
            translation = self.api.summarize_text(prompt)
            
            if not translation:
                return f"翻译失败，请检查API连接"
                
            return translation
            
        except Exception as e:
            error_msg = f"翻译文本时发生错误: {str(e)}"
            logger.error(error_msg)
            return f"翻译失败: {str(e)}"

def test_summarizer():
    """测试TitanSummarizer功能"""
    # 实例化
    summarizer = TitanSummarizer(model_size="deepseek-api", device="cpu")
    
    # 准备测试文本
    test_text = """
    人工智能（Artificial Intelligence，简称AI）是一门研究如何使计算机模拟人类智能的学科。它涵盖了机器学习、深度学习、自然语言处理等多个领域。人工智能技术已经广泛应用于医疗、金融、教育等行业，极大地提高了工作效率和服务质量。
    机器学习是人工智能的核心技术之一，它通过算法让计算机从数据中学习规律，进而做出决策或预测。深度学习则是机器学习的进阶版，它通过多层神经网络来处理复杂数据，模拟人脑的工作方式。
    在自然语言处理方面，大型语言模型如GPT、BERT等取得了突破性进展，能够生成流畅的文本、回答问题、甚至创作诗歌和短篇小说。计算机视觉技术则让机器能够"看见"并理解图像和视频内容。
    尽管人工智能技术飞速发展，但它仍面临诸多挑战，如道德伦理问题、隐私安全问题等。未来，人工智能有望在更多领域发挥作用，为人类社会创造更多价值。
    """
    
    print("===== 测试TitanSummarizer =====")
    print(f"原文长度: {len(test_text)} 字符")
    
    # 生成摘要
    print("\n生成式摘要:")
    summary = summarizer.generate_summary(test_text, max_length=100, summary_mode="generative")
    print(summary)
    print(f"摘要长度: {len(summary)} 字符")
    
    # 提取式摘要
    print("\n提取式摘要:")
    summary = summarizer.generate_summary(test_text, max_length=100, summary_mode="extractive")
    print(summary)
    print(f"摘要长度: {len(summary)} 字符")
    
    # 翻译
    print("\n翻译测试:")
    translation = summarizer.translate_text("人工智能正在改变世界", "English")
    print(translation)
    
    print("\n===== 测试完成 =====")

if __name__ == "__main__":
    test_summarizer() 
