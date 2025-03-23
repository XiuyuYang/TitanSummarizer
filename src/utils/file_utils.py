#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文件处理工具模块
提供文件和目录操作的实用函数
"""

import os
import re
import json
import logging
from typing import List, Dict, Tuple, Optional, Any

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def read_text_file(file_path: str, encoding: str = 'utf-8') -> str:
    """
    读取文本文件内容
    
    Args:
        file_path: 文件路径
        encoding: 编码格式
        
    Returns:
        文件内容
    """
    encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'ascii']
    
    # 如果指定了编码，优先使用指定的编码
    if encoding != 'utf-8':
        encodings_to_try.insert(0, encoding)
    
    # 尝试不同的编码
    for enc in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=enc) as file:
                content = file.read()
            return content
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.error(f"读取文件 {file_path} 失败: {e}")
            return f"[读取文件错误: {str(e)}]"
    
    # 如果所有编码都失败，使用二进制模式读取
    try:
        with open(file_path, 'rb') as file:
            content = file.read().decode('utf-8', errors='replace')
        return content
    except Exception as e:
        logger.error(f"读取文件 {file_path} 失败（二进制模式）: {e}")
        return f"[读取文件错误: {str(e)}]"

def save_text_file(file_path: str, content: str, encoding: str = 'utf-8') -> bool:
    """
    保存文本到文件
    
    Args:
        file_path: 文件路径
        content: 文件内容
        encoding: 编码格式
        
    Returns:
        是否成功保存
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        with open(file_path, 'w', encoding=encoding) as file:
            file.write(content)
        return True
    except Exception as e:
        logger.error(f"保存文件 {file_path} 失败: {e}")
        return False

def load_json_file(file_path: str, default: Any = None) -> Any:
    """
    加载JSON文件
    
    Args:
        file_path: 文件路径
        default: 如果加载失败，返回的默认值
        
    Returns:
        JSON对象，或者默认值
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        return default
    except Exception as e:
        logger.error(f"加载JSON文件 {file_path} 失败: {e}")
        return default

def save_json_file(file_path: str, data: Any, indent: int = 4) -> bool:
    """
    保存数据到JSON文件
    
    Args:
        file_path: 文件路径
        data: 要保存的数据
        indent: JSON缩进
        
    Returns:
        是否成功保存
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=indent)
        return True
    except Exception as e:
        logger.error(f"保存JSON文件 {file_path} 失败: {e}")
        return False

def find_files(
    directory: str,
    extensions: List[str] = ['.txt'],
    recursive: bool = True
) -> List[str]:
    """
    在指定目录中查找指定扩展名的文件
    
    Args:
        directory: 目录路径
        extensions: 文件扩展名列表
        recursive: 是否递归搜索子目录
        
    Returns:
        文件路径列表
    """
    file_list = []
    
    # 确保扩展名以.开头
    extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]
    
    try:
        if recursive:
            for root, _, files in os.walk(directory):
                for file in files:
                    if any(file.lower().endswith(ext.lower()) for ext in extensions):
                        file_list.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path) and any(file.lower().endswith(ext.lower()) for ext in extensions):
                    file_list.append(file_path)
                    
        # 排序文件列表
        file_list.sort()
        
        return file_list
    except Exception as e:
        logger.error(f"查找文件时出错: {e}")
        return []

def extract_chapter_info(
    file_path: str,
    content: Optional[str] = None
) -> Tuple[str, int]:
    """
    从文件路径和内容中提取章节标题和索引
    
    Args:
        file_path: 文件路径
        content: 文件内容，如果为None则读取文件
        
    Returns:
        (章节标题, 章节索引)
    """
    # 提取文件名
    file_name = os.path.basename(file_path)
    
    # 如果没有提供内容，则读取文件
    if content is None:
        content = read_text_file(file_path)
        
    # 从内容中查找可能的章节标题
    title_from_content = extract_title_from_content(content)
    
    # 如果从内容中找到了标题，使用它
    if title_from_content:
        title = title_from_content
    else:
        # 否则，从文件名中提取
        title = extract_title_from_filename(file_name)
        
    # 提取章节索引
    chapter_index = extract_chapter_index(file_name)
    
    return title, chapter_index

def extract_title_from_content(content: str) -> str:
    """
    从文本内容中提取标题
    
    Args:
        content: 文本内容
        
    Returns:
        提取的标题
    """
    if not content:
        return ""
    
    # 尝试提取第一行作为标题
    lines = content.strip().split('\n')
    if not lines:
        return ""
    
    first_line = lines[0].strip()
    
    # 如果第一行看起来像标题（少于50个字符），返回它
    if len(first_line) < 50:
        # 检查是否包含章节标识
        if re.search(r'第[0-9一二三四五六七八九十百千万]+[章节卷集部篇]', first_line):
            return first_line
            
        # 检查是否为短标题
        if 5 <= len(first_line) <= 30:
            return first_line
    
    # 在前3行中查找章节标记
    for i in range(min(3, len(lines))):
        line = lines[i].strip()
        if re.search(r'第[0-9一二三四五六七八九十百千万]+[章节卷集部篇]', line):
            return line
    
    return ""

def extract_title_from_filename(file_name: str) -> str:
    """
    从文件名中提取标题
    
    Args:
        file_name: 文件名
        
    Returns:
        提取的标题
    """
    # 移除扩展名
    name_without_ext = os.path.splitext(file_name)[0]
    
    # 尝试提取章节标记
    chapter_match = re.search(r'第[0-9一二三四五六七八九十百千万]+[章节卷集部篇]', name_without_ext)
    if chapter_match:
        # 查找章节标记之后的标题
        title_part = name_without_ext[chapter_match.start():]
        # 如果有其他标点符号，截取到该标点
        title_end = re.search(r'[,.，。、]', title_part)
        if title_end:
            return title_part[:title_end.start()]
        return title_part
    
    # 如果没有找到章节标记，使用文件名作为标题
    return name_without_ext

