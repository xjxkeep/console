#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
油门非线性曲线组件
用于显示和调整油门输入到输出的非线性映射关系
"""

import sys
import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QApplication, QLabel, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QPointF
from PyQt5.QtGui import (
    QPainter, QPen, QColor, QFont, QBrush, QPainterPath,
    QLinearGradient
)

try:
    from qfluentwidgets import (
        Slider, PushButton, BodyLabel, CardWidget,
        TransparentPushButton, FluentIcon, ComboBox,
        isDarkTheme
    )
    HAS_FLUENT = True
except ImportError:
    HAS_FLUENT = False
    def isDarkTheme():
        return True


class CurveFunction:
    """非线性曲线函数定义"""

    # 可用的曲线函数类型
    EXPO = "expo"              # 指数混合曲线
    POLYNOMIAL = "polynomial"  # 多项式曲线
    SCURVE = "scurve"          # S形曲线
    FLAT_MIDDLE = "flat_middle"  # 中间平坦曲线
    RACING = "racing"          # 竞速曲线（快速响应）

    # 函数信息字典：{id: (显示名称, 描述)}
    FUNCTIONS = {
        EXPO: ("Expo 指数混合", "混合线性和立方曲线，适合通用场景"),
        POLYNOMIAL: ("Polynomial 多项式", "使用幂函数，可调整曲线陡峭程度"),
        SCURVE: ("S-Curve S形曲线", "平滑的S形过渡，中间区域变化较快"),
        FLAT_MIDDLE: ("Flat Middle 中间平坦", "中间区域响应平缓，两端响应快"),
        RACING: ("Racing 竞速", "低油门区快速响应，高油门区精细控制"),
    }

    @classmethod
    def get_function_list(cls) -> list:
        """获取所有支持的非线性函数列表

        Returns:
            list: [(函数ID, 显示名称, 描述), ...]
        """
        return [(fid, name, desc) for fid, (name, desc) in cls.FUNCTIONS.items()]

    @classmethod
    def get_function_ids(cls) -> list:
        """获取所有函数ID列表"""
        return list(cls.FUNCTIONS.keys())

    @classmethod
    def get_function_names(cls) -> list:
        """获取所有函数显示名称列表"""
        return [name for name, _ in cls.FUNCTIONS.values()]

    @classmethod
    def get_function_name(cls, func_id: str) -> str:
        """根据ID获取函数显示名称"""
        if func_id in cls.FUNCTIONS:
            return cls.FUNCTIONS[func_id][0]
        return "Unknown"

    @classmethod
    def get_function_description(cls, func_id: str) -> str:
        """根据ID获取函数描述"""
        if func_id in cls.FUNCTIONS:
            return cls.FUNCTIONS[func_id][1]
        return ""


class ThrottleCurveWidget(QWidget):
    """
    油门非线性曲线显示组件

    显示一个图表，x轴是输入油门(0-100%)，y轴是输出油门(0-100%)
    支持显示当前油门输入值的垂直指示线和交点高亮
    支持多种非线性函数类型

    Signals:
        curve_changed: 当非线性度改变时发出，参数为当前非线性度值
        value_changed: 当输入值改变时发出，参数为(输入值, 输出值)
        function_changed: 当曲线函数类型改变时发出，参数为函数ID
    """

    curve_changed = pyqtSignal(float)
    value_changed = pyqtSignal(float, float)
    function_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # 当前使用的曲线函数类型
        self._curve_function = CurveFunction.EXPO

        # 非线性度参数 (expo)
        # expo > 0: 曲线在低油门区更平缓（降低灵敏度）
        # expo < 0: 曲线在低油门区更陡峭（提高灵敏度）
        # expo = 0: 线性
        self._expo = 0.0

        # 当前输入值 (0-1)
        self._input_value = 0.0

        # 图表颜色配置 - 根据主题动态设置
        self._update_colors()

        # 绘制参数
        self.padding = 25  # 图表边距（减小以占满更多空间）
        self.grid_divisions = 5  # 网格分割数

        # 设置最小尺寸
        self.setMinimumSize(150, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _update_colors(self):
        """根据当前主题更新图表颜色配置（不包括背景）"""
        if isDarkTheme():
            # 深色主题
            self.grid_color = QColor(80, 80, 85)
            self.axis_color = QColor(120, 120, 125)
            self.linear_color = QColor(140, 140, 140, 100)
            self.curve_color = QColor(0, 150, 255)
            self.indicator_color = QColor(255, 165, 0)
            self.intersection_color = QColor(255, 100, 100)
            self.text_color = QColor(200, 200, 200)
            self.fill_color = QColor(0, 150, 255, 30)
        else:
            # 浅色主题
            self.grid_color = QColor(200, 200, 205)
            self.axis_color = QColor(150, 150, 155)
            self.linear_color = QColor(180, 180, 180, 100)
            self.curve_color = QColor(0, 120, 215)
            self.indicator_color = QColor(255, 140, 0)
            self.intersection_color = QColor(220, 80, 80)
            self.text_color = QColor(80, 80, 80)
            self.fill_color = QColor(0, 120, 215, 25)

    @property
    def expo(self) -> float:
        """获取非线性度参数"""
        return self._expo

    @expo.setter
    def expo(self, value: float):
        """设置非线性度参数，范围 -1 到 1"""
        self._expo = max(-1.0, min(1.0, value))
        self.curve_changed.emit(self._expo)
        self._emit_value_changed()
        self.update()

    @property
    def input_value(self) -> float:
        """获取当前输入值"""
        return self._input_value

    @input_value.setter
    def input_value(self, value: float):
        """设置当前输入值，范围 0 到 1"""
        self._input_value = max(0.0, min(1.0, value))
        self._emit_value_changed()
        self.update()

    def _emit_value_changed(self):
        """发出值变化信号"""
        output = self.calculate_output(self._input_value)
        self.value_changed.emit(self._input_value, output)

    @property
    def curve_function(self) -> str:
        """获取当前曲线函数类型"""
        return self._curve_function

    @curve_function.setter
    def curve_function(self, func_id: str):
        """设置曲线函数类型"""
        if func_id in CurveFunction.FUNCTIONS:
            self._curve_function = func_id
            self.function_changed.emit(func_id)
            self._emit_value_changed()
            self.update()

    def set_curve_function(self, func_id: str):
        """设置曲线函数类型"""
        self.curve_function = func_id

    @staticmethod
    def get_supported_functions() -> list:
        """获取支持的非线性函数列表

        Returns:
            list: [(函数ID, 显示名称, 描述), ...]
        """
        return CurveFunction.get_function_list()

    @staticmethod
    def get_function_ids() -> list:
        """获取支持的函数ID列表"""
        return CurveFunction.get_function_ids()

    @staticmethod
    def get_function_names() -> list:
        """获取支持的函数显示名称列表"""
        return CurveFunction.get_function_names()

    def calculate_output(self, input_val: float) -> float:
        """
        根据当前曲线函数类型和非线性度计算输出值

        支持的曲线类型：
        - expo: 混合线性和立方曲线
        - polynomial: 多项式曲线
        - scurve: S形曲线
        - flat_middle: 中间平坦曲线
        - racing: 竞速曲线

        所有曲线都保证：input=0 -> output=0, input=1 -> output=1
        """
        if self._curve_function == CurveFunction.EXPO:
            return self._calc_expo(input_val)
        elif self._curve_function == CurveFunction.POLYNOMIAL:
            return self._calc_polynomial(input_val)
        elif self._curve_function == CurveFunction.SCURVE:
            return self._calc_scurve(input_val)
        elif self._curve_function == CurveFunction.FLAT_MIDDLE:
            return self._calc_flat_middle(input_val)
        elif self._curve_function == CurveFunction.RACING:
            return self._calc_racing(input_val)
        else:
            return self._calc_expo(input_val)

    def _calc_expo(self, input_val: float) -> float:
        """Expo 指数混合曲线

        output = input * (1 - expo) + input^3 * expo  (当 expo >= 0)
        output = input * (1 + expo) - input^(1/3) * expo  (当 expo < 0)
        """
        if self._expo >= 0:
            linear = input_val
            cubic = input_val ** 3
            return linear * (1 - self._expo) + cubic * self._expo
        else:
            linear = input_val
            cubic_root = np.sign(input_val) * (abs(input_val) ** (1/3)) if input_val != 0 else 0
            return linear * (1 + self._expo) + cubic_root * (-self._expo)

    def _calc_polynomial(self, input_val: float) -> float:
        """Polynomial 多项式曲线

        使用可变指数的幂函数
        expo > 0: 指数增加，曲线更弯曲（低区平缓）
        expo < 0: 指数减小，曲线反向弯曲（低区陡峭）
        """
        # 将 expo (-1, 1) 映射到指数 (0.5, 3)
        # expo = 0 -> power = 1 (线性)
        # expo = 1 -> power = 3
        # expo = -1 -> power = 0.33
        if self._expo >= 0:
            power = 1 + self._expo * 2  # 1 到 3
        else:
            power = 1 / (1 - self._expo * 2)  # 1 到 0.33

        return input_val ** power

    def _calc_scurve(self, input_val: float) -> float:
        """S-Curve S形曲线

        使用 sigmoid 变体，中间区域变化较快
        """
        if input_val <= 0:
            return 0.0
        if input_val >= 1:
            return 1.0

        # 调整 S 曲线的陡峭程度
        # expo > 0: 更陡的 S 曲线
        # expo < 0: 更平缓的 S 曲线
        steepness = 5 + self._expo * 4  # 1 到 9

        # 使用平移后的 sigmoid
        x = (input_val - 0.5) * steepness
        sigmoid = 1 / (1 + np.exp(-x))

        # 归一化到 0-1 范围
        x_min = -0.5 * steepness
        x_max = 0.5 * steepness
        sig_min = 1 / (1 + np.exp(-x_min))
        sig_max = 1 / (1 + np.exp(-x_max))

        return (sigmoid - sig_min) / (sig_max - sig_min)

    def _calc_flat_middle(self, input_val: float) -> float:
        """Flat Middle 中间平坦曲线

        中间区域响应平缓，两端响应快
        """
        # 使用分段函数
        # expo 控制中间平坦区域的大小
        flat_zone = 0.3 + self._expo * 0.2  # 0.1 到 0.5

        if input_val <= 0.5 - flat_zone / 2:
            # 低区：快速上升
            t = input_val / (0.5 - flat_zone / 2)
            return 0.5 * t * t
        elif input_val >= 0.5 + flat_zone / 2:
            # 高区：快速上升
            t = (input_val - 0.5 - flat_zone / 2) / (0.5 - flat_zone / 2)
            return 0.5 + 0.5 * (2 * t - t * t)
        else:
            # 中间平坦区：线性缓慢变化
            t = (input_val - (0.5 - flat_zone / 2)) / flat_zone
            return 0.5 * (1 - flat_zone) + t * flat_zone * 0.5

    def _calc_racing(self, input_val: float) -> float:
        """Racing 竞速曲线

        低油门区快速响应，高油门区精细控制
        适合需要快速起步的场景
        """
        # 使用对数/指数混合
        # expo > 0: 更激进的快速响应
        # expo < 0: 更保守的响应
        aggressiveness = 0.5 + self._expo * 0.4  # 0.1 到 0.9

        if input_val <= 0:
            return 0.0
        if input_val >= 1:
            return 1.0

        # 使用幂函数的反向形式
        return 1 - (1 - input_val) ** (1 + aggressiveness)

    def set_expo(self, value: float):
        """设置非线性度"""
        self.expo = value

    def set_input_value(self, value: float):
        """设置输入值（0-1范围）"""
        self.input_value = value

    def set_input_percent(self, percent: float):
        """设置输入值（0-100百分比）"""
        self.input_value = percent / 100.0

    def increase_expo(self, delta: float = 0.1):
        """增加非线性度"""
        self.expo = self._expo + delta

    def decrease_expo(self, delta: float = 0.1):
        """减少非线性度"""
        self.expo = self._expo - delta

    def paintEvent(self, event):
        """绘制事件"""
        # 每次绑制前更新颜色，以适应主题切换
        self._update_colors()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 获取绘制区域
        rect = self.rect()
        width = rect.width()
        height = rect.height()

        # 计算图表区域（尽可能占满空间）
        margin = self.padding
        chart_left = margin
        chart_top = margin // 2
        chart_width = width - margin * 1.3
        chart_height = height - margin * 1.2

        # 不填充背景，使用父组件的背景（跟随 qfluentwidgets 主题）

        # 绘制网格
        self._draw_grid(painter, chart_left, chart_top, chart_width, chart_height)

        # 绘制坐标轴
        self._draw_axes(painter, chart_left, chart_top, chart_width, chart_height)

        # 绘制线性参考线
        self._draw_linear_reference(painter, chart_left, chart_top, chart_width, chart_height)

        # 绘制非线性曲线
        self._draw_curve(painter, chart_left, chart_top, chart_width, chart_height)

        # 绘制当前输入指示线和交点
        self._draw_indicator(painter, chart_left, chart_top, chart_width, chart_height)

        # 绘制简化的标签
        self._draw_labels(painter, chart_left, chart_top, chart_width, chart_height)

        # 绘制信息（右上角）
        self._draw_info(painter, width, height)

    def _draw_grid(self, painter, left, top, width, height):
        """绘制网格"""
        painter.setPen(QPen(self.grid_color, 1, Qt.DotLine))

        # 垂直网格线
        for i in range(1, self.grid_divisions):
            x = left + (width * i / self.grid_divisions)
            painter.drawLine(int(x), int(top), int(x), int(top + height))

        # 水平网格线
        for i in range(1, self.grid_divisions):
            y = top + (height * i / self.grid_divisions)
            painter.drawLine(int(left), int(y), int(left + width), int(y))

    def _draw_axes(self, painter, left, top, width, height):
        """绘制坐标轴"""
        painter.setPen(QPen(self.axis_color, 2))

        # X轴
        painter.drawLine(int(left), int(top + height), int(left + width), int(top + height))

        # Y轴
        painter.drawLine(int(left), int(top), int(left), int(top + height))

    def _draw_linear_reference(self, painter, left, top, width, height):
        """绘制线性参考线（对角线）"""
        painter.setPen(QPen(self.linear_color, 1, Qt.DashLine))
        painter.drawLine(int(left), int(top + height), int(left + width), int(top))

    def _draw_curve(self, painter, left, top, width, height):
        """绘制非线性曲线"""
        # 创建曲线路径
        path = QPainterPath()
        fill_path = QPainterPath()

        num_points = 100
        first_point = True

        for i in range(num_points + 1):
            input_val = i / num_points
            output_val = self.calculate_output(input_val)

            # 转换到屏幕坐标
            x = left + input_val * width
            y = top + height - output_val * height

            if first_point:
                path.moveTo(x, y)
                fill_path.moveTo(left, top + height)
                fill_path.lineTo(x, y)
                first_point = False
            else:
                path.lineTo(x, y)
                fill_path.lineTo(x, y)

        # 完成填充路径
        fill_path.lineTo(left + width, top + height)
        fill_path.lineTo(left, top + height)

        # 绘制填充
        painter.fillPath(fill_path, QBrush(self.fill_color))

        # 绘制曲线
        pen = QPen(self.curve_color, 3)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)

    def _draw_indicator(self, painter, left, top, width, height):
        """绘制当前输入指示线和交点"""
        if self._input_value <= 0:
            return

        # 计算指示线位置
        x = left + self._input_value * width
        output_val = self.calculate_output(self._input_value)
        y = top + height - output_val * height

        # 绘制垂直指示线
        painter.setPen(QPen(self.indicator_color, 2, Qt.DashLine))
        painter.drawLine(int(x), int(top), int(x), int(top + height))

        # 绘制水平指示线到交点
        painter.setPen(QPen(self.indicator_color, 1, Qt.DotLine))
        painter.drawLine(int(left), int(y), int(x), int(y))

        # 绘制交点
        intersection_radius = 6
        gradient = QLinearGradient(x - intersection_radius, y - intersection_radius,
                                   x + intersection_radius, y + intersection_radius)
        gradient.setColorAt(0, self.intersection_color)
        gradient.setColorAt(1, self.intersection_color.darker(150))

        painter.setPen(QPen(Qt.white, 2))
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(QPointF(x, y), intersection_radius, intersection_radius)

    def _draw_labels(self, painter, left, top, width, height):
        """绘制简化的坐标轴标签"""
        painter.setPen(self.text_color)
        painter.setFont(QFont("Arial", 8))

        # 只显示 0 和 100
        # X轴: 0 和 100
        painter.drawText(int(left - 5), int(top + height + 12), "0")
        painter.drawText(int(left + width - 15), int(top + height + 12), "100")

        # Y轴: 0 和 100
        painter.drawText(int(left - 18), int(top + height + 4), "0")
        painter.drawText(int(left - 22), int(top + 8), "100")

    def _draw_info(self, painter, width, height):
        """绘制简化的信息"""
        painter.setPen(self.text_color)
        painter.setFont(QFont("Arial", 9))

        # 只显示 Expo 值
        expo_text = f"Expo: {self._expo:+.2f}"
        painter.drawText(int(width - 85), 15, expo_text)


class ThrottleCurveDemo(QWidget):
    """油门曲线演示窗口"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("油门非线性曲线设置")
        self.setGeometry(100, 100, 650, 550)
        self.setStyleSheet("background-color: #1a1a1f;")

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题
        if HAS_FLUENT:
            title = BodyLabel("油门曲线调节")
            title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        else:
            title = QLabel("油门曲线调节")
            title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # 曲线函数选择区域
        func_layout = QHBoxLayout()
        func_layout.setSpacing(10)

        if HAS_FLUENT:
            func_label = BodyLabel("曲线函数:")
            func_label.setStyleSheet("color: white;")
        else:
            func_label = QLabel("曲线函数:")
            func_label.setStyleSheet("color: white;")
        func_layout.addWidget(func_label)

        # 曲线函数下拉菜单
        if HAS_FLUENT:
            self.func_combo = ComboBox()
        else:
            from PyQt5.QtWidgets import QComboBox
            self.func_combo = QComboBox()
            self.func_combo.setStyleSheet("""
                QComboBox {
                    background-color: #3a3a45;
                    color: white;
                    border: 1px solid #4a4a55;
                    border-radius: 5px;
                    padding: 6px 12px;
                    min-width: 200px;
                }
                QComboBox:hover {
                    border-color: #00aaff;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 30px;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 6px solid #888;
                    margin-right: 10px;
                }
                QComboBox QAbstractItemView {
                    background-color: #2a2a35;
                    color: white;
                    selection-background-color: #00aaff;
                    border: 1px solid #4a4a55;
                }
            """)

        # 添加曲线函数选项
        self._func_id_map = {}  # 索引到函数ID的映射
        for idx, (func_id, name, desc) in enumerate(ThrottleCurveWidget.get_supported_functions()):
            self.func_combo.addItem(name)
            self._func_id_map[idx] = func_id

        self.func_combo.currentIndexChanged.connect(self.on_function_changed)
        func_layout.addWidget(self.func_combo)

        # 函数描述标签
        if HAS_FLUENT:
            self.func_desc_label = BodyLabel("")
            self.func_desc_label.setStyleSheet("color: #888; font-size: 12px;")
        else:
            self.func_desc_label = QLabel("")
            self.func_desc_label.setStyleSheet("color: #888; font-size: 12px;")
        func_layout.addWidget(self.func_desc_label, 1)

        layout.addLayout(func_layout)

        # 图表组件
        self.curve_widget = ThrottleCurveWidget()
        layout.addWidget(self.curve_widget, 1)

        # 非线性度控制区域
        expo_layout = QHBoxLayout()
        expo_layout.setSpacing(10)

        if HAS_FLUENT:
            expo_label = BodyLabel("非线性度 (Expo):")
            expo_label.setStyleSheet("color: white;")
        else:
            expo_label = QLabel("非线性度 (Expo):")
            expo_label.setStyleSheet("color: white;")
        expo_layout.addWidget(expo_label)

        # 降低非线性度按钮
        if HAS_FLUENT:
            self.decrease_btn = PushButton("- 降低")
            self.decrease_btn.setFixedWidth(100)
        else:
            self.decrease_btn = QPushButton("- 降低")
            self.decrease_btn.setFixedWidth(100)
            self.decrease_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3a3a45;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px;
                }
                QPushButton:hover {
                    background-color: #4a4a55;
                }
                QPushButton:pressed {
                    background-color: #2a2a35;
                }
            """)
        self.decrease_btn.clicked.connect(self.on_decrease_expo)
        expo_layout.addWidget(self.decrease_btn)

        # 当前值显示
        if HAS_FLUENT:
            self.expo_value_label = BodyLabel("0.00")
            self.expo_value_label.setStyleSheet("color: #00aaff; font-size: 16px; font-weight: bold;")
            self.expo_value_label.setFixedWidth(60)
            self.expo_value_label.setAlignment(Qt.AlignCenter)
        else:
            self.expo_value_label = QLabel("0.00")
            self.expo_value_label.setStyleSheet("color: #00aaff; font-size: 16px; font-weight: bold;")
            self.expo_value_label.setFixedWidth(60)
            self.expo_value_label.setAlignment(Qt.AlignCenter)
        expo_layout.addWidget(self.expo_value_label)

        # 提高非线性度按钮
        if HAS_FLUENT:
            self.increase_btn = PushButton("+ 提高")
            self.increase_btn.setFixedWidth(100)
        else:
            self.increase_btn = QPushButton("+ 提高")
            self.increase_btn.setFixedWidth(100)
            self.increase_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3a3a45;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px;
                }
                QPushButton:hover {
                    background-color: #4a4a55;
                }
                QPushButton:pressed {
                    background-color: #2a2a35;
                }
            """)
        self.increase_btn.clicked.connect(self.on_increase_expo)
        expo_layout.addWidget(self.increase_btn)

        expo_layout.addStretch()
        layout.addLayout(expo_layout)

        # 油门输入滑块
        throttle_layout = QHBoxLayout()
        throttle_layout.setSpacing(10)

        if HAS_FLUENT:
            throttle_label = BodyLabel("油门输入:")
            throttle_label.setStyleSheet("color: white;")
        else:
            throttle_label = QLabel("油门输入:")
            throttle_label.setStyleSheet("color: white;")
        throttle_layout.addWidget(throttle_label)

        if HAS_FLUENT:
            self.throttle_slider = Slider(Qt.Horizontal)
        else:
            from PyQt5.QtWidgets import QSlider
            self.throttle_slider = QSlider(Qt.Horizontal)
            self.throttle_slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    background: #3a3a45;
                    height: 8px;
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: #00aaff;
                    width: 20px;
                    margin: -6px 0;
                    border-radius: 10px;
                }
                QSlider::sub-page:horizontal {
                    background: #0077cc;
                    border-radius: 4px;
                }
            """)
        self.throttle_slider.setRange(0, 100)
        self.throttle_slider.setValue(0)
        self.throttle_slider.valueChanged.connect(self.on_throttle_changed)
        throttle_layout.addWidget(self.throttle_slider, 1)

        # 油门值显示
        if HAS_FLUENT:
            self.throttle_value_label = BodyLabel("0%")
            self.throttle_value_label.setStyleSheet("color: #ffa500; font-size: 14px;")
            self.throttle_value_label.setFixedWidth(50)
        else:
            self.throttle_value_label = QLabel("0%")
            self.throttle_value_label.setStyleSheet("color: #ffa500; font-size: 14px;")
            self.throttle_value_label.setFixedWidth(50)
        throttle_layout.addWidget(self.throttle_value_label)

        layout.addLayout(throttle_layout)

        # 输出值显示
        output_layout = QHBoxLayout()
        if HAS_FLUENT:
            output_label = BodyLabel("输出值:")
            output_label.setStyleSheet("color: white;")
            self.output_value_label = BodyLabel("0%")
            self.output_value_label.setStyleSheet("color: #ff6464; font-size: 16px; font-weight: bold;")
        else:
            output_label = QLabel("输出值:")
            output_label.setStyleSheet("color: white;")
            self.output_value_label = QLabel("0%")
            self.output_value_label.setStyleSheet("color: #ff6464; font-size: 16px; font-weight: bold;")
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_value_label)
        output_layout.addStretch()
        layout.addLayout(output_layout)

        self.setLayout(layout)

        # 连接信号
        self.curve_widget.curve_changed.connect(self.on_curve_changed)
        self.curve_widget.value_changed.connect(self.on_value_changed)
        self.curve_widget.function_changed.connect(self.on_function_type_changed)

        # 初始化函数描述
        self._update_function_description(0)

    def on_function_changed(self, index):
        """曲线函数选择改变"""
        if index in self._func_id_map:
            func_id = self._func_id_map[index]
            self.curve_widget.set_curve_function(func_id)
            self._update_function_description(index)

    def _update_function_description(self, index):
        """更新函数描述标签"""
        if index in self._func_id_map:
            func_id = self._func_id_map[index]
            desc = CurveFunction.get_function_description(func_id)
            self.func_desc_label.setText(desc)

    def on_function_type_changed(self, func_id):
        """曲线函数类型改变回调（来自widget）"""
        pass  # 可以在这里添加额外处理

    def on_decrease_expo(self):
        """降低非线性度"""
        self.curve_widget.decrease_expo(0.1)

    def on_increase_expo(self):
        """提高非线性度"""
        self.curve_widget.increase_expo(0.1)

    def on_throttle_changed(self, value):
        """油门滑块值改变"""
        self.curve_widget.set_input_percent(value)
        self.throttle_value_label.setText(f"{value}%")

    def on_curve_changed(self, expo):
        """曲线改变回调"""
        self.expo_value_label.setText(f"{expo:+.2f}")

    def on_value_changed(self, input_val, output_val):
        """值改变回调"""
        self.output_value_label.setText(f"{output_val * 100:.1f}%")


# 兼容导入
from PyQt5.QtWidgets import QPushButton


def main():
    app = QApplication(sys.argv)

    # 创建演示窗口
    demo = ThrottleCurveDemo()
    demo.show()

    # 设置初始值
    demo.throttle_slider.setValue(50)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
