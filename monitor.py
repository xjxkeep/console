
import logging

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import *
import numpy as np
from qfluentwidgets import PushButton

from view.channel import ChannelGroup,ChannelDisp
from pkg.model import Setting
from protocol.highway_pb2 import Device, DeviceParam, Video
from view.imu import IMUWidget
from view.status import StatusBar, StatusPanel
from view.video import VideoPanel
from view.wave import WaveformWidget
from view.controller import ControlPanel


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
        main_layout = QGridLayout()
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
        
        hlayout=QHBoxLayout()
        self.channelDisp=ChannelDisp()
        self.channelDisp.setMaximumWidth(300)
        self.controlPanel.joystick_changed.connect(self.handle_joystick_changed)
        self.waveform.setMinimumWidth(200)
        hlayout.addWidget(self.waveform)
        hlayout.addWidget(self.channelDisp)
        main_layout.addWidget(self.statusBar,0,0,1,2)
        main_layout.addWidget(self.display,1,0)
        main_layout.addLayout(hlayout,2,0)
        main_layout.addLayout(buttonLayout,3,0)
        main_layout.addWidget(self.controlPanel,1,1,2,1,Qt.AlignTop)
        main_layout.addWidget(self.statusPanel,1,2,2,1,Qt.AlignTop)
        # main_layout.addWidget(self.channelGroup,1,2,2,1)
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
        # logging.info(data)
        # self.imu.update_imu_data(data.imu_param)
        pass

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

