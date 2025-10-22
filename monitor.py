from datetime import datetime
import logging
import time

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QCloseEvent, QColor, QIcon, QImage, QPixmap
from PyQt5.QtWidgets import *
import numpy as np
from qfluentwidgets import (
    Action,
    FlowLayout,
    FluentIcon,
    FluentIconBase,
    PushButton,
    RoundMenu,
    TransparentDropDownPushButton,
    TransparentPushButton,
    TransparentToolButton,
)

from pkg.codec import H264Decoder
from pkg.model import Setting
from pkg.quic import HighwayQuicClient
from protocol.highway_pb2 import Device, DeviceParam, Video
from view.imu import IMUWidget
from view.video_display import VideoDisplayWidget
from view.wave import WaveformWidget

class StatusBar(QWidget):
    param_changed=pyqtSignal(dict)
    def update(self):
        self.date.setText(datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    
    def update_fps(self,value:int):
        self.fps.setText(f"{value} fps")
    
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
        self.fps=TransparentPushButton(FluentIcon.VIDEO.icon(),"30 fps")
        self.date=TransparentPushButton(FluentIcon.DATE_TIME.icon(),"2025/02/09 21:44:00")
        self.channel=TransparentDropDownPushButton(FluentIcon.IOT.icon(),"线路: 上海")
        self.resolution=TransparentDropDownPushButton(FluentIcon.VIDEO.icon(),"清晰度: 高清")
        self.video_format=TransparentDropDownPushButton(FluentIcon.VIDEO.icon(),"视频格式: H.264")
        self.bABR=TransparentPushButton(FluentIcon.VIDEO.icon(),"码率自适应: 关闭")
        self.battery=TransparentPushButton(QIcon("assets/svg/battery-full.svg"),"100%")

        switch_menu=RoundMenu(parent=self)
        switch_menu.addActions([
            Action('开启'),
            Action('关闭'),
        ])
        self.bABR.setMenu(switch_menu)
        switch_menu.triggered.connect(self.__handle_bABR_menu_triggered)


        channel_menu = RoundMenu(parent=self)
        channel_menu.addActions([
            Action('上海'),
            Action('北京'),
        ])
        self.channel.setMenu(channel_menu)
        channel_menu.triggered.connect(self.__handle_channel_menu_triggered)


        video_format_menu=RoundMenu(parent=self)
        video_format_menu.addActions([
            Action('H.264'),
            Action('H.265'),
        ])
        self.video_format.setMenu(video_format_menu)
        video_format_menu.triggered.connect(self.__handle_video_format_menu_triggered)


        resolution_menu=RoundMenu(parent=self)
        resolution_menu.addActions([
            Action('高清'),
            Action('标清'),
            Action('流畅'),
        ])
        self.resolution.setMenu(resolution_menu)
        resolution_menu.triggered.connect(self.__handle_resolution_menu_triggered)

        self.timer=QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        self.sync=TransparentToolButton(FluentIcon.SYNC.icon())


        layout.addWidget(self.signal)
        layout.addWidget(self.battery)

        layout.addWidget(self.upload)
        layout.addWidget(self.download)

        layout.addWidget(self.video_format)
        layout.addWidget(self.resolution)
        layout.addWidget(self.channel)
        layout.addWidget(self.bABR)
        layout.addWidget(self.fps)
        layout.addWidget(self.date)
        layout.addWidget(self.sync)
        
        
        self.setLayout(layout)
        self.setStyleSheet("background-color: rgb(255,0,0)")

    def __handel_setting_changed(self):
         self.param_changed.emit({
            "resolution":self.resolution.text().split(":")[1].strip(),
            "video_format":self.video_format.text().split(":")[1].strip(),
            "channel":self.channel.text().split(":")[1].strip(),
            "bABR":self.bABR.text().split(":")[1].strip(),
        })
    
    def __handle_channel_menu_triggered(self,action:Action):
        logging.info(action.text())
        self.channel.setText("线路: "+action.text())
        self.__handel_setting_changed()

    def __handle_video_format_menu_triggered(self,action:Action):
        logging.info(action.text())
        self.video_format.setText("视频格式: "+action.text())
        self.__handel_setting_changed()
    def __handle_resolution_menu_triggered(self,action:Action):
        logging.info(action.text())
        self.resolution.setText("清晰度: "+action.text())
        self.__handel_setting_changed()
    def __handle_bABR_menu_triggered(self,action:Action):
        logging.info(action.text())
        self.bABR.setText("码率自适应: "+action.text())
        self.__handel_setting_changed()
    def __init__(self):
        super().__init__()
        self.setupUi()



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
        main_layout = QVBoxLayout()
        self.statusBar = StatusBar()
        main_layout.addWidget(self.statusBar)

 
        
        self.display = QLabel("无信号，等待客户端连接...")
        self.display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        self.display.setStyleSheet("background-color: rgb(0,0,0);color: rgb(255,255,255);")
        
   
        main_layout.addWidget(self.display)
        
        self.waveform = WaveformWidget()
        main_layout.addWidget(self.waveform)
        
  
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
        main_layout.addLayout(buttonLayout)
        self.setLayout(main_layout)
        
        self.__frame = None



    def __init__(self,setting:Setting,parent=None) -> None:
        super().__init__(parent)
        self.setting=setting
        self.setupUi()
        self.fps=0
        self.timer=QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_fps)
        self.timer.start()
        self.latency=0
        self.statusBar.param_changed.connect(self.param_changed)
    
    def conncet_server(self):
        self.startButton.setDisabled(True)
        self.sendTestCodecButton.setEnabled(True)
        self.sendTestDatagramButton.setEnabled(True)
        self.sendTestVideoButton.setEnabled(True)
        self.startSignal.emit()
        
        
    
    def update_device_param(self,data:DeviceParam):
        logging.info(data)
        # self.imu.update_imu_data(data.imu_param)

    def update_wave_form(self,value:np.ndarray):
        self.waveform.set_data(value)
    
    def update_upload_speed(self,value:float):
        self.statusBar.update_upload_speed(value)
    
    def update_download_speed(self,value:float):
        self.statusBar.update_download_speed(value)
    

  
    def update_latency(self,value:int):
        self.statusBar.update_latency(value)
    
    def update_fps(self):
        self.statusBar.update_fps(self.fps)
        self.fps=0
    
    
    def setPixmap(self, pixmap:QPixmap):
        try:
            # Increment the frame count
            self.fps += 1
            self.__frame=pixmap
            scaled_pixmap = self.__frame.scaled(self.display.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.display.setPixmap(scaled_pixmap)
        
        except Exception as e:
            logging.info(f"Error displaying video: {str(e)}")



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

