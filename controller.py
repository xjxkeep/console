import logging
import sys
from typing import Any
import typing

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import *
from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    FluentIcon,
    GroupHeaderCardWidget,
    PillPushButton,
    ProgressBar,
    ScrollArea,
    SpinBox,
    Theme,
    TransparentPushButton,
    TransparentToolButton,
    setTheme,
)

from pkg.joystick import JoyStick
from pkg.model import Setting
from view.channel import Detector,ChannelGroup


class Controller(ScrollArea):
    controlMessage=pyqtSignal(list)
    def setupUi(self):
        self.setObjectName("Controller")
        self.setWindowTitle("Controller")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(QWidget())
        self.resize(100, 100)
        layout=QVBoxLayout()
        self.detector=Detector()
        layout.addWidget(self.detector)
        self.channelGroup=ChannelGroup(channelCount=self.setting.channel_count,fineTunes=self.setting.channels)
        layout.addWidget(self.channelGroup)
        self.widget().setLayout(layout)
        self.enableTransparentBackground()

        self.timer=QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.__emit_control_message)
        self.timer.start()
        
    def __init__(self,setting:Setting) -> None:
        super().__init__()
        self.setting=setting
        self.channelCount=self.setting.channel_count
        self.setupUi()
        self.detector.signal.connect(self.setChannelValue)

    def getChannelValues(self):
        return self.channelGroup.getValues()


    def __emit_control_message(self):
        channelValues=self.getChannelValues()
        self.controlMessage.emit(channelValues)
    # 更新通道值 
    def setChannelValue(self,values:list[int]):
        self.channelGroup.setValues(values)
        self.__emit_control_message()
    
    def setJoystickValue(self,x:float,y:float):
        self.channelGroup.setValue(0,round(50+x*50))
        self.channelGroup.setValue(1,round(50-y*50))
        self.__emit_control_message()

    

    
    def close(self):
        self.timer.stop()
        logging.info("controller timer stop")
        self.detector.close()
        logging.info("controller detector close")
        super().close()

    

if __name__ == "__main__":
    from pkg.model import Setting
    app = QApplication(sys.argv)
    setTheme(Theme.DARK)
    controller = Controller(Setting())
    controller.show()
    sys.exit(app.exec_())
        
        
