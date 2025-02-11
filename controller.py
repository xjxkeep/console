from qfluentwidgets import ProgressBar,SpinBox,PillPushButton
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import *
import sys
from PyQt5.QtCore import QTimer
from pkg.joystick import JoyStick

class Channel(QWidget):
    channelSignal=pyqtSignal(int)
    def setupUi(self):
        layout=QHBoxLayout()
        self.label=QLabel("Channel")
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
    
    def onFineTuneChanged(self,x:int):
        self.progressBar.setValue(self.channelValue+x)

class Controller(QWidget):
    controlMessage=pyqtSignal(list)
    def setupUi(self):
        self.setWindowTitle("Controller")
        self.resize(100, 100)
        layout=QVBoxLayout()
        self.channels=[Channel() for _ in range(self.channelCount)]
        for idx,channel in enumerate(self.channels):
            channel.setLabel(f"Channel{idx+1}")
            channel.channelSignal.connect(self.__updateChannelValues)
            layout.addWidget(channel)
        self.setLayout(layout)
        
    def __init__(self) -> None:
        super().__init__()
        self.channelCount=10
        self.setupUi()
        self.timer=QTimer()
        self.timer.timeout.connect(self.__updateChannelValues)
        self.timer.start(1000)
        self.joystick=JoyStick()
        self.joystick.select_device(0)
        self.joystick.signal.connect(self.setChannelValue)
    
    def __updateChannelValues(self):
        self.controlMessage.emit(self.getChannelValues())
    
    def getChannelValues(self):
        return [channel.getValue() for channel in self.channels]
    # 更新通道值 
    def setChannelValue(self,idx:int,x:int):
        if idx<1 or idx>self.channelCount:
            return
        self.channels[idx-1].setValue(x)
    
    def closeEvent(self, a0) -> None:
        self.joystick.running=False
        self.joystick.thread.join()
        super().closeEvent(a0)
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = Controller()
    controller.show()
    sys.exit(app.exec_())
        
        
