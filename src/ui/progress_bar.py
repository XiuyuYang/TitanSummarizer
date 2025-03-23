#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
进度条组件模块
提供命令行界面进度显示功能
"""

import sys
import time
import threading
from typing import Optional, Callable

class ProgressBar:
    """命令行进度条类"""
    
    def __init__(
        self,
        total: int = 100,
        prefix: str = '',
        suffix: str = '',
        decimals: int = 1,
        length: int = 50,
        fill: str = '█',
        print_end: str = '\r'
    ):
        """
        初始化进度条
        
        Args:
            total: 总步数
            prefix: 前缀字符串
            suffix: 后缀字符串
            decimals: 百分比小数位数
            length: 进度条字符长度
            fill: 进度条填充字符
            print_end: 打印结束字符
        """
        self.total = max(1, total)  # 避免除以零错误
        self.prefix = prefix
        self.suffix = suffix
        self.decimals = decimals
        self.length = length
        self.fill = fill
        self.print_end = print_end
        
        self._iteration = 0
        self._is_running = False
        self._start_time = None
        self._lock = threading.Lock()
        self._spinner_thread = None
        self._spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self._spinner_index = 0
        self._last_update_time = 0
        self._min_update_interval = 0.1  # 最小更新间隔，秒
    
    def update(self, iteration: Optional[int] = None, prefix: Optional[str] = None, suffix: Optional[str] = None):
        """
        更新进度条
        
        Args:
            iteration: 当前步数，如果为None则自动递增
            prefix: 更新的前缀
            suffix: 更新的后缀
        """
        current_time = time.time()
        
        # 限制更新频率，避免闪烁
        if current_time - self._last_update_time < self._min_update_interval:
            return
            
        self._last_update_time = current_time
            
        with self._lock:
            if iteration is not None:
                self._iteration = iteration
            else:
                self._iteration += 1
                
            if prefix is not None:
                self.prefix = prefix
                
            if suffix is not None:
                self.suffix = suffix
            
            # 计算进度百分比
            percent = min(100.0, (self._iteration / float(self.total)) * 100.0)
            
            # 计算已填充进度条长度
            filled_length = int(self.length * self._iteration // self.total)
            
            # 创建进度条字符串
            progress_bar = self.fill * filled_length + '-' * (self.length - filled_length)
            
            # 计算运行时间
            if self._start_time is None:
                self._start_time = time.time()
                
            elapsed_time = time.time() - self._start_time
            time_str = self._format_time(elapsed_time)
            
            # 打印进度条
            print(f'\r{self.prefix} |{progress_bar}| {percent:.{self.decimals}f}% {time_str} {self.suffix}', end=self.print_end)
            
            # 如果完成，打印换行
            if self._iteration >= self.total:
                print()
    
    def start_spinner(self, text: str = 'Loading'):
        """
        启动加载旋转动画
        
        Args:
            text: 显示的文本
        """
        if self._is_running:
            return
            
        self._is_running = True
        self._start_time = time.time()
        
        def _spin():
            while self._is_running:
                elapsed_time = time.time() - self._start_time
                time_str = self._format_time(elapsed_time)
                
                with self._lock:
                    sys.stdout.write(f'\r{text} {self._spinner_chars[self._spinner_index]} {time_str}')
                    sys.stdout.flush()
                
                self._spinner_index = (self._spinner_index + 1) % len(self._spinner_chars)
                time.sleep(0.1)
        
        self._spinner_thread = threading.Thread(target=_spin)
        self._spinner_thread.daemon = True
        self._spinner_thread.start()
    
    def stop_spinner(self, message: Optional[str] = None):
        """
        停止加载旋转动画
        
        Args:
            message: 完成后显示的消息
        """
        self._is_running = False
        
        if self._spinner_thread:
            self._spinner_thread.join(timeout=0.5)
            
        if message:
            elapsed_time = time.time() - self._start_time
            time_str = self._format_time(elapsed_time)
            print(f'\r{message} {time_str}')
        else:
            print()
    
    def _format_time(self, seconds: float) -> str:
        """
        格式化时间显示
        
        Args:
            seconds: 时间秒数
            
        Returns:
            格式化的时间字符串
        """
        if seconds < 60:
            return f"[{seconds:.1f}s]"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            seconds = seconds % 60
            return f"[{minutes}m {seconds:.1f}s]"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds = seconds % 60
            return f"[{hours}h {minutes}m {seconds:.1f}s]"

class CallbackProgressBar:
    """
    可以用作回调函数的进度条包装器
    """
    
    def __init__(
        self,
        total: int = 100,
        prefix: str = 'Progress',
        suffix: str = 'Complete',
        length: int = 50
    ):
        """
        初始化进度条回调
        
        Args:
            total: 总步数
            prefix: 进度条前缀
            suffix: 进度条后缀
            length: 进度条长度
        """
        self.progress_bar = ProgressBar(
            total=total,
            prefix=prefix,
            suffix=suffix,
            length=length
        )
        self.finished = False
    
    def __call__(self, current: int, total: Optional[int] = None, message: Optional[str] = None):
        """
        作为回调函数使用
        
        Args:
            current: 当前进度
            total: 可选的总步数更新
            message: 可选的消息或状态
        """
        if total is not None and total != self.progress_bar.total:
            self.progress_bar.total = max(1, total)
            
        suffix = message if message is not None else self.progress_bar.suffix
        
        if current >= self.progress_bar.total:
            if not self.finished:
                self.progress_bar.update(current, suffix=suffix)
                self.finished = True
        else:
            self.progress_bar.update(current, suffix=suffix)
            self.finished = False

def create_progress_callback(
    total: int = 100,
    prefix: str = 'Progress',
    desc: str = 'Processing'
) -> Callable:
    """
    创建进度回调函数
    
    Args:
        total: 总步数
        prefix: 进度条前缀
        desc: 描述文本
        
    Returns:
        进度回调函数
    """
    progress_bar = CallbackProgressBar(
        total=total,
        prefix=f"{prefix} |",
        suffix=desc
    )
    
    return progress_bar

# 测试代码
def test_progress_bar():
    """测试进度条组件"""
    print("===== 进度条组件测试 =====")
    
    # 基本进度条测试
    print("\n基本进度条测试:")
    progress = ProgressBar(total=50, prefix='处理中', suffix='完成')
    
    for i in range(51):
        progress.update()
        time.sleep(0.02)
    
    # 旋转加载动画测试
    print("\n旋转加载动画测试:")
    spinner = ProgressBar()
    spinner.start_spinner("加载中")
    
    time.sleep(2)
    
    spinner.stop_spinner("加载完成")
    
    # 进度回调测试
    print("\n进度回调测试:")
    callback = create_progress_callback(total=100, prefix='下载', desc='下载文件')
    
    total_items = 100
    for i in range(total_items + 1):
        callback(i, total_items, f"文件 {i}/{total_items}")
        time.sleep(0.01)
        
    print("\n测试完成!")

if __name__ == "__main__":
    test_progress_bar() 