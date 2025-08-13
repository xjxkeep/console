from PyQt5.QtCore import QObject, pyqtSignal, QThread
from model import HIDBody   
import uuid
import hid
import time
import queue
import threading


class HIDConnectionThread(QThread):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    
    def __init__(self, vendor_id: int, product_id: int):
        super().__init__()
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.running = True
    
    def run(self):
        while self.running:
            try:
                devices = hid.enumerate(int(self.vendor_id), int(self.product_id))
                if devices:
                    self.connected.emit()
                else:
                    self.disconnected.emit()
                time.sleep(1)
            except Exception as e:
                print(f"HID connection error: {e}")
                time.sleep(1)
    
    def stop(self):
        self.running = False
        self.wait()

class HIDDataReceiverThread(QThread):
    data_received = pyqtSignal(HIDBody)
    
    def __init__(self, hid_device):
        super().__init__()
        self.hid_device = hid_device
        self.running = True
        self.buffer=bytearray()
    
    def run(self):
        while self.running and self.hid_device:
            try:
                # 读取HID数据
                data = self.hid_device.read(128, timeout_ms=100)
                if data:
                    self.buffer.extend(data)
                    self.__parse_frame()
            except Exception as e:
                if "timeout" not in str(e).lower():
                    print(f"HID data read error: {e}")
                time.sleep(0.01)
    def __parse_frame(self):
        """解析缓冲区中的帧数据，提取完整的JSON并序列化为HIDBody"""
        if not self.buffer:
            return
        
        # 过滤掉值为0的字节（HID填充字节）
        filtered_buffer = bytearray()
        for byte in self.buffer:
            if byte != 0:
                filtered_buffer.append(byte)
        
        if not filtered_buffer:
            # 如果过滤后没有数据，清空原缓冲区
            self.buffer.clear()
            return
        
        try:
            # 转换为字符串
            buffer_str = filtered_buffer.decode('utf-8', errors='ignore')
            
            # 查找完整的JSON对象
            json_start = 0
            brace_count = 0
            in_string = False
            escape_next = False
            processed_length = 0
            
            for i, char in enumerate(buffer_str):
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if not in_string:
                    if char == '{':
                        if brace_count == 0:
                            json_start = i
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            # 找到一个完整的JSON对象
                            json_str = buffer_str[json_start:i+1]
                            try:
                                # 解析JSON并创建HIDBody
                                import json
                                response_dict = json.loads(json_str)
                                hid_body = HIDBody(**response_dict)
                                self.data_received.emit(hid_body)
                                
                                
                                # 更新已处理的数据长度
                                processed_length = i + 1
                                
                            except json.JSONDecodeError as e:
                                print(f"JSON解析失败: {e}, 数据: {json_str}")
                                # 如果解析失败，可能是数据不完整，继续等待更多数据
                                break
                            except Exception as e:
                                print(f"HIDBody创建失败: {e}")
                                processed_length = i + 1
            
            # 移除已处理的数据
            if processed_length > 0:
                # 计算原始缓冲区中对应的字节位置
                original_processed = 0
                filtered_index = 0
                
                for i, byte in enumerate(self.buffer):
                    if byte != 0:  # 非填充字节
                        if filtered_index >= processed_length:
                            break
                        filtered_index += 1
                    original_processed = i + 1
                
                # 移除已处理的原始数据
                self.buffer = self.buffer[original_processed:]
                
            
        except Exception as e:
            print(f"帧解析失败: {e}")
            # 如果出现严重错误，清空缓冲区
            self.buffer.clear()
    
    def stop(self):
        self.running = False
        self.wait()

