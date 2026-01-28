import logging
import sys
from typing import Any
import typing

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import *
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ComboBox,
    FluentIcon,
    GroupHeaderCardWidget,
    PillPushButton,
    ProgressBar,
    ScrollArea,
    SpinBox,
    Slider,
    Theme,
    TransparentPushButton,
    TransparentToolButton,
    setTheme,
)

from pkg.joystick import JoyStick
from pkg.model import Setting
from components.channel import Detector, ChannelGroup
from components.throttle_curve import ThrottleCurveWidget, CurveFunction


class CurveSettingPanel(GroupHeaderCardWidget):
    """非线性曲线设置面板"""

    # 当曲线设置改变时发出信号: (channel, expo, function_id)
    setting_changed = pyqtSignal(int, float, str)

    def __init__(self, title: str, channel: int = 0, parent=None):
        super().__init__(parent)
        self.channel = channel
        self._title = title
        self.initUI()

    def initUI(self):
        self.setTitle(self._title)
        self.setupUi()

    def setupUi(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # 曲线函数选择
        func_row = QHBoxLayout()
        func_row.setSpacing(8)
        func_label = CaptionLabel("曲线类型")
        func_label.setFixedWidth(60)
        func_row.addWidget(func_label)

        self.func_combo = ComboBox()
        self._func_id_map = {}
        for idx, (func_id, name, desc) in enumerate(ThrottleCurveWidget.get_supported_functions()):
            self.func_combo.addItem(name)
            self._func_id_map[idx] = func_id
        self.func_combo.currentIndexChanged.connect(self._on_function_changed)
        func_row.addWidget(self.func_combo, 1)
        main_layout.addLayout(func_row)

        # 曲线图表
        self.curve_widget = ThrottleCurveWidget()
        self.curve_widget.setMinimumSize(150, 100)
        main_layout.addWidget(self.curve_widget, 1)  # stretch factor 1 让图表占用更多空间

        # Expo 调节
        expo_row = QHBoxLayout()
        expo_row.setSpacing(8)

        expo_label = CaptionLabel("非线性度")
        expo_label.setFixedWidth(60)
        expo_row.addWidget(expo_label)

        self.expo_slider = Slider(Qt.Horizontal)
        self.expo_slider.setRange(-100, 100)
        self.expo_slider.setValue(0)
        self.expo_slider.valueChanged.connect(self._on_expo_slider_changed)
        expo_row.addWidget(self.expo_slider, 1)

        self.expo_value_label = BodyLabel("0.00")
        self.expo_value_label.setFixedWidth(45)
        self.expo_value_label.setAlignment(Qt.AlignCenter)
        expo_row.addWidget(self.expo_value_label)

        main_layout.addLayout(expo_row)

        # 通道选择
        channel_row = QHBoxLayout()
        channel_row.setSpacing(8)

        channel_label = CaptionLabel("应用通道")
        channel_label.setFixedWidth(60)
        channel_row.addWidget(channel_label)

        self.channel_spin = SpinBox()
        self.channel_spin.setRange(1, 16)
        self.channel_spin.setValue(self.channel + 1)  # 显示从1开始
        self.channel_spin.valueChanged.connect(self._on_channel_changed)
        channel_row.addWidget(self.channel_spin)

        channel_row.addStretch()
        main_layout.addLayout(channel_row)

        self.vBoxLayout.addLayout(main_layout)

        # 连接曲线组件信号
        self.curve_widget.curve_changed.connect(self._on_curve_changed)

    def _on_function_changed(self, index):
        """曲线函数类型改变"""
        if index in self._func_id_map:
            func_id = self._func_id_map[index]
            self.curve_widget.set_curve_function(func_id)
            self._emit_setting_changed()

    def _on_expo_slider_changed(self, value):
        """Expo 滑块改变"""
        expo = value / 100.0
        self.curve_widget.expo = expo
        self.expo_value_label.setText(f"{expo:+.2f}")
        self._emit_setting_changed()

    def _on_channel_changed(self, value):
        """通道改变"""
        self.channel = value - 1  # 内部从0开始
        self._emit_setting_changed()

    def _on_curve_changed(self, expo):
        """曲线改变回调"""
        # 同步滑块
        self.expo_slider.blockSignals(True)
        self.expo_slider.setValue(int(expo * 100))
        self.expo_slider.blockSignals(False)
        self.expo_value_label.setText(f"{expo:+.2f}")

    def _emit_setting_changed(self):
        """发出设置改变信号"""
        func_id = self._func_id_map.get(self.func_combo.currentIndex(), CurveFunction.EXPO)
        self.setting_changed.emit(self.channel, self.curve_widget.expo, func_id)

    def set_input_value(self, value: float):
        """设置当前输入值用于显示 (0-1)"""
        self.curve_widget.input_value = value

    def apply_curve(self, value: float) -> float:
        """应用非线性曲线转换

        Args:
            value: 输入值 (0-100)
        Returns:
            转换后的值 (0-100)
        """
        normalized = value / 100.0
        output = self.curve_widget.calculate_output(normalized)
        return output * 100.0

    def get_channel(self) -> int:
        """获取当前应用的通道号 (从0开始)"""
        return self.channel

    def get_expo(self) -> float:
        """获取当前非线性度"""
        return self.curve_widget.expo

    def get_function_id(self) -> str:
        """获取当前曲线函数ID"""
        return self.curve_widget.curve_function


class Controller(QWidget):
    controlMessage=pyqtSignal(list)
    def setupUi(self):
        self.setObjectName("Controller")
        self.setWindowTitle("Controller")
        # self.setWidgetResizable(True)
        # self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.setWidget(QWidget())
        self.resize(100, 100)
        layout=QVBoxLayout()
        self.detector=Detector()
        layout.addWidget(self.detector)
        self.channelGroup=ChannelGroup(channelCount=self.setting.channel_count,fineTunes=self.setting.channels)
        layout.addWidget(self.channelGroup)

        # 非线性曲线设置面板
        curves_layout = QHBoxLayout()
        curves_layout.setSpacing(10)

        # 油门非线性设置 (默认通道1，索引0)
        self.throttle_curve_panel = CurveSettingPanel("油门曲线", channel=0)
        curves_layout.addWidget(self.throttle_curve_panel)

        # 转向非线性设置 (默认通道2，索引1)
        self.steering_curve_panel = CurveSettingPanel("转向曲线", channel=1)
        curves_layout.addWidget(self.steering_curve_panel)

        layout.addLayout(curves_layout)

        self.setLayout(layout)

        # 注意：不要在包含自定义绑制组件时使用透明背景
        # self.enableTransparentBackground()

        self.timer=QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.__emit_control_message)
        self.timer.start()

    def __init__(self,setting:Setting) -> None:
        super().__init__()
        self.setting=setting
        self.channelCount=self.setting.channel_count
        self.setupUi()
        self.detector.signal.connect(self.setChannelValue)

    def getChannelValues(self):
        return self.channelGroup.getValues()

    def _apply_curves(self, values: list[int]) -> list[int]:
        """应用非线性曲线到通道值"""
        result = values.copy()

        # 应用油门曲线
        throttle_ch = self.throttle_curve_panel.get_channel()
        if 0 <= throttle_ch < len(result):
            original = result[throttle_ch]
            result[throttle_ch] = int(self.throttle_curve_panel.apply_curve(original))
            # 更新曲线显示
            self.throttle_curve_panel.set_input_value(original / 100.0)

        # 应用转向曲线
        steering_ch = self.steering_curve_panel.get_channel()
        if 0 <= steering_ch < len(result):
            original = result[steering_ch]
            result[steering_ch] = int(self.steering_curve_panel.apply_curve(original))
            # 更新曲线显示
            self.steering_curve_panel.set_input_value(original / 100.0)

        return result

    def __emit_control_message(self):
        channelValues=self.getChannelValues()
        # 应用非线性曲线
        channelValues = self._apply_curves(channelValues)
        self.controlMessage.emit(channelValues)

    # 更新通道值
    def setChannelValue(self,values:list[int]):
        self.channelGroup.setValues(values)
        self.__emit_control_message()

    def setJoystickValue(self,x:float,y:float):
        self.channelGroup.setValue(0,round(50+x*50))
        self.channelGroup.setValue(1,round(50-y*50))
        self.__emit_control_message()


    def close(self):
        self.timer.stop()
        logging.info("controller timer stop")
        self.detector.close()
        logging.info("controller detector close")
        super().close()



if __name__ == "__main__":
    from pkg.model import Setting
    app = QApplication(sys.argv)
    setTheme(Theme.DARK)
    controller = Controller(Setting())
    controller.show()
    sys.exit(app.exec_())
        
        
