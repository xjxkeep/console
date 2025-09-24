
import json
import os
import sys
import time
import typing

from PyQt5.QtCore import QRect, QThread, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QCloseEvent, QFont, QPixmap
from PyQt5.QtWidgets import (
    QSplashScreen,
)




class LoadingThread(QThread):
    """后台加载线程，用于模拟加载过程并发送进度更新"""
    progress_updated = pyqtSignal(int)
    loading_finished = pyqtSignal() 
    
    def __init__(self,parent=None):
        super().__init__(parent)
        self.progress=0
    
    def run(self):
        """模拟加载过程，实际项目中可替换为真实的资源加载逻辑"""
        # 模拟加载步骤

        while self.progress < 100:
            self.progress += 1
            # 发送进度更新信号
            self.progress_updated.emit(self.progress)
            # 模拟加载延迟
            time.sleep(0.01)
        
        # 加载完成，发送完成信号
        self.loading_finished.emit()

class SplashScreen(QSplashScreen):
    """启动加载页面"""
    def __init__(self):
        # 创建启动页并设置背景
        pixmap = QPixmap(600, 400)
        pixmap.fill(Qt.white)
        super().__init__(pixmap)
        
        # 设置启动页标题
        self.setWindowTitle("加载中")
        
        # 初始化进度值
        self.progress_value = 0
        
        # 创建并启动加载线程
        self.loading_thread = LoadingThread(self)
        self.loading_thread.progress_updated.connect(self.update_progress)
        self.loading_thread.loading_finished.connect(self.loading_complete)
        self.loading_thread.start()
    
    def drawContents(self, painter):
        """重写绘制方法，在 macOS 上确保内容正确显示"""
        super().drawContents(painter)
        
        # 设置字体
        font = QFont("Arial", 16, QFont.Bold)
        painter.setFont(font)
        painter.setPen(Qt.black)
        
        # 绘制标题文本
        title_text = "应用程序启动中"
        painter.drawText(0, 150, 600, 30, Qt.AlignCenter, title_text)
        
        # 绘制进度条背景
        progress_bg_rect = QRect(100, 250, 400, 20)
        painter.setBrush(Qt.lightGray)
        painter.setPen(Qt.black)
        painter.drawRect(progress_bg_rect)
        
        # 绘制进度条填充
        if self.progress_value > 0:
            progress_width = int(400 * self.progress_value / 100)
            progress_rect = QRect(100, 250, progress_width, 20)
            painter.setBrush(Qt.blue)
            painter.drawRect(progress_rect)
        
        # 绘制进度文本
        progress_text = f"{self.progress_value}%"
        painter.setFont(QFont("Arial", 10))
        painter.drawText(progress_bg_rect, Qt.AlignCenter, progress_text)
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_value = value
        # 强制重绘
        self.repaint()
    
    def loading_complete(self):
        """加载完成，关闭启动页并显示主窗口"""
        # 延迟一小段时间，让用户看到加载完成
        self.loading_thread.progress = 100
        self.loading_thread.wait()
        self.update_progress(100)
        QTimer.singleShot(500, self.close)
    
