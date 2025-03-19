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
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers.utils import logging as transformers_logging
from pathlib import Path
from typing import Optional, List, Dict, Callable, Tuple
from tqdm import tqdm
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TitanSummarizer")

# 设置transformers的日志级别
transformers_logging.set_verbosity_info()

# 模型配置
MODELS = {
    "1.5B": "THUDM/chatglm-6b",
    "7B": "THUDM/chatglm2-6b",
    "Qwen-7B": "Qwen/Qwen-7B",
    "Qwen-14B": "Qwen/Qwen-14B",
    "Qwen-32B": "Qwen/Qwen-32B",
    "Qwen-72B": "Qwen/Qwen-72B"
}

# 添加Hugging Face日志处理器
class ProgressHandler(logging.Handler):
    """
    处理transformers日志并转换为进度回调的处理器
    """
    def __init__(self, callback, stage="模型"):
        """
        初始化处理器
        :param callback: 进度回调函数
        :param stage: 当前处理阶段名称（"分词器"或"模型"）
        """
        super().__init__()
        self.callback = callback
        self.stage = stage
        
    def emit(self, record):
        """处理日志记录"""
        try:
            msg = self.format(record)
            
            # 处理下载进度信息 - 适应多种格式
            if "Downloading" in msg:
                try:
                    # 尝试更精确地提取文件名
                    if ":" in msg:
                        file_parts = msg.split(":")
                        file_name = file_parts[0].split("Downloading")[-1].strip()
                    else:
                        file_name_match = re.search(r"Downloading (.*?)(\[|\s|$)", msg)
                        if file_name_match:
                            file_name = file_name_match.group(1).strip()
                        else:
                            file_name = "未知文件"
                    
                    # 提取进度百分比 - 支持更多格式
                    file_percentage = None
                    if "[" in msg and "]" in msg:
                        bracket_content = msg.split("[")[1].split("]")[0].strip()
                        if "%" in bracket_content:
                            try:
                                file_percentage = float(bracket_content.replace("%", "").strip())
                                # 确保是有效数字
                                if not (0 <= file_percentage <= 100):
                                    file_percentage = None
                            except:
                                pass
                    
                    # 直接从文本中搜索百分比
                    if file_percentage is None:
                        percent_match = re.search(r"(\d+(\.\d+)?)%", msg)
                        if percent_match:
                            try:
                                file_percentage = float(percent_match.group(1))
                            except:
                                pass
                    
                    # 如果仍然没有进度数据，查找特殊模式
                    if file_percentage is None and "it/s]" in msg:
                        # 可能是HF的下载开始消息，设为5%作为起始
                        file_percentage = 5.0
                        
                    # 提取大小信息
                    size_info = ""
                    if "]" in msg:
                        size_part = msg.split("]")[-1].strip()
                        if "/" in size_part:
                            size_info = size_part.strip()
                    
                    # 构建详细信息
                    detail = f"{self.stage}下载{file_name}"
                    if size_info:
                        detail += f": {size_info}"
                    
                    # 计算总体进度
                    if file_percentage is not None:
                        if self.stage == "分词器":
                            # 分词器阶段占总进度的20%
                            overall_progress = 0.1 + (file_percentage / 100.0) * 0.2
                        else:
                            # 模型阶段占总进度的50%
                            overall_progress = 0.3 + (file_percentage / 100.0) * 0.5
                        
                        # 打印调试信息
                        logger.debug(f"文件下载进度解析成功: 文件={file_name}, 百分比={file_percentage:.1f}%, 整体进度={overall_progress:.2f}")
                        
                        # 调用回调函数 - 传递详细文件进度信息
                        self.callback(overall_progress, detail, file_percentage)
                    else:
                        # 如果没提取到百分比但确实是下载消息，使用默认值
                        logger.debug(f"未能从下载消息解析进度百分比: {msg}")
                        if "starting" in msg.lower():
                            self.callback(0.3 if self.stage == "模型" else 0.1, detail, 0)
                        
                except Exception as e:
                    logger.error(f"解析下载进度失败: {str(e)}, 消息: {msg}")
            
            # 处理完成信息
            elif "100%" in msg and ("Downloading" in msg or "download" in msg.lower()):
                logger.debug("检测到100%下载完成消息")
                self.callback(0.8 if self.stage == "模型" else 0.3, f"{self.stage}下载完成，正在优化...", 100.0)
            
            # 处理其他日志消息
            elif not any(skip_term in msg.lower() for skip_term in ["download", "extract", "load"]):
                # 对于非下载类消息，只更新总体进度
                if "初始化" in msg:
                    self.callback(0.05, msg, None)
                elif "加载" in msg:
                    self.callback(0.85, msg, None)
                elif "优化" in msg:
                    self.callback(0.95, msg, None)
        except Exception as e:
            logger.error(f"进度处理器处理失败: {str(e)}")
    
    def _format_size(self, size_bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0 or unit == 'GB':
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} GB"

