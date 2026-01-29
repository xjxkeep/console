from PyQt5.QtWidgets import *
from qfluentwidgets import *
from qfluentwidgets import ScrollArea
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal
from pkg.model import Setting
import logging

class NumberSpinBox(QWidget):
    valueChanged=pyqtSignal(int)
    def __init__(self,value:int):
        super().__init__()
        self.__value=value
        self.setupUi()

    def setupUi(self):
        self.setLayout(QHBoxLayout())
        self.input=LineEdit()
        self.input.setText(str(self.__value))
        self.input.textChanged.connect(self.__inputChanged)
        self.layout().addWidget(self.input)
    
    def __inputChanged(self,text:str):
        try:
            self.__value=int(text)
            self.valueChanged.emit(self.__value)
        except ValueError:
            pass
    def value(self):
        return self.__value
    
    def setValue(self,value:int):
        self.__value=value
        self.input.setText(str(self.__value))

class SettingItem(QWidget):
    settingChanged=pyqtSignal(dict)
    def setupUi(self):
        self.setLayout(QHBoxLayout())
        self.label=BodyLabel(self.key)
        # Choose widget based on value type
        if isinstance(self.value, bool):
            self.valueEdit = SwitchButton()
            self.valueEdit.setOnText("True")
            self.valueEdit.setOffText("False")
            self.valueEdit.setChecked(self.value)
            self.valueEdit.checkedChanged.connect(self.__settingChanged)
        elif isinstance(self.value, (int, float)):
            self.valueEdit = NumberSpinBox(self.value)
            self.valueEdit.setValue(self.value)
            self.valueEdit.valueChanged.connect(self.__settingChanged)
        else:
            # Default to LineEdit for strings and other types
            self.valueEdit = LineEdit()
            self.valueEdit.setText(self.value)
            self.valueEdit.textChanged.connect(self.__settingChanged)
        self.layout().addWidget(self.label)
        self.layout().addWidget(self.valueEdit)

    def setValue(self,value):
        self.value=value
        if isinstance(self.valueEdit, SwitchButton):
            self.valueEdit.setChecked(value)
        elif isinstance(self.valueEdit, (SpinBox, DoubleSpinBox,NumberSpinBox)):
            self.valueEdit.setValue(value)
        else:
            self.valueEdit.setText(value)

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
        elif isinstance(self.valueEdit, (SpinBox, DoubleSpinBox,NumberSpinBox)):
            value = self.valueEdit.value()
        else:
            value = self.valueEdit.text()
        return value

