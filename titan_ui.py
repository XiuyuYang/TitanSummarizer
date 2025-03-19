#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TitanSummarizer UI - 大文本摘要系统界面
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import queue
import re
from pathlib import Path
from titan_summarizer import TitanSummarizer, MODELS
import torch
import json
import os
import logging
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("titan_ui.log", mode="w", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

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
        model_combo = ttk.Combobox(
            model_frame,
            textvariable=self.model_var,
            values=list(MODELS.keys()),
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

class LoadingWindow:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("模型加载中")
        self.window.geometry("500x350")  # 增加窗口高度
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        
        # 设置窗口样式
        self.window.configure(bg='#f0f0f0')
        
        # 创建主框架
        main_frame = ttk.Frame(self.window, padding="10")  # 减小内边距
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建进度区域框架 - 将所有进度相关元素组合在一起
        progress_frame = ttk.LabelFrame(main_frame, text="加载进度", padding="5")
        progress_frame.pack(fill=tk.X, pady=(0, 5))  # 减小底部间距
        
        # 总进度框架
        total_progress_frame = ttk.Frame(progress_frame)
        total_progress_frame.pack(fill=tk.X)
        
        # 总进度标签和进度条
        ttk.Label(
            total_progress_frame,
            text="总体进度:",
            font=('Microsoft YaHei UI', 9),
            width=10
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        progress_bar_frame = ttk.Frame(total_progress_frame)
        progress_bar_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(
            progress_bar_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            length=350  # 减小进度条长度
        )
        self.progress.pack(fill=tk.X)
        
        # 百分比标签
        self.percent_label = ttk.Label(
            total_progress_frame,
            text="0%",
            font=('Microsoft YaHei UI', 9),
            width=5,
            anchor='e'
        )
        self.percent_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 状态标签
        status_frame = ttk.Frame(progress_frame)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(
            status_frame,
            text="状态:",
            font=('Microsoft YaHei UI', 9),
            width=10
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        self.status_label = ttk.Label(
            status_frame,
            text="正在初始化...",
            font=('Microsoft YaHei UI', 9),
            wraplength=380
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 文件进度框架
        file_progress_frame = ttk.Frame(progress_frame)
        file_progress_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(
            file_progress_frame,
            text="文件进度:",
            font=('Microsoft YaHei UI', 9),
            width=10
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        file_bar_frame = ttk.Frame(file_progress_frame)
        file_bar_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.file_progress_var = tk.DoubleVar()
        self.file_progress = ttk.Progressbar(
            file_bar_frame,
            variable=self.file_progress_var,
            maximum=100,
            mode='determinate',
            length=350  # 减小进度条长度
        )
        self.file_progress.pack(fill=tk.X)
        
        # 文件百分比标签
        self.file_percent_label = ttk.Label(
            file_progress_frame,
            text="0%",
            font=('Microsoft YaHei UI', 9),
            width=5,
            anchor='e'
        )
        self.file_percent_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 详细信息区域
        details_frame = ttk.LabelFrame(main_frame, text="详细信息", padding="5")
        details_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.detail_label = ttk.Label(
            details_frame,
            text="准备下载模型文件...",
            font=('Microsoft YaHei UI', 9),
            foreground="#333333",
            wraplength=460,
            justify=tk.LEFT
        )
        self.detail_label.pack(fill=tk.X, expand=True, pady=(2, 2))
        
        # 日志框架 - 分配更多空间
        log_frame = ttk.LabelFrame(main_frame, text="加载日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=12,  # 增加日志区域高度
            font=('Consolas', 9),
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # 添加不同日志级别的标签颜色
        self.log_tags = {
            "INFO": "blue",
            "WARNING": "orange",
            "ERROR": "red",
            "DEBUG": "gray",
            "CRITICAL": "purple"
        }
        
        for tag, color in self.log_tags.items():
            self.log_text.tag_config(tag, foreground=color)
        
        # 取消按钮 - 移至底部
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.cancel_button = ttk.Button(
            button_frame,
            text="取消",
            command=self.cancel_loading
        )
        self.cancel_button.pack(side=tk.RIGHT)
        
        self.cancelled = False
        logger.info("加载窗口已初始化")
        
    def winfo_exists(self):
        """检查窗口是否存在"""
        try:
            return self.window.winfo_exists()
        except:
            return False
        
    def destroy(self):
        """销毁窗口"""
        try:
            if self.winfo_exists():
                self.window.destroy()
        except Exception as e:
            logger.error(f"销毁加载窗口失败: {str(e)}")
        
    def update_progress(self, percentage: int, message: str, file_percentage=None, file_detail=None):
        """更新进度和状态信息"""
        if not self.cancelled and self.window.winfo_exists():
            self.progress_var.set(percentage)
            self.percent_label.config(text=f"{percentage}%")
            self.status_label.config(text=message)
            
            # 更新文件进度（如果提供）
            if file_percentage is not None:
                self.file_progress_var.set(file_percentage)
                self.file_percent_label.config(text=f"{file_percentage}%")
                
            if file_detail:
                self.detail_label.config(text=file_detail)
                
            self.window.update_idletasks()
        
    def update_detail(self, message: str):
        """更新详细信息"""
        if not self.cancelled and self.window.winfo_exists():
            self.detail_label.config(text=message)
            self.window.update_idletasks()
        
    def add_log(self, message: str):
        """添加日志消息"""
        if not self.cancelled and self.window.winfo_exists():
            current_time = time.strftime("%H:%M:%S", time.localtime())
            
            # 提取文件下载进度信息
            file_percentage = None
            file_name = ""
            size_info = ""
            
            # 处理Hugging Face下载信息格式
            if "Downloading" in message:
                try:
                    # 从日志中提取文件名
                    if ":" in message:
                        file_parts = message.split(":")
                        if len(file_parts) > 1:
                            file_name = file_parts[0].split("Downloading")[-1].strip()
                    else:
                        # 尝试其他格式提取文件名
                        file_name_match = re.search(r"Downloading (.*)", message)
                        if file_name_match:
                            file_name = file_name_match.group(1).strip()
                    
                    # 提取进度百分比
                    if "[" in message and "]" in message:
                        percentage_str = message.split("[")[-1].split("]")[0].strip()
                        if "%" in percentage_str:
                            file_percentage = float(percentage_str.strip("%"))
                    
                    # 提取大小信息
                    if "]" in message:
                        size_part = message.split("]")[-1].strip()
                        if "/" in size_part:
                            size_info = size_part.strip()
                    
                    # 构造详细信息
                    detail_text = f"正在下载: {file_name}"
                    if size_info:
                        detail_text += f" ({size_info})"
                    
                    # 更新详细信息标签和文件进度
                    if file_name:
                        self.detail_label.config(text=detail_text)
                    
                    if file_percentage is not None:
                        self.file_progress_var.set(file_percentage)
                        self.file_percent_label.config(text=f"{file_percentage:.1f}%")
                        
                except Exception as e:
                    logger.error(f"解析下载进度失败: {str(e)}")
            
            # 处理loading file信息
            elif "loading file" in message and "from cache" in message:
                try:
                    # 提取文件名
                    file_parts = message.split("loading file")
                    if len(file_parts) > 1:
                        file_name = file_parts[1].split("from cache")[0].strip()
                        
                        # 更新详细信息标签
                        self.detail_label.config(text=f"正在加载缓存文件: {file_name}")
                except Exception as e:
                    logger.error(f"解析加载信息失败: {str(e)}")
            
            # 查找日志级别标签
            log_level = "INFO"  # 默认级别
            for level in self.log_tags.keys():
                if f"[{level}]" in message:
                    log_level = level
                    break
            
            # 启用编辑
            self.log_text.config(state=tk.NORMAL)
            
            # 添加带时间戳的日志条目
            self.log_text.insert(tk.END, f"[{current_time}] ", "")
            self.log_text.insert(tk.END, f"{message}\n", log_level)
            
            # 滚动到底部
            self.log_text.see(tk.END)
            
            # 禁用编辑
            self.log_text.config(state=tk.DISABLED)
            
            # 更新UI
            self.window.update_idletasks()
        
    def cancel_loading(self):
        """取消加载"""
        if not self.cancelled:
            self.cancelled = True
            self.add_log("[WARNING] 用户取消加载")
            logger.warning("用户取消加载模型")
            self.window.destroy()

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
        model_combo = ttk.Combobox(
            control_frame,
            textvariable=self.model_var,
            values=list(MODELS.keys()),
            state="readonly",
            width=20
        )
        model_combo.pack(side=tk.LEFT, padx=5)
        
        # 设备选择
        ttk.Label(control_frame, text="设备:").pack(side=tk.LEFT, padx=5)
        self.device_var = tk.StringVar(value=self.settings.get("default_device", "GPU" if torch.cuda.is_available() else "CPU"))
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
        
    def update_button_states(self):
        """更新按钮状态"""
        model_loaded = self.summarizer is not None
        self.generate_button.state(['disabled'] if not model_loaded else ['!disabled'])
        self.translate_button.state(['disabled'] if not model_loaded else ['!disabled'])
        
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
        """加载语言模型"""
        try:
            # 添加日志处理器，将模型加载日志发送到UI
            class UILogHandler(logging.Handler):
                def __init__(self, ui_callback):
                    super().__init__()
                    self.ui_callback = ui_callback
                    
                def emit(self, record):
                    try:
                        msg = self.format(record)
                        # 在UI线程中更新日志
                        self.ui_callback(record.levelname, msg)
                    except Exception as e:
                        print(f"UI日志处理器错误: {e}")
            
            # 显示加载窗口
            loading_window = LoadingWindow(self.root)
            
            # 添加日志到UI的函数
            def add_log_to_ui(level, msg):
                if loading_window.winfo_exists():
                    loading_window.add_log(f"[{level}] {msg}")
            
            # 为模型加载器设置日志处理器
            model_logger = logging.getLogger("titan_summarizer")
            ui_handler = UILogHandler(add_log_to_ui)
            ui_handler.setLevel(logging.INFO)
            ui_handler.setFormatter(logging.Formatter('%(message)s'))
            model_logger.addHandler(ui_handler)
            
            # 添加transformers的日志处理器
            transformers_logger = logging.getLogger("transformers.modeling_utils")
            transformers_logger.addHandler(ui_handler)
            tokenizer_logger = logging.getLogger("transformers.tokenization_utils_base")
            tokenizer_logger.addHandler(ui_handler)
            
            # 进度回调函数
            def progress_callback(progress, message, file_percentage=None):
                if loading_window.winfo_exists():
                    try:
                        # 总体进度处理
                        percentage = int(progress * 100)
                        loading_window.progress_var.set(percentage)
                        loading_window.percent_label.config(text=f"{percentage}%")
                        loading_window.status_label.config(text=message)
                        
                        # 文件进度处理 - 确保正确更新
                        if file_percentage is not None:
                            try:
                                # 确保文件百分比是浮点数并四舍五入为整数
                                fp = round(float(file_percentage))
                                
                                # 记录到日志
                                logger.debug(f"文件进度更新: {fp}%, 消息: {message}")
                                
                                # 直接更新文件进度条
                                loading_window.file_progress_var.set(fp)
                                loading_window.file_percent_label.config(text=f"{fp}%")
                                
                                # 如果包含文件名信息，更新详细信息标签
                                if "下载" in message and ":" in message:
                                    file_parts = message.split(":")
                                    if len(file_parts) >= 2:
                                        file_name = file_parts[0].split("下载")[-1].strip()
                                        detail = f"正在下载: {file_name}"
                                        
                                        # 查找大小信息
                                        if "/" in message:
                                            size_parts = message.split(":")
                                            if len(size_parts) >= 2:
                                                size_info = size_parts[1].strip()
                                                detail += f" ({size_info})"
                                                
                                        loading_window.detail_label.config(text=detail)
                            except Exception as e:
                                logger.error(f"处理文件进度失败: {str(e)}, 原始值: {file_percentage}")
                        
                        # 强制更新UI
                        loading_window.window.update_idletasks()
                    except Exception as e:
                        logger.error(f"更新进度UI失败: {str(e)}")
            
            # 显示初始化消息
            loading_window.update_progress(0, "正在初始化模型加载...")
            loading_window.add_log("[INFO] 开始加载模型...")
            
            # 创建后台任务加载模型
            def load_model_task():
                try:
                    # 记录开始时间
                    start_time = time.time()
                    
                    # 初始化模型
                    model_size = self.model_var.get()  # 使用UI中选择的模型大小
                    device = "cuda" if self.device_var.get() == "GPU" and torch.cuda.is_available() else "cpu"
                    loading_window.add_log(f"[INFO] 使用设备: {device}")
                    loading_window.add_log(f"[INFO] 模型大小: {model_size}")
                    
                    self.summarizer = TitanSummarizer(
                        model_size=model_size,
                        device=device,
                        progress_callback=progress_callback
                    )
                    
                    # 记录完成时间
                    elapsed_time = time.time() - start_time
                    loading_window.add_log(f"[INFO] 模型加载完成，耗时: {elapsed_time:.2f}秒")
                    loading_window.update_progress(100, "模型加载完成!", 100)
                    
                    # 稍作延迟后关闭加载窗口
                    time.sleep(1)
                    if loading_window.winfo_exists():
                        loading_window.destroy()
                    
                    # 更新UI状态
                    self.root.after(0, lambda: self.update_status("模型加载完成"))
                    self.root.after(0, self.update_button_states)
                except Exception as e:
                    error_msg = f"模型加载失败: {str(e)}"
                    self.logger.error(error_msg)
                    
                    if loading_window.winfo_exists():
                        loading_window.add_log(f"[ERROR] {error_msg}")
                        loading_window.update_progress(0, "模型加载失败!", 0)
                        # 稍作延迟后关闭加载窗口
                        time.sleep(3)
                        loading_window.destroy()
                    
                    # 更新UI状态
                    self.root.after(0, lambda: self.update_status(error_msg))
                finally:
                    # 移除UI日志处理器
                    model_logger.removeHandler(ui_handler)
                    transformers_logger.removeHandler(ui_handler)
                    tokenizer_logger.removeHandler(ui_handler)
            
            # 启动后台线程
            threading.Thread(target=load_model_task, daemon=True).start()
            
        except Exception as e:
            error_msg = f"启动模型加载失败: {str(e)}"
            self.logger.error(error_msg)
            self.update_status(error_msg)
            
            # 如果加载窗口还存在，关闭它
            try:
                if 'loading_window' in locals() and loading_window.winfo_exists():
                    loading_window.destroy()
            except:
                pass
        
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