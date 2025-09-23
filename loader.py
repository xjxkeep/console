
import json
import os
import sys
import time
import typing

from PyQt5.QtCore import QThread, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QCloseEvent, QFont, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QProgressBar,
    QSplashScreen,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import BodyLabel
from qfluentwidgets.common import FluentIcon
from qfluentwidgets.window import FluentWindow




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
            time.sleep(0.1)
        
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
        
        # 添加标题文本
        self.title_label = QLabel("应用程序启动中", self)
        self.title_label.setFont(QFont("SimHei", 16, QFont.Bold))
        self.title_label.setGeometry(0, 150, 600, 30)
        self.title_label.setAlignment(Qt.AlignCenter)
        
        # 添加加载进度条
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setGeometry(100, 250, 400, 20)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        
        # 创建并启动加载线程
        self.loading_thread = LoadingThread(self)
        self.loading_thread.progress_updated.connect(self.update_progress)
        self.loading_thread.loading_finished.connect(self.loading_complete)
        self.loading_thread.start()
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def loading_complete(self):
        """加载完成，关闭启动页并显示主窗口"""
        # 延迟一小段时间，让用户看到加载完成
        self.loading_thread.progress=100
        self.loading_thread.wait()
        self.update_progress(100)
        QTimer.singleShot(500, self.close)
    
