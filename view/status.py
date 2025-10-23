from datetime import datetime
import logging

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QCloseEvent, QColor, QIcon, QImage, QPixmap
from PyQt5.QtWidgets import *
from qfluentwidgets import (
    Action,
    FlowLayout,
    FluentIcon,
    RoundMenu,
    TransparentDropDownPushButton,
    TransparentPushButton,
    TransparentToolButton,
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
