import asyncio
import paho.mqtt.client as mqtt
from PyQt5.QtCore import QObject,pyqtSignal
import threading
from protocol.video_pb2 import VideoAttributeMessage
import time
from queue import Queue
from pkg.model import MqttMessage
import hashlib


def get_uuid(device_id: str, subscribe_id: str) -> str:
    """
    生成聊天UUID
    
    Args:
        device_id: 设备ID
        subscribe_id: 订阅ID
    
    Returns:
        32个字符的十六进制UUID字符串
    """
    # 1. 字典序小的在前
    if device_id < subscribe_id:
        first, second = device_id, subscribe_id
    else:
        first, second = subscribe_id, device_id
    
    # 2. 拼接字符串：first:second
    raw = f"{first}:{second}"
    
    # 3. 计算 SHA-256，取前 16 字节
    md = hashlib.sha256(raw.encode('utf-8')).digest()
    
    # 4. 转成 32 个十六进制字符
    uuid = md[:16].hex()
    
    return uuid


class MQTTClient:
    def __init__(self,setting:dict):
        self.setting=setting
        self.host=setting.get("mqtt_host","stream.api.andless.tech")
        self.port=setting.get("mqtt_port",31883)
        self.running=False
        self.client=mqtt.Client()
        self.fifo=Queue()    
        self.thread=None
        # 用于退出线程的特殊标记
        self._stop_sentinel = object()
        

    @property
    def setting_topic(self):
        basic_topic=self.setting.get("mqtt_setting_topic","andless/device/aiomqtt")
        device_id=self.setting.get("device_id",0)
        sub_id=self.setting.get("source_device_id",0)
        uuid=get_uuid(str(sub_id),str(device_id))
        return f"{basic_topic}/{uuid}"

    def start(self):
        self.running=True
        self.thread=threading.Thread(target=self.__run)
        self.thread.start()

    def __run(self):
        while self.running:
            try:
                print("mqtt client loop start")
                self.client.connect(self.host,self.port,60)
                self.client.loop_start()
                self.client.on_connect=self.__on_connect
            except Exception as e:
                print("mqtt client connect error",e)
                time.sleep(1)
                continue
            while self.running:
                try:
                    message=self.fifo.get(timeout=1)  # 添加超时，避免永久阻塞
                    if message is self._stop_sentinel:
                        break  # 收到退出信号，退出循环
                    print(self.setting_topic,"publish  video setting",message)
                    self.client.publish(self.setting_topic, message, qos=1)
                except:
                    # 超时或其他异常，继续循环检查running状态
                    continue

    def __on_connect(self,client,userdata,flags,rc):
        print("connected to mqtt server")
    

    def update_video_setting_sync(self,resolution,video_encode_type,bABR):
        if self.client is None:
            return
        video_setting=VideoAttributeMessage()
        if resolution=="高清":
            video_setting.width=1920
            video_setting.height=1080
        elif resolution=="标清":
            video_setting.width=1280
            video_setting.height=720
        elif resolution=="流畅":
            video_setting.width=640
            video_setting.height=360
        else:
            return
        video_setting.max_rate=10000000
        video_setting.frame_rate=30
        video_setting.video_encode_type=video_encode_type
        mqtt_message=MqttMessage(width=video_setting.width,height=video_setting.height,video_encode_type=video_setting.video_encode_type,bABR={"开启":1,"关闭":0}[bABR])
        self.fifo.put(mqtt_message.model_dump_json())
        
    def close(self):
        print("mqtt client close")
        self.running=False
        # 发送退出信号到队列，唤醒被阻塞的线程
        self.fifo.put_nowait(self._stop_sentinel)
        if self.client is not None:
            self.client.disconnect()
        if self.thread is not None:
            self.thread.join()
        print("mqtt client close end")
       
        
        



if __name__ == "__main__":
    # 测试代码
    client = MQTTClient({"mqtt_host": "test.mosquitto.org"})
    client.start()
    time.sleep(2)
    client.close()