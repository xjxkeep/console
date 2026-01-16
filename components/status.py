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
    ProgressBar,
    SubtitleLabel,
    CardWidget
)


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
        layout.setContentsMargins(10, 5, 10, 5)  # 调整边距
        layout.setHorizontalSpacing(15)  # 增加水平间距
        layout.setVerticalSpacing(5)  # 设置垂直间距
        
        # 创建组件并设置统一的样式
        self.signal=TransparentPushButton(FluentIcon.WIFI.icon(color=QColor("#4CAF50")),"10 ms")
        self.signal.setMinimumWidth(80)
        
        self.upload=TransparentPushButton(FluentIcon.UP.icon(color=QColor("#2196F3")),"100 kb/s")
        self.upload.setMinimumWidth(100)
        
        self.download=TransparentPushButton(FluentIcon.DOWN.icon(color=QColor("#FF9800")),"99 kb/s")
        self.download.setMinimumWidth(100)
        
        self.date=TransparentPushButton(FluentIcon.DATE_TIME.icon(color=QColor("#607D8B")),"2025/02/09 21:44:00")
        self.date.setMinimumWidth(180)
        
        self.channel=ComboBox()
        self.channel.addItems(["线路: 上海","线路: 北京"])
        self.channel.setCurrentIndex(0)
        self.channel.setMinimumWidth(120)
        self.channel.setStyleSheet("""
            QComboBox {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: rgba(255, 255, 255, 0.8);
            }
            QComboBox:hover {
                border-color: #BDBDBD;
            }
        """)
        self.channel.currentTextChanged.connect(self.__handle_channel_menu_triggered)
        
        self.connect_status=TransparentPushButton(FluentIcon.CLOUD.icon(color=QColor("#F44336")),"服务器状态: 未连接")
        self.connect_status.setMinimumWidth(150)
        
        self.battery=TransparentPushButton(QIcon("assets/svg/battery-full.svg"),"100%")
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




class StatusItem(QWidget):
    """单个状态项组件"""
    def __init__(self, label: str, icon: FluentIcon = None, parent=None):
        super().__init__(parent)
        self.label_text = label
        self.icon = icon
        self.setupUi()
    
    def setupUi(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 顶部行：图标和标签
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)
        
        if self.icon:
            try:
                icon_label = QLabel()
                # 稍微增大图标
                icon_label.setPixmap(self.icon.icon().pixmap(20, 20))
                icon_label.setFixedSize(20, 20)
                top_layout.addWidget(icon_label)
            except (AttributeError, TypeError) as e:
                logging.warning(f"Failed to load icon: {e}")
        
        self.label = BodyLabel(self.label_text)
        top_layout.addWidget(self.label)
        top_layout.addStretch()
        
        layout.addLayout(top_layout)
        
        # 中间：值显示
        self.value_label = BodyLabel("--")
        self.value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.value_label)
        
        # 底部：进度条
        self.progress_container = QWidget()
        progress_container_layout = QVBoxLayout()
        progress_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.progress_bar = ProgressBar(useAni=True)
        self.progress_bar.setFixedHeight(4)  # 更细的进度条
        progress_container_layout.addWidget(self.progress_bar)
        
        self.progress_container.setLayout(progress_container_layout)
        # 只有在需要时才显示容器，或者保持占位但不可见
        # 这里我们保持它在布局中，但初始高度可能为0或者隐藏
        # 为了布局对齐，建议保持固定高度
        self.progress_container.setFixedHeight(4)
        layout.addWidget(self.progress_container)
        
        self.setLayout(layout)
    
    def setValue(self, value: str, progress: Optional[int] = None):
        """设置值，如果提供 progress，则显示进度条"""
        self.value_label.setText(value)
        if progress is not None:
            self.progress_bar.setValue(progress)
            self.progress_bar.setVisible(True)
        else:
            self.progress_bar.setVisible(False)


