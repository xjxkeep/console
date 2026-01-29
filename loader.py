
import os
import time

from PyQt5.QtCore import QRect, QThread, QTimer, Qt, pyqtSignal, QRectF
from PyQt5.QtGui import (
    QColor, QFont, QLinearGradient, QPainter, QPainterPath,
    QPixmap, QBrush, QPen
)
from PyQt5.QtWidgets import QSplashScreen

from pkg.version import VERSION, APP_NAME


class LoadingThread(QThread):
    """后台加载线程，用于模拟加载过程并发送进度更新"""
    progress_updated = pyqtSignal(int)
    loading_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress = 0

    def run(self):
        """模拟加载过程，实际项目中可替换为真实的资源加载逻辑"""
        while self.progress < 100:
            self.progress += 1
            self.progress_updated.emit(self.progress)
            time.sleep(0.02)

        self.loading_finished.emit()


class SplashScreen(QSplashScreen):
    """启动加载页面 - 现代风格设计"""

    def __init__(self):
        # 创建启动页
        pixmap = QPixmap(500, 380)
        pixmap.fill(Qt.transparent)
        super().__init__(pixmap)

        # 设置窗口属性
        self.setWindowTitle("Andless")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)

        # 初始化进度值
        self.progress_value = 0

        # 加载 logo 图片
        logo_path = os.path.join(os.path.dirname(__file__), "assets/images/logo.jpg")
        self.logo_pixmap = QPixmap(logo_path) if os.path.exists(logo_path) else None

        # 创建并启动加载线程
        self.loading_thread = LoadingThread(self)
        self.loading_thread.progress_updated.connect(self.update_progress)
        self.loading_thread.loading_finished.connect(self.loading_complete)
        self.loading_thread.start()

    def drawContents(self, painter):
        """绘制启动页内容"""
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        width = self.pixmap().width()
        height = self.pixmap().height()

        # 绘制背景（深色渐变）
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor(25, 35, 55))
        gradient.setColorAt(0.5, QColor(20, 30, 45))
        gradient.setColorAt(1, QColor(15, 22, 35))

        # 绘制圆角矩形背景
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, width, height), 16, 16)
        painter.fillPath(path, QBrush(gradient))

        # 绘制边框
        painter.setPen(QPen(QColor(60, 80, 110), 1))
        painter.drawPath(path)

        # 绘制 Logo
        if self.logo_pixmap and not self.logo_pixmap.isNull():
            logo_size = 160
            logo_scaled = self.logo_pixmap.scaled(
                logo_size, logo_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            logo_x = (width - logo_scaled.width()) // 2
            logo_y = 50
            painter.drawPixmap(logo_x, logo_y, logo_scaled)
        else:
            # 如果没有 logo，绘制占位符
            self._draw_placeholder_logo(painter, width)

        # 绘制品牌名称
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 28, QFont.Bold)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 3)
        painter.setFont(font)
        painter.drawText(0, 220, width, 45, Qt.AlignCenter, "andless")

        # 绘制标语
        painter.setPen(QColor(120, 150, 200))
        font = QFont("Arial", 11)
        painter.setFont(font)
        painter.drawText(0, 265, width, 25, Qt.AlignCenter, "Remote Control System")

        # 绘制进度条
        self._draw_progress_bar(painter, width, height)

        # 绘制版本号
        painter.setPen(QColor(80, 100, 130))
        font = QFont("Arial", 9)
        painter.setFont(font)
        painter.drawText(0, height - 30, width, 20, Qt.AlignCenter, f"v{VERSION}")

    def _draw_placeholder_logo(self, painter, width):
        """绘制占位 Logo（当图片不存在时）"""
        logo_size = 120
        logo_x = (width - logo_size) // 2
        logo_y = 60

        # 绘制外框
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        painter.setBrush(Qt.NoBrush)

        path = QPainterPath()
        path.addRoundedRect(QRectF(logo_x, logo_y, logo_size, logo_size), 20, 20)
        painter.drawPath(path)

        # 绘制 & 符号
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        font = QFont("Arial", 60, QFont.Bold)
        painter.setFont(font)
        painter.drawText(logo_x, logo_y, logo_size, logo_size, Qt.AlignCenter, "&")

    def _draw_progress_bar(self, painter, width, height):
        """绘制现代风格进度条"""
        bar_width = 300
        bar_height = 4
        bar_x = (width - bar_width) // 2
        bar_y = height - 70

        # 进度条背景
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(40, 50, 70))
        bg_path = QPainterPath()
        bg_path.addRoundedRect(QRectF(bar_x, bar_y, bar_width, bar_height), 2, 2)
        painter.fillPath(bg_path, QBrush(QColor(40, 50, 70)))

        # 进度条填充（渐变）
        if self.progress_value > 0:
            progress_width = int(bar_width * self.progress_value / 100)

            gradient = QLinearGradient(bar_x, 0, bar_x + progress_width, 0)
            gradient.setColorAt(0, QColor(0, 150, 255))
            gradient.setColorAt(1, QColor(0, 200, 255))

            progress_path = QPainterPath()
            progress_path.addRoundedRect(
                QRectF(bar_x, bar_y, progress_width, bar_height), 2, 2
            )
            painter.fillPath(progress_path, QBrush(gradient))

        # 进度文本
        painter.setPen(QColor(100, 130, 170))
        font = QFont("Arial", 10)
        painter.setFont(font)
        status_text = f"Loading... {self.progress_value}%"
        painter.drawText(0, bar_y + 12, width, 20, Qt.AlignCenter, status_text)

    def update_progress(self, value):
        """更新进度条"""
        self.progress_value = value
        self.repaint()

    def loading_complete(self):
        """加载完成，关闭启动页"""
        self.loading_thread.progress = 100
        self.loading_thread.wait()
        self.update_progress(100)
        QTimer.singleShot(300, self.close)
