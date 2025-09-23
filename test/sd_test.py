import numpy as np
import sounddevice as sd

def play_sine_wave(frequency=440, duration=2, samplerate=44100, volume=0.5):
    """
    播放正弦波音频
    
    参数:
        frequency: 正弦波频率(Hz)，默认440Hz(A4音)
        duration: 播放时长(秒)，默认2秒
        samplerate: 采样率，默认44100Hz
        volume: 音量(0-1之间)，默认0.5
    """
    # 生成时间轴
    t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
    
    # 生成正弦波数据 (振幅限制在-1到1之间)
    sine_wave = volume * np.sin(2 * np.pi * frequency * t)
    
    # 播放音频
    print(f"播放 {frequency}Hz 正弦波，时长 {duration}秒...")
    sd.play(sine_wave, samplerate=samplerate)
    
    # 等待播放完成
    sd.wait()
    print("播放结束")

if __name__ == "__main__":
    # 示例1: 播放440Hz(A4)正弦波，持续2秒
    play_sine_wave()
    
    # 示例2: 播放880Hz(A5)正弦波，持续3秒，音量0.3
    # play_sine_wave(frequency=880, duration=3, volume=0.3)
    
    # 示例3: 播放1000Hz正弦波，使用22050采样率
    # play_sine_wave(frequency=1000, duration=1, samplerate=22050)
