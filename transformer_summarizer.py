#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TitanSummarizer Transformer - 基于Transformer的小说摘要生成器
使用预训练的Transformer模型（如BART、T5等）生成中文小说摘要
"""

import os
import re
import torch
import logging
from typing import List, Dict, Tuple, Any, Optional
from transformers import (
    AutoTokenizer, 
    AutoModelForSeq2SeqLM,
    BartForConditionalGeneration,
    T5ForConditionalGeneration,
    pipeline
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TransformerSummarizer")

# 可用的预训练模型
AVAILABLE_MODELS = {
    "bart-base-chinese": {
        "model_name": "fnlp/bart-base-chinese",
        "max_length": 1024,
        "type": "bart"
    },
    "mt5-small-chinese": {
        "model_name": "google/mt5-small",
        "max_length": 512,
        "type": "t5"
    },
    "cpt-base": {
        "model_name": "fnlp/cpt-base",
        "max_length": 1024,
        "type": "bart"
    }
}

def read_file(file_path: str) -> str:
    """读取文本文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        return content
    except UnicodeDecodeError:
        # 尝试其他编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                logger.info(f"成功使用 {encoding} 编码读取文件")
                return content
            except UnicodeDecodeError:
                continue
        
        # 如果所有编码都失败，尝试二进制读取并解码
        with open(file_path, 'rb') as f:
            content = f.read()
            # 尝试检测编码
            try:
                import chardet
                detected = chardet.detect(content)
                encoding = detected['encoding']
                logger.info(f"检测到编码: {encoding}")
                return content.decode(encoding)
            except:
                # 最后尝试忽略错误解码
                return content.decode('utf-8', errors='ignore')

def detect_chapters(content: str) -> List[Dict[str, Any]]:
    """
    检测小说章节
    返回章节列表，每个章节包含标题和内容
    """
    # 常见的章节标题模式
    chapter_patterns = [
        r'第[零一二三四五六七八九十百千万亿\d]+章\s*[^\n]+',  # 第一章 标题
        r'第[零一二三四五六七八九十百千万亿\d]+节\s*[^\n]+',  # 第一节 标题
        r'Chapter\s*\d+\s*[^\n]+',                        # Chapter 1 标题
        r'CHAPTER\s*\d+\s*[^\n]+'                         # CHAPTER 1 标题
    ]
    
    # 合并模式
    pattern = '|'.join(chapter_patterns)
    
    # 查找所有章节标题
    chapter_titles = re.findall(pattern, content)
    
    # 如果没有找到章节，将整个内容作为一个章节
    if not chapter_titles:
        return [{
            "title": "全文",
            "content": content,
            "start_pos": 0,
            "end_pos": len(content),
            "original_length": len(content)
        }]
    
    # 查找章节标题的位置
    chapter_positions = []
    for title in chapter_titles:
        pos = content.find(title)
        if pos != -1:
            chapter_positions.append((pos, title))
    
    # 按位置排序
    chapter_positions.sort()
    
    # 提取章节内容
    chapters = []
    for i, (start_pos, title) in enumerate(chapter_positions):
        # 章节结束位置是下一章节的开始位置或文本结束
        end_pos = chapter_positions[i+1][0] if i < len(chapter_positions) - 1 else len(content)
        chapter_content = content[start_pos:end_pos]
        
        chapters.append({
            "title": title.strip(),
            "content": chapter_content,
            "start_pos": start_pos,
            "end_pos": end_pos,
            "original_length": len(chapter_content)
        })
    
    return chapters

def load_model(model_name: str, device: Optional[str] = None) -> Tuple[Any, Any, str, int]:
    """
    加载预训练模型和分词器
    返回模型、分词器、设备和最大长度
    """
    if model_name not in AVAILABLE_MODELS:
        raise ValueError(f"不支持的模型: {model_name}，可用模型: {list(AVAILABLE_MODELS.keys())}")
    
    model_info = AVAILABLE_MODELS[model_name]
    model_path = model_info["model_name"]
    max_length = model_info["max_length"]
    
    # 确定设备
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # 加载分词器
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    
    # 加载模型
    if model_info["type"] == "bart":
        model = BartForConditionalGeneration.from_pretrained(model_path)
    elif model_info["type"] == "t5":
        model = T5ForConditionalGeneration.from_pretrained(model_path)
    else:
        model = AutoModelForSeq2SeqLM.from_pretrained(model_path)
    
    model = model.to(device)
    
    return model, tokenizer, device, max_length

