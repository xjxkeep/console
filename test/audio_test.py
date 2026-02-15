import os
import sys
import signal
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pkg.buffer import BytesBufferStream
from pkg.audio import AudioRecorder, AudioPlayer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

encoder_buffer = BytesBufferStream(maxSize=1024*1024*2, timeout=5)
player_buffer = BytesBufferStream(maxSize=1024*1024*2, timeout=5)

recorder = AudioRecorder(buffer=encoder_buffer, format="g726")
player = AudioPlayer(buffer=player_buffer, format="g726")

def on_frame_encoded():
    data = encoder_buffer.read(1024)
    if data:
        player_buffer.write(data)

recorder.on_frame_encoded = on_frame_encoded

recorder.start()
player.start()

print("Audio test running — speak into mic to hear playback. Ctrl+C to stop.")

try:
    signal.pause()
except KeyboardInterrupt:
    pass
finally:
    print("\nShutting down...")
    recorder.close()
    player.close()
    print("Done.")
