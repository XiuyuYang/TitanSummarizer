#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TitanSummarizer - 大文本摘要系统UI
简化版UI，专注于中文小说摘要生成
支持DeepSeek API云端摘要和Ollama本地模型摘要
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
import shutil

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
        self.root.title("Titan小说摘要生成器")
        self.root.geometry("1000x700")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 初始化变量和设置
        self.model = None
        self.summarizer = None
        self.model_name = None
        self.generating = False
        self.current_novel_path = None
        self.current_chapter_index = None
        self.novel_path_var = tk.StringVar()  # 添加小说路径变量
        self.novels_dir = "novels"  # 默认小说目录
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 加载设置
        self.settings = self.load_settings()
        
        # 应用设置中的默认小说
        if self.settings.get("default_novel"):
            logger.info(f"设置默认小说: {self.settings['default_novel']}")
        
        # 创建UI组件
        self.create_menu()
        self.create_control_bar()
        self.create_text_areas()
        self.create_status_bar()
        
        # 重定向标准输出到日志区域
        sys.stdout = TextRedirector(self.log_text)
        sys.stderr = TextRedirector(self.log_text)
        
        # 扫描小说目录
        logger.info("开始扫描小说目录...")
        self.scan_novels()
        
        # 初始消息
        self.update_status("就绪")
        logger.info("Titan小说摘要生成器启动完成")
        
        # 自动加载默认模型
        self.current_local_model_path = self.settings.get("default_local_model")
        logger.info(f"准备加载默认模型: {self.current_local_model_path}")
        
        # 使用设置中的默认模型，强制使用本地模型
        default_model = "ollama-local"  # 强制使用本地模型
        
        logger.info(f"从设置中加载默认模型: {default_model}")
        self.root.after(1000, lambda: self.load_model(default_model))

    def load_settings(self):
        """加载设置"""
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
                logger.info(f"成功加载设置: {settings}")
                
                # 确保设置中有默认模型，并处理大小写和名称规范问题
                model_name = settings.get("default_model", "").lower()
                if "deepseek" in model_name:
                    settings["default_model"] = "deepseek-api"
                    logger.info("设置使用DeepSeek API模型")
                elif "ollama" in model_name or model_name == "ollama-local":
                    settings["default_model"] = "ollama-local"
                    logger.info("设置使用本地Ollama模型")
                else:
                    # 默认使用本地模型
                    settings["default_model"] = "ollama-local"
                    logger.info("未识别的模型类型，默认使用本地模型")
                    
                # 添加默认模型路径
                if "default_local_model" not in settings:
                    settings["default_local_model"] = "D:\\Work\\AI_Models\\Qwen\\Qwen2-0.5B-Instruct-GGUF\\qwen2-0_5b-instruct-q4_k_m.gguf"
                    logger.info("设置默认本地模型为qwen2-0_5b-instruct-q4_k_m.gguf")
                    
                # 移除device设置
                if "default_device" in settings:
                    del settings["default_device"]
                    
                return settings
        except Exception as e:
            logger.warning(f"加载设置失败，使用默认值: {str(e)}")
            return {
                "default_model": "ollama-local",
                "default_local_model": "D:\\Work\\AI_Models\\Qwen\\Qwen2-0.5B-Instruct-GGUF\\qwen2-0_5b-instruct-q4_k_m.gguf",
                "default_length": 100,
                "default_novel": "凡人修仙传",
                "theme": "clam"
            }
            
    def create_menu(self):
        """创建菜单栏"""
        menu_bar = tk.Menu(self.root)
        
        # 文件菜单
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="打开文件", command=self.open_file)
        file_menu.add_command(label="浏览小说", command=self.browse_novels)
        file_menu.add_separator()
        file_menu.add_command(label="测试示例", command=self.run_test_example)
        file_menu.add_separator()
        file_menu.add_command(label="保存摘要", command=self.save_summary)
        file_menu.add_command(label="导出全部摘要", command=self.export_all_summaries)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menu_bar.add_cascade(label="文件", menu=file_menu)
        
        # 模型菜单
        model_menu = tk.Menu(menu_bar, tearoff=0)
        model_menu.add_command(label="DeepSeek API", command=lambda: self.load_model("DeepSeek API"))
        model_menu.add_command(label="Ollama 本地模型", command=lambda: self.load_model("Ollama 本地模型"))
        model_menu.add_command(label="OpenAI API", command=lambda: self.load_model("OpenAI API"))
        model_menu.add_separator()
        model_menu.add_command(label="浏览本地模型", command=self.browse_model)
        model_menu.add_command(label="重载当前模型", command=self.reload_model)
        menu_bar.add_cascade(label="模型", menu=model_menu)
        
        # 帮助菜单
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="使用指南", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
        menu_bar.add_cascade(label="帮助", menu=help_menu)
        
        self.root.config(menu=menu_bar)
        
    def create_control_bar(self):
        """创建控制栏"""
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 添加小说控制
        novel_frame = ttk.LabelFrame(control_frame, text="小说选择")
        novel_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 小说下拉框
        ttk.Label(novel_frame, text="选择小说:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.novel_var = tk.StringVar()
        self.novel_combobox = ttk.Combobox(novel_frame, textvariable=self.novel_var, state="readonly", width=20)
        self.novel_combobox.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.novel_combobox.bind("<<ComboboxSelected>>", self.on_novel_select)
        
        # 添加刷新按钮
        refresh_btn = ttk.Button(novel_frame, text="打开小说目录", command=self.open_novels_dir)
        refresh_btn.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        
        # 章节变量（用于兼容性）
        self.chapter_var = tk.StringVar()
        
        # 模型设置和生成控制
        gen_frame = ttk.LabelFrame(control_frame, text="模型设置")
        gen_frame.pack(side=tk.LEFT, padx=5, fill=tk.X)
        
        # 模型选择下拉框
        ttk.Label(gen_frame, text="模型:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.model_var = tk.StringVar(value="Ollama 本地模型")
        self.model_combobox = ttk.Combobox(gen_frame, textvariable=self.model_var, state="readonly", width=20)
        self.model_combobox["values"] = ["DeepSeek API", "Ollama 本地模型"]
        self.model_combobox.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 加载模型按钮
        self.load_model_btn = ttk.Button(gen_frame, text="加载模型", command=lambda: self.load_model(None))
        self.load_model_btn.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        
        # 摘要控制区域
        summary_frame = ttk.LabelFrame(control_frame, text="摘要控制")
        summary_frame.pack(side=tk.LEFT, padx=5, fill=tk.X)
        
        # 摘要模式选择
        ttk.Label(summary_frame, text="模式:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.summary_mode_var = tk.StringVar(value="生成式")
        mode_combobox = ttk.Combobox(summary_frame, textvariable=self.summary_mode_var, state="readonly", width=10)
        mode_combobox["values"] = ["生成式", "提取式"]
        mode_combobox.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 摘要长度选择
        ttk.Label(summary_frame, text="长度:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.summary_length_var = tk.StringVar(value="中等")
        length_combobox = ttk.Combobox(summary_frame, textvariable=self.summary_length_var, state="readonly", width=10)
        length_combobox["values"] = ["简短", "中等", "详细"]
        length_combobox.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # 生成摘要按钮
        self.generate_button = ttk.Button(summary_frame, text="生成摘要", command=self.toggle_generation)
        self.generate_button.grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        
        # 批量生成按钮
        self.stop_button = ttk.Button(summary_frame, text="停止", command=self.stop_generation, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)

    def create_text_areas(self):
        """创建文本区域"""
        # 创建主要框架
        main_frame = ttk.Frame(self.main_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建左侧章节列表框架
        chapters_frame = ttk.LabelFrame(main_frame, text="章节列表")
        chapters_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False, padx=5, pady=5, ipadx=5, ipady=5)
        
        # 创建章节列表
        columns = ("章节", "字数", "状态")
        self.chapter_list = ttk.Treeview(chapters_frame, columns=columns, show="headings", height=25)
        self.chapter_list.column("章节", width=150, anchor="w")
        self.chapter_list.column("字数", width=60, anchor="center")
        self.chapter_list.column("状态", width=60, anchor="center")
        self.chapter_list.heading("章节", text="章节")
        self.chapter_list.heading("字数", text="字数")
        self.chapter_list.heading("状态", text="状态")
        
        # 添加滚动条
        chapter_scrollbar = ttk.Scrollbar(chapters_frame, orient=tk.VERTICAL, command=self.chapter_list.yview)
        self.chapter_list.configure(yscrollcommand=chapter_scrollbar.set)
        
        self.chapter_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        chapter_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定选择事件
        self.chapter_list.bind("<<TreeviewSelect>>", self.on_chapter_list_select)
        
        # 创建文本内容框架
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建原文框架
        original_frame = ttk.LabelFrame(content_frame, text="原文")
        original_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 原文文本区域
        self.original_text = tk.Text(original_frame, wrap=tk.WORD, width=40, height=20)
        original_scrollbar = ttk.Scrollbar(original_frame, orient=tk.VERTICAL, command=self.original_text.yview)
        self.original_text.config(yscrollcommand=original_scrollbar.set)
        self.original_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        original_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建摘要框架
        summary_frame = ttk.LabelFrame(content_frame, text="摘要")
        summary_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 摘要文本区域
        self.summary_text = tk.Text(summary_frame, wrap=tk.WORD, width=40, height=20)
        summary_scrollbar = ttk.Scrollbar(summary_frame, orient=tk.VERTICAL, command=self.summary_text.yview)
        self.summary_text.config(yscrollcommand=summary_scrollbar.set)
        self.summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建日志框架
        log_frame = ttk.LabelFrame(self.main_frame, text="日志")
        log_frame.pack(fill=tk.X, expand=False, padx=10, pady=5)
        
        # 日志文本区域
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=6)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_status_bar(self):
        """创建状态栏"""
        self.status_var = tk.StringVar(value="就绪")
        self.status_bar = ttk.Label(
            self.root, 
            textvariable=self.status_var, 
            relief=tk.SUNKEN, 
            anchor=tk.W,
            padding=(5, 2)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 添加进度条
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(
            self.status_bar,
            orient=tk.HORIZONTAL,
            length=150,
            mode='determinate',
            variable=self.progress_var
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=5)
        
    def update_status(self, message):
        """更新状态栏信息"""
        self.status_var.set(message)
        logger.info(message)
        
    def update_progress(self, value, message=""):
        """更新进度条"""
        self.progress_var.set(value)
        if message:
            self.update_status(message)
            
    def update_progress_log(self, progress, total=100, message=""):
        """更新进度日志和进度条"""
        try:
            # 尝试转换参数为数值
            try:
                progress_value = float(progress)
                total_value = float(total) if total else 100.0
            except (ValueError, TypeError):
                logger.error(f"进度更新参数错误: progress={progress}, total={total}, message={message}")
                return
                
            # 计算百分比（确保total大于0）
            if total_value > 0:
                percent = min(100, (progress_value / total_value) * 100)
            else:
                percent = 0
                
            # 截断至2位小数
            percent = round(percent, 2)
            
            # 更新进度条
            self.progress_bar["value"] = percent
            
            # 更新状态文本
            status_text = f"{percent}% - {message}" if message else f"{percent}%"
            self.update_status(status_text)
            
            # 添加到日志
            timestamp = time.strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {status_text}"
            
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, log_entry + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
            
            # 更新UI
            self.root.update_idletasks()
            
        except Exception as e:
            logger.error(f"更新进度日志时出错: {str(e)}", exc_info=True)
        
    def show_about(self):
        """显示关于对话框"""
        about_text = """Titan小说摘要器 v1.0
        
一个用于生成小说章节摘要的工具，支持以下功能：
- 支持多种模型：DeepSeek API、Ollama本地模型、OpenAI API
- 支持生成式和提取式摘要
- 支持调整摘要长度
- 支持批量导出摘要
- 支持保存单个摘要

开发者：AI辅助开发
联系方式：example@example.com
        
感谢使用！
"""
        messagebox.showinfo("关于", about_text)
        
    def show_help(self):
        """显示帮助信息"""
        help_text = (
            "使用说明：\n\n"
            "1. 模型选择与加载：\n"
            "   - 从菜单栏的\"模型\"中选择DeepSeek API或本地模型\n"
            "   - 若选择本地模型，将显示可用的GGUF格式模型列表\n\n"
            "2. 加载小说：\n"
            "   - 点击\"文件\"->\"打开小说目录\"选择小说所在目录\n"
            "   - 选择小说后，在章节下拉框中选择要摘要的章节\n\n"
            "3. 生成摘要：\n"
            "   - 设置摘要模式（生成式/提取式）和长度\n"
            "   - 点击\"生成摘要\"按钮开始生成\n"
            "   - 点击\"批量生成\"可为所有章节生成摘要\n\n"
            "4. 保存结果：\n"
            "   - 点击\"文件\"->\"保存摘要\"可保存当前摘要\n"
            "   - 点击\"文件\"->\"导出全部摘要\"可导出所有章节摘要\n"
        )
        
        # 创建帮助窗口
        help_window = tk.Toplevel(self.root)
        help_window.title("使用说明")
        help_window.geometry("600x500")
        help_window.minsize(500, 400)
        help_window.transient(self.root)
        help_window.grab_set()
        
        # 创建文本区域
        help_text_widget = scrolledtext.ScrolledText(
            help_window,
            wrap=tk.WORD,
            width=70,
            height=25,
            font=("SimSun", 10)
        )
        help_text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        help_text_widget.insert(tk.END, help_text)
        help_text_widget.config(state=tk.DISABLED)
        
        # 关闭按钮
        close_btn = ttk.Button(help_window, text="关闭", command=help_window.destroy)
        close_btn.pack(pady=10)
        
    def run_test_example(self):
        """运行测试示例"""
        # 检查模型是否已加载
        if not hasattr(self, 'summarizer') or not self.summarizer:
            messagebox.showinfo("提示", "请先加载模型")
            return
            
        # 清空文本区域
        self.original_text.delete("1.0", tk.END)
        self.summary_text.delete("1.0", tk.END)
        
        # 添加示例文本
        example_text = (
            "在唐代宫廷中，一位叫杨贵妃的美人深受唐明皇喜爱。她身段丰腴，态度柔美，唐明皇对她宠爱有加，"
            "赐号贵妃，又封她的姐妹为婕妤贵人等。杨贵妃与唐明皇朝夕相处，春寒时节，于华清池沐浴温泉，夏天在避暑的离宫享受清凉，"
            "秋天饮酒赏菊，冬天携手赏雪。一年四季，帝王对爱妃的感情都如胶似漆。后来发生了安史之乱，唐明皇被迫逃往四川。"
            "在马嵬驿，随行的将士因粮草不足、军心涣散而发生了哗变，将士们认为祸乱起因是杨贵妃的亲戚杨国忠，"
            "要求杀掉杨国忠。哗变的将士杀了杨国忠，又逼迫唐明皇处死杨贵妃。在万般无奈之下，唐明皇命人赐死了杨贵妃。"
            "事后，唐明皇非常后悔，思念杨贵妃，于是派人去寻找仙人，想要找回杨贵妃的魂魄。"
            "后来，唐明皇梦游仙境，得以与杨贵妃重逢，两人难舍难分，杨贵妃送给唐明皇一根金钗和一个锦盒作为纪念，"
            "相约来世再续情缘。"
        )
        
        self.original_text.insert("1.0", example_text)
        
        # 生成摘要
        self.generate_summary()
        
    def on_closing(self):
        """处理窗口关闭事件"""
        if messagebox.askokcancel("退出", "确定要退出程序吗?"):
            # 保存设置
            self.save_settings()
            # 关闭窗口
            self.root.destroy()
            
    def open_novel_dir(self):
        """打开小说目录（为保持兼容性）"""
        self.browse_novel()

    def load_model(self, model_name=None):
        """加载模型"""
        self.update_status("正在加载模型...")
        logger.info(f"开始加载模型，参数: {model_name}")
        
        if hasattr(self, 'generate_button'):
            self.generate_button.config(state=tk.DISABLED)
        elif hasattr(self, 'generate_btn'):
            self.generate_btn.config(state=tk.DISABLED)
        
        if hasattr(self, 'stop_button'):
            self.stop_button.config(state=tk.DISABLED)
        elif hasattr(self, 'generate_all_btn'):
            self.generate_all_btn.config(state=tk.DISABLED)
        
        # 如果没有传入模型名称，则使用下拉框中的选择或设置中的默认模型
        if not model_name:
            model_display = self.model_var.get()
            logger.info(f"从UI获取模型: {model_display}")
            
            # 根据显示名称确定模型类型
            if "DeepSeek" in model_display or "deepseek" in model_display.lower():
                model_name = "deepseek-api"
                logger.info("选择了DeepSeek API模型")
            elif "Ollama" in model_display or "ollama" in model_display.lower():
                model_name = "ollama-local"
                logger.info("选择了Ollama本地模型")
                # 如果选择了Ollama但没有具体模型，需要选择模型
                if not hasattr(self, 'current_local_model_path'):
                    logger.info("没有本地模型路径，弹出选择对话框")
                    self.select_local_model()
                    return
        # 处理从设置中加载默认模型的情况
        elif model_name in ["DeepSeek API", "deepseek api"]:
            model_name = "deepseek-api"
            logger.info("从设置中加载DeepSeek API模型")
        elif model_name in ["ollama-local", "ollama local", "Ollama 本地模型"]:
            model_name = "ollama-local"
            logger.info("从设置中加载Ollama本地模型")
        
        logger.info(f"确认加载模型: {model_name}, 本地模型路径: {getattr(self, 'current_local_model_path', 'None')}")
        
        # 使用单独的线程初始化API，避免UI卡顿
        def init_api_in_background():
            try:
                # 记录开始时间
                start_time = time.time()
                logger.info(f"开始在后台线程中初始化API: {model_name}")
                
                # 创建Summarizer实例
                self.summarizer = TitanSummarizer(
                    model_size=model_name,
                    progress_callback=self.progress_callback_adapter
                )
                
                # 如果是Ollama本地模型，需要加载具体的模型文件
                if model_name == "ollama-local" and hasattr(self, 'current_local_model_path'):
                    # 加载选中的本地模型
                    logger.info(f"准备加载本地模型: {self.current_local_model_path}")
                    try:
                        success = self.summarizer.load_local_model(self.current_local_model_path)
                        logger.info(f"本地模型加载结果: {success}")
                    except Exception as e:
                        logger.error(f"加载本地模型时出错: {str(e)}", exc_info=True)
                        success = False
                    
                    if not success:
                        def show_error():
                            messagebox.showerror(
                                "模型加载失败",
                                f"无法加载本地模型: {os.path.basename(self.current_local_model_path)}\n请检查Ollama服务是否正常运行，或选择其他模型。"
                            )
                        self.root.after(0, show_error)
                        self.update_status("模型加载失败")
                        return
                
                # 记录完成时间和耗时
                end_time = time.time()
                elapsed = end_time - start_time
                logger.info(f"API初始化完成，耗时: {elapsed:.2f}秒")
                
                # 在UI线程中更新状态
                def update_ui():
                    if hasattr(self.summarizer, 'is_model_loaded') and self.summarizer.is_model_loaded():
                        self.update_status(f"模型加载成功 (用时 {elapsed:.2f} 秒)")
                        self.settings["default_model"] = model_name
                        self.save_settings()
                        logger.info("模型加载成功，更新UI状态")
                        
                        # 更新UI状态
                        self.update_ui_after_model_loaded()
                    else:
                        self.update_status("模型加载失败")
                        logger.error("模型加载失败，summarizer.is_model_loaded() 返回 False 或方法不存在")
                        messagebox.showerror("错误", "模型加载失败，请检查日志获取详细信息")
                
                self.root.after(0, update_ui)
                
            except Exception as e:
                logger.error(f"加载模型时出错: {str(e)}", exc_info=True)
                
                # 在UI线程中显示错误
                def show_error():
                    messagebox.showerror("错误", f"加载模型时出错: {str(e)}")
                    self.update_status("模型加载失败")
                
                self.root.after(0, show_error)
        
        # 启动后台线程加载模型
        threading.Thread(target=init_api_in_background, daemon=True).start()

    def select_local_model(self):
        """选择本地模型（为保持兼容性）"""
        self.browse_model()

    def toggle_generation(self):
        """切换生成状态"""
        if self.generating:
            self.stop_generation()
        else:
            if self.generate_summary():
                self.generate_button.config(text="停止生成")
                self.stop_button.config(state=tk.NORMAL)

    def generate_summary(self):
        """生成摘要"""
        try:
            # 检查模型是否已加载
            if not self.summarizer:
                messagebox.showerror("错误", "请先加载模型")
                return
                
            # 检查是否正在生成
            if self.generating:
                messagebox.showinfo("提示", "正在生成中，请稍候")
                return
                
            # 获取原文
            original_content = self.original_text.get("1.0", tk.END).strip()
            if not original_content:
                # 检查是否有选中的章节
                if hasattr(self, 'current_chapter_index') and self.current_chapter_index is not None:
                    try:
                        chapter = self.novel_chapters[self.current_chapter_index]
                        original_content = chapter['content']
                        logger.info(f"使用当前选中章节内容生成摘要: {chapter['title']}")
                    except (IndexError, AttributeError) as e:
                        logger.error(f"获取当前章节内容失败: {str(e)}")
                        
            if not original_content:
                messagebox.showerror("错误", "无内容可进行摘要")
                return
                
            # 获取摘要模式和长度
            summary_mode = self.summary_mode_var.get()
            summary_length = self.summary_length_var.get()
            
            # 禁用生成按钮
            self.generate_button.config(state=tk.DISABLED)
            self.generating = True
            
            # 清空摘要区域
            self.summary_text.delete("1.0", tk.END)
            
            # 更新日志和状态
            self.update_progress_log(0.1, 100, "开始生成摘要...")
            self.update_status("正在生成摘要...")
            
            # 在后台线程中生成摘要
            threading.Thread(
                target=self._generate_summary_thread, 
                args=(original_content, summary_mode, summary_length),
                daemon=True
            ).start()
            
            return True
                
        except Exception as e:
            self.generating = False
            self.generate_button.config(state=tk.NORMAL)
            logger.error(f"生成摘要出错: {str(e)}", exc_info=True)
            messagebox.showerror("错误", f"生成摘要出错: {str(e)}")
            return False

    def update_ui_after_model_loaded(self):
        """模型加载后更新UI状态"""
        try:
            # 确保summarizer已初始化
            if not self.summarizer:
                logger.error("模型加载失败，summarizer为None")
                return
                
            # 检查模型是否已加载
            is_loaded = hasattr(self.summarizer, 'is_model_loaded') and self.summarizer.is_model_loaded()
            
            if is_loaded:
                logger.info("模型加载成功，更新UI状态")
                
                # 更新模型状态标签
                if hasattr(self, 'model_status_label'):
                    self.model_status_label.config(text="已加载", foreground="green")
                    
                # 启用生成摘要按钮
                if hasattr(self, 'generate_button'):
                    self.generate_button.config(state=tk.NORMAL)
                    
                # 启用导出功能
                if hasattr(self, 'export_button'):
                    self.export_button.config(state=tk.NORMAL)
                
                # 移除自动生成第一章摘要的功能
                # self.root.after(1000, self.auto_generate_first_chapter_summary)
                    
            else:
                logger.error("模型加载失败，summarizer.is_model_loaded() 返回 False 或方法不存在")
                
                # 更新模型状态标签
                if hasattr(self, 'model_status_label'):
                    self.model_status_label.config(text="加载失败", foreground="red")
                    
        except Exception as e:
            logger.error(f"更新UI状态出错: {str(e)}")
            
    def auto_generate_first_chapter_summary(self):
        """自动生成第一章摘要"""
        try:
            logger.info("开始自动生成第一章摘要")
            
            # 确保小说已加载
            if not hasattr(self, 'novel_chapters') or not self.novel_chapters:
                logger.warning("找不到小说章节，无法自动生成摘要")
                return
                
            # 查找第一章（跳过前言）
            first_chapter_index = 0
            for i, chapter in enumerate(self.novel_chapters):
                chapter_title = chapter['title'].split('\n')[0]
                if "第一章" in chapter_title or "第1章" in chapter_title:
                    first_chapter_index = i
                    break
            
            # 如果找到了第一章，选中它并生成摘要
            if first_chapter_index >= 0 and first_chapter_index < len(self.novel_chapters):
                # 获取第一章的内容
                first_chapter = self.novel_chapters[first_chapter_index]
                chapter_title = first_chapter['title'].split('\n')[0]
                logger.info(f"找到第一章: {chapter_title}")
                
                # 在章节列表中找到并选中第一章
                if hasattr(self, 'chapter_list'):
                    items = self.chapter_list.get_children()
                    if items and first_chapter_index < len(items):
                        # 选中第一章
                        self.chapter_list.selection_set(items[first_chapter_index])
                        self.chapter_list.focus(items[first_chapter_index])
                        self.chapter_list.see(items[first_chapter_index])
                        # 触发章节选择事件
                        self.on_chapter_list_select(None)
                        
                        # 设置当前章节索引
                        self.current_chapter_index = first_chapter_index
                        
                        # 在内容显示区域显示第一章内容
                        self.original_text.delete("1.0", tk.END)
                        self.original_text.insert(tk.END, first_chapter['content'])
                        
                        # 设置生成状态
                        self.generating = True
                        if hasattr(self, 'generate_button'):
                            self.generate_button.config(text="停止生成", state=tk.NORMAL)
                        if hasattr(self, 'stop_button'):
                            self.stop_button.config(state=tk.NORMAL)
                        
                        # 生成摘要
                        self.update_status(f"正在自动生成 '{chapter_title}' 的摘要...")
                        
                        # 获取摘要模式和长度
                        summary_mode = self.summary_mode_var.get()
                        summary_length = self.summary_length_var.get()
                        
                        # 在后台线程中生成摘要
                        threading.Thread(
                            target=self._generate_summary_thread, 
                            args=(first_chapter['content'], summary_mode, summary_length),
                            daemon=True
                        ).start()
                        
                        logger.info(f"已启动第一章自动摘要生成线程，章节: {chapter_title}")
                    else:
                        logger.warning("章节列表为空或者索引无效，无法选择第一章")
                else:
                    logger.warning("找不到章节列表控件，无法选择第一章")
            else:
                logger.warning("未找到第一章，无法自动生成摘要")
                
        except Exception as e:
            logger.error(f"自动生成第一章摘要出错: {str(e)}", exc_info=True)

    def generate_summary_text(self, original_content, summary_mode, length):
        """生成摘要文本"""
        try:
            # 检查是否已加载模型
            if not self.summarizer:
                return "错误：请先加载模型"
                
            # 检查模型是否已加载
            is_loaded = hasattr(self.summarizer, 'is_model_loaded') and self.summarizer.is_model_loaded()
            if not is_loaded:
                return "错误：模型尚未加载完成"
                
            # 根据摘要模式和长度设置提示词
            length_tokens = {
                "简短": 100,
                "中等": 200,
                "详细": 400
            }
            
            if summary_mode == "生成式":
                prompt = f"请总结以下内容，生成一个{length}摘要：\n\n{original_content}"
            else:  # 提取式
                prompt = f"请从以下内容中提取重要的句子，生成一个{length}摘要：\n\n{original_content}"
            
            # 开始生成摘要的线程
            def generate():
                try:
                    # 调用API生成摘要
                    summary = self.summarizer.generate_summary(
                        prompt, 
                        max_length=length_tokens.get(length, 200)
                    )
                    
                    return summary
                except Exception as e:
                    logger.error(f"生成摘要出错: {str(e)}")
                    raise e
                    
            # 更新状态
            self.update_status("正在生成摘要...")
            self.update_progress_log(0.1, 100, "开始生成")
            
            # 生成摘要
            logger.info("开始生成")
            summary = generate()
            
            # 更新状态
            self.update_progress_log(1.0, 100, "摘要生成完成")
            
            return summary
            
        except Exception as e:
            logger.error(f"生成摘要出错: {str(e)}")
            self.update_progress_log(0, 100, f"摘要生成失败: {str(e)}")
            return f"生成摘要时出错: {str(e)}"

    def batch_summary(self):
        """批量生成多个章节的摘要"""
        # 获取选中的章节
        selected = self.chapter_list.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选择要生成摘要的章节")
            return
            
        if not self.summarizer:
            messagebox.showinfo("提示", "请先初始化模型")
            return
        
        # 获取并验证摘要参数
        try:
            max_length = int(self.summary_length_var.get())
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
        default_novel_path = self.settings.get("default_novel")
        default_novel_dir = self.settings.get("default_novel_dir", "novels")
        
        # 更新当前小说目录
        self.novels_dir = default_novel_dir
        
        # 如果设置中有默认小说路径并且存在该文件，则加载
        if default_novel_path and os.path.exists(os.path.join(default_novel_dir, default_novel_path)):
            logger.info(f"尝试加载默认小说: {os.path.join(default_novel_dir, default_novel_path)}")
            # 设置下拉框值
            self.novel_var.set(default_novel_path)
            # 触发选择事件
            self.on_novel_select(None)
            return
            
        # 尝试加载凡人修仙传_完整版.txt
        default_file = os.path.join("novels", "凡人修仙传_完整版.txt")
        if os.path.exists(default_file):
            logger.info(f"尝试加载凡人修仙传_完整版.txt")
            self.load_novel(default_file)
            return
            
        # 尝试加载novels目录下的任何TXT文件
        novels_dir = "novels"
        if os.path.exists(novels_dir):
            txt_files = [f for f in os.listdir(novels_dir) if f.endswith(".txt") and os.path.isfile(os.path.join(novels_dir, f))]
            if txt_files:
                # 更新下拉框值
                self.novel_combobox['values'] = txt_files
                # 设置选中的值
                self.novel_var.set(txt_files[0])
                # 触发选择事件
                self.on_novel_select(None)
                return
                
        logger.warning("未找到默认小说文件")
    
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
            pattern = r"第[零一二三四五六七八九十百千万0-9]+章\s*[^\n]+"
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
            
            # 设置当前小说路径和文件名
            self.current_novel_path = os.path.dirname(file_path)
            self.current_novel_file = os.path.basename(file_path)
            self.novel_path_var.set(file_path)
            
            # 保存当前小说路径
            self.settings["default_novel"] = file_path
            self.save_settings()
            
            # 清空文本区域
            self.original_text.delete("1.0", tk.END)
            self.summary_text.delete("1.0", tk.END)
            
            # 选中第一个章节
            if self.chapter_list.get_children():
                first_item = self.chapter_list.get_children()[0]
                self.chapter_list.selection_set(first_item)
                self.chapter_list.focus(first_item)
                self.on_chapter_list_select(None)  # 触发章节列表选择事件
            
        except Exception as e:
            messagebox.showerror("错误", f"加载小说失败: {str(e)}")
            logger.error(f"加载小说失败: {str(e)}", exc_info=True)
    
    def on_chapter_select(self, event):
        """当选择章节时触发"""
        try:
            selected_chapter = self.chapter_var.get()
            
            # 检查章节和小说路径是否有效
            if not selected_chapter or not self.current_novel_path:
                logger.warning(f"章节选择事件: 未选择章节或小说路径未初始化 (selected_chapter={selected_chapter}, current_novel_path={self.current_novel_path})")
                return
                
            logger.info(f"选择章节: {selected_chapter}")
            self.update_status(f"已选择: {selected_chapter}")
            
            # 构建完整章节路径
            chapter_path = os.path.join(self.current_novel_path, selected_chapter)
            logger.info(f"章节完整路径: {chapter_path}")
            
            # 尝试不同的编码方式读取文件
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'big5', 'latin1']
            content = None
            
            for encoding in encodings:
                try:
                    with open(chapter_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    logger.info(f"成功使用 {encoding} 编码读取章节内容")
                    break
                except UnicodeDecodeError:
                    logger.debug(f"{encoding} 编码读取失败，尝试下一种编码")
                except Exception as e:
                    logger.error(f"使用 {encoding} 编码读取章节时出错: {str(e)}")
                    raise
            
            if content is None:
                logger.error(f"所有编码尝试均失败，无法读取文件: {chapter_path}")
                messagebox.showerror("错误", f"无法读取章节文件，请检查文件编码")
                return
                
            # 显示章节内容
            self.original_text.delete('1.0', tk.END)
            self.original_text.insert(tk.END, content)
            
            # 保存选择的章节
            self.settings["selected_chapter"] = selected_chapter
            self.save_settings()
            
        except Exception as e:
            logger.error(f"章节选择出错: {str(e)}", exc_info=True)
            messagebox.showerror("错误", f"章节选择出错: {str(e)}")

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
                
    def save_settings(self):
        """保存当前设置"""
        try:
            # 更新设置
            if self.model_var.get():
                model_display = self.model_var.get()
                # 保存到设置时转换为标准名称
                if "DeepSeek" in model_display or "deepseek" in model_display.lower():
                    self.settings["default_model"] = "DeepSeek API"
                elif "Ollama" in model_display or "ollama" in model_display.lower():
                    self.settings["default_model"] = "ollama-local"
                else:
                    self.settings["default_model"] = model_display
                
            if self.summary_length_var.get():
                try:
                    self.settings["default_length"] = int(self.summary_length_var.get())
                except ValueError:
                    pass
            
            # 写入文件
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
                
            logger.info("设置已保存")
        except Exception as e:
            logger.error(f"保存设置失败: {str(e)}")

    def on_model_select(self, event):
        """模型选择事件处理"""
        try:
            # 获取选定的显示名称
            if hasattr(self, 'model_var'):
                selected_display = self.model_var.get()
            else:
                # 如果没有display变量，直接使用model_var
                self.model_var = tk.StringVar(value="DeepSeek API")
                selected_display = self.model_var.get()
            
            # 获取对应的实际模型名称
            model_name = self.model_var.get()
            # 更新模型变量
            self.model_var.set(model_name)
            
            # 如果新选择的模型与当前加载的不同，则加载新模型
            if self.summarizer is None or self.summarizer.model_name != model_name:
                # 自动加载选定的模型
                self.load_model(model_name)
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
            messagebox.showinfo("提示", "请先初始化模型")
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
            max_length = int(self.summary_length_var.get())
            if max_length <= 0:
                messagebox.showerror("错误", "摘要长度必须是正整数")
                return
        except ValueError:
            messagebox.showerror("错误", "摘要长度必须是数字")
            return
            
        # 清空现有文本
        self.original_text.delete("1.0", tk.END)
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
                    self.original_text.insert(tk.END, f"【{title}】\n\n{text}")
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

    def stop_generation(self):
        """停止生成"""
        try:
            if hasattr(self, 'generating') and self.generating:
                self.generating = False
                self.update_status("已停止生成")
                self.generate_button.config(text="生成摘要")
                self.stop_button.config(state=tk.DISABLED)
        except Exception as e:
            logger.error(f"停止生成出错: {str(e)}")
            
    def run(self):
        """运行UI"""
        self.root.mainloop()

    def validate_length(self, event):
        """验证摘要长度"""
        try:
            max_length = int(self.summary_length_var.get())
            if max_length <= 0:
                messagebox.showerror("错误", "摘要长度必须是正整数")
                self.summary_length_var.set(str(self.settings.get("default_length", 100)))
        except ValueError:
            messagebox.showerror("错误", "摘要长度必须是数字")
            self.summary_length_var.set(str(self.settings.get("default_length", 100)))

    def summarize_all_chapters(self):
        """生成所有章节的摘要"""
        if not self.summarizer:
            messagebox.showinfo("提示", "请先初始化模型")
            return
            
        if not self.novel_chapters:
            messagebox.showinfo("提示", "请先加载小说")
            return
            
        # 获取并验证摘要参数
        try:
            max_length = int(self.summary_length_var.get())
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
                if hasattr(self, 'summary_mode_var') and self.summary_mode_var.get():
                    summary_mode = self.summary_mode_var.get()
                
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

    def on_novel_select(self, event):
        """小说选择事件处理"""
        try:
            # 获取选中的小说
            selected_novel = self.novel_var.get()
            if not selected_novel:
                logger.warning("小说选择事件：未选择小说")
                return
                
            # 更新状态
            logger.info(f"选择小说: {selected_novel}")
            self.update_status(f"已选择小说: {selected_novel}")
            
            # 确定小说所在目录
            novels_dir = getattr(self, 'novels_dir', 'novels')
            
            # 构造完整路径
            novel_path = os.path.join(novels_dir, selected_novel)
            logger.info(f"小说完整路径: {novel_path}")
            
            # 如果是目录，加载章节，否则直接加载小说文件
            if os.path.isdir(novel_path):
                self.load_novel_chapters(novel_path)
            else:
                self.load_novel(novel_path)
            
            # 更新设置
            self.settings["default_novel"] = selected_novel
            self.settings["default_novel_dir"] = novels_dir  # 保存小说目录
            self.save_settings()
        except Exception as e:
            logger.error(f"小说选择事件处理出错: {str(e)}", exc_info=True)
            messagebox.showerror("错误", f"小说选择出错: {str(e)}")
        
    def load_novel_chapters(self, novel_path):
        """加载小说章节"""
        try:
            # 检查路径是否存在
            if not os.path.exists(novel_path):
                logger.error(f"小说路径不存在: {novel_path}")
                messagebox.showerror("错误", f"小说路径不存在: {novel_path}")
                return
            
            logger.info(f"开始加载小说章节，路径: {novel_path}")
            
            # 清空章节变量
            self.chapter_var.set("")
            
            # 清空章节列表
            for item in self.chapter_list.get_children():
                self.chapter_list.delete(item)
            
            # 获取所有文本文件作为章节
            chapters = []
            for file in os.listdir(novel_path):
                if file.endswith(('.txt', '.md')):
                    chapters.append(file)
                    logger.debug(f"找到章节文件: {file}")
                    
            # 排序章节（可能根据章节号等进行排序）
            chapters.sort()
            logger.info(f"找到 {len(chapters)} 个章节文件")
            
            if not chapters:
                logger.warning(f"在路径 {novel_path} 中没有找到章节文件")
                self.update_status("未找到章节文件")
                return
            
            # 更新当前小说路径，必须在选择章节前设置
            self.current_novel_path = novel_path
            logger.info(f"设置当前小说路径: {self.current_novel_path}")
            
            # 将章节添加到章节列表控件
            for chapter_file in chapters:
                try:
                    # 尝试读取文件获取字数
                    file_path = os.path.join(novel_path, chapter_file)
                    try:
                        # 尝试不同编码读取文件
                        content = None
                        for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-16', 'big5', 'latin1']:
                            try:
                                with open(file_path, 'r', encoding=encoding) as f:
                                    content = f.read()
                                break
                            except UnicodeDecodeError:
                                continue
                        
                        # 如果读取成功，添加到列表
                        if content:
                            word_count = len(content)
                            self.chapter_list.insert("", "end", values=(
                                chapter_file.replace(".txt", "").replace(".md", ""),
                                f"{word_count}字",
                                "未生成"
                            ))
                        else:
                            # 文件无法读取，使用默认值
                            self.chapter_list.insert("", "end", values=(
                                chapter_file.replace(".txt", "").replace(".md", ""),
                                "无法读取",
                                "未生成"
                            ))
                    except Exception as e:
                        logger.error(f"读取章节文件出错: {str(e)}")
                        # 出错时添加默认值
                        self.chapter_list.insert("", "end", values=(
                            chapter_file.replace(".txt", "").replace(".md", ""),
                            "读取出错",
                            "未生成"
                        ))
                except Exception as e:
                    logger.error(f"处理章节文件 {chapter_file} 时出错: {str(e)}")
            
            # 如果有章节，选择第一个
            if chapters:
                logger.info(f"选择第一个章节: {chapters[0]}")
                self.chapter_var.set(chapters[0])
                
                # 选中列表中的第一项
                if self.chapter_list.get_children():
                    first_item = self.chapter_list.get_children()[0]
                    self.chapter_list.selection_set(first_item)
                    self.chapter_list.focus(first_item)
                    self.on_chapter_list_select(None)  # 触发章节列表选择事件
                
            self.update_status(f"已加载 {len(chapters)} 个章节")
            
        except Exception as e:
            logger.error(f"加载小说章节出错: {str(e)}", exc_info=True)
            messagebox.showerror("错误", f"加载小说章节出错: {str(e)}")
            
    def on_chapter_list_select(self, event):
        """章节列表选择事件处理"""
        try:
            selected_items = self.chapter_list.selection()
            if not selected_items:
                return
                
            item = selected_items[0]  # 获取选中的第一项
            chapter_title = self.chapter_list.item(item, "values")[0]
            
            # 查找对应的章节内容
            chapter_content = None
            chapter_index = None
            
            for i, chapter in enumerate(self.novel_chapters):
                title = chapter['title'].split('\n')[0]  # 只显示第一行作为标题
                if chapter_title in title or chapter_title == title:
                    chapter_content = chapter['content']
                    chapter_index = i
                    break
            
            if chapter_content:
                # 显示章节内容
                self.original_text.delete('1.0', tk.END)
                self.original_text.insert(tk.END, chapter_content)
                
                # 记录当前章节索引
                self.current_chapter_index = chapter_index
                
                # 保存选择的章节
                self.settings["selected_chapter"] = chapter_title
                self.save_settings()
                
                # 更新状态栏
                self.update_status(f"已选择: {chapter_title}")
            else:
                logger.error(f"未找到章节内容: {chapter_title}")
                messagebox.showerror("错误", f"未找到章节内容")
            
        except Exception as e:
            logger.error(f"章节列表选择事件处理出错: {str(e)}", exc_info=True)
            messagebox.showerror("错误", f"章节选择出错: {str(e)}")

    def export_all_summaries(self):
        """导出所有章节摘要"""
        try:
            if not hasattr(self, 'current_novel_path') or not self.current_novel_path:
                messagebox.showwarning("警告", "没有选择小说，无法导出摘要")
                return
                
            # 选择导出目录
            export_dir = filedialog.askdirectory(title="选择导出目录")
            if not export_dir:
                return  # 用户取消了选择
                
            # 获取小说名称
            novel_name = os.path.basename(self.current_novel_path)
            
            # 创建小说摘要目录
            summary_dir = os.path.join(export_dir, f"{novel_name}_摘要")
            if os.path.exists(summary_dir):
                if not messagebox.askyesno("确认覆盖", f"摘要目录 '{summary_dir}' 已存在，是否覆盖?"):
                    return  # 用户取消覆盖
                shutil.rmtree(summary_dir)
            os.makedirs(summary_dir)
            
            # 获取章节列表中的所有章节
            all_chapters = []
            for item in self.chapter_list.get_children():
                chapter_title = self.chapter_list.item(item, "values")[0]
                # 查找对应的文件名
                chapter_file = None
                for file in os.listdir(self.current_novel_path):
                    if file.endswith(('.txt', '.md')) and (chapter_title in file or chapter_title == file.replace(".txt", "").replace(".md", "")):
                        chapter_file = file
                        break
                
                if chapter_file:
                    all_chapters.append((item, chapter_file))
            
            if not all_chapters:
                messagebox.showwarning("警告", "没有发现章节，无法导出摘要")
                return
                
            # 开始批量生成摘要的线程
            def export_summaries():
                total_chapters = len(all_chapters)
                for i, (item_id, chapter_file) in enumerate(all_chapters):
                    try:
                        # 更新进度
                        progress = (i / total_chapters) * 100
                        self.update_progress(progress, f"导出摘要: {chapter_file}")
                        
                        # 读取章节内容
                        chapter_path = os.path.join(self.current_novel_path, chapter_file)
                        content = None
                        # 尝试不同编码读取文件
                        for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-16', 'big5', 'latin1']:
                            try:
                                with open(chapter_path, 'r', encoding=encoding) as f:
                                    content = f.read()
                                break
                            except UnicodeDecodeError:
                                continue
                            except Exception as e:
                                logger.error(f"读取文件时出错: {str(e)}")
                        
                        if not content:
                            logger.error(f"无法读取章节文件: {chapter_path}")
                            continue
                            
                        # 生成摘要
                        summary = self.generate_summary_text(content, self.summary_mode_var.get(), self.summary_length_var.get())
                        
                        # 保存摘要
                        summary_path = os.path.join(summary_dir, f"{os.path.splitext(chapter_file)[0]}_摘要.txt")
                        with open(summary_path, 'w', encoding='utf-8') as f:
                            f.write(summary)
                            
                        # 更新章节列表状态
                        self.chapter_list.item(item_id, values=(
                            self.chapter_list.item(item_id, "values")[0],
                            self.chapter_list.item(item_id, "values")[1],
                            "已生成"
                        ))
                            
                    except Exception as e:
                        logger.error(f"导出章节 {chapter_file} 摘要出错: {str(e)}")
                        
                # 完成导出
                self.update_progress(100, "摘要导出完成")
                messagebox.showinfo("完成", f"所有摘要已导出至: {summary_dir}")
                
            # 启动线程执行导出
            threading.Thread(target=export_summaries, daemon=True).start()
            
        except Exception as e:
            logger.error(f"导出所有摘要出错: {str(e)}")
            messagebox.showerror("错误", f"导出所有摘要出错: {str(e)}")

    def save_summary(self):
        """保存摘要"""
        try:
            # 获取摘要内容
            summary_content = self.summary_text.get(1.0, tk.END).strip()
            if not summary_content:
                messagebox.showwarning("警告", "摘要内容为空，无法保存")
                return
                
            # 打开保存对话框
            file_path = filedialog.asksaveasfilename(
                title="保存摘要",
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("Markdown", "*.md"), ("所有文件", "*.*")]
            )
            if not file_path:
                return  # 用户取消了保存
                
            # 保存内容到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(summary_content)
                
            # 更新状态
            file_name = os.path.basename(file_path)
            self.update_status(f"摘要已保存至: {file_name}")
            
        except Exception as e:
            logger.error(f"保存摘要出错: {str(e)}")
            messagebox.showerror("错误", f"保存摘要出错: {str(e)}")

    def open_file(self):
        """打开单个文件进行摘要"""
        try:
            file_path = filedialog.askopenfilename(
                title="选择文件",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
            if not file_path:
                return  # 用户取消了打开
                
            # 尝试不同编码打开文件
            content = None
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    logger.error(f"打开文件出错: {str(e)}")
                    messagebox.showerror("错误", f"打开文件出错: {str(e)}")
                    return
            
            if content is None:
                messagebox.showerror("错误", "无法以支持的编码打开文件")
                return
                
            # 显示文件内容到原文区域
            self.original_text.delete(1.0, tk.END)
            self.original_text.insert(tk.END, content)
            
            # 更新状态
            file_name = os.path.basename(file_path)
            self.update_status(f"已打开文件: {file_name}")
            
        except Exception as e:
            logger.error(f"打开文件出错: {str(e)}")
            messagebox.showerror("错误", f"打开文件出错: {str(e)}")

    def reload_model(self):
        """重新加载当前选择的模型"""
        current_model = self.model_var.get()
        if not current_model:
            messagebox.showwarning("警告", "请先选择一个模型")
            return
            
        # 清空摘要区域
        self.summary_text.delete(1.0, tk.END)
        
        # 更新状态
        self.update_status(f"正在重新加载模型: {current_model}")
        
        # 重新加载模型
        self.load_model(current_model)

    def browse_novel(self):
        """浏览并选择小说目录"""
        novel_dir = filedialog.askdirectory(title="选择小说目录")
        if not novel_dir:
            logger.info("用户取消了选择小说目录")
            return
            
        logger.info(f"用户选择小说目录: {novel_dir}")
        self.novel_path_var.set(novel_dir)
        self.current_novel_path = novel_dir
        
        # 更新小说目录下的章节列表
        self.load_novel_chapters(novel_dir)
        
        # 保存设置
        self.settings["default_novel"] = os.path.basename(novel_dir)
        self.save_settings()
        
        # 更新状态
        self.update_status(f"已加载小说: {os.path.basename(novel_dir)}")

    def browse_model(self):
        """浏览并选择本地模型文件"""
        # 设置为Ollama本地模型
        self.model_var.set("Ollama 本地模型")
        
        # 打开文件选择对话框
        model_path = filedialog.askopenfilename(
            title="选择本地模型文件",
            filetypes=[
                ("GGUF模型", "*.gguf"),
                ("量化模型", "*.bin"),
                ("所有文件", "*.*")
            ],
            initialdir=os.path.dirname(self.current_local_model_path) if self.current_local_model_path else None
        )
        
        if not model_path:
            logger.info("用户取消了选择本地模型")
            return
            
        logger.info(f"用户选择本地模型: {model_path}")
        
        # 保存模型路径
        self.current_local_model_path = model_path
        self.api_key_var.set(model_path)
        
        # 更新API密钥标签
        self.api_key_label.config(text="模型路径:")
        
        # 隐藏API密钥，显示模型路径
        self.api_key_entry.config(show="")
        
        # 显示浏览按钮
        self.browse_model_btn.pack(side=tk.RIGHT)
        
        # 保存设置
        self.settings["default_local_model"] = model_path
        self.save_settings()
        
        # 更新状态
        self.update_status(f"已选择本地模型: {os.path.basename(model_path)}")
        
        # 询问是否立即加载模型
        if messagebox.askyesno("加载模型", "是否立即加载选择的模型?"):
            self.load_model("ollama-local")

    def scan_novels(self):
        """扫描小说目录，查找并加载小说列表"""
        try:
            self.update_status("正在扫描小说目录...")
            novels_dir = "novels"
            self.novels_dir = novels_dir  # 更新当前小说目录
            
            if not os.path.exists(novels_dir):
                os.mkdir(novels_dir)
                logger.info(f"创建小说目录: {novels_dir}")
                
            # 查找小说文件
            novel_files = []
            for file in os.listdir(novels_dir):
                file_path = os.path.join(novels_dir, file)
                if os.path.isfile(file_path) and file.endswith(('.txt', '.md')):
                    novel_files.append(file)
                    logger.debug(f"找到小说文件: {file}")
            
            # 查找小说目录
            novel_dirs = []
            for item in os.listdir(novels_dir):
                item_path = os.path.join(novels_dir, item)
                if os.path.isdir(item_path):
                    # 检查目录中是否有txt文件
                    has_txt = False
                    for file in os.listdir(item_path):
                        if file.endswith(('.txt', '.md')):
                            has_txt = True
                            break
                    
                    if has_txt:
                        novel_dirs.append(os.path.basename(item_path))  # 只添加目录名
                        logger.debug(f"找到小说目录: {item}")
            
            # 更新小说下拉框
            all_novels = novel_files + novel_dirs
            if all_novels:
                self.novel_combobox['values'] = all_novels
                logger.info(f"更新小说下拉框，共 {len(all_novels)} 个小说")
            
            # 如果找到了小说文件或目录
            if novel_files or novel_dirs:
                # 如果是用于初始化的扫描，尝试加载默认小说
                if not self.current_novel_path:
                    self.load_default_novel()
                
                logger.info(f"扫描完成，找到 {len(novel_files)} 个小说文件和 {len(novel_dirs)} 个小说目录")
                self.update_status(f"扫描完成，找到 {len(novel_files) + len(novel_dirs)} 个小说")
                return
            
            # 如果没有找到任何小说，显示提示
            messagebox.showinfo("提示", "未找到小说文件或目录，请将小说文件放在novels目录下")
            logger.warning("未找到小说文件或目录")
            self.update_status("未找到小说文件或目录")
            
        except Exception as e:
            logger.error(f"扫描小说目录出错: {str(e)}", exc_info=True)
            messagebox.showerror("错误", f"扫描小说目录出错: {str(e)}")

    def update_summary_display(self, summary):
        """更新摘要显示"""
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, summary)
        self.update_status("摘要生成完成")
        self.update_progress_log(1.0, 100, "摘要生成完成")
        
    def handle_summary_error(self, error_msg):
        """处理摘要生成错误"""
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, f"生成摘要出错: {error_msg}")
        self.update_status(f"摘要生成失败: {error_msg}")
        self.update_progress_log(0, 100, f"摘要生成失败: {error_msg}")

    def _generate_summary_thread(self, original_content, summary_mode, summary_length):
        """在后台线程中生成摘要的方法"""
        try:
            # 生成摘要
            summary = self.generate_summary_text(original_content, summary_mode, summary_length)
            
            # 在UI线程中更新摘要区域
            self.root.after(0, lambda: self.update_summary_display(summary))
        except Exception as e:
            logger.error(f"生成摘要线程出错: {str(e)}", exc_info=True)
            self.root.after(0, lambda: self.handle_summary_error(str(e)))
        finally:
            # 恢复UI状态
            def reset_ui():
                # 恢复生成按钮状态
                if hasattr(self, 'generate_button'):
                    self.generate_button.config(text="生成摘要", state=tk.NORMAL)
                if hasattr(self, 'stop_button'):
                    self.stop_button.config(state=tk.DISABLED)
                # 重置生成状态
                self.generating = False
            
            self.root.after(0, reset_ui)

    def browse_novels(self):
        """浏览和选择小说文件"""
        try:
            novels_dir = "novels"
            
            if not os.path.exists(novels_dir):
                os.mkdir(novels_dir)
                logger.info(f"创建小说目录: {novels_dir}")
                
            # 查找小说文件
            novel_files = []
            for file in os.listdir(novels_dir):
                file_path = os.path.join(novels_dir, file)
                if os.path.isfile(file_path) and file.endswith(('.txt', '.md')):
                    novel_files.append(file_path)
            
            # 查找小说目录
            novel_dirs = []
            for item in os.listdir(novels_dir):
                item_path = os.path.join(novels_dir, item)
                if os.path.isdir(item_path):
                    # 检查目录中是否有txt文件
                    has_txt = False
                    for file in os.listdir(item_path):
                        if file.endswith(('.txt', '.md')):
                            has_txt = True
                            break
                    
                    if has_txt:
                        novel_dirs.append(item_path)
            
            # 如果没有找到任何小说，显示提示
            if not novel_files and not novel_dirs:
                messagebox.showinfo("提示", "未找到小说文件或目录，请将小说文件放在novels目录下")
                return
            
            # 创建小说列表窗口
            novel_window = tk.Toplevel(self.root)
            novel_window.title("选择小说")
            novel_window.geometry("600x400")
            novel_window.minsize(400, 300)
            
            # 创建列表框架
            list_frame = ttk.LabelFrame(novel_window, text="可用的小说")
            list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 创建列表框
            novel_listbox = tk.Listbox(list_frame, font=("宋体", 12))
            novel_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # 添加滚动条
            scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=novel_listbox.yview)
            novel_listbox.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
            
            # 添加小说文件到列表
            for file_path in novel_files:
                file_name = os.path.basename(file_path)
                novel_listbox.insert(tk.END, f"[文件] {file_name}")
            
            # 添加小说目录到列表
            for dir_path in novel_dirs:
                dir_name = os.path.basename(dir_path)
                novel_listbox.insert(tk.END, f"[目录] {dir_name}")
            
            # 按钮框架
            btn_frame = ttk.Frame(novel_window)
            btn_frame.pack(fill=tk.X, pady=10)
            
            # 选择按钮
            def on_select():
                selected_idx = novel_listbox.curselection()
                if not selected_idx:
                    messagebox.showinfo("提示", "请先选择一个小说")
                    return
                    
                selected_item = novel_listbox.get(selected_idx[0])
                
                # 处理文件和目录选择
                if selected_item.startswith("[文件]"):
                    file_name = selected_item[7:].strip()  # 去除前缀和空格
                    file_path = os.path.join(novels_dir, file_name)
                    logger.info(f"选择小说文件: {file_path}")
                    self.load_novel(file_path)
                else:
                    dir_name = selected_item[7:].strip()  # 去除前缀和空格
                    dir_path = os.path.join(novels_dir, dir_name)
                    logger.info(f"选择小说目录: {dir_path}")
                    self.load_novel_chapters(dir_path)
                
                # 关闭窗口
                novel_window.destroy()
                
            def on_cancel():
                novel_window.destroy()
                
            # 添加按钮
            select_btn = ttk.Button(btn_frame, text="选择", command=on_select, width=10)
            select_btn.pack(side=tk.RIGHT, padx=10)
            
            cancel_btn = ttk.Button(btn_frame, text="取消", command=on_cancel, width=10)
            cancel_btn.pack(side=tk.RIGHT, padx=10)
            
        except Exception as e:
            logger.error(f"浏览小说列表出错: {str(e)}", exc_info=True)
            messagebox.showerror("错误", f"浏览小说列表出错: {str(e)}")

    def open_novels_dir(self):
        """打开小说目录并加载小说列表"""
        try:
            # 打开文件选择对话框
            novel_dir = filedialog.askdirectory(title="选择小说目录")
            if not novel_dir:
                logger.info("用户取消了选择小说目录")
                return
                
            logger.info(f"用户选择小说目录: {novel_dir}")
            self.update_status(f"正在加载目录: {novel_dir}")
            
            # 检查目录是否存在
            if not os.path.exists(novel_dir) or not os.path.isdir(novel_dir):
                messagebox.showerror("错误", "选择的路径不是有效的目录")
                return
                
            # 查找所有TXT和MD文件
            novel_files = []
            for file in os.listdir(novel_dir):
                file_path = os.path.join(novel_dir, file)
                if os.path.isfile(file_path) and file.endswith(('.txt', '.md')):
                    novel_files.append(file)
                    logger.debug(f"找到小说文件: {file}")
            
            if not novel_files:
                messagebox.showinfo("提示", "所选目录中没有找到文本文件(.txt, .md)")
                return
                
            # 更新小说下拉框
            self.novel_combobox['values'] = novel_files
            logger.info(f"更新小说下拉框，共 {len(novel_files)} 个文件")
            
            # 选择第一个小说
            if novel_files:
                self.novel_var.set(novel_files[0])
                # 触发小说选择事件
                self.on_novel_select(None)
                
            # 更新当前小说目录
            self.novels_dir = novel_dir
            
            # 更新状态
            self.update_status(f"已加载 {len(novel_files)} 个小说文件")
            
        except Exception as e:
            logger.error(f"打开小说目录出错: {str(e)}", exc_info=True)
            messagebox.showerror("错误", f"打开小说目录出错: {str(e)}")

    def progress_callback_adapter(self, progress, message, total=None):
        """适配器方法，用于将TitanSummarizer的回调转换为update_progress_log格式"""
        try:
            # 如果参数顺序和类型不匹配，尝试进行推断和调整
            # 确保progress是一个浮点数（范围0-1）
            if isinstance(progress, str) and isinstance(message, (int, float)):
                # 如果参数顺序被颠倒了，则交换它们
                progress, message = message, progress
                
            # 确保progress是数值类型
            if not isinstance(progress, (int, float)):
                try:
                    progress = float(progress)
                except (ValueError, TypeError):
                    progress = 0.0
                    
            # 确保total是有效的数值，如果为None则使用默认值100
            if total is None or not isinstance(total, (int, float)):
                total_value = 100
            else:
                total_value = total
                
            # 调用UI的进度更新方法，按照正确的参数顺序
            self.update_progress_log(progress, total_value, message)
        except Exception as e:
            logger.error(f"进度回调适配器错误: {str(e)}")
            # 在出错时，直接用最保守的参数调用更新方法
            self.update_progress_log(0.0, 100, f"更新进度出错: {str(e)}")

def save_settings_file():
    """创建默认设置文件"""
    settings = {
        "default_model": "ollama-local",
        "default_local_model": "D:\\Work\\AI_Models\\Qwen\\Qwen2-0.5B-Instruct-GGUF\\qwen2-0_5b-instruct-q4_k_m.gguf",
        "default_length": 100,
        "default_novel": "凡人修仙传",  # 修改为小说名称而不是路径
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