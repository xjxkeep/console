import os
import sys
import signal
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pkg.buffer import BytesBufferStream
from pkg.audio import AudioRecorder, AudioPlayer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

shared_buffer = BytesBufferStream(maxSize=1024*1024*2, timeout=5)
recorder = AudioRecorder(buffer=shared_buffer, format="g726",frame_size=128)
player = AudioPlayer(buffer=shared_buffer, format="g726",frame_size=128)

recorder.start()
player.start()

print("Audio echo running — speak into mic to hear playback. Ctrl+C to stop.")

try:
    signal.pause()
except KeyboardInterrupt:
    pass
finally:
    print("\nShutting down...")
    recorder.close()
    player.close()
    print("Done.")
