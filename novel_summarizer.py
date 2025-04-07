#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import re
import json
import traceback
import codecs
import json
from PyQt5 import QtWidgets, QtGui, QtCore
from openrouter_api import summarize_text

class NovelSummarizer(QtWidgets.QMainWindow):
    def __init__(self):
        super(NovelSummarizer, self).__init__()
        
        self.novel_content = ""
        self.chapters = []
        self.chapter_summaries = {}
        self.current_chapter_index = -1
        self.current_model = "meta-llama/llama-4-maverick:free"
        
        self.initUI()
        self.loadNovel("novels/凡人修仙传.txt")
        
    def initUI(self):
        # 设置窗口属性
        self.setWindowTitle(u'小说章节摘要工具 - by Allen Yang')
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央窗口部件
        centralWidget = QtWidgets.QWidget()
        self.setCentralWidget(centralWidget)
        
        # 创建主布局
        mainLayout = QtWidgets.QVBoxLayout(centralWidget)
        
        # 顶部控制区域
        controlLayout = QtWidgets.QHBoxLayout()
        
        # 模型选择
        modelLabel = QtWidgets.QLabel(u"模型:")
        self.modelCombo = QtWidgets.QComboBox()
        self.modelCombo.addItems([
            "meta-llama/llama-4-maverick:free",
        ])
        self.modelCombo.setEditable(True)
        self.modelCombo.currentIndexChanged.connect(self.changeModel)
        
        # 摘要长度选择
        summaryLenLabel = QtWidgets.QLabel(u"摘要长度:")
        self.summaryLenSpinBox = QtWidgets.QSpinBox()
        self.summaryLenSpinBox.setRange(50, 500)
        self.summaryLenSpinBox.setValue(100)
        self.summaryLenSpinBox.setSuffix(u" 字")
        
        # 保存摘要按钮
        self.saveButton = QtWidgets.QPushButton(u"保存所有摘要")
        self.saveButton.clicked.connect(self.saveAllSummaries)
        
        # 加载摘要按钮
        self.loadButton = QtWidgets.QPushButton(u"加载摘要文件")
        self.loadButton.clicked.connect(self.loadSummaries)
        
        # 加载小说按钮
        self.loadNovelButton = QtWidgets.QPushButton(u"加载小说")
        self.loadNovelButton.clicked.connect(self.browseNovel)
        
        # 添加到控制区域
        controlLayout.addWidget(modelLabel)
        controlLayout.addWidget(self.modelCombo)
        controlLayout.addWidget(summaryLenLabel)
        controlLayout.addWidget(self.summaryLenSpinBox)
        controlLayout.addWidget(self.saveButton)
        controlLayout.addWidget(self.loadButton)
        controlLayout.addWidget(self.loadNovelButton)
        
        # 设置控制区域的固定高度
        controlContainer = QtWidgets.QWidget()
        controlContainer.setLayout(controlLayout)
        controlContainer.setFixedHeight(50)
        
        # 主内容区域
        contentLayout = QtWidgets.QHBoxLayout()
        
        # 左侧章节列表
        self.chapterList = QtWidgets.QListWidget()
        self.chapterList.setFixedWidth(200)
        self.chapterList.currentRowChanged.connect(self.chapterSelected)
        
        # 右侧内容区域
        rightLayout = QtWidgets.QVBoxLayout()
        
        # 正文区域
        self.contentTextEdit = QtWidgets.QTextEdit()
        self.contentTextEdit.setReadOnly(True)
        
        # 摘要区域
        summaryLayout = QtWidgets.QHBoxLayout()
        self.summaryTextEdit = QtWidgets.QTextEdit()
        self.summaryTextEdit.setFixedHeight(120)
        summarizeButton = QtWidgets.QPushButton(u"生成摘要")
        summarizeButton.clicked.connect(self.generateSummary)
        
        summaryLayout.addWidget(self.summaryTextEdit)
        summaryLayout.addWidget(summarizeButton)
        
        rightLayout.addWidget(self.contentTextEdit, 3)
        rightLayout.addLayout(summaryLayout, 1)
        
        # 添加到内容区域
        contentLayout.addWidget(self.chapterList)
        contentLayout.addLayout(rightLayout)
        
        # 组装主布局
        mainLayout.addWidget(controlContainer)
        mainLayout.addLayout(contentLayout)
        
        # 状态栏
        self.statusBar().showMessage(u'准备就绪')
        
        # 显示窗口
        self.show()
        
    def loadNovel(self, filepath):
        self.statusBar().showMessage(u'正在加载小说: ' + filepath)
        try:
            # 检查文件是否存在
            if not os.path.exists(filepath):
                self.statusBar().showMessage(u'加载小说失败: 文件不存在 - ' + filepath)
                return
                
            # 读取小说文件，尝试不同编码
            try:
                with codecs.open(filepath, 'r', 'utf-8') as f:
                    self.novel_content = f.read()
            except UnicodeDecodeError:
                try:
                    with codecs.open(filepath, 'r', 'gbk') as f:
                        self.novel_content = f.read()
                except UnicodeDecodeError:
                    with codecs.open(filepath, 'r', 'gb18030') as f:
                        self.novel_content = f.read()
            
            # 分析章节
            self.chapters = []
            lines = self.novel_content.split('\n')
            
            chapter_start_line = 0
            current_line = 0
            chapter_title = u""
            
            for i, line in enumerate(lines):
                # 检测章节标题，这里使用简单的启发式方法：以"第"开头且包含"章"的行
                if (line.strip().startswith(u'第') and u'章' in line) or \
                   (line.strip().startswith(u'Chapter') and len(line.strip()) < 30):
                    
                    # 如果不是第一个章节，就添加上一章
                    if chapter_start_line > 0:
                        chapter_content = '\n'.join(lines[chapter_start_line:i])
                        self.chapters.append({
                            'title': chapter_title,
                            'content': chapter_content
                        })
                    
                    chapter_start_line = i
                    chapter_title = line.strip()
                    current_line = i + 1
            
            # 添加最后一章
            if chapter_start_line > 0:
                chapter_content = '\n'.join(lines[chapter_start_line:])
                self.chapters.append({
                    'title': chapter_title,
                    'content': chapter_content
                })
            
            # 清空章节列表和摘要字典
            self.chapterList.clear()
            self.chapter_summaries = {}
            
            # 填充章节列表
            for chapter in self.chapters:
                self.chapterList.addItem(chapter['title'])
            
            # 尝试加载现有摘要
            summary_path = filepath.replace('.txt', '_summaries.json')
            if os.path.exists(summary_path):
                self.loadSummariesFromFile(summary_path)
            
            self.statusBar().showMessage(u'小说加载完成，共 {0} 章'.format(len(self.chapters)))
        
        except Exception as e:
            self.statusBar().showMessage(u'加载小说失败: ' + str(e))
    
    def chapterSelected(self, index):
        if index >= 0 and index < len(self.chapters):
            self.current_chapter_index = index
            
            # 显示章节内容
            self.contentTextEdit.setPlainText(self.chapters[index]['content'])
            
            # 显示摘要（如果有）
            chapter_title = self.chapters[index]['title']
            if chapter_title in self.chapter_summaries:
                self.summaryTextEdit.setPlainText(self.chapter_summaries[chapter_title])
            else:
                self.summaryTextEdit.clear()
    
    def generateSummary(self):
        if self.current_chapter_index < 0:
            return
        
        chapter = self.chapters[self.current_chapter_index]
        summary_len = self.summaryLenSpinBox.value()
        
        self.statusBar().showMessage(u'正在生成摘要...')
        
        try:
            summary = summarize_text(
                chapter['content'], 
                summary_len, 
                model=self.current_model
            )
            
            self.summaryTextEdit.setPlainText(summary)
            self.chapter_summaries[chapter['title']] = summary
            
            self.statusBar().showMessage(u'摘要生成完成')
        except Exception as e:
            self.statusBar().showMessage(u'生成摘要失败: ' + str(e))
    
    def saveAllSummaries(self):
        if not self.chapters:
            return
        
        # 获取原小说路径，将摘要保存在同一目录下
        novel_path = "novels/凡人修仙传.txt"  # 默认路径
        summary_path = novel_path.replace('.txt', '_summaries.json')
        
        try:
            with codecs.open(summary_path, 'w', 'utf-8') as f:
                json.dump(self.chapter_summaries, f, ensure_ascii=False, indent=4)
            
            self.statusBar().showMessage(u'摘要已保存到: ' + summary_path)
        except Exception as e:
            self.statusBar().showMessage(u'保存摘要失败: ' + str(e))
    
    def loadSummaries(self):
        file_dialog = QtWidgets.QFileDialog()
        summary_path, _ = file_dialog.getOpenFileName(
            self, u"加载摘要文件", "novels", "JSON Files (*.json)"
        )
        
        if summary_path:
            self.loadSummariesFromFile(summary_path)
    
    def loadSummariesFromFile(self, summary_path):
        try:
            with codecs.open(summary_path, 'r', 'utf-8') as f:
                self.chapter_summaries = json.load(f)
            
            # 如果当前有选中的章节，更新摘要显示
            if self.current_chapter_index >= 0:
                chapter_title = self.chapters[self.current_chapter_index]['title']
                if chapter_title in self.chapter_summaries:
                    self.summaryTextEdit.setPlainText(self.chapter_summaries[chapter_title])
            
            self.statusBar().showMessage(u'摘要加载完成，共 {0} 章'.format(len(self.chapter_summaries)))
        except Exception as e:
            self.statusBar().showMessage(u'加载摘要失败: ' + str(e))
    
    def browseNovel(self):
        file_dialog = QtWidgets.QFileDialog()
        novel_path, _ = file_dialog.getOpenFileName(
            self, u"选择小说文件", "novels", "Text Files (*.txt)"
        )
        
        if novel_path:
            self.loadNovel(novel_path)
    
    def changeModel(self, index):
        self.current_model = self.modelCombo.currentText()
        self.statusBar().showMessage(u'已切换到模型: ' + self.current_model)

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")  # 设置现代化的风格
    
    # 设置应用程序图标
    if os.path.exists("images/icon.png"):
        app.setWindowIcon(QtGui.QIcon("images/icon.png"))
    
    # 应用暗色模式样式表
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #2d2d2d;
            color: #e0e0e0;
        }
        QTextEdit {
            border: 1px solid #555555;
            border-radius: 3px;
            padding: 5px;
            background-color: #353535;
            color: #e0e0e0;
            font-family: 'Microsoft YaHei', Arial;
            font-size: 14px;
        }
        QListWidget {
            border: 1px solid #555555;
            border-radius: 3px;
            background-color: #353535;
            color: #e0e0e0;
            font-family: 'Microsoft YaHei', Arial;
            font-size: 13px;
            padding: 5px;
        }
        QListWidget::item {
            padding: 5px;
        }
        QListWidget::item:selected {
            background-color: #3a7ab3;
            color: white;
        }
        QPushButton {
            background-color: #3a7ab3;
            color: white;
            border: none;
            border-radius: 3px;
            padding: 5px 15px;
            min-width: 80px;
        }
        QPushButton:hover {
            background-color: #4a8ac3;
        }
        QPushButton:pressed {
            background-color: #2a6aa3;
        }
        QLabel {
            font-family: 'Microsoft YaHei', Arial;
            color: #e0e0e0;
        }
        QComboBox, QSpinBox {
            border: 1px solid #555555;
            border-radius: 3px;
            padding: 3px;
            min-width: 6em;
            background-color: #353535;
            color: #e0e0e0;
            selection-background-color: #3a7ab3;
        }
        QComboBox QAbstractItemView {
            background-color: #353535;
            color: #e0e0e0;
            selection-background-color: #3a7ab3;
        }
        QStatusBar {
            background-color: #2a2a2a;
            color: #e0e0e0;
        }
        QScrollBar:vertical {
            border: none;
            background: #353535;
            width: 10px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:vertical {
            background: #555555;
            min-height: 20px;
            border-radius: 5px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
    """)
    
    ex = NovelSummarizer()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 

