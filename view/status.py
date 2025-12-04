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
        self.signal=TransparentPushButton(FluentIcon.WIFI.icon(color=QColor("green")),"10 ms")
        self.upload=TransparentPushButton(FluentIcon.UP.icon(),"100 kb/s")
        self.download=TransparentPushButton(FluentIcon.DOWN.icon(),"99 kb/s")
        self.date=TransparentPushButton(FluentIcon.DATE_TIME.icon(),"2025/02/09 21:44:00")
        self.channel=ComboBox()
        self.channel.addItems(["线路: 上海","线路: 北京"])
        self.channel.setCurrentIndex(0)
        self.channel.currentTextChanged.connect(self.__handle_channel_menu_triggered)
        self.connect_status=TransparentPushButton(FluentIcon.CLOUD.icon(color=QColor("red")),"服务器状态: 未连接")
        
      
        self.battery=TransparentPushButton(QIcon("assets/svg/battery-full.svg"),"100%")

        self.timer=QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        self.sync=TransparentToolButton(FluentIcon.SYNC.icon())

        layout.addWidget(self.connect_status)
        layout.addWidget(self.signal)
        layout.addWidget(self.battery)

        layout.addWidget(self.upload)
        layout.addWidget(self.download)

        layout.addWidget(self.date)
        layout.addWidget(self.channel)
        layout.addWidget(self.sync)
        
        
        self.setLayout(layout)
        self.setStyleSheet("background-color: rgb(255,0,0)")

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
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 标签行
        label_layout = QHBoxLayout()
        label_layout.setContentsMargins(0, 0, 0, 0)
        if self.icon:
            try:
                icon_label = QLabel()
                icon_label.setPixmap(self.icon.icon().pixmap(16, 16))
                icon_label.setFixedSize(16, 16)
                label_layout.addWidget(icon_label)
            except (AttributeError, TypeError) as e:
                # 如果图标不存在或无法加载，跳过图标显示
                logging.warning(f"Failed to load icon: {e}")
        
        self.label = BodyLabel(self.label_text)
        label_layout.addWidget(self.label)
        label_layout.addStretch()
        
        # 值显示
        self.value_label = BodyLabel("--")
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label_layout.addWidget(self.value_label)
        
        layout.addLayout(label_layout)
        
        # 进度条容器 - 始终占用固定空间以保持布局一致性
        self.progress_container = QWidget()
        progress_container_layout = QVBoxLayout()
        progress_container_layout.setContentsMargins(0, 0, 0, 0)
        progress_container_layout.setSpacing(0)
        
        self.progress_bar = ProgressBar(useAni=True)
        self.progress_bar.setFixedHeight(4)
        progress_container_layout.addWidget(self.progress_bar)
        
        self.progress_container.setLayout(progress_container_layout)
        self.progress_container.setFixedHeight(4)  # 固定高度，保持布局一致
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
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 标题
        title_label = SubtitleLabel(self.title)
        layout.addWidget(title_label)
        
        # 三个轴的数据
        axes_layout = QHBoxLayout()
        
        self.x_label = BodyLabel("X: --")
        self.y_label = BodyLabel("Y: --")
        self.z_label = BodyLabel("Z: --")
        
        axes_layout.addWidget(self.x_label)
        axes_layout.addWidget(self.y_label)
        axes_layout.addWidget(self.z_label)
        
        layout.addLayout(axes_layout)
        self.setLayout(layout)
    
    def setValues(self, x: float, y: float, z: float):
        """设置三个轴的值"""
        self.x_label.setText(f"X: {x:.2f}")
        self.y_label.setText(f"Y: {y:.2f}")
        self.z_label.setText(f"Z: {z:.2f}")


