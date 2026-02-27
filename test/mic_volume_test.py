"""
麦克风音量显示示例

使用 AudioRecorder 采集麦克风音频，同时将 PCM 数据
发送给 MicVolumeWidget 实时显示音量。
"""
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import pyqtSignal, QObject

from components.mic_volume import MicVolumeWidget
from pkg.buffer import BytesBufferStream
from pkg.audio import AudioRecorder

logging.basicConfig(level=logging.WARNING)


class VolumeEmitter(QObject):
    """跨线程信号桥：将音频线程的 PCM 数据发送到 Qt 主线程"""
    volumeReady = pyqtSignal(np.ndarray)


class MicVolumeDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("麦克风音量 - AudioRecorder 示例")
        self.setFixedSize(180, 360)

        self._emitter = VolumeEmitter()
        self._recorder = None

        self._init_ui()
        self._emitter.volumeReady.connect(self._on_volume)

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 音量组件
        self.volume_widget = MicVolumeWidget(label="MIC")
        layout.addWidget(self.volume_widget, stretch=1)

        # 状态标签
        self.status_label = QLabel("点击开始录音")
        self.status_label.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(self.status_label)

        # 按钮
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始")
        self.start_btn.clicked.connect(self._toggle)
        btn_layout.addWidget(self.start_btn)
        layout.addLayout(btn_layout)

    def _toggle(self):
        if self._recorder and self._recorder.running:
            self._stop()
        else:
            self._start()

    def _start(self):
        buffer = BytesBufferStream(maxSize=1024 * 1024 * 2, timeout=5)
        self._recorder = AudioRecorder(buffer=buffer, format="g726")

        # 保存原始回调，包装一层以提取音量
        original_callback = self._recorder.audio_callback

        def callback_with_volume(indata, frames, time_info, status):
            # 提取 PCM 用于音量显示
            pcm = np.frombuffer(indata, dtype=np.int16).copy()
            self._emitter.volumeReady.emit(pcm)
            # 调用原始回调继续编码流程
            original_callback(indata, frames, time_info, status)

        self._recorder.audio_callback = callback_with_volume
        self._recorder.start()

        self.start_btn.setText("停止")
        self.status_label.setText("录音中...")

    def _stop(self):
        if self._recorder:
            self._recorder.close()
            self._recorder = None

        self.start_btn.setText("开始")
        self.status_label.setText("已停止")

    def _on_volume(self, pcm: np.ndarray):
        self.volume_widget.setRMS(pcm)

    def closeEvent(self, event):
        self._stop()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    demo = MicVolumeDemo()
    demo.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
