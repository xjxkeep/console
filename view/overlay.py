from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor

class Overlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setLayout(QVBoxLayout())
        self.label=QLabel("1/3",self)
        self.layout().addWidget(self.label)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))  # 半透明黑色
    
    def highlight(self,w:QWidget):
        self.label.setGeometry(w.geometry())
        self.label.setFixedHeight(w.height())
        self.label.setFixedWidth(w.width())
        self.label.setStyleSheet("background-color: rgba(0, 0, 255, 100);border-radius: 10px; border: 1px solid rgba(255, 255, 255, 100);")
        self.label.show()
    def unhighlight(self):
        self.label.hide()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Overlay Example")
        self.setGeometry(100, 100, 400, 300)

        # 添加一些控件
        layout = QVBoxLayout()

        self.button1 = QPushButton("Button 1")
        self.button2 = QPushButton("Button 2")
        self.toggle_overlay_button = QPushButton("Toggle Overlay")

        layout.addWidget(self.button1)
        layout.addWidget(self.button2)
        layout.addWidget(self.toggle_overlay_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # 创建蒙层
        self.overlay = Overlay(self)
        self.overlay.hide()

        # 连接按钮信号
        self.toggle_overlay_button.clicked.connect(self.toggle_overlay)

    def toggle_overlay(self):
        if self.overlay.isVisible():
            self.overlay.hide()
        else:
            # 确保蒙层大小与主窗口相同
            self.overlay.resize(self.size())
            self.overlay.move(0, 0)  # 确保蒙层位置正确
            self.overlay.raise_()  # 确保蒙层在最顶层
            self.overlay.highlight(self.button2)
            print(self.button2.geometry())
            self.overlay.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 当窗口大小改变时，同步调整蒙层大小
        if self.overlay.isVisible():
            self.overlay.resize(self.size())
            self.overlay.move(0, 0)

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())
