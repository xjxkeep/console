"""
速度仪表盘组件 Demo
模拟速度变化，展示 Speedometer 组件效果

使用方式:
    python demo_speedometer.py
"""

import sys
import math

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QPushButton, QSlider, QLabel
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from components.speedometer import Speedometer


class SpeedometerDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("速度仪表盘 Demo - Speedometer")
        self.resize(650, 420)
        self.setStyleSheet("background-color: #1a1c24;")

        self._auto_mode = False
        self._auto_time = 0.0
        self._odometer = 0.0

        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)

        # 左侧: 大尺寸仪表盘
        self.speedometer = Speedometer(max_speed=120)
        self.speedometer.setMinimumSize(300, 300)
        main_layout.addWidget(self.speedometer, 1)

        # 右侧: 控制面板
        control_layout = QVBoxLayout()

        label_style = "color: #b0b5c5;"

        # 速度滑块
        slider_group = QGroupBox("速度控制")
        slider_group.setStyleSheet(
            "QGroupBox { color: #b0b5c5; border: 1px solid #3a3d4a; "
            "border-radius: 6px; margin-top: 10px; padding-top: 16px; }"
            "QGroupBox::title { subcontrol-position: top left; padding: 0 6px; }"
        )
        sg_layout = QVBoxLayout(slider_group)

        self.speed_label = QLabel("速度: 0 km/h")
        self.speed_label.setStyleSheet(label_style)
        self.speed_label.setFont(QFont("Consolas", 11))
        sg_layout.addWidget(self.speed_label)

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(0, 120)
        self.speed_slider.setValue(0)
        self.speed_slider.setStyleSheet(
            "QSlider::groove:horizontal { background: #2a2d3a; height: 6px; border-radius: 3px; }"
            "QSlider::handle:horizontal { background: #00dcff; width: 16px; margin: -5px 0; border-radius: 8px; }"
            "QSlider::sub-page:horizontal { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, "
            "stop:0 #00dcff, stop:0.5 #ffdc00, stop:1 #ff4444); border-radius: 3px; }"
        )
        self.speed_slider.valueChanged.connect(self._on_slider)
        sg_layout.addWidget(self.speed_slider)

        control_layout.addWidget(slider_group)

        # 里程
        self.odo_label = QLabel("里程: 0.0 km")
        self.odo_label.setStyleSheet(label_style)
        self.odo_label.setFont(QFont("Consolas", 10))
        control_layout.addWidget(self.odo_label)

        # 预设按钮
        preset_group = QGroupBox("快速预设")
        preset_group.setStyleSheet(slider_group.styleSheet())
        pg_layout = QHBoxLayout(preset_group)

        btn_style = (
            "QPushButton { background: #2a2d3a; color: #b0b5c5; border: 1px solid #3a3d4a; "
            "border-radius: 4px; padding: 6px 12px; }"
            "QPushButton:hover { background: #3a3d4a; }"
            "QPushButton:pressed { background: #4a4d5a; }"
        )

        for speed in [0, 30, 60, 90, 120]:
            btn = QPushButton(f"{speed}")
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(lambda _, s=speed: self._set_speed(s))
            pg_layout.addWidget(btn)

        control_layout.addWidget(preset_group)

        # 自动模式
        btn_layout = QHBoxLayout()
        self.auto_btn = QPushButton("自动演示")
        self.auto_btn.setCheckable(True)
        self.auto_btn.setStyleSheet(btn_style)
        self.auto_btn.clicked.connect(self._toggle_auto)
        btn_layout.addWidget(self.auto_btn)

        self.accel_btn = QPushButton("急加速")
        self.accel_btn.setStyleSheet(btn_style)
        self.accel_btn.clicked.connect(lambda: self._set_speed(120))
        btn_layout.addWidget(self.accel_btn)

        self.brake_btn = QPushButton("急刹车")
        self.brake_btn.setStyleSheet(btn_style)
        self.brake_btn.clicked.connect(lambda: self._set_speed(0))
        btn_layout.addWidget(self.brake_btn)

        control_layout.addLayout(btn_layout)
        control_layout.addStretch()

        main_layout.addLayout(control_layout)

    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)

    def _on_slider(self, v):
        if self._auto_mode:
            return
        self.speedometer.setValue(v)
        self.speed_label.setText(f"速度: {v} km/h")

    def _set_speed(self, speed):
        self.speed_slider.setValue(speed)
        self.speedometer.setValue(speed)
        self.speed_label.setText(f"速度: {speed} km/h")

    def _toggle_auto(self, checked):
        self._auto_mode = checked
        self._auto_time = 0.0
        self.speed_slider.setEnabled(not checked)

    def _tick(self):
        dt = 0.033
        current = self.speedometer._display_value
        self._odometer += current / 3600 * dt
        self.speedometer.setOdometer(self._odometer)
        self.odo_label.setText(f"里程: {self._odometer:.1f} km")

        if not self._auto_mode:
            return

        self._auto_time += dt
        t = self._auto_time

        # 模拟驾驶: 加速 → 巡航 → 减速 → 再加速
        speed = 60 + 55 * math.sin(t * 0.4) + 15 * math.sin(t * 1.1)
        speed = max(0, min(120, speed))

        self.speedometer.setValue(speed)
        self.speed_label.setText(f"速度: {speed:.0f} km/h")

        self.speed_slider.blockSignals(True)
        self.speed_slider.setValue(int(speed))
        self.speed_slider.blockSignals(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    demo = SpeedometerDemo()
    demo.show()
    sys.exit(app.exec_())
