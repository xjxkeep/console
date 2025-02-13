from PyQt5.QtWidgets import QWidget


class Debug(QWidget):
    
    def __init__(self):
        super().__init__()
        self.setupUi()
        
    def setupUi(self):
        self.setObjectName("Debug")
        
    
    


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app=QApplication(sys.argv)
    debug=Debug()
    debug.show()
    sys.exit(app.exec_())