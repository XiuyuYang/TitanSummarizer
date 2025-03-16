#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TitanSummarizer Transformer UI - 基于Transformer的小说摘要生成器图形界面
允许用户选择小说文件并显示日志和分章节的摘要总结
"""

import sys
import os
import logging
import re
import time
import torch
from datetime import datetime
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QFileDialog, QTextEdit, QComboBox, 
                            QSpinBox, QDoubleSpinBox, QProgressBar, QTabWidget, 
                            QSplitter, QTreeWidget, QTreeWidgetItem, QMessageBox,
                            QCheckBox, QGroupBox, QRadioButton, QButtonGroup, QSplashScreen,
                            QDialog, QProgressDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QMutex, QWaitCondition
from PyQt5.QtGui import QFont, QIcon, QTextCursor, QPixmap

# 导入摘要器模块
try:
    # 添加当前目录到路径
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from transformer_summarizer import (
        load_model, detect_chapters, summarize_by_chapter, 
        summarize_full_text, read_file, AVAILABLE_MODELS
    )
    SUMMARIZER_AVAILABLE = True
except ImportError as e:
    SUMMARIZER_AVAILABLE = False
    print(f"导入Transformer摘要器模块失败: {e}")

# 配置日志
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"transformer_ui_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TransformerSummarizerUI")

# 摘要生成线程
class TransformerSummarizerThread(QThread):
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    chapter_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, file_path, model_name="bart-base-chinese", by_chapter=True, 
                max_summary_length=150, device=None, advanced_params=None):
        super().__init__()
        self.file_path = file_path
        self.model_name = model_name
        self.by_chapter = by_chapter
        self.max_summary_length = max_summary_length
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        self.advanced_params = advanced_params or {}  # 添加高级参数
        self.paused = False
        self.stopped = False  # 添加停止标志
        self.mutex = QMutex()  # 用于线程同步
        self.pause_condition = QWaitCondition()  # 用于暂停/恢复
        
    def pause(self):
        """暂停线程"""
        self.mutex.lock()
        self.paused = True
        self.mutex.unlock()
        self.update_signal.emit("摘要生成已暂停")
        
    def resume(self):
        """恢复线程"""
        self.mutex.lock()
        self.paused = False
        self.pause_condition.wakeAll()  # 唤醒所有等待的线程
        self.mutex.unlock()
        self.update_signal.emit("摘要生成已恢复")
        
    def stop(self):
        """停止线程"""
        self.mutex.lock()
        self.stopped = True
        self.paused = False  # 如果正在暂停，也需要恢复以便能够停止
        self.pause_condition.wakeAll()  # 唤醒所有等待的线程
        self.mutex.unlock()
        self.update_signal.emit("摘要生成已停止")
        
    def is_paused(self):
        """检查是否暂停"""
        return self.paused
        
    def is_stopped(self):
        """检查是否停止"""
        return self.stopped
        
    def run(self):
        try:
            self.update_signal.emit(f"开始处理文件: {self.file_path}")
            self.progress_signal.emit(5)
            
            # 读取文件
            self.update_signal.emit("正在读取文件...")
            content = read_file(self.file_path)
            self.update_signal.emit(f"文件读取完成，总长度: {len(content)} 字符")
            self.progress_signal.emit(10)
            
            # 检查暂停和停止状态
            self.mutex.lock()
            if self.stopped:
                self.mutex.unlock()
                self.update_signal.emit("处理已停止")
                return
            if self.paused:
                self.pause_condition.wait(self.mutex)
            self.mutex.unlock()
            
            # 加载模型
            try:
                self.update_signal.emit(f"正在加载模型: {self.model_name}...")
                
                # 更新进度 - 模型加载过程
                self.progress_signal.emit(12)
                self.update_signal.emit("正在初始化分词器...")
                
                # 加载模型 - 分步骤更新进度
                model, tokenizer, device, max_length = load_model(self.model_name, self.device)
                
                self.progress_signal.emit(18)
                self.update_signal.emit(f"模型加载完成，使用设备: {device}")
            except ImportError as e:
                self.update_signal.emit(f"错误: 缺少必要的依赖库 - {str(e)}")
                self.update_signal.emit("请安装缺少的依赖: pip install sentencepiece protobuf")
                return
            except Exception as e:
                self.update_signal.emit(f"错误: 模型加载失败 - {str(e)}")
                return
                
            self.progress_signal.emit(20)
            
            # 检查暂停和停止状态
            self.mutex.lock()
            if self.stopped:
                self.mutex.unlock()
                self.update_signal.emit("处理已停止")
                return
            if self.paused:
                self.pause_condition.wait(self.mutex)
            self.mutex.unlock()
            
            # 生成摘要
            start_time = time.time()
            
            if self.by_chapter:
                self.update_signal.emit("按章节生成摘要...")
                
                # 定义章节回调函数
                def chapter_callback(chapter_info):
                    # 检查暂停和停止状态
                    self.mutex.lock()
                    if self.stopped:
                        self.mutex.unlock()
                        return False  # 返回False表示停止处理
                    if self.paused:
                        self.update_signal.emit("等待恢复...")
                        self.pause_condition.wait(self.mutex)
                        if self.stopped:  # 再次检查，因为可能在暂停时被停止
                            self.mutex.unlock()
                            return False
                        self.update_signal.emit("已恢复处理")
                    self.mutex.unlock()
                    
                    # 发送章节信号
                    self.chapter_signal.emit(chapter_info)
                    
                    # 更新进度条
                    progress = 20 + int(80 * (chapter_info["chapter_index"] + 1) / chapter_info["total_chapters"])
                    self.progress_signal.emit(progress)
                    
                    # 更新日志
                    self.update_signal.emit(
                        f"完成章节 {chapter_info['chapter_index']+1}/{chapter_info['total_chapters']}: "
                        f"{chapter_info['title']} (压缩比: {chapter_info['compression_ratio']:.2%})"
                    )
                    
                    return True  # 返回True表示继续处理
                
                # 使用回调函数处理章节
                result = summarize_by_chapter(
                    content, 
                    model, 
                    tokenizer, 
                    device, 
                    max_length,
                    max_summary_length=self.max_summary_length,
                    chapter_callback=chapter_callback,
                    advanced_params=self.advanced_params  # 传递高级参数
                )
                
                # 检查是否已停止
                if self.is_stopped():
                    self.update_signal.emit("处理已停止")
                    return
                
            else:
                self.update_signal.emit("生成全文摘要...")
                
                # 检查暂停和停止状态
                self.mutex.lock()
                if self.stopped:
                    self.mutex.unlock()
                    self.update_signal.emit("处理已停止")
                    return
                if self.paused:
                    self.update_signal.emit("等待恢复...")
                    self.pause_condition.wait(self.mutex)
                    if self.stopped:  # 再次检查，因为可能在暂停时被停止
                        self.mutex.unlock()
                        self.update_signal.emit("处理已停止")
                        return
                    self.update_signal.emit("已恢复处理")
                self.mutex.unlock()
                
                result = summarize_full_text(
                    content, 
                    model, 
                    tokenizer, 
                    device, 
                    max_length,
                    max_summary_length=self.max_summary_length * 2,
                    advanced_params=self.advanced_params  # 传递高级参数
                )
                
                # 检查是否已停止
                if self.is_stopped():
                    self.update_signal.emit("处理已停止")
                    return
                
                # 发送章节信号
                self.chapter_signal.emit(result["chapters"][0])
                self.progress_signal.emit(90)
            
            elapsed_time = time.time() - start_time
            
            # 生成结果信息
            self.update_signal.emit(f"摘要生成完成!")
            self.update_signal.emit(f"摘要长度: {len(result['full_summary'])} 字符")
            self.update_signal.emit(f"压缩比: {len(result['full_summary']) / len(content):.2%}")
            self.update_signal.emit(f"耗时: {elapsed_time:.2f} 秒")
            self.update_signal.emit(f"处理速度: {len(content) / elapsed_time:.2f} 字符/秒")
            
            # 保存摘要
            output_dir = os.path.join(os.path.dirname(self.file_path), "summaries")
            os.makedirs(output_dir, exist_ok=True)
            
            base_name = os.path.splitext(os.path.basename(self.file_path))[0]
            output_path = os.path.join(output_dir, f"{base_name}_transformer_summary.txt")
            
            with open(output_path, 'w', encoding='utf-8-sig') as f:
                f.write(result["full_summary"])
            
            # 保存详细结果
            detail_path = os.path.join(output_dir, f"{base_name}_transformer_summary_detail.json")
            with open(detail_path, 'w', encoding='utf-8-sig') as f:
                # 创建可序列化的结果
                serializable_result = {
                    "file_path": self.file_path,
                    "model": self.model_name,
                    "by_chapter": self.by_chapter,
                    "chapters": [
                        {
                            "title": ch["title"],
                            "original_length": ch["original_length"],
                            "summary_length": ch["summary_length"],
                            "summary": ch["summary"]
                        } for ch in result["chapters"]
                    ],
                    "elapsed_time": elapsed_time,
                    "compression_ratio": len(result["full_summary"]) / len(content)
                }
                json.dump(serializable_result, f, ensure_ascii=False, indent=2)
            
            self.update_signal.emit(f"摘要已保存到: {output_path}")
            self.update_signal.emit(f"详细结果已保存到: {detail_path}")
            self.progress_signal.emit(100)
            
            # 发送完成信号
            result["output_path"] = output_path
            result["detail_path"] = detail_path
            self.finished_signal.emit(result)
            
        except Exception as e:
            self.update_signal.emit(f"错误: {str(e)}")
            logger.error(f"摘要生成失败: {str(e)}", exc_info=True)

# 主窗口
class TransformerSummarizerUI(QMainWindow):
    """
    基于Transformer的文本摘要生成器UI
    """
    def __init__(self, update_progress=None):
        super().__init__()
        self.logger = logging.getLogger("TransformerSummarizerUI")
        self.summarizer_thread = None
        self.update_progress = update_progress
        # 设置窗口标志，确保不会自动显示
        self.setAttribute(Qt.WA_DontShowOnScreen, True)
        self.init_ui()
        self.chapters_data = []
        # 移除不显示标志，允许后续显示
        self.setAttribute(Qt.WA_DontShowOnScreen, False)
        
    def init_ui(self):
        self.setWindowTitle("TitanSummarizer Transformer - 基于深度学习的小说摘要生成器")
        self.setMinimumSize(1000, 800)
        
        # 主布局
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # 文件选择区域
        file_layout = QHBoxLayout()
        self.file_label = QLabel("小说文件:")
        self.file_path = QTextEdit()
        self.file_path.setMaximumHeight(30)
        self.file_path.setReadOnly(True)
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_file)
        
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.file_path)
        file_layout.addWidget(self.browse_button)
        main_layout.addLayout(file_layout)
        
        # 参数设置区域
        param_layout = QHBoxLayout()
        
        # 模型选择
        model_layout = QVBoxLayout()
        model_label = QLabel("预训练模型:")
        self.model_combo = QComboBox()
        
        # 检查模型依赖并添加可用模型
        self.available_models = []
        self.unavailable_models = {}  # 存储不可用模型的信息
        
        for model_name, model_info in AVAILABLE_MODELS.items():
            # 检查模型是否标记为不可用
            if model_info.get("available") is False:
                self.unavailable_models[model_name] = model_info.get("message", "此模型暂不可用")
                continue
                
            try:
                from transformer_summarizer import check_dependencies
                if check_dependencies(model_name):
                    self.available_models.append(model_name)
                else:
                    logger.warning(f"模型 {model_name} 缺少必要的依赖库，已禁用")
            except:
                # 如果check_dependencies不可用，添加所有未标记为不可用的模型
                self.available_models.append(model_name)
        
        # 添加可用模型
        self.model_combo.addItems(self.available_models)
        
        # 添加不可用模型（灰色显示）
        for model_name in self.unavailable_models.keys():
            index = self.model_combo.count()
            self.model_combo.addItem(f"{model_name} (暂不可用)")
            # 禁用该选项
            self.model_combo.model().item(index).setEnabled(False)
            # 设置工具提示
            self.model_combo.setItemData(index, self.unavailable_models[model_name], Qt.ToolTipRole)
        
        # 连接信号
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        param_layout.addLayout(model_layout)
        
        # 摘要长度
        length_layout = QVBoxLayout()
        length_label = QLabel("摘要长度:")
        self.length_spin = QSpinBox()
        self.length_spin.setRange(50, 1000)  # 增加最大值
        self.length_spin.setSingleStep(50)  # 增加步长
        self.length_spin.setValue(300)  # 增加默认值
        length_layout.addWidget(length_label)
        length_layout.addWidget(self.length_spin)
        
        # 添加摘要长度说明
        length_tip = QLabel("(每章节摘要的目标字符数，值越大摘要越详细)")
        length_tip.setStyleSheet("color: gray; font-size: 9pt;")
        length_layout.addWidget(length_tip)
        
        param_layout.addLayout(length_layout)
        
        # 添加高级参数设置区域
        self.advanced_group = QGroupBox("高级参数设置")
        self.advanced_group.setCheckable(True)
        self.advanced_group.setChecked(False)  # 默认不启用
        advanced_layout = QVBoxLayout()
        self.advanced_group.setLayout(advanced_layout)
        
        # 重复惩罚参数
        rep_penalty_layout = QHBoxLayout()
        rep_penalty_label = QLabel("重复惩罚:")
        self.rep_penalty_spin = QDoubleSpinBox()
        self.rep_penalty_spin.setRange(1.0, 5.0)
        self.rep_penalty_spin.setSingleStep(0.1)
        self.rep_penalty_spin.setValue(1.5)
        rep_penalty_layout.addWidget(rep_penalty_label)
        rep_penalty_layout.addWidget(self.rep_penalty_spin)
        advanced_layout.addLayout(rep_penalty_layout)
        
        # 采样温度参数
        temperature_layout = QHBoxLayout()
        temperature_label = QLabel("采样温度:")
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.1, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(1.0)
        temperature_layout.addWidget(temperature_label)
        temperature_layout.addWidget(self.temperature_spin)
        advanced_layout.addLayout(temperature_layout)
        
        # Top-p采样参数
        top_p_layout = QHBoxLayout()
        top_p_label = QLabel("Top-p采样:")
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.1, 1.0)
        self.top_p_spin.setSingleStep(0.05)
        self.top_p_spin.setValue(0.9)
        top_p_layout.addWidget(top_p_label)
        top_p_layout.addWidget(self.top_p_spin)
        advanced_layout.addLayout(top_p_layout)
        
        # 采样策略选择
        strategy_layout = QHBoxLayout()
        strategy_label = QLabel("生成策略:")
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["Beam Search", "采样", "贪婪"])
        self.strategy_combo.currentIndexChanged.connect(self.update_strategy_ui)
        strategy_layout.addWidget(strategy_label)
        strategy_layout.addWidget(self.strategy_combo)
        advanced_layout.addLayout(strategy_layout)
        
        # 添加高级参数说明
        advanced_tip = QLabel("(调整这些参数可以影响摘要的质量和多样性)")
        advanced_tip.setStyleSheet("color: gray; font-size: 9pt;")
        advanced_layout.addWidget(advanced_tip)
        
        # 添加高级参数区域到主布局（放在参数设置区域之后，进度条之前）
        main_layout.addWidget(self.advanced_group)
        
        # 摘要模式
        mode_group = QGroupBox("摘要模式")
        mode_layout = QVBoxLayout()
        self.chapter_mode = QRadioButton("按章节摘要")
        self.full_mode = QRadioButton("全文摘要")
        self.chapter_mode.setChecked(True)
        mode_layout.addWidget(self.chapter_mode)
        mode_layout.addWidget(self.full_mode)
        mode_group.setLayout(mode_layout)
        param_layout.addWidget(mode_group)
        
        # 设备选择
        device_layout = QVBoxLayout()
        device_label = QLabel("计算设备:")
        self.device_combo = QComboBox()
        self.device_combo.addItems(["自动选择", "CPU", "GPU"])
        if not torch.cuda.is_available():
            self.device_combo.setCurrentText("CPU")
            self.device_combo.model().item(2).setEnabled(False)
        device_layout.addWidget(device_label)
        device_layout.addWidget(self.device_combo)
        param_layout.addLayout(device_layout)
        
        # 开始按钮
        self.start_button = QPushButton("开始生成摘要")
        self.start_button.setMinimumHeight(50)
        self.start_button.clicked.connect(self.start_summarization)
        
        # 暂停/恢复按钮
        self.pause_button = QPushButton("暂停")
        self.pause_button.setMinimumHeight(50)
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setEnabled(False)  # 初始状态禁用
        
        # 停止按钮
        self.stop_button = QPushButton("停止")
        self.stop_button.setMinimumHeight(50)
        self.stop_button.clicked.connect(self.stop_summarization)
        self.stop_button.setEnabled(False)  # 初始状态禁用
        
        # 按钮布局
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.start_button)
        
        # 创建水平布局用于暂停和停止按钮
        pause_stop_layout = QHBoxLayout()
        pause_stop_layout.addWidget(self.pause_button)
        pause_stop_layout.addWidget(self.stop_button)
        button_layout.addLayout(pause_stop_layout)
        
        param_layout.addLayout(button_layout)
        
        main_layout.addLayout(param_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setFormat("就绪 %p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid grey;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 10px;
                margin: 0.5px;
            }
        """)
        self.progress_bar.setMinimumHeight(25)
        main_layout.addWidget(self.progress_bar)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧章节树
        self.chapter_tree = QTreeWidget()
        self.chapter_tree.setHeaderLabels(["章节"])
        self.chapter_tree.setMinimumWidth(200)
        self.chapter_tree.itemClicked.connect(self.on_chapter_selected)
        
        # 右侧选项卡
        self.tab_widget = QTabWidget()
        
        # 日志选项卡
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.tab_widget.addTab(self.log_text, "处理日志")
        
        # 摘要选项卡
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.tab_widget.addTab(self.summary_text, "摘要结果")
        
        # 添加到分割器
        splitter.addWidget(self.chapter_tree)
        splitter.addWidget(self.tab_widget)
        splitter.setSizes([200, 800])
        
        main_layout.addWidget(splitter)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 检查依赖
        if not SUMMARIZER_AVAILABLE:
            QMessageBox.warning(self, "依赖错误", "无法导入Transformer摘要器模块，请确保已安装所有依赖。")
            self.start_button.setEnabled(False)
            
        # 检查PyTorch和CUDA
        if torch.cuda.is_available():
            self.log_text.append(f"检测到CUDA: {torch.cuda.get_device_name(0)}")
            self.log_text.append(f"CUDA版本: {torch.version.cuda}")
        else:
            self.log_text.append("未检测到CUDA，将使用CPU进行计算（速度较慢）")
            self.log_text.append("建议安装支持CUDA的PyTorch版本以加速处理")
            
        # 默认加载凡人修仙传 - 移到这里，确保log_text已创建
        default_novel_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "novels", "凡人修仙传_完整版.txt")
        if os.path.exists(default_novel_path):
            self.file_path.setText(default_novel_path)
            self.log_text.append(f"已默认加载小说: {default_novel_path}")
            
        # 初始化UI状态
        self.update_strategy_ui()
    
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择小说文件", "", "文本文件 (*.txt);;所有文件 (*.*)"
        )
        if file_path:
            self.file_path.setText(file_path)
            self.log_text.append(f"已选择文件: {file_path}")
    
    def start_summarization(self):
        file_path = self.file_path.toPlainText()
        if not file_path:
            QMessageBox.warning(self, "错误", "请先选择小说文件")
            return
        
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "错误", f"文件不存在: {file_path}")
            return
        
        # 获取参数
        model_name = self.model_combo.currentText()
        max_summary_length = self.length_spin.value()
        by_chapter = self.chapter_mode.isChecked()
        
        # 设置设备
        device = None
        device_selection = self.device_combo.currentText()
        if device_selection == "CPU":
            device = "cpu"
        elif device_selection == "GPU" and torch.cuda.is_available():
            device = "cuda"
        
        # 获取高级参数
        advanced_params = {}
        if hasattr(self, 'advanced_group') and self.advanced_group.isChecked():
            # 重复惩罚
            advanced_params['repetition_penalty'] = self.rep_penalty_spin.value()
            
            # 采样温度
            advanced_params['temperature'] = self.temperature_spin.value()
            
            # Top-p采样
            advanced_params['top_p'] = self.top_p_spin.value()
            
            # 生成策略
            strategy = self.strategy_combo.currentText()
            if strategy == "Beam Search":
                advanced_params['do_sample'] = False
                advanced_params['num_beams'] = 5
                # 移除采样相关参数，避免冲突
                if 'temperature' in advanced_params:
                    del advanced_params['temperature']
                if 'top_p' in advanced_params:
                    del advanced_params['top_p']
            elif strategy == "采样":
                advanced_params['do_sample'] = True
                advanced_params['num_beams'] = 1
            elif strategy == "贪婪":
                advanced_params['do_sample'] = False
                advanced_params['num_beams'] = 1
                # 移除采样相关参数，避免冲突
                if 'temperature' in advanced_params:
                    del advanced_params['temperature']
                if 'top_p' in advanced_params:
                    del advanced_params['top_p']
            
            self.log_text.append(f"使用高级参数: {advanced_params}")
        
        # 清空之前的结果
        self.log_text.clear()
        self.summary_text.clear()
        self.chapter_tree.clear()
        self.chapters_data = []
        
        # 检查模型依赖
        try:
            from transformer_summarizer import check_dependencies
            if not check_dependencies(model_name):
                QMessageBox.critical(self, "依赖错误", 
                                    f"模型 {model_name} 缺少必要的依赖库，请安装后再试。\n"
                                    f"可能需要安装: sentencepiece 或 protobuf")
                return
        except ImportError:
            # 如果check_dependencies不可用，继续执行
            pass
        
        # 禁用开始按钮
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)
        
        # 创建并启动线程
        self.thread = TransformerSummarizerThread(
            file_path, 
            model_name, 
            by_chapter, 
            max_summary_length,
            device,
            advanced_params  # 传递高级参数
        )
        
        # 连接信号
        self.thread.update_signal.connect(self.update_log)
        
        # 确保self.update_progress是一个方法而不是None
        if hasattr(self, 'update_progress') and callable(self.update_progress):
            self.thread.progress_signal.connect(self.update_progress)
        
        self.thread.chapter_signal.connect(self.add_chapter)
        self.thread.finished_signal.connect(self.summarization_finished)
        
        # 启动线程
        self.thread.start()
    
    def update_log(self, message):
        # 添加时间戳
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # 根据消息类型设置不同的样式
        if "错误" in message or "失败" in message:
            formatted_message = f'<span style="color:red;">{formatted_message}</span>'
        elif "完成" in message or "成功" in message:
            formatted_message = f'<span style="color:green;">{formatted_message}</span>'
        elif "加载" in message or "初始化" in message:
            formatted_message = f'<span style="color:blue;">{formatted_message}</span>'
        
        # 添加到日志
        self.log_text.append(formatted_message)
        self.statusBar().showMessage(message)
        logger.info(message)
        
        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
        
        # 强制更新UI
        QApplication.processEvents()
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
        
        # 更新进度条文本
        if value < 20:
            self.progress_bar.setFormat("加载模型中... %p%")
        elif value < 50:
            self.progress_bar.setFormat("处理文本中... %p%")
        elif value < 90:
            self.progress_bar.setFormat("生成摘要中... %p%")
        else:
            self.progress_bar.setFormat("即将完成... %p%")
        
        # 强制更新UI
        QApplication.processEvents()
    
    def add_chapter(self, chapter_data):
        # 添加到章节数据
        self.chapters_data.append(chapter_data)
        
        # 添加到章节树
        item = QTreeWidgetItem(self.chapter_tree)
        item.setText(0, chapter_data["title"])
        item.setData(0, Qt.UserRole, len(self.chapters_data) - 1)  # 存储索引
        self.chapter_tree.addTopLevelItem(item)
        
        # 自动选中并显示最新添加的章节
        self.chapter_tree.setCurrentItem(item)
        self.on_chapter_selected(item, 0)
        
        # 确保章节树滚动到最新项
        self.chapter_tree.scrollToItem(item)
    
    def on_chapter_selected(self, item, column):
        # 获取章节索引
        index = item.data(0, Qt.UserRole)
        if index is not None and 0 <= index < len(self.chapters_data):
            chapter = self.chapters_data[index]
            
            # 显示摘要
            self.summary_text.setText(chapter["summary"])
            
            # 切换到摘要选项卡
            self.tab_widget.setCurrentIndex(1)
    
    def summarization_finished(self, result=None):
        """摘要生成完成后的处理"""
        # 启用开始按钮，禁用暂停和停止按钮
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.pause_button.setText("暂停")  # 重置暂停按钮文本
        
        # 如果没有章节被选中，显示全文摘要
        if self.chapter_tree.topLevelItemCount() > 0:
            self.chapter_tree.topLevelItem(0).setSelected(True)
            self.on_chapter_selected(self.chapter_tree.topLevelItem(0), 0)
        
        # 根据线程状态更新状态栏
        if self.thread and self.thread.is_stopped():
            self.statusBar().showMessage("摘要生成已停止")
            self.update_log("摘要生成已停止")
        elif result and 'output_path' in result:
            self.statusBar().showMessage(f"摘要生成完成，已保存到: {result['output_path']}")
            self.update_log("摘要生成已完成")
        else:
            self.statusBar().showMessage("摘要生成已完成")
            self.update_log("摘要生成已完成")
        
        # 确保线程正确清理
        if self.thread:
            try:
                # 等待线程完成
                if self.thread.isRunning():
                    self.thread.wait(1000)  # 最多等待1秒
                
                # 断开所有信号连接
                try:
                    self.thread.update_signal.disconnect()
                    self.thread.progress_signal.disconnect()
                    self.thread.chapter_signal.disconnect()
                    self.thread.finished_signal.disconnect()
                except:
                    # 忽略断开连接时可能出现的错误
                    pass
                    
                # 确保线程被正确删除
                self.thread.deleteLater()
                self.thread = None
            except:
                # 忽略清理时可能出现的错误
                self.thread = None

    def toggle_pause(self):
        if self.thread.is_paused():
            self.thread.resume()
            self.pause_button.setText("暂停")
        else:
            self.thread.pause()
            self.pause_button.setText("恢复")

    def stop_summarization(self):
        """停止摘要生成过程"""
        if self.thread and self.thread.isRunning():
            self.update_log("正在停止摘要生成...")
            self.thread.stop()
            # 立即启用开始按钮，不等待线程结束
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.pause_button.setText("暂停")  # 重置暂停按钮文本
            # 不需要等待线程结束，线程会自行发出finished信号
            # 按钮状态将在summarization_finished中更新

    def update_strategy_ui(self):
        """根据选择的生成策略更新UI"""
        strategy = self.strategy_combo.currentText()
        
        # 启用或禁用温度和top_p参数
        enable_sampling_params = (strategy == "采样")
        self.temperature_spin.setEnabled(enable_sampling_params)
        self.top_p_spin.setEnabled(enable_sampling_params)
        
        # 更新参数说明
        if strategy == "Beam Search":
            self.advanced_group.setToolTip("Beam Search策略使用多个候选序列，生成更稳定的摘要")
        elif strategy == "采样":
            self.advanced_group.setToolTip("采样策略使用温度和top_p参数控制生成的多样性，生成更有创意的摘要")
        elif strategy == "贪婪":
            self.advanced_group.setToolTip("贪婪策略每次选择概率最高的词，生成确定性的摘要")

    def on_model_changed(self):
        # 当模型选择发生变化时，更新UI
        self.update_strategy_ui()

def main():
    # 记录开始时间
    start_time = time.time()
    
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    # 预先处理事件，确保Qt系统已初始化
    app.processEvents()
    
    # 创建主窗口 - 不使用进度更新回调
    window = TransformerSummarizerUI(update_progress=None)
    
    # 显示主窗口
    window.show()
    window.raise_()
    window.activateWindow()
    
    # 计算并显示启动时间
    elapsed_time = time.time() - start_time
    window.log_text.append(f"<span style='color:blue; font-weight:bold;'>程序启动耗时: {elapsed_time:.2f} 秒</span>")
    
    # 强制更新UI，确保启动时间显示
    app.processEvents()
    
    # 将启动时间信息添加到日志
    logger.info(f"程序启动耗时: {elapsed_time:.2f} 秒")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 