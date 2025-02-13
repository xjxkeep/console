from PyQt5.QtWidgets import QWidget



class About(QWidget):
    def setupUi(self):
        self.setObjectName("about")
    def __init__(self) -> None:
        super().__init__()
        self.setupUi()