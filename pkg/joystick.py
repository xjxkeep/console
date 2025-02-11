from PyQt5.QtCore import QObject,pyqtSignal


class JoyStick(QObject):
    def __init__(self) -> None:
        super().__init__()
        