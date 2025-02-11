from qfluentwidgets import ProgressBar,SpinBox
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import *
import sys

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
        layout.addWidget(self.label)
        layout.addWidget(self.progressBar)
        layout.addWidget(self.fineTune)
        self.fineTune.valueChanged.connect(self.onFineTuneChanged)
        self.progressBar.valueChanged.connect(self.channelSignal.emit)
        self.setLayout(layout)
        
    def __init__(self) -> None:
        super().__init__()
        self.setupUi()
        
    def setLabel(self,label:str):
        self.label.setText(label)
    
    def setValue(self,x:int):
        self.channelValue=x
        self.progressBar.setValue(x+self.fineTune.value())
        
    def onFineTuneChanged(self,x:int):
        self.progressBar.setValue(self.channelValue+x)

class Controller(QWidget):
    channelSignal=pyqtSignal(int,int)
    def setupUi(self):
        self.setWindowTitle("Controller")
        self.resize(100, 100)
        layout=QVBoxLayout()
        self.channels=[Channel() for _ in range(10)]
        for idx,channel in enumerate(self.channels):
            def onChannelValueChanged(x:int,idx=idx):
                self.channelSignal.emit(idx,x)
            channel.setValue(10*idx+10)
            channel.setLabel(f"Channel{idx+1}")
            channel.channelSignal.connect(onChannelValueChanged)
            layout.addWidget(channel)
        self.setLayout(layout)
        
    def __init__(self) -> None:
        super().__init__()
        self.setupUi()
        self.channelSignal.connect(self.channelValueChanged)
    def channelValueChanged(self,idx:int,x:int):
        print(f"Channel{idx+1} value changed to {x}")
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = Controller()
    controller.show()
    sys.exit(app.exec_())
        
        
