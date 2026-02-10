"""
姿态球组件 Demo
模拟IMU数据，展示 AttitudeBall 组件效果

使用方式:
    python demo_attitude_ball.py

键盘控制:
    W/S  - 俯仰 (pitch)
    A/D  - 滚转 (roll)
    Q/E  - 偏航 (yaw)
    R    - 重置姿态
    Space - 切换自动演示模式
"""

import sys
import math

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QGroupBox, QPushButton, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from components.attitude_ball import AttitudeBall
from protocol.highway_pb2 import IMUParam


class AttitudeBallDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("姿态球组件 Demo - AttitudeBall")
        self.resize(700, 500)

        self._auto_mode = False
        self._auto_time = 0.0

        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)

        # 左侧: 姿态球
        self.attitude_ball = AttitudeBall()
        self.attitude_ball.setMinimumSize(350, 350)
        main_layout.addWidget(self.attitude_ball, 1)

        # 右侧: 控制面板
        control_panel = QVBoxLayout()

        # 滑块组
        slider_group = QGroupBox("姿态控制")
        slider_layout = QVBoxLayout(slider_group)

        self.roll_slider = self._create_slider("Roll (滚转)", -180, 180, 0, slider_layout)
        self.pitch_slider = self._create_slider("Pitch (俯仰)", -90, 90, 0, slider_layout)
        self.yaw_slider = self._create_slider("Yaw (偏航)", -180, 180, 0, slider_layout)

        self.roll_slider.valueChanged.connect(self._on_slider_changed)
        self.pitch_slider.valueChanged.connect(self._on_slider_changed)
        self.yaw_slider.valueChanged.connect(self._on_slider_changed)

        control_panel.addWidget(slider_group)

        # 数据显示
        data_group = QGroupBox("IMU 数据")
        data_layout = QVBoxLayout(data_group)
        font = QFont("Consolas", 10)

        self.roll_label = QLabel("Roll:  0.0°")
        self.pitch_label = QLabel("Pitch: 0.0°")
        self.yaw_label = QLabel("Yaw:   0.0°")
        for lbl in [self.roll_label, self.pitch_label, self.yaw_label]:
            lbl.setFont(font)
            data_layout.addWidget(lbl)

        control_panel.addWidget(data_group)

        # 按钮
        btn_layout = QHBoxLayout()

        self.auto_btn = QPushButton("自动演示模式")
        self.auto_btn.setCheckable(True)
        self.auto_btn.clicked.connect(self._toggle_auto)
        btn_layout.addWidget(self.auto_btn)

        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self._reset)
        btn_layout.addWidget(reset_btn)

        control_panel.addLayout(btn_layout)

        # IMU模拟
        imu_group = QGroupBox("IMU 模拟")
        imu_layout = QVBoxLayout(imu_group)
        self.imu_btn = QPushButton("发送模拟 IMU 数据")
        self.imu_btn.clicked.connect(self._send_simulated_imu)
        imu_layout.addWidget(self.imu_btn)

        self.imu_info = QLabel("点击按钮发送模拟的 DeviceParam.imu_param 数据")
        self.imu_info.setWordWrap(True)
        self.imu_info.setFont(QFont("Microsoft YaHei", 8))
        imu_layout.addWidget(self.imu_info)

        control_panel.addWidget(imu_group)
        control_panel.addStretch()

        main_layout.addLayout(control_panel)

    def _create_slider(self, label: str, min_val: int, max_val: int,
                       default: int, layout: QVBoxLayout) -> QSlider:
        lbl = QLabel(f"{label}: {default}°")
        lbl.setFont(QFont("Microsoft YaHei", 9))
        layout.addWidget(lbl)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default)
        slider.setProperty("_label", lbl)
        slider.setProperty("_name", label)
        slider.valueChanged.connect(
            lambda v, l=lbl, n=label: l.setText(f"{n}: {v}°")
        )
        layout.addWidget(slider)
        return slider

    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._auto_update)
        self.timer.start(33)  # ~30 FPS

    def _on_slider_changed(self):
        if self._auto_mode:
            return
        roll = self.roll_slider.value()
        pitch = self.pitch_slider.value()
        yaw = self.yaw_slider.value()
        self.attitude_ball.set_attitude(roll, pitch, yaw)
        self._update_labels(roll, pitch, yaw)

    def _update_labels(self, roll, pitch, yaw):
        self.roll_label.setText(f"Roll:  {roll:+.1f}°")
        self.pitch_label.setText(f"Pitch: {pitch:+.1f}°")
        self.yaw_label.setText(f"Yaw:   {yaw:+.1f}°")

    def _toggle_auto(self, checked):
        self._auto_mode = checked
        self._auto_time = 0.0
        self.roll_slider.setEnabled(not checked)
        self.pitch_slider.setEnabled(not checked)
        self.yaw_slider.setEnabled(not checked)

    def _reset(self):
        self._auto_mode = False
        self.auto_btn.setChecked(False)
        self.roll_slider.setValue(0)
        self.pitch_slider.setValue(0)
        self.yaw_slider.setValue(0)
        self.roll_slider.setEnabled(True)
        self.pitch_slider.setEnabled(True)
        self.yaw_slider.setEnabled(True)
        self.attitude_ball.set_attitude(0, 0, 0)
        self._update_labels(0, 0, 0)

    def _auto_update(self):
        if not self._auto_mode:
            return

        dt = 0.033
        self._auto_time += dt

        t = self._auto_time
        roll = 30 * math.sin(t * 0.8)
        pitch = 20 * math.sin(t * 0.5)
        yaw = 45 * math.sin(t * 0.3)

        self.attitude_ball.set_attitude(roll, pitch, yaw)
        self._update_labels(roll, pitch, yaw)

        # 同步滑块 (不触发信号)
        self.roll_slider.blockSignals(True)
        self.pitch_slider.blockSignals(True)
        self.yaw_slider.blockSignals(True)
        self.roll_slider.setValue(int(roll))
        self.pitch_slider.setValue(int(pitch))
        self.yaw_slider.setValue(int(yaw))
        self.roll_slider.blockSignals(False)
        self.pitch_slider.blockSignals(False)
        self.yaw_slider.blockSignals(False)

    def _send_simulated_imu(self):
        """模拟发送 IMUParam 数据，演示 update_from_imu 接口"""
        imu = IMUParam(
            gyroscope_x=5.0,
            gyroscope_y=-3.0,
            gyroscope_z=1.5,
            acceleration_x=0.5,
            acceleration_y=-0.3,
            acceleration_z=9.8
        )
        self.attitude_ball.update_from_imu(imu, dt=0.05)
        self._update_labels(
            self.attitude_ball.roll,
            self.attitude_ball.pitch,
            self.attitude_ball.yaw
        )
        self.imu_info.setText(
            f"已发送 IMU 数据:\n"
            f"  Gyro:  X={imu.gyroscope_x:.1f} Y={imu.gyroscope_y:.1f} Z={imu.gyroscope_z:.1f} °/s\n"
            f"  Accel: X={imu.acceleration_x:.1f} Y={imu.acceleration_y:.1f} Z={imu.acceleration_z:.1f} m/s²"
        )

    def keyPressEvent(self, event):
        step = 5
        key = event.key()
        if key == Qt.Key_W:
            self.pitch_slider.setValue(self.pitch_slider.value() + step)
        elif key == Qt.Key_S:
            self.pitch_slider.setValue(self.pitch_slider.value() - step)
        elif key == Qt.Key_A:
            self.roll_slider.setValue(self.roll_slider.value() - step)
        elif key == Qt.Key_D:
            self.roll_slider.setValue(self.roll_slider.value() + step)
        elif key == Qt.Key_Q:
            self.yaw_slider.setValue(self.yaw_slider.value() - step)
        elif key == Qt.Key_E:
            self.yaw_slider.setValue(self.yaw_slider.value() + step)
        elif key == Qt.Key_R:
            self._reset()
        elif key == Qt.Key_Space:
            self.auto_btn.setChecked(not self.auto_btn.isChecked())
            self._toggle_auto(self.auto_btn.isChecked())
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    demo = AttitudeBallDemo()
    demo.show()
    sys.exit(app.exec_())
