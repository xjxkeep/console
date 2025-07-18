
import threading
from collections import deque
import time
import io
import asyncio
from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=1)

class RingBuffer:
    def __init__(self,maxSize=1024*1024,blocked=True,timeout=None):
        self.maxSize=maxSize
        self.blocked=blocked
        self.timeout=timeout
        self.buffer=[b'0' for _ in range(maxSize)]
        self.semaphore = threading.Semaphore(0)
        self.running = True
        self.pos=0

    def read(self,n):
        self.semaphore.acquire(n)
        data=self.buffer[self.pos:self.pos+n]
        self.pos=(self.pos+n)%self.maxSize
        if data is None:
            return data
        return data

    def write(self,data):
        if len(data)+self.pos>self.maxSize:
            self.buffer[self.pos:]=data[self.maxSize-self.pos:]
            self.buffer[:len(data)-self.maxSize+self.pos]=data[:self.maxSize-self.pos]
        else:
            self.buffer[self.pos:self.pos+len(data)]=data[:]
        self.semaphore.release(len(data))

     

     


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
                print("fifo full")
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
        self.semaphore.release(10)
        self.buffer.clear()

class RingBytesIO:
    def __init__(self,maxSize=0,blocked=True,timeout=None):
        self.maxSize=maxSize
        self.blocked=blocked
        self.timeout=timeout
        self.buffer=io.BytesIO()
        self.semaphore = threading.Semaphore(0)
        self.running = True
        self.lock = threading.Lock()
        self.read_pos=0
        self.read_count=0
        self.read_latency=0.0
        self.write_count=0
        self.write_latency=0.0
    
    def read(self,n):
        with self.lock:
            self.buffer.seek(self.read_pos)
            data=self.buffer.read(n)
            start_time=time.time()
            self.read_pos+=len(data)
            if self.read_pos>1024*1024:
                self.buffer=io.BytesIO(self.buffer.getvalue()[self.read_pos:])
                self.read_pos=0 
            self.read_latency+=time.time()-start_time
            self.read_count+=1
            return data
        
    def write(self,data):
        start_time=time.time()
        with self.lock:
            self.buffer.write(data)
            self.write_count+=1
            self.write_latency+=time.time()-start_time
            self.semaphore.release(len(data))
            return len(data)
    def close(self):
        self.running = False
        self.semaphore.release(10)
        self.buffer.close()

