import numpy as np
import sounddevice as sd
import sys
from collections import deque
import time
import av


container=av.open("audio_input.g726","w",format="g726")
stream=container.add_stream("g726",rate=8000)
stream.layout="mono"
stream.bit_rate=4000

def audio_callback(indata, frames, time, status):
    frame=av.AudioFrame.from_ndarray(indata.reshape(1, -1),layout="mono")
    av.AudioResampler(format="pcm_s16le").resample(frame,stream)

def record_and_visualize(duration=None, samplerate=44100, channels=1, blocksize=1024):
    """录制音频并实时显示波形"""
    print("开始录音... 按Ctrl+C停止")
    print("=" * 80)
    
    try:
        with sd.InputStream(
            samplerate=samplerate,
            blocksize=blocksize,
            channels=channels,
            callback=audio_callback
        ):
            if duration:
                # 按指定时长录音
                time.sleep(duration)
            else:
                # 无限录音，直到用户中断
                while True:
                    time.sleep(0.1)
                    
    except KeyboardInterrupt:
        print("\n录音已停止")
    except Exception as e:
        print(f"\n发生错误: {e}")

if __name__ == "__main__":
    # 录制并实时显示波形（默认无限录制，按Ctrl+C停止）
    record_and_visualize(
        samplerate=8000,    # 采样率
        blocksize=1024,      # 每次处理的帧数
        channels=1           # 单声道
    )
