import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox
)

class FormLayoutDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # 1. 设置窗口基础属性
        self.setWindowTitle('QFormLayout 用法示例')
        self.resize(400, 300)

        # 2. 创建 QFormLayout 实例
        form_layout = QFormLayout()

        # 3. ------------- 基础用法：添加「标签-字段」对 -------------
        # 方式1：直接传文本（自动创建QLabel）+ 控件
        form_layout.addRow("用户名：", QLineEdit())
        # 方式2：自定义QLabel（可设置样式）+ 控件
        pwd_label = QLabel("密码：")
        pwd_label.setStyleSheet("color: red;")
        form_layout.addRow(pwd_label, QLineEdit())

        # 4. ------------- 高级用法：自定义控件 + 布局调整 -------------
        # 添加下拉框
        form_layout.addRow("性别：", QComboBox())
        # 添加数字输入框
        form_layout.addRow("年龄：", QSpinBox())

        # 5. 跨列：单个控件占整行（无标签）
        submit_btn = QPushButton("提交")
        form_layout.addRow(submit_btn)  # 无标签，控件跨两列

        # 6. 换行：手动插入空行（用空QLabel占位）
        form_layout.addRow(QLabel(""), QLabel("—— 其他设置 ——"))

        # 7. 对齐方式设置
        # 标签对齐：右对齐（默认），可选 Qt.AlignLeft/AlignCenter 等
        form_layout.setLabelAlignment(Qt.AlignRight)
        # 字段对齐：左对齐
        form_layout.setFormAlignment(Qt.AlignLeft)
        # 行包装：当窗口过窄时，标签和字段自动换行（标签在上，字段在下）
        form_layout.setRowWrapPolicy(QFormLayout.WrapLongRows)

        # 8. 间距调整
        form_layout.setSpacing(15)  # 控件间距
        form_layout.setContentsMargins(20, 20, 20, 20)  # 布局边距（上、右、下、左）

        # 9. 将布局设置到窗口
        self.setLayout(form_layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    demo = FormLayoutDemo()
    demo.show()
    sys.exit(app.exec_())