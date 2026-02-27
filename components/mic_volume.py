import numpy as np
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont,
    QLinearGradient, QRadialGradient
)


class MicVolumeWidget(QWidget):
    """
    麦克风音量动态显示组件

    功能：
    - 竖向分段式音量条 (绿 → 黄 → 红)
    - 峰值标记线，带缓慢下落
    - 底部 dB 数值显示
    - 支持通过 setLevel / setRMS 设置音量

    用法：
        widget = MicVolumeWidget()
        widget.setLevel(0.6)        # 直接设置 0.0~1.0
        widget.setRMS(pcm_array)    # 传入 int16 PCM 自动计算
    """

    levelChanged = pyqtSignal(float)

    # 分段数
    _NUM_BARS = 30
    _BAR_GAP = 2

    def __init__(self, parent=None, label="MIC"):
        super().__init__(parent)
        self.setMinimumSize(48, 120)

        self._label = label
        self._level = 0.0       # 当前音量 0.0 ~ 1.0
        self._peak = 0.0        # 峰值
        self._peak_hold = 0     # 峰值保持计数
        self._smooth_level = 0.0

        # 峰值下落定时器
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._decay_tick)
        self._timer.start(33)   # ~30fps

    # ---- public API ----

    def setLevel(self, level: float):
        """设置音量 (0.0 ~ 1.0)"""
        level = max(0.0, min(1.0, level))
        self._level = level

        # 平滑处理
        alpha = 0.35
        self._smooth_level = alpha * level + (1 - alpha) * self._smooth_level

        # 更新峰值
        if self._smooth_level >= self._peak:
            self._peak = self._smooth_level
            self._peak_hold = 20  # 保持 ~0.66s

        self.levelChanged.emit(self._smooth_level)
        self.update()

    def setRMS(self, pcm: np.ndarray):
        """传入 int16 PCM 数据，自动计算 RMS 并更新"""
        if len(pcm) == 0:
            return
        rms = np.sqrt(np.mean(pcm.astype(np.float64) ** 2))
        # int16 最大值 32768，映射到 0~1
        level = min(1.0, rms / 16384.0)
        self.setLevel(level)

    # ---- internal ----

    def _decay_tick(self):
        """峰值缓慢下落"""
        if self._peak_hold > 0:
            self._peak_hold -= 1
        else:
            self._peak = max(0.0, self._peak - 0.015)

        # 无信号时平滑归零
        self._smooth_level *= 0.92
        self.update()

    def _bar_color(self, ratio: float) -> QColor:
        """根据位置返回颜色: 绿 → 黄 → 红"""
        if ratio < 0.6:
            t = ratio / 0.6
            return QColor(int(80 * t), int(200 + 55 * t), 80)
        elif ratio < 0.85:
            t = (ratio - 0.6) / 0.25
            return QColor(int(80 + 175 * t), 255, int(80 * (1 - t)))
        else:
            t = (ratio - 0.85) / 0.15
            return QColor(255, int(255 * (1 - t * 0.7)), 0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # 背景
        painter.fillRect(self.rect(), QColor(25, 25, 30))

        # 标签区域高度
        label_h = 22
        db_h = 20
        meter_top = 6
        meter_bottom = h - label_h - db_h
        meter_h = meter_bottom - meter_top

        # 音量条区域
        bar_left = 10
        bar_right = w - 10
        bar_w = bar_right - bar_left

        self._draw_bars(painter, bar_left, meter_top, bar_w, meter_h)
        self._draw_peak_line(painter, bar_left, meter_top, bar_w, meter_h)
        self._draw_db(painter, 0, meter_bottom + 2, w, db_h)
        self._draw_label(painter, 0, h - label_h, w, label_h)

    def _draw_bars(self, painter: QPainter, x, y, w, h):
        """绘制分段音量条"""
        num = self._NUM_BARS
        gap = self._BAR_GAP
        bar_h = (h - gap * (num - 1)) / num
        active_bars = int(self._smooth_level * num)

        for i in range(num):
            ratio = i / num
            bar_y = y + h - (i + 1) * (bar_h + gap)
            rect = QRectF(x, bar_y, w, bar_h)

            if i < active_bars:
                color = self._bar_color(ratio)
                # 发光效果
                glow = QColor(color.red(), color.green(), color.blue(), 60)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(glow))
                glow_rect = QRectF(x - 2, bar_y - 1, w + 4, bar_h + 2)
                painter.drawRoundedRect(glow_rect, 2, 2)
                # 主色
                painter.setBrush(QBrush(color))
                painter.drawRoundedRect(rect, 2, 2)
            else:
                # 暗色背景格
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(40, 42, 48)))
                painter.drawRoundedRect(rect, 2, 2)

    def _draw_peak_line(self, painter: QPainter, x, y, w, h):
        """绘制峰值标记线"""
        if self._peak < 0.01:
            return
        peak_y = y + h - self._peak * h
        color = self._bar_color(self._peak)
        pen = QPen(QColor(color.red(), color.green(), color.blue(), 200), 2)
        painter.setPen(pen)
        painter.drawLine(QPointF(x, peak_y), QPointF(x + w, peak_y))

    def _draw_db(self, painter: QPainter, x, y, w, h):
        """绘制 dB 数值"""
        if self._smooth_level > 0.0001:
            db = 20 * np.log10(self._smooth_level + 1e-10)
        else:
            db = -60.0
        db = max(-60.0, db)

        painter.setPen(QPen(QColor(180, 185, 195)))
        font = QFont("Consolas", 9)
        painter.setFont(font)
        text = f"{db:.0f} dB"
        painter.drawText(QRectF(x, y, w, h), Qt.AlignCenter, text)

    def _draw_label(self, painter: QPainter, x, y, w, h):
        """绘制底部标签"""
        painter.setPen(QPen(QColor(120, 125, 140)))
        font = QFont("Consolas", 10, QFont.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(x, y, w, h), Qt.AlignCenter, self._label)
