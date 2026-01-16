#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QApplication, QLabel
from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QFont
from PyQt5.Qt import Qt

class WaveformWidget(QWidget):
    """简单的波形显示组件，只使用QPainter绘制"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = np.array([])
        self.background_color = QColor(20, 20, 20)  # 深色背景
        self.waveform_color = QColor(0, 255, 0)     # 绿色波形
        self.grid_color = QColor(60, 60, 60)        # 网格颜色
        self.center_line_color = QColor(100, 100, 100)  # 中心线
        
        # 显示设置
        self.show_grid = True
        self.show_center_line = True
        self.auto_scale = True
        self.scale_factor = 1.0
        
        self.setFixedHeight(100)
        
    def set_data(self, data):
        """设置要显示的波形数据"""
        if isinstance(data, (list, tuple)):
            self.data = np.array(data)
        else:
            self.data = data
        self.update()  # 触发重绘
    
    def set_colors(self, background=None, waveform=None, grid=None):
        """设置颜色主题"""
        if background:
            self.background_color = QColor(background)
        if waveform:
            self.waveform_color = QColor(waveform)
        if grid:
            self.grid_color = QColor(grid)
        self.update()
    
    def paintEvent(self, event):
        """绘制波形"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # 抗锯齿
        
        # 获取绘制区域
        rect = self.rect()
        width = rect.width()
        height = rect.height()
        
        # 填充背景
        painter.fillRect(rect, self.background_color)
        
        # 如果没有数据，显示提示
        if len(self.data) == 0:
            painter.setPen(QColor(128, 128, 128))
            painter.setFont(QFont("Arial", 12))
            painter.drawText(rect, Qt.AlignCenter, "No Data")
            return
        
        # 绘制网格
        if self.show_grid:
            self._draw_grid(painter, width, height)
        
        # 绘制中心线
        if self.show_center_line:
            painter.setPen(QPen(self.center_line_color, 1))
            painter.drawLine(0, height // 2, width, height // 2)
        
        # 绘制波形
        self._draw_waveform(painter, width, height)
        
        # 绘制信息
        self._draw_info(painter, width, height)
    
    def _draw_grid(self, painter, width, height):
        """绘制网格"""
        painter.setPen(QPen(self.grid_color, 1))
        
        # 垂直网格线
        grid_spacing_x = width // 10
        for i in range(1, 10):
            x = i * grid_spacing_x
            painter.drawLine(x, 0, x, height)
        
        # 水平网格线
        grid_spacing_y = height // 8
        for i in range(1, 8):
            y = i * grid_spacing_y
            painter.drawLine(0, y, width, y)
    
    def _draw_waveform(self, painter, width, height):
        """绘制波形"""
        if len(self.data) < 2:
            return
        
        # 设置波形画笔
        painter.setPen(QPen(self.waveform_color, 2))
        
        # 计算缩放
        data_len = len(self.data)
        x_scale = width / (data_len - 1)
        
        # 自动缩放Y轴
        if self.auto_scale and len(self.data) > 0:
            data_max = np.max(np.abs(self.data))
            if data_max > 0:
                y_scale = (height * 0.4) / data_max  # 使用40%的高度
            else:
                y_scale = 1
        else:
            y_scale = height * 0.4 * self.scale_factor
        
        # 计算中心位置
        center_y = height // 2
        
        # 绘制波形线条
        points = []
        for i in range(data_len):
            x = int(i * x_scale)
            y = int(center_y - self.data[i] * y_scale)
            
            # 限制Y坐标在有效范围内
            y = max(0, min(height, y))
            points.append((x, y))
        
        # 连接所有点
        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], 
                           points[i + 1][0], points[i + 1][1])
    
    def _draw_info(self, painter, width, height):
        """绘制信息文本"""
        if len(self.data) == 0:
            return
            
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("Arial", 10))
        
        # 显示数据信息
        info_text = f"Samples: {len(self.data)} | "
        info_text += f"Max: {np.max(self.data):.3f} | "
        info_text += f"Min: {np.min(self.data):.3f} | "
        info_text += f"RMS: {np.sqrt(np.mean(self.data**2)):.3f}"
        
        painter.drawText(10, height - 10, info_text)

