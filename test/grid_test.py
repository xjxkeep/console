import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QGridLayout, QLabel, 
                            QLineEdit, QPushButton, QTextEdit, QCheckBox,
                            QComboBox, QRadioButton, QGroupBox)
from PyQt5.QtCore import Qt


class GridLayoutDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # 窗口基本设置
        self.setWindowTitle("QGridLayout 完整示例")
        self.setGeometry(300, 300, 800, 500)  # 位置(x,y)和大小(w,h)

        # 创建网格布局（核心布局）
        grid = QGridLayout()
        grid.setSpacing(10)  # 控件之间的间距（像素）
        grid.setContentsMargins(20, 20, 20, 20)  # 布局边缘与窗口的间距

        # --------------------------
        # 1. 第一行：标题（跨3列）
        # --------------------------
        title = QLabel("网格布局信息录入系统")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        # 添加到网格：行0，列0，跨1行，跨3列，居中对齐
        grid.addWidget(title, 0, 0, 1, 3, Qt.AlignCenter)

        # --------------------------
        # 2. 第二行到第五行：表单控件
        # --------------------------
        # 行1：姓名标签 + 输入框（输入框跨2列）
        grid.addWidget(QLabel("姓名："), 1, 0, Qt.AlignRight | Qt.AlignVCenter)  # 标签右对齐+垂直居中
        self.name_edit = QLineEdit()
        grid.addWidget(self.name_edit, 1, 1, 1, 2)  # 跨2列

        # 行2：性别标签 + 单选框组（跨2列）
        grid.addWidget(QLabel("性别："), 2, 0, Qt.AlignRight | Qt.AlignVCenter)
        gender_group = QGroupBox()  # 用分组框包裹单选框（互斥）
        gender_layout = QGridLayout(gender_group)
        self.male_radio = QRadioButton("男")
        self.female_radio = QRadioButton("女")
        self.male_radio.setChecked(True)
        gender_layout.addWidget(self.male_radio, 0, 0)
        gender_layout.addWidget(self.female_radio, 0, 1)
        grid.addWidget(gender_group, 2, 1, 1, 2)  # 跨2列

        # 行3：爱好标签 + 复选框（跨2列）
        grid.addWidget(QLabel("爱好："), 3, 0, Qt.AlignRight | Qt.AlignVCenter)
        hobby_layout = QGridLayout()
        self.read_check = QCheckBox("阅读")
        self.sport_check = QCheckBox("运动")
        self.game_check = QCheckBox("游戏")
        hobby_layout.addWidget(self.read_check, 0, 0)
        hobby_layout.addWidget(self.sport_check, 0, 1)
        hobby_layout.addWidget(self.game_check, 0, 2)
        # 用一个容器包裹复选框布局，再添加到网格
        hobby_widget = QWidget()
        hobby_widget.setLayout(hobby_layout)
        grid.addWidget(hobby_widget, 3, 1, 1, 2)  # 跨2列

        # 行4：职业标签 + 下拉框（跨2列）
        grid.addWidget(QLabel("职业："), 4, 0, Qt.AlignRight | Qt.AlignVCenter)
        self.job_combo = QComboBox()
        self.job_combo.addItems(["学生", "教师", "工程师", "其他"])
        grid.addWidget(self.job_combo, 4, 1, 1, 2)  # 跨2列

        # --------------------------
        # 3. 第六行到第八行：备注区域（跨3列，占2行高度）
        # --------------------------
        grid.addWidget(QLabel("备注："), 5, 0, Qt.AlignRight | Qt.AlignTop)  # 标签顶部对齐
        self.remark_edit = QTextEdit()
        self.remark_edit.setPlaceholderText("请输入备注信息...")
        # 添加到网格：行5，列1，跨3行（行5、6、7），跨2列
        grid.addWidget(self.remark_edit, 5, 1, 3, 2)

        # --------------------------
        # 4. 第九行：按钮区域（跨3列）
        # --------------------------
        btn_layout = QGridLayout()
        self.submit_btn = QPushButton("提交")
        self.reset_btn = QPushButton("重置")
        self.exit_btn = QPushButton("退出")
        
        # 按钮添加到子布局（设置拉伸权重，让按钮均匀分布）
        btn_layout.addWidget(self.submit_btn, 0, 0)
        btn_layout.addWidget(self.reset_btn, 0, 1)
        btn_layout.addWidget(self.exit_btn, 0, 2)
        btn_layout.setColumnStretch(0, 1)  # 三列按钮平均分配宽度
        btn_layout.setColumnStretch(1, 1)
        btn_layout.setColumnStretch(2, 1)
        
        # 子布局添加到主网格（跨3列）
        grid.addLayout(btn_layout, 8, 0, 1, 3)

        # --------------------------
        # 设置行列拉伸权重（关键！控制窗口缩放时的空间分配）
        # --------------------------
        # 列拉伸：第0列（标签列）不拉伸，第1、2列（内容列）拉伸
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        
        # 行拉伸：备注区域（行5-7）拉伸，其他行不拉伸
        for row in range(9):
            if 5 <= row <=7:
                grid.setRowStretch(row, 1)  # 备注区域占主要拉伸空间
            else:
                grid.setRowStretch(row, 0)

        # 绑定按钮事件
        self.submit_btn.clicked.connect(self.submit_info)
        self.reset_btn.clicked.connect(self.reset_info)
        self.exit_btn.clicked.connect(self.close)

        # 设置窗口主布局
        self.setLayout(grid)

    def submit_info(self):
        """提交信息并弹窗显示"""
        # 收集表单数据
        gender = "男" if self.male_radio.isChecked() else "女"
        hobbies = []
        if self.read_check.isChecked():
            hobbies.append("阅读")
        if self.sport_check.isChecked():
            hobbies.append("运动")
        if self.game_check.isChecked():
            hobbies.append("游戏")
        hobby_str = ",".join(hobbies) if hobbies else "无"

        # 显示提交结果（这里简化为打印，实际可改为弹窗）
        result = (
            f"提交成功！\n"
            f"姓名：{self.name_edit.text()}\n"
            f"性别：{gender}\n"
            f"爱好：{hobby_str}\n"
            f"职业：{self.job_combo.currentText()}\n"
            f"备注：{self.remark_edit.toPlainText()}"
        )
        print(result)  # 实际开发中可替换为 QMessageBox.information

    def reset_info(self):
        """重置表单"""
        self.name_edit.clear()
        self.male_radio.setChecked(True)
        self.read_check.setChecked(False)
        self.sport_check.setChecked(False)
        self.game_check.setChecked(False)
        self.job_combo.setCurrentIndex(0)
        self.remark_edit.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GridLayoutDemo()
    window.show()
    sys.exit(app.exec_())