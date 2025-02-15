from PyQt5.QtWidgets import *
from qfluentwidgets import *
from PyQt5.QtCore import Qt

class SettingItem(QWidget):
    settingChanged=pyqtSignal(dict)
    def setupUi(self):
        self.setLayout(QHBoxLayout())
        self.label=QLabel(self.key)
        # Choose widget based on value type
        if isinstance(self.value, bool):
            self.valueEdit = SwitchButton()
            self.valueEdit.setOnText("True")
            self.valueEdit.setOffText("False")
            self.valueEdit.setChecked(self.value)
            self.valueEdit.checkedChanged.connect(self.__settingChanged)
        elif isinstance(self.value, (int, float)):
            self.valueEdit = SpinBox() if isinstance(self.value, int) else DoubleSpinBox()
            if isinstance(self.value, int):
                self.valueEdit.setRange(-999999999, 999999999)
            else:
                self.valueEdit.setRange(-999999999.0, 999999999.0)
            self.valueEdit.setValue(self.value)
            self.valueEdit.valueChanged.connect(self.__settingChanged)
        else:
            # Default to LineEdit for strings and other types
            self.valueEdit = LineEdit()
            self.valueEdit.setText(self.value)
            self.valueEdit.textChanged.connect(self.__settingChanged)
        self.layout().addWidget(self.label)
        self.layout().addWidget(self.valueEdit)
    
    def __init__(self,key:str,value):
        super().__init__()
        self.key=key
        self.value=value
        self.setupUi()
    
    def __settingChanged(self):
        self.settingChanged.emit(self.getSetting())
    
    def getSetting(self):
        return {self.label.text():self.getValue()}

    def getValue(self):
        if isinstance(self.valueEdit, SwitchButton):
            value = self.valueEdit.isChecked()
        elif isinstance(self.valueEdit, (SpinBox, DoubleSpinBox)):
            value = self.valueEdit.value()
        else:
            value = self.valueEdit.text()
        return value

class Debug(ScrollArea):
    settingChanged=pyqtSignal(dict)
    def __init__(self,setting:dict):
        super().__init__()
        self.setting=setting
        self.setupUi()
        
    def setupUi(self):
        self.setObjectName("Debug")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(QWidget())
        
        layout=QVBoxLayout()
        self.setting_list=[]
        self.settingItemMap=dict()
        for key,value in self.setting.items():
            item=SettingItem(key,value)
            self.setting_list.append(item)
            item.settingChanged.connect(self.updateSetting)
            self.settingItemMap[key]=item
            layout.addWidget(item)
        
        self.saveButton=PushButton("Save")
        self.saveButton.clicked.connect(self.saveSetting)
        layout.addWidget(self.saveButton)
        self.widget().setLayout(layout)
    
    def updateSetting(self,setting:dict):
        for key,value in setting.items():
            self.setting[key]=value
        self.settingChanged.emit(setting)

    def getSetting(self,key=None):
        if key is None:
            return {k:self.getValue(k) for k in self.settingItemMap.keys()}
        else:
            return {key:self.getValue(key)}
    
    def getValue(self,key:str):
        return self.settingItemMap[key].getValue()
    
    
    def saveSetting(self):
        print("save",self.getSetting())
        with open("setting.json", "w") as f:
            json.dump(self.getSetting(), f)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app=QApplication(sys.argv)
    debug=Debug({
        "host":"127.0.0.1",
        "port":30042,
        "insecure":True,
        "source_device_id":1
    })
    debug.show()
    sys.exit(app.exec_())