class GPSDataWidget(QWidget):
    """GPS/经纬度传感器数据显示组件"""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.setupUi()
    
    def setupUi(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 标题
        title_label = SubtitleLabel(self.title)
        layout.addWidget(title_label)
        
        # 经纬度和海拔数据
        data_layout = QVBoxLayout()
        data_layout.setSpacing(3)
        
        self.latitude_label = BodyLabel("纬度: --")
        self.longitude_label = BodyLabel("经度: --")
        self.altitude_label = BodyLabel("海拔: --")
        
        data_layout.addWidget(self.latitude_label)
        data_layout.addWidget(self.longitude_label)
        data_layout.addWidget(self.altitude_label)
        
        layout.addLayout(data_layout)
        self.setLayout(layout)
    
    def setValues(self, latitude: float, longitude: float, altitude: Optional[float] = None):
        """设置GPS数据
        Args:
            latitude: 纬度（度）
            longitude: 经度（度）
            altitude: 海拔（米），可选
        """
        self.latitude_label.setText(f"纬度: {latitude:.6f}°")
        self.longitude_label.setText(f"经度: {longitude:.6f}°")
        if altitude is not None:
            self.altitude_label.setText(f"海拔: {altitude:.2f} m")
        else:
            self.altitude_label.setText("海拔: --")


class SpeedOdometerWidget(QWidget):
    """时速和里程显示组件"""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.setupUi()
    
    def setupUi(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 标题
        title_label = SubtitleLabel(self.title)
        layout.addWidget(title_label)
        
        # 时速和里程数据
        data_layout = QVBoxLayout()
        data_layout.setSpacing(3)
        
        self.speed_label = BodyLabel("时速: --")
        self.odometer_label = BodyLabel("里程: --")
        
        data_layout.addWidget(self.speed_label)
        data_layout.addWidget(self.odometer_label)
        
        layout.addLayout(data_layout)
        self.setLayout(layout)
    
    def setValues(self, speed: float, odometer: float):
        """设置时速和里程数据
        Args:
            speed: 时速（km/h）
            odometer: 里程（km）
        """
        self.speed_label.setText(f"时速: {speed:.2f} km/h")
        self.odometer_label.setText(f"里程: {odometer:.2f} km")


class StatusPanel(GroupHeaderCardWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        self.setTitle("系统状态")
        self.setupUi()
    
    def setupUi(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # 第一行：CPU 利用率、内存利用率
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(10)
        
        self.cpu_item = StatusItem("CPU 利用率", FluentIcon.DEVELOPER_TOOLS)
        self.cpu_item.setValue("0%", 0)
        row1_layout.addWidget(self.cpu_item)
        
        self.memory_item = StatusItem("内存利用率", FluentIcon.SETTING)
        self.memory_item.setValue("0%", 0)
        row1_layout.addWidget(self.memory_item)
        
        main_layout.addLayout(row1_layout)
        
        # 第二行：信号强度、电池电压
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(10)
        
        self.signal_item = StatusItem("信号强度", FluentIcon.WIFI)
        self.signal_item.setValue("0%", 0)
        row2_layout.addWidget(self.signal_item)
        
        self.battery_voltage_item = StatusItem("电池电压", None)
        self.battery_voltage_item.setValue("0.0 V")
        row2_layout.addWidget(self.battery_voltage_item)
        
        main_layout.addLayout(row2_layout)
        
        # 第三行：电池容量、系统温度
        row3_layout = QHBoxLayout()
        row3_layout.setSpacing(10)
        
        self.battery_capacity_item = StatusItem("电池容量", None)
        self.battery_capacity_item.setValue("0%", 0)
        row3_layout.addWidget(self.battery_capacity_item)
        
        self.temperature_item = StatusItem("系统温度", None)
        self.temperature_item.setValue("--°C")
        row3_layout.addWidget(self.temperature_item)
        
        main_layout.addLayout(row3_layout)
        
        # 第四行：网络延迟、运行时间
        row4_layout = QHBoxLayout()
        row4_layout.setSpacing(10)
        
        self.latency_item = StatusItem("网络延迟", FluentIcon.WIFI)
        self.latency_item.setValue("-- ms")
        row4_layout.addWidget(self.latency_item)
        
        self.uptime_item = StatusItem("运行时间", FluentIcon.DATE_TIME)
        self.uptime_item.setValue("00:00:00")
        row4_layout.addWidget(self.uptime_item)
        
        main_layout.addLayout(row4_layout)
        
        # 第五行：磁盘使用率、（预留位置）
        row5_layout = QHBoxLayout()
        row5_layout.setSpacing(10)
        
        self.disk_item = StatusItem("磁盘使用", FluentIcon.SETTING)
        self.disk_item.setValue("0%", 0)
        row5_layout.addWidget(self.disk_item)
        
        # 预留位置，可以添加其他状态项
        row5_layout.addStretch()
        
        main_layout.addLayout(row5_layout)
        
        # 传感器数据部分
        sensors_layout = QVBoxLayout()
        sensors_layout.setSpacing(10)
        
        sensors_title = SubtitleLabel("传感器数据")
        sensors_layout.addWidget(sensors_title)
        
        # 第一行：加速度和角速度传感器
        sensors_grid = QHBoxLayout()
        sensors_grid.setSpacing(10)
        
        # 加速度传感器
        self.acceleration_widget = SensorDataWidget("加速度 (m/s²)")
        sensors_grid.addWidget(self.acceleration_widget)
        
        # 角速度传感器
        self.angular_velocity_widget = SensorDataWidget("角速度 (rad/s)")
        sensors_grid.addWidget(self.angular_velocity_widget)
        
        sensors_layout.addLayout(sensors_grid)
        
        # 第二行：GPS/经纬度传感器、时速和里程
        gps_layout = QHBoxLayout()
        gps_layout.setSpacing(10)
        
        # GPS/经纬度传感器
        self.gps_widget = GPSDataWidget("GPS 位置")
        gps_layout.addWidget(self.gps_widget)
        
        # 时速和里程
        self.speed_odometer_widget = SpeedOdometerWidget("速度里程")
        gps_layout.addWidget(self.speed_odometer_widget)
        
        sensors_layout.addLayout(gps_layout)
        main_layout.addLayout(sensors_layout)
        
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