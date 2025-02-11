import ffmpeg
import numpy as np
import threading
import time
from PyQt5.QtCore import QObject,pyqtSignal

class H264Decoder(QObject):
    frame_decoded = pyqtSignal(np.ndarray)
    def __init__(self, frame_height=1080, frame_width=1920, frame_size=None):
        super().__init__()
        self.process = (
            ffmpeg
            .input("",f="h264")
            .output('pipe:1', format='rawvideo',pix_fmt='rgb24')
            .run_async(pipe_stdout=True, pipe_stdin=True)
        )
        self.frame_height = frame_height
        self.frame_width = frame_width
        self.frame_size = frame_height * frame_width * 3
        self.decode_thread = threading.Thread(target=self.__decode_frames,daemon=True)
        self.running = True
        self.decode_thread.start()
    
    def close(self):
        self.running = False
        self.decode_thread.join()
        self.process.stdin.close()
        self.process.stdout.close()
        self.process.wait()
    
    def write(self, data):
        self.process.stdin.write(data)
            
    def __decode_frames(self):
        while self.running:
            data = self.process.stdout.read(self.frame_size)
            if not data:
                time.sleep(0.01)
                continue
            frame = np.frombuffer(data, np.uint8)
            frame = frame.reshape([self.frame_height, self.frame_width, 3])
            self.frame_decoded.emit(frame)
    
    


if __name__ == "__main__":
    decoder = H264Decoder()

    with open("/Users/xiongjinxin/workspace/endless/console/output.h264", "rb") as f:
        data = f.read()
        decoder.write(data)
    decoder.close()