class WaveformDemo(QWidget):
    """演示窗口"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.init_timer()
        
    def init_ui(self):
        self.setWindowTitle("简单波形显示器")
        self.setGeometry(100, 100, 800, 600)
        
        layout = QVBoxLayout()
        
        # 波形显示组件
        self.waveform = WaveformWidget()
        layout.addWidget(self.waveform)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        self.sine_btn = QPushButton("正弦波")
        self.sine_btn.clicked.connect(self.generate_sine)
        button_layout.addWidget(self.sine_btn)
        
        self.square_btn = QPushButton("方波")
        self.square_btn.clicked.connect(self.generate_square)
        button_layout.addWidget(self.square_btn)
        
        self.noise_btn = QPushButton("噪声")
        self.noise_btn.clicked.connect(self.generate_noise)
        button_layout.addWidget(self.noise_btn)
        
        self.audio_btn = QPushButton("模拟音频")
        self.audio_btn.clicked.connect(self.start_audio_simulation)
        button_layout.addWidget(self.audio_btn)
        
        self.clear_btn = QPushButton("清除")
        self.clear_btn.clicked.connect(self.clear_waveform)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        # 状态标签
        self.status_label = QLabel("点击按钮生成波形")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def init_timer(self):
        """初始化定时器用于动态更新"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_audio_simulation)
        self.audio_time = 0
        
    def generate_sine(self):
        """生成正弦波"""
        t = np.linspace(0, 4 * np.pi, 1000)
        data = np.sin(t) * 0.8
        self.waveform.set_data(data)
        self.status_label.setText("显示正弦波")
    
    def generate_square(self):
        """生成方波"""
        t = np.linspace(0, 4 * np.pi, 1000)
        data = np.sign(np.sin(t)) * 0.6
        self.waveform.set_data(data)
        self.status_label.setText("显示方波")
    
    def generate_noise(self):
        """生成随机噪声"""
        data = np.random.normal(0, 0.3, 1000)
        self.waveform.set_data(data)
        self.status_label.setText("显示随机噪声")
    
    def start_audio_simulation(self):
        """开始音频模拟"""
        if self.timer.isActive():
            self.timer.stop()
            self.audio_btn.setText("模拟音频")
            self.status_label.setText("停止音频模拟")
        else:
            self.timer.start(50)  # 20fps更新
            self.audio_btn.setText("停止")
            self.status_label.setText("实时音频模拟中...")
    
    def update_audio_simulation(self):
        """更新音频模拟"""
        # 模拟复合音频信号
        sample_rate = 1000
        duration = 1.0
        t = np.linspace(0, duration, sample_rate)
        
        # 基频 + 谐波 + 少量噪声
        fundamental = 0.5 * np.sin(2 * np.pi * 440 * t + self.audio_time)
        harmonic2 = 0.2 * np.sin(2 * np.pi * 880 * t + self.audio_time * 1.1)
        harmonic3 = 0.1 * np.sin(2 * np.pi * 1320 * t + self.audio_time * 0.9)
        noise = 0.05 * np.random.normal(0, 1, len(t))
        
        data = fundamental + harmonic2 + harmonic3 + noise
        
        # 添加包络
        envelope = np.exp(-t * 2) * (1 + 0.3 * np.sin(self.audio_time * 3))
        data *= envelope
        
        self.waveform.set_data(data)
        self.audio_time += 0.1
    
    def clear_waveform(self):
        """清除波形"""
        self.waveform.set_data([])
        self.status_label.setText("波形已清除")

def main():
    app = QApplication(sys.argv)
    
    # 创建演示窗口
    demo = WaveformDemo()
    demo.show()
    
    # 生成初始波形
    demo.generate_sine()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 