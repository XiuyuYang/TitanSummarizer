#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TitanSummarizer - 用户界面
支持中文小说等长文本的摘要生成
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import time
import logging
import torch
from pathlib import Path
import datetime
import re
import json
import traceback

# 导入辅助函数模块
from get_model_name import get_model_name, get_model_display_name, get_folder_size, get_readable_size

# 导入摘要生成器
try:
    from titan_summarizer import TitanSummarizer
except ImportError:
    print("警告: 找不到titan_summarizer模块，模型加载功能可能不可用")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("TitanUI")

# 创建进度专用日志器
progress_logger = logging.getLogger("progress")
progress_logger.setLevel(logging.INFO)

# 全局变量，用于保存加载窗口的引用
loading_window = None

# 创建专门的进度条日志记录器
progress_logger = logging.getLogger("progress_logger")
progress_logger.setLevel(logging.DEBUG)

# 确保logs目录存在
if not os.path.exists("logs"):
    os.makedirs("logs")

# 创建带时间戳的日志文件名
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
progress_log_file = f"logs/progress_{timestamp}.log"

# 添加文件处理器
progress_file_handler = logging.FileHandler(progress_log_file, encoding="utf-8")
progress_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
progress_logger.addHandler(progress_file_handler)

# 确保不会传递到父级logger
progress_logger.propagate = False

# 记录初始日志
progress_logger.info(f"===== 进度条日志开始记录 =====")
progress_logger.info(f"日志文件: {progress_log_file}")

# 使用从get_model_name模块导入的函数

