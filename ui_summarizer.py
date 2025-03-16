#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TitanSummarizer UI - 小说摘要生成器图形界面
允许用户选择小说文件并显示日志和分章节的摘要总结
"""

import os
import sys
import time
import logging
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QFileDialog, QTextEdit, QComboBox, 
                            QSpinBox, QDoubleSpinBox, QProgressBar, QTabWidget, 
                            QSplitter, QTreeWidget, QTreeWidgetItem, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon

# 导入摘要器模块
try:
    from titan_summarizer import logger as titan_logger
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples"))
    from simple_chinese_summarizer import textrank_summarize, extract_keywords, read_file
    SUMMARIZER_AVAILABLE = True
except ImportError as e:
    SUMMARIZER_AVAILABLE = False
    print(f"导入摘要器模块失败: {e}")

# 配置日志
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"ui_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TitanSummarizerUI")

# 摘要生成线程
class SummarizerThread(QThread):
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, file_path, ratio=0.05, algorithm="textrank"):
        super().__init__()
        self.file_path = file_path
        self.ratio = ratio
        self.algorithm = algorithm
        
    def run(self):
        try:
            self.update_signal.emit(f"开始处理文件: {self.file_path}")
            self.progress_signal.emit(10)
            
            # 读取文件
            self.update_signal.emit("正在读取文件...")
            content = read_file(self.file_path)
            self.update_signal.emit(f"文件读取完成，总长度: {len(content)} 字符")
            self.progress_signal.emit(30)
            
            # 提取关键词
            self.update_signal.emit("正在提取关键词...")
            keywords = extract_keywords(content, top_n=20)
            self.update_signal.emit(f"关键词: {', '.join(keywords)}")
            self.progress_signal.emit(50)
            
            # 生成摘要
            self.update_signal.emit(f"使用 {self.algorithm} 算法生成摘要，比例: {self.ratio}...")
            start_time = time.time()
            
            summary = textrank_summarize(
                content, 
                ratio=self.ratio, 
                use_textrank=(self.algorithm == "textrank")
            )
            
            elapsed_time = time.time() - start_time
            self.progress_signal.emit(90)
            
            # 生成结果信息
            self.update_signal.emit(f"摘要生成完成!")
            self.update_signal.emit(f"摘要长度: {len(summary)} 字符")
            self.update_signal.emit(f"压缩比: {len(summary) / len(content):.2%}")
            self.update_signal.emit(f"耗时: {elapsed_time:.2f} 秒")
            self.update_signal.emit(f"处理速度: {len(content) / elapsed_time:.2f} 字符/秒")
            
            # 保存摘要
            output_path = os.path.join(os.path.dirname(self.file_path), 
                                      f"{os.path.basename(self.file_path)}_summary_{self.algorithm}.txt")
            
            with open(output_path, 'w', encoding='utf-8-sig') as f:
                f.write(summary)
            
            self.update_signal.emit(f"摘要已保存到: {output_path}")
            self.progress_signal.emit(100)
            
            # 发送完成信号
            result = {
                "summary": summary,
                "keywords": keywords,
                "output_path": output_path,
                "stats": {
                    "original_length": len(content),
                    "summary_length": len(summary),
                    "compression_ratio": len(summary) / len(content),
                    "elapsed_time": elapsed_time
                }
            }
            self.finished_signal.emit(result)
            
        except Exception as e:
            self.update_signal.emit(f"错误: {str(e)}")
            logger.error(f"摘要生成失败: {str(e)}", exc_info=True)

# 主窗口
class TitanSummarizerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("TitanSummarizer - 小说摘要生成器")
        self.setMinimumSize(900, 700)
        
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
        
        # 算法选择
        algo_layout = QVBoxLayout()
        algo_label = QLabel("摘要算法:")
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["textrank", "tfidf"])
        algo_layout.addWidget(algo_label)
        algo_layout.addWidget(self.algo_combo)
        param_layout.addLayout(algo_layout)
        
        # 摘要比例
        ratio_layout = QVBoxLayout()
        ratio_label = QLabel("摘要比例:")
        self.ratio_spin = QDoubleSpinBox()
        self.ratio_spin.setRange(0.01, 0.5)
        self.ratio_spin.setSingleStep(0.01)
        self.ratio_spin.setValue(0.05)
        self.ratio_spin.setDecimals(2)
        ratio_layout.addWidget(ratio_label)
        ratio_layout.addWidget(self.ratio_spin)
        param_layout.addLayout(ratio_layout)
        
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
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        
        # 日志选项卡
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.tab_widget.addTab(self.log_text, "处理日志")
        
        # 摘要选项卡
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.tab_widget.addTab(self.summary_text, "摘要结果")
        
        # 关键词选项卡
        self.keywords_text = QTextEdit()
        self.keywords_text.setReadOnly(True)
        self.tab_widget.addTab(self.keywords_text, "关键词")
        
        main_layout.addWidget(self.tab_widget)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 检查依赖
        if not SUMMARIZER_AVAILABLE:
            QMessageBox.warning(self, "依赖错误", "无法导入摘要器模块，请确保已安装所有依赖。")
            self.start_button.setEnabled(False)
    
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
        algorithm = self.algo_combo.currentText()
        ratio = self.ratio_spin.value()
        
        # 清空之前的结果
        self.log_text.clear()
        self.summary_text.clear()
        self.keywords_text.clear()
        
        # 禁用开始按钮
        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # 创建并启动线程
        self.thread = SummarizerThread(file_path, ratio, algorithm)
        self.thread.update_signal.connect(self.update_log)
        self.thread.progress_signal.connect(self.update_progress)
        self.thread.finished_signal.connect(self.summarization_finished)
        self.thread.start()
    
    def update_log(self, message):
        self.log_text.append(message)
        self.statusBar().showMessage(message)
        logger.info(message)
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def summarization_finished(self, result):
        # 启用开始按钮
        self.start_button.setEnabled(True)
        
        # 显示摘要
        self.summary_text.setText(result["summary"])
        
        # 显示关键词
        self.keywords_text.setText(", ".join(result["keywords"]))
        
        # 更新状态栏
        self.statusBar().showMessage(f"摘要生成完成，已保存到: {result['output_path']}")
        
        # 切换到摘要选项卡
        self.tab_widget.setCurrentIndex(1)

def main():
    app = QApplication(sys.argv)
    window = TitanSummarizerUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 