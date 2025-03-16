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
    PegasusForConditionalGeneration,
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
    "mt5-small-chinese": {
        "model_name": "google/mt5-small",
        "max_length": 512,
        "type": "t5",
        "use_fast": False,  # 禁用fast tokenizer，避免protobuf错误
        "requires": ["sentencepiece"]  # 标记需要sentencepiece库
    },
    # 预留选项，暂不可用
    "longformer-chinese": {
        "model_name": "暂不可用",
        "max_length": 4096,
        "type": "longformer",
        "available": False,  # 标记为不可用
        "message": "Longformer模型暂未实现"
    },
    # 预留选项，暂不可用
    "bigbird-chinese": {
        "model_name": "暂不可用",
        "max_length": 4096,
        "type": "bigbird",
        "available": False,  # 标记为不可用
        "message": "BigBird模型暂未实现"
    }
    # 其他模型已移除
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

def check_dependencies(model_name: str) -> bool:
    """检查模型依赖是否已安装"""
    if model_name not in AVAILABLE_MODELS:
        return False
    
    model_info = AVAILABLE_MODELS[model_name]
    
    # 检查模型是否标记为不可用
    if model_info.get("available") is False:
        logger.warning(f"模型 {model_name} 暂不可用: {model_info.get('message', '未提供原因')}")
        return False
    
    required_libs = model_info.get("requires", [])
    
    for lib in required_libs:
        try:
            if lib == "sentencepiece":
                import sentencepiece
            elif lib == "protobuf":
                import google.protobuf
            # 可以添加其他依赖检查
        except ImportError:
            logger.error(f"缺少依赖库: {lib}，请使用 pip install {lib} 安装")
            return False
    
    return True

def load_model(model_name: str, device: Optional[str] = None) -> Tuple[Any, Any, str, int]:
    """
    加载预训练模型和分词器
    返回模型、分词器、设备和最大长度
    """
    if model_name not in AVAILABLE_MODELS:
        raise ValueError(f"不支持的模型: {model_name}，可用模型: {list(AVAILABLE_MODELS.keys())}")
    
    # 检查依赖
    logger.info(f"检查模型 {model_name} 的依赖...")
    if not check_dependencies(model_name):
        raise ImportError(f"模型 {model_name} 缺少必要的依赖库或暂不可用")
    
    model_info = AVAILABLE_MODELS[model_name]
    model_path = model_info["model_name"]
    max_length = model_info["max_length"]
    use_fast = model_info.get("use_fast", True)  # 默认使用fast tokenizer
    
    # 确定设备
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"将使用设备: {device}")
    
    # 加载分词器
    logger.info(f"正在加载分词器 {model_path}...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=use_fast)
        logger.info("分词器加载完成")
    except Exception as e:
        logger.error(f"加载分词器失败: {str(e)}")
        # 尝试使用慢速分词器
        logger.info("尝试使用慢速分词器...")
        tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=False)
        logger.info("慢速分词器加载完成")
    
    # 加载模型
    logger.info(f"正在加载模型 {model_path}...")
    try:
        if model_info["type"] == "bart":
            logger.info("使用BART模型架构")
            model = BartForConditionalGeneration.from_pretrained(model_path)
        elif model_info["type"] == "t5":
            logger.info("使用T5模型架构")
            model = T5ForConditionalGeneration.from_pretrained(model_path)
        elif model_info["type"] == "pegasus":
            logger.info("使用Pegasus模型架构")
            model = PegasusForConditionalGeneration.from_pretrained(model_path)
        elif model_info["type"] == "longformer":
            logger.info("使用Longformer模型架构")
            # 这里只是预留，实际上这个分支不会被执行，因为check_dependencies会先返回False
            raise NotImplementedError("Longformer模型暂未实现")
        elif model_info["type"] == "bigbird":
            logger.info("使用BigBird模型架构")
            # 这里只是预留，实际上这个分支不会被执行，因为check_dependencies会先返回False
            raise NotImplementedError("BigBird模型暂未实现")
        else:
            logger.info("使用通用Seq2Seq模型架构")
            model = AutoModelForSeq2SeqLM.from_pretrained(model_path)
        
        logger.info(f"正在将模型移动到 {device} 设备...")
        model = model.to(device)
        logger.info("模型加载完成")
    except Exception as e:
        logger.error(f"加载模型失败: {str(e)}")
        raise
    
    return model, tokenizer, device, max_length

