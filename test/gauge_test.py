import sys
import math
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath
from PyQt5.QtCore import Qt, QRectF, QSize,QPointF,pyqtProperty


class DashboardGauge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 60  # 默认值
        self._min_value = 0  # 最小值
        self._max_value = 100  # 最大值
        self._unit = "km/h"  # 单位
        
        # 颜色配置
        self._ring_color = QColor(41, 128, 185)  # 进度环颜色
        self._bg_color = QColor(230, 230, 230)   # 背景环颜色
        self._text_color = QColor(50, 50, 50)    # 文字颜色
        self._scale_color = QColor(100, 100, 100)  # 刻度颜色
        self._critical_color = QColor(255, 80, 80)  # 警戒区颜色
        self._ring_width = 10                     # 圆环宽度
        
        # 角度参数（单位：度）-120度到180度形成一个240度的扇形仪表盘
        self._start_deg = -120
        self._end_deg = 180
        self._clockwise = True
        
        # 刻度配置
        self._major_ticks = 12  # 主刻度数量
        self._minor_ticks = 4   # 每个主刻度间的小刻度数量
        self._scale_radius_ratio = 0.85  # 刻度半径相对比例
        self._scale_length = 10          # 主刻度长度
        self._minor_scale_length = 5     # 小刻度长度
        
        # 文字配置
        self._value_font_size = 20       # 数值字体大小
        self._unit_font_size = 12        # 单位字体大小
        self._scale_font_size = 10       # 刻度值字体大小
        
        # 设置最小尺寸
        self.setMinimumSize(200, 200)

    def paintEvent(self, event):
        painter = QPainter(self)
        # 启用全面抗锯齿
        painter.setRenderHints(
            QPainter.Antialiasing | 
            QPainter.TextAntialiasing |
            QPainter.SmoothPixmapTransform | 
            QPainter.HighQualityAntialiasing
        )
        
        # 获取绘制区域（正方形）
        size = min(self.width(), self.height())
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = (size - self._ring_width) / 2
        
        # 绘制背景圆环
        self._draw_background_ring(painter, center_x, center_y, radius)
        
        # 绘制警戒区域（如超过80%最大值的区域）
        self._draw_critical_zone(painter, center_x, center_y, radius)
        
        # 绘制刻度和刻度值
        self._draw_scales(painter, center_x, center_y, radius)
        
        # 绘制进度指针
        self._draw_needle(painter, center_x, center_y, radius)
        
        # 绘制中心数值和单位
        self._draw_center_text(painter, center_x, center_y)

    def _draw_background_ring(self, painter, center_x, center_y, radius):
        """绘制背景圆环"""
        painter.save()
        
        # 绘制外圆环
        pen = QPen(self._bg_color, self._ring_width)
        pen.setCapStyle(Qt.FlatCap)  # 平角笔触更适合仪表盘
        painter.setPen(pen)
        
        # 计算角度
        start16, span16 = self._compute_arc16(
            self._start_deg, self._end_deg, self._clockwise
        )
        
        # 绘制背景弧
        rect = QRectF(
            center_x - radius,
            center_y - radius,
            radius * 2,
            radius * 2
        )
        painter.drawArc(rect, start16, span16)
        
        painter.restore()

    def _draw_critical_zone(self, painter, center_x, center_y, radius):
        """绘制警戒区域（如高速区）"""
        painter.save()
        
        # 计算警戒区域起始角度（80%最大值位置）
        critical_value = self._max_value * 0.8
        critical_ratio = (critical_value - self._min_value) / (self._max_value - self._min_value)
        total_deg = abs(self._end_deg - self._start_deg)
        critical_start_deg = self._start_deg + critical_ratio * total_deg
        
        # 绘制警戒弧
        pen = QPen(self._critical_color, self._ring_width)
        pen.setCapStyle(Qt.FlatCap)
        painter.setPen(pen)
        
        start16, span16 = self._compute_arc16(
            critical_start_deg, self._end_deg, self._clockwise
        )
        
        rect = QRectF(
            center_x - radius,
            center_y - radius,
            radius * 2,
            radius * 2
        )
        painter.drawArc(rect, start16, span16)
        
        painter.restore()

    def _draw_scales(self, painter, center_x, center_y, radius):
        """绘制主刻度、小刻度和刻度值"""
        painter.save()
        painter.translate(center_x, center_y)  # 将原点移至中心
        
        total_deg = abs(self._end_deg - self._start_deg)
        total_value_range = self._max_value - self._min_value
        scale_radius = radius * self._scale_radius_ratio
        
        # 直接使用配置的起始和结束角度，与圆环保持一致
        start_deg = 120-self._start_deg
        end_deg = 120-self._end_deg
        
        # 绘制小刻度
        painter.setPen(QPen(self._scale_color, 1))
        for i in range(self._major_ticks * (self._minor_ticks + 1) + 1):
            # 计算当前刻度角度
            ratio = i / (self._major_ticks * (self._minor_ticks + 1))
            deg = start_deg + ratio * (end_deg - start_deg)
            rad = math.radians(deg)
            
            # 计算刻度线起点和终点
            x1 = math.cos(rad) * (scale_radius - self._minor_scale_length)
            y1 = -math.sin(rad) * (scale_radius - self._minor_scale_length)
            x2 = math.cos(rad) * scale_radius
            y2 = -math.sin(rad) * scale_radius
            
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        
        # 绘制主刻度和刻度值
        painter.setPen(QPen(self._scale_color, 2))
        font = QFont()
        font.setPointSize(self._scale_font_size)
        painter.setFont(font)
        
        for i in range(self._major_ticks + 1):
            # 计算当前刻度角度和对应值
            ratio = i / self._major_ticks
            deg = start_deg + ratio * (end_deg - start_deg)
            rad = math.radians(deg)
            
            # 根据顺时针/逆时针调整数值映射
            if self._clockwise:
                # 顺时针：从起始角度到结束角度，数值从最小值到最大值
                value = self._min_value + ratio * total_value_range
            else:
                # 逆时针：从起始角度到结束角度，数值从最大值到最小值
                value = self._max_value - ratio * total_value_range
            
            # 绘制主刻度线
            x1 = math.cos(rad) * (scale_radius - self._scale_length)
            y1 = -math.sin(rad) * (scale_radius - self._scale_length)
            x2 = math.cos(rad) * scale_radius
            y2 = -math.sin(rad) * scale_radius
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            
            # 绘制刻度值
            text = f"{int(value)}"
            text_radius = scale_radius - self._scale_length - 10  # 文字位置半径
            text_x = math.cos(rad) * text_radius
            text_y = -math.sin(rad) * text_radius
            
            # 文本居中对齐
            text_rect = painter.boundingRect(0, 0, 30, 20, Qt.AlignCenter, text)
            painter.drawText(
                int(text_x - text_rect.width()/2),
                int(text_y + text_rect.height()/4),  # 微调垂直位置
                text
            )
        
        painter.restore()

    def _draw_needle(self, painter, center_x, center_y, radius):
        """绘制指针"""
        painter.save()
        painter.translate(center_x, center_y)  # 将原点移至中心
        
        # 计算指针角度
        # total_deg = abs(self._end_deg - self._start_deg)
        ratio = (self._value - self._min_value) / (self._max_value - self._min_value)
        deg = ratio * 360 - self._start_deg
        # 根据顺时针/逆时针调整角度计算
        # if self._clockwise:
        #     # 顺时针：从起始角度到结束角度，数值从最小值到最大值
        #     # 使用与刻度相同的角度计算方式
        #     deg = self._start_deg + ratio * total_deg
        # else:
        #     # 逆时针：从起始角度到结束角度，数值从最大值到最小值
        #     # 需要反转比例：1-ratio
        #     deg = self._start_deg + (1 - ratio) * total_deg
        
        painter.rotate(deg)  # 旋转坐标系
        
        # 绘制指针
        needle_length = radius * 0.75
        painter.setBrush(QBrush(self._ring_color))
        painter.setPen(QPen(QColor(50, 50, 50), 1))
        
        # 指针形状（三角形）
        needle_path = QPainterPath()
        needle_path.moveTo(0, 5)  # 指针尾部
        needle_path.lineTo(needle_length, 0)  # 指针尖端
        needle_path.lineTo(0, -5)
        needle_path.closeSubpath()
        painter.drawPath(needle_path)
        
        # 绘制指针中心
        painter.setBrush(QBrush(QColor(50, 50, 50)))
        painter.drawEllipse(QPointF(0, 0), 6, 6)
        
        painter.restore()

    def _draw_center_text(self, painter, center_x, center_y):
        """绘制中心数值和单位"""
        painter.save()
        
        # 绘制数值
        font = QFont()
        font.setPointSize(self._value_font_size)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(self._text_color))
        
        value_text = f"{int(self._value) if self._value.is_integer() else round(self._value, 1)}"
        value_rect = QRectF(center_x - 50, center_y - 20, 100, 40)
        painter.drawText(value_rect, Qt.AlignCenter, value_text)
        
        # 绘制单位
        font.setPointSize(self._unit_font_size)
        font.setBold(False)
        painter.setFont(font)
        
        unit_rect = QRectF(center_x - 50, center_y + 20, 100, 20)
        painter.drawText(unit_rect, Qt.AlignCenter, self._unit)
        
        painter.restore()

    def _compute_arc16(self, start_deg: float, end_deg: float, clockwise: bool) -> tuple:
        """将起止角度转换为 Qt 使用的 1/16 度起点与扫角"""
        start16 = int(start_deg * 16)
        span_deg = end_deg - start_deg
        span_abs16 = int(abs(span_deg) * 16)
        span16 = -span_abs16 if clockwise else span_abs16
        return start16, span16

    # 属性设置方法
    def setValue(self, value):
        """设置当前值"""
        clamped = max(self._min_value, min(value, self._max_value))
        if clamped != self._value:
            self._value = clamped
            self.update()

    def getValue(self):
        return self._value

    def setMinValue(self, value):
        if value != self._min_value:
            self._min_value = value
            if self._value < value:
                self._value = value
            self.update()

    def getMinValue(self):
        return self._min_value

    def setMaxValue(self, value):
        if value != self._max_value:
            self._max_value = value
            if self._value > value:
                self._value = value
            self.update()

    def getMaxValue(self):
        return self._max_value

    def setUnit(self, unit):
        if unit != self._unit:
            self._unit = unit
            self.update()

    def getUnit(self):
        return self._unit

    # 其他样式设置方法（简化版，保留核心样式配置）
    def setRingColor(self, color):
        if self._ring_color != color:
            self._ring_color = color
            self.update()

    def setBgColor(self, color):
        if self._bg_color != color:
            self._bg_color = color
            self.update()

    def setRingWidth(self, width):
        if width > 0 and width != self._ring_width:
            self._ring_width = width
            self.update()

    # 角度参数设置方法
    def setStartAngle(self, angle):
        if angle != self._start_deg:
            self._start_deg = angle
            self.update()

    def getStartAngle(self):
        return self._start_deg

    def setEndAngle(self, angle):
        if angle != self._end_deg:
            self._end_deg = angle
            self.update()

    def getEndAngle(self):
        return self._end_deg

    def setClockwise(self, clockwise):
        if clockwise != self._clockwise:
            self._clockwise = clockwise
            self.update()

    def getClockwise(self):
        return self._clockwise

    # Qt属性定义
    value = pyqtProperty(float, fget=getValue, fset=setValue)
    minValue = pyqtProperty(float, fget=getMinValue, fset=setMinValue)
    maxValue = pyqtProperty(float, fget=getMaxValue, fset=setMaxValue)
    unit = pyqtProperty(str, fget=getUnit, fset=setUnit)
    ringColor = pyqtProperty(QColor, fget=lambda self: self._ring_color, fset=setRingColor)
    bgColor = pyqtProperty(QColor, fget=lambda self: self._bg_color, fset=setBgColor)
    ringWidth = pyqtProperty(int, fget=lambda self: self._ring_width, fset=setRingWidth)
    startAngle = pyqtProperty(float, fget=getStartAngle, fset=setStartAngle)
    endAngle = pyqtProperty(float, fget=getEndAngle, fset=setEndAngle)
    clockwise = pyqtProperty(bool, fget=getClockwise, fset=setClockwise)

    def sizeHint(self):
        return QSize(300, 300)


# 演示窗口
class DemoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # 创建仪表盘
        self.gauge = DashboardGauge()
        self.gauge.setUnit("km/h")
        self.gauge.setMaxValue(120)
        self.gauge.setRingColor(QColor(46, 204, 113))  # 绿色进度
        self.gauge.setRingWidth(12)
        
        # 布局
        layout = QVBoxLayout()
        layout.addWidget(self.gauge, alignment=Qt.AlignCenter)
        self.setLayout(layout)
        
        self.setWindowTitle("汽车仪表盘")
        self.setGeometry(300, 300, 400, 400)
        
        # 模拟数值更新
        self.counter = 0
        from PyQt5.QtCore import QTimer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateValue)
        self.timer.start(100)  # 每100ms更新一次

    def updateValue(self):
        """模拟速度变化"""
        self.counter += 0.5
        speed = 0 + 100 * math.sin(self.counter / 10)  # 0-100波动
        self.gauge.setValue(speed)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoWindow()
    window.show()
    sys.exit(app.exec_())