import logging
import sys,os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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

class Channel(QWidget):
    valueChanged=pyqtSignal(int)
    def setupUi(self):
        layout=QHBoxLayout(self)
        self.label=BodyLabel()
        self.progressBar=ProgressBar(useAni=False)
        self.fineTune=SpinBox(self)
        self.fineTune.setMinimum(-100)
        self.fineTune.setMaximum(100)
        self.fineTune.setValue(0)
        self.channelValue=0
        self.reverse=PillPushButton("反向",self)
        layout.addWidget(self.reverse)
        layout.addWidget(self.label)
        layout.addWidget(self.progressBar)
        layout.addWidget(self.fineTune)
        self.reverseFlag=False
        self.reverse.clicked.connect(self.setReverse)
        self.fineTune.valueChanged.connect(self.onFineTuneChanged)
        self.progressBar.valueChanged.connect(self.valueChanged.emit)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        self.setLayout(layout)


        
    def __init__(self,label="通道",showFineTune:bool=True,showReverse:bool=True) -> None:
        super().__init__()
        self.setupUi()
        self.label.setText(label)
        self.fineTune.setVisible(showFineTune)
        self.reverse.setVisible(showReverse)
    
    def setReverse(self,reverse:bool):
        self.reverseFlag=reverse

    def setLabel(self,label:str):
        self.label.setText(label)
    
    def setValue(self,x:int):
        if self.reverseFlag:
            x=100-x
        self.channelValue=x
        self.progressBar.setValue(x+self.fineTune.value())
    
    def getValue(self):
        return self.channelValue+self.fineTune.value()
    
    def setFineTune(self,x:int):
        self.fineTune.setValue(x)
    
    def getFineTune(self):
        return self.fineTune.value()
    
    def onFineTuneChanged(self,x:int):
        self.progressBar.setValue(self.channelValue+x)


    
class ChannelGroup(QWidget):


    channelValueChanged=pyqtSignal(int,int)

    def setupUi(self):
        layout=QVBoxLayout()
        self.channels=[Channel(showFineTune=self.showFineTune,showReverse=self.showReverse) for _ in range(self.channelCount)]
        for idx,channel in enumerate[Channel](self.channels):
            channel.setLabel(f"{self.prefix}{idx+1}")
            channel.setFineTune(self.fineTunes[idx] if idx<len(self.fineTunes) else 0)
            channel.valueChanged.connect(lambda value: self.channelValueChanged.emit(idx,value))
            layout.addWidget(channel)
        self.setLayout(layout)

    def __init__(self,channelCount:int=10,fineTunes:list[int]=[0]*10,prefix:str="通道",showFineTune:bool=True,showReverse:bool=True) -> None:
        super().__init__()
        self.channelCount=channelCount
        self.fineTunes=fineTunes
        self.prefix=prefix
        self.showFineTune=showFineTune
        self.showReverse=showReverse
        self.setupUi()

    def getValues(self) -> list[int]:
        return [channel.getValue() for channel in self.channels]
    

    def setValue(self,idx:int,value:int):
        if idx>=self.channelCount:
            return
        self.channels[idx].setValue(value)


    def setValues(self,values:list[int]):
        for idx,value in enumerate[Any](values):
            if idx>=self.channelCount:
                break
            self.setValue(idx,value)


class Detector(QWidget):
    signal=pyqtSignal(list) # (channel,value)
    loading=pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setupUi()
        self.deviceMap:dict[Any, Any]=dict[Any, Any]()      
        self.joystick=JoyStick()


    def setupUi(self):
        layout=QHBoxLayout()
        self.devices=ComboBox(self)
        self.refresh=TransparentToolButton(FluentIcon.SYNC.icon(),self)
        self.label=TransparentPushButton(FluentIcon.GAME.icon(),"选择设备:",self)
        self.refresh.clicked.connect(self.refreshDevices)
        self.devices.currentIndexChanged.connect(self.deviceChosen)
        layout.addWidget(self.label)
        layout.addWidget(self.devices)
        layout.addWidget(self.refresh)
        self.setLayout(layout)
    
    def deviceChosen(self,idx:int):
        device=self.deviceMap.get(idx)
        if device is None:
            return
        self.__getattribute__(device["type"]).select_device(device["id"])
        self.__getattribute__(device["type"]).signal.connect(self.signal.emit)
        
    def setDevices(self,devices:list):
        self.devices.clear()
        self.devices.addItems(devices)
    
    def getDevices(self):
        deviceCount=0
        devices=[]
        # TODO 实现其他设备
        joys=self.joystick.get_device_list()
        for joy in joys:
            devices.append(joy["name"])
            self.deviceMap[deviceCount]={"id":joy["id"],"type":"joystick"} # type需要和变量名一致
            deviceCount+=1
        logging.info(devices)
        logging.info(self.deviceMap)
        return devices
    
    def refreshDevices(self):
        self.setDevices(self.getDevices())
    

    def close(self):
        if hasattr(self,"joystick"):
            self.joystick.close()
            logging.info("detector joystick close")
        super().close()
    
    def lazy_init(self):
        if not hasattr(self,"joystick"):
            self.joystick.init()
    


class ChannelDisp(QWidget):
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.channels:list[Channel]=[]
        self.setupUi()
        

    def setupUi(self):
        layout=QGridLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(10,10,10,10)
        
        row,col=5,2
        for j in range(col):
            for i in range(row):
                label=f"No.{j*row+i+1}"
                channel=Channel(label=label,showFineTune=False,showReverse=False)
                channel.setContentsMargins(0,0,10,0)
                self.channels.append(channel)
                layout.addWidget(channel,i,j)
        self.setLayout(layout)
    
    def update_channel_value(self,idx:int,value:int):
        if idx>=len(self.channels):
            return
        self.channels[idx].setValue(value)

if __name__ == "__main__":
    app=QApplication(sys.argv)
    channel=ChannelDisp()
    channel.show()
    
    app.exec_()