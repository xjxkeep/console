import math
import random
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import (
    Qt, QRectF, QPointF, QTimer, pyqtProperty,
    QPropertyAnimation, QEasingCurve
)
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QRadialGradient, QConicalGradient, QLinearGradient
)


class _Particle:
    """速度弧末端的发光粒子"""
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life', 'size', 'color')

    def __init__(self, x, y, angle, speed_ratio):
        self.x = x
        self.y = y
        spread = 0.6
        base_angle = angle + random.uniform(-spread, spread)
        v = random.uniform(0.5, 2.0) * (0.5 + speed_ratio)
        self.vx = math.cos(base_angle) * v
        self.vy = math.sin(base_angle) * v
        self.max_life = random.uniform(0.3, 0.8)
        self.life = self.max_life
        self.size = random.uniform(1.0, 3.0)
        self.color = QColor(255, 200, 60)

    def update(self, dt):
        self.x += self.vx * dt * 30
        self.y += self.vy * dt * 30
        self.life -= dt
        return self.life > 0

    @property
    def alpha(self):
        return max(0, self.life / self.max_life)


class Speedometer(QWidget):
    """
    赛车风格速度仪表盘
    - 渐变发光弧 (cyan → yellow → red)
    - 动态粒子尾迹
    - 平滑指针动画
    - 中心数字显示
    """

    # 仪表弧角度范围 (degree): 从左下到右下, 开口朝下
    _ARC_START_DEG = 225   # 左下起点
    _ARC_SWEEP_DEG = -270  # 顺时针扫过270度

    def __init__(self, parent=None, max_speed=120):
        super().__init__(parent)
        self.setMinimumSize(120, 120)

        self._max_speed = max_speed
        self._display_value = 0.0   # 动画驱动的显示值
        self._target_value = 0.0
        self._odometer = 0.0
        self._particles = []

        # 指针动画
        self._anim = QPropertyAnimation(self, b"displayValue")
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        # 粒子 & 刷新定时器
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)  # ~30fps

    # ---- pyqtProperty for animation ----
    def _get_display_value(self):
        return self._display_value

    def _set_display_value(self, v):
        self._display_value = v
        self.update()

    displayValue = pyqtProperty(float, fget=_get_display_value, fset=_set_display_value)

    # ---- public API ----
    def setValue(self, speed: float):
        speed = max(0, min(speed, self._max_speed))
        if abs(speed - self._target_value) < 0.01:
            return
        self._target_value = speed
        self._anim.stop()
        self._anim.setStartValue(self._display_value)
        self._anim.setEndValue(speed)
        self._anim.start()

    def setOdometer(self, km: float):
        self._odometer = km
        self.update()

    def setMaxSpeed(self, v: float):
        self._max_speed = v
        self.update()

    # ---- internal ----
    def _tick(self):
        dt = 0.033
        ratio = self._display_value / self._max_speed if self._max_speed else 0

        # 生成粒子 (速度越高粒子越多)
        if ratio > 0.05:
            count = max(1, int(ratio * 4))
            angle_deg = self._ARC_START_DEG + self._ARC_SWEEP_DEG * ratio
            angle_rad = math.radians(angle_deg)

            side = min(self.width(), self.height())
            r = side / 2 * 0.78
            cx, cy = self.width() / 2, self.height() / 2
            px = cx + r * math.cos(angle_rad)
            py = cy - r * math.sin(angle_rad)

            # 粒子沿弧线切线方向散射
            tangent = angle_rad - math.pi / 2  # 切线方向
            for _ in range(count):
                self._particles.append(_Particle(px, py, tangent, ratio))

        # 更新粒子
        self._particles = [p for p in self._particles if p.update(dt)]

        # 限制粒子总数
        if len(self._particles) > 80:
            self._particles = self._particles[-80:]

        self.update()

    def _speed_color(self, ratio: float) -> QColor:
        """根据速度比例返回颜色: cyan → yellow → red"""
        if ratio < 0.5:
            t = ratio / 0.5
            r = int(0 + 255 * t)
            g = int(220 + (220 - 220) * t)
            b = int(255 * (1 - t))
            return QColor(r, g, b)
        else:
            t = (ratio - 0.5) / 0.5
            r = 255
            g = int(220 * (1 - t))
            b = 0
            return QColor(r, g, b)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        side = min(self.width(), self.height())
        cx = self.width() / 2
        cy = self.height() / 2
        radius = side / 2 - 4

        painter.save()
        painter.translate(cx, cy)

        self._draw_background(painter, radius)
        self._draw_glow_arc(painter, radius)
        self._draw_scale(painter, radius)
        self._draw_needle(painter, radius)
        self._draw_center_text(painter, radius)

        painter.restore()

        # 粒子在全局坐标绘制
        self._draw_particles(painter)

    def _draw_background(self, painter: QPainter, radius: float):
        """深色圆形背景"""
        # 外环
        grad = QRadialGradient(0, 0, radius)
        grad.setColorAt(0, QColor(20, 22, 30))
        grad.setColorAt(0.85, QColor(25, 28, 38))
        grad.setColorAt(0.95, QColor(40, 44, 55))
        grad.setColorAt(1.0, QColor(55, 60, 72))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(QPointF(0, 0), radius, radius)

        # 内环微光
        inner_r = radius * 0.92
        inner_grad = QRadialGradient(0, 0, inner_r)
        inner_grad.setColorAt(0, QColor(30, 33, 45))
        inner_grad.setColorAt(1, QColor(20, 22, 30, 0))
        painter.setBrush(QBrush(inner_grad))
        painter.drawEllipse(QPointF(0, 0), inner_r, inner_r)

    def _draw_glow_arc(self, painter: QPainter, radius: float):
        """绘制渐变发光弧"""
        ratio = self._display_value / self._max_speed if self._max_speed else 0
        if ratio < 0.001:
            return

        arc_r = radius * 0.78
        arc_w = radius * 0.09

        # 弧的角度
        start_angle_16 = int(self._ARC_START_DEG * 16)
        sweep_16 = int(self._ARC_SWEEP_DEG * ratio * 16)

        rect = QRectF(-arc_r, -arc_r, arc_r * 2, arc_r * 2)
        color = self._speed_color(ratio)

        # 外发光层 (多层半透明弧模拟 glow)
        for i in range(3, 0, -1):
            glow_w = arc_w + i * radius * 0.03
            glow_alpha = int(30 * (1 - i / 4))
            glow_color = QColor(color.red(), color.green(), color.blue(), glow_alpha)
            pen = QPen(glow_color, glow_w)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawArc(rect, start_angle_16, sweep_16)

        # 主弧
        pen = QPen(color, arc_w)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, start_angle_16, sweep_16)

        # 弧末端亮点
        end_angle_deg = self._ARC_START_DEG + self._ARC_SWEEP_DEG * ratio
        end_rad = math.radians(end_angle_deg)
        tip_x = arc_r * math.cos(end_rad)
        tip_y = -arc_r * math.sin(end_rad)

        tip_grad = QRadialGradient(tip_x, tip_y, arc_w * 1.5)
        bright = QColor(255, 255, 255, 180)
        tip_grad.setColorAt(0, bright)
        tip_grad.setColorAt(0.4, QColor(color.red(), color.green(), color.blue(), 120))
        tip_grad.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(tip_grad))
        painter.drawEllipse(QPointF(tip_x, tip_y), arc_w * 1.5, arc_w * 1.5)

    def _draw_scale(self, painter: QPainter, radius: float):
        """刻度线和数字"""
        scale_r = radius * 0.88
        num_major = 6  # 主刻度数量
        num_minor = 4  # 每段小刻度

        total = num_major * num_minor
        for i in range(total + 1):
            ratio = i / total
            angle_deg = self._ARC_START_DEG + self._ARC_SWEEP_DEG * ratio
            angle_rad = math.radians(angle_deg)

            is_major = (i % num_minor == 0)

            if is_major:
                tick_len = radius * 0.08
                pen = QPen(QColor(180, 185, 200), 1.5)
            else:
                tick_len = radius * 0.04
                pen = QPen(QColor(80, 85, 100), 1)

            painter.setPen(pen)
            x1 = scale_r * math.cos(angle_rad)
            y1 = -scale_r * math.sin(angle_rad)
            x2 = (scale_r - tick_len) * math.cos(angle_rad)
            y2 = -(scale_r - tick_len) * math.sin(angle_rad)
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

            # 主刻度数字
            if is_major:
                value = int(self._max_speed * ratio)
                font_size = max(6, int(radius / 12))
                font = QFont("Consolas", font_size)
                painter.setFont(font)
                painter.setPen(QPen(QColor(160, 165, 180)))

                text_r = scale_r - tick_len - radius * 0.08
                tx = text_r * math.cos(angle_rad)
                ty = -text_r * math.sin(angle_rad)
                text = str(value)
                fm = painter.fontMetrics()
                tw = fm.horizontalAdvance(text)
                th = fm.height()
                painter.drawText(QPointF(tx - tw / 2, ty + th / 4), text)

    def _draw_needle(self, painter: QPainter, radius: float):
        """指针"""
        ratio = self._display_value / self._max_speed if self._max_speed else 0
        angle_deg = self._ARC_START_DEG + self._ARC_SWEEP_DEG * ratio
        angle_rad = math.radians(angle_deg)

        needle_len = radius * 0.65
        tail_len = radius * 0.12
        half_w = radius * 0.02

        painter.save()
        painter.rotate(-angle_deg)  # QPainter rotate is clockwise

        # 指针阴影
        shadow_path = QPainterPath()
        shadow_path.moveTo(needle_len + 1, 1)
        shadow_path.lineTo(0, half_w + 1)
        shadow_path.lineTo(-tail_len, 1)
        shadow_path.lineTo(0, -(half_w - 1))
        shadow_path.closeSubpath()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 60)))
        painter.drawPath(shadow_path)

        # 指针本体
        color = self._speed_color(ratio)
        needle_path = QPainterPath()
        needle_path.moveTo(needle_len, 0)
        needle_path.lineTo(0, half_w)
        needle_path.lineTo(-tail_len, 0)
        needle_path.lineTo(0, -half_w)
        needle_path.closeSubpath()

        grad = QLinearGradient(-tail_len, 0, needle_len, 0)
        grad.setColorAt(0, QColor(100, 100, 110))
        grad.setColorAt(0.3, color)
        grad.setColorAt(1, QColor(255, 255, 255, 220))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(0, 0, 0, 80), 0.5))
        painter.drawPath(needle_path)

        # 中心圆
        painter.restore()
        cap_grad = QRadialGradient(0, 0, radius * 0.06)
        cap_grad.setColorAt(0, QColor(200, 205, 215))
        cap_grad.setColorAt(0.6, QColor(80, 85, 95))
        cap_grad.setColorAt(1, QColor(40, 42, 50))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(cap_grad))
        painter.drawEllipse(QPointF(0, 0), radius * 0.06, radius * 0.06)

    def _draw_center_text(self, painter: QPainter, radius: float):
        """中心速度数字和里程"""
        ratio = self._display_value / self._max_speed if self._max_speed else 0
        color = self._speed_color(ratio)

        # 速度数值
        speed_font_size = max(10, int(radius / 4))
        font = QFont("Consolas", speed_font_size, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QPen(color))

        speed_text = f"{self._display_value:.0f}"
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(speed_text)
        painter.drawText(QPointF(-tw / 2, radius * 0.28), speed_text)

        # 单位
        unit_font_size = max(6, int(radius / 10))
        font2 = QFont("Consolas", unit_font_size)
        painter.setFont(font2)
        painter.setPen(QPen(QColor(120, 125, 140)))
        unit_text = "km/h"
        tw2 = painter.fontMetrics().horizontalAdvance(unit_text)
        painter.drawText(QPointF(-tw2 / 2, radius * 0.42), unit_text)

        # 里程
        odo_font_size = max(5, int(radius / 13))
        font3 = QFont("Consolas", odo_font_size)
        painter.setFont(font3)
        painter.setPen(QPen(QColor(90, 95, 110)))
        odo_text = f"ODO {self._odometer:.1f} km"
        tw3 = painter.fontMetrics().horizontalAdvance(odo_text)
        painter.drawText(QPointF(-tw3 / 2, radius * 0.56), odo_text)

    def _draw_particles(self, painter: QPainter):
        """绘制粒子效果"""
        painter.save()
        ratio = self._display_value / self._max_speed if self._max_speed else 0
        base_color = self._speed_color(ratio)

        for p in self._particles:
            alpha = int(p.alpha * 200)
            c = QColor(
                min(255, base_color.red() + 40),
                min(255, base_color.green() + 30),
                min(255, base_color.blue()),
                alpha
            )
            painter.setPen(Qt.NoPen)

            # 粒子发光
            glow_r = p.size * 2.5
            grad = QRadialGradient(p.x, p.y, glow_r)
            grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), alpha))
            grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 0))
            painter.setBrush(QBrush(grad))
            painter.drawEllipse(QPointF(p.x, p.y), glow_r, glow_r)

            # 粒子核心
            painter.setBrush(QBrush(QColor(255, 255, 255, alpha)))
            painter.drawEllipse(QPointF(p.x, p.y), p.size * 0.5, p.size * 0.5)

        painter.restore()
