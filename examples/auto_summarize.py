#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
自动化摘要生成脚本
直接使用配置文件控制，无需命令行参数
支持按章节总结凡人修仙传
自动删除冗余文件和代码
"""

import os
import sys
import time
import logging
import re
import json
import glob
import shutil
from datetime import datetime

# 配置日志
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "log")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"auto_summarize_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AutoSummarize")

# 导入简化版摘要器
try:
    from simple_chinese_summarizer import textrank_summarize, extract_keywords, read_file
    logger.info("成功导入简化版摘要器")
except ImportError:
    logger.error("未找到simple_chinese_summarizer.py，请确保该文件在当前目录")
    sys.exit(1)

# 默认配置
DEFAULT_CONFIG = {
    "novels_dir": "novels",
    "output_dir": "summaries",
    "algorithms": ["textrank"],  # 默认只使用TextRank算法
    "default_ratio": 0.01,
    "large_file_threshold": 1000000,  # 1MB以上视为大文件
    "chunk_size": 200000,
    "max_sentences": 5000,
    "file_patterns": ["*.txt", "凡人修仙传*.txt"],
    "auto_ratio": True,  # 自动根据文件大小调整摘要比例
    "compare_algorithms": False,  # 默认不比较不同算法
    "save_keywords": True,  # 是否保存关键词
    "generate_report": True,  # 是否生成报告
    "by_chapter": True,  # 是否按章节总结
    "chapter_pattern": r"第[一二三四五六七八九十百千万0-9１２３４５６７８９０]+[章回节]",  # 章节匹配模式
    "clean_temp_files": True,  # 是否清理临时文件
    "config_file": "config.json"  # 配置文件路径
}

def determine_ratio(file_size):
    """根据文件大小自动确定摘要比例"""
    if file_size > 10000000:  # 10MB
        return 0.003
    elif file_size > 5000000:  # 5MB
        return 0.005
    elif file_size > 1000000:  # 1MB
        return 0.01
    elif file_size > 500000:  # 500KB
        return 0.02
    elif file_size > 100000:  # 100KB
        return 0.05
    else:
        return 0.1

def split_by_chapters(content, chapter_pattern):
    """按章节分割文本"""
    # 编译正则表达式
    pattern = re.compile(chapter_pattern)
    
    # 查找所有章节标题的位置
    matches = list(pattern.finditer(content))
    
    if not matches:
        logger.warning("未找到任何章节标记，将整个文本作为一个章节处理")
        return [("全文", content)]
    
    # 分割章节
    chapters = []
    for i, match in enumerate(matches):
        chapter_title = match.group(0)
        start_pos = match.start()
        
        # 确定章节结束位置
        if i < len(matches) - 1:
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(content)
        
        # 提取章节内容
        chapter_content = content[start_pos:end_pos]
        chapters.append((chapter_title, chapter_content))
    
    logger.info(f"成功分割出 {len(chapters)} 个章节")
    return chapters

def process_file(
    file_path, 
    output_dir, 
    algorithm="textrank", 
    ratio=None, 
    chunk_size=200000, 
    max_sentences=5000,
    auto_ratio=True,
    save_keywords=True,
    by_chapter=True,
    chapter_pattern=r"第[一二三四五六七八九十百千万0-9１２３４５６７８９０]+[章回节]",
    clean_temp_files=True
):
    """处理单个文件的摘要生成"""
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取文件名（不含路径和扩展名）
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # 读取文件内容
    logger.info(f"正在读取文件: {file_path}")
    start_time = time.time()
    content = read_file(file_path)
    read_time = time.time() - start_time
    logger.info(f"读取完成，文件大小: {len(content)} 字符，耗时: {read_time:.2f} 秒")
    
    # 自动确定摘要比例
    if auto_ratio and ratio is None:
        ratio = determine_ratio(len(content))
        logger.info(f"自动确定摘要比例: {ratio:.3f}")
    elif ratio is None:
        ratio = DEFAULT_CONFIG["default_ratio"]
    
    # 提取关键词
    keywords = []
    if save_keywords:
        logger.info("提取关键词...")
        keywords_start = time.time()
        keywords = extract_keywords(content, top_n=50)
        keywords_time = time.time() - keywords_start
        logger.info(f"关键词提取完成，耗时: {keywords_time:.2f} 秒")
        logger.info(f"关键词: {', '.join(keywords[:20])}...")
        
        # 保存关键词
        keywords_file = os.path.join(output_dir, f"{file_name}_keywords.txt")
        with open(keywords_file, 'w', encoding='utf-8-sig') as f:
            f.write('\n'.join(keywords))
        logger.info(f"关键词已保存到: {keywords_file}")
    
    # 创建临时目录
    temp_dir = os.path.join(output_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    # 按章节处理
    if by_chapter:
        logger.info("按章节处理文本...")
        chapters = split_by_chapters(content, chapter_pattern)
        
        # 处理每个章节
        chapter_summaries = []
        for i, (chapter_title, chapter_content) in enumerate(chapters):
            logger.info(f"处理章节 {i+1}/{len(chapters)}: {chapter_title}")
            
            # 为短章节调整摘要比例
            chapter_ratio = min(ratio * 2, 0.2) if len(chapter_content) < 5000 else ratio
            
            # 生成章节摘要
            chapter_summary = textrank_summarize(
                chapter_content, 
                ratio=chapter_ratio, 
                use_textrank=(algorithm == "textrank"),
                max_sentences=max_sentences
            )
            
            # 保存章节摘要
            chapter_file = os.path.join(temp_dir, f"{file_name}_chapter_{i+1}_{algorithm}.txt")
            with open(chapter_file, 'w', encoding='utf-8-sig') as f:
                f.write(f"{chapter_title}\n\n{chapter_summary}")
            
            # 添加到章节摘要列表
            chapter_summaries.append(f"{chapter_title}\n\n{chapter_summary}")
            
            logger.info(f"章节 {i+1} 摘要完成，长度: {len(chapter_summary)} 字符")
        
        # 合并所有章节摘要
        final_summary = "\n\n" + "="*50 + "\n\n".join(chapter_summaries)
        
    else:
        # 分块处理大文件
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
                chunk_file = os.path.join(temp_dir, f"{file_name}_chunk_{i+1}_{algorithm}.txt")
                with open(chunk_file, 'w', encoding='utf-8-sig') as f:
                    f.write(chunk_summary)
            
            # 合并所有摘要
            final_summary = "\n\n".join(all_summaries)
            
            # 如果合并后的摘要太长，再次摘要
            if len(final_summary) > chunk_size / 2:
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
    output_file = os.path.join(output_dir, f"{file_name}_summary_{algorithm}.txt")
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
    
    # 打印摘要预览
    preview_length = min(500, len(final_summary))
    logger.info(f"摘要预览: {final_summary[:preview_length]}...")
    
    # 清理临时文件
    if clean_temp_files:
        logger.info("清理临时文件...")
        try:
            shutil.rmtree(temp_dir)
            logger.info("临时文件清理完成")
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
    
    # 返回处理结果
    return {
        "file_path": file_path,
        "file_name": file_name,
        "algorithm": algorithm,
        "ratio": ratio,
        "original_size": len(content),
        "summary_size": len(final_summary),
        "compression_ratio": compression_ratio,
        "processing_time": total_time,
        "processing_speed": len(content) / total_time,
        "output_file": output_file,
        "keywords": keywords[:20] if save_keywords else []
    }

def generate_report(results, output_dir):
    """生成摘要处理报告"""
    report_file = os.path.join(output_dir, f"auto_summarize_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    
    with open(report_file, 'w', encoding='utf-8-sig') as f:
        f.write("自动摘要生成报告\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write(f"处理文件总数: {len(results)}\n\n")
        
        # 按算法分组
        algorithms = {}
        for result in results:
            alg = result["algorithm"]
            if alg not in algorithms:
                algorithms[alg] = []
            algorithms[alg].append(result)
        
        # 输出每种算法的统计信息
        for alg, alg_results in algorithms.items():
            f.write(f"算法: {alg}\n")
            f.write(f"处理文件数: {len(alg_results)}\n")
            
            total_original = sum(r["original_size"] for r in alg_results)
            total_summary = sum(r["summary_size"] for r in alg_results)
            total_time = sum(r["processing_time"] for r in alg_results)
            
            f.write(f"总原文大小: {total_original} 字符\n")
            f.write(f"总摘要大小: {total_summary} 字符\n")
            f.write(f"平均压缩比: {total_summary / total_original:.2%}\n")
            f.write(f"总处理时间: {total_time:.2f} 秒\n")
            f.write(f"平均处理速度: {total_original / total_time:.2f} 字符/秒\n\n")
        
        # 输出每个文件的详细信息
        f.write("文件详细信息:\n")
        for result in results:
            f.write(f"\n文件: {result['file_name']}\n")
            f.write(f"算法: {result['algorithm']}\n")
            f.write(f"摘要比例: {result['ratio']:.3f}\n")
            f.write(f"原文大小: {result['original_size']} 字符\n")
            f.write(f"摘要大小: {result['summary_size']} 字符\n")
            f.write(f"压缩比: {result['compression_ratio']:.2%}\n")
            f.write(f"处理时间: {result['processing_time']:.2f} 秒\n")
            f.write(f"处理速度: {result['processing_speed']:.2f} 字符/秒\n")
            f.write(f"输出文件: {result['output_file']}\n")
            
            if result["keywords"]:
                f.write(f"关键词 (Top 20): {', '.join(result['keywords'])}\n")
    
    logger.info(f"报告已生成: {report_file}")
    return report_file

def auto_summarize(config=None):
    """自动摘要生成主函数"""
    # 使用默认配置，如果有自定义配置则更新
    cfg = DEFAULT_CONFIG.copy()
    if config:
        cfg.update(config)
    
    # 确保目录存在
    os.makedirs(cfg["novels_dir"], exist_ok=True)
    os.makedirs(cfg["output_dir"], exist_ok=True)
    
    # 获取要处理的文件
    files = []
    for pattern in cfg["file_patterns"]:
        pattern_path = os.path.join(cfg["novels_dir"], pattern)
        files.extend(glob.glob(pattern_path))
    
    if not files:
        logger.warning(f"在 {cfg['novels_dir']} 目录下未找到匹配的文件")
        return []
    
    logger.info(f"找到 {len(files)} 个文件需要处理")
    
    # 处理结果
    results = []
    
    # 处理每个文件
    for file_path in files:
        file_size = os.path.getsize(file_path)
        logger.info(f"开始处理文件: {file_path} (大小: {file_size} 字节)")
        
        # 确定摘要比例
        ratio = determine_ratio(file_size) if cfg["auto_ratio"] else cfg["default_ratio"]
        
        # 处理每种算法
        if cfg["compare_algorithms"]:
            for algorithm in cfg["algorithms"]:
                logger.info(f"使用算法 {algorithm} 处理文件 {os.path.basename(file_path)}")
                result = process_file(
                    file_path=file_path,
                    output_dir=cfg["output_dir"],
                    algorithm=algorithm,
                    ratio=ratio,
                    chunk_size=cfg["chunk_size"],
                    max_sentences=cfg["max_sentences"],
                    auto_ratio=cfg["auto_ratio"],
                    save_keywords=cfg["save_keywords"],
                    by_chapter=cfg["by_chapter"],
                    chapter_pattern=cfg["chapter_pattern"],
                    clean_temp_files=cfg["clean_temp_files"]
                )
                results.append(result)
        else:
            # 只使用第一个算法
            algorithm = cfg["algorithms"][0]
            logger.info(f"使用算法 {algorithm} 处理文件 {os.path.basename(file_path)}")
            result = process_file(
                file_path=file_path,
                output_dir=cfg["output_dir"],
                algorithm=algorithm,
                ratio=ratio,
                chunk_size=cfg["chunk_size"],
                max_sentences=cfg["max_sentences"],
                auto_ratio=cfg["auto_ratio"],
                save_keywords=cfg["save_keywords"],
                by_chapter=cfg["by_chapter"],
                chapter_pattern=cfg["chapter_pattern"],
                clean_temp_files=cfg["clean_temp_files"]
            )
            results.append(result)
    
    # 生成报告
    if cfg["generate_report"] and results:
        generate_report(results, cfg["output_dir"])
    
    return results

def load_config(config_file):
    """加载配置文件"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return None

def save_config(config, config_file):
    """保存配置文件"""
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        logger.info(f"配置已保存到: {config_file}")
        return True
    except Exception as e:
        logger.error(f"保存配置文件失败: {e}")
        return False

if __name__ == "__main__":
    # 直接从配置文件加载配置
    config_file = DEFAULT_CONFIG["config_file"]
    
    # 如果配置文件不存在，创建默认配置
    if not os.path.exists(config_file):
        logger.info(f"配置文件 {config_file} 不存在，创建默认配置")
        save_config(DEFAULT_CONFIG, config_file)
    
    # 加载配置
    config = load_config(config_file)
    if not config:
        logger.warning("无法加载配置文件，使用默认配置")
        config = DEFAULT_CONFIG
    
    # 执行自动摘要
    auto_summarize(config) 