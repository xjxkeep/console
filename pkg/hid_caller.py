from PyQt5.QtCore import QObject, pyqtSignal, QThread
from pkg.model import HIDBody   
import uuid
import hid
import time
import queue
import threading
import json

class HIDConnectionThread(QThread):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    
    def __init__(self, vendor_id: int, product_id: int):
        super().__init__()
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.is_connected=False
        self.running = True
    
    def run(self):
        while self.running:
            try:
                devices = hid.enumerate(int(self.vendor_id), int(self.product_id))
                if devices and not self.is_connected:
                    self.connected.emit()
                    self.is_connected=True
                elif not devices and self.is_connected:
                    self.disconnected.emit()
                    self.is_connected=False
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
        self.frame_size=256
        self.buffer=bytearray()
    
    def run(self):
        while self.running and self.hid_device:
            try:
                # 读取HID数据
                data = self.hid_device.read(self.frame_size, timeout_ms=100)
                if data:
                    print("HID data received:",data)
                    json_str=bytes(data).strip(b'\x00').decode('utf-8', errors='ignore')
                    print(json_str)
                    if json_str:
                        try:
                            json_dict=json.loads(json_str)
                            hid_body=HIDBody(**json_dict)
                            print("HID body:",hid_body)
                            self.data_received.emit(hid_body)
                        except json.JSONDecodeError as e:
                            print(f"JSON解析失败: {e}, 数据: {json_str}")
                        except Exception as e:
                            print(f"HIDBody创建失败: {e}, 数据: {json_str}")
                            pass
            except Exception as e:
                if "timeout" not in str(e).lower():
                    print(f"HID data read error: {e}")
                time.sleep(0.01)
  
    
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
        self.frame_size=255
        


    def _on_device_connected(self):
        """设备连接成功时的处理"""
        try:
            # 打开HID设备
            self.hid_device = hid.device()
            self.hid_device.open(self.vendor_id, self.product_id)
            
            # 启动数据接收线程
            self.data_receiver_thread = HIDDataReceiverThread(self.hid_device)
            self.data_receiver_thread.data_received.connect(self.data_received)
            self.data_receiver_thread.start()
            self.connected.emit()
            print("HID device connected successfully")
            self.call_function("get_device_info",{})
            
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

    


    def _send(self, request: HIDBody):
        """发送HID请求"""
        if not self.hid_device:
            raise Exception("HID device not connected")
        
        try:
            # 序列化请求并分包
            packets = self._serialize_request_packets(request)
            
            # 发送所有数据包
            for packet in packets:
                
                self.hid_device.write(b'0'+packet)
                # 可选：在包之间添加短暂延迟
                time.sleep(0.001)
            
        except Exception as e:
            print(f"Failed to send HID request: {e}")
            raise
    
    def _serialize_request_packets(self, request: HIDBody) -> list:
        """序列化HIDRequest为多个frame_size字节的数据包"""
        try:
            # 将HIDRequest转换为JSON字符串
            json_str = request.model_dump_json()
            
            # 转换为字节数据
            data = json_str.encode('utf-8')
            
            packet_size = self.frame_size
            packets = []
            
            # 分包处理
            for i in range(0, len(data), packet_size):
                packet = bytearray(data[i:i + packet_size])
                
                while len(packet) < packet_size:
                    packet.append(0)
                
                packets.append(bytes(packet))
            
            return packets
            
        except Exception as e:
            print(f"Failed to serialize request packets: {e}")
            raise


    def call_function(self, method: str, args: dict) :
        """调用HID函数"""
        request_id=str(uuid.uuid4())
        request = HIDBody(type="request",cmd=method, args=args, request_id=request_id)
        self._send(request)
        return request_id



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


