#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
针对《凡人修仙传》完整版的测试脚本
支持分块处理超长文本，并提供多种摘要算法选择
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime

# 配置日志
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "log")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"test_fanren_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TestFanrenComplete")

# 导入简化版摘要器
try:
    from simple_chinese_summarizer import textrank_summarize, extract_keywords, read_file
    logger.info("成功导入简化版摘要器")
except ImportError:
    logger.error("未找到simple_chinese_summarizer.py，请确保该文件在当前目录")
    sys.exit(1)

def test_fanren_complete(
    file_path: str,
    output_dir: str,
    ratio: float = 0.01,
    algorithm: str = "textrank",
    chunk_size: int = 10000,
    max_sentences: int = 5000
):
    """
    测试《凡人修仙传》完整版摘要生成
    
    Args:
        file_path: 小说文件路径
        output_dir: 输出目录
        ratio: 摘要占原文的比例
        algorithm: 摘要算法，可选 "textrank" 或 "tfidf"
        chunk_size: 分块大小（字符数）
        max_sentences: 最大处理句子数
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"输出目录: {output_dir}")
    
    # 读取小说内容
    logger.info(f"正在读取小说文件: {file_path}")
    start_time = time.time()
    content = read_file(file_path)
    read_time = time.time() - start_time
    logger.info(f"读取完成，文件大小: {len(content)} 字符，耗时: {read_time:.2f} 秒")
    
    # 提取关键词
    logger.info("提取关键词...")
    keywords_start = time.time()
    keywords = extract_keywords(content, top_n=50)
    keywords_time = time.time() - keywords_start
    logger.info(f"关键词提取完成，耗时: {keywords_time:.2f} 秒")
    logger.info(f"关键词: {', '.join(keywords[:20])}...")
    
    # 保存关键词
    keywords_file = os.path.join(output_dir, f"fanren_complete_keywords.txt")
    with open(keywords_file, 'w', encoding='utf-8-sig') as f:
        f.write('\n'.join(keywords))
    logger.info(f"关键词已保存到: {keywords_file}")
    
    # 分块处理
    if len(content) > chunk_size:
        logger.info(f"文件较大，将进行分块处理，每块大小: {chunk_size} 字符")
        chunks = []
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i+chunk_size]
            chunks.append(chunk)
        logger.info(f"分块完成，共 {len(chunks)} 块")
        
        # 处理每个块
        all_summaries = []
        for i, chunk in enumerate(chunks):
            logger.info(f"处理第 {i+1}/{len(chunks)} 块...")
            chunk_start = time.time()
            
            # 生成摘要
            chunk_summary = textrank_summarize(
                chunk, 
                ratio=ratio, 
                use_textrank=(algorithm == "textrank"),
                max_sentences=max_sentences
            )
            
            chunk_time = time.time() - chunk_start
            logger.info(f"第 {i+1} 块摘要生成完成，长度: {len(chunk_summary)} 字符，耗时: {chunk_time:.2f} 秒")
            all_summaries.append(chunk_summary)
            
            # 保存当前块的摘要
            chunk_file = os.path.join(output_dir, f"fanren_complete_chunk_{i+1}_{algorithm}.txt")
            with open(chunk_file, 'w', encoding='utf-8-sig') as f:
                f.write(chunk_summary)
            logger.info(f"第 {i+1} 块摘要已保存到: {chunk_file}")
        
        # 合并所有摘要
        final_summary = "\n\n".join(all_summaries)
        
        # 如果合并后的摘要太长，再次摘要
        if len(final_summary) > chunk_size:
            logger.info(f"合并后的摘要较长 ({len(final_summary)} 字符)，进行二次摘要...")
            second_summary_start = time.time()
            final_summary = textrank_summarize(
                final_summary, 
                ratio=0.5,  # 二次摘要取50%
                use_textrank=(algorithm == "textrank"),
                max_sentences=max_sentences
            )
            second_summary_time = time.time() - second_summary_start
            logger.info(f"二次摘要完成，长度: {len(final_summary)} 字符，耗时: {second_summary_time:.2f} 秒")
    else:
        # 直接处理
        logger.info("文件大小适中，直接处理...")
        summary_start = time.time()
        final_summary = textrank_summarize(
            content, 
            ratio=ratio, 
            use_textrank=(algorithm == "textrank"),
            max_sentences=max_sentences
        )
        summary_time = time.time() - summary_start
        logger.info(f"摘要生成完成，长度: {len(final_summary)} 字符，耗时: {summary_time:.2f} 秒")
    
    # 保存最终摘要
    output_file = os.path.join(output_dir, f"fanren_complete_summary_{algorithm}.txt")
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        f.write(final_summary)
    
    # 计算总体统计信息
    total_time = time.time() - start_time
    compression_ratio = len(final_summary) / len(content)
    
    logger.info(f"摘要生成完成!")
    logger.info(f"原文长度: {len(content)} 字符")
    logger.info(f"摘要长度: {len(final_summary)} 字符")
    logger.info(f"压缩比: {compression_ratio:.2%}")
    logger.info(f"总耗时: {total_time:.2f} 秒")
    logger.info(f"处理速度: {len(content) / total_time:.2f} 字符/秒")
    logger.info(f"最终摘要已保存到: {output_file}")
    
    # 生成报告
    report_file = os.path.join(output_dir, f"fanren_complete_report_{algorithm}.txt")
    with open(report_file, 'w', encoding='utf-8-sig') as f:
        f.write(f"《凡人修仙传》完整版摘要生成报告\n")
        f.write(f"算法: {algorithm}\n")
        f.write(f"目标比例: {ratio:.2%}\n")
        f.write(f"原文长度: {len(content)} 字符\n")
        f.write(f"摘要长度: {len(final_summary)} 字符\n")
        f.write(f"实际压缩比: {compression_ratio:.2%}\n")
        f.write(f"总耗时: {total_time:.2f} 秒\n")
        f.write(f"处理速度: {len(content) / total_time:.2f} 字符/秒\n\n")
        f.write(f"关键词 (Top 20):\n")
        f.write(f"{', '.join(keywords[:20])}\n\n")
        f.write(f"摘要预览 (前1000字符):\n")
        f.write(f"{final_summary[:1000]}...\n")
    
    logger.info(f"报告已保存到: {report_file}")
    
    # 打印摘要预览
    preview_length = min(500, len(final_summary))
    logger.info(f"摘要预览: {final_summary[:preview_length]}...")
    
    return final_summary

def main():
    parser = argparse.ArgumentParser(description='《凡人修仙传》完整版摘要测试')
    parser.add_argument('--file_path', type=str, default="novels/凡人修仙传_完整版.txt", help='小说文件路径')
    parser.add_argument('--output_dir', type=str, default="summaries", help='输出目录')
    parser.add_argument('--ratio', type=float, default=0.01, help='摘要占原文的比例')
    parser.add_argument('--algorithm', type=str, default="textrank", choices=["textrank", "tfidf"], help='摘要算法')
    parser.add_argument('--chunk_size', type=int, default=100000, help='分块大小（字符数）')
    parser.add_argument('--max_sentences', type=int, default=5000, help='最大处理句子数')
    
    args = parser.parse_args()
    
    # 记录参数
    logger.info(f"参数: {args}")
    
    # 测试凡人修仙传完整版
    test_fanren_complete(
        file_path=args.file_path,
        output_dir=args.output_dir,
        ratio=args.ratio,
        algorithm=args.algorithm,
        chunk_size=args.chunk_size,
        max_sentences=args.max_sentences
    )

if __name__ == "__main__":
    main() 