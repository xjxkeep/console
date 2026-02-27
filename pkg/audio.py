import logging
from queue import Queue
import threading

import av
import numpy as np
import sounddevice as sd

from pkg.buffer import BytesBufferStream

# g726 8000
class AudioRecorder:
    def __init__(self, buffer: BytesBufferStream = None, scale=1, format="g726",
                 frame_size=1024, samplerate=8000,bitrate=32000, on_frame_encoded=None):
        self.buffer = buffer or BytesBufferStream(maxSize=1024*1024*2, timeout=5)
        self.samplerate = samplerate
        self.frame_size = frame_size
        self.running = False
        self.scale = scale
        self.format = format
        self.fifo = Queue()
        self.bitrate = bitrate
        self.pts = 0
        self.on_frame_encoded = on_frame_encoded
        self._thread = None

    def read(self, n):
        return self.buffer.read(n)

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            logging.info(f"{status}")
        pcm = np.frombuffer(indata, dtype=np.int16)
        pcm = np.clip(pcm * self.scale, -32768, 32767)
        frame = av.AudioFrame.from_ndarray(pcm.reshape(1, -1), layout="mono")
        frame.sample_rate = self.samplerate
        frame.pts = self.pts
        self.pts += len(pcm)
        logging.info(f"callback frame {frame}")
        self.fifo.put(frame)

    def _run(self):
        self.running = True

        self.sound_device_id = sd.default.device[0]
        container = av.open(self.buffer, "w", format=self.format, buffer_size=self.frame_size)
        stream = container.add_stream(self.format, rate=self.samplerate)
        assert isinstance(stream, av.AudioStream)
        stream.layout = "mono"
        stream.bit_rate = self.bitrate

        try:
            with sd.InputStream(
                device=self.sound_device_id,
                samplerate=self.samplerate,
                blocksize=self.frame_size,
                channels=1,
                dtype="int16",
                callback=self.audio_callback
            ):
                while self.running:
                    frame = self.fifo.get()
                    if frame is None:
                        break

                    for packet in stream.encode(frame):
                        logging.info(f"encode packet {packet}")
                        container.mux(packet)
                        if self.on_frame_encoded:
                            self.on_frame_encoded()
            self.fifo.put(None)
            container.close()
        except Exception as e:
            import traceback
            traceback.print_exc()
            logging.info(f"AudioRecorder _run error: {e}")

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def close(self):
        self.running = False
        self.fifo.put(None)
        self.buffer.close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)


class AudioPlayer:
    def __init__(self, buffer: BytesBufferStream = None, format="g726", scale=1,
                 frame_size=1024, samplerate=8000,bitrate=32000):
        self.buffer = buffer or BytesBufferStream(maxSize=1024*1024*2, timeout=5)
        self.format = format
        self.scale = scale
        self.frame_size = frame_size
        self.running = False
        self.samplerate = samplerate
        self.fifo = Queue()
        self._thread = None
        self._sample_buf = np.empty((0, 1), dtype=np.int16)
        self.bitrate = bitrate
    def write(self, data):
        logging.info(f"write {len(data)}")
        self.buffer.write(data)

    def audio_callback(self, outdata, frames, time_info, status):
        needed = frames
        chunks = []
        collected = 0

        # drain from _sample_buf first, then pull from fifo
        while collected < needed:
            if len(self._sample_buf) > 0:
                take = min(len(self._sample_buf), needed - collected)
                chunks.append(self._sample_buf[:take])
                self._sample_buf = self._sample_buf[take:]
                collected += take
            else:
                data = self.fifo.get()
                if data is None:
                    outdata[:] = 0
                    return
                self._sample_buf = data

        outdata[:] = np.concatenate(chunks, axis=0)

    def _run(self):
        self.running = True
        self.sound_device_id = sd.default.device[1]
        container = av.open(self.buffer, "r", format=self.format, buffer_size=self.frame_size,
                            options={"probesize": str(self.frame_size), "analyzeduration": "0"})
        stream = container.streams.audio[0]
        assert isinstance(stream, av.AudioStream)
        stream.layout = "mono"
        stream.bit_rate = self.bitrate

        try:
            with sd.OutputStream(
                device=self.sound_device_id,
                samplerate=self.samplerate,
                blocksize=self.frame_size,
                channels=1,
                dtype="int16",
                callback=self.audio_callback
            ):
                while self.running:
                    for frame in container.decode(stream):
                        logging.info(f"decode frame {frame}")
                        pcm = frame.to_ndarray()
                        pcm = np.clip(pcm * self.scale, -32768, 32767).astype(np.int16)
                        if not self.running:
                            break
                        self.fifo.put(pcm.T)

            container.close()
        except Exception as e:
            logging.info(f"AudioPlayer _run error: {e}")

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def close(self):
        self.running = False
        self.fifo.put(None)
        self.buffer.close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
