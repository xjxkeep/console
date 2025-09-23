import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pkg.audio import AudioRecorder,AudioPlayer
import time
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QApplication,QWidget

class AudioTest(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Test")
        self.setGeometry(100,100,800,600)
        self.show()
        self.audio_recorder=AudioRecorder()
        self.audio_thread=QThread()
        self.audio_recorder.moveToThread(self.audio_thread)
        self.audio_thread.started.connect(self.audio_recorder.run_task)
        self.audio_thread.finished.connect(self.audio_recorder.deleteLater)
        self.audio_thread.start()
        
        self.audio_player=AudioPlayer()
        self.audio_player_thread=QThread()
        self.audio_player.moveToThread(self.audio_player_thread)
        self.audio_player_thread.started.connect(self.audio_player.run_task)
        self.audio_player_thread.finished.connect(self.audio_player.deleteLater)
        self.audio_player_thread.start()
    
        self.audio_recorder.frame_encoded.connect(self.receive_audio_frame)
        
        
    def receive_audio_frame(self):
        
        data=self.audio_recorder.read(1024)
        print("receive_audio_frame",len(data))
        self.audio_player.write(data)
        
        

app=QApplication(sys.argv)

at=AudioTest()
at.show()
app.exec_()