def extract_key_sentences(text: str, num_sentences: int = 5) -> str:
    """
    从文本中提取关键句子，用于辅助摘要生成
    """
    # 分割句子
    sentences = re.split(r'([。！？])', text)
    sentences = [''.join(i) for i in zip(sentences[0::2], sentences[1::2] + [''])]
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(sentences) <= num_sentences:
        return text
    
    # 简单的重要性评分：句子长度、位置和关键词
    scores = []
    keywords = ['主要', '重要', '关键', '核心', '总结', '总之', '因此', '所以', '结论', 
                '最终', '最后', '首先', '其次', '然后', '接着', '最后']
    
    for i, sentence in enumerate(sentences):
        # 基础分数：句子长度的平方根（避免过长句子获得过高分数）
        score = (len(sentence) ** 0.5) * 0.5
        
        # 位置分数：文章开头和结尾的句子更重要
        position_score = 0
        if i < len(sentences) * 0.2:  # 前20%的句子
            position_score = 1.0 - (i / (len(sentences) * 0.2))
        elif i > len(sentences) * 0.8:  # 后20%的句子
            position_score = (i - len(sentences) * 0.8) / (len(sentences) * 0.2)
        
        # 关键词分数
        keyword_score = sum(2 for keyword in keywords if keyword in sentence)
        
        # 总分
        total_score = score + position_score * 2 + keyword_score
        scores.append((i, total_score))
    
    # 选择得分最高的句子
    top_sentences = sorted(scores, key=lambda x: x[1], reverse=True)[:num_sentences]
    top_sentences = sorted(top_sentences, key=lambda x: x[0])  # 按原始顺序排序
    
    # 组合成摘要
    summary = ''.join(sentences[i] for i, _ in top_sentences)
    return summary

