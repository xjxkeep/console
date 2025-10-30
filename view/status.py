from datetime import datetime
import logging

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QCloseEvent, QColor, QIcon, QImage, QPixmap
from PyQt5.QtWidgets import *
from qfluentwidgets import (
    FlowLayout,
    FluentIcon,
    TransparentPushButton,
    TransparentToolButton,
    ComboBox
)


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
        self.channel=ComboBox()
        self.channel.addItems(["线路: 上海","线路: 北京"])
        self.channel.setCurrentIndex(0)
        self.channel.currentTextChanged.connect(self.__handle_channel_menu_triggered)
        
        self.resolution=ComboBox()
        self.resolution.addItems(["清晰度: 高清","清晰度: 标清","清晰度: 流畅"])
        self.resolution.setCurrentIndex(0)
        self.resolution.currentTextChanged.connect(self.__handle_resolution_menu_triggered)
        
        self.video_format=ComboBox()
        self.video_format.addItems(["视频格式: H.264","视频格式: H.265"])
        self.video_format.setCurrentIndex(0)
        self.video_format.currentTextChanged.connect(self.__handle_video_format_menu_triggered)
        

        self.bABR=ComboBox()
        self.bABR.addItems(["码率自适应: 开启","码率自适应: 关闭"])
        self.bABR.setCurrentIndex(0)
        self.bABR.currentTextChanged.connect(self.__handle_bABR_menu_triggered)
        self.battery=TransparentPushButton(QIcon("assets/svg/battery-full.svg"),"100%")

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
            "resolution":self.resolution.currentText().split(":")[1].strip(),
            "video_format":self.video_format.currentText().split(":")[1].strip(),
            "channel":self.channel.currentText().split(":")[1].strip(),
            "bABR":self.bABR.currentText().split(":")[1].strip(),
        })
    
    def __handle_channel_menu_triggered(self,text:str):
        logging.info(text)
        self.__handel_setting_changed()

    def __handle_video_format_menu_triggered(self,text:str):
        logging.info(text)
        self.__handel_setting_changed()
    def __handle_resolution_menu_triggered(self,text:str):
        logging.info(text)
        self.__handel_setting_changed()
    def __handle_bABR_menu_triggered(self,text:str):
        logging.info(text)
        self.__handel_setting_changed()
    def __init__(self):
        super().__init__()
        self.setupUi()
