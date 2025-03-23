#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Titan摘要器 - 主UI模块
提供图形用户界面的主要实现
"""

import os
import sys
import time
import json
import queue
import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# 确保src目录在路径中
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# 导入自定义模块
from models.factory import SummarizerFactory
from ui.progress_bar import create_progress_callback, ProgressBar
from utils.file_utils import read_text_file, save_text_file, find_files

# 设置日志
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
    """Titan摘要生成器UI类"""
    
    def __init__(self, root):
        """初始化UI"""
        self.root = root
        self.root.title("Titan摘要生成器")
        self.root.geometry("1000x700")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 初始化变量和设置
        self.summarizer = None
        self.generating = False
        self.current_file_path = None
        self.summarize_queue = queue.Queue()
        
        # 加载设置
        self.settings = self.load_settings()
        
        # 创建UI组件
        self.create_menu()
        self.create_control_bar()
        self.create_text_areas()
        self.create_status_bar()
        
        # 重定向标准输出到日志区域
        sys.stdout = TextRedirector(self.log_text)
        sys.stderr = TextRedirector(self.log_text)
        
        # 初始消息
        self.update_status("就绪")
        logger.info("Titan摘要生成器启动完成")
        
        # 准备加载默认模型
        self.load_default_model()
        
        # 启动队列处理
        self.root.after(100, self.process_summarize_queue)
    
    def load_settings(self):
        """加载设置"""
        default_settings = {
            "default_model": "deepseek-api",
            "default_length": 200,
            "api_key": None,
            "theme": "clam"
        }
        
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    logger.info(f"成功加载设置: {settings}")
                    
                    # 确保default_length是200
                    if "default_length" not in settings or settings["default_length"] != 200:
                        settings["default_length"] = 200
                        
                    return settings
            else:
                logger.warning("设置文件不存在，使用默认值")
                return default_settings
        except Exception as e:
            logger.warning(f"加载设置失败，使用默认值: {str(e)}")
            return default_settings
    
    def save_settings(self):
        """保存设置"""
        try:
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
            logger.info("设置已保存")
        except Exception as e:
            logger.error(f"保存设置失败: {str(e)}")
    
    def load_default_model(self):
        """加载默认模型"""
        default_model = self.settings.get("default_model", "deepseek-api")
        api_key = self.settings.get("api_key")
        
        logger.info(f"尝试加载默认模型: {default_model}")
        
        # 设置模型下拉框的值
        if default_model == "deepseek-api":
            self.model_var.set("DeepSeek在线API")
            self.root.after(1000, lambda: self.load_model("deepseek-api"))
        elif default_model == "ollama-local":
            self.model_var.set("Ollama本地模型")
            self.root.after(1000, lambda: self.load_model("ollama-local"))
        else:
            logger.warning(f"未识别的默认模型: {default_model}")
            
        # 加载默认小说文件
        default_novel_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                         "novels", "凡人修仙传_完整版.txt")
        if os.path.exists(default_novel_path):
            logger.info(f"加载默认小说: {default_novel_path}")
            self.root.after(2000, lambda: self.load_file(default_novel_path))
    
    def create_menu(self):
        """创建菜单栏"""
        menu_bar = tk.Menu(self.root)
        
        # 文件菜单
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="打开文件", command=self.open_file)
        file_menu.add_command(label="打开目录", command=self.open_directory)
        file_menu.add_separator()
        file_menu.add_command(label="保存摘要", command=self.save_summary)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menu_bar.add_cascade(label="文件", menu=file_menu)
        
        # 模型菜单
        model_menu = tk.Menu(menu_bar, tearoff=0)
        model_menu.add_command(label="DeepSeek API", command=lambda: self.load_model("deepseek-api"))
        model_menu.add_command(label="Ollama本地模型", command=lambda: self.load_model("ollama-local"))
        model_menu.add_separator()
        model_menu.add_command(label="浏览模型", command=self.browse_model)
        model_menu.add_command(label="设置API密钥", command=self.set_api_key)
        menu_bar.add_cascade(label="模型", menu=model_menu)
        
        # 设置菜单
        settings_menu = tk.Menu(menu_bar, tearoff=0)
        settings_menu.add_command(label="保存当前设置为默认", command=self.save_as_default)
        menu_bar.add_cascade(label="设置", menu=settings_menu)
        
        # 帮助菜单
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="使用指南", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
        menu_bar.add_cascade(label="帮助", menu=help_menu)
        
        self.root.config(menu=menu_bar)
    
    def create_control_bar(self):
        """创建控制栏"""
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 文件信息
        file_frame = ttk.LabelFrame(control_frame, text="文件信息")
        file_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Label(file_frame, text="当前文件:").grid(row=0, column=0, padx=2, pady=2, sticky=tk.W)
        self.file_path_var = tk.StringVar(value="未选择文件")
        file_path_label = ttk.Label(file_frame, textvariable=self.file_path_var, width=40)
        file_path_label.grid(row=0, column=1, padx=2, pady=2, sticky=tk.W)
        
        # 添加浏览按钮
        browse_btn = ttk.Button(file_frame, text="浏览文件", command=self.open_file, width=10)
        browse_btn.grid(row=0, column=2, padx=2, pady=2, sticky=tk.W)
        
        # 模型设置
        model_frame = ttk.LabelFrame(control_frame, text="模型设置")
        model_frame.pack(side=tk.LEFT, padx=5, fill=tk.X)
        
        ttk.Label(model_frame, text="模型选择:").grid(row=0, column=0, padx=2, pady=2, sticky=tk.W)
        self.model_var = tk.StringVar(value="请选择模型")
        self.model_combobox = ttk.Combobox(model_frame, textvariable=self.model_var, state="readonly", width=40)
        
        # 初始加载基本模型选项
        model_options = ["DeepSeek在线API"]
        
        # 获取本地GGUF模型列表
        self.local_models = []
        try:
            from src.api.ollama_api import OllamaAPI
            api = OllamaAPI()
            self.local_models = api.find_all_models()
            if self.local_models:
                for model in self.local_models:
                    model_name = os.path.basename(model['path'])
                    model_options.append(f"{model_name}")
                logger.info(f"已添加 {len(self.local_models)} 个本地模型到选项中")
        except Exception as e:
            logger.error(f"获取本地模型列表时出错: {str(e)}")
            
        self.model_combobox["values"] = model_options
        self.model_combobox.grid(row=0, column=1, padx=2, pady=2, sticky=tk.W)
        self.model_combobox.bind("<<ComboboxSelected>>", self.on_model_select)
        
        # 摘要控制
        summary_frame = ttk.LabelFrame(control_frame, text="摘要控制")
        summary_frame.pack(side=tk.LEFT, padx=5, fill=tk.X)
        
        # 摘要模式选择
        ttk.Label(summary_frame, text="模式:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.summary_mode_var = tk.StringVar(value="生成式")
        mode_combobox = ttk.Combobox(summary_frame, textvariable=self.summary_mode_var, state="readonly", width=8)
        mode_combobox["values"] = ["生成式", "提取式"]
        mode_combobox.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 摘要长度选择
        ttk.Label(summary_frame, text="长度:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.summary_length_var = tk.StringVar(value=str(self.settings.get("default_length", 200)))
        length_combobox = ttk.Combobox(summary_frame, textvariable=self.summary_length_var, state="normal", width=6)
        length_combobox["values"] = ["100", "200", "300", "500", "800", "1000"]
        length_combobox.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        length_combobox.bind("<FocusOut>", self.validate_length)
        
        # 生成摘要按钮
        self.generate_button = ttk.Button(summary_frame, text="生成摘要", command=self.generate_summary)
        self.generate_button.grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        
        # 批量处理按钮
        self.batch_button = ttk.Button(summary_frame, text="批量处理", command=self.batch_process)
        self.batch_button.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
    
    def create_text_areas(self):
        """创建文本区域"""
        # 创建主要框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建PanedWindow，支持面板大小调整
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 创建左侧文件列表框架
        files_frame = ttk.LabelFrame(paned_window, text="章节列表")
        paned_window.add(files_frame, weight=1)
        
        # 创建文件列表
        columns = ("名称", "大小", "状态")
        self.file_list = ttk.Treeview(files_frame, columns=columns, show="headings", height=25)
        self.file_list.column("名称", width=150, anchor="w")
        self.file_list.column("大小", width=60, anchor="center")
        self.file_list.column("状态", width=60, anchor="center")
        self.file_list.heading("名称", text="名称")
        self.file_list.heading("大小", text="大小")
        self.file_list.heading("状态", text="状态")
        
        # 添加滚动条
        file_scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.file_list.yview)
        self.file_list.configure(yscrollcommand=file_scrollbar.set)
        
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定选择事件
        self.file_list.bind("<<TreeviewSelect>>", self.on_file_select)
        
        # 创建右侧内容/摘要区域
        content_frame = ttk.Frame(paned_window)
        paned_window.add(content_frame, weight=3)
        
        # 创建垂直分隔的PanedWindow
        vertical_paned = ttk.PanedWindow(content_frame, orient=tk.VERTICAL)
        vertical_paned.pack(fill=tk.BOTH, expand=True)
        
        # 创建原文区域
        original_frame = ttk.LabelFrame(vertical_paned, text="原文")
        vertical_paned.add(original_frame, weight=1)
        
        self.original_text = scrolledtext.ScrolledText(original_frame, wrap=tk.WORD, width=80, height=15)
        self.original_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建摘要区域
        summary_frame = ttk.LabelFrame(vertical_paned, text="摘要")
        vertical_paned.add(summary_frame, weight=1)
        
        self.summary_text = scrolledtext.ScrolledText(summary_frame, wrap=tk.WORD, width=80, height=15)
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建隐藏的日志文本区域用于记录日志
        self.log_text = tk.Text(self.root)
        self.log_text.pack_forget()  # 不显示在UI上
    
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
            
    def on_closing(self):
        """关闭窗口时的处理"""
        if messagebox.askokcancel("退出", "确定要退出程序吗？"):
            # 保存设置
            self.save_settings()
            self.root.destroy()
            
    def show_help(self):
        """显示帮助信息"""
        help_text = """Titan摘要器使用指南