def generate_summary(text: str, model: Any, tokenizer: Any, device: str, 
                    max_length: int, max_summary_length: int = 150,
                    advanced_params: Optional[Dict[str, Any]] = None) -> str:
    """
    使用Transformer模型生成摘要
    
    参数:
        text: 文本内容
        model: 预训练模型
        tokenizer: 分词器
        device: 计算设备
        max_length: 模型输入最大长度
        max_summary_length: 摘要最大长度
        advanced_params: 高级参数字典，可以包含repetition_penalty, temperature, top_p等
    """
    # 计算原文长度
    original_length = len(text)
    
    # 对于非常短的章节，调整摘要长度
    if original_length < max_summary_length * 2:
        # 如果原文不到摘要长度的2倍，将摘要长度设为原文的一半
        adjusted_max_length = max(50, original_length // 2)
        logger.info(f"原文较短 ({original_length} 字符)，调整摘要长度为 {adjusted_max_length}")
        max_summary_length = adjusted_max_length
    
    # 截断过长的文本
    if len(text) > max_length * 4:  # 估计字符数是token数的4倍
        logger.warning(f"文本过长 ({len(text)} 字符)，将被截断")
        
        # 智能截断：提取关键句子而不是简单截断
        if len(text) > max_length * 8:  # 文本非常长时
            # 提取关键句子
            key_sentences = extract_key_sentences(text, num_sentences=max(10, max_length // 50))
            # 如果提取的关键句子仍然太长，再截断
            if len(key_sentences) > max_length * 4:
                text = key_sentences[:max_length * 4]
            else:
                text = key_sentences
        else:
            text = text[:max_length * 4]
    
    # 编码文本
    inputs = tokenizer(text, return_tensors="pt", max_length=max_length, truncation=True)
    inputs = inputs.to(device)
    
    # 根据模型类型调整生成参数
    model_type = model.__class__.__name__
    
    # 计算合理的最小长度，确保生成足够长的摘要
    # 对于较大的max_summary_length，设置更大的最小长度比例
    min_length_ratio = 0.3  # 默认最小长度为最大长度的30%
    if max_summary_length > 200:
        min_length_ratio = 0.4  # 对于较长的摘要，增加最小长度比例
    if max_summary_length > 500:
        min_length_ratio = 0.5  # 对于非常长的摘要，进一步增加最小长度比例
    
    min_length = max(30, int(max_summary_length * min_length_ratio))
    
    # 基本生成参数 - 使用简单的beam search，避免参数冲突
    generation_params = {
        "max_length": max_summary_length,
        "min_length": min_length,  # 使用计算的最小长度
        "early_stopping": True,
        "no_repeat_ngram_size": 3,  # 增大不重复n-gram的大小
        "repetition_penalty": 1.5,  # 增加重复惩罚
        "length_penalty": 1.2,  # 调整长度惩罚
        "num_beams": 5  # 使用beam search
    }
    
    # 根据摘要长度调整参数
    if max_summary_length > 300:
        # 对于较长的摘要，增加beam search宽度和长度惩罚
        generation_params.update({
            "num_beams": 8,
            "length_penalty": 1.5,
            "no_repeat_ngram_size": 4  # 增大不重复n-gram的大小
        })
    
    # 根据模型类型调整特定参数
    if "Bart" in model_type:
        # BART模型特定优化
        bart_params = {
            "encoder_no_repeat_ngram_size": 3,  # BART特有参数
            "forced_bos_token_id": tokenizer.bos_token_id,  # 强制使用开始标记
            "forced_eos_token_id": tokenizer.eos_token_id,  # 强制使用结束标记
            "num_beams": generation_params["num_beams"]  # 保持一致的beam search宽度
        }
        
        # 对于较长的摘要，进一步调整BART参数
        if max_summary_length > 300:
            bart_params.update({
                "length_penalty": 2.0,  # 增加长度惩罚，鼓励生成更长的摘要
                "encoder_no_repeat_ngram_size": 4  # 增大不重复n-gram的大小
            })
            
        generation_params.update(bart_params)
    elif "T5" in model_type:
        # T5模型特定优化
        t5_params = {
            "repetition_penalty": 2.0,  # 增加重复惩罚
            "length_penalty": 1.5  # 增加长度惩罚
        }
        
        # 对于较长的摘要，进一步调整T5参数
        if max_summary_length > 300:
            t5_params.update({
                "length_penalty": 2.0,  # 增加长度惩罚
                "no_repeat_ngram_size": 4  # 增大不重复n-gram的大小
            })
            
        generation_params.update(t5_params)
    
    # 应用高级参数（如果提供）
    if advanced_params:
        logger.info(f"应用高级参数: {advanced_params}")
        generation_params.update(advanced_params)
    
    # 记录实际使用的参数
    logger.info(f"摘要生成参数: {generation_params}")
    
    # 生成摘要
    with torch.no_grad():
        summary_ids = model.generate(
            inputs["input_ids"],
            **generation_params
        )
    
    # 解码摘要
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    
    # 处理可能产生的乱码
    # 移除不可见字符和控制字符
    summary = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', summary)
    
    # 移除非中文、英文、数字和常见标点的字符
    summary = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9，。！？、：；""''（）【】《》\s]', '', summary)
    
    # 优化摘要：移除中文字符之间的多余空格
    summary = re.sub(r'(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])', '', summary)
    
    # 确保标点符号前没有空格
    summary = re.sub(r'\s+(?=[，。！？、：；])', '', summary)
    
    # 确保标点符号后的空格保持一致
    summary = re.sub(r'([，。！？、：；])\s*', r'\1 ', summary)
    
    # 移除多余的空格
    summary = re.sub(r'\s{2,}', ' ', summary)
    
    # 移除句子开头的空格
    summary = re.sub(r'^\s+', '', summary)
    summary = re.sub(r'\n\s+', '\n', summary)
    
    # 检查摘要是否只是原文的开头部分
    # 如果摘要与原文开头部分相似度过高，尝试重新生成
    if len(summary) > 20 and summary[:20] in text[:100]:
        logger.warning("摘要可能只是原文的开头部分，尝试重新生成")
        # 修改参数再次尝试 - 使用采样模式
        generation_params.update({
            "do_sample": True,  # 启用采样
            "temperature": 1.0,  # 增加温度
            "top_p": 0.95,  # 增加采样范围
            "top_k": 50,  # 增加top-k采样范围
            "repetition_penalty": 2.0,  # 增加重复惩罚
            "no_repeat_ngram_size": 4,  # 增加不重复n-gram大小
            # 保持最大和最小长度不变
            "max_length": max_summary_length,
            "min_length": generation_params["min_length"]
        })
        
        logger.info(f"重新生成摘要，参数: max_length={max_summary_length}, min_length={generation_params['min_length']}")
        
        with torch.no_grad():
            summary_ids = model.generate(
                inputs["input_ids"],
                **generation_params
            )
        
        # 解码新摘要
        new_summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        
        # 应用相同的后处理
        new_summary = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', new_summary)
        new_summary = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9，。！？、：；""''（）【】《》\s]', '', new_summary)
        new_summary = re.sub(r'(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])', '', new_summary)
        new_summary = re.sub(r'\s+(?=[，。！？、：；])', '', new_summary)
        new_summary = re.sub(r'([，。！？、：；])\s*', r'\1 ', new_summary)
        new_summary = re.sub(r'\s{2,}', ' ', new_summary)
        new_summary = re.sub(r'^\s+', '', new_summary)
        new_summary = re.sub(r'\n\s+', '\n', new_summary)
        
        # 如果新摘要看起来更好，使用它
        if len(new_summary) > 20 and new_summary[:20] not in text[:100]:
            summary = new_summary
        
        # 移除末尾可能的多余句号（如果已经有句号了）
        summary = re.sub(r'[。！？][。！？]+$', lambda m: m.group(0)[0], summary)
    
    return summary

def summarize_by_chapter(content: str, model: Any, tokenizer: Any, device: str, 
                        max_length: int, max_summary_length: int = 150, 
                        chapter_callback: Optional[callable] = None,
                        advanced_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    按章节生成摘要
    
    参数:
        content: 文本内容
        model: 预训练模型
        tokenizer: 分词器
        device: 计算设备
        max_length: 模型输入最大长度
        max_summary_length: 摘要最大长度
        chapter_callback: 章节处理完成后的回调函数，接收章节信息字典作为参数
        advanced_params: 高级参数字典，传递给generate_summary函数
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
            max_summary_length,
            advanced_params
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
            "compression_ratio": len(summary) / chapter["original_length"] if chapter["original_length"] > 0 else 0,
            "chapter_index": i,
            "total_chapters": len(chapters)
        }
        chapter_summaries.append(chapter_info)
        
        # 如果提供了回调函数，调用它
        if chapter_callback:
            continue_processing = chapter_callback(chapter_info)
            # 如果回调函数返回False，表示需要停止处理
            if continue_processing is False:
                logger.info("章节处理被用户停止")
                break
    
    return {
        "full_summary": full_summary,
        "chapters": chapter_summaries
    }

def summarize_full_text(content: str, model: Any, tokenizer: Any, device: str, 
                       max_length: int, max_summary_length: int = 300,
                       advanced_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
        max_summary_length,
        advanced_params
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