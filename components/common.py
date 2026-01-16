from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget
from qfluentwidgets import *
from PyQt5.QtWidgets import *



class BLineEdit(QWidget):
    
    def __init__(self,icon:FluentIcon=None,text=None, parent=None) -> None:
        super().__init__(parent)
        
        self.but=TransparentToolButton(icon,parent)
        self.lineEdit=LineEdit(parent)
        if text:
            self.lineEdit.setText(text)
        
        self.setLayout(QHBoxLayout(self))
        self.layout().addWidget(self.lineEdit)
        self.layout().addWidget(self.but)
    
    def text(self):
        return self.lineEdit.text()

    def clear(self):
        self.lineEdit.clear()
        
    def setPlaceholderText(self,text):
        self.lineEdit.setPlaceholderText(text)

class TLineEdit(QWidget):
    def __init__(self, label=None,text=None,parent=None) -> None:
        super().__init__(parent)
        self.label=QLabel(parent=parent)
        self.label.setScaledContents(True)
        if label:
            self.label.setText(label)
        self.line=LineEdit(parent)
        if text:
            self.line.setText(text)
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.label)
        self.layout().addWidget(self.line)
    
    def text(self):
         return self.line.text()
        
        
    