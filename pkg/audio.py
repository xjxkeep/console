import av
import numpy as np
import pyaudio
import os
from datetime import datetime
from PyQt5.QtCore import QObject,pyqtSignal
from queue import Queue
import threading
from codec import BufferStream

class MP3Encoder(QObject):
    frame_decoded = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.format="mp3"
        self.channels=1
        self.rate=16000
        self.chunk=1024
        self.p = pyaudio.PyAudio()
        self.audio_stream = self.p.open(format=pyaudio.paInt16,
                    channels=self.channels,
                    rate=self.rate,
                    input=True,
                    frames_per_buffer=self.chunk)
        self.out_buffer=BufferStream()
       
        self.encode_thread = threading.Thread(target=self.__encode_frames,daemon=True)
        self.running = True
        self.encode_thread.start()

    def close(self):
        self.running = False
        self.encode_thread.join()

    def write(self, data):
        if len(data)==0:
            return
        self.out_buffer.write(data)
        self.frame_decoded.emit()
    
    def read_frame(self):
        return self.out_buffer.readSingle()
                


    def __encode_frames(self):
        self.container = av.open(self,format=self.format,mode="w")
        self.audio_stream.start_stream()
        self.out_stream = self.container.add_stream(self.format, rate=self.rate)

        print("start decode")
        while self.running:
            try:
                data = self.audio_stream.read(self.chunk, exception_on_overflow=False)
                audio_data = np.frombuffer(data,dtype=np.int16)
                frame = av.AudioFrame.from_ndarray(np.expand_dims(audio_data, axis=0), format="s16",layout='mono')
                frame.sample_rate = self.rate
                frame.pts = av.time_base
                print(f"get frame: {len(audio_data)}")

                for packet in self.out_stream.encode(frame):
                    self.container.mux(packet)
            except Exception as e:
                print(e)
            
        
        self.audio_stream.stop_stream()
        self.audio_stream.close()
        self.container.close()
        self.p.terminate()



class MP3Decoder(QObject):
    frame_decoded = pyqtSignal()
    def __init__(self) -> None:
        super().__init__()
        self.running=True
        self.frames=Queue()
        self.rate=8000
        self.stream=BufferStream()
        self.decode_thread = threading.Thread(target=self.__decode_frames,daemon=True)
        self.decode_thread.start()
        
    def close(self):
        self.running=False
        self.decode_thread.join()
        
    
    def write(self,data):
        if len(data)==0:
            return
        self.stream.write(data)
    
    
    def read_pcm(self):
        return self.frames.get()
    
    def __decode_frames(self):
        self.container=av.open(self.stream,format="mp3")
        print("start decode")
        while self.running:
            for frame in self.container.decode(audio=0):
                pcm=frame.to_ndarray()
                self.frames.put(pcm)
                self.frame_decoded.emit()
            

def test_encoder():
    import time
    encoder=MP3Encoder()
    st=time.time()
    with open("audio.mp3","wb") as f:
        while True:
            data=encoder.read_frame()
            print(f"get encoded frame {data}")
            if time.time()-st>5:
                break
            if len(data)==0:
                continue
            f.write(data)


if __name__=="__main__":
    test_encoder()