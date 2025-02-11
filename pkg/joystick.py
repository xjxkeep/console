from PyQt5.QtCore import QObject,pyqtSignal


class JoyStick(QObject):
    joystickSignal=pyqtSignal(int,int) # (channel,value)
    def __init__(self) -> None:
        super().__init__()
        