class Debug(ScrollArea):
    settingChanged=pyqtSignal(dict)
    def __init__(self,setting:Setting):
        super().__init__()
        self.setting=setting
        self.setupUi()
        
    def setupUi(self):
        self.setObjectName("Debug")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(QWidget())
        
        layout=QVBoxLayout()
        
        # 添加日志级别选择器
        log_level_group = HeaderCardWidget("日志设置")
        log_level_layout = QHBoxLayout()
        log_level_layout.addWidget(BodyLabel("日志级别:"))
        
        self.log_level_combo = ComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        
        # 设置当前日志级别
        from pkg.log_manager import log_manager
        # 优先从设置中读取，如果没有则使用日志管理器的当前级别
        if hasattr(self.setting, 'log_level') and self.setting.log_level:
            current_level = self.setting.log_level
            # 同步到日志管理器
            log_manager.set_log_level(current_level)
        else:
            current_level = log_manager.get_log_level()
            # 同步到设置
            self.setting.log_level = current_level
        
        self.log_level_combo.setCurrentText(current_level)
        
        self.log_level_combo.currentTextChanged.connect(self.change_log_level)
        log_level_layout.addWidget(self.log_level_combo)
        
        self.log_level_button = PushButton("应用")
        self.log_level_button.clicked.connect(self.apply_log_level)
        log_level_layout.addWidget(self.log_level_button)
        
        # 添加日志管理按钮
        log_manage_layout = QHBoxLayout()
        self.clear_log_button = PushButton("清空日志")
        self.clear_log_button.clicked.connect(self.clear_log_file)
        log_manage_layout.addWidget(self.clear_log_button)
        
        self.rotate_log_button = PushButton("轮转日志")
        self.rotate_log_button.clicked.connect(self.rotate_log_file)
        log_manage_layout.addWidget(self.rotate_log_button)
        
        log_level_layout.addLayout(log_manage_layout)
        log_level_group.viewLayout.addLayout(log_level_layout)
        layout.addWidget(log_level_group)
        
        # 添加日志查看器
        from pkg.log_viewer import LogViewer
        self.log_viewer = LogViewer()
        layout.addWidget(self.log_viewer)
        
        self.setting_list=[]
        self.settingItemMap=dict()
        for key,value in self.setting.model_dump().items():
            logging.info(f"key {key} value {value}")
            if key=="channels":
                continue
            item=SettingItem(key,value)
            self.setting_list.append(item)
            item.settingChanged.connect(self.updateSetting)
            self.settingItemMap[key]=item
            layout.addWidget(item)
        
        self.saveButton=PushButton("Save")
        self.saveButton.clicked.connect(self.saveSetting)
        layout.addWidget(self.saveButton)
        self.widget().setLayout(layout)
        self.enableTransparentBackground()
    
    def updateSetting(self,setting:dict):
        for key,value in setting.items():
            setattr(self.setting,key,value)
        self.settingChanged.emit(setting)


    def setValue(self,key:str,value):
        if key in self.settingItemMap:
            self.settingItemMap[key].setValue(value)

    def getSetting(self,key=None):
        if key is None:
            return {k:self.getValue(k) for k in self.settingItemMap.keys()}
        else:
            return {key:self.getValue(key)}
    
    def getValue(self,key:str):
        return self.settingItemMap[key].getValue()
    
    
    def saveSetting(self):
        """保存设置到 QSettings"""
        logging.info(f"save {self.getSetting()}")
        # 更新 setting 对象的值
        for key, value in self.getSetting().items():
            if hasattr(self.setting, key):
                setattr(self.setting, key, value)
        # 同步到磁盘
        self.setting.sync()
    
    def change_log_level(self, level_text):
        """日志级别选择改变时的处理"""
        logging.info(f"日志级别选择改变为: {level_text}")
    
    def apply_log_level(self):
        """应用日志级别设置"""
        level_text = self.log_level_combo.currentText()
        
        # 使用日志管理器设置级别
        from pkg.log_manager import log_manager
        success = log_manager.set_log_level(level_text)
        
        if success:
            # 更新设置
            self.setting.log_level = level_text
            self.settingChanged.emit({"log_level": level_text})
            self.setValue("log_level", level_text)
    
            # 显示确认消息
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.success(
                title="设置成功",
                content=f"日志级别已设置为 {level_text} ",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        else:
            # 显示错误消息
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.error(
                title="设置失败",
                content=f"无法设置日志级别为 {level_text}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
    
    def save_log_level_setting(self):
        """保存日志级别设置到 QSettings"""
        try:
            # 同步到磁盘
            self.setting.sync()
            logging.info(f"日志级别设置已保存: {self.setting.log_level}")

        except Exception as e:
            logging.error(f"保存日志级别设置时出错: {e}")
            # 显示错误提示
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.warning(
                title="保存失败",
                content=f"无法保存日志级别设置: {e}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def clear_log_file(self):
        """清空日志文件"""
        from pkg.log_manager import log_manager
        log_manager.clear_log_file()
        
        # 显示确认消息
        from qfluentwidgets import InfoBar, InfoBarPosition
        InfoBar.success(
            title="操作成功",
            content="日志文件已清空",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    def rotate_log_file(self):
        """轮转日志文件"""
        from pkg.log_manager import log_manager
        log_manager.rotate_log_file()
        
        # 显示确认消息
        from qfluentwidgets import InfoBar, InfoBarPosition
        InfoBar.success(
            title="操作成功",
            content="日志文件已轮转",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app=QApplication(sys.argv)
    debug=Debug(Setting())
    debug.show()
    sys.exit(app.exec_())