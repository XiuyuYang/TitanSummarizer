#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TitanSummarizer 增强版UI - 小说摘要生成器图形界面
允许用户选择小说文件并显示日志和分章节的摘要总结
"""

import os
import sys
import time
import re
import logging
import json
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
log_file = os.path.join(log_dir, f"ui_enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TitanSummarizerEnhancedUI")

# 章节检测和分割函数
def detect_chapters(text):
    """检测小说章节"""
    # 常见的章节标题模式
    patterns = [
        r'第[零一二三四五六七八九十百千万亿\d]+章\s*[^\n]*',  # 第X章 标题
        r'第[零一二三四五六七八九十百千万亿\d]+节\s*[^\n]*',  # 第X节 标题
        r'Chapter\s+\d+\s*[^\n]*',  # Chapter X 标题
        r'\d+\.\s+[^\n]+',  # 数字编号. 标题
    ]
    
    # 合并模式
    combined_pattern = '|'.join(f'({p})' for p in patterns)
    
    # 查找所有匹配
    matches = list(re.finditer(combined_pattern, text))
    
    chapters = []
    for i, match in enumerate(matches):
        title = match.group(0).strip()
        start_pos = match.start()
        
        # 确定章节结束位置
        if i < len(matches) - 1:
            end_pos = matches[i+1].start()
        else:
            end_pos = len(text)
        
        chapters.append({
            'title': title,
            'start': start_pos,
            'end': end_pos,
            'content': text[start_pos:end_pos]
        })
    
    # 如果没有检测到章节，将整个文本作为一个章节
    if not chapters:
        chapters.append({
            'title': '全文',
            'start': 0,
            'end': len(text),
            'content': text
        })
    
    return chapters

# 摘要生成线程
class EnhancedSummarizerThread(QThread):
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    chapter_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, file_path, ratio=0.05, algorithm="textrank", by_chapter=True):
        super().__init__()
        self.file_path = file_path
        self.ratio = ratio
        self.algorithm = algorithm
        self.by_chapter = by_chapter
        
    def run(self):
        try:
            self.update_signal.emit(f"开始处理文件: {self.file_path}")
            self.progress_signal.emit(5)
            
            # 读取文件
            self.update_signal.emit("正在读取文件...")
            content = read_file(self.file_path)
            self.update_signal.emit(f"文件读取完成，总长度: {len(content)} 字符")
            self.progress_signal.emit(10)
            
            # 提取全文关键词
            self.update_signal.emit("正在提取全文关键词...")
            keywords = extract_keywords(content, top_n=20)
            self.update_signal.emit(f"全文关键词: {', '.join(keywords)}")
            self.progress_signal.emit(20)
            
            # 检测章节
            self.update_signal.emit("正在检测章节...")
            chapters = detect_chapters(content)
            self.update_signal.emit(f"检测到 {len(chapters)} 个章节")
            self.progress_signal.emit(30)
            
            # 创建结果字典
            result = {
                "file_path": self.file_path,
                "total_length": len(content),
                "keywords": keywords,
                "chapters": [],
                "full_summary": "",
                "stats": {
                    "original_length": len(content),
                    "summary_length": 0,
                    "compression_ratio": 0,
                    "elapsed_time": 0
                }
            }
            
            start_time = time.time()
            
            if self.by_chapter:
                # 按章节生成摘要
                self.update_signal.emit(f"使用 {self.algorithm} 算法按章节生成摘要，比例: {self.ratio}...")
                
                total_chapters = len(chapters)
                full_summary = []
                
                for i, chapter in enumerate(chapters):
                    chapter_title = chapter['title']
                    chapter_content = chapter['content']
                    
                    self.update_signal.emit(f"处理章节 {i+1}/{total_chapters}: {chapter_title}")
                    
                    # 生成章节摘要
                    chapter_summary = textrank_summarize(
                        chapter_content, 
                        ratio=self.ratio, 
                        use_textrank=(self.algorithm == "textrank")
                    )
                    
                    # 提取章节关键词
                    chapter_keywords = extract_keywords(chapter_content, top_n=10)
                    
                    # 添加到结果
                    chapter_result = {
                        "title": chapter_title,
                        "original_length": len(chapter_content),
                        "summary": chapter_summary,
                        "summary_length": len(chapter_summary),
                        "keywords": chapter_keywords
                    }
                    
                    result["chapters"].append(chapter_result)
                    full_summary.append(f"【{chapter_title}】\n\n{chapter_summary}\n\n")
                    
                    # 发送章节信号
                    self.chapter_signal.emit(chapter_result)
                    
                    # 更新进度
                    progress = 30 + int(60 * (i+1) / total_chapters)
                    self.progress_signal.emit(progress)
                
                # 合并所有章节摘要
                result["full_summary"] = "\n".join(full_summary)
                result["stats"]["summary_length"] = len(result["full_summary"])
                
            else:
                # 生成全文摘要
                self.update_signal.emit(f"使用 {self.algorithm} 算法生成全文摘要，比例: {self.ratio}...")
                
                full_summary = textrank_summarize(
                    content, 
                    ratio=self.ratio, 
                    use_textrank=(self.algorithm == "textrank")
                )
                
                result["full_summary"] = full_summary
                result["stats"]["summary_length"] = len(full_summary)
                
                # 添加到结果
                chapter_result = {
                    "title": "全文摘要",
                    "original_length": len(content),
                    "summary": full_summary,
                    "summary_length": len(full_summary),
                    "keywords": keywords
                }
                
                result["chapters"].append(chapter_result)
                
                # 发送章节信号
                self.chapter_signal.emit(chapter_result)
                self.progress_signal.emit(90)
            
            elapsed_time = time.time() - start_time
            result["stats"]["elapsed_time"] = elapsed_time
            result["stats"]["compression_ratio"] = result["stats"]["summary_length"] / result["stats"]["original_length"]
            
            # 生成结果信息
            self.update_signal.emit(f"摘要生成完成!")
            self.update_signal.emit(f"摘要长度: {result['stats']['summary_length']} 字符")
            self.update_signal.emit(f"压缩比: {result['stats']['compression_ratio']:.2%}")
            self.update_signal.emit(f"耗时: {elapsed_time:.2f} 秒")
            self.update_signal.emit(f"处理速度: {result['stats']['original_length'] / elapsed_time:.2f} 字符/秒")
            
            # 保存摘要
            output_dir = os.path.join(os.path.dirname(self.file_path), "summaries")
            os.makedirs(output_dir, exist_ok=True)
            
            base_name = os.path.splitext(os.path.basename(self.file_path))[0]
            output_path = os.path.join(output_dir, f"{base_name}_summary_{self.algorithm}.txt")
            
            with open(output_path, 'w', encoding='utf-8-sig') as f:
                f.write(result["full_summary"])
            
            # 保存详细结果
            detail_path = os.path.join(output_dir, f"{base_name}_summary_detail.json")
            with open(detail_path, 'w', encoding='utf-8-sig') as f:
                # 创建可序列化的结果
                serializable_result = {
                    "file_path": result["file_path"],
                    "total_length": result["total_length"],
                    "keywords": result["keywords"],
                    "chapters": [
                        {
                            "title": ch["title"],
                            "original_length": ch["original_length"],
                            "summary_length": ch["summary_length"],
                            "keywords": ch["keywords"]
                        } for ch in result["chapters"]
                    ],
                    "stats": result["stats"]
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
class TitanSummarizerEnhancedUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.chapters_data = []
        
    def init_ui(self):
        self.setWindowTitle("TitanSummarizer 增强版 - 小说摘要生成器")
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
        
        # 关键词选项卡
        self.keywords_text = QTextEdit()
        self.keywords_text.setReadOnly(True)
        self.tab_widget.addTab(self.keywords_text, "关键词")
        
        # 添加到分割器
        splitter.addWidget(self.chapter_tree)
        splitter.addWidget(self.tab_widget)
        splitter.setSizes([200, 800])
        
        main_layout.addWidget(splitter)
        
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
        by_chapter = self.chapter_mode.isChecked()
        
        # 清空之前的结果
        self.log_text.clear()
        self.summary_text.clear()
        self.keywords_text.clear()
        self.chapter_tree.clear()
        self.chapters_data = []
        
        # 禁用开始按钮
        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # 创建并启动线程
        self.thread = EnhancedSummarizerThread(file_path, ratio, algorithm, by_chapter)
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
            
            # 显示关键词
            self.keywords_text.setText(", ".join(chapter["keywords"]))
            
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
    window = TitanSummarizerEnhancedUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 