class SettingsWindow:
    def __init__(self, parent, settings):
        self.window = tk.Toplevel(parent)
        self.window.title("设置")
        self.window.geometry("500x500")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        
        # 保存设置引用
        self.settings = settings
        
        # 创建主框架
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建设置选项
        self.create_settings(main_frame)
        
        # 创建按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(
            button_frame,
            text="保存",
            command=self.save_settings
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            button_frame,
            text="取消",
            command=self.window.destroy
        ).pack(side=tk.RIGHT, padx=5)
        
    def create_settings(self, parent):
        # 模型设置
        model_frame = ttk.LabelFrame(parent, text="模型设置", padding="10")
        model_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(model_frame, text="默认模型:").grid(row=0, column=0, sticky=tk.W)
        self.model_var = tk.StringVar(value=self.settings.get("default_model", "1.5B"))
        model_options = ["small", "medium", "large", "1.5B", "6B", "7B", "13B"]  # 使用固定的选项列表
        model_combo = ttk.Combobox(
            model_frame,
            textvariable=self.model_var,
            values=model_options,
            state="readonly",
            width=30
        )
        model_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # 设备设置
        ttk.Label(model_frame, text="默认设备:").grid(row=1, column=0, sticky=tk.W)
        self.device_var = tk.StringVar(value=self.settings.get("default_device", "GPU"))
        device_combo = ttk.Combobox(
            model_frame,
            textvariable=self.device_var,
            values=["GPU", "CPU"],
            state="readonly",
            width=30
        )
        device_combo.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # 摘要设置
        summary_frame = ttk.LabelFrame(parent, text="摘要设置", padding="10")
        summary_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(summary_frame, text="默认摘要长度:").grid(row=0, column=0, sticky=tk.W)
        self.length_var = tk.StringVar(value=str(self.settings.get("default_length", 20)))
        ttk.Entry(summary_frame, textvariable=self.length_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # 章节设置
        chapter_frame = ttk.LabelFrame(parent, text="章节设置", padding="10")
        chapter_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(chapter_frame, text="章节标题模式:").grid(row=0, column=0, sticky=tk.W)
        self.chapter_pattern_var = tk.StringVar(value=self.settings.get("chapter_pattern", r"第[零一二三四五六七八九十百千万]+章"))
        ttk.Entry(chapter_frame, textvariable=self.chapter_pattern_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # 翻译设置
        translate_frame = ttk.LabelFrame(parent, text="翻译设置", padding="10")
        translate_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(translate_frame, text="目标语言:").grid(row=0, column=0, sticky=tk.W)
        self.target_lang_var = tk.StringVar(value=self.settings.get("target_language", "English"))
        lang_combo = ttk.Combobox(
            translate_frame,
            textvariable=self.target_lang_var,
            values=["English", "Japanese", "Korean", "French", "German"],
            state="readonly",
            width=30
        )
        lang_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # 界面设置
        ui_frame = ttk.LabelFrame(parent, text="界面设置", padding="10")
        ui_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.theme_var = tk.StringVar(value=self.settings.get("theme", "clam"))
        ttk.Label(ui_frame, text="主题:").grid(row=0, column=0, sticky=tk.W)
        theme_combo = ttk.Combobox(
            ui_frame,
            textvariable=self.theme_var,
            values=["clam", "alt", "default", "classic"],
            state="readonly",
            width=30
        )
        theme_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        
    def save_settings(self):
        """保存设置"""
        try:
            self.settings.update({
                "default_model": self.model_var.get(),
                "default_device": self.device_var.get(),
                "default_length": int(self.length_var.get()),
                "chapter_pattern": self.chapter_pattern_var.get(),
                "target_language": self.target_lang_var.get(),
                "theme": self.theme_var.get()
            })
            
            # 保存到文件
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
                
            self.window.destroy()
            messagebox.showinfo("成功", "设置已保存")
            
        except Exception as e:
            messagebox.showerror("错误", f"保存设置失败: {str(e)}")

class AboutWindow:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("关于")
        self.window.geometry("400x300")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        
        # 创建主框架
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(
            main_frame,
            text="TitanSummarizer",
            font=('Microsoft YaHei UI', 16, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        # 版本
        version_label = ttk.Label(
            main_frame,
            text="版本 1.0.0",
            font=('Microsoft YaHei UI', 10)
        )
        version_label.pack(pady=(0, 20))
        
        # 描述
        desc_text = """
TitanSummarizer 是一个强大的文本摘要系统，
专门用于处理中文小说等长文本的摘要生成。

主要特点：
• 支持多种预训练模型
• 智能章节划分
• 实时生成摘要
• 多语言翻译
• 专业级用户界面
• 丰富的自定义选项

作者：Your Name
        """
        
        desc_label = ttk.Label(
            main_frame,
            text=desc_text,
            font=('Microsoft YaHei UI', 10),
            justify=tk.LEFT
        )
        desc_label.pack(pady=(0, 20))
        
        # 关闭按钮
        ttk.Button(
            main_frame,
            text="关闭",
            command=self.window.destroy
        ).pack()

class ChapterListWindow:
    def __init__(self, parent, chapters, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("章节列表")
        self.window.geometry("800x600")
        self.window.transient(parent)
        self.window.grab_set()
        
        # 创建主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建工具栏
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        # 搜索框
        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_chapters)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        
        # 按钮
        button_frame = ttk.Frame(toolbar)
        button_frame.pack(side=tk.RIGHT)
        
        ttk.Button(
            button_frame,
            text="全选",
            command=lambda: self.select_all(True)
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="取消全选",
            command=lambda: self.select_all(False)
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="生成选中章节摘要",
            command=lambda: self.generate_selected(callback)
        ).pack(side=tk.LEFT, padx=5)
        
        # 创建章节列表
        self.chapter_vars = {}
        self.chapters = chapters
        self.chapter_list = ttk.Treeview(
            main_frame,
            columns=("title", "length", "status"),
            show="headings"
        )
        self.chapter_list.heading("title", text="章节标题")
        self.chapter_list.heading("length", text="长度")
        self.chapter_list.heading("status", text="状态")
        self.chapter_list.column("title", width=500)
        self.chapter_list.column("length", width=100)
        self.chapter_list.column("status", width=100)
        self.chapter_list.pack(fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.chapter_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chapter_list.configure(yscrollcommand=scrollbar.set)
        
        # 添加章节
        self.refresh_chapters()
            
    def refresh_chapters(self):
        """刷新章节列表"""
        # 清空列表
        for item in self.chapter_list.get_children():
            self.chapter_list.delete(item)
            
        # 添加章节
        for i, chapter in enumerate(self.chapters):
            status = "已生成" if chapter.get("summary") else "未生成"
            self.chapter_list.insert("", tk.END, values=(
                chapter["title"],
                f"{len(chapter['content'])}字",
                status
            ))
            self.chapter_vars[i] = tk.BooleanVar(value=True)
            
    def filter_chapters(self, *args):
        """根据搜索文本过滤章节"""
        search_text = self.search_var.get().lower()
        
        # 清空列表
        for item in self.chapter_list.get_children():
            self.chapter_list.delete(item)
            
        # 添加匹配的章节
        for i, chapter in enumerate(self.chapters):
            if search_text in chapter["title"].lower():
                status = "已生成" if chapter.get("summary") else "未生成"
                self.chapter_list.insert("", tk.END, values=(
                    chapter["title"],
                    f"{len(chapter['content'])}字",
                    status
                ))
                self.chapter_vars[i] = tk.BooleanVar(value=True)
            
    def select_all(self, value):
        """全选/取消全选"""
        for var in self.chapter_vars.values():
            var.set(value)
            
    def generate_selected(self, callback):
        """生成选中章节的摘要"""
        selected = []
        for i, var in self.chapter_vars.items():
            if var.get():
                selected.append(i)
        if selected:
            callback(selected)
            self.refresh_chapters()

class StdoutRedirector:
    """用于重定向标准输出到Tkinter窗口"""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""
        self.line_buffer = []
        # 保存原始stdout便于调试输出
        self.original_stdout = sys.stdout
        
    def write(self, string):
        # 同时输出到原始stdout，便于命令行调试
        self.original_stdout.write(string)
        self.original_stdout.flush()
        
        # 将输入添加到缓冲区
        self.buffer += string
        
        # 处理换行或回车
        if '\n' in self.buffer or '\r' in self.buffer:
            # 如果包含回车符，可能是进度条更新
            if '\r' in self.buffer and '|' in self.buffer and '%' in self.buffer:
                # 提取最后一个进度条行
                lines = self.buffer.split('\r')
                progress_line = lines[-1].strip()
                
                if progress_line:
                    # 过滤掉不完整的行
                    if self._is_progress_bar(progress_line):
                        # 发送到UI
                        self._update_ui_with_progress(progress_line)
                        
                # 保留最后一行为缓冲区
                self.buffer = progress_line if progress_line else ""
            else:
                # 正常的换行处理
                lines = self.buffer.split('\n')
                # 保留最后一个可能不完整的行
                self.buffer = lines[-1]
                
                # 处理完整的行
                for line in lines[:-1]:
                    if line.strip():  # 忽略空行
                        self._update_ui_with_text(line)
                        
    def _update_ui_with_progress(self, progress_line):
        """更新UI显示进度条"""
        try:
            self.text_widget.config(state=tk.NORMAL)
            
            # 尝试找到并替换最后一个进度条行
            found = False
            progress_line_index = 0
            
            # 检查是否有存在的进度条行
            for i in range(10):
                tag_name = f"progress_line_{i}"
                line_ranges = self.text_widget.tag_ranges(tag_name)
                if line_ranges:
                    # 替换已有的进度条行
                    self.text_widget.delete(line_ranges[0], line_ranges[1])
                    self.text_widget.insert(line_ranges[0], progress_line, (tag_name, "progress"))
                    found = True
                    progress_line_index = i
                    break
            
            if not found:
                # 如果没有找到进度条行，添加新行
                progress_line_index = 0
                current_end = self.text_widget.index(tk.END)
                line_start = f"{float(current_end) - 0.1}"
                tag_name = f"progress_line_{progress_line_index}"
                self.text_widget.insert(tk.END, progress_line + "\n", (tag_name, "progress"))
            
            # 尝试提取进度百分比
            self._extract_and_update_progress(progress_line)
            
            # 确保进度条行可见
            self.text_widget.see(tk.END)
            self.text_widget.config(state=tk.DISABLED)
            self.text_widget.update_idletasks()
        except Exception as e:
            self.original_stdout.write(f"更新进度条失败: {e}\n")
            
    def _update_ui_with_text(self, text):
        """更新UI显示普通文本"""
        try:
            # 添加到窗口
            self.text_widget.config(state=tk.NORMAL)
            
            # 确定文本类型
            tag = "info"
            if "error" in text.lower() or "失败" in text:
                tag = "error"
            elif "warning" in text.lower() or "警告" in text:
                tag = "warning"
            elif "success" in text.lower() or "成功" in text:
                tag = "success"
            elif self._is_progress_bar(text):
                tag = "progress"
                # 尝试提取进度百分比
                self._extract_and_update_progress(text)
            
            # 添加文本
            self.text_widget.insert(tk.END, text + "\n", tag)
            
            # 滚动到底部并更新UI
            self.text_widget.see(tk.END)
            self.text_widget.config(state=tk.DISABLED)
            self.text_widget.update_idletasks()
        except Exception as e:
            self.original_stdout.write(f"更新文本失败: {e}\n")
            
    def _extract_and_update_progress(self, text):
        """从进度条文本中提取百分比并更新进度条"""
        try:
            # 查找窗口引用
            window = self.text_widget.master
            while not isinstance(window, LoadingWindow) and hasattr(window, 'master'):
                window = window.master
                
            if isinstance(window, LoadingWindow):
                # 尝试提取百分比
                if '%' in text:
                    parts = text.split('%', 1)[0].split()
                    for part in reversed(parts):
                        try:
                            # 尝试将部分转换为浮点数
                            percent = float(part)
                            if 0 <= percent <= 100:
                                window.update_progress(percent / 100.0)
                                break
                        except ValueError:
                            continue
        except Exception as e:
            self.original_stdout.write(f"提取进度百分比失败: {e}\n")
                    
    def flush(self):
        # 刷新原始stdout
        self.original_stdout.flush()
        
        # 处理缓冲区中的剩余内容
        if self.buffer:
            if self._is_progress_bar(self.buffer):
                self._update_ui_with_progress(self.buffer)
            else:
                self._update_ui_with_text(self.buffer)
            self.buffer = ""
                
    def _is_progress_bar(self, text):
        """检查文本是否是进度条"""
        return "%" in text and ("|" in text or "bar" in text.lower())

class LoadingWindow:
    def __init__(self, parent):
        """初始化加载窗口"""
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("模型加载中")
        self.window.geometry("800x600")
        self.window.resizable(True, True)
        
        # 窗口居中
        self.window.update_idletasks()
        window_width = self.window.winfo_width()
        window_height = self.window.winfo_height()
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.window.geometry(f"+{x}+{y}")
        
        # 创建主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="正在加载模型", font=("TkDefaultFont", 14, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 状态信息
        self.status_label = ttk.Label(main_frame, text="正在准备下载模型...")
        self.status_label.pack(pady=(0, 5))
        
        # 模型路径信息
        models_dir = os.path.join(os.getcwd(), "models")
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=(0, 5))
        path_label = ttk.Label(path_frame, text="模型存储路径:")
        path_label.pack(side=tk.LEFT)
        path_value = ttk.Label(path_frame, text=models_dir)
        path_value.pack(side=tk.LEFT, padx=(5, 0))
        
        # 进度条框架
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 进度条
        self.progress_bar = ttk.Progressbar(progress_frame, length=100, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 进度百分比标签
        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 日志显示区域
        log_frame = ttk.LabelFrame(main_frame, text="日志输出")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 使用等宽字体显示日志，以确保进度条正确显示
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=20, font=('Courier New', 10))
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_text.tag_configure("info", foreground="black")
        self.log_text.tag_configure("warning", foreground="orange")
        self.log_text.tag_configure("error", foreground="red")
        self.log_text.tag_configure("success", foreground="green")
        self.log_text.tag_configure("progress", foreground="blue")
        
        # 添加进度条专用标签
        for i in range(10):
            tag_name = f"progress_line_{i}"
            self.log_text.tag_configure(tag_name, foreground="blue", font=('Courier New', 10))
        
        # 滚动条
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # 取消按钮
        self.cancel_button = ttk.Button(button_frame, text="取消", command=self.cancel)
        self.cancel_button.pack(pady=5)
        
        # 初始化取消标志
        self.cancelled = False
        
        # 创建标准输出重定向器
        self.stdout_redirector = StdoutRedirector(self.log_text)
        
    def add_log(self, message, level="info"):
        """添加日志到日志显示区域"""
        if not hasattr(self, 'log_text'):
            return
            
        try:
            # 清除结尾的\r和\r\n，保持消息整洁
            while message.endswith('\r') or message.endswith('\n'):
                message = message.rstrip('\r\n')
                
            # 如果消息为空，不处理
            if not message:
                return
                
            self.log_text.config(state=tk.NORMAL)
            
            # 检查是否是进度条消息
            is_progress_bar = ("%" in message and 
                              ("|" in message or "bar" in message.lower()) and 
                              "[" in message and 
                              "]" in message)
            
            if is_progress_bar:
                # 尝试找到消息中的最后一行(可能包含\r)
                if '\r' in message:
                    message = message.split('\r')[-1]
                
                # 对于进度条消息，使用等宽字体显示
                self.log_text.insert(tk.END, message + "\n", "progress")
                
                # 尝试提取进度百分比
                try:
                    percent_part = message.split("%")[0]
                    # 取最后一个数字作为百分比
                    for word in reversed(percent_part.split()):
                        if word.replace('.', '', 1).isdigit() and word.count('.') <= 1:
                            percent = float(word)
                            self.update_progress(percent / 100.0)
                            break
                except Exception:
                    pass
            else:
                # 普通日志消息
                self.log_text.insert(tk.END, message + "\n", level)
            
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
            
            # 同时打印到控制台以便调试
            print(f"[UI日志-{level}] {message}")
            
            # 更新UI响应
            self.window.update_idletasks()
        except Exception as e:
            print(f"添加日志出错: {e}")
            
    def update_progress(self, progress):
        """更新进度条"""
        try:
            # 确保进度值在0-1之间
            progress = max(0.0, min(1.0, progress))
            progress_percent = int(progress * 100)
            
            self.progress_bar['value'] = progress_percent
            self.progress_label.config(text=f"{progress_percent}%")
            
            # 更新状态文本
            if progress < 0.3:
                self.status_label.config(text="正在准备模型...")
            elif progress < 0.6:
                self.status_label.config(text="正在下载模型文件...")
            elif progress < 0.9:
                self.status_label.config(text="正在加载模型...")
            else:
                self.status_label.config(text="模型加载完成")
                
            self.window.update_idletasks()
        except Exception as e:
            print(f"更新进度条出错: {e}")
    
    def cancel(self):
        """取消加载"""
        try:
            # 设置取消标志
            self.cancelled = True
            self.add_log("用户取消模型加载", "warning")
            
            # 禁用取消按钮，防止重复点击
            self.cancel_button.config(state=tk.DISABLED)
            
            # 更新状态信息
            self.status_label.config(text="正在取消操作...")
            
            # 立即关闭窗口
            self.window.after(500, self.close)
        except Exception as e:
            print(f"取消操作失败: {e}")
            # 尝试直接关闭
            self.close()
        
    def close(self):
        """关闭窗口"""
        try:
            # 确保恢复原始标准输出
            if hasattr(self, 'stdout_redirector') and hasattr(self.stdout_redirector, 'original_stdout'):
                sys.stdout = self.stdout_redirector.original_stdout
                
            # 销毁窗口
            self.window.destroy()
        except Exception as e:
            print(f"关闭窗口出错: {e}")

class TitanUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TitanSummarizer - 大文本摘要系统")
        
        # 设置窗口大小和位置
        window_width = 1200
        window_height = 800
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 创建日志记录器
        self.logger = logging.getLogger("titan_ui")
        
        # 状态栏变量 - 确保在方法调用前初始化
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        
        # 加载设置
        self.settings = self.load_settings()
        
        # 初始化变量
        self.novel_path = None
        self.novel_content = ""
        self.chapters = []
        self.current_chapter_index = -1
        self.summarizer = None
        
        # 创建UI组件
        self.create_menu()
        self.create_widgets()
        
        # 状态栏
        self.status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            font=('Microsoft YaHei UI', 9),
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 加载默认小说 - 在状态栏创建后调用
        self.load_default_novel()
        
        # 记录初始化完成
        self.logger.info("TitanUI初始化完成")
        
    def load_settings(self):
        """加载设置"""
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {
                "default_model": "1.5B",
                "default_device": "GPU" if torch.cuda.is_available() else "CPU",
                "default_length": 20,
                "chapter_pattern": r"第[零一二三四五六七八九十百千万]+章",
                "target_language": "English",
                "theme": "clam"
            }
            
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="选择小说", command=self.select_novel)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="清空摘要", command=self.clear_summary)
        
        # 设置菜单
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(label="选项", command=self.show_settings)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)
        
    def create_widgets(self):
        """创建UI组件"""
        # 创建主框架
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建顶部控制栏
        self.create_control_bar()
        
        # 创建文本区域
        self.create_text_areas()
        
    def create_control_bar(self):
        """创建控制栏"""
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 模型选择
        ttk.Label(control_frame, text="模型:").pack(side=tk.LEFT, padx=5)
        self.model_var = tk.StringVar(value=self.settings.get("default_model", "1.5B"))
        model_options = ["small", "medium", "large", "1.5B", "6B", "7B", "13B"]  # 使用固定的选项列表
        model_combo = ttk.Combobox(
            control_frame,
            textvariable=self.model_var,
            values=model_options,
            state="readonly",
            width=20
        )
        model_combo.pack(side=tk.LEFT, padx=5)
        
        # 设备选择
        ttk.Label(control_frame, text="设备:").pack(side=tk.LEFT, padx=5)
        self.device_var = tk.StringVar(value=self.settings.get("default_device", "GPU"))
        device_combo = ttk.Combobox(
            control_frame,
            textvariable=self.device_var,
            values=["GPU", "CPU"],
            state="readonly",
            width=10
        )
        device_combo.pack(side=tk.LEFT, padx=5)
        
        # 加载模型按钮
        self.load_button = ttk.Button(
            control_frame,
            text="加载模型",
            command=self.load_model
        )
        self.load_button.pack(side=tk.LEFT, padx=5)
        
        # 生成/停止按钮
        self.generate_button = ttk.Button(
            control_frame,
            text="生成摘要",
            command=self.toggle_generation
        )
        self.generate_button.pack(side=tk.LEFT, padx=5)
        
        # 语言选择
        ttk.Label(control_frame, text="目标语言:").pack(side=tk.LEFT, padx=5)
        self.target_lang_var = tk.StringVar(value=self.settings.get("target_language", "English"))
        lang_combo = ttk.Combobox(
            control_frame,
            textvariable=self.target_lang_var,
            values=["English", "Japanese", "Korean", "French", "German"],
            state="readonly",
            width=15
        )
        lang_combo.pack(side=tk.LEFT, padx=5)
        
        # 翻译按钮
        self.translate_button = ttk.Button(
            control_frame,
            text="翻译",
            command=self.translate_text
        )
        self.translate_button.pack(side=tk.LEFT, padx=5)
        
        # 设置按钮状态
        self.update_button_states()
        
    def create_text_areas(self):
        """创建文本区域"""
        # 创建左右分栏
        paned = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧章节列表区域
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        chapter_label_frame = ttk.LabelFrame(left_frame, text="章节列表")
        chapter_label_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建章节列表
        self.chapter_list = ttk.Treeview(
            chapter_label_frame,
            columns=("title", "length", "status"),
            show="headings"
        )
        self.chapter_list.heading("title", text="章节标题")
        self.chapter_list.heading("length", text="长度")
        self.chapter_list.heading("status", text="状态")
        self.chapter_list.column("title", width=300)
        self.chapter_list.column("length", width=100)
        self.chapter_list.column("status", width=100)
        self.chapter_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 绑定点击事件
        self.chapter_list.bind("<<TreeviewSelect>>", self.on_chapter_select)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(chapter_label_frame, orient=tk.VERTICAL, command=self.chapter_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chapter_list.configure(yscrollcommand=scrollbar.set)
        
        # 右侧区域
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        
        # 创建上下分栏
        right_paned = ttk.PanedWindow(right_frame, orient=tk.VERTICAL)
        right_paned.pack(fill=tk.BOTH, expand=True)
        
        # 原文区域
        original_frame = ttk.Frame(right_paned)
        right_paned.add(original_frame, weight=2)
        
        original_label_frame = ttk.LabelFrame(original_frame, text="原文")
        original_label_frame.pack(fill=tk.BOTH, expand=True)
        
        self.original_text = scrolledtext.ScrolledText(
            original_label_frame,
            wrap=tk.WORD,
            font=('Microsoft YaHei UI', 10)
        )
        self.original_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 摘要区域
        summary_frame = ttk.Frame(right_paned)
        right_paned.add(summary_frame, weight=1)
        
        summary_label_frame = ttk.LabelFrame(summary_frame, text="摘要")
        summary_label_frame.pack(fill=tk.BOTH, expand=True)
        
        self.summary_text = scrolledtext.ScrolledText(
            summary_label_frame,
            wrap=tk.WORD,
            font=('Microsoft YaHei UI', 10)
        )
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def update_button_states(self, enable=True):
        """更新界面按钮状态"""
        try:
            # 更新生成摘要按钮状态
            if hasattr(self, "generate_button"):
                if enable and self.summarizer:
                    self.generate_button.config(state=tk.NORMAL)
                else:
                    self.generate_button.config(state=tk.DISABLED)
                    
            # 更新翻译按钮状态
            if hasattr(self, "translate_button"):
                if enable and self.summarizer:
                    self.translate_button.config(state=tk.NORMAL)
                else:
                    self.translate_button.config(state=tk.DISABLED)
                    
            # 更新加载按钮状态 - 总是可用
            if hasattr(self, "load_button"):
                self.load_button.config(state=tk.NORMAL)
                
            logger.debug(f"按钮状态已更新: enable={enable}")
        except Exception as e:
            logger.error(f"更新按钮状态失败: {str(e)}")

    def get_novel_files(self):
        """获取novels目录中的所有小说文件"""
        novel_files = []
        if os.path.exists("novels"):
            novel_files = [f for f in os.listdir("novels") if f.endswith(".txt")]
        return novel_files

    def load_default_novel(self):
        """加载默认小说"""
        try:
            # 查找可能的小说文件
            default_candidates = [
                "novels/凡人修仙传_完整版.txt",
                "novels/凡人修仙传.txt"
            ]
            
            # 添加novels目录下的所有小说文件
            for novel_file in self.get_novel_files():
                default_candidates.append(f"novels/{novel_file}")
            
            # 尝试加载小说文件
            for novel_path in default_candidates:
                if os.path.exists(novel_path):
                    self.update_status(f"正在加载默认小说: {novel_path}")
                    self.load_novel(novel_path)
                    return
            
            # 如果没有找到小说文件
            self.update_status("未找到默认小说文件，请将小说文件放入novels目录")
            
        except Exception as e:
            self.update_status(f"加载默认小说失败: {str(e)}")

    def load_novel(self, file_path: str):
        """加载小说文件"""
        try:
            self.update_status(f"正在加载小说: {file_path}")
            
            # 尝试使用不同编码读取文件
            content = None
            encodings = ['utf-8', 'gb2312', 'gbk', 'gb18030', 'big5', 'latin-1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    logger.error(f"读取文件时发生错误: {str(e)}")
                    continue
            
            if not content:
                logger.error("所有编码均无法读取文件内容")
                self.update_status("无法读取文件，请检查文件编码")
                return
                
            # 清空章节列表
            for item in self.chapter_list.get_children():
                self.chapter_list.delete(item)
            
            # 分割章节
            self.chapters = []
            pattern = r"第[零一二三四五六七八九十百千万]+章\s*[^\n]+"
            matches = list(re.finditer(pattern, content))
            
            if not matches:
                # 尝试其他模式
                other_patterns = [
                    r"第\s*\d+章\s*[^\n]+",    # 第 123章 标题
                    r"第\d+章\s*[^\n]+",       # 第123章 标题
                    r"Chapter\s*\d+\s*[^\n]+"  # Chapter 123 标题
                ]
                
                for pattern in other_patterns:
                    matches = list(re.finditer(pattern, content))
                    if matches:
                        break
            
            if not matches:
                self.update_status("未检测到章节，请检查文件格式")
                logger.error("尝试所有模式后仍未检测到章节")
                return
                
            # 处理第一章之前的内容
            if matches[0].start() > 0:
                self.chapters.append({
                    'title': "前言",
                    'content': content[:matches[0].start()].strip(),
                    'summary': None
                })
            
            # 处理所有章节
            chapter_count = 0
            for i in range(len(matches)):
                start = matches[i].start()
                end = matches[i + 1].start() if i < len(matches) - 1 else len(content)
                
                chapter_title = matches[i].group().strip()
                chapter_content = content[start:end].strip()
                
                self.chapters.append({
                    'title': chapter_title,
                    'content': chapter_content,
                    'summary': None
                })
                chapter_count += 1
            
            # 更新章节列表
            for i, chapter in enumerate(self.chapters):
                title = chapter['title'].split('\n')[0]  # 只显示第一行作为标题
                length = len(chapter['content'])
                status = "已生成" if chapter.get("summary") else "未生成"
                self.chapter_list.insert("", "end", values=(title, f"{length}字", status))
                
            self.update_status(f"成功加载小说，共{len(self.chapters)}章")
            logger.info(f"成功加载小说，共{len(self.chapters)}章")
            
            # 保存当前小说路径
            self.novel_path = file_path
            
        except Exception as e:
            self.update_status(f"加载小说失败: {str(e)}")
            logger.error(f"加载小说失败: {str(e)}", exc_info=True)
        
    def load_model(self):
        """加载模型"""
        try:
            # 获取模型大小和设备设置
            model_size = self.model_var.get()
            device = "cuda" if self.device_var.get() == "GPU" and torch.cuda.is_available() else "cpu"
            
            # 创建加载窗口
            loading_window = LoadingWindow(self.root)
            
            # 启动后台线程加载模型
            threading.Thread(
                target=self.load_model_task, 
                args=(loading_window, model_size, device), 
                daemon=True
            ).start()
            
        except Exception as e:
            self.logger.error(f"加载模型时发生错误: {str(e)}")
            messagebox.showerror("错误", f"加载模型失败: {str(e)}")
    
    def load_model_task(self, loading_window, model_size, device):
        """在后台线程中加载模型的任务"""
        # 保存原始标准输出
        original_stdout = sys.stdout
        
        try:
            # 重定向标准输出到UI
            sys.stdout = loading_window.stdout_redirector
            
            # 添加初始日志
            loading_window.add_log("开始加载模型...", "info")
            loading_window.add_log(f"模型规格: {model_size}", "info")
            loading_window.add_log(f"设备: {device}", "info")
            
            # 显示模型将下载到的路径
            models_dir = os.path.join(os.getcwd(), "models")
            loading_window.add_log(f"模型将下载到: {models_dir}", "info")
            
            # 创建progress_callback函数来更新UI
            def progress_callback(progress, message, file_progress=None):
                # 检查是否取消 - 如果取消了立即返回True
                if loading_window.cancelled:
                    loading_window.add_log("检测到取消请求，停止模型加载", "warning")
                    return True  # 返回True以通知TitanSummarizer停止加载
                
                # 处理不同类型的消息
                if isinstance(message, str):
                    # 正常的消息字符串
                    loading_window.add_log(message)
                elif isinstance(progress, str):
                    # 有时候Transformers库会将进度条字符串作为第一个参数传递
                    loading_window.add_log(progress)
                
                # 如果有数值进度，更新进度条
                if isinstance(progress, (int, float)) and 0 <= progress <= 1:
                    loading_window.update_progress(progress)
                
                # 返回取消状态
                return loading_window.cancelled
            
            # 创建TitanSummarizer实例并加载模型
            self.summarizer = None  # 重置之前的实例
            
            # 如果用户取消了，提前结束
            if loading_window.cancelled:
                loading_window.add_log("加载过程被取消", "warning")
                sys.stdout = original_stdout
                return
                
            # 创建实例并加载模型
            try:
                loading_window.add_log("开始创建模型实例...", "info")
                self.summarizer = TitanSummarizer(model_size, device, progress_callback)
                
                # 模型加载完成后的处理
                if not loading_window.cancelled and self.summarizer is not None and hasattr(self.summarizer, 'model') and self.summarizer.model is not None:
                    loading_window.add_log("模型加载完成!", "success")
                    loading_window.update_progress(1.0)
                    
                    # 更新UI按钮状态
                    self.root.after(0, lambda: self.update_button_states(True))
                    
                    # 延迟关闭窗口，让用户有时间看到最终状态
                    time.sleep(1)
                    
                    # 如果没有取消，自动关闭窗口
                    if not loading_window.cancelled:
                        loading_window.close()
                elif loading_window.cancelled:
                    loading_window.add_log("模型加载被用户取消", "warning")
            except KeyboardInterrupt:
                loading_window.add_log("模型加载被中断", "warning")
                loading_window.cancelled = True
            except Exception as e:
                loading_window.add_log(f"模型加载过程中发生错误: {str(e)}", "error")
                loading_window.cancelled = True
                
        except Exception as e:
            # 恢复原始标准输出
            sys.stdout = original_stdout
            
            error_message = f"模型加载失败: {str(e)}"
            print(error_message)  # 输出到控制台
            
            if loading_window and not loading_window.cancelled:
                try:
                    loading_window.add_log(error_message, "error")
                    loading_window.add_log(traceback.format_exc(), "error")
                    # 延迟关闭窗口，让用户有时间看到错误信息
                    time.sleep(3)
                    loading_window.close()
                except Exception as ui_error:
                    print(f"显示错误信息失败: {ui_error}")
        finally:
            # 恢复原始标准输出
            sys.stdout = original_stdout
        
    def update_ui_after_model_loaded(self):
        """模型加载后更新UI"""
        try:
            # 启用相关按钮
            self.update_button_states(True)
            
            # 更新状态
            self.update_status("模型加载完成")
        except Exception as e:
            logger.error(f"更新UI失败: {str(e)}")

    def select_novel(self):
        """选择小说文件"""
        file_path = filedialog.askopenfilename(
            title="选择小说文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            self.load_novel(file_path)
            
    def toggle_generation(self):
        """切换生成/停止状态"""
        if self.is_generating:
            self.stop_generation()
        else:
            self.start_generation()
            
    def start_generation(self):
        """开始生成摘要"""
        if not self.summarizer:
            self.update_status("请先加载模型")
            return
            
        selected = self.chapter_list.selection()
        if not selected:
            self.update_status("请选择要生成摘要的章节")
            return
            
        self.is_generating = True
        self.generate_button.config(text="停止生成")
        self.update_status("正在生成摘要...")
        
        # 获取选中章节的索引
        indices = [self.chapter_list.index(item) for item in selected]
        
        # 添加到处理队列
        self.processing_queue.put(("generate", indices))
        
    def stop_generation(self):
        """停止生成摘要"""
        self.is_generating = False
        self.generate_button.config(text="生成摘要")
        self.update_status("已停止生成")
        
    def translate_text(self):
        """翻译文本"""
        if not self.summarizer:
            self.update_status("请先加载模型")
            return
            
        # 获取当前选中的章节
        selected = self.chapter_list.selection()
        if not selected:
            self.update_status("请选择要翻译的章节")
            return
            
        # 获取目标语言
        target_lang = self.target_lang_var.get()
        self.update_status(f"正在翻译为{target_lang}...")
        
        # 获取选中章节的索引
        indices = [self.chapter_list.index(item) for item in selected]
        
        # 添加到处理队列
        self.processing_queue.put(("translate", indices, target_lang))
        
    def process_queue(self):
        """处理队列中的任务"""
        while True:
            try:
                task = self.processing_queue.get()
                task_type = task[0]
                
                if task_type == "generate":
                    indices = task[1]
                    self.generate_chapter_summaries(indices)
                elif task_type == "translate":
                    indices, target_lang = task[1:]
                    self.translate_chapters(indices, target_lang)
                    
            except Exception as e:
                self.update_status(f"处理任务时出错: {str(e)}")
                
    def generate_chapter_summaries(self, indices: list):
        """生成选中章节的摘要"""
        for i in indices:
            if not self.is_generating:
                break
                
            chapter = self.chapters[i]
            self.summary_text.insert(tk.END, f"\n{chapter['title']}\n")
            self.summary_text.insert(tk.END, "-" * 50 + "\n")
            
            def update_callback(new_text: str):
                if self.is_generating:
                    self.root.after(0, self.update_output, new_text)
                    
            try:
                summary = self.summarizer.generate_summary(
                    chapter['content'],
                    max_length=self.settings.get("default_length", 20),
                    callback=update_callback
                )
                
                # 保存摘要
                chapter["summary"] = summary
                self.refresh_chapter_list()
                
            except Exception as e:
                self.update_status(f"生成章节摘要失败: {str(e)}")
                
        if self.is_generating:
            self.is_generating = False
            self.generate_button.config(text="生成摘要")
            self.update_status("摘要生成完成")
            
    def translate_chapters(self, indices: list, target_lang: str):
        """翻译选中章节"""
        for i in indices:
            chapter = self.chapters[i]
            
            # 翻译原文
            original_prompt = f"请将以下中文文本翻译为{target_lang}：\n\n{chapter['content']}\n\n翻译："
            
            def update_original_callback(new_text: str):
                self.root.after(0, self.update_original_translation, new_text)
                
            try:
                original_translation = self.summarizer.generate_summary(
                    original_prompt,
                    max_length=len(chapter['content']) * 2,
                    callback=update_original_callback
                )
                
                # 如果有摘要，也翻译摘要
                if chapter.get("summary"):
                    summary_prompt = f"请将以下中文文本翻译为{target_lang}：\n\n{chapter['summary']}\n\n翻译："
                    
                    def update_summary_callback(new_text: str):
                        self.root.after(0, self.update_summary_translation, new_text)
                        
                    summary_translation = self.summarizer.generate_summary(
                        summary_prompt,
                        max_length=len(chapter['summary']) * 2,
                        callback=update_summary_callback
                    )
                    
            except Exception as e:
                self.update_status(f"翻译章节失败: {str(e)}")
                
        self.update_status("翻译完成")
        
    def update_original_translation(self, text: str):
        """更新原文翻译"""
        self.original_text.delete('1.0', tk.END)
        self.original_text.insert('1.0', text)
        self.original_text.see(tk.END)
        
    def update_summary_translation(self, text: str):
        """更新摘要翻译"""
        self.summary_text.delete('1.0', tk.END)
        self.summary_text.insert('1.0', text)
        self.summary_text.see(tk.END)
        
    def update_output(self, text: str):
        """更新输出文本"""
        self.summary_text.insert(tk.END, text)
        self.summary_text.see(tk.END)
        
    def clear_summary(self):
        """清空摘要"""
        self.summary_text.delete('1.0', tk.END)
        self.update_status("已清空摘要")
        
    def update_status(self, message: str):
        """更新状态栏"""
        self.status_var.set(message)
        
    def show_settings(self):
        """显示设置窗口"""
        SettingsWindow(self.root, self.settings)
        
    def show_about(self):
        """显示关于窗口"""
        AboutWindow(self.root)
        
    def on_chapter_select(self, event):
        """章节选择事件处理"""
        selected = self.chapter_list.selection()
        if not selected:
            return
            
        # 获取选中章节的索引
        index = self.chapter_list.index(selected[0])
        chapter = self.chapters[index]
        
        # 显示原文
        self.original_text.delete('1.0', tk.END)
        self.original_text.insert('1.0', chapter['content'])
        
        # 如果有摘要，显示摘要
        if chapter.get("summary"):
            self.summary_text.delete('1.0', tk.END)
            self.summary_text.insert('1.0', chapter['summary'])
        else:
            self.summary_text.delete('1.0', tk.END)
        
    def run(self):
        """运行UI"""
        self.root.mainloop()

def main():
    """主函数"""
    try:
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("titan_ui.log", mode="w", encoding="utf-8")
            ]
        )
        
        # 确保novels目录存在
        if not os.path.exists("novels"):
            os.makedirs("novels")
            logging.info("创建novels目录")
        
        # 创建并运行应用
        root = tk.Tk()
        app = TitanUI(root)
        app.root.mainloop()
    except Exception as e:
        logging.error(f"程序启动失败: {str(e)}", exc_info=True)
        messagebox.showerror("错误", f"程序启动失败: {str(e)}")

if __name__ == "__main__":
    main() 