#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TitanSummarizer Transformer UI - 基于Transformer的小说摘要生成器图形界面
允许用户选择小说文件并显示日志和分章节的摘要总结
"""

import os
import sys
import time
import re
import json
import logging
import torch
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QFileDialog, QTextEdit, QComboBox, 
                            QSpinBox, QDoubleSpinBox, QProgressBar, QTabWidget, 
                            QSplitter, QTreeWidget, QTreeWidgetItem, QMessageBox,
                            QCheckBox, QGroupBox, QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon, QTextCursor

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
                max_summary_length=150, device=None):
        super().__init__()
        self.file_path = file_path
        self.model_name = model_name
        self.by_chapter = by_chapter
        self.max_summary_length = max_summary_length
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        
    def run(self):
        try:
            self.update_signal.emit(f"开始处理文件: {self.file_path}")
            self.progress_signal.emit(5)
            
            # 读取文件
            self.update_signal.emit("正在读取文件...")
            content = read_file(self.file_path)
            self.update_signal.emit(f"文件读取完成，总长度: {len(content)} 字符")
            self.progress_signal.emit(10)
            
            # 加载模型
            self.update_signal.emit(f"正在加载模型: {self.model_name}...")
            model, tokenizer, device, max_length = load_model(self.model_name, self.device)
            self.update_signal.emit(f"模型加载完成，使用设备: {device}")
            self.progress_signal.emit(20)
            
            # 生成摘要
            start_time = time.time()
            
            if self.by_chapter:
                self.update_signal.emit("按章节生成摘要...")
                result = summarize_by_chapter(
                    content, 
                    model, 
                    tokenizer, 
                    device, 
                    max_length,
                    max_summary_length=self.max_summary_length
                )
                
                # 发送章节信号
                for chapter in result["chapters"]:
                    self.chapter_signal.emit(chapter)
                    
            else:
                self.update_signal.emit("生成全文摘要...")
                result = summarize_full_text(
                    content, 
                    model, 
                    tokenizer, 
                    device, 
                    max_length,
                    max_summary_length=self.max_summary_length * 2
                )
                
                # 发送章节信号
                self.chapter_signal.emit(result["chapters"][0])
            
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
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.chapters_data = []
        
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
        self.model_combo.addItems(list(AVAILABLE_MODELS.keys()))
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        param_layout.addLayout(model_layout)
        
        # 摘要长度
        length_layout = QVBoxLayout()
        length_label = QLabel("摘要长度:")
        self.length_spin = QSpinBox()
        self.length_spin.setRange(50, 500)
        self.length_spin.setSingleStep(10)
        self.length_spin.setValue(150)
        length_layout.addWidget(length_label)
        length_layout.addWidget(self.length_spin)
        param_layout.addLayout(length_layout)
        
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
        param_layout.addWidget(self.start_button)
        
        main_layout.addLayout(param_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
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
        
        # 清空之前的结果
        self.log_text.clear()
        self.summary_text.clear()
        self.chapter_tree.clear()
        self.chapters_data = []
        
        # 禁用开始按钮
        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # 创建并启动线程
        self.thread = TransformerSummarizerThread(
            file_path, 
            model_name, 
            by_chapter, 
            max_summary_length,
            device
        )
        self.thread.update_signal.connect(self.update_log)
        self.thread.progress_signal.connect(self.update_progress)
        self.thread.chapter_signal.connect(self.add_chapter)
        self.thread.finished_signal.connect(self.summarization_finished)
        self.thread.start()
    
    def update_log(self, message):
        self.log_text.append(message)
        self.statusBar().showMessage(message)
        logger.info(message)
        
        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def add_chapter(self, chapter_data):
        # 添加到章节数据
        self.chapters_data.append(chapter_data)
        
        # 添加到章节树
        item = QTreeWidgetItem(self.chapter_tree)
        item.setText(0, chapter_data["title"])
        item.setData(0, Qt.UserRole, len(self.chapters_data) - 1)  # 存储索引
        self.chapter_tree.addTopLevelItem(item)
    
    def on_chapter_selected(self, item, column):
        # 获取章节索引
        index = item.data(0, Qt.UserRole)
        if index is not None and 0 <= index < len(self.chapters_data):
            chapter = self.chapters_data[index]
            
            # 显示摘要
            self.summary_text.setText(chapter["summary"])
            
            # 切换到摘要选项卡
            self.tab_widget.setCurrentIndex(1)
    
    def summarization_finished(self, result):
        # 启用开始按钮
        self.start_button.setEnabled(True)
        
        # 如果没有章节被选中，显示全文摘要
        if self.chapter_tree.topLevelItemCount() > 0:
            self.chapter_tree.topLevelItem(0).setSelected(True)
            self.on_chapter_selected(self.chapter_tree.topLevelItem(0), 0)
        
        # 更新状态栏
        self.statusBar().showMessage(f"摘要生成完成，已保存到: {result['output_path']}")

def main():
    app = QApplication(sys.argv)
    window = TransformerSummarizerUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 