def extract_chapter_index(file_name: str) -> int:
    """
    从文件名中提取章节索引
    
    Args:
        file_name: 文件名
        
    Returns:
        章节索引
    """
    # 尝试从文件名中提取数字
    digits = re.findall(r'\d+', file_name)
    
    if digits:
        # 假设第一组数字是章节索引
        try:
            return int(digits[0])
        except ValueError:
            pass
    
    # 尝试从文件名中提取中文数字
    chinese_num_match = re.search(r'第([一二三四五六七八九十百千万]+)[章节卷集部篇]', file_name)
    if chinese_num_match:
        chinese_num = chinese_num_match.group(1)
        # 将中文数字转换为阿拉伯数字
        try:
            return convert_chinese_num(chinese_num)
        except:
            pass
    
    return 0  # 默认返回0

def convert_chinese_num(chinese_num: str) -> int:
    """
    将中文数字转换为阿拉伯数字
    
    Args:
        chinese_num: 中文数字
        
    Returns:
        阿拉伯数字
    """
    cn_num = {
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        '百': 100, '千': 1000, '万': 10000
    }
    
    # 简单情况：单个中文数字
    if chinese_num in cn_num:
        return cn_num[chinese_num]
    
    # 复杂情况
    result = 0
    temp = 0
    
    for i in range(len(chinese_num)):
        char = chinese_num[i]
        
        if char in cn_num:
            if cn_num[char] < 10:
                temp = cn_num[char]
            else:
                # 处理十、百、千等
                if temp == 0:
                    temp = 1
                result += temp * cn_num[char]
                temp = 0
    
    if temp > 0:
        result += temp
    
    return result

def split_into_chapters(content: str) -> List[Tuple[str, str]]:
    """
    将文本内容分割成章节
    
    Args:
        content: 文本内容
        
    Returns:
        章节列表，每个元素为(章节标题, 章节内容)
    """
    # 使用正则表达式匹配常见的章节标记
    pattern = r'(第[0-9一二三四五六七八九十百千万]+[章节卷集部篇].*?)\n'
    
    # 查找所有匹配
    matches = list(re.finditer(pattern, content))
    
    if not matches:
        # 如果没有找到章节标记，将整个内容作为一个章节
        return [("未命名章节", content)]
    
    chapters = []
    
    # 处理每个章节
    for i in range(len(matches)):
        # 提取章节标题
        title = matches[i].group(1).strip()
        
        # 确定章节起始位置
        start_pos = matches[i].start()
        
        # 确定章节结束位置
        if i < len(matches) - 1:
            end_pos = matches[i+1].start()
        else:
            end_pos = len(content)
        
        # 提取章节内容
        chapter_content = content[start_pos:end_pos].strip()
        
        chapters.append((title, chapter_content))
    
    return chapters

# 测试代码
def test_file_utils():
    """测试文件处理工具"""
    # 创建测试目录和文件
    test_dir = "test_files"
    os.makedirs(test_dir, exist_ok=True)
    
    # 创建测试文件
    test_file1 = os.path.join(test_dir, "第一章 测试章节.txt")
    test_content1 = """第一章 测试章节
这是一个测试章节的内容。
用于测试文件处理工具模块的功能。
"""
    
    test_file2 = os.path.join(test_dir, "chapter02.txt")
    test_content2 = """第二章 另一个测试
这是第二个测试章节的内容。
继续测试文件处理工具的功能。
"""
    
    # 保存测试文件
    save_text_file(test_file1, test_content1)
    save_text_file(test_file2, test_content2)
    
    print("===== 文件处理工具测试 =====")
    
    # 测试文件查找
    print("\n测试文件查找:")
    files = find_files(test_dir, ['.txt'], recursive=True)
    for file in files:
        print(f"- {file}")
    
    # 测试读取文件
    print("\n测试读取文件:")
    content1 = read_text_file(test_file1)
    print(f"文件内容:\n{content1}")
    
    # 测试提取章节信息
    print("\n测试提取章节信息:")
    title1, index1 = extract_chapter_info(test_file1, content1)
    print(f"文件: {test_file1}")
    print(f"提取的标题: {title1}")
    print(f"提取的索引: {index1}")
    
    title2, index2 = extract_chapter_info(test_file2)
    print(f"\n文件: {test_file2}")
    print(f"提取的标题: {title2}")
    print(f"提取的索引: {index2}")
    
    # 测试章节分割
    print("\n测试章节分割:")
    combined_content = test_content1 + "\n" + test_content2
    chapters = split_into_chapters(combined_content)
    
    print(f"分割出 {len(chapters)} 个章节:")
    for i, (title, content) in enumerate(chapters, 1):
        print(f"章节 {i}: {title}")
        print(f"内容前50个字符: {content[:50]}...")
    
    # 测试JSON操作
    print("\n测试JSON操作:")
    test_data = {
        "chapters": [
            {"title": title1, "index": index1, "content": content1},
            {"title": title2, "index": index2, "content": test_content2}
        ]
    }
    
    json_file = os.path.join(test_dir, "test.json")
    save_json_file(json_file, test_data)
    print(f"保存数据到 {json_file}")
    
    loaded_data = load_json_file(json_file)
    print(f"加载的数据包含 {len(loaded_data['chapters'])} 个章节")
    
    # 清理测试文件
    import shutil
    shutil.rmtree(test_dir)
    print("\n测试完成，已清理测试文件")

if __name__ == "__main__":
    test_file_utils() 