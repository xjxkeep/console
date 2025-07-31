from PyQt5.QtWidgets import QWidget
from qfluentwidgets import *
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import *
import sys
from PyQt5.QtCore import QTimer
from pkg.joystick import JoyStick
import threading

class GuideButtonGroup(QWidget):
    prevClicked=pyqtSignal()
    nextClicked=pyqtSignal()
    skipClicked=pyqtSignal()
    def setupUi(self):
        self.setObjectName("guideButton")
        layout=QHBoxLayout()
        
        # 添加弹性空间来居中按钮
        layout.addStretch()  # 左侧弹性空间
        
        self.nextButton=PrimaryPushButton("下一步")
        self.skipButton=PushButton("跳过")
        self.label=BodyLabel("1/3",self)
        
        layout.addWidget(self.skipButton)
        layout.addWidget(self.nextButton)
        layout.addWidget(self.label)
        layout.addStretch()  # 右侧弹性空间
        
        
        self.nextButton.clicked.connect(self.nextClicked)
        self.skipButton.clicked.connect(self.skipClicked)
        
        self.setLayout(layout)
    def __init__(self) -> None:
        super().__init__()
        self.setupUi()
    
    def setText(self,text):
        self.label.setText(text)
    

    
        
class WelcomeStep(QWidget):
    def setupUi(self):
        self.setObjectName("welcomeStep")
        layout=QVBoxLayout()
        # 设置布局间距
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        
        self.titleLabel=TitleLabel("欢迎使用",self)
        self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)   
        
        # 标题使用Fixed策略，确保它保持在顶部
        self.titleLabel.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Fixed)
        
        self.descLabel=BodyLabel("请按照以下步骤进行操作，点击下一步继续请按照以下步骤进行操作请按照以下步骤进行操作请按照以下步骤进行操作请按照以下步骤进行操作请按照以下步骤进行操作请按照以下步骤进行操作请按照以下步骤进行操作",self)
        self.descLabel.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # 描述文字使用Expanding策略，占用剩余空间
        self.descLabel.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        self.descLabel.setWordWrap(True)
        
        layout.addWidget(self.titleLabel)
        layout.addWidget(self.descLabel)
        layout.addStretch()  # 在描述文字后添加弹性空间，将标题推到顶部
        self.setLayout(layout)
    def __init__(self) -> None:
        super().__init__()
        self.setupUi()



class Guide(QWidget):
    def setupUi(self):
        self.setObjectName("guide")
        self.resize(500,500)
        
        mainLayout=QVBoxLayout()
        # 设置布局的间距
        mainLayout.setSpacing(0)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        
        self.steps=[
            WelcomeStep(),
            PushButton("测试本地视频解码"),
            PushButton("连接服务器"),
            PushButton("发送摄像头视频"),
        ]
        self.stepGroup=QStackedWidget()
        self.stepGroup.addWidget(self.steps[0])
        self.stepGroup.addWidget(self.steps[1])
        self.stepGroup.addWidget(self.steps[2])
        self.stepGroup.addWidget(self.steps[3])
        self.stepGroup.setCurrentIndex(0)

        
        self.buttonGroup=GuideButtonGroup()
        self.buttonGroup.setText(f"1/{len(self.steps)}")
        self.buttonGroup.skipClicked.connect(self.close)
        self.buttonGroup.nextClicked.connect(self.nextStep)
        # 按钮组使用Expanding策略，让它可以扩展
        self.buttonGroup.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        mainLayout.addWidget(self.stepGroup)
        
        mainLayout.addWidget(self.buttonGroup)
        self.setLayout(mainLayout)
        
    def nextStep(self):
        index=self.stepGroup.currentIndex()
        if index+1<len(self.steps):
            self.stepGroup.setCurrentIndex(index+1)
            self.buttonGroup.setText(f"{index+2}/{len(self.steps)}")
            
        if self.stepGroup.currentIndex()+1>=len(self.steps):
            self.buttonGroup.nextButton.setText("完成")
            self.buttonGroup.nextButton.clicked.connect(self.close)
    
    def __init__(self) -> None:
        super().__init__()
        self.setupUi()
        
    


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Guide()
    window.show()
    sys.exit(app.exec_())