1. 基本使用:
   - 打开文件: 点击"浏览文件"按钮选择要摘要的文本文件
   - 选择模型: 从下拉列表中选择要使用的模型类型
   - 设置摘要模式和长度: 选择"生成式"或"提取式"，并设置摘要长度
   - 生成摘要: 点击"生成摘要"按钮

2. 批量处理:
   - 点击"打开目录"选择包含多个文件的文件夹
   - 设置好模型、模式和长度后，点击"批量处理"
   - 摘要结果将保存在原文件目录的"summaries"子目录下

3. 模型说明:
   - DeepSeek在线API: 需要设置API密钥，质量高
   - Ollama本地模型: 本地运行，无需联网，但需要安装Ollama

4. 小提示:
   - 提取式摘要不需要AI模型，适合快速摘要
   - 生成式摘要质量更高，但速度较慢
"""
        messagebox.showinfo("使用指南", help_text)
        
    def show_about(self):
        """显示关于信息"""
        about_text = """Titan摘要器 v1.0.0

一个多功能文本摘要工具，支持以下特性：
- 生成式和提取式摘要
- 多种模型支持（DeepSeek API、Ollama本地模型）
- 批量处理功能
- 自定义摘要长度

开发者: AI辅助开发
日期: 2024
"""
        messagebox.showinfo("关于", about_text)
        
    def process_summarize_queue(self):
        """处理摘要队列中的任务"""
        try:
            if not self.summarize_queue.empty():
                # 获取队列中的任务
                task = self.summarize_queue.get(False)
                
                # 处理任务
                self.handle_summarize_task(task)
                
                # 标记任务完成
                self.summarize_queue.task_done()
        except queue.Empty:
            pass
        except Exception as e:
            logger.error(f"处理摘要队列任务时出错: {str(e)}")
            
        # 继续检查队列
        self.root.after(100, self.process_summarize_queue)
    
    def handle_summarize_task(self, task):
        """处理摘要任务"""
        task_type = task.get("type", "")
        
        if task_type == "single_file":
            # 处理单个文件
            file_path = task.get("file_path", "")
            mode = task.get("mode", "generative")
            max_length = task.get("max_length", 500)
            
            if not file_path or not os.path.exists(file_path):
                self.update_status(f"文件不存在: {file_path}")
                return
                
            # 显示文件内容
            self.show_file_content(file_path)
            
            # 开始生成摘要
            self.generating = True
            self.generate_button.config(text="停止生成")
            self.update_status(f"正在生成摘要: {os.path.basename(file_path)}")
            
            # 定义进度回调
            def progress_callback(current, total=100, message=""):
                self.update_progress(current, message)
            
            try:
                # 生成摘要
                self.update_progress(0, "开始生成摘要...")
                
                # 转换模式
                mode_map = {"生成式": "generative", "提取式": "extractive"}
                api_mode = mode_map.get(self.summary_mode_var.get(), "generative")
                
                # 调用摘要生成
                title, summary = self.summarizer.summarize_file(
                    file_path=file_path,
                    output_path=None,  # 不自动保存
                    max_length=max_length,
                    mode=api_mode
                )
                
                # 显示摘要
                self.summary_text.delete(1.0, tk.END)
                self.summary_text.insert(tk.END, summary)
                
                # 更新文件列表中的状态
                for item in self.file_list.get_children():
                    if self.file_list.item(item, "values")[0] == os.path.basename(file_path):
                        self.file_list.item(item, values=(
                            os.path.basename(file_path),
                            self.file_list.item(item, "values")[1],
                            "已摘要"
                        ))
                        break
                
                self.update_status(f"摘要完成: {os.path.basename(file_path)}")
                
            except Exception as e:
                logger.error(f"生成摘要时出错: {str(e)}")
                self.update_status(f"生成摘要失败: {str(e)}")
                self.summary_text.delete(1.0, tk.END)
                self.summary_text.insert(tk.END, f"生成摘要失败: {str(e)}")
            
            finally:
                # 更新UI状态
                self.generating = False
                self.generate_button.config(text="生成摘要")
                self.update_progress(100, "完成")
        
        elif task_type == "batch":
            # 处理批量任务
            directory = task.get("directory", "")
            mode = task.get("mode", "generative")
            max_length = task.get("max_length", 500)
            recursive = task.get("recursive", True)
            
            if not directory or not os.path.isdir(directory):
                self.update_status(f"目录不存在: {directory}")
                return
            
            # 创建输出目录
            output_dir = os.path.join(directory, "summaries")
            os.makedirs(output_dir, exist_ok=True)
            
            # 开始批量处理
            self.generating = True
            self.batch_button.config(text="停止处理")
            self.update_status(f"正在批量处理目录: {directory}")
            
            try:
                # 转换模式
                mode_map = {"生成式": "generative", "提取式": "extractive"}
                api_mode = mode_map.get(self.summary_mode_var.get(), "generative")
                
                # 调用批量处理
                results = self.summarizer.summarize_directory(
                    directory=directory,
                    output_directory=output_dir,
                    file_extensions=[".txt", ".md", ".json"],
                    max_length=max_length,
                    mode=api_mode,
                    recursive=recursive
                )
                
                # 更新状态
                self.update_status(f"批量处理完成，共处理 {len(results)} 个文件")
                
                # 创建索引文件
                index_path = os.path.join(output_dir, "index.md")
                index_content = f"# 摘要索引 - {os.path.basename(directory)}\n\n"
                
                for item in results:
                    if item.get("output"):
                        rel_path = os.path.relpath(item["output"], output_dir)
                        index_content += f"- [{item['title']}]({rel_path})\n"
                
                save_text_file(index_path, index_content)
                
                # 打开输出目录
                self.open_folder(output_dir)
                
            except Exception as e:
                logger.error(f"批量处理时出错: {str(e)}")
                self.update_status(f"批量处理失败: {str(e)}")
            
            finally:
                # 更新UI状态
                self.generating = False
                self.batch_button.config(text="批量处理")
                self.update_progress(100, "完成")
        
    def on_model_select(self, event):
        """模型选择改变时的处理"""
        model_name = self.model_var.get()
        
        if model_name == "DeepSeek在线API":
            self.load_model("deepseek-api")
        elif model_name == "Ollama本地模型":
            self.load_model("ollama-local")
        elif model_name.startswith("本地: "):
            # 处理直接选择的本地模型
            selected_model_name = model_name[4:]  # 移除 "本地: " 前缀
            
            # 查找对应的模型路径
            selected_model = None
            for model in self.local_models:
                if os.path.basename(model['path']) == selected_model_name:
                    selected_model = model
                    break
                    
            if selected_model:
                logger.info(f"直接选择本地模型: {selected_model['path']}")
                # 先设置为ollama-local类型
                self.load_model("ollama-local", selected_model['path'])
            else:
                logger.error(f"未找到所选模型: {selected_model_name}")
                messagebox.showerror("模型错误", f"未找到所选模型: {selected_model_name}")
    
    def validate_length(self, event):
        """验证摘要长度输入"""
        try:
            length = int(self.summary_length_var.get())
            if length < 1:
                self.summary_length_var.set("100")
            elif length > 2000:
                self.summary_length_var.set("2000")
                messagebox.showwarning("长度限制", "摘要长度不能超过2000")
        except ValueError:
            self.summary_length_var.set("500")
            messagebox.showwarning("输入错误", "摘要长度必须是数字")
    
    def open_file(self):
        """打开文件对话框"""
        file_path = filedialog.askopenfilename(
            title="选择要摘要的文件",
            filetypes=[
                ("文本文件", "*.txt"), 
                ("Markdown文件", "*.md"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path):
        """加载文件内容"""
        try:
            # 清空文件列表
            for item in self.file_list.get_children():
                self.file_list.delete(item)
            
            # 更新当前文件路径
            self.current_file_path = file_path
            self.file_path_var.set(os.path.basename(file_path))
            
            # 读取文件内容
            content = read_text_file(file_path, encoding='utf-8')  # 指定编码为utf-8
            
            # 显示文件内容
            self.show_file_content(file_path)
            
            # 清空摘要内容
            self.summary_text.delete(1.0, tk.END)
            
            # 检查是否存在已保存的摘要文件
            base_name = os.path.splitext(file_path)[0]
            summary_file = f"{base_name}_sum.json"
            
            # 尝试加载已有摘要
            saved_summaries = None
            if os.path.exists(summary_file):
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        saved_summaries = json.load(f)
                        logger.info(f"已加载保存的摘要: {summary_file}")
                except Exception as e:
                    logger.error(f"加载摘要文件失败: {str(e)}")
            
            # 获取章节信息
            from src.utils.file_utils import split_into_chapters
            chapters = split_into_chapters(content)
            
            # 如果没有章节，则将整个文件作为一个章节
            if not chapters:
                chapters = [("完整文件", content)]
            
            # 添加章节到列表
            for i, (title, chapter_content) in enumerate(chapters):
                # 计算章节大小
                chapter_size = len(chapter_content) // 1024  # KB
                
                # 检查章节状态
                status = "未处理"
                
                # 如果有已保存的摘要，更新状态
                if saved_summaries and i < len(saved_summaries.get("chapters", [])):
                    status = "已摘要"
                
                # 添加到章节列表
                self.file_list.insert("", "end", values=(
                    title,
                    f"{chapter_size} KB",
                    status
                ), tags=(str(i),))  # 使用索引作为标签
            
            # 存储章节信息
            self.chapters = chapters
            
            self.update_status(f"已加载文件: {os.path.basename(file_path)}, 共 {len(chapters)} 个章节")
            
        except Exception as e:
            logger.error(f"加载文件失败: {str(e)}")
            messagebox.showerror("加载错误", f"无法加载文件: {str(e)}")
    
    def show_file_content(self, file_path):
        """显示文件内容"""
        try:
            content = read_text_file(file_path, encoding='utf-8')  # 指定编码为utf-8
            
            self.original_text.delete(1.0, tk.END)
            self.original_text.insert(tk.END, content)
            
        except Exception as e:
            logger.error(f"显示文件内容失败: {str(e)}")
            self.original_text.delete(1.0, tk.END)
            self.original_text.insert(tk.END, f"无法显示文件内容: {str(e)}")
    
    def open_directory(self):
        """打开目录对话框"""
        directory = filedialog.askdirectory(title="选择要处理的目录")
        
        if directory:
            self.load_directory(directory)
    
    def load_directory(self, directory):
        """加载目录中的文件"""
        try:
            # 清空文件列表
            for item in self.file_list.get_children():
                self.file_list.delete(item)
            
            # 查找文件
            files = find_files(directory, [".txt", ".md"], recursive=True)
            
            if not files:
                messagebox.showinfo("提示", "目录中没有找到文本文件")
                return
            
            # 添加到文件列表
            for file_path in files:
                file_size = os.path.getsize(file_path) // 1024  # KB
                self.file_list.insert("", "end", values=(
                    os.path.basename(file_path),
                    f"{file_size} KB",
                    "未处理"
                ))
            
            # 更新当前目录
            self.current_directory = directory
            self.file_path_var.set(f"目录: {os.path.basename(directory)}")
            
            # 清空文本区域
            self.original_text.delete(1.0, tk.END)
            self.summary_text.delete(1.0, tk.END)
            
            self.update_status(f"已加载目录: {directory}，找到 {len(files)} 个文件")
            
        except Exception as e:
            logger.error(f"加载目录失败: {str(e)}")
            messagebox.showerror("加载错误", f"无法加载目录: {str(e)}")
    
    def on_file_select(self, event):
        """选择章节列表中的章节"""
        try:
            # 获取选中的项
            selected = self.file_list.selection()
            
            if not selected:
                return
                
            # 获取章节标题和索引
            chapter_title = self.file_list.item(selected[0], "values")[0]
            chapter_idx = int(self.file_list.item(selected[0], "tags")[0])
            
            # 如果有章节数据
            if hasattr(self, "chapters") and chapter_idx < len(self.chapters):
                # 获取章节内容
                _, chapter_content = self.chapters[chapter_idx]
                
                # 显示章节内容
                self.original_text.delete(1.0, tk.END)
                self.original_text.insert(tk.END, chapter_content)
                
                # 记录当前选中的章节索引
                self.current_chapter_idx = chapter_idx
                
                # 检查是否有已生成的摘要
                base_name = os.path.splitext(self.current_file_path)[0]
                summary_file = f"{base_name}_sum.json"
                
                if os.path.exists(summary_file):
                    try:
                        with open(summary_file, 'r', encoding='utf-8') as f:
                            saved_summaries = json.load(f)
                            
                        # 获取当前章节的摘要
                        if "chapters" in saved_summaries and chapter_idx < len(saved_summaries["chapters"]):
                            chapter_summary = saved_summaries["chapters"][chapter_idx]["summary"]
                            
                            # 显示已保存的摘要
                            self.summary_text.delete(1.0, tk.END)
                            self.summary_text.insert(tk.END, chapter_summary)
                            
                            self.update_status(f"已加载章节 '{chapter_title}' 的保存摘要")
                        else:
                            # 清空摘要区域
                            self.summary_text.delete(1.0, tk.END)
                    except Exception as e:
                        logger.error(f"加载摘要文件失败: {str(e)}")
                else:
                    # 清空摘要区域
                    self.summary_text.delete(1.0, tk.END)
                
                self.update_status(f"已选择章节: {chapter_title}")
                
        except Exception as e:
            logger.error(f"选择章节时出错: {str(e)}")
    
    def load_model(self, model_type, model_path=None):
        """加载模型"""
        try:
            self.update_status(f"正在加载模型: {model_type}")
            
            # 创建进度回调
            def progress_callback(current, total=100, message=""):
                self.update_progress(current, message)
            
            # 设置API密钥（如果有）
            api_key = self.settings.get("api_key")
            
            # 加载模型
            from titan_summarizer import TitanSummarizer
            
            # 关闭现有的摘要器
            if self.summarizer:
                # 没有实际的关闭方法，但确保引用被释放
                self.summarizer = None
            
            # 创建新的摘要器
            self.summarizer = TitanSummarizer(
                model_type=model_type,
                model_path=model_path or self.settings.get("default_local_model"),
                api_key=api_key,
                mock_mode=False,
                max_tokens=8000,
                progress_callback=progress_callback
            )
            
            # 更新状态
            self.update_status(f"模型加载完成: {model_type}")
            self.update_progress(100, "模型就绪")
            
            # 保存设置
            self.settings["default_model"] = model_type
            if model_path:
                self.settings["default_local_model"] = model_path
            
        except Exception as e:
            logger.error(f"加载模型失败: {str(e)}")
            messagebox.showerror("模型错误", f"加载模型失败: {str(e)}")
            self.update_status("模型加载失败")
    
    def browse_model(self):
        """浏览选择本地模型文件"""
        file_path = filedialog.askopenfilename(
            title="选择本地模型文件",
            filetypes=[
                ("GGUF模型", "*.gguf"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            # 更新设置
            self.settings["default_local_model"] = file_path
            messagebox.showinfo("模型选择", f"已选择模型文件: {os.path.basename(file_path)}")
            
            # 如果当前使用的是本地模型，则重新加载
            if self.model_var.get() == "Ollama本地模型":
                self.load_model("ollama-local")
    
    def set_api_key(self):
        """设置API密钥"""
        # 获取当前API密钥
        current_key = self.settings.get("api_key", "")
        
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("设置API密钥")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 创建框架
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 添加标签和输入框
        ttk.Label(frame, text="请输入API密钥:").pack(anchor=tk.W, pady=(0, 5))
        
        key_var = tk.StringVar(value=current_key)
        key_entry = ttk.Entry(frame, textvariable=key_var, width=50)
        key_entry.pack(fill=tk.X, pady=5)
        
        # 创建按钮
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        def save_key():
            new_key = key_var.get().strip()
            self.settings["api_key"] = new_key
            messagebox.showinfo("API密钥", "API密钥已保存")
            dialog.destroy()
            
            # 如果当前使用的是API模型，则重新加载
            if self.model_var.get() == "DeepSeek在线API":
                self.load_model("deepseek-api")
        
        ttk.Button(button_frame, text="保存", command=save_key).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def save_as_default(self):
        """保存当前设置为默认设置"""
        # 保存当前摘要长度
        try:
            length = int(self.summary_length_var.get())
            self.settings["default_length"] = length
        except ValueError:
            pass
        
        # 保存当前模型类型
        model_name = self.model_var.get()
        if model_name == "DeepSeek在线API":
            self.settings["default_model"] = "deepseek-api"
        elif model_name == "Ollama本地模型":
            self.settings["default_model"] = "ollama-local"
        
        # 保存设置
        self.save_settings()
        messagebox.showinfo("设置", "当前设置已保存为默认设置")
    
    def generate_summary(self):
        """生成摘要"""
        # 检查是否正在生成
        if self.generating:
            # 如果正在生成，则停止
            self.generating = False
            self.generate_button.config(text="生成摘要")
            self.update_status("已停止生成")
            return
            
        # 检查是否已加载文件
        if not self.current_file_path:
            messagebox.showwarning("提示", "请先选择要摘要的文件")
            return
            
        # 检查是否已加载模型（如果选择生成式摘要）
        if self.summary_mode_var.get() == "生成式" and not self.summarizer:
            messagebox.showwarning("提示", "请先加载模型")
            return
            
        # 获取摘要长度
        try:
            max_length = int(self.summary_length_var.get())
        except ValueError:
            max_length = 500
            self.summary_length_var.set("500")
            
        # 添加任务到队列
        self.summarize_queue.put({
            "type": "single_file",
            "file_path": self.current_file_path,
            "mode": self.summary_mode_var.get(),
            "max_length": max_length
        })
        
        self.update_status("已添加摘要任务到队列")
    
    def batch_process(self):
        """批量处理文件"""
        # 检查是否正在生成
        if self.generating:
            # 如果正在生成，则停止
            self.generating = False
            self.batch_button.config(text="批量处理")
            self.update_status("已停止批量处理")
            return
            
        # 检查是否已加载目录
        if not hasattr(self, "current_directory"):
            messagebox.showwarning("提示", "请先选择要处理的目录")
            return
            
        # 检查是否已加载模型（如果选择生成式摘要）
        if self.summary_mode_var.get() == "生成式" and not self.summarizer:
            messagebox.showwarning("提示", "请先加载模型")
            return
            
        # 获取摘要长度
        try:
            max_length = int(self.summary_length_var.get())
        except ValueError:
            max_length = 500
            self.summary_length_var.set("500")
            
        # 添加任务到队列
        self.summarize_queue.put({
            "type": "batch",
            "directory": self.current_directory,
            "mode": self.summary_mode_var.get(),
            "max_length": max_length,
            "recursive": True
        })
        
        self.update_status("已添加批量处理任务到队列")
    
    def save_summary(self):
        """保存摘要到文件"""
        # 获取摘要内容
        summary = self.summary_text.get(1.0, tk.END).strip()
        
        if not summary:
            messagebox.showwarning("提示", "没有可保存的摘要内容")
            return
            
        # 打开保存对话框
        file_path = filedialog.asksaveasfilename(
            title="保存摘要",
            defaultextension=".md",
            filetypes=[
                ("Markdown文件", "*.md"),
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            try:
                # 保存文件
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(summary)
                    
                self.update_status(f"摘要已保存到: {file_path}")
                
                # 询问是否打开文件
                if messagebox.askyesno("文件已保存", "摘要已保存，是否打开文件？"):
                    self.open_file_with_default_app(file_path)
                    
            except Exception as e:
                logger.error(f"保存摘要失败: {str(e)}")
                messagebox.showerror("保存错误", f"无法保存摘要: {str(e)}")
    
    def open_file_with_default_app(self, file_path):
        """使用默认应用打开文件"""
        try:
            import os
            import platform
            import subprocess
            
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(('open', file_path))
            else:  # Linux
                subprocess.call(('xdg-open', file_path))
                
        except Exception as e:
            logger.error(f"打开文件失败: {str(e)}")
    
    def open_folder(self, folder_path):
        """打开文件夹"""
        try:
            import os
            import platform
            import subprocess
            
            if platform.system() == 'Windows':
                os.startfile(folder_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(('open', folder_path))
            else:  # Linux
                subprocess.call(('xdg-open', folder_path))
                
        except Exception as e:
            logger.error(f"打开文件夹失败: {str(e)}")


def main():
    """主函数"""
    root = tk.Tk()
    app = TitanUI(root)
    root.mainloop()


if __name__ == "__main__":
    main() 