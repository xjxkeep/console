import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                            QGridLayout, QFormLayout, QLabel, QLineEdit, 
                            QComboBox, QPushButton, QTextEdit, QGroupBox,
                            QRadioButton, QCheckBox)
from PyQt5.QtCore import Qt


class LayoutDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # 设置窗口基本属性
        self.setWindowTitle("PyQt5 布局综合示例")
        self.setGeometry(300, 300, 800, 600)  # 窗口位置(x,y)和大小(w,h)

        # 创建主布局（垂直布局，作为整个窗口的容器）
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)  # 主布局边缘间距
        main_layout.setSpacing(15)  # 主布局内各组件间距

        # 1. 添加标题区域（水平布局，居中显示）
        title_layout = QHBoxLayout()
        title_label = QLabel("用户信息管理系统")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        title_layout.addWidget(title_label, alignment=Qt.AlignCenter)
        main_layout.addLayout(title_layout)

        # 2. 添加表单区域（使用QFormLayout）
        form_group = QGroupBox("基本信息")  # 用分组框包裹表单
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)  # 标签右对齐
        form_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)  # 不自动换行

        # 表单控件
        self.name_edit = QLineEdit()
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["男", "女", "保密"])
        self.age_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.phone_edit = QLineEdit()

        # 添加表单行
        form_layout.addRow("姓名：", self.name_edit)
        form_layout.addRow("性别：", self.gender_combo)
        form_layout.addRow("年龄：", self.age_edit)
        form_layout.addRow("邮箱：", self.email_edit)
        form_layout.addRow("电话：", self.phone_edit)

        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)

        # 3. 添加选项区域（使用QGridLayout）
        option_group = QGroupBox("附加选项")
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)  # 网格内间距

        # 网格布局内容（2行2列）
        self.vip_radio = QRadioButton("VIP用户")
        self.normal_radio = QRadioButton("普通用户")
        self.normal_radio.setChecked(True)  # 默认选中普通用户

        self.sms_check = QCheckBox("接收短信通知")
        self.email_check = QCheckBox("接收邮件通知")

        # 添加到网格（行, 列, 跨行列数）
        grid_layout.addWidget(self.vip_radio, 0, 0)
        grid_layout.addWidget(self.normal_radio, 0, 1)
        grid_layout.addWidget(self.sms_check, 1, 0)
        grid_layout.addWidget(self.email_check, 1, 1)

        option_group.setLayout(grid_layout)
        main_layout.addWidget(option_group)

        # 4. 添加按钮区域（使用QHBoxLayout）
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)  # 按钮间距

        self.save_btn = QPushButton("保存")
        self.reset_btn = QPushButton("重置")
        self.exit_btn = QPushButton("退出")

        # 设置按钮拉伸权重（让按钮靠右显示，左侧留空）
        btn_layout.addStretch(1)  # 左侧拉伸项，权重1
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addWidget(self.exit_btn)

        main_layout.addLayout(btn_layout)

        # 5. 添加状态显示区域（占满剩余空间）
        self.status_edit = QTextEdit()
        self.status_edit.setReadOnly(True)  # 只读
        self.status_edit.setPlaceholderText("操作日志将显示在这里...")
        main_layout.addWidget(self.status_edit, stretch=1)  # 拉伸权重1，占满剩余空间

        # 绑定按钮事件
        self.save_btn.clicked.connect(self.save_info)
        self.reset_btn.clicked.connect(self.reset_info)
        self.exit_btn.clicked.connect(self.close)

        # 设置窗口主布局
        self.setLayout(main_layout)

    def save_info(self):
        """保存信息到状态区"""
        info = (
            f"保存成功！\n"
            f"姓名：{self.name_edit.text()}\n"
            f"性别：{self.gender_combo.currentText()}\n"
            f"年龄：{self.age_edit.text()}\n"
            f"邮箱：{self.email_edit.text()}\n"
            f"电话：{self.phone_edit.text()}\n"
            f"用户类型：{'VIP' if self.vip_radio.isChecked() else '普通'}\n"
            f"通知设置：{'短信' if self.sms_check.isChecked() else ''}{' + 邮件' if self.email_check.isChecked() else ''}\n"
            f"-------------------------\n"
        )
        self.status_edit.insertPlainText(info)

    def reset_info(self):
        """重置表单"""
        self.name_edit.clear()
        self.gender_combo.setCurrentIndex(0)
        self.age_edit.clear()
        self.email_edit.clear()
        self.phone_edit.clear()
        self.normal_radio.setChecked(True)
        self.sms_check.setChecked(False)
        self.email_check.setChecked(False)
        self.status_edit.insertPlainText("已重置表单\n-------------------------\n")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LayoutDemo()
    window.show()
    sys.exit(app.exec_())