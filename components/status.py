from datetime import datetime
import logging
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QCloseEvent, QColor, QIcon, QImage, QPixmap
from PyQt5.QtWidgets import *
from qfluentwidgets import (
    FlowLayout,
    FluentIcon,
    TransparentPushButton,
    TransparentToolButton,
    ComboBox,
    GroupHeaderCardWidget,
    BodyLabel,
    CaptionLabel,
    ProgressBar,
    SubtitleLabel,
    CardWidget,
    TableWidget,
    SimpleCardWidget,
    isDarkTheme
)
from components.attitude_ball import AttitudeBall
from components.speedometer import Speedometer
from protocol.highway_pb2 import IMUParam


class DashboardPanel(GroupHeaderCardWidget):
    """仪表盘面板 - 速度仪表盘和姿态球"""
    def __init__(self):
        super().__init__()
        self.setTitle("仪表盘")
        self.setupUi()

    def setupUi(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.speedometer = Speedometer(max_speed=120)
        self.speedometer.setMinimumSize(160, 160)
        layout.addWidget(self.speedometer, 1, Qt.AlignCenter)

        self.attitude_ball = AttitudeBall()
        self.attitude_ball.setMinimumSize(160, 160)
        layout.addWidget(self.attitude_ball, 1, Qt.AlignCenter)

        self.vBoxLayout.addLayout(layout)

    def update_speed_odometer(self, speed: float, odometer: float):
        self.speedometer.setValue(speed)
        self.speedometer.setOdometer(odometer)

    def update_attitude(self, imu_data: IMUParam, dt: float = 0.05):
        """更新姿态球"""
        self.attitude_ball.update_from_imu(imu_data, dt)


class StatusBar(QWidget):
    param_changed=pyqtSignal(dict)
    def update(self):
        self.date.setText(datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    
 
    def update_upload_speed(self,value:float):
        self.upload.setText(f"{value/1024:.2f} kb/s")
    
    def update_download_speed(self,value:float):
        self.download.setText(f"{value/1024:.2f} kb/s")
    
    def update_latency(self,value:int):
        self.signal.setText(f"{value} ms")
    
    def setupUi(self):
        layout=FlowLayout(self,needAni=False)
        layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.setContentsMargins(10, 10, 10, 10)  # 调整边距
        layout.setHorizontalSpacing(15)  # 增加水平间距
        layout.setVerticalSpacing(5)  # 设置垂直间距
        
        # 创建组件并设置统一的样式
        self.signal=TransparentPushButton(FluentIcon.WIFI.icon(color=QColor("#4CAF50")),"- ms")
        self.signal.setMinimumWidth(80)
        
        self.upload=TransparentPushButton(FluentIcon.UP.icon(color=QColor("#2196F3")),"- kb/s")
        self.upload.setMinimumWidth(100)
        
        self.download=TransparentPushButton(FluentIcon.DOWN.icon(color=QColor("#FF9800")),"- kb/s")
        self.download.setMinimumWidth(100)
        
        self.date=TransparentPushButton(FluentIcon.DATE_TIME.icon(color=QColor("#607D8B")),"2025/02/09 21:44:00")
        self.date.setMinimumWidth(180)
        
        self.channel=ComboBox()
        self.channel.addItems(["线路: 上海","线路: 北京"])
        self.channel.setCurrentIndex(0)
        self.channel.setMinimumWidth(120)
   
        self.channel.currentTextChanged.connect(self.__handle_channel_menu_triggered)
        
        self.connect_status=TransparentPushButton(FluentIcon.CLOUD.icon(color=QColor("#F44336")),"服务器状态: 未连接")
        self.connect_status.setMinimumWidth(150)
        
        self.battery=TransparentPushButton(QIcon("assets/svg/battery-full.svg"),"-%")
        self.battery.setMinimumWidth(80)

        self.timer=QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        
        self.sync=TransparentToolButton(FluentIcon.SYNC.icon(color=QColor("#673AB7")))
        self.sync.setToolTip("同步数据")

        # 添加组件到布局
        layout.addWidget(self.connect_status)
        layout.addWidget(self.signal)
        layout.addWidget(self.battery)
        layout.addWidget(self.upload)
        layout.addWidget(self.download)
        layout.addWidget(self.date)
        layout.addWidget(self.channel)
        layout.addWidget(self.sync)
        
        self.setLayout(layout)
        
        # 设置柔和的背景色和边框
        self.setStyleSheet("""
            StatusBar {
                background-color: rgba(245, 245, 245, 0.9);
                border-bottom: 1px solid #E0E0E0;
                padding: 2px 0;
            }
            TransparentPushButton {
                border-radius: 4px;
                padding: 4px 8px;
            }
            TransparentPushButton:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
        """)

    def __handel_setting_changed(self):
         self.param_changed.emit({
            "channel":self.channel.currentText().split(":")[1].strip(),
        })
    
    def __handle_channel_menu_triggered(self,text:str):
        logging.info(text)
        self.__handel_setting_changed()


    def __init__(self):
        super().__init__()
        self.setupUi()


    def handle_server_connected(self):
        self.connect_status.setText("服务器状态: 已连接")
        self.connect_status.setIcon(FluentIcon.CLOUD.icon(color=QColor("green")))

    def handle_server_disconnected(self):
        self.connect_status.setText("服务器状态: 未连接")
        self.connect_status.setIcon(FluentIcon.CLOUD.icon(color=QColor("red")))


class StatusPanel(GroupHeaderCardWidget):
    """系统状态面板 - 使用 qfluentwidgets 组件的紧凑版"""
    def __init__(self):
        super().__init__()
        self._value_labels = {}  # 存储值标签的引用
        self.initUI()

    def initUI(self):
        self.setTitle("设备状态")
        self.setupUi()

    def _create_row(self, items: list) -> QHBoxLayout:
        """创建一行数据，items: [(label, key), ...]"""
        row = QHBoxLayout()
        row.setSpacing(4)
        row.setContentsMargins(10, 0, 10, 0)

        for i, (label_text, key, default_value) in enumerate(items):
            if i > 0:
                row.addSpacing(12)

            # 标签 (使用 CaptionLabel，颜色较淡)
            label = CaptionLabel(label_text)
            label.setFixedWidth(36)
            row.addWidget(label)

            # 值 (使用 BodyLabel)
            value_label = BodyLabel(default_value)
            value_label.setFixedWidth(70)
            row.addWidget(value_label)

            # 保存引用
            self._value_labels[key] = value_label

        row.addStretch()
        return row

    def setupUi(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)

        # 系统状态 - 每行2-3个数据
        # 第1行: CPU, 内存, 磁盘
        row1 = self._create_row([
            ("CPU", "cpu", "0%"),
            ("内存", "memory", "0%"),
            ("磁盘", "disk", "0%"),
        ])
        main_layout.addLayout(row1)

        # 第2行: 信号, 延迟, 运行
        row2 = self._create_row([
            ("信号", "signal", "0%"),
            ("延迟", "latency", "--"),
            ("运行", "uptime", "00:00:00"),
        ])
        main_layout.addLayout(row2)

        # 第3行: 电压, 电量, 温度
        row3 = self._create_row([
            ("电压", "voltage", "0.0V"),
            ("电量", "capacity", "0%"),
            ("温度", "temp", "--"),
        ])
        main_layout.addLayout(row3)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFixedHeight(1)
        main_layout.addWidget(line)

        # 传感器区域
        sensor_data_layout = QVBoxLayout()
        sensor_data_layout.setSpacing(6)

        # 加速度
        accel_row = QHBoxLayout()
        accel_row.setSpacing(4)
        accel_row.setContentsMargins(10,0,10,0)
        accel_label = CaptionLabel("加速度")
        accel_label.setFixedWidth(48)
        accel_row.addWidget(accel_label)
        self._value_labels["accel"] = BodyLabel("X:-- Y:-- Z:--")
        accel_row.addWidget(self._value_labels["accel"])
        accel_row.addStretch()
        sensor_data_layout.addLayout(accel_row)

        # 角速度
        gyro_row = QHBoxLayout()
        gyro_row.setSpacing(4)
        gyro_row.setContentsMargins(10,0,10,0)
        gyro_label = CaptionLabel("角速度")
        gyro_label.setFixedWidth(48)
        gyro_row.addWidget(gyro_label)
        self._value_labels["gyro"] = BodyLabel("X:-- Y:-- Z:--")
        gyro_row.addWidget(self._value_labels["gyro"])
        gyro_row.addStretch()
        sensor_data_layout.addLayout(gyro_row)

        # GPS
        gps_row = QHBoxLayout()
        gps_row.setSpacing(4)
        gps_row.setContentsMargins(10,0,10,0)
        gps_label = CaptionLabel("GPS")
        gps_label.setFixedWidth(48)
        gps_row.addWidget(gps_label)
        self._value_labels["gps"] = BodyLabel("--")
        gps_row.addWidget(self._value_labels["gps"])
        gps_row.addStretch()
        sensor_data_layout.addLayout(gps_row)

        sensor_data_layout.addStretch()

        main_layout.addLayout(sensor_data_layout)

        self.vBoxLayout.addLayout(main_layout)

    def _update_value(self, key: str, value: str):
        """更新指定key的值"""
        if key in self._value_labels:
            self._value_labels[key].setText(value)

    # 更新方法
    def update_cpu(self, usage: float):
        self._update_value('cpu', f"{usage:.1f}%")

    def update_memory(self, usage: float):
        self._update_value('memory', f"{usage:.1f}%")

    def update_signal_strength(self, strength: float):
        self._update_value('signal', f"{strength:.0f}%")

    def update_battery_voltage(self, voltage: float):
        self._update_value('voltage', f"{voltage:.1f}V")

    def update_battery_capacity(self, capacity: float):
        self._update_value('capacity', f"{capacity:.0f}%")

    def update_temperature(self, temp: float):
        self._update_value('temp', f"{temp:.1f}C")

    def update_latency(self, latency: int):
        self._update_value('latency', f"{latency}ms")

    def update_uptime(self, hours: int, minutes: int, seconds: int):
        self._update_value('uptime', f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def update_disk_usage(self, usage: float):
        self._update_value('disk', f"{usage:.1f}%")

    def update_acceleration(self, x: float, y: float, z: float):
        self._update_value('accel', f"X:{x:.1f} Y:{y:.1f} Z:{z:.1f}")

    def update_angular_velocity(self, x: float, y: float, z: float):
        self._update_value('gyro', f"X:{x:.1f} Y:{y:.1f} Z:{z:.1f}")

    def update_gps(self, latitude: float, longitude: float, altitude: Optional[float] = None):
        if altitude is not None:
            self._update_value('gps', f"{latitude:.4f}, {longitude:.4f}, {altitude:.0f}m")
        else:
            self._update_value('gps', f"{latitude:.4f}, {longitude:.4f}")




if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    status_panel = StatusPanel()
    status_panel.show()
    sys.exit(app.exec_())