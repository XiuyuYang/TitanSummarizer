#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TitanSummarizer - 大文本摘要系统UI
简化版UI，专注于中文小说摘要生成
使用DeepSeek API进行云端摘要
"""

import os
import re
import json
import time
import queue
import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import sys
import io

# 导入自定义模块
from titan_summarizer import TitanSummarizer
from get_model_name import get_model_display_name, get_model_name

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("titan_ui.log", encoding="utf-8", mode="w"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("titan_ui")

class TextRedirector:
    """将标准输出重定向到文本控件"""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""
        
    def write(self, string):
        self.buffer += string
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.update()
        
    def flush(self):
        pass

class TitanUI:
    """大文本摘要系统UI"""
    
    def __init__(self, root):
        """初始化UI"""
        self.root = root
        self.root.title("TitanSummarizer - 大文本摘要系统")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 设置主题
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
            
        # 加载设置
        self.settings = self.load_settings()
        
        # 初始化变量
        self.summarizer = None
        self.novel_chapters = []
        self.current_chapter_index = None
        self.is_generating = False
        self.processing_queue = queue.Queue()
        
        # 创建菜单
        self.create_menu()
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建控制栏
        self.create_control_bar()
        
        # 创建文本区域
        self.create_text_areas()
        
        # 创建状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding="5 2"
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 尝试加载默认小说
        self.load_default_novel()
        
        # 启动处理队列线程
        threading.Thread(target=self.process_queue, daemon=True).start()
        
        # 禁用生成按钮，直到API初始化完成
        self.generate_btn.config(state=tk.DISABLED)
        self.generate_all_btn.config(state=tk.DISABLED)
        
        # 不再自动加载模型
        # self.load_model()
        
        logger.info("TitanUI初始化完成")

    def load_settings(self):
        """加载设置"""
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
                logger.info(f"成功加载设置: {settings}")
                
                # 确保设置中有deepseek-api模型
                if settings.get("default_model") not in ["deepseek-api"]:
                    settings["default_model"] = "deepseek-api"
                    logger.info("更新设置为使用DeepSeek API")
                    
                # 移除device设置
                if "default_device" in settings:
                    del settings["default_device"]
                    
                return settings
        except Exception as e:
            logger.warning(f"加载设置失败，使用默认值: {str(e)}")
            return {
                "default_model": "deepseek-api",
                "default_length": 100,
                "default_novel": "novels/凡人修仙传_完整版.txt",
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
        file_menu.add_command(label="加载API", command=self.load_model)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="清空摘要", command=self.clear_summary)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="运行API测试", command=self.run_model_test)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)
            
    def create_control_bar(self):
        """创建控制栏"""
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # 左侧控制区域
        left_controls = ttk.Frame(control_frame)
        left_controls.pack(side=tk.LEFT)

        # 模型选择区域
        model_frame = ttk.LabelFrame(left_controls, text="API设置")
        model_frame.pack(side=tk.LEFT, padx=5, pady=5)

        # 模型标签和下拉框
        ttk.Label(model_frame, text="API模型:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        # 可用模型列表 - 现在只保留DeepSeek API选项
        models = ["deepseek-api"]
        
        # 创建模型名称到显示名称的映射
        self.model_display_map = {get_model_display_name(model): model for model in models}
        
        # 设置模型显示变量
        self.model_display_var = tk.StringVar(value=get_model_display_name("deepseek-api"))
        
        # 使用显示名称作为下拉菜单选项
        self.model_var = tk.StringVar(value="deepseek-api")
        self.model_selector = ttk.Combobox(
            model_frame, 
            textvariable=self.model_display_var,
            values=list(self.model_display_map.keys()),
            width=30,
            state="readonly"
        )
        self.model_selector.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.model_selector.current(0)  # 默认选择第一个模型

        # 添加初始化API按钮
        self.load_btn = ttk.Button(
            model_frame,
            text="初始化API",
            command=self.load_model
        )
        self.load_btn.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)

        # 添加摘要模式选择
        mode_frame = ttk.LabelFrame(left_controls, text="摘要模式")
        mode_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 创建单选按钮变量和选项
        self.summary_mode = tk.StringVar(value="extractive")
        ttk.Radiobutton(
            mode_frame, 
            text="提取式摘要", 
            variable=self.summary_mode, 
            value="extractive"
        ).grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        
        ttk.Radiobutton(
            mode_frame, 
            text="生成式摘要", 
            variable=self.summary_mode, 
            value="generative"
        ).grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        
        # 添加模式说明提示
        mode_info = ttk.Label(
            mode_frame, 
            text="提示: 提取式摘要更快，生成式质量更高", 
            font=("Microsoft YaHei UI", 8)
        )
        mode_info.grid(row=2, column=0, padx=5, pady=1, sticky=tk.W)

        # 摘要长度选择区域
        length_frame = ttk.LabelFrame(left_controls, text="摘要长度")
        length_frame.pack(side=tk.LEFT, padx=5, pady=5)

        # 摘要长度标签和输入框
        ttk.Label(length_frame, text="长度限制:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.length_var = tk.StringVar(value="100")
        length_entry = ttk.Entry(length_frame, textvariable=self.length_var, width=5)
        length_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        length_entry.bind("<KeyRelease>", self.validate_length)
        ttk.Label(length_frame, text="字").grid(row=0, column=2, padx=0, pady=5, sticky=tk.W)

        # 右侧按钮区域
        right_buttons = ttk.Frame(control_frame)
        right_buttons.pack(side=tk.RIGHT)

        # 生成摘要按钮
        self.generate_btn = ttk.Button(
            right_buttons, 
            text="生成摘要", 
            command=self.generate_summary, 
            style="Accent.TButton",
            state=tk.DISABLED  # 初始状态为禁用
        )
        self.generate_btn.pack(side=tk.RIGHT, padx=5, pady=5)

        # 生成所有摘要按钮
        self.generate_all_btn = ttk.Button(
            right_buttons, 
            text="生成所有章节摘要", 
            command=self.summarize_all_chapters,
            state=tk.DISABLED  # 初始状态为禁用
        )
        self.generate_all_btn.pack(side=tk.RIGHT, padx=5, pady=5)

        # 清空摘要按钮
        ttk.Button(
            right_buttons, 
            text="清空摘要", 
            command=self.clear_summary
        ).pack(side=tk.RIGHT, padx=5, pady=5)

        # 打开文件按钮
        ttk.Button(
            right_buttons, 
            text="打开小说文件", 
            command=self.select_novel
        ).pack(side=tk.RIGHT, padx=5, pady=5)

    def create_text_areas(self):
        """创建文本区域"""
        # 创建章节列表和文本区域的容器 (使用PanedWindow)
        text_frame = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧: 章节列表
        left_frame = ttk.Frame(text_frame)
        
        # 章节列表标题
        ttk.Label(left_frame, text="章节列表", font=("Microsoft YaHei UI", 10, "bold")).pack(fill=tk.X, pady=(0, 5))
        
        # 章节列表
        columns = ("标题", "长度", "状态")
        self.chapter_list = ttk.Treeview(left_frame, columns=columns, show="headings", height=20)
        for col in columns:
            self.chapter_list.heading(col, text=col)
            self.chapter_list.column(col, width=80)
        
        # 设置列宽度
        self.chapter_list.column("标题", width=150)
        self.chapter_list.column("长度", width=70)
        self.chapter_list.column("状态", width=70)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.chapter_list.yview)
        self.chapter_list.configure(yscrollcommand=scrollbar.set)
        
        # 章节列表绑定事件
        self.chapter_list.bind("<<TreeviewSelect>>", self.on_chapter_select)
        
        # 包装章节列表和滚动条
        self.chapter_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 添加到PanedWindow
        text_frame.add(left_frame, weight=1)
        
        # 右侧: 内容和摘要 (上下排列)
        right_paned = ttk.PanedWindow(text_frame, orient=tk.VERTICAL)
        text_frame.add(right_paned, weight=3)
        
        # 上部: 原文
        mid_frame = ttk.Frame(right_paned)
        
        ttk.Label(mid_frame, text="原文", font=("Microsoft YaHei UI", 10, "bold")).pack(fill=tk.X, pady=(0, 5))
        
        self.content_text = scrolledtext.ScrolledText(
            mid_frame,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10)
        )
        self.content_text.pack(fill=tk.BOTH, expand=True)
        
        # 添加到垂直PanedWindow
        right_paned.add(mid_frame, weight=2)
        
        # 下部: 摘要
        bottom_frame = ttk.Frame(right_paned)
        
        ttk.Label(bottom_frame, text="摘要", font=("Microsoft YaHei UI", 10, "bold")).pack(fill=tk.X, pady=(0, 5))
        
        self.summary_text = scrolledtext.ScrolledText(
            bottom_frame,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10)
        )
        self.summary_text.pack(fill=tk.BOTH, expand=True)
        
        # 添加到垂直PanedWindow
        right_paned.add(bottom_frame, weight=1)
    
    def load_model(self):
        """初始化DeepSeek API"""
        # 获取选择的模型名称
        model_display = self.model_display_var.get()
        model_name = self.model_display_map.get(model_display, "deepseek-api")
        self.model_var.set(model_name)  # 更新实际模型名称
        
        # 更新状态
        self.update_status(f"正在初始化API: {model_display}")
        
        # 禁用按钮，防止重复点击
        self.model_selector.config(state="disabled")
        self.load_btn.config(state="disabled")
        self.generate_btn.config(state="disabled")
        self.generate_all_btn.config(state="disabled")
        
        # 在后台线程中初始化API
        def init_api_in_background():
            try:
                # 初始化摘要器
                self.summarizer = TitanSummarizer(
                    model_size=model_name,
                    progress_callback=self.update_progress_log
                )
                
                # 完成后在UI线程更新界面
                self.root.after(0, self.update_ui_after_model_loaded)
                
            except Exception as e:
                error_message = str(e)
                
                # 更新UI
                def show_error():
                    messagebox.showerror("API初始化失败", f"初始化API时出错: {error_message}")
                    self.update_status(f"API初始化失败: {error_message}")
                    self.model_selector.config(state="readonly")
                    self.load_btn.config(state="normal")
                
                self.root.after(0, show_error)
        
        # 启动初始化线程
        threading.Thread(target=init_api_in_background, daemon=True).start()
    
    def toggle_generation(self):
        """切换摘要生成状态"""
        # 检查API是否已初始化
        if not self.summarizer:
            messagebox.showinfo("提示", "请先点击初始化API按钮")
            return
        
        if self.is_generating:
            # 停止生成
            self.is_generating = False
            self.generate_btn.config(text="生成摘要")
            self.update_status("摘要生成已停止")
        else:
            # 开始生成
            self.generate_summary()
    
    def generate_summary(self):
        """生成摘要"""
        # 检查API是否已初始化
        if not self.summarizer:
            messagebox.showerror("错误", "请先初始化DeepSeek API")
            return
        
        # 获取当前章节内容
        current_item = self.chapter_list.selection()
        if not current_item:
            messagebox.showerror("错误", "请先选择一个章节")
            return
        
        # 获取当前章节内容和索引
        chapter_idx = self.chapter_list.index(current_item[0])
        chapter_content = self.novel_chapters[chapter_idx]['content']
        if not chapter_content.strip():
            messagebox.showerror("错误", "所选章节内容为空")
            return
        
        # 获取摘要长度
        try:
            max_length = int(self.length_var.get())
            if max_length <= 0:
                raise ValueError("摘要长度必须大于0")
        except ValueError as e:
            messagebox.showerror("错误", f"无效的摘要长度: {str(e)}")
            return
        
        # 获取摘要模式
        summary_mode = self.summary_mode.get()
        
        # 禁用生成按钮
        self.generate_btn.configure(state="disabled")
        self.update_status("正在生成摘要...")
        
        # 清空摘要区域
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, "正在生成摘要，请稍候...\n")
        
        # 在后台线程中生成摘要
        def generate_in_background():
            try:
                # 使用带摘要模式参数的方法生成摘要
                start_time = time.time()
                summary = self.summarizer.generate_summary(
                    chapter_content, 
                    max_length=max_length,
                    summary_mode=summary_mode
                )
                end_time = time.time()
                
                # 计算处理时间和摘要长度
                process_time = end_time - start_time
                summary_length = len(summary)
                
                # 更新UI线程中的结果
                def update_ui():
                    self.summary_text.delete(1.0, tk.END)
                    self.summary_text.insert(tk.END, summary)
                    
                    # 更新章节状态
                    self.chapter_list.item(
                        current_item, 
                        values=(
                            self.novel_chapters[chapter_idx]['title'],
                            f"{len(chapter_content)}字",
                            "已摘要"
                        )
                    )
                    
                    # 保存摘要到章节数据
                    self.novel_chapters[chapter_idx]['summary'] = summary
                    
                    # 显示完成信息
                    mode_text = "提取式" if summary_mode == "extractive" else "生成式"
                    self.update_status(
                        f"{mode_text}摘要已生成: {summary_length}字，耗时{process_time:.2f}秒"
                    )
                    
                    # 启用生成按钮
                    self.generate_btn.configure(state="normal")
                
                # 在UI线程中更新界面
                self.root.after(0, update_ui)
                
            except Exception as e:
                # 显示错误
                def show_error():
                    self.summary_text.delete(1.0, tk.END)
                    error_message = f"生成摘要失败: {str(e)}"
                    self.summary_text.insert(tk.END, error_message)
                    self.update_status(error_message)
                    self.generate_btn.configure(state="normal")
                
                self.root.after(0, show_error)
        
        # 启动后台线程
        threading.Thread(target=generate_in_background, daemon=True).start()
    
    def update_ui_after_model_loaded(self):
        """模型加载后更新UI状态"""
        if self.summarizer:
            self.generate_btn.config(state=tk.NORMAL)
            self.generate_all_btn.config(state=tk.NORMAL)
            
            # 获取模型名称和友好显示名称
            model_name = self.model_var.get()
            display_name = get_model_display_name(model_name)
            
            # 更新状态栏
            self.update_status(f"已初始化API: {display_name}")
            logger.info(f"已初始化API: {model_name}")
        else:
            self.generate_btn.config(state=tk.DISABLED)
            self.generate_all_btn.config(state=tk.DISABLED)
            
            # 更新状态栏
            self.update_status("API初始化失败")
            logger.error("API初始化失败")
    
    def batch_summary(self):
        """批量生成多个章节的摘要"""
        # 获取选中的章节
        selected = self.chapter_list.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择要生成摘要的章节")
            return
            
        if not self.summarizer:
            messagebox.showinfo("提示", "请先初始化DeepSeek API")
            return
        
        # 获取并验证摘要参数
        try:
            max_length = int(self.length_var.get())
            if max_length <= 0:
                messagebox.showerror("错误", "摘要长度必须是正整数")
                return
        except ValueError:
            messagebox.showerror("错误", "摘要长度必须是数字")
            return
        
        # 清空当前摘要
        self.clear_summary()
        
        # 显示进度条
        progress_dialog = tk.Toplevel(self.root)
        progress_dialog.title("批量生成摘要")
        progress_dialog.geometry("300x120")
        progress_dialog.transient(self.root)
        progress_dialog.grab_set()
        
        ttk.Label(progress_dialog, text="正在生成摘要...").pack(pady=(10, 5))
        
        progress_var = tk.DoubleVar()
        progress = ttk.Progressbar(
            progress_dialog,
            variable=progress_var,
            maximum=len(selected),
            mode="determinate"
        )
        progress.pack(fill=tk.X, padx=20, pady=5)
        
        status_var = tk.StringVar(value="准备中...")
        status_label = ttk.Label(progress_dialog, textvariable=status_var)
        status_label.pack(pady=5)
        
        # 创建摘要生成函数
        def generate_batch_summaries():
            try:
                # 处理队列
                for i, item in enumerate(selected):
                    idx = self.chapter_list.index(item)
                    chapter = self.novel_chapters[idx]
                    
                    # 更新进度条
                    progress_var.set(i)
                    status_var.set(f"处理: {chapter['title']}")
                    progress_dialog.update()
                    
                    # 生成摘要
                    content = chapter['content']
                    try:
                        summary = self.summarizer.generate_summary(content, max_length=max_length)
                        
                        # 保存摘要
                        self.novel_chapters[idx]['summary'] = summary
                        
                        # 更新摘要文本框
                        self.summary_text.insert(tk.END, f"\n{chapter['title']}\n")
                        self.summary_text.insert(tk.END, "-" * 50 + "\n")
                        self.summary_text.insert(tk.END, summary + "\n")
                        
                        # 更新章节列表状态
                        self.chapter_list.item(item, values=(
                            chapter['title'].split('\n')[0],
                            f"{len(content)}字",
                            "已生成"
                        ))
                        
                    except Exception as e:
                        error_message = str(e)
                        logger.error(f"生成章节 '{chapter['title']}' 摘要时出错: {error_message}")
                        # 继续处理下一个章节，而不是中断
                        continue
                        
                # 关闭进度条
                progress_dialog.destroy()
                
                # 更新状态
                self.update_status("批量摘要生成完成")
            except Exception as e:
                error_message = str(e)
                progress_dialog.destroy()
                self.root.after(0, lambda: messagebox.showerror("错误", f"批量生成摘要时出错: {error_message}"))
                self.update_status("批量摘要生成失败")
        
        # 启动生成线程
        threading.Thread(target=generate_batch_summaries, daemon=True).start()
    
    def load_default_novel(self):
        """加载默认小说"""
        default_novel = self.settings.get("default_novel")
        if default_novel and os.path.exists(default_novel):
            logger.info(f"尝试加载默认小说: {default_novel}")
            self.load_novel(default_novel)
        else:
            logger.warning(f"默认小说不存在: {default_novel}")
            # 尝试加载novels目录下的任何小说
            novels_dir = "novels"
            if os.path.exists(novels_dir):
                novel_files = [f for f in os.listdir(novels_dir) if f.endswith(".txt")]
                if novel_files:
                    novel_path = os.path.join(novels_dir, novel_files[0])
                    logger.info(f"尝试加载找到的小说: {novel_path}")
                    self.load_novel(novel_path)
    
    def select_novel(self):
        """选择小说文件对话框"""
        file_path = filedialog.askopenfilename(
            title="选择小说文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            self.load_novel(file_path)
    
    def load_novel(self, file_path):
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
                    logger.info(f"成功使用编码 {encoding} 读取文件")
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    logger.error(f"读取文件时发生错误: {str(e)}")
                    continue
            
            if not content:
                logger.error("所有编码均无法读取文件内容")
                messagebox.showerror("错误", "无法读取文件，请检查文件编码")
                return
                
            # 检查文件内容
            if not content.strip():
                messagebox.showerror("错误", "文件内容为空")
                return
                
            # 清空章节列表
            for item in self.chapter_list.get_children():
                self.chapter_list.delete(item)
                
            # 分割章节
            self.novel_chapters = []
            pattern = r"第[零一二三四五六七八九十百千万]+章\s*[^\n]+"
            matches = list(re.finditer(pattern, content))
            
            if not matches:
                messagebox.showinfo("提示", "未找到章节标记，将整个文件作为一章处理")
                self.novel_chapters.append({
                    'title': os.path.basename(file_path),
                    'content': content,
                    'summary': None
                })
            else:
                # 处理第一章之前的内容
                if matches[0].start() > 0:
                    self.novel_chapters.append({
                        'title': "前言",
                        'content': content[:matches[0].start()].strip(),
                        'summary': None
                    })
                
                # 处理各章节
                for i in range(len(matches)):
                    start_match = matches[i]
                    chapter_title = start_match.group(0)
                    start = start_match.start()
                    
                    if i < len(matches) - 1:
                        end = matches[i + 1].start()
                    else:
                        end = len(content)
                        
                    chapter_content = content[start:end].strip()
                    
                    self.novel_chapters.append({
                        'title': chapter_title,
                        'content': chapter_content,
                        'summary': None
                    })
            
            # 更新章节列表
            for i, chapter in enumerate(self.novel_chapters):
                title = chapter['title'].split('\n')[0]  # 只显示第一行作为标题
                length = len(chapter['content'])
                status = "已生成" if chapter.get("summary") else "未生成"
                self.chapter_list.insert("", "end", values=(title, f"{length}字", status))
                
            self.update_status(f"成功加载小说，共{len(self.novel_chapters)}章")
            logger.info(f"成功加载小说，共{len(self.novel_chapters)}章")
            
            # 保存当前小说路径
            self.settings["default_novel"] = file_path
            
            # 清空文本区域
            self.content_text.delete("1.0", tk.END)
            self.summary_text.delete("1.0", tk.END)
            
        except Exception as e:
            messagebox.showerror("错误", f"加载小说失败: {str(e)}")
            logger.error(f"加载小说失败: {str(e)}", exc_info=True)
    
    def on_chapter_select(self, event):
        """章节选择事件处理"""
        selected = self.chapter_list.selection()
        if not selected:
            return
            
        # 获取选中章节的索引
        i = self.chapter_list.index(selected[0])
        chapter = self.novel_chapters[i]
        
        # 显示原文
        self.content_text.delete('1.0', tk.END)
        self.content_text.insert('1.0', chapter['content'])
        
        # 如果有摘要，显示摘要
        self.summary_text.delete('1.0', tk.END)
        if chapter.get('summary'):
            self.summary_text.insert('1.0', chapter['summary'])
        
    def clear_summary(self):
        """清空摘要"""
        self.summary_text.delete('1.0', tk.END)
        self.update_status("已清空摘要")
        
    def process_queue(self):
        """处理队列中的任务"""
        while True:
            try:
                task = self.processing_queue.get(timeout=0.1)
                if task:
                    task()
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"处理队列任务时出错: {str(e)}")
            finally:
                time.sleep(0.1)  # 避免CPU占用过高
                
    def update_status(self, message):
        """更新状态栏消息"""
        self.status_var.set(message)
        self.root.update_idletasks()
        logger.info(message)
        
    def update_progress_log(self, message, progress=None, file_progress=None):
        """更新进度日志，用于API回调"""
        # 记录到日志
        logger.info(f"API进度: {message}")
        
        # 更新状态栏
        status_msg = f"API: {message}"
        
        # 处理进度参数
        if progress is not None:
            # 确保 progress 是浮点数
            try:
                if isinstance(progress, str):
                    # 如果是字符串，尝试转换为浮点数
                    progress_float = 0.0  # 默认值
                else:
                    # 否则尝试直接转换
                    progress_float = float(progress)
                
                # 转换为百分比
                progress_percent = int(progress_float * 100)
                status_msg += f" ({progress_percent}%)"
            except (ValueError, TypeError):
                # 如果转换失败，不添加百分比信息
                pass
        
        self.update_status(status_msg)
    
    def show_about(self):
        """显示关于对话框"""
        messagebox.showinfo(
            "关于 TitanSummarizer",
            "TitanSummarizer 大文本摘要系统\n"
            "版本: 1.0.0\n\n"
            "基于DeepSeek API的中文小说章节摘要工具\n"
            "支持批量摘要生成和多种格式小说"
        )
        
    def run(self):
        """运行UI"""
        self.root.mainloop()

    def validate_length(self, event):
        """验证摘要长度"""
        try:
            max_length = int(self.length_var.get())
            if max_length <= 0:
                messagebox.showerror("错误", "摘要长度必须是正整数")
                self.length_var.set(str(self.settings.get("default_length", 100)))
        except ValueError:
            messagebox.showerror("错误", "摘要长度必须是数字")
            self.length_var.set(str(self.settings.get("default_length", 100)))

    def summarize_all_chapters(self):
        """生成所有章节的摘要"""
        if not self.summarizer:
            messagebox.showinfo("提示", "请先初始化DeepSeek API")
            return
            
        if not self.novel_chapters:
            messagebox.showinfo("提示", "请先加载小说")
            return
            
        # 获取并验证摘要参数
        try:
            max_length = int(self.length_var.get())
            if max_length <= 0:
                messagebox.showerror("错误", "摘要长度必须是正整数")
                return
        except ValueError:
            messagebox.showerror("错误", "摘要长度必须是数字")
            return
            
        # 确认是否继续
        total_chapters = len(self.novel_chapters)
        if total_chapters > 20:
            if not messagebox.askyesno("确认", f"小说共有{total_chapters}章，生成所有摘要可能需要较长时间。是否继续？"):
                return
        
        # 清空当前摘要
        self.clear_summary()
        
        # 显示进度对话框
        progress_dialog = tk.Toplevel(self.root)
        progress_dialog.title("生成全部章节摘要")
        progress_dialog.geometry("400x150")
        progress_dialog.transient(self.root)
        progress_dialog.grab_set()
        
        ttk.Label(progress_dialog, text="正在生成摘要...", font=("Microsoft YaHei UI", 10, "bold")).pack(pady=(10, 5))
        
        progress_var = tk.DoubleVar()
        progress = ttk.Progressbar(
            progress_dialog,
            variable=progress_var,
            maximum=total_chapters,
            mode="determinate"
        )
        progress.pack(fill=tk.X, padx=20, pady=5)
        
        status_var = tk.StringVar(value="准备中...")
        status_label = ttk.Label(progress_dialog, textvariable=status_var, font=("Microsoft YaHei UI", 9))
        status_label.pack(pady=5)
        
        time_var = tk.StringVar(value="预计剩余时间: 计算中...")
        time_label = ttk.Label(progress_dialog, textvariable=time_var, font=("Microsoft YaHei UI", 9))
        time_label.pack(pady=5)
        
        # 进度更新函数
        def update_progress(current, total, chapter_title, elapsed_time):
            progress_var.set(current)
            status_var.set(f"处理: {chapter_title}")
            
            # 计算剩余时间
            if current > 0:
                avg_time = elapsed_time / current
                remaining_time = avg_time * (total - current)
                time_var.set(f"预计剩余时间: {int(remaining_time//60)}分{int(remaining_time%60)}秒")
            
            progress_dialog.update()
        
        # 在后台线程中处理
        def generate_all_summaries():
            try:
                progress_var.set(0)
                
                summary_results = []
                error_chapters = []
                
                # 获取摘要模式
                # 默认使用生成式摘要模式
                summary_mode = "generative"
                # 如果存在模式选择变量，则使用它
                if hasattr(self, 'mode_var') and self.mode_var.get():
                    summary_mode = self.mode_var.get()
                
                for i, chapter in enumerate(self.novel_chapters):
                    # 更新进度
                    progress_var.set(i / len(self.novel_chapters) * 100)
                    status_var.set(f"生成章节 {i+1}/{len(self.novel_chapters)}: {chapter['title']}")
                    progress_dialog.update()
                    
                    try:
                        # 生成摘要
                        summary = self.summarizer.generate_summary(
                            chapter['content'], 
                            max_length=max_length,
                            summary_mode=summary_mode
                        )
                        
                        # 记录结果
                        self.novel_chapters[i]['summary'] = summary
                        summary_results.append((chapter['title'], summary))
                        
                        # 更新列表状态
                        item_id = self.chapter_list.get_children()[i]
                        self.chapter_list.item(item_id, values=(
                            chapter['title'].split('\n')[0],
                            f"{len(chapter['content'])}字",
                            "已生成"
                        ))
                    except Exception as e:
                        # 记录错误但继续处理
                        error_message = str(e)
                        logger.error(f"生成章节 '{chapter['title']}' 摘要时出错: {error_message}")
                        error_chapters.append(chapter['title'])
                        continue
                
                # 完成生成
                progress_var.set(100)
                progress_dialog.destroy()
                
                # 在UI线程中显示结果
                def show_completion():
                    # 显示摘要结果
                    self.summary_text.delete('1.0', tk.END)
                    
                    if error_chapters:
                        self.summary_text.insert(tk.END, "以下章节生成失败:\n")
                        for title in error_chapters:
                            self.summary_text.insert(tk.END, f"- {title}\n")
                        self.summary_text.insert(tk.END, "\n" + "-"*50 + "\n\n")
                    
                    for title, summary in summary_results:
                        self.summary_text.insert(tk.END, f"{title}\n")
                        self.summary_text.insert(tk.END, "-"*50 + "\n")
                        self.summary_text.insert(tk.END, f"{summary}\n\n")
                        
                    mode_text = "提取式" if summary_mode == "extractive" else "生成式"
                    self.update_status(f"全部章节摘要生成完成，使用{mode_text}模式，{len(error_chapters)}个失败")
                    
                    # 如果只有一章，直接显示结果
                    if len(self.novel_chapters) == 1 and self.novel_chapters[0].get('summary'):
                        self.summary_text.delete('1.0', tk.END)
                        self.summary_text.insert(tk.END, self.novel_chapters[0]['summary'] + "\n")
                
                self.root.after(0, show_completion)
                
            except Exception as e:
                error_message = str(e)
                
                def show_error():
                    progress_dialog.destroy()
                    messagebox.showerror("错误", f"生成全部章节摘要时出错: {error_message}")
                    self.update_status("生成全部章节摘要失败")
                
                self.root.after(0, show_error)
        
        # 启动生成线程
        threading.Thread(target=generate_all_summaries, daemon=True).start()

    def save_settings(self):
        """保存当前设置"""
        try:
            # 更新设置
            if self.model_var.get():
                self.settings["default_model"] = self.model_var.get()
                
            if self.length_var.get():
                try:
                    self.settings["default_length"] = int(self.length_var.get())
                except ValueError:
                    pass
            
            # 写入文件
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
                
            logger.info("设置已保存")
        except Exception as e:
            logger.error(f"保存设置失败: {str(e)}")

    def on_closing(self):
        """窗口关闭时的处理"""
        try:
            # 保存设置
            self.save_settings()
            
            # 关闭窗口
            self.root.destroy()
        except Exception as e:
            logger.error(f"关闭窗口时出错: {str(e)}")
            self.root.destroy()

    def on_model_select(self, event):
        """模型选择事件处理"""
        try:
            # 获取选定的显示名称
            if hasattr(self, 'model_display_var'):
                selected_display = self.model_display_var.get()
            else:
                # 如果没有display变量，直接使用model_var
                self.model_display_var = tk.StringVar(value=get_model_display_name("deepseek-api"))
                selected_display = self.model_display_var.get()
            
            # 获取对应的实际模型名称
            model_name = self.model_display_map[selected_display]
            # 更新模型变量
            self.model_var.set(model_name)
            
            # 如果新选择的模型与当前加载的不同，则加载新模型
            if self.summarizer is None or self.summarizer.model_name != model_name:
                # 自动加载选定的模型
                self.load_model()
        except Exception as e:
            logger.error(f"模型选择时发生错误: {str(e)}")
            messagebox.showerror("错误", f"模型选择时发生错误: {str(e)}")

    def get_test_text(self, model_name):
        """获取模型的测试文本"""
        # 通用测试文本
        common_tests = [
            ("新闻文本", """人民网北京12月8日电（记者姜洁）12月8日，中央经济工作会议在北京举行。会议认为，今年是新中国成立70周年，是决胜全面建成小康社会第一个百年奋斗目标的关键之年。以习近平同志为核心的党中央团结带领全国各族人民，十分重视经济工作，高瞻远瞩、统揽全局、科学决策、果断施策，坚持稳中求进工作总基调，坚持以供给侧结构性改革为主线，推动高质量发展，扎实做好"六稳"工作。"""),
            
            ("小说文本", """周芷若冷笑道："是么？我倒要试他一试。"转过身去，低声道："赵姑娘，我们上去涤器室取些酒菜，待会儿下来奉陪众位师哥。"赵灵珠见她和祖千秋冷言相向，本已有些担忧，听她说不为难张无忌，这才放下了心，答道："好！"两个姑娘一起走开。张无忌道："师叔，适才多谢您相援。"殷梨亭道："大侄子，你吃了九阳神功的亏了。"张无忌微微一怔，道："干吗？"殷梨亭道："忘了你体内的九阳神功护体，竟会中她降龙十八掌的'潜龙勿用'之力。"张无忌一惊，忙道："啊，那怎么办？"殷梨亭道："事已如此，只好恕她这一掌之罪了。"张无忌心下难安，寻思："难道真的是我恃武凌人？将九阳神功的力道发了出来？"顺着这个思路想去，越想越觉有理。"""),
        ]
        
        return common_tests

    def run_model_test(self):
        """运行选定模型的测试"""
        if not self.summarizer:
            messagebox.showinfo("提示", "请先初始化DeepSeek API")
            return
            
        # 获取当前模型
        model_name = self.model_var.get()
        display_name = get_model_display_name(model_name)
        
        # 获取测试文本
        test_texts = self.get_test_text(model_name)
        if not test_texts:
            messagebox.showinfo("提示", f"没有找到{display_name}的测试文本")
            return
            
        # 验证摘要参数
        try:
            max_length = int(self.length_var.get())
            if max_length <= 0:
                messagebox.showerror("错误", "摘要长度必须是正整数")
                return
        except ValueError:
            messagebox.showerror("错误", "摘要长度必须是数字")
            return
            
        # 清空现有文本
        self.content_text.delete("1.0", tk.END)
        self.summary_text.delete("1.0", tk.END)
        
        # 创建测试窗口
        test_window = tk.Toplevel(self.root)
        test_window.title(f"{display_name} - API测试")
        test_window.geometry("600x400")
        test_window.transient(self.root)
        
        # 添加测试说明
        ttk.Label(
            test_window, 
            text=f"{display_name} API测试", 
            font=("Microsoft YaHei UI", 14, "bold")
        ).pack(pady=(10, 5))
        
        ttk.Label(
            test_window, 
            text="正在对多种文本类型进行摘要生成测试", 
            font=("Microsoft YaHei UI", 10)
        ).pack(pady=(0, 20))
        
        # 创建进度条
        progress_var = tk.DoubleVar()
        progress = ttk.Progressbar(
            test_window,
            variable=progress_var,
            maximum=len(test_texts),
            mode="determinate"
        )
        progress.pack(fill=tk.X, padx=20, pady=10)
        
        # 创建结果文本框
        result_text = scrolledtext.ScrolledText(
            test_window,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10)
        )
        result_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 运行测试
        def run_tests():
            for i, (title, text) in enumerate(test_texts):
                # 更新进度
                progress_var.set(i)
                test_window.update()
                
                # 生成摘要
                try:
                    result_text.insert(tk.END, f"\n【{title}】\n{'-'*50}\n")
                    result_text.insert(tk.END, f"原文 ({len(text)} 字):\n{text[:200]}...\n\n")
                    
                    # 生成摘要
                    summary = self.summarizer.generate_summary(text, max_length=max_length)
                    
                    # 显示结果
                    result_text.insert(tk.END, f"摘要 ({len(summary)} 字):\n{summary}\n\n")
                    result_text.see(tk.END)
                except Exception as e:
                    result_text.insert(tk.END, f"生成摘要失败: {str(e)}\n\n")
                
                # 如果是最后一个文本，同时显示在主界面上
                if i == len(test_texts) - 1:
                    self.content_text.insert(tk.END, f"【{title}】\n\n{text}")
                    self.summary_text.insert(tk.END, summary)
            
            # 更新最终进度
            progress_var.set(len(test_texts))
            
            # 添加完成按钮
            ttk.Button(
                test_window,
                text="完成",
                command=test_window.destroy
            ).pack(pady=10)
        
        # 在新线程中运行测试
        threading.Thread(target=run_tests, daemon=True).start()

def save_settings_file():
    """创建默认设置文件"""
    settings = {
        "default_model": "deepseek-api",
        "default_length": 100,
        "default_novel": "novels/凡人修仙传_完整版.txt",
        "theme": "clam"
    }
    
    try:
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        logger.info("创建默认设置文件成功")
    except Exception as e:
        logger.error(f"创建设置文件失败: {str(e)}")


def main():
    """主函数"""
    try:
        # 确保novels目录存在
        if not os.path.exists("novels"):
            os.makedirs("novels")
            logger.info("创建novels目录")
            
        # 确保设置文件存在
        if not os.path.exists("settings.json"):
            save_settings_file()
        
        # 创建并运行应用
        root = tk.Tk()
        app = TitanUI(root)
        app.run()
        
    except Exception as e:
        logger.error(f"程序启动失败: {str(e)}", exc_info=True)
        messagebox.showerror("错误", f"程序启动失败: {str(e)}")


if __name__ == "__main__":
    main() 