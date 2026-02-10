import math
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QLinearGradient,
    QRadialGradient, QPainterPath, QConicalGradient
)
from protocol.highway_pb2 import IMUParam


class AttitudeBall(QWidget):
    """
    姿态球组件 - 航空仪表风格的姿态指示器
    显示来自IMU的 roll(滚转), pitch(俯仰), yaw(偏航) 数据
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(250, 250)

        # 姿态角
        self.roll = 0.0    # 滚转角 (-180 ~ 180)
        self.pitch = 0.0   # 俯仰角 (-90 ~ 90)
        self.yaw = 0.0     # 偏航角 (-180 ~ 180)

        # 互补滤波状态
        self._filter_initialized = False

        # 颜色配置
        self._sky_color = QColor(0, 119, 190)
        self._sky_color_dark = QColor(0, 60, 120)
        self._ground_color = QColor(139, 90, 43)
        self._ground_color_dark = QColor(80, 50, 20)
        self._horizon_color = QColor(255, 255, 255)
        self._pointer_color = QColor(255, 200, 0)
        self._scale_color = QColor(255, 255, 255, 200)
        self._bezel_color = QColor(50, 50, 50)
        self._text_color = QColor(0, 255, 0)

    def update_from_imu(self, data: IMUParam, dt: float = 0.05):
        """
        从IMU数据更新姿态角 (互补滤波)
        data: IMUParam protobuf 对象
        dt: 采样间隔 (秒)
        """
        ax = data.acceleration_x
        ay = data.acceleration_y
        az = data.acceleration_z
        gx = data.gyroscope_x
        gy = data.gyroscope_y
        gz = data.gyroscope_z

        # 从加速度计算参考角度
        pitch_acc = math.atan2(ax, math.sqrt(ay ** 2 + az ** 2)) * 180 / math.pi
        roll_acc = math.atan2(-ay, az) * 180 / math.pi

        if not self._filter_initialized:
            self.pitch = pitch_acc
            self.roll = roll_acc
            self.yaw = 0.0
            self._filter_initialized = True
        else:
            # 陀螺仪积分
            self.roll += gx * dt
            self.pitch += gy * dt
            self.yaw += gz * dt

            # 互补滤波
            alpha = 0.96
            self.roll = alpha * self.roll + (1 - alpha) * roll_acc
            self.pitch = alpha * self.pitch + (1 - alpha) * pitch_acc

        # 限制范围
        self.roll = (self.roll + 180) % 360 - 180
        self.pitch = max(-90, min(90, self.pitch))
        self.yaw = (self.yaw + 180) % 360 - 180

        self.update()

    def set_attitude(self, roll: float, pitch: float, yaw: float):
        """直接设置姿态角 (度)"""
        self.roll = max(-180, min(180, roll))
        self.pitch = max(-90, min(90, pitch))
        self.yaw = max(-180, min(180, yaw))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # 计算绘制区域 (居中正方形)
        side = min(self.width(), self.height())
        radius = side / 2 - 4
        cx = self.width() / 2
        cy = self.height() / 2

        painter.save()
        painter.translate(cx, cy)

        # 裁剪为圆形
        clip_path = QPainterPath()
        clip_path.addEllipse(QPointF(0, 0), radius, radius)
        painter.setClipPath(clip_path)

        # 1. 绘制天空和地面 (随 roll 和 pitch 旋转/平移)
        self._draw_sky_ground(painter, radius)

        # 2. 绘制俯仰刻度线
        self._draw_pitch_lines(painter, radius)

        # 3. 移除裁剪，绘制固定元素
        painter.setClipping(False)

        # 4. 绘制滚转刻度弧
        self._draw_roll_scale(painter, radius)

        # 5. 绘制中心飞机符号 (固定)
        self._draw_aircraft_symbol(painter, radius)

        # 6. 绘制外圈边框
        self._draw_bezel(painter, radius)

        # 7. 绘制偏航指示 (底部)
        self._draw_yaw_indicator(painter, radius)

        # 8. 绘制数据文字
        self._draw_data_text(painter, radius)

        painter.restore()

    def _draw_sky_ground(self, painter: QPainter, radius: float):
        """绘制天空和地面，随roll/pitch旋转平移"""
        painter.save()

        # 按 roll 旋转
        painter.rotate(-self.roll)

        # pitch 平移: 每度对应的像素偏移
        pitch_px_per_deg = radius / 45.0
        pitch_offset = self.pitch * pitch_px_per_deg

        # 天空渐变
        sky_grad = QLinearGradient(0, -radius * 2.5 + pitch_offset, 0, pitch_offset)
        sky_grad.setColorAt(0, self._sky_color_dark)
        sky_grad.setColorAt(1, self._sky_color)

        # 地面渐变
        ground_grad = QLinearGradient(0, pitch_offset, 0, radius * 2.5 + pitch_offset)
        ground_grad.setColorAt(0, self._ground_color)
        ground_grad.setColorAt(1, self._ground_color_dark)

        big = radius * 3

        # 天空
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(sky_grad))
        painter.drawRect(QRectF(-big, -big + pitch_offset, big * 2, big))

        # 地面
        painter.setBrush(QBrush(ground_grad))
        painter.drawRect(QRectF(-big, pitch_offset, big * 2, big))

        # 地平线
        pen = QPen(self._horizon_color, 2)
        painter.setPen(pen)
        painter.drawLine(QPointF(-big, pitch_offset), QPointF(big, pitch_offset))

        painter.restore()

    def _draw_pitch_lines(self, painter: QPainter, radius: float):
        """绘制俯仰刻度线"""
        painter.save()
        painter.rotate(-self.roll)

        pitch_px_per_deg = radius / 45.0
        pen = QPen(self._scale_color, 1.5)
        painter.setPen(pen)
        font = QFont("Consolas", max(7, int(radius / 18)))
        painter.setFont(font)

        for deg in range(-80, 81, 10):
            if deg == 0:
                continue
            y = -deg * pitch_px_per_deg + self.pitch * pitch_px_per_deg
            half_w = radius * 0.3 if deg % 20 == 0 else radius * 0.15

            painter.drawLine(QPointF(-half_w, y), QPointF(half_w, y))

            if deg % 20 == 0:
                painter.drawText(QRectF(-half_w - 35, y - 8, 30, 16),
                                 Qt.AlignRight | Qt.AlignVCenter, str(abs(deg)))
                painter.drawText(QRectF(half_w + 5, y - 8, 30, 16),
                                 Qt.AlignLeft | Qt.AlignVCenter, str(abs(deg)))

        painter.restore()

    def _draw_roll_scale(self, painter: QPainter, radius: float):
        """绘制滚转刻度弧"""
        painter.save()

        r = radius * 0.88
        pen = QPen(self._scale_color, 1.5)
        painter.setPen(pen)

        # 绘制刻度弧上的标记
        for deg in [-60, -45, -30, -20, -10, 0, 10, 20, 30, 45, 60]:
            angle_rad = math.radians(deg - 90)
            x1 = r * math.cos(angle_rad)
            y1 = r * math.sin(angle_rad)

            if deg % 30 == 0:
                tick_len = radius * 0.1
            elif deg % 45 == 0:
                tick_len = radius * 0.07
            else:
                tick_len = radius * 0.05

            x2 = (r - tick_len) * math.cos(angle_rad)
            y2 = (r - tick_len) * math.sin(angle_rad)
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # 绘制滚转三角形指针 (随 roll 旋转)
        pointer_r = r + radius * 0.02
        roll_rad = math.radians(-self.roll - 90)
        px = pointer_r * math.cos(roll_rad)
        py = pointer_r * math.sin(roll_rad)

        tri_size = radius * 0.06
        path = QPainterPath()
        # 三角形指向圆心
        p1 = QPointF(px, py)
        perp_x = -math.sin(roll_rad) * tri_size
        perp_y = math.cos(roll_rad) * tri_size
        inward_x = -math.cos(roll_rad) * tri_size * 1.5
        inward_y = -math.sin(roll_rad) * tri_size * 1.5
        p2 = QPointF(px + perp_x + inward_x, py + perp_y + inward_y)
        p3 = QPointF(px - perp_x + inward_x, py - perp_y + inward_y)

        path.moveTo(p1)
        path.lineTo(p2)
        path.lineTo(p3)
        path.closeSubpath()

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._pointer_color))
        painter.drawPath(path)

        # 固定顶部三角形 (参考标记)
        ref_y = -r + radius * 0.01
        ref_size = radius * 0.05
        ref_path = QPainterPath()
        ref_path.moveTo(QPointF(0, ref_y))
        ref_path.lineTo(QPointF(-ref_size, ref_y - ref_size * 1.5))
        ref_path.lineTo(QPointF(ref_size, ref_y - ref_size * 1.5))
        ref_path.closeSubpath()
        painter.setBrush(QBrush(self._pointer_color))
        painter.drawPath(ref_path)

        painter.restore()

    def _draw_aircraft_symbol(self, painter: QPainter, radius: float):
        """绘制中心飞机符号 (固定不动)"""
        painter.save()

        pen = QPen(self._pointer_color, 3)
        painter.setPen(pen)

        w = radius * 0.35
        dot_r = radius * 0.04

        # 中心点
        painter.setBrush(QBrush(self._pointer_color))
        painter.drawEllipse(QPointF(0, 0), dot_r, dot_r)

        # 左翼
        painter.drawLine(QPointF(-dot_r * 1.5, 0), QPointF(-w, 0))
        painter.drawLine(QPointF(-w, 0), QPointF(-w, radius * 0.06))

        # 右翼
        painter.drawLine(QPointF(dot_r * 1.5, 0), QPointF(w, 0))
        painter.drawLine(QPointF(w, 0), QPointF(w, radius * 0.06))

        painter.restore()

    def _draw_bezel(self, painter: QPainter, radius: float):
        """绘制外圈边框"""
        painter.save()

        # 外圈渐变
        grad = QConicalGradient(0, 0, 0)
        grad.setColorAt(0, QColor(80, 80, 80))
        grad.setColorAt(0.25, QColor(60, 60, 60))
        grad.setColorAt(0.5, QColor(90, 90, 90))
        grad.setColorAt(0.75, QColor(60, 60, 60))
        grad.setColorAt(1, QColor(80, 80, 80))

        pen = QPen(QBrush(grad), 4)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(0, 0), radius, radius)

        # 内圈高光
        pen2 = QPen(QColor(100, 100, 100, 80), 1)
        painter.setPen(pen2)
        painter.drawEllipse(QPointF(0, 0), radius - 2, radius - 2)

        painter.restore()

    def _draw_yaw_indicator(self, painter: QPainter, radius: float):
        """绘制偏航角指示 (底部小罗盘条)"""
        painter.save()

        bar_h = radius * 0.12
        bar_w = radius * 1.2
        bar_y = radius * 0.78

        # 背景条
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 160)))
        painter.drawRoundedRect(QRectF(-bar_w / 2, bar_y, bar_w, bar_h), 3, 3)

        # 方向标记
        pen = QPen(QColor(255, 255, 255, 200), 1)
        painter.setPen(pen)
        font = QFont("Consolas", max(6, int(radius / 22)))
        painter.setFont(font)

        directions = {0: "N", 45: "NE", 90: "E", 135: "SE",
                      180: "S", -135: "SW", -90: "W", -45: "NW"}

        px_per_deg = bar_w / 120.0  # 显示 ±60 度范围

        for deg_offset in range(-180, 181, 15):
            rel = deg_offset - self.yaw
            # 包裹到 -180..180
            while rel > 180:
                rel -= 360
            while rel < -180:
                rel += 360

            if abs(rel) > 60:
                continue

            x = rel * px_per_deg
            tick_y_top = bar_y + 2
            tick_y_bot = bar_y + bar_h - 2

            if deg_offset % 45 == 0 and deg_offset in directions:
                # 绘制方向文字
                painter.drawText(QRectF(x - 12, bar_y, 24, bar_h),
                                 Qt.AlignCenter, directions[deg_offset])
            elif deg_offset % 15 == 0:
                painter.drawLine(QPointF(x, tick_y_top), QPointF(x, tick_y_bot))

        # 中心标记
        pen2 = QPen(self._pointer_color, 2)
        painter.setPen(pen2)
        painter.drawLine(QPointF(0, bar_y - 2), QPointF(0, bar_y + bar_h + 2))

        painter.restore()

    def _draw_data_text(self, painter: QPainter, radius: float):
        """绘制姿态数据文字"""
        painter.save()

        font = QFont("Consolas", max(8, int(radius / 16)))
        font.setBold(True)
        painter.setFont(font)

        # 半透明背景
        bg = QColor(0, 0, 0, 140)
        text_h = radius * 0.12
        text_w = radius * 0.55

        # 左下: Roll
        lx = -radius * 0.9
        ly = radius * 0.6
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(QRectF(lx, ly, text_w, text_h), 3, 3)
        painter.setPen(QPen(self._text_color))
        painter.drawText(QRectF(lx, ly, text_w, text_h),
                         Qt.AlignCenter, f"R {self.roll:+.1f}\u00b0")

        # 右下: Pitch
        rx = radius * 0.9 - text_w
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(QRectF(rx, ly, text_w, text_h), 3, 3)
        painter.setPen(QPen(self._text_color))
        painter.drawText(QRectF(rx, ly, text_w, text_h),
                         Qt.AlignCenter, f"P {self.pitch:+.1f}\u00b0")

        # 底部中心: Yaw
        yw = radius * 0.5
        yx = -yw / 2
        yy = radius * 0.92
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(QRectF(yx, yy, yw, text_h), 3, 3)
        painter.setPen(QPen(self._text_color))
        painter.drawText(QRectF(yx, yy, yw, text_h),
                         Qt.AlignCenter, f"Y {self.yaw:+.1f}\u00b0")

        painter.restore()


class AttitudeBallWidget(QWidget):
    """
    姿态球面板 - 包含姿态球和数据标签，可直接嵌入到布局中
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(280, 280)

        self.attitude_ball = AttitudeBall()
        self._imu_data = IMUParam()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.attitude_ball)

    def update_imu_data(self, data: IMUParam, dt: float = 0.05):
        """接收IMU数据并更新姿态球"""
        self._imu_data = data
        self.attitude_ball.update_from_imu(data, dt)

    def set_attitude(self, roll: float, pitch: float, yaw: float):
        """直接设置姿态角"""
        self.attitude_ball.set_attitude(roll, pitch, yaw)
