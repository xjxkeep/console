from PyQt5.QtCore import Qt
from qfluentwidgets import StyleSheetBase, Theme, isDarkTheme, qconfig
from qfluentwidgets import button
from qfluentwidgets import FluentIcon,FluentIconBase,TransparentPushButton,TransparentToolButton,TransparentDropDownPushButton,RoundMenu,Action
from PyQt5.QtGui import QIcon,QColor,QImage,QPixmap
from PyQt5.QtCore import Qt,QTimer
from PyQt5.QtWidgets import *
from datetime import datetime
from pkg.quic import HighwayQuicClient
from protocol.highway_pb2 import Device
import asyncio
from pkg.decode import H264Decoder
import numpy as np

class StatusBar(QWidget):
    def update(self):
        self.date.setText(datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    def setupUi(self):
        layout=QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.signal=TransparentPushButton(FluentIcon.WIFI.icon(color=QColor("green")),"10 ms")
        self.upload=TransparentPushButton(FluentIcon.UP.icon(),"100 kb/s")
        self.download=TransparentPushButton(FluentIcon.DOWN.icon(),"99 kb/s")
        self.fps=TransparentPushButton(FluentIcon.VIDEO.icon(),"30 fps")
        self.date=TransparentPushButton(FluentIcon.DATE_TIME.icon(),"2025/02/09 21:44:00")
        self.channel=TransparentDropDownPushButton(FluentIcon.IOT.icon(),"线路: 上海")
        self.battery=TransparentPushButton(QIcon("assets/svg/battery-full.svg"),"100%")
        menu = RoundMenu(parent=self)
        menu.addActions([
            Action('线路: 上海'),
            Action('线路: 北京'),
        ])
        self.channel.setMenu(menu)

        self.timer=QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        self.sync=TransparentToolButton(FluentIcon.SYNC.icon())


        layout.addWidget(self.signal)
        layout.addWidget(self.battery)

        layout.addWidget(self.upload)
        layout.addWidget(self.download)
        layout.addWidget(self.channel)
        layout.addWidget(self.fps)
        layout.addWidget(self.date)
        layout.addWidget(self.sync)
        
        
        self.setLayout(layout)
        self.setFixedHeight(50)
        self.setStyleSheet("background-color: rgb(255,0,0)")

    
    def __init__(self):
        super().__init__()
        self.setupUi()


class Monitor(QWidget):


    def setupUi(self):
        self.resize(800,600)
        layout=QVBoxLayout()
        statusBar=StatusBar()
        
        layout.addWidget(statusBar)

        self.display=QLabel()
        self.display.setStyleSheet("background-color: rgb(255,0,0)")
        layout.addWidget(self.display)

        self.setLayout(layout)



    def __init__(self,parent=None) -> None:
        super().__init__(parent)
        
        self.setupUi()
        self.client=HighwayQuicClient(Device(id=1,message_type=Device.MessageType.VIDEO),host="127.0.0.1",port=30042,ca_certs="assets/tls/cert.pem",insecure=True)
        self.client.connected.connect(self.connected)
        self.decoder=H264Decoder()
        self.client.video_stream.connect(self.decoder.write)
        self.decoder.frame_decoded.connect(self.display_video)
        self.connectDevice(1)
    
    
    def connectDevice(self,device_id:int):
        self.client.start(device_id)
    
    def connected(self):
        print("connected")
    def display_video(self, image):
        try:
            # 将 numpy 数组转换为 QImage
            height, width, _ = image.shape
            bytes_per_line = 3 * width
            q_img = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)
            # 将 QImage 显示在 QLabel 上
            pixmap = QPixmap.fromImage(q_img)
            self.display.setPixmap(pixmap)
        except Exception as e:
            print(f"Error displaying video: {str(e)}")