def generate_summary(text: str, model: Any, tokenizer: Any, device: str, 
                    max_length: int, max_summary_length: int = 150) -> str:
    """
    使用Transformer模型生成摘要
    """
    # 截断过长的文本
    if len(text) > max_length * 4:  # 估计字符数是token数的4倍
        logger.warning(f"文本过长 ({len(text)} 字符)，将被截断")
        text = text[:max_length * 4]
    
    # 编码文本
    inputs = tokenizer(text, return_tensors="pt", max_length=max_length, truncation=True)
    inputs = inputs.to(device)
    
    # 生成摘要
    with torch.no_grad():
        summary_ids = model.generate(
            inputs["input_ids"],
            max_length=max_summary_length,
            min_length=30,
            num_beams=4,
            length_penalty=2.0,
            early_stopping=True,
            no_repeat_ngram_size=3
        )
    
    # 解码摘要
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    
    return summary

def summarize_by_chapter(content: str, model: Any, tokenizer: Any, device: str, 
                        max_length: int, max_summary_length: int = 150) -> Dict[str, Any]:
    """
    按章节生成摘要
    """
    # 检测章节
    chapters = detect_chapters(content)
    logger.info(f"检测到 {len(chapters)} 个章节")
    
    # 为每个章节生成摘要
    chapter_summaries = []
    full_summary = ""
    
    for i, chapter in enumerate(chapters):
        logger.info(f"正在处理章节 {i+1}/{len(chapters)}: {chapter['title']}")
        
        # 生成摘要
        summary = generate_summary(
            chapter["content"], 
            model, 
            tokenizer, 
            device, 
            max_length,
            max_summary_length
        )
        
        # 添加章节标题
        chapter_summary = f"{chapter['title']}\n{summary}\n\n"
        full_summary += chapter_summary
        
        # 保存章节摘要信息
        chapter_info = {
            "title": chapter["title"],
            "summary": summary,
            "original_length": chapter["original_length"],
            "summary_length": len(summary),
            "compression_ratio": len(summary) / chapter["original_length"] if chapter["original_length"] > 0 else 0
        }
        chapter_summaries.append(chapter_info)
    
    return {
        "full_summary": full_summary,
        "chapters": chapter_summaries
    }

def summarize_full_text(content: str, model: Any, tokenizer: Any, device: str, 
                       max_length: int, max_summary_length: int = 300) -> Dict[str, Any]:
    """
    生成全文摘要
    """
    # 生成摘要
    summary = generate_summary(
        content, 
        model, 
        tokenizer, 
        device, 
        max_length,
        max_summary_length
    )
    
    # 创建章节信息
    chapter_info = {
        "title": "全文摘要",
        "summary": summary,
        "original_length": len(content),
        "summary_length": len(summary),
        "compression_ratio": len(summary) / len(content) if len(content) > 0 else 0
    }
    
    return {
        "full_summary": summary,
        "chapters": [chapter_info]
    }

def main():
    """测试函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="基于Transformer的小说摘要生成器")
    parser.add_argument("--file_path", type=str, required=True, help="小说文件路径")
    parser.add_argument("--model", type=str, default="bart-base-chinese", 
                        choices=list(AVAILABLE_MODELS.keys()), help="预训练模型")
    parser.add_argument("--by_chapter", action="store_true", help="按章节生成摘要")
    parser.add_argument("--max_summary_length", type=int, default=150, help="摘要最大长度")
    parser.add_argument("--output_path", type=str, help="输出文件路径")
    parser.add_argument("--device", type=str, choices=["cpu", "cuda"], help="计算设备")
    
    args = parser.parse_args()
    
    # 读取文件
    content = read_file(args.file_path)
    logger.info(f"文件读取完成，总长度: {len(content)} 字符")
    
    # 加载模型
    model, tokenizer, device, max_length = load_model(args.model, args.device)
    logger.info(f"模型加载完成，使用设备: {device}")
    
    # 生成摘要
    if args.by_chapter:
        logger.info("按章节生成摘要...")
        result = summarize_by_chapter(
            content, 
            model, 
            tokenizer, 
            device, 
            max_length,
            args.max_summary_length
        )
    else:
        logger.info("生成全文摘要...")
        result = summarize_full_text(
            content, 
            model, 
            tokenizer, 
            device, 
            max_length,
            args.max_summary_length * 2
        )
    
    # 输出摘要
    if args.output_path:
        with open(args.output_path, 'w', encoding='utf-8-sig') as f:
            f.write(result["full_summary"])
        logger.info(f"摘要已保存到: {args.output_path}")
    else:
        print("\n" + "="*50 + " 摘要 " + "="*50)
        print(result["full_summary"])
        print("="*110)

if __name__ == "__main__":
    main() 