class SensorDataWidget(QWidget):
    """传感器数据显示组件（加速度/角速度）"""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.setupUi()
    
    def setupUi(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 标题
        title_label = SubtitleLabel(self.title)
        layout.addWidget(title_label)
        
        # 三个轴的数据 Grid
        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(20)
        grid_layout.setVerticalSpacing(8)
        
        # X Axis
        grid_layout.addWidget(BodyLabel("X"), 0, 0)
        self.x_label = BodyLabel("--")
        grid_layout.addWidget(self.x_label, 0, 1)
        
        # Y Axis
        grid_layout.addWidget(BodyLabel("Y"), 1, 0)
        self.y_label = BodyLabel("--")
        grid_layout.addWidget(self.y_label, 1, 1)
        
        # Z Axis
        grid_layout.addWidget(BodyLabel("Z"), 2, 0)
        self.z_label = BodyLabel("--")
        grid_layout.addWidget(self.z_label, 2, 1)
        
        layout.addLayout(grid_layout)
        self.setLayout(layout)
    
    def setValues(self, x: float, y: float, z: float):
        """设置三个轴的值"""
        self.x_label.setText(f"{x:.2f}")
        self.y_label.setText(f"{y:.2f}")
        self.z_label.setText(f"{z:.2f}")


class GPSDataWidget(QWidget):
    """GPS/经纬度传感器数据显示组件"""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.setupUi()
    
    def setupUi(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 标题
        title_label = SubtitleLabel(self.title)
        layout.addWidget(title_label)
        
        # 经纬度和海拔数据 Grid
        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(20)
        grid_layout.setVerticalSpacing(8)
        
        # Latitude
        grid_layout.addWidget(BodyLabel("纬度"), 0, 0)
        self.latitude_label = BodyLabel("--")
        grid_layout.addWidget(self.latitude_label, 0, 1)
        
        # Longitude
        grid_layout.addWidget(BodyLabel("经度"), 1, 0)
        self.longitude_label = BodyLabel("--")
        grid_layout.addWidget(self.longitude_label, 1, 1)
        
        # Altitude
        grid_layout.addWidget(BodyLabel("海拔"), 2, 0)
        self.altitude_label = BodyLabel("--")
        grid_layout.addWidget(self.altitude_label, 2, 1)
        
        layout.addLayout(grid_layout)
        self.setLayout(layout)
    
    def setValues(self, latitude: float, longitude: float, altitude: Optional[float] = None):
        """设置GPS数据"""
        self.latitude_label.setText(f"{latitude:.6f}°")
        self.longitude_label.setText(f"{longitude:.6f}°")
        if altitude is not None:
            self.altitude_label.setText(f"{altitude:.2f} m")
        else:
            self.altitude_label.setText("--")


class SpeedOdometerWidget(QWidget):
    """时速和里程显示组件"""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.setupUi()
    
    def setupUi(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 标题
        title_label = SubtitleLabel(self.title)
        layout.addWidget(title_label)
        
        # 时速和里程数据 Grid
        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(20)
        grid_layout.setVerticalSpacing(8)
        
        # Speed
        grid_layout.addWidget(BodyLabel("时速"), 0, 0)
        self.speed_label = BodyLabel("--")
        grid_layout.addWidget(self.speed_label, 0, 1)
        
        # Odometer
        grid_layout.addWidget(BodyLabel("里程"), 1, 0)
        self.odometer_label = BodyLabel("--")
        grid_layout.addWidget(self.odometer_label, 1, 1)
        
        layout.addLayout(grid_layout)
        self.setLayout(layout)
    
    def setValues(self, speed: float, odometer: float):
        """设置时速和里程数据"""
        self.speed_label.setText(f"{speed:.2f} km/h")
        self.odometer_label.setText(f"{odometer:.2f} km")


class StatusPanel(GroupHeaderCardWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        self.setTitle("系统状态")
        self.setupUi()
    
    def setupUi(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)
        
        # 主要状态网格 (3列布局)
        status_grid = QGridLayout()
        status_grid.setSpacing(20)
        
        # 1. CPU
        self.cpu_item = StatusItem("CPU 利用率", FluentIcon.DEVELOPER_TOOLS)
        self.cpu_item.setValue("0%", 0)
        status_grid.addWidget(self.cpu_item, 0, 0)
        
        # 2. Memory
        self.memory_item = StatusItem("内存利用率", FluentIcon.SETTING)
        self.memory_item.setValue("0%", 0)
        status_grid.addWidget(self.memory_item, 0, 1)
        
        # 3. Disk
        self.disk_item = StatusItem("磁盘使用", FluentIcon.SETTING)
        self.disk_item.setValue("0%", 0)
        status_grid.addWidget(self.disk_item, 0, 2)
        
        # 4. Signal
        self.signal_item = StatusItem("信号强度", FluentIcon.WIFI)
        self.signal_item.setValue("0%", 0)
        status_grid.addWidget(self.signal_item, 1, 0)
        
        # 5. Latency
        self.latency_item = StatusItem("网络延迟", FluentIcon.WIFI)
        self.latency_item.setValue("-- ms")
        status_grid.addWidget(self.latency_item, 1, 1)
        
        # 6. Uptime
        self.uptime_item = StatusItem("运行时间", FluentIcon.DATE_TIME)
        self.uptime_item.setValue("00:00:00")
        status_grid.addWidget(self.uptime_item, 1, 2)
        
        # 7. Battery Voltage
        self.battery_voltage_item = StatusItem("电池电压", None)
        self.battery_voltage_item.setValue("0.0 V")
        status_grid.addWidget(self.battery_voltage_item, 2, 0)
        
        # 8. Battery Capacity
        self.battery_capacity_item = StatusItem("电池容量", None)
        self.battery_capacity_item.setValue("0%", 0)
        status_grid.addWidget(self.battery_capacity_item, 2, 1)
        
        # 9. Temperature
        self.temperature_item = StatusItem("系统温度", None)
        self.temperature_item.setValue("--°C")
        status_grid.addWidget(self.temperature_item, 2, 2)
        
        main_layout.addLayout(status_grid)
        
        # 传感器数据部分
        sensors_title = SubtitleLabel("传感器数据")
        main_layout.addWidget(sensors_title)
        
        # 传感器网格 (2列布局)
        sensors_grid = QGridLayout()
        sensors_grid.setSpacing(20)
        
        # 加速度
        self.acceleration_widget = SensorDataWidget("加速度 (m/s²)")
        sensors_grid.addWidget(self.acceleration_widget, 0, 0)
        
        # 角速度
        self.angular_velocity_widget = SensorDataWidget("角速度 (rad/s)")
        sensors_grid.addWidget(self.angular_velocity_widget, 0, 1)
        
        # GPS
        self.gps_widget = GPSDataWidget("GPS 位置")
        sensors_grid.addWidget(self.gps_widget, 1, 0)
        
        # Speed/Odometer
        self.speed_odometer_widget = SpeedOdometerWidget("速度里程")
        sensors_grid.addWidget(self.speed_odometer_widget, 1, 1)
        
        main_layout.addLayout(sensors_grid)
        
        # 添加弹性空间
        main_layout.addStretch()
        
        self.vBoxLayout.addLayout(main_layout)
    
    # 以下方法用于更新数据（暂时只搭建界面，数据更新逻辑后续实现）
    def update_cpu(self, usage: float):
        """更新 CPU 利用率 (0-100)"""
        self.cpu_item.setValue(f"{usage:.1f}%", int(usage))
    
    def update_memory(self, usage: float):
        """更新内存利用率 (0-100)"""
        self.memory_item.setValue(f"{usage:.1f}%", int(usage))
    
    def update_signal_strength(self, strength: float):
        """更新信号强度 (0-100)"""
        self.signal_item.setValue(f"{strength:.1f}%", int(strength))
    
    def update_battery_voltage(self, voltage: float):
        """更新电池电压 (V)"""
        self.battery_voltage_item.setValue(f"{voltage:.2f} V")
    
    def update_battery_capacity(self, capacity: float):
        """更新电池容量 (0-100)"""
        self.battery_capacity_item.setValue(f"{capacity:.1f}%", int(capacity))
    
    def update_acceleration(self, x: float, y: float, z: float):
        """更新加速度数据 (m/s²)"""
        self.acceleration_widget.setValues(x, y, z)
    
    def update_angular_velocity(self, x: float, y: float, z: float):
        """更新角速度数据 (rad/s)"""
        self.angular_velocity_widget.setValues(x, y, z)
    
    def update_temperature(self, temp: float):
        """更新系统温度 (°C)"""
        self.temperature_item.setValue(f"{temp:.1f}°C")
    
    def update_latency(self, latency: int):
        """更新网络延迟 (ms)"""
        self.latency_item.setValue(f"{latency} ms")
    
    def update_uptime(self, hours: int, minutes: int, seconds: int):
        """更新运行时间"""
        self.uptime_item.setValue(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def update_disk_usage(self, usage: float):
        """更新磁盘使用率 (0-100)"""
        self.disk_item.setValue(f"{usage:.1f}%", int(usage))
    
    def update_gps(self, latitude: float, longitude: float, altitude: Optional[float] = None):
        """更新GPS/经纬度数据
        Args:
            latitude: 纬度（度）
            longitude: 经度（度）
            altitude: 海拔（米），可选
        """
        self.gps_widget.setValues(latitude, longitude, altitude)
    
    def update_speed_odometer(self, speed: float, odometer: float):
        """更新时速和里程数据
        Args:
            speed: 时速（km/h）
            odometer: 里程（km）
        """
        self.speed_odometer_widget.setValues(speed, odometer)




if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    status_panel = StatusPanel()
    status_panel.show()
    sys.exit(app.exec_())