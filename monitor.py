
import logging

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import *
import numpy as np
from qfluentwidgets import PushButton

from components.channel import ChannelGroup,ChannelDisp
from pkg.model import Setting
from protocol.highway_pb2 import Device, DeviceParam, Video
from components.imu import IMUWidget
from components.status import StatusBar, StatusPanel, DashboardPanel
from components.video import VideoPanel
from components.wave import WaveformWidget
from components.controller import ControlPanel
from components.map import MapWidget


# TODO imu 显示会导致无法resize窗口
class Monitor(QWidget):
    startSignal=pyqtSignal()
    sendTestVideoSignal=pyqtSignal()    
    sendTestDatagramSignal=pyqtSignal()
    sendTestCodecSignal=pyqtSignal()
    param_changed=pyqtSignal(dict)
    def setupUi(self):
        self.setObjectName("Monitor")
        self.resize(800,600)
        
        # 使用QGridLayout来实现IMU控件在display右下角的布局
        
        self.statusBar = StatusBar()
        

 
        
        self.display =VideoPanel()
        self.display.param_changed.connect(self.param_changed)
  
        self.waveform = WaveformWidget()
        
        
  
        self.startButton = PushButton("连接服务器")
        self.startButton.clicked.connect(self.conncet_server)
        self.sendTestVideoButton = PushButton("发送摄像头视频(stream)")
        self.sendTestDatagramButton = PushButton("发送摄像头视频(datagram)")
        self.sendTestCodecButton = PushButton("测试摄像头视频编解码(codec)")
        self.sendTestVideoButton.clicked.connect(self.sendTestVideoSignal.emit)
        self.sendTestDatagramButton.clicked.connect(self.sendTestDatagramSignal.emit)
        self.sendTestCodecButton.clicked.connect(self.sendTestCodecSignal.emit)
        
        self.startButton.setEnabled(True)
        self.sendTestVideoButton.setEnabled(False)
        self.sendTestDatagramButton.setEnabled(False)
        self.sendTestCodecButton.setEnabled(False)
        
        buttonLayout=QHBoxLayout()
        buttonLayout.addWidget(self.startButton)
        buttonLayout.addWidget(self.sendTestVideoButton)
        buttonLayout.addWidget(self.sendTestDatagramButton)
        buttonLayout.addWidget(self.sendTestCodecButton)
        
        
        self.controlPanel=ControlPanel()

        # self.channelGroup=ChannelGroup(self.setting.channel_count,self.setting.channels,showFineTune=False,showReverse=False)
        self.statusPanel=StatusPanel()
        self.dashboardPanel=DashboardPanel()
        self.mapWidget=MapWidget()

        # 设置右侧面板宽度一致
        panel_width = 350
        self.controlPanel.setFixedWidth(panel_width)
        self.mapWidget.setFixedWidth(panel_width)

        # 设置组件可以垂直扩展
        self.controlPanel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # 右侧面板：地图 + 实时控制
        right_panel = QWidget()
        right_panel.setFixedWidth(panel_width)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        right_layout.addWidget(self.mapWidget)
        right_layout.addWidget(self.controlPanel, 1)
        right_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # 左侧面板：视频 + 状态仪表盘 + 按钮（垂直排列）
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # 视频面板
        self.display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.display, 1)  # stretch=1，占用剩余空间

        # 设备状态 + 仪表盘 水平排列
        status_row = QWidget()
        status_row_layout = QHBoxLayout(status_row)
        status_row_layout.setContentsMargins(0, 0, 0, 0)
        status_row_layout.setSpacing(10)
        status_row_layout.addWidget(self.statusPanel)
        status_row_layout.addWidget(self.dashboardPanel)
        left_layout.addWidget(status_row)

        # 按钮行
        left_layout.addLayout(buttonLayout)

        left_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 主布局
        main_layout = QGridLayout()
        main_layout.addWidget(self.statusBar, 0, 0, 1, 2)
        main_layout.addWidget(left_panel, 1, 0)
        main_layout.addWidget(right_panel, 1, 1)
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 0)
        main_layout.setRowStretch(0, 0)
        main_layout.setRowStretch(1, 1)
        self.setLayout(main_layout)

        self.__frame = None



    def handle_joystick_changed(self,x:float,y:float):
        self.channelDisp.update_channel_value(1,50+int(x*50))
        self.channelDisp.update_channel_value(0,50+int(y*50))

    def __init__(self,setting:Setting,parent=None) -> None:
        super().__init__(parent)
        self.setting=setting
        self.setupUi()
        self.latency=0
        self.statusBar.param_changed.connect(self.param_changed)
    
    def conncet_server(self):
        self.startButton.setDisabled(True)
        self.sendTestCodecButton.setEnabled(True)
        self.sendTestDatagramButton.setEnabled(True)
        self.sendTestVideoButton.setEnabled(True)
        self.startSignal.emit()
        
        
    
    def update_device_param(self,data:DeviceParam):
        """更新设备参数数据并显示在界面上"""
        try:
            # 更新 CPU 利用率
            self.statusPanel.update_cpu(data.cpu_usage)
            
            # 更新内存利用率
            self.statusPanel.update_memory(data.memory_usage)

            # 更新磁盘使用率
            self.statusPanel.update_disk_usage(data.disk_usage)

            # 更新信号强度 (将 dBm 转换为百分比)
            # RSSI 通常在 -30 dBm (最强) 到 -120 dBm (最弱) 之间
            if data.rssi_dbm >= -30:
                signal_strength = 100
            elif data.rssi_dbm <= -120:
                signal_strength = 0
            else:
                signal_strength = (data.rssi_dbm + 120) / 0.9
            self.statusPanel.update_signal_strength(signal_strength)
            
            # 更新电池电压
            self.statusPanel.update_battery_voltage(data.voltage)
            
            # 更新系统温度
            self.statusPanel.update_temperature(data.temperature)
            
            # 更新加速度数据
            if data.imu_param:
                self.statusPanel.update_acceleration(
                    data.imu_param.acceleration_x,
                    data.imu_param.acceleration_y,
                    data.imu_param.acceleration_z
                )
                
                # 更新角速度数据
                self.statusPanel.update_angular_velocity(
                    data.imu_param.gyroscope_x,
                    data.imu_param.gyroscope_y,
                    data.imu_param.gyroscope_z
                )

                # 更新姿态球
                self.dashboardPanel.update_attitude(data.imu_param)
            
        except Exception as e:
            logging.error(f"更新设备参数数据时出错: {e}")

    def update_wave_form(self,value:np.ndarray):
        self.waveform.set_data(value)
    
    def update_upload_speed(self,value:float):
        self.statusBar.update_upload_speed(value)
    
    def update_download_speed(self,value:float):
        self.statusBar.update_download_speed(value)
    

  
    def update_latency(self,value:int):
        self.statusBar.update_latency(value)
        
    
    def setQImage(self, qimage:QImage):
        self.display.setQImage(qimage)



if __name__=="__main__":
    import sys
    # TODO
    # 1. 封装下请求的host 等参数 统一管理 后面host走下发
    # 2. 界面完善
    # 3. OTA

    app=QApplication(sys.argv)

    m=Monitor(Setting())
    m.show()

    app.exec()