class HID(QObject):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    data_received = pyqtSignal(HIDBody)
    

    def __init__(self, vendor_id: int, product_id: int):
        super().__init__()
        self.hid_device = None
        self.vendor_id = vendor_id
        self.product_id = product_id
        
        # 响应队列和等待字典
        self.response_queue = queue.Queue()
        self.pending_requests = {}  # request_id -> threading.Event()
        self.pending_lock = threading.Lock()
        self.responses={}

        
        # 未匹配响应队列（用于异步读取）
        self.unmatched_responses = queue.Queue()
        
        # 数据缓冲相关
        self.data_buffer = bytearray()
        self.buffer_lock = threading.Lock()
        
        # 连接监控线程
        self.connection_thread = HIDConnectionThread(vendor_id, product_id)
        self.connection_thread.connected.connect(self._on_device_connected)
        self.connection_thread.disconnected.connect(self._on_device_disconnected)
        self.connection_thread.start()
        
        # 数据接收线程
        self.data_receiver_thread = None
        


    def _on_device_connected(self):
        """设备连接成功时的处理"""
        try:
            # 打开HID设备
            self.hid_device = hid.device()
            self.hid_device.open(self.vendor_id, self.product_id)
            
            # 启动数据接收线程
            self.data_receiver_thread = HIDDataReceiverThread(self.hid_device)
            self.data_receiver_thread.data_received.connect(self._on_data_received)
            self.data_receiver_thread.start()
            

            
            self.connected.emit()
            print("HID device connected successfully")
            
        except Exception as e:
            print(f"Failed to connect to HID device: {e}")
            self._on_device_disconnected()



    def _on_device_disconnected(self):
        """设备断开连接时的处理"""
        # 停止数据接收线程
        if self.data_receiver_thread:
            self.data_receiver_thread.stop()
            self.data_receiver_thread = None
        

        
        # 关闭HID设备
        if self.hid_device:
            try:
                self.hid_device.close()
            except:
                pass
            self.hid_device = None
        
        # 清理所有等待的请求
        with self.pending_lock:
            for event in self.pending_requests.values():
                event.set()
            self.pending_requests.clear()
        
        self.disconnected.emit()
        print("HID device disconnected")

    def _on_data_received(self, hid_body: HIDBody):
        
        if hid_body.type=="response":
            if hid_body.request_id in self.pending_requests:
                self.responses[hid_body.request_id]=hid_body
                self.pending_requests[hid_body.request_id].set()

        self.data_received.emit(hid_body)


    def _send(self, request: HIDBody):
        """发送HID请求"""
        if not self.hid_device:
            raise Exception("HID device not connected")
        
        try:
            # 序列化请求并分包
            packets = self._serialize_request_packets(request)
            
            # 发送所有数据包
            for packet in packets:
                self.hid_device.write(packet)
                # 可选：在包之间添加短暂延迟
                time.sleep(0.001)
            
        except Exception as e:
            print(f"Failed to send HID request: {e}")
            raise

    def _serialize_request_packets(self, request: HIDBody) -> list:
        """序列化HIDRequest为多个128字节的数据包"""
        try:
            # 将HIDRequest转换为JSON字符串
            import json
            json_str = request.model_dump_json()
            
            # 转换为字节数据
            data = json_str.encode('utf-8')
            
            # 按照128字节分包
            packet_size = 128
            packets = []
            
            # 分包处理
            for i in range(0, len(data), packet_size):
                packet = bytearray(data[i:i + packet_size])
                
                # 如果包大小不足128字节，用0填充
                while len(packet) < packet_size:
                    packet.append(0)
                
                packets.append(bytes(packet))
            
            return packets
            
        except Exception as e:
            print(f"Failed to serialize request packets: {e}")
            raise

    def _recv(self, request_id: str) -> HIDBody:
        """阻塞等待指定请求的响应"""
        # 创建等待事件
        with self.pending_lock:
            event = self.pending_requests[request_id]
        event.wait()
        with self.pending_lock:
            del self.pending_requests[request_id]
        response=self.responses[request_id]
        del self.responses[request_id]
        return response

    def call_function(self, method: str, args: dict) -> HIDBody:
        """调用HID函数"""
        request_id=str(uuid.uuid4())
        request = HIDBody(type="request",cmd=method, args=args, request_id=request_id)
        event = threading.Event()
        with self.pending_lock:
            self.pending_requests[request_id] = event
        self._send(request)
        response = self._recv(request.request_id)
        return response



    def cleanup(self):
        """清理资源"""
        # 停止连接监控线程
        if hasattr(self, 'connection_thread'):
            self.connection_thread.stop()
        
        # 停止数据接收线程
        if self.data_receiver_thread:
            self.data_receiver_thread.stop()
        
        # 关闭HID设备
        if self.hid_device:
            try:
                self.hid_device.close()
            except:
                pass