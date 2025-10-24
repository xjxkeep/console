import sys
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel)
from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal
from PyQt5.QtGui import QPainter, QBrush, QPen, QColor, QFont, QRadialGradient
from qfluentwidgets import (FluentWindow, SubtitleLabel, PushButton,
                           Theme, setTheme,GroupHeaderCardWidget)


class JoystickController(QWidget):
    """模拟摇杆组件 - 提供X/Y坐标输出和视觉反馈"""
    
    # 信号定义：摇杆位置变化时发出信号
    position_changed = pyqtSignal(float, float)  # x, y 坐标 (-1.0 到 1.0)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.setAttribute(Qt.WA_TranslucentBackground)
       
        # 摇杆状态
        self._center_pos = QPoint(0, 0)  # 相对中心的偏移量
        # 创建动画使回到中心更平滑
        self.animation = QPropertyAnimation(self, b"center_pos")
        self.animation.setDuration(200)  # 动画时长200ms
        self.animation.setEndValue(QPoint(0, 0))  # 目标位置：中心
        self.animation.setEasingCurve(QEasingCurve.OutBack)  # 缓动曲线，有回弹效果
        
        self.is_dragging = False         # 是否正在拖动
        self.outer_radius = 0            # 外圆半径（动态计算）
        self.inner_radius = 0            # 内圆半径（动态计算）
        self.max_distance = 0            # 最大拖动距离
        
        # 摇杆数值 (-1.0 到 1.0)
        self._x_value = 0.0
        self._y_value = 0.0

    def resizeEvent(self, event):
        """窗口大小变化时重新计算半径"""
        super().resizeEvent(event)
        self.outer_radius = min(self.width(), self.height()) // 2 - 15
        self.inner_radius = self.outer_radius // 4
        self.max_distance = self.outer_radius - self.inner_radius

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # 抗锯齿
        
        # 计算控件中心坐标
        center_x = self.width() // 2
        center_y = self.height() // 2

        # 1. 绘制外圆环背景（深色背景）
        painter.setPen(Qt.NoPen)
        gradient = QRadialGradient(center_x, center_y, self.outer_radius)
        gradient.setColorAt(0, QColor(60, 60, 60, 100))
        gradient.setColorAt(1, QColor(40, 40, 40, 150))
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(
            center_x - self.outer_radius,
            center_y - self.outer_radius,
            self.outer_radius * 2,
            self.outer_radius * 2
        )

        # 2. 绘制外圆环边框
        pen = QPen(QColor(100, 100, 100), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(
            center_x - self.outer_radius,
            center_y - self.outer_radius,
            self.outer_radius * 2,
            self.outer_radius * 2
        )

        # 3. 绘制摇杆内圈（有立体感）
        knob_x = center_x + self._center_pos.x()
        knob_y = center_y + self._center_pos.y()
        
        # 内圈阴影效果
        shadow_gradient = QRadialGradient(knob_x + 2, knob_y + 2, self.inner_radius)
        shadow_gradient.setColorAt(0, QColor(0, 0, 0, 80))
        shadow_gradient.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(shadow_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            knob_x - self.inner_radius,
            knob_y - self.inner_radius,
            self.inner_radius * 2,
            self.inner_radius * 2
        )
        
        # 内圈主体（渐变效果）
        knob_gradient = QRadialGradient(knob_x, knob_y, self.inner_radius)
        if self.is_dragging:
            # 拖动时更亮的颜色
            knob_gradient.setColorAt(0, QColor(255, 200, 50))
            knob_gradient.setColorAt(0.7, QColor(255, 140, 0))
            knob_gradient.setColorAt(1, QColor(200, 100, 0))
        else:
            # 默认颜色
            knob_gradient.setColorAt(0, QColor(255, 180, 40))
            knob_gradient.setColorAt(0.7, QColor(255, 120, 0))
            knob_gradient.setColorAt(1, QColor(180, 80, 0))
        
        painter.setBrush(QBrush(knob_gradient))
        painter.setPen(QPen(QColor(140, 70, 0), 1))
        painter.drawEllipse(
            knob_x - self.inner_radius,
            knob_y - self.inner_radius,
            self.inner_radius * 2,
            self.inner_radius * 2
        )
        
        # 4. 绘制中心点（小圆点）
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 150)))
        center_dot_radius = 3
        painter.drawEllipse(
            knob_x - center_dot_radius,
            knob_y - center_dot_radius,
            center_dot_radius * 2,
            center_dot_radius * 2
        )

    def mousePressEvent(self, event):
        """鼠标按下时判断是否点击在摇杆范围内"""
        if event.button() == Qt.LeftButton:
            # 计算鼠标相对控件中心的位置
            center_x = self.width() // 2
            center_y = self.height() // 2
            mouse_pos = event.pos()
            relative_pos = QPoint(mouse_pos.x() - center_x, mouse_pos.y() - center_y)
            
            # 检查是否在摇杆范围内（外圆内）
            distance = (relative_pos.x()**2 + relative_pos.y()**2)**0.5
            if distance <= self.outer_radius:
                self.is_dragging = True
                self.setCursor(Qt.ClosedHandCursor)
                # 立即更新位置
                self._update_position(relative_pos)

    def mouseMoveEvent(self, event):
        """鼠标拖动时更新摇杆位置"""
        if self.is_dragging:
            # 计算鼠标相对控件中心的偏移
            center_x = self.width() // 2
            center_y = self.height() // 2
            mouse_pos = event.pos()
            new_pos = QPoint(mouse_pos.x() - center_x, mouse_pos.y() - center_y)
            
            self._update_position(new_pos)

    def mouseReleaseEvent(self, event):
        """鼠标松开时返回原点（带动画）"""
        if event.button() == Qt.LeftButton and self.is_dragging:
            print("mouseReleaseEvent")
            self.is_dragging = False
            self.setCursor(Qt.ArrowCursor)  # 恢复鼠标样式
            
            
          
            self.animation.setStartValue(self._center_pos)  # 设置起始位置
            
            # 连接动画完成信号，确保归位完成
            self.animation.finished.connect(lambda: self._ensure_centered())
            self.animation.start()

    def _update_position(self, pos):
        """更新摇杆位置并计算数值"""
        # 计算距离
        distance = (pos.x()**2 + pos.y()**2)**0.5
        
        # 限制在最大范围内
        if distance > self.max_distance:
            ratio = self.max_distance / distance
            pos.setX(int(pos.x() * ratio))
            pos.setY(int(pos.y() * ratio))
            distance = self.max_distance
        
        # 更新位置
        self._center_pos = pos
        self.update()
        
        # 计算并更新数值 (-1.0 到 1.0)
        if self.max_distance > 0:
            self._x_value = pos.x() / self.max_distance
            self._y_value = -pos.y() / self.max_distance  # Y轴反向（向上为正）
        else:
            self._x_value = 0.0
            self._y_value = 0.0
        
        # 发出位置变化信号
        self.position_changed.emit(self._x_value, self._y_value)

    def _ensure_centered(self):
        """确保摇杆归位到中心"""
        if self._center_pos != QPoint(0, 0):
            self._center_pos = QPoint(0, 0)
            self._x_value = 0.0
            self._y_value = 0.0
            self.update()
            self.position_changed.emit(0.0, 0.0)

    # 为动画提供属性访问接口（使用pyqtProperty装饰器）
    @pyqtProperty(QPoint)
    def center_pos(self):
        return self._center_pos

    @center_pos.setter
    def center_pos(self, pos):
        self._center_pos = pos  # 赋值给内部变量，避免递归
        # 重新计算数值
        if self.max_distance > 0:
            self._x_value = pos.x() / self.max_distance
            self._y_value = -pos.y() / self.max_distance
        else:
            self._x_value = 0.0
            self._y_value = 0.0
        self.update()
        self.position_changed.emit(self._x_value, self._y_value)
    
    def get_values(self):
        """获取摇杆当前数值"""
        return self._x_value, self._y_value
    
    def set_values(self, x, y):
        """设置摇杆数值（-1.0 到 1.0）"""
        x = max(-1.0, min(1.0, x))
        y = max(-1.0, min(1.0, y))
        
        pos_x = int(x * self.max_distance)
        pos_y = int(-y * self.max_distance)  # Y轴反向
        
        self._center_pos = QPoint(pos_x, pos_y)
        self._x_value = x
        self._y_value = y
        print(f"set_values: x={x}, y={y}")
        self.update()
        self.position_changed.emit(self._x_value, self._y_value)

