#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TitanSummarizer - 大文本摘要系统
支持中文小说等长文本的摘要生成
"""

import os
import sys
import argparse
import logging
from datetime import datetime

# 配置日志
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"titan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TitanSummarizer")

# 导入简化版摘要器
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples"))
    from simple_chinese_summarizer import textrank_summarize, extract_keywords, read_file
    SIMPLE_AVAILABLE = True
    logger.info("成功导入简化版摘要器")
except ImportError:
    SIMPLE_AVAILABLE = False
    logger.warning("未找到简化版摘要器")

def main():
    parser = argparse.ArgumentParser(description='TitanSummarizer - 大文本摘要系统')
    parser.add_argument('--file_path', type=str, help='小说文件路径')
    parser.add_argument('--input_dir', type=str, help='输入目录（批量处理）')
    parser.add_argument('--output_dir', type=str, help='输出目录（批量处理）')
    parser.add_argument('--ratio', type=float, default=0.05, help='摘要占原文的比例')
    parser.add_argument('--algorithm', type=str, default="textrank", 
                        choices=["textrank", "tfidf", "simple", "hierarchical", "extractive", "hybrid"],
                        help='摘要算法')
    parser.add_argument('--batch', action='store_true', help='批量处理模式')
    parser.add_argument('--file_pattern', type=str, default="*.txt", help='文件匹配模式（批量处理）')
    
    args = parser.parse_args()
    
    # 记录参数
    logger.info(f"参数: {args}")
    
    # 检查参数
    if args.batch:
        if not args.input_dir or not args.output_dir:
            logger.error("批量处理模式需要指定--input_dir和--output_dir参数")
            sys.exit(1)
        
        # 导入批量处理模块
        try:
            from examples.batch_summarize import batch_summarize
            logger.info("成功导入批量处理模块")
            
            # 执行批量处理
            batch_summarize(
                input_dir=args.input_dir,
                output_dir=args.output_dir,
                file_pattern=args.file_pattern,
                ratio=args.ratio,
                algorithm=args.algorithm,
                use_titan=False  # 使用简化版摘要器
            )
        except ImportError:
            logger.error("未找到批量处理模块，请确保examples/batch_summarize.py存在")
            sys.exit(1)
    else:
        if not args.file_path:
            logger.error("单文件处理模式需要指定--file_path参数")
            sys.exit(1)
        
        if not SIMPLE_AVAILABLE:
            logger.error("未找到简化版摘要器，无法处理文件")
            sys.exit(1)
        
        # 读取文件
        logger.info(f"正在读取文件: {args.file_path}")
        content = read_file(args.file_path)
        logger.info(f"文件大小: {len(content)} 字符")
        
        # 提取关键词
        logger.info("提取关键词...")
        keywords = extract_keywords(content, top_n=20)
        logger.info(f"关键词: {', '.join(keywords)}")
        
        # 生成摘要
        logger.info(f"使用 {args.algorithm} 算法生成摘要，比例: {args.ratio}...")
        import time
        start_time = time.time()
        
        summary = textrank_summarize(
            content, 
            ratio=args.ratio, 
            use_textrank=(args.algorithm == "textrank")
        )
        
        elapsed_time = time.time() - start_time
        
        logger.info(f"摘要生成完成!")
        logger.info(f"摘要长度: {len(summary)} 字符")
        logger.info(f"压缩比: {len(summary) / len(content):.2%}")
        logger.info(f"耗时: {elapsed_time:.2f} 秒")
        logger.info(f"处理速度: {len(content) / elapsed_time:.2f} 字符/秒")
        
        # 保存摘要
        output_path = f"{args.file_path}_summary_{args.algorithm}.txt"
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.write(summary)
        
        logger.info(f"摘要已保存到: {output_path}")
        
        # 打印摘要预览
        preview_length = min(500, len(summary))
        logger.info(f"摘要预览: {summary[:preview_length]}...")

if __name__ == "__main__":
    main() 