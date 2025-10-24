from PyQt5.QtWidgets import QWidget
from qfluentwidgets import *
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import *
from pkg.joystick import JoyStick  
import logging


class Channel(QWidget):
    channelSignal=pyqtSignal(int)
    def setupUi(self):
        layout=QHBoxLayout()
        self.label=BodyLabel("Channel")
        self.progressBar=ProgressBar(useAni=False)
        self.fineTune=SpinBox(self)
        self.fineTune.setMinimum(-100)
        self.fineTune.setMaximum(100)
        self.fineTune.setValue(0)
        self.channelValue=0
        self.reverse=PillPushButton("Reverse",self)
        layout.addWidget(self.reverse)
        layout.addWidget(self.label)
        layout.addWidget(self.progressBar)
        layout.addWidget(self.fineTune)
        self.reverseFlag=False
        self.reverse.clicked.connect(self.setReverse)
        self.fineTune.valueChanged.connect(self.onFineTuneChanged)
        self.progressBar.valueChanged.connect(self.channelSignal.emit)
        self.setLayout(layout)

        
    def __init__(self) -> None:
        super().__init__()
        self.setupUi()
    
    
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


class Detector(QWidget):
    signal=pyqtSignal(list) # (channel,value)
    loading=pyqtSignal(str)
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
    
    def __init__(self) -> None:
        super().__init__()
        self.setupUi()
        self.deviceMap=dict()      
        self.joystick=JoyStick()
       

