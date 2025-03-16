#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
批量处理多个小说文件的脚本
"""

import os
import sys
import time
import argparse
import glob
import logging
from typing import List, Dict
from datetime import datetime

# 配置日志
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "log")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"batch_summarizer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BatchSummarizer")

# 尝试导入简化版摘要器
try:
    from simple_chinese_summarizer import textrank_summarize, extract_keywords, read_file
    SIMPLE_AVAILABLE = True
    logger.info("成功导入简化版摘要器")
except ImportError:
    SIMPLE_AVAILABLE = False
    logger.warning("未找到simple_chinese_summarizer.py，将尝试使用完整版摘要器")

# 尝试导入完整版摘要器
try:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from titan_summarizer import TitanSummarizer
    TITAN_AVAILABLE = True
    logger.info("成功导入完整版摘要器")
except ImportError:
    TITAN_AVAILABLE = False
    logger.warning("未找到完整版摘要器")
    if not SIMPLE_AVAILABLE:
        logger.error("错误: 未找到任何摘要器，请确保simple_chinese_summarizer.py或titan_summarizer可用")
        sys.exit(1)

def batch_summarize(
    input_dir: str,
    output_dir: str,
    file_pattern: str = "*.txt",
    ratio: float = 0.05,
    algorithm: str = "textrank",
    use_titan: bool = False
) -> Dict[str, Dict]:
    """
    批量处理多个小说文件
    
    Args:
        input_dir: 输入目录
        output_dir: 输出目录
        file_pattern: 文件匹配模式
        ratio: 摘要占原文的比例
        algorithm: 摘要算法
        use_titan: 是否使用完整版摘要器
        
    Returns:
        处理结果统计
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"输出目录: {output_dir}")
    
    # 查找所有匹配的文件
    file_pattern_path = os.path.join(input_dir, file_pattern)
    files = glob.glob(file_pattern_path)
    
    if not files:
        logger.warning(f"未找到匹配的文件: {file_pattern_path}")
        return {}
    
    logger.info(f"找到 {len(files)} 个文件，开始处理...")
    
    # 初始化完整版摘要器（如果需要）
    if use_titan and TITAN_AVAILABLE:
        logger.info(f"使用完整版摘要器，算法: {algorithm}")
        if algorithm == "textrank" or algorithm == "tfidf":
            # 使用抽取式摘要
            summarizer = TitanSummarizer(
                strategy="extractive",
                extractive_ratio=ratio
            )
        else:
            # 使用指定的策略
            summarizer = TitanSummarizer(
                model_name="facebook/bart-large-cnn",
                strategy=algorithm,
                chunk_size=2000,
                overlap=200,
                min_length=int(100 * ratio),
                max_length=int(500 * ratio)
            )
    
    # 处理结果统计
    results = {}
    
    # 处理每个文件
    for file_path in files:
        file_name = os.path.basename(file_path)
        logger.info(f"处理文件: {file_name}")
        
        # 读取文件内容
        try:
            if SIMPLE_AVAILABLE:
                content = read_file(file_path)
            else:
                # 如果没有导入read_file函数，则使用内部实现
                encodings = ['utf-8', 'gbk', 'gb18030']
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()
                            logger.info(f"成功使用{encoding}编码读取文件")
                            break
                    except UnicodeDecodeError:
                        continue
                else:
                    logger.error(f"无法读取文件{file_path}，跳过")
                    continue
        except Exception as e:
            logger.error(f"读取文件{file_path}时出错: {str(e)}，跳过")
            continue
        
        logger.info(f"文件大小: {len(content)} 字符")
        
        # 提取关键词
        try:
            keywords = extract_keywords(content, top_n=20)
            logger.info(f"关键词: {', '.join(keywords[:10])}...")
        except Exception as e:
            logger.error(f"提取关键词失败: {str(e)}")
            keywords = []
        
        # 生成摘要
        start_time = time.time()
        
        try:
            if use_titan and TITAN_AVAILABLE:
                # 使用完整版摘要器
                summary = summarizer.summarize(content)
            else:
                # 使用简化版摘要器
                summary = textrank_summarize(
                    content, 
                    ratio=ratio, 
                    use_textrank=(algorithm == "textrank")
                )
            
            elapsed_time = time.time() - start_time
            
            # 保存摘要
            output_file = os.path.join(output_dir, f"{file_name}_summary_{algorithm}.txt")
            with open(output_file, 'w', encoding='utf-8-sig') as f:
                f.write(summary)
            
            # 记录结果
            results[file_name] = {
                "original_size": len(content),
                "summary_size": len(summary),
                "ratio": len(summary) / len(content),
                "time": elapsed_time,
                "speed": len(content) / elapsed_time,
                "keywords": keywords[:10]
            }
            
            # 打印结果
            logger.info(f"摘要生成完成!")
            logger.info(f"摘要长度: {len(summary)} 字符")
            logger.info(f"压缩比: {len(summary) / len(content):.2%}")
            logger.info(f"耗时: {elapsed_time:.2f} 秒")
            logger.info(f"处理速度: {len(content) / elapsed_time:.2f} 字符/秒")
            logger.info(f"摘要已保存到: {output_file}")
        except Exception as e:
            logger.error(f"生成摘要时出错: {str(e)}")
            continue
    
    # 生成汇总报告
    if results:
        report_path = os.path.join(output_dir, "summary_report.txt")
        with open(report_path, 'w', encoding='utf-8-sig') as f:
            f.write(f"摘要生成报告\n")
            f.write(f"算法: {algorithm}\n")
            f.write(f"目标比例: {ratio:.2%}\n")
            f.write(f"处理文件数: {len(files)}\n\n")
            
            f.write(f"{'文件名':<30} {'原始大小':<10} {'摘要大小':<10} {'压缩比':<10} {'耗时(秒)':<10} {'速度(字符/秒)':<15}\n")
            f.write("-" * 85 + "\n")
            
            for file_name, result in results.items():
                compression_ratio = f"{result['ratio']:.2%}"
                processing_time = f"{result['time']:.2f}"
                processing_speed = f"{result['speed']:.2f}"
                f.write(f"{file_name:<30} {result['original_size']:<10} {result['summary_size']:<10} "
                       f"{compression_ratio:<10} {processing_time:<10} {processing_speed:<15}\n")
        
        logger.info(f"汇总报告已保存到: {report_path}")
    else:
        logger.warning("没有成功处理任何文件，未生成汇总报告")
    
    return results

