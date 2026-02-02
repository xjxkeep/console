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

from pkg.joystick_remote import create_joystick

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
        layout=QGridLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        self.channels=[Channel(showFineTune=self.showFineTune,showReverse=self.showReverse) for _ in range(self.channelCount)]
        for idx,channel in enumerate[Channel](self.channels):
            channel.setLabel(f"{self.prefix}{idx+1}")
            channel.setFineTune(self.fineTunes[idx] if idx<len(self.fineTunes) else 0)
            channel.valueChanged.connect(lambda value: self.channelValueChanged.emit(idx,value))
            # 每行两列：row = idx // 2, col = idx % 2
            row = idx // 2
            col = idx % 2
            layout.addWidget(channel, row, col)
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
    # 新增信号：当选择模拟摇杆时为True，否则为False
    virtual_joystick_selected = pyqtSignal(bool)
    # 设备列表刷新信号：(设备名称列表)
    devices_refreshed = pyqtSignal(list)
    # 设备选择变化信号：(设备索引)
    device_index_changed = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()
        self._syncing = False  # 防止循环触发
        self.setupUi()
        self.deviceMap:dict[Any, Any]=dict[Any, Any]()
        self.joystick=create_joystick()

        # 延迟导入 JoystickController 以避免循环导入
        from components.controller import JoystickController
        self.virtual_joystick=JoystickController()
        # 默认连接虚拟摇杆的信号
        self.virtual_joystick.position_changed.connect(self.handle_virtual_joystick_change)
        self.current_device_type = None
        # 初始化时刷新设备列表并默认选择模拟摇杆
        self.refreshDevices()


    def setupUi(self):
        layout=QHBoxLayout()
        self.devices=ComboBox(self)
        self.refresh=TransparentToolButton(FluentIcon.SYNC.icon(),self)
        self.label=TransparentPushButton(FluentIcon.GAME.icon(),"选择设备:",self)
        self.refresh.clicked.connect(self.refreshDevices)
        self.devices.currentIndexChanged.connect(self._onDeviceIndexChanged)
        layout.addWidget(self.label)
        layout.addWidget(self.devices)
        layout.addWidget(self.refresh)
        self.setLayout(layout)

    def _onDeviceIndexChanged(self, idx: int):
        """内部处理设备索引变化"""
        self.deviceChosen(idx)
        if not self._syncing:
            self.device_index_changed.emit(idx)

    def deviceChosen(self,idx:int):
        device=self.deviceMap.get(idx)
        if device is None:
            return

        # 断开当前物理摇杆设备的信号连接（如果有）
        if hasattr(self, "joystick") and hasattr(self.joystick, "signal"):
            try:
                self.joystick.signal.disconnect(self.signal.emit)
            except TypeError:
                # 如果没有连接，忽略错误
                pass

        # 设置当前设备类型
        self.current_device_type = device["type"]

        # 发出虚拟摇杆选择状态信号
        is_virtual = device["type"] == "virtual_joystick"
        self.virtual_joystick_selected.emit(is_virtual)

        # 连接新设备的信号
        if device["type"] == "virtual_joystick":
            # 虚拟摇杆已经在初始化时连接了信号，只需要标记当前设备类型
            logging.info("选择了模拟摇杆")
        else:
            # 选择物理摇杆设备
            self.__getattribute__(device["type"]).select_device(device["id"])
            self.__getattribute__(device["type"]).signal.connect(self.signal.emit)
            logging.info(f"选择了设备: {device['type']}, ID: {device['id']}")

    def setDevices(self,devices:list):
        self.devices.clear()
        self.devices.addItems(devices)

    def getDevices(self):
        deviceCount=0
        devices=[]
        # 添加模拟摇杆选项
        devices.append("模拟摇杆")
        self.deviceMap[deviceCount]={"id":0,"type":"virtual_joystick"}
        deviceCount+=1

        # 添加物理摇杆设备
        joys=self.joystick.get_device_list()
        for joy in joys:
            devices.append(joy["name"])
            self.deviceMap[deviceCount]={"id":joy["id"],"type":"joystick"} # type需要和变量名一致
            deviceCount+=1
        logging.info(devices)
        logging.info(self.deviceMap)
        return devices

    def refreshDevices(self):
        devices = self.getDevices()
        self.setDevices(devices)
        # 默认选择模拟摇杆（索引0）
        self.devices.setCurrentIndex(0)
        # 手动触发设备选择事件
        self.deviceChosen(0)
        # 发出设备列表刷新信号
        self.devices_refreshed.emit(devices)

    def setCurrentDevice(self, index: int):
        """设置当前选中的设备（用于同步，不触发 device_index_changed 信号）"""
        self._syncing = True
        if 0 <= index < self.devices.count():
            self.devices.setCurrentIndex(index)
        self._syncing = False

    def close(self):
        if hasattr(self,"joystick"):
            self.joystick.close()
            logging.info("detector joystick close")
        super().close()

    def lazy_init(self):
        if not hasattr(self,"joystick"):
            self.joystick.init()

    def handle_virtual_joystick_change(self, x: float, y: float):
        """处理虚拟摇杆的位置变化信号"""
        if self.current_device_type == "virtual_joystick":
            # 将x,y转换为channel值（0-100）
            channel0_value = int(50 + x * 50)  # 左右控制通道0
            channel1_value = int(50 + y * 50)  # 上下控制通道1
            # 发送信号，格式为[channel0_value, channel1_value]
            self.signal.emit([channel0_value, channel1_value])
    


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

    def setJoystickValue(self,x:float,y:float):
        self.channels[0].setValue(round(50+x*50))
        self.channels[1].setValue(round(50-y*50))

    def setValues(self, values: list[int]):
        """设置所有通道的值"""
        for idx, value in enumerate(values):
            if idx >= len(self.channels):
                break
            self.channels[idx].setValue(value)

    def update_channel_value(self,idx:int,value:int):
        if idx>=len(self.channels):
            return
        self.channels[idx].setValue(value)

if __name__ == "__main__":
    app=QApplication(sys.argv)
    channel=ChannelDisp()
    channel.show()
    
    app.exec_()