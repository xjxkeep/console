import sys
import os
import math
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
)
from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal
from PyQt5.QtGui import QPainter, QBrush, QPen, QColor, QFont, QRadialGradient
from qfluentwidgets import (
    FluentWindow,
    SubtitleLabel,
    PushButton,
    Theme,
    components,
    setTheme,
    GroupHeaderCardWidget,
    SpinBox,
    BodyLabel,
)

if __name__ == "__main__" and __package__ is None:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from components.channel import ChannelDisp


class ThrottleCurveView(QWidget):
    value_changed = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._k = 0.0
        self._input_value = 50.0
        self._points = []
        self.setMinimumHeight(220)

    def set_parameters(self, k: float):
        self._k = max(-1.0, min(1.0, k))
        self.update()

    def set_input_value(self, value: float):
        self._input_value = max(0.0, min(100.0, value))
        y = self._evaluate(self._input_value)
        self.value_changed.emit(self._input_value, y)
        self.update()

    def _evaluate(self, x: float) -> float:
        t = x / 100.0
        k = self._k
        y = (1.0 - k) * t + k * (t * t * t)
        return max(0.0, min(1.0, y)) * 100.0

    def _build_points(self, rect):
        left = rect.left()
        right = rect.right()
        top = rect.top()
        bottom = rect.bottom()
        width = max(1.0, right - left)
        height = max(1.0, bottom - top)
        pts = []
        for i in range(101):
            x = i
            y = self._evaluate(x)
            px = left + (x / 100.0) * width
            py = bottom - (y / 100.0) * height
            pts.append(QPoint(int(px), int(py)))
        self._points = pts

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(40, 10, -20, -30)
        if rect.width() <= 0 or rect.height() <= 0:
            return

        painter.fillRect(self.rect(), self.palette().window())

        axis_pen = QPen(self.palette().mid().color())
        axis_pen.setWidth(1)
        painter.setPen(axis_pen)
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
        painter.drawLine(rect.left(), rect.top(), rect.left(), rect.bottom())

        grid_pen = QPen(self.palette().midlight().color())
        grid_pen.setStyle(Qt.DashLine)
        painter.setPen(grid_pen)
        for i in range(1, 4):
            y = rect.bottom() - rect.height() * i / 4.0
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))
        for i in range(1, 4):
            x = rect.left() + rect.width() * i / 4.0
            painter.drawLine(int(x), rect.top(), int(x), rect.bottom())

        text_pen = QPen(self.palette().text().color())
        painter.setPen(text_pen)
        font = painter.font()
        font.setPointSize(max(8, font.pointSize()))
        painter.setFont(font)
        for i in range(5):
            x_value = int(100 * i / 4)
            y_value = int(100 * i / 4)
            x_pos = rect.left() + rect.width() * i / 4.0
            y_pos = rect.bottom() - rect.height() * i / 4.0
            painter.drawText(int(x_pos) - 8, rect.bottom() + 18, str(x_value))
            painter.drawText(rect.left() - 30, int(y_pos) + 4, str(y_value))

        self._build_points(rect)
        if self._points:
            curve_pen = QPen(QColor(0, 120, 215))
            curve_pen.setWidth(2)
            painter.setPen(curve_pen)
            for i in range(1, len(self._points)):
                painter.drawLine(self._points[i - 1], self._points[i])

        input_x = self._input_value
        input_y = self._evaluate(input_x)
        px = rect.left() + (input_x / 100.0) * rect.width()
        py = rect.bottom() - (input_y / 100.0) * rect.height()
        marker_pen = QPen(QColor(220, 0, 0))
        marker_pen.setWidth(2)
        painter.setPen(marker_pen)
        painter.setBrush(QColor(220, 0, 0))
        r = 4
        painter.drawEllipse(QPoint(int(px), int(py)), r, r)
        painter.setPen(text_pen)
        painter.drawText(int(px) + 6, int(py) - 6, f"{int(input_y)}")


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