def main():
    parser = argparse.ArgumentParser(description='批量处理多个小说文件')
    parser.add_argument('--input_dir', type=str, required=True, help='输入目录')
    parser.add_argument('--output_dir', type=str, required=True, help='输出目录')
    parser.add_argument('--file_pattern', type=str, default="*.txt", help='文件匹配模式')
    parser.add_argument('--ratio', type=float, default=0.05, help='摘要占原文的比例')
    parser.add_argument('--algorithm', type=str, default="textrank", 
                        choices=["textrank", "tfidf", "simple", "hierarchical", "extractive", "hybrid"],
                        help='摘要算法')
    parser.add_argument('--use_titan', action='store_true', help='使用完整版摘要器')
    
    args = parser.parse_args()
    
    # 记录参数
    logger.info(f"参数: input_dir={args.input_dir}, output_dir={args.output_dir}, "
                f"file_pattern={args.file_pattern}, ratio={args.ratio}, "
                f"algorithm={args.algorithm}, use_titan={args.use_titan}")
    
    # 检查是否使用完整版摘要器
    if args.use_titan and not TITAN_AVAILABLE:
        logger.warning("未找到完整版摘要器，将使用简化版摘要器")
        args.use_titan = False
    
    # 检查算法是否可用
    if not args.use_titan and args.algorithm not in ["textrank", "tfidf"]:
        logger.warning(f"简化版摘要器不支持 {args.algorithm} 算法，将使用 textrank 算法")
        args.algorithm = "textrank"
    
    # 批量处理
    batch_summarize(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        file_pattern=args.file_pattern,
        ratio=args.ratio,
        algorithm=args.algorithm,
        use_titan=args.use_titan
    )

if __name__ == "__main__":
    main() 