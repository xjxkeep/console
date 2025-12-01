
import threading
from collections import deque
import time
import io
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=1)

class BytesBufferStream:
    
    def __init__(self, maxSize=1024*1024*20, timeout=None): # maxSize now in bytes
        self.maxSize = maxSize
        self.timeout = timeout
        self.buffer = b''  # Store as a single bytes object for easy byte-wise reading
        self.running = True
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock) # Use Condition for waiting/notifying
        self.total_size = 0

    def data_len(self):
        with self.lock:
            return len(self.buffer)
    
    # --- FFmpeg/PyAV 期望调用的方法 ---
    def read(self, n):
        with self.lock:
            if not self.running:
                return b''

            # 1. Wait until there is *some* data
            if not self.buffer:
                # Wait for data or timeout
                acquired = self.condition.wait(self.timeout)
                if not acquired or not self.running:
                    # Returning b'' if timed out or stopped is critical for non-EOF distinction
                    return b'' 
            
            # 2. Extract up to n bytes
            read_data = self.buffer[:n]
            
            # 3. Update the buffer and size
            self.buffer = self.buffer[n:]
            self.total_size -= len(read_data)
            
            return read_data

    def write(self, data):
        if not self.running or not data:
            return

        with self.lock:
            # Drop oldest data if exceeding maxSize (optional for live stream)
            new_data_len = len(data)
            self.buffer += data
            self.total_size += new_data_len
            
            # Enforce max size by trimming the front
            if self.maxSize > 0 and self.total_size > self.maxSize:
                excess = self.total_size - self.maxSize
                self.buffer = self.buffer[excess:]
                self.total_size = self.maxSize
            
            # Notify waiting readers
            self.condition.notify()

    def close(self):
        with self.lock:
            self.running = False
            self.condition.notify_all() # Wake up all waiting readers
            self.buffer = b''
            self.total_size = 0

    # Retain your original block-read method, renamed for clarity
    def read_block(self):
        # This original logic is not used by PyAV/FFmpeg for decoding
        # but could be used elsewhere in your application.
        # However, since the internal buffer is now a single bytes object, 
        # this method is no longer easily implemented.
        raise NotImplementedError("Block reading is not supported in the new byte stream mode.")



     
class BufferStream:
    
    def __init__(self,maxSize=0,blocked=True,timeout=None):
        self.maxSize=maxSize
        self.blocked=blocked
        self.timeout=timeout
        self.buffer = deque()
        self.semaphore = threading.Semaphore(0)
        self.running = True
        self.lock = threading.Lock()  # Add a lock for buffer operations
        self.buffer_size=0


    def size(self):
        with self.lock:
            return self.buffer_size

    def __read(self):
        try:
            if not self.running:
                return bytes()
            acquired = self.semaphore.acquire(blocking=self.blocked,timeout=self.timeout)
            if not self.running or not acquired:
                return bytes()
            
            with self.lock:  # Use lock to ensure thread-safe access to the buffer
                self.buffer_size-=1
                return self.buffer.popleft()
        except Exception as e:
            logging.error(f"__read error {e}")
            return bytes()

    def __write(self, data):
        try:
            with self.lock:  # Use lock to ensure thread-safe access to the buffer
                self.buffer.append(data)
                self.buffer_size+=1
                if self.maxSize>0 and self.buffer_size>self.maxSize:
                    self.buffer.popleft()
                    self.buffer_size-=1
                else:
                    self.semaphore.release()
        except Exception as e:
            logging.error(f"__write error {e}")

    def readSingle(self):
        result = self.__read()
        return result
    
    
    async def read_single_async(self):
        loop=asyncio.get_event_loop()
        result=await loop.run_in_executor(executor,self.__read)
        return result
    
  
    def read(self, n):
        return self.__read()
    
    def write(self, data):
        self.__write(data)

    
    def close(self):
        self.running = False
        self.semaphore.release(1024)
        self.buffer.clear()
