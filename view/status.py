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
        if self.icon:
            try:
                icon_label = QLabel()
                icon_label.setPixmap(self.icon.icon().pixmap(16, 16))
                label_layout.addWidget(icon_label)
            except (AttributeError, TypeError) as e:
                # 如果图标不存在或无法加载，跳过图标显示
                logging.warning(f"Failed to load icon: {e}")
        
        self.label = BodyLabel(self.label_text)
        label_layout.addWidget(self.label)
        label_layout.addStretch()
        
        # 值显示
        self.value_label = BodyLabel("--")
        self.value_label.setAlignment(Qt.AlignRight)
        label_layout.addWidget(self.value_label)
        
        layout.addLayout(label_layout)
        
        # 进度条（如果需要）
        self.progress_bar = ProgressBar(useAni=True)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
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
        
        # 第一行：系统资源（CPU、内存）
        resources_layout = QHBoxLayout()
        resources_layout.setSpacing(10)
        
        # CPU 利用率
        self.cpu_item = StatusItem("CPU 利用率", FluentIcon.DEVELOPER_TOOLS)
        self.cpu_item.setValue("0%", 0)
        resources_layout.addWidget(self.cpu_item)
        
        # 内存利用率
        self.memory_item = StatusItem("内存利用率", FluentIcon.SETTING)
        self.memory_item.setValue("0%", 0)
        resources_layout.addWidget(self.memory_item)
        
        main_layout.addLayout(resources_layout)
        
        # 第二行：网络和电池
        network_battery_layout = QHBoxLayout()
        network_battery_layout.setSpacing(10)
        
        # 信号强度
        self.signal_item = StatusItem("信号强度", FluentIcon.WIFI)
        self.signal_item.setValue("0%", 0)
        network_battery_layout.addWidget(self.signal_item)
        
        # 电池电压
        self.battery_voltage_item = StatusItem("电池电压", None)
        self.battery_voltage_item.setValue("0.0 V")
        network_battery_layout.addWidget(self.battery_voltage_item)
        
        # 电池容量
        self.battery_capacity_item = StatusItem("电池容量", None)
        self.battery_capacity_item.setValue("0%", 0)
        network_battery_layout.addWidget(self.battery_capacity_item)
        
        main_layout.addLayout(network_battery_layout)
        
        # 第三行：传感器数据
        sensors_layout = QVBoxLayout()
        sensors_layout.setSpacing(10)
        
        sensors_title = SubtitleLabel("传感器数据")
        sensors_layout.addWidget(sensors_title)
        
        sensors_grid = QHBoxLayout()
        sensors_grid.setSpacing(10)
        
        # 加速度传感器
        self.acceleration_widget = SensorDataWidget("加速度 (m/s²)")
        sensors_grid.addWidget(self.acceleration_widget)
        
        # 角速度传感器
        self.angular_velocity_widget = SensorDataWidget("角速度 (rad/s)")
        sensors_grid.addWidget(self.angular_velocity_widget)
        
        sensors_layout.addLayout(sensors_grid)
        main_layout.addLayout(sensors_layout)
        
        # 第四行：其他系统信息
        other_info_layout = QVBoxLayout()
        other_info_layout.setSpacing(10)
        
        other_title = SubtitleLabel("其他信息")
        other_info_layout.addWidget(other_title)
        
        other_grid = QHBoxLayout()
        other_grid.setSpacing(10)
        
        # 系统温度
        self.temperature_item = StatusItem("系统温度", None)
        self.temperature_item.setValue("--°C")
        other_grid.addWidget(self.temperature_item)
        
        # 网络延迟
        self.latency_item = StatusItem("网络延迟", FluentIcon.WIFI)
        self.latency_item.setValue("-- ms")
        other_grid.addWidget(self.latency_item)
        
        # 运行时间
        self.uptime_item = StatusItem("运行时间", FluentIcon.DATE_TIME)
        self.uptime_item.setValue("00:00:00")
        other_grid.addWidget(self.uptime_item)
        
        # 磁盘使用率
        self.disk_item = StatusItem("磁盘使用", FluentIcon.SETTING)
        self.disk_item.setValue("0%", 0)
        other_grid.addWidget(self.disk_item)
        
        other_info_layout.addLayout(other_grid)
        main_layout.addLayout(other_info_layout)
        
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