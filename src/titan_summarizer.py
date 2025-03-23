#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Titan Summarizer - 主程序模块
整合所有模块功能，提供全文摘要的主要入口
"""

import os
import sys
import time
import logging
import argparse
from typing import List, Dict, Optional, Tuple, Any, Callable

# 添加src目录到sys.path，确保能正确导入模块
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# 导入模型工厂和模型模块
from models.factory import SummarizerFactory
from models.summarizer import BaseSummarizer

# 导入工具模块
from utils.file_utils import (
    read_text_file, 
    save_text_file, 
    find_files, 
    extract_chapter_info,
    split_into_chapters
)
from utils.text_utils import (
    clean_text, 
    truncate_text, 
    format_text_chunks,
    detect_language,
    count_tokens
)

# 导入进度条组件
from ui.progress_bar import create_progress_callback, ProgressBar

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("titan_summarizer.log")
    ]
)
logger = logging.getLogger("TitanSummarizer")

# 版本信息
__version__ = "1.0.0"

class TitanSummarizer:
    """
    Titan Summarizer核心类
    整合模型工厂、文件处理、文本处理等功能
    """
    
    def __init__(
        self,
        model_type: str = "deepseek-api",
        model_path: Optional[str] = None,
        api_key: Optional[str] = None,
        mock_mode: bool = False,
        max_tokens: int = 8000,
        progress_callback: Optional[Callable] = None
    ):
        """
        初始化Titan摘要器
        
        Args:
            model_type: 模型类型（deepseek-api或ollama-local）
            model_path: 模型路径（仅用于Ollama模型）
            api_key: API密钥（仅用于DeepSeek API）
            mock_mode: 是否使用模拟模式
            max_tokens: 最大标记数量
            progress_callback: 进度回调函数
        """
        self.model_type = model_type
        self.model_path = model_path
        self.api_key = api_key
        self.mock_mode = mock_mode
        self.max_tokens = max_tokens
        
        # 创建进度回调函数（如果没有提供）
        if progress_callback is None:
            self.progress_callback = create_progress_callback(
                total=100,
                prefix="处理中",
                desc="Summarizing"
            )
        else:
            self.progress_callback = progress_callback
            
        # 初始化摘要器
        self.summarizer_factory = SummarizerFactory()
        self.summarizer = self._create_summarizer()
        
        logger.info(f"初始化 TitanSummarizer v{__version__} 成功，使用模型: {model_type}")
    
    def _create_summarizer(self) -> BaseSummarizer:
        """
        创建摘要器实例
        
        Returns:
            摘要器实例
        """
        try:
            # 使用工厂创建摘要器
            summarizer = self.summarizer_factory.create_summarizer(
                model_type=self.model_type,
                model_path=self.model_path,
                api_key=self.api_key,
                use_mock=self.mock_mode,
                progress_callback=self.progress_callback
            )
            
            return summarizer
        except Exception as e:
            logger.error(f"创建摘要器失败: {e}")
            raise
    
    def summarize_text(
        self,
        text: str,
        max_length: int = 1000,
        mode: str = "generative"
    ) -> str:
        """
        对文本进行摘要
        
        Args:
            text: 要摘要的文本
            max_length: 摘要的最大长度
            mode: 摘要模式（extractive或generative）
            
        Returns:
            生成的摘要
        """
        # 清理和截断文本
        text = clean_text(text)
        
        if not text:
            return "无法摘要空文本"
            
        # 如果文本超过最大标记数，截断它
        token_count = count_tokens(text)
        if token_count > self.max_tokens:
            logger.info(f"文本过长 ({token_count} 个标记)，截断至 {self.max_tokens} 个标记")
            text = truncate_text(text, self.max_tokens)
        
        # 生成摘要
        try:
            summary = self.summarizer.generate_summary(text, max_length, mode)
            return summary
        except Exception as e:
            logger.error(f"摘要生成失败: {e}")
            return f"摘要生成失败: {str(e)}"
    
    def summarize_file(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        max_length: int = 1000,
        mode: str = "generative"
    ) -> Tuple[str, str]:
        """
        对文件内容进行摘要
        
        Args:
            file_path: 文件路径
            output_path: 输出文件路径
            max_length: 摘要的最大长度
            mode: 摘要模式
            
        Returns:
            (标题, 摘要内容)
        """
        # 读取文件内容
        content = read_text_file(file_path)
        
        if not content:
            return "无标题", "无法读取文件内容"
            
        # 提取章节标题
        title, _ = extract_chapter_info(file_path, content)
        
        if not title:
            title = os.path.basename(file_path)
        
        # 生成摘要
        self.progress_callback(0, 100, f"摘要 {title}...")
        summary = self.summarize_text(content, max_length, mode)
        self.progress_callback(100, 100, f"完成 {title}")
        
        # 保存摘要
        if output_path:
            save_text_file(
                output_path, 
                f"# {title}\n\n{summary}"
            )
            logger.info(f"摘要已保存到 {output_path}")
        
        return title, summary
    
    def summarize_directory(
        self,
        directory: str,
        output_directory: str,
        file_extensions: List[str] = ['.txt'],
        max_length: int = 1000,
        mode: str = "generative",
        recursive: bool = True
    ) -> List[Dict[str, str]]:
        """
        摘要目录中的所有文件
        
        Args:
            directory: 输入目录
            output_directory: 输出目录
            file_extensions: 要处理的文件扩展名
            max_length: 摘要的最大长度
            mode: 摘要模式
            recursive: 是否递归处理子目录
            
        Returns:
            摘要结果列表
        """
        # 查找所有文件
        files = find_files(directory, file_extensions, recursive)
        total_files = len(files)
        
        if total_files == 0:
            logger.warning(f"在目录 {directory} 中未找到任何 {file_extensions} 文件")
            return []
            
        logger.info(f"在目录 {directory} 中找到 {total_files} 个文件")
        
        # 创建输出目录
        os.makedirs(output_directory, exist_ok=True)
        
        # 处理每个文件
        results = []
        
        for i, file_path in enumerate(files):
            try:
                # 计算相对路径，保持目录结构
                rel_path = os.path.relpath(file_path, directory)
                output_path = os.path.join(
                    output_directory, 
                    f"{os.path.splitext(rel_path)[0]}_summary.md"
                )
                
                # 确保输出目录存在
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # 更新总进度
                progress_pct = int((i / total_files) * 100)
                self.progress_callback(
                    progress_pct, 
                    100, 
                    f"处理 {i+1}/{total_files}: {os.path.basename(file_path)}"
                )
                
                # 摘要文件
                title, summary = self.summarize_file(
                    file_path=file_path,
                    output_path=output_path,
                    max_length=max_length,
                    mode=mode
                )
                
                # 添加结果
                results.append({
                    "file": file_path,
                    "title": title,
                    "summary": summary,
                    "output": output_path
                })
                
            except Exception as e:
                logger.error(f"处理文件 {file_path} 时出错: {e}")
                results.append({
                    "file": file_path,
                    "title": os.path.basename(file_path),
                    "summary": f"处理失败: {str(e)}",
                    "output": None
                })
        
        # 完成进度
        self.progress_callback(100, 100, f"完成所有 {total_files} 个文件")
        
        return results
    
    def summarize_novel(
        self,
        novel_file: str,
        output_file: str,
        max_length: int = 1000,
        mode: str = "generative",
        chapter_by_chapter: bool = True
    ) -> Dict[str, Any]:
        """
        摘要小说文件，可选择按章节处理
        
        Args:
            novel_file: 小说文件路径
            output_file: 输出文件路径
            max_length: 每个章节摘要的最大长度
            mode: 摘要模式
            chapter_by_chapter: 是否按章节分别摘要
            
        Returns:
            摘要结果信息
        """
        # 读取小说内容
        content = read_text_file(novel_file)
        
        if not content:
            return {
                "success": False, 
                "message": "无法读取小说文件",
                "chapter_count": 0,
                "output_file": None
            }
        
        # 如果按章节处理，拆分成章节
        if chapter_by_chapter:
            chapters = split_into_chapters(content)
            chapter_count = len(chapters)
            
            if chapter_count == 0:
                logger.warning("未能在小说中识别出章节，将整个文件作为一个章节处理")
                chapters = [("完整小说", content)]
                chapter_count = 1
                
            logger.info(f"从小说中识别出 {chapter_count} 个章节")
            
            # 处理每个章节
            all_summaries = []
            
            for i, (title, chapter_content) in enumerate(chapters):
                try:
                    # 更新进度
                    progress_pct = int((i / chapter_count) * 100)
                    self.progress_callback(
                        progress_pct, 
                        100, 
                        f"摘要章节 {i+1}/{chapter_count}: {title}"
                    )
                    
                    # 生成章节摘要
                    summary = self.summarize_text(
                        chapter_content, 
                        max_length, 
                        mode
                    )
                    
                    # 添加到结果
                    all_summaries.append({
                        "title": title,
                        "summary": summary
                    })
                    
                except Exception as e:
                    logger.error(f"处理章节 {title} 时出错: {e}")
                    all_summaries.append({
                        "title": title,
                        "summary": f"摘要生成失败: {str(e)}"
                    })
            
            # 组合所有摘要
            novel_title = os.path.basename(novel_file)
            combined_summary = f"# {novel_title} - 摘要\n\n"
            
            for chapter in all_summaries:
                combined_summary += f"## {chapter['title']}\n\n{chapter['summary']}\n\n"
                
            # 保存摘要
            save_text_file(output_file, combined_summary)
            
            # 完成进度
            self.progress_callback(100, 100, f"完成所有 {chapter_count} 个章节")
            
            return {
                "success": True,
                "message": f"成功生成 {chapter_count} 个章节的摘要",
                "chapter_count": chapter_count,
                "output_file": output_file,
                "chapters": all_summaries
            }
            
        else:
            # 整体摘要
            novel_title = os.path.basename(novel_file)
            
            try:
                # 更新进度
                self.progress_callback(0, 100, f"摘要 {novel_title}...")
                
                # 生成摘要
                summary = self.summarize_text(content, max_length, mode)
                
                # 保存摘要
                full_summary = f"# {novel_title} - 摘要\n\n{summary}"
                save_text_file(output_file, full_summary)
                
                # 完成进度
                self.progress_callback(100, 100, "摘要完成")
                
                return {
                    "success": True,
                    "message": "成功生成小说摘要",
                    "chapter_count": 1,
                    "output_file": output_file,
                    "summary": summary
                }
                
            except Exception as e:
                logger.error(f"生成小说摘要时出错: {e}")
                return {
                    "success": False,
                    "message": f"摘要生成失败: {str(e)}",
                    "chapter_count": 0,
                    "output_file": None
                }
    
    def translate_text(
        self,
        text: str,
        target_language: str = "Chinese"
    ) -> str:
        """
        翻译文本
        
        Args:
            text: 要翻译的文本
            target_language: 目标语言
            
        Returns:
            翻译后的文本
        """
        try:
            return self.summarizer.translate_text(text, target_language)
        except AttributeError:
            return "当前模型不支持翻译功能"
        except Exception as e:
            logger.error(f"翻译文本时出错: {e}")
            return f"翻译失败: {str(e)}"
    
    def get_available_models(self) -> Dict[str, str]:
        """
        获取可用的模型类型
        
        Returns:
            模型类型和显示名称的字典
        """
        return self.summarizer_factory.get_available_models()

def get_args():
    """
    解析命令行参数
    
    Returns:
        解析的参数
    """
    parser = argparse.ArgumentParser(description="Titan Summarizer - 文本摘要工具")
    
    # 基本设置参数
    parser.add_argument("--text", type=str, help="要摘要的文本")
    parser.add_argument("--file", type=str, help="要摘要的文件路径")
    parser.add_argument("--dir", type=str, help="要摘要的目录路径")
    parser.add_argument("--novel", type=str, help="要摘要的小说文件")
    parser.add_argument("--output", type=str, help="输出文件或目录的路径")
    
    # 模型参数
    parser.add_argument("--model", type=str, default="deepseek-api", 
                       help="使用的模型类型 (deepseek-api 或 ollama-local)")
    parser.add_argument("--model-path", type=str, help="Ollama模型路径(仅用于ollama-local)")
    parser.add_argument("--api-key", type=str, help="DeepSeek API密钥(仅用于deepseek-api)")
    parser.add_argument("--mock", action="store_true", help="使用模拟模式，不调用实际API")
    
    # 摘要参数
    parser.add_argument("--max-length", type=int, default=1000, help="摘要的最大长度")
    parser.add_argument("--mode", type=str, default="generative", 
                       choices=["extractive", "generative"], help="摘要模式")
    parser.add_argument("--recursive", action="store_true", help="递归处理子目录")
    parser.add_argument("--by-chapter", action="store_true", help="按章节处理小说")
    
    # 其他参数
    parser.add_argument("--ext", type=str, default=".txt", help="处理的文件扩展名")
    parser.add_argument("--translate", type=str, help="将摘要翻译成指定语言")
    parser.add_argument("--version", action="store_true", help="显示版本信息")
    
    return parser.parse_args()

def main():
    """主程序入口"""
    args = get_args()
    
    # 显示版本信息
    if args.version:
        print(f"Titan Summarizer v{__version__}")
        return
    
    # 初始化摘要器
    try:
        summarizer = TitanSummarizer(
            model_type=args.model,
            model_path=args.model_path,
            api_key=args.api_key,
            mock_mode=args.mock
        )
    except Exception as e:
        logger.error(f"初始化摘要器失败: {e}")
        print(f"错误: {e}")
        return
    
    # 处理文本摘要
    if args.text:
        summary = summarizer.summarize_text(
            args.text,
            max_length=args.max_length,
            mode=args.mode
        )
        
        # 翻译摘要
        if args.translate:
            summary = summarizer.translate_text(summary, args.translate)
            
        # 输出摘要
        if args.output:
            save_text_file(args.output, summary)
            print(f"摘要已保存到: {args.output}")
        else:
            print("\n" + "-" * 40)
            print("摘要结果：")
            print("-" * 40)
            print(summary)
            print("-" * 40)
    
    # 处理文件摘要
    elif args.file:
        if not args.output:
            args.output = f"{os.path.splitext(args.file)[0]}_summary.md"
            
        title, summary = summarizer.summarize_file(
            args.file,
            args.output,
            args.max_length,
            args.mode
        )
        
        # 翻译摘要
        if args.translate:
            translated = summarizer.translate_text(summary, args.translate)
            
            # 保存翻译后的摘要
            translated_output = f"{os.path.splitext(args.output)[0]}_translated.md"
            save_text_file(translated_output, f"# {title}\n\n{translated}")
            print(f"翻译后的摘要已保存到: {translated_output}")
            
        print(f"摘要已保存到: {args.output}")
    
    # 处理目录摘要
    elif args.dir:
        if not args.output:
            args.output = f"{args.dir}_summaries"
            
        extensions = args.ext.split(',')
        
        results = summarizer.summarize_directory(
            args.dir,
            args.output,
            file_extensions=extensions,
            max_length=args.max_length,
            mode=args.mode,
            recursive=args.recursive
        )
        
        print(f"已处理 {len(results)} 个文件，摘要保存到: {args.output}")
        
        # 创建索引文件
        index_path = os.path.join(args.output, "index.md")
        index_content = f"# {os.path.basename(args.dir)} - 摘要索引\n\n"
        
        for item in results:
            if item["output"]:
                rel_path = os.path.relpath(item["output"], args.output)
                index_content += f"- [{item['title']}]({rel_path})\n"
        
        save_text_file(index_path, index_content)
        print(f"摘要索引已保存到: {index_path}")
    
    # 处理小说摘要
    elif args.novel:
        if not args.output:
            args.output = f"{os.path.splitext(args.novel)[0]}_summary.md"
            
        result = summarizer.summarize_novel(
            args.novel,
            args.output,
            args.max_length,
            args.mode,
            args.by_chapter
        )
        
        if result["success"]:
            print(f"小说摘要已保存到: {args.output}")
            print(f"已处理 {result['chapter_count']} 个章节")
        else:
            print(f"小说摘要生成失败: {result['message']}")
    
    # 显示帮助信息
    else:
        print("请指定要摘要的文本、文件、目录或小说。使用 --help 查看帮助。")

if __name__ == "__main__":
    main() 