class ButtonController(QWidget):
    """按钮控制器 - 十字布局的方向控制按钮"""
    
    # 信号定义
    forward_changed = pyqtSignal(int)      # 前进信号: 0(释放), 1(按下)
    backward_changed = pyqtSignal(int)     # 后退信号: 0(释放), 1(按下)
    left_changed = pyqtSignal(int)         # 左转信号: 0(释放), 1(按下)
    right_changed = pyqtSignal(int)        # 右转信号: 0(释放), 1(按下)
    emergency_triggered = pyqtSignal()     # 急停信号: 触发时发出
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        """初始化按钮布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(15)
        
        # 第一行：前进按钮
        row1 = QHBoxLayout()
        row1.setAlignment(Qt.AlignCenter)
        self.btn_forward = PushButton("↑ 前进")
        self.btn_forward.setMinimumHeight(60)
        self.btn_forward.setMinimumWidth(120)
        self.btn_forward.setFont(QFont("Microsoft YaHei", 12))
        row1.addWidget(self.btn_forward)
        main_layout.addLayout(row1)
        
        # 第二行：左转、急停、右转
        row2 = QHBoxLayout()
        row2.setAlignment(Qt.AlignCenter)
        row2.setSpacing(15)
        
        self.btn_left = PushButton("← 左转")
        self.btn_left.setMinimumHeight(60)
        self.btn_left.setMinimumWidth(120)
        self.btn_left.setFont(QFont("Microsoft YaHei", 12))
        
        # 急停按钮（红色，更大）
        self.btn_emergency = PushButton("急停")
        self.btn_emergency.setMinimumHeight(80)
        self.btn_emergency.setMinimumWidth(80)
        self.btn_emergency.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        # 设置急停按钮样式为红色
        self.btn_emergency.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                border: 2px solid #b71c1c;
                border-radius: 40px;
            }
            QPushButton:hover {
                background-color: #f44336;
                border: 2px solid #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
                border: 2px solid #8b0000;
            }
        """)
        
        self.btn_right = PushButton("→ 右转")
        self.btn_right.setMinimumHeight(60)
        self.btn_right.setMinimumWidth(120)
        self.btn_right.setFont(QFont("Microsoft YaHei", 12))
        
        row2.addWidget(self.btn_left)
        row2.addWidget(self.btn_emergency)
        row2.addWidget(self.btn_right)
        main_layout.addLayout(row2)
        
        # 第三行：后退按钮
        row3 = QHBoxLayout()
        row3.setAlignment(Qt.AlignCenter)
        self.btn_backward = PushButton("↓ 后退")
        self.btn_backward.setMinimumHeight(60)
        self.btn_backward.setMinimumWidth(120)
        self.btn_backward.setFont(QFont("Microsoft YaHei", 12))
        row3.addWidget(self.btn_backward)
        main_layout.addLayout(row3)
        
        # 连接按钮信号
        self.btn_forward.pressed.connect(lambda: self.forward_changed.emit(1))
        self.btn_forward.released.connect(lambda: self.forward_changed.emit(0))
        
        self.btn_backward.pressed.connect(lambda: self.backward_changed.emit(1))
        self.btn_backward.released.connect(lambda: self.backward_changed.emit(0))
        
        self.btn_left.pressed.connect(lambda: self.left_changed.emit(1))
        self.btn_left.released.connect(lambda: self.left_changed.emit(0))
        
        self.btn_right.pressed.connect(lambda: self.right_changed.emit(1))
        self.btn_right.released.connect(lambda: self.right_changed.emit(0))
        
        self.btn_emergency.clicked.connect(self.emergency_triggered.emit)
    
    def get_buttons(self):
        """获取所有按钮的引用"""
        return {
            'forward': self.btn_forward,
            'backward': self.btn_backward,
            'left': self.btn_left,
            'right': self.btn_right,
            'emergency': self.btn_emergency
        }