class TitanSummarizer:
    def __init__(self, model_size="1.5B", device="cpu", progress_callback=None):
        """
        初始化摘要器
        :param model_size: 模型大小，可选：1.5B, 7B, Qwen-7B, Qwen-14B, Qwen-32B, Qwen-72B
        :param device: 使用设备，可选值：cpu, cuda
        :param progress_callback: 进度回调函数，接收两个参数：进度(0-1)和消息
        """
        self.model_size = model_size
        self.device = device
        self.progress_callback = progress_callback
        self.model_name = MODELS.get(model_size, MODELS["1.5B"])
        self.model = None
        self.tokenizer = None
        
        # 初始化模型
        self._init_model()
        
    def _init_model(self):
        """
        初始化分词器和模型
        
        Args:
            model_size: 模型大小 (small/medium/large)
            device: 设备 (cpu/cuda)
        """
        # 确定模型名称
        model_names = {
            "small": "THUDM/chatglm-6b",
            "medium": "THUDM/chatglm2-6b",
            "large": "THUDM/chatglm3-6b"
        }
        model_name = model_names.get(self.model_size, "THUDM/chatglm2-6b")
        
        # 备用模型（如果主模型加载失败）
        backup_models = ["THUDM/chatglm-6b", "THUDM/chatglm2-6b", "THUDM/chatglm3-6b"]
        
        # 移除当前模型，确保尝试其他备用模型
        if model_name in backup_models:
            backup_models.remove(model_name)
            
        try:
            if self.progress_callback:
                self.progress_callback(0.05, f"正在初始化分词器: {model_name}")
            
            # 为分词器创建进度处理器
            handlers = []
            if self.progress_callback:
                tokenizer_progress = ProgressHandler(self.progress_callback, "分词器")
                handlers.append(tokenizer_progress)
                logger.debug(f"添加分词器进度处理器")
                
                # 添加日志处理器
                transformers_logger = logging.getLogger("transformers")
                for handler in handlers:
                    transformers_logger.addHandler(handler)
            
            # 首先尝试加载分词器
            try:
                if "chatglm3" in model_name.lower():
                    tokenizer = AutoTokenizer.from_pretrained(
                        model_name, 
                        trust_remote_code=True
                    )
                else:
                    tokenizer = AutoTokenizer.from_pretrained(
                        model_name, 
                        trust_remote_code=True
                    )
                    
                logger.info(f"分词器 {model_name} 加载成功")
                if self.progress_callback:
                    self.progress_callback(0.3, f"分词器加载成功，正在初始化模型: {model_name}")
            except Exception as e:
                logger.error(f"分词器加载失败: {str(e)}")
                
                # 尝试备用模型分词器
                tokenizer = None
                for backup_model in backup_models:
                    try:
                        if self.progress_callback:
                            self.progress_callback(0.1, f"尝试使用备用模型分词器: {backup_model}")
                        logger.info(f"尝试使用备用模型分词器: {backup_model}")
                        
                        tokenizer = AutoTokenizer.from_pretrained(
                            backup_model, 
                            trust_remote_code=True
                        )
                        
                        logger.info(f"备用分词器 {backup_model} 加载成功")
                        if self.progress_callback:
                            self.progress_callback(0.3, f"备用分词器 {backup_model} 加载成功")
                        model_name = backup_model  # 更新模型名称
                        break
                    except Exception as backup_error:
                        logger.error(f"备用分词器 {backup_model} 加载失败: {str(backup_error)}")
                
                if tokenizer is None:
                    raise ValueError("所有分词器加载均失败，请检查网络连接或模型配置")
            
            # 移除分词器进度处理器，准备加载模型
            if self.progress_callback:
                for handler in handlers:
                    transformers_logger.removeHandler(handler)
                handlers.clear()
                
                # 创建模型进度处理器
                model_progress = ProgressHandler(self.progress_callback, "模型")
                handlers.append(model_progress)
                transformers_logger.addHandler(model_progress)
                
                # 设置进度阶段
                self.progress_callback(0.3, f"正在加载模型: {model_name}")
            
            # 监控文件下载进度的自定义回调
            class DownloadProgressCallback(object):
                def __init__(self, progress_callback):
                    self.progress_callback = progress_callback
                    
                def __call__(self, current, total, width=80):
                    if total > 0:
                        file_percentage = current / total * 100
                        # 直接更新文件进度
                        self.progress_callback(0.4, f"下载模型文件: {current}/{total}", file_percentage)
                    
            # 创建下载进度回调
            download_callback = DownloadProgressCallback(self.progress_callback) if self.progress_callback else None
                
            # 加载模型
            try:
                if "chatglm3" in model_name.lower():
                    model = AutoModelForCausalLM.from_pretrained(
                        model_name, 
                        trust_remote_code=True,
                        device_map=self.device,
                        bf16=False,
                        fp16=(self.device=="cuda"),
                        progress_callback=download_callback
                    )
                else:
                    model = AutoModelForCausalLM.from_pretrained(
                        model_name, 
                        trust_remote_code=True,
                        device_map=self.device,
                        progress_callback=download_callback
                    )
                
                logger.info(f"模型 {model_name} 加载成功")
                if self.progress_callback:
                    self.progress_callback(0.9, f"模型加载成功，正在优化...")
            except Exception as e:
                logger.error(f"模型加载失败: {str(e)}")
                raise
            finally:
                # 移除日志处理器
                if self.progress_callback:
                    for handler in handlers:
                        transformers_logger.removeHandler(handler)
            
            # 设置模型优化
            if self.device == "cuda":
                model = model.half()
                logger.info("模型已转换为半精度")
            
            model.eval()
            logger.info("模型已设置为评估模式")
            
            # 保存模型和分词器
            self.tokenizer = tokenizer
            self.model = model
            
            if self.progress_callback:
                self.progress_callback(1.0, "模型初始化完成")
                
            logger.info("模型初始化完成")
        
        except Exception as e:
            # 确保清理所有处理器
            if 'handlers' in locals() and handlers:
                transformers_logger = logging.getLogger("transformers")
                for handler in handlers:
                    if handler in transformers_logger.handlers:
                        transformers_logger.removeHandler(handler)
                        
            logger.error(f"模型初始化失败: {str(e)}")
            raise
            
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
            
            # 提取摘要部分
            summary = summary.split("摘要：")[-1].strip()
            
            # 实时回调
            if callback:
                callback(summary)
                
            if self.progress_callback:
                self.progress_callback(1.0, "摘要生成完成", file_percentage)
                
            return summary
            
        except Exception as e:
            logger.error(f"生成摘要失败: {str(e)}")
            raise

    def process_file(self, file_path: str, max_length: int = 20, callback: Callable[[str], None] = None) -> Optional[str]:
        """处理文件并生成摘要"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"文件不存在: {file_path}")
                return None

            # 尝试使用不同编码读取文件
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='gb2312') as f:
                        text = f.read()
                except UnicodeDecodeError:
                    logger.error(f"无法读取文件，不支持的编码: {file_path}")
                    return None

            return self.generate_summary(text, max_length, callback)

        except Exception as e:
            logger.error(f"处理文件时出错: {str(e)}")
            return None
            
    def get_model_info(self) -> Dict:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "model_size": self.model_size,
            "device": self.device,
            "loaded": self.model is not None
        }

def main():
    # 使用示例
    summarizer = TitanSummarizer(model_size="1.5B", device="cuda")
    
    # 示例文本
    text = """二愣子睁大着双眼，直直望着茅草和烂泥糊成的黑屋顶，身上盖着的旧棉被，已呈深黄色，看不出原来的本来面目，还若有若无的散发着淡淡的霉味。"""
    
    # 生成摘要
    summary = summarizer.generate_summary(text, max_length=20)
    print("\n\n完整摘要:")
    print(summary)

if __name__ == "__main__":
    main() 