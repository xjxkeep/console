
import threading
from collections import deque
import time
import io
import asyncio
from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=1)


     
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
        if not self.running:
            return bytes()
        acquired = self.semaphore.acquire(blocking=self.blocked,timeout=self.timeout)
        if not self.running or not acquired:
            return bytes()
        
        with self.lock:  # Use lock to ensure thread-safe access to the buffer
            self.buffer_size-=1
            return self.buffer.popleft()

    def __write(self, data):
        with self.lock:  # Use lock to ensure thread-safe access to the buffer
            self.buffer.append(data)
            self.buffer_size+=1
            if self.maxSize>0 and self.buffer_size>self.maxSize:
                self.buffer.popleft()
                self.buffer_size-=1
            else:
                self.semaphore.release()

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