class ThrottleNonlinearityWidget(GroupHeaderCardWidget):
    parameters_changed = pyqtSignal(float)
    preview_changed = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._k = 0.0
        self._input_value = 50.0
        self._curve_view = ThrottleCurveView(self)
        self._curve_view.set_parameters(self._k)
        self._curve_view.set_input_value(self._input_value)
        self._curve_view.value_changed.connect(self._on_curve_value_changed)
        self._init_ui()

    def _init_ui(self):
        self.setTitle("油门非线性")
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(12)

        main_layout.addWidget(self._curve_view)

        param_layout = QHBoxLayout()
        param_layout.setSpacing(10)
        k_label = BodyLabel("非线性强度")
        self.k_spin = SpinBox()
        self.k_spin.setRange(-100, 100)
        self.k_spin.setValue(int(self._k * 100))
        self.k_spin.valueChanged.connect(self._on_k_changed)
        param_layout.addWidget(k_label)
        param_layout.addWidget(self.k_spin)
        param_layout.addStretch(1)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        input_label = BodyLabel("输入预览")
        self.input_slider = QSlider(Qt.Horizontal)
        self.input_slider.setRange(0, 100)
        self.input_slider.setValue(int(self._input_value))
        self.input_slider.valueChanged.connect(self._on_input_changed)
        self.output_label = BodyLabel("输出: 50")
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_slider)
        input_layout.addWidget(self.output_label)

        main_layout.addLayout(param_layout)
        main_layout.addLayout(input_layout)
        self.setLayout(main_layout)

    def _on_k_changed(self, v: int):
        self._k = v / 100.0
        self._curve_view.set_parameters(self._k)
        self.parameters_changed.emit(self._k)
        self._curve_view.set_input_value(self._input_value)

    def _on_input_changed(self, v: int):
        self._input_value = float(v)
        self._curve_view.set_input_value(self._input_value)

    def _on_curve_value_changed(self, x: float, y: float):
        self.output_label.setText(f"输出: {int(y)}")
        self.preview_changed.emit(x, y)

    def get_parameter(self) -> float:
        return self._k

    def get_output(self, x: float) -> float:
        return self._curve_view._evaluate(max(0.0, min(100.0, x)))


class ControlPanel(GroupHeaderCardWidget):
    joystick_changed = pyqtSignal(float, float)
    def __init__(self):
        super().__init__()
        self.initUI()
        # self.setFixedSize(400, 600)

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
        self.channelDisp=ChannelDisp()
        joystick_layout.addWidget(self.channelDisp, alignment=Qt.AlignCenter)
        # 数值显示标签
        self.value_label = QLabel("X: 0.00  Y: 0.00")
        self.value_label.setFont(QFont("Microsoft YaHei", 12))
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("color: #ffffff; background-color: rgba(0, 0, 0, 100); padding: 8px; border-radius: 8px;")
        joystick_layout.addWidget(self.value_label, alignment=Qt.AlignCenter)
        
        # 连接摇杆信号
        self.joystick.position_changed.connect(self.on_joystick_changed)
        
        main_layout.addLayout(joystick_layout)    
        main_layout.addStretch(1)
        self.vBoxLayout.addLayout(main_layout)

    def on_joystick_changed(self, x, y):
        """摇杆位置变化回调"""
        self.value_label.setText(f"X: {x:.2f}  Y: {y:.2f}")
        self.channelDisp.setJoystickValue(x,y)
        self.joystick_changed.emit(x,y)



    def centerWindow(self):
        """窗口居中显示"""
        qr = self.frameGeometry()
        cp = QApplication.desktop().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei"))
    main = QWidget()
    layout = QVBoxLayout(main)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(16)
    throttle = ThrottleNonlinearityWidget()
    layout.addWidget(throttle)
    main.setWindowTitle("油门非线性调节示例")
    main.resize(600, 400)
    main.show()
    sys.exit(app.exec_())