class ControlPanel(GroupHeaderCardWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.setFixedSize(400, 600)

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(20)

        self.setTitle("实时控制")

        # 圆形控制区（居中显示）
        joystick_layout = QVBoxLayout()
        joystick_layout.setAlignment(Qt.AlignCenter)
        
        # 摇杆组件
        self.joystick = JoystickController()
        joystick_layout.addWidget(self.joystick, alignment=Qt.AlignCenter)
        
        # 数值显示标签
        self.value_label = QLabel("X: 0.00  Y: 0.00")
        self.value_label.setFont(QFont("Microsoft YaHei", 12))
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("color: #ffffff; background-color: rgba(0, 0, 0, 100); padding: 8px; border-radius: 8px;")
        joystick_layout.addWidget(self.value_label, alignment=Qt.AlignCenter)
        
        # 连接摇杆信号
        self.joystick.position_changed.connect(self.on_joystick_changed)
        
        main_layout.addLayout(joystick_layout)

        # 方向按钮区域 - 使用ButtonController组件
        self.button_controller = ButtonController()
        main_layout.addWidget(self.button_controller)
        
        # 连接按钮信号
        self.button_controller.forward_changed.connect(self.on_forward_changed)
        self.button_controller.backward_changed.connect(self.on_backward_changed)
        self.button_controller.left_changed.connect(self.on_left_changed)
        self.button_controller.right_changed.connect(self.on_right_changed)
        self.button_controller.emergency_triggered.connect(self.on_emergency_stop)
        
        # 底部留白
        main_layout.addStretch(1)
        
        self.vBoxLayout.addLayout(main_layout)

    def on_joystick_changed(self, x, y):
        """摇杆位置变化回调"""
        self.value_label.setText(f"X: {x:.2f}  Y: {y:.2f}")
        
        # 这里可以添加你的控制逻辑
        # 例如：发送控制命令、更新机器人位置等
        if abs(x) > 0.1 or abs(y) > 0.1:  # 只有移动超过阈值才处理
            print(f"摇杆移动: X={x:.2f}, Y={y:.2f}")

    def on_forward_changed(self, value):
        """前进按钮回调"""
        print(f"前进: {value}")
        # 这里可以添加前进控制逻辑
        # value: 1(按下), 0(释放)

    def on_backward_changed(self, value):
        """后退按钮回调"""
        print(f"后退: {value}")
        # 这里可以添加后退控制逻辑
        # value: 1(按下), 0(释放)

    def on_left_changed(self, value):
        """左转按钮回调"""
        print(f"左转: {value}")
        # 这里可以添加左转控制逻辑
        # value: 1(按下), 0(释放)

    def on_right_changed(self, value):
        """右转按钮回调"""
        print(f"右转: {value}")
        # 这里可以添加右转控制逻辑
        # value: 1(按下), 0(释放)

    def on_emergency_stop(self):
        """急停按钮回调"""
        print("紧急停止！")
        # 这里可以添加急停逻辑
        # 例如：停止所有运动、发送急停命令等
        
        # 可选：显示急停提示
        from PyQt5.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("紧急停止")
        msg.setText("设备已紧急停止")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def centerWindow(self):
        """窗口居中显示"""
        qr = self.frameGeometry()
        cp = QApplication.desktop().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei"))  # 确保中文显示
    window = ControlPanel()
    window.show()
    sys.exit(app.exec_())