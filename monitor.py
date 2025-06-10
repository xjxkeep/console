from PyQt5.QtCore import Qt,pyqtSignal
from qfluentwidgets import FluentIcon,FluentIconBase,TransparentPushButton,TransparentToolButton,TransparentDropDownPushButton,RoundMenu,Action
from PyQt5.QtGui import QCloseEvent, QIcon,QColor,QImage,QPixmap
from PyQt5.QtCore import Qt,QTimer
from PyQt5.QtWidgets import *
from datetime import datetime
from pkg.quic import HighwayQuicClient
from protocol.highway_pb2 import Device,Video
from pkg.codec import H264Decoder
import time
import threading
from view.wave import WaveformWidget
import numpy as np
class StatusBar(QWidget):
    video_format_changed=pyqtSignal(str)
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
        layout=QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.signal=TransparentPushButton(FluentIcon.WIFI.icon(color=QColor("green")),"10 ms")
        self.upload=TransparentPushButton(FluentIcon.UP.icon(),"100 kb/s")
        self.download=TransparentPushButton(FluentIcon.DOWN.icon(),"99 kb/s")
        self.fps=TransparentPushButton(FluentIcon.VIDEO.icon(),"30 fps")
        self.date=TransparentPushButton(FluentIcon.DATE_TIME.icon(),"2025/02/09 21:44:00")
        self.channel=TransparentDropDownPushButton(FluentIcon.IOT.icon(),"线路: 上海")
        self.video_format=TransparentDropDownPushButton(FluentIcon.VIDEO.icon(),"视频格式: h264")
        self.battery=TransparentPushButton(QIcon("assets/svg/battery-full.svg"),"100%")
        menu = RoundMenu(parent=self)
        menu.addActions([
            Action('线路: 上海'),
            Action('线路: 北京'),
        ])
        self.channel.setMenu(menu)
        menu.triggered.connect(self.__handle_menu_triggered)


        menu=RoundMenu(parent=self)
        menu.addActions([
            Action('h264'),
            Action('h265'),
        ])
        self.video_format.setMenu(menu)
        menu.triggered.connect(self.__handle_video_format_menu_triggered)

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
        layout.addWidget(self.channel)
        layout.addWidget(self.fps)
        layout.addWidget(self.date)
        layout.addWidget(self.sync)
        
        
        self.setLayout(layout)
        self.setFixedHeight(50)
        self.setStyleSheet("background-color: rgb(255,0,0)")

    def __handle_menu_triggered(self,action:Action):
        print(action.text())
    

    def __handle_video_format_menu_triggered(self,action:Action):
        print(action.text())
        self.video_format_changed.emit(action.text())
        self.video_format.setText("视频格式: "+action.text())
    def __init__(self):
        super().__init__()
        self.setupUi()


class Monitor(QWidget):
    # TODO 视频解码卡顿
    startSignal=pyqtSignal()
    sendTestVideoSignal=pyqtSignal()
    video_format_changed=pyqtSignal(str)
    def setupUi(self):
        self.setObjectName("Monitor")
        self.resize(800,600)
        layout=QVBoxLayout()
        self.statusBar=StatusBar()
        
        layout.addWidget(self.statusBar)

        self.display=QLabel("无信号，等待客户端连接...")
        self.display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.display.setStyleSheet("background-color: rgb(0,0,0);color: rgb(255,255,255);")
        layout.addWidget(self.display)
        self.waveform=WaveformWidget()
        layout.addWidget(self.waveform)
        
        self.testButton=QPushButton("测试本地视频解码")
        self.testButton.clicked.connect(self.test)
        self.startButton=QPushButton("连接服务器")
        self.startButton.clicked.connect(self.startSignal.emit)
        self.sendTestVideoButton=QPushButton("发送摄像头视频")
        self.sendTestVideoButton.clicked.connect(self.sendTestVideoSignal.emit)
        layout.addWidget(self.testButton)
        layout.addWidget(self.startButton)
        layout.addWidget(self.sendTestVideoButton)
        
        

        self.setLayout(layout)
        
        self.__frame=None



    def __init__(self,setting:dict,parent=None) -> None:
        super().__init__(parent)
        self.setting=setting
        self.setupUi()
        self.fps=0
        self.timer=QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_fps)
        self.timer.start()
        self.decoder=H264Decoder()
        self.latency=0
        self.statusBar.video_format_changed.connect(self.video_format_changed.emit)
    
    def update_wave_form(self,value:np.ndarray):
        print("update_wave_form",len(value))
        self.waveform.set_data(value)
    
    def update_upload_speed(self,value:float):
        self.statusBar.update_upload_speed(value)
    
    def update_download_speed(self,value:float):
        self.statusBar.update_download_speed(value)
    
    def test(self):
        threading.Thread(target=self.videoDecodeTest,daemon=True).start()
    
    def videoDecodeTest(self):
        with open(r"output.h264","rb") as f:
            while True:
                data=f.read(9600)
                if not data:
                    break
                self.decoder.write(data)
                time.sleep(0.005)
  
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
            print(f"Error displaying video: {str(e)}")

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        self.decoder.close()
        print("decoder closed")
        return super().closeEvent(a0)

if __name__=="__main__":
    import sys
    # TODO
    # 1. 封装下请求的host 等参数 统一管理 后面host走下发
    # 2. 界面完善
    # 3. OTA

    app=QApplication(sys.argv)

    m=Monitor()
    m.show()

    app.exec()

