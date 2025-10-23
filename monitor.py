
import logging

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import *
import numpy as np
from qfluentwidgets import PushButton

from pkg.model import Setting
from protocol.highway_pb2 import Device, DeviceParam, Video
from view.imu import IMUWidget
from view.status import StatusBar
from view.video import VideoPlayer
from view.wave import WaveformWidget


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

 
        
        self.display =VideoPlayer("无信号，等待客户端连接...")
        self.display.fps_collected.connect(self.statusBar.update_fps)
        
   
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
        
    
    def setPixmap(self, pixmap:QPixmap):
        self.display.setPixmap(pixmap)



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

