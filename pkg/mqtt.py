import asyncio
from aiomqtt import Client
from PyQt5.QtCore import QObject,pyqtSignal
import threading
from protocol.video_pb2 import VideoAttributeMessage
import time
class MQTTClient(QObject):
    def __init__(self,setting:dict):
        
        super().__init__()
        self.setting=setting
        self.host=setting.get("mqtt_host","test.mosquitto.org")
        self.port=setting.get("mqtt_port",1883)
        self.setting_topic=setting.get("mqtt_setting_topic","demo/aiomqtt")
        self.running=False
        self.client=None
        
        
    
    
    def start(self):
        """Start the client in a new thread"""
        if self.running:
            return
        print("mqtt start")
        self.running = True
        self.loop = asyncio.new_event_loop()
        
        # Start event loop in new thread
        self.run_thread= threading.Thread(
            target=self._run_event_loop,
            daemon=True
        )
        self.run_thread.start()
    
    async def run(self):
        while self.running:
            try:
                async with Client(self.host,self.port) as client:
                    self.client=client
                    print("mqtt connected",self.client)
                    while self.running:
                        await asyncio.sleep(1)
            except Exception as e:
                print(e)
                await asyncio.sleep(1)

            
            
        
    def _run_event_loop(self):
        """Run the event loop in a separate thread"""
        asyncio.set_event_loop(self.loop)
        try:
            
            self.loop.run_until_complete(self.run())
            self.loop.run_forever()
        except Exception as e:
            print(e)
        finally:
            self.loop.close()
    
    async def update_video_setting(self,resolution,video_encode_type):
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
        await self.client.publish(self.setting_topic, video_setting.SerializeToString(), qos=1)
    
    def update_video_setting_sync(self,resolution,video_encode_type):
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
        print(self.setting_topic,"publish  video setting",video_setting)
        result=asyncio.run_coroutine_threadsafe(self.client.publish(self.setting_topic, video_setting.SerializeToString(), qos=1),self.loop)
        print("publish result",result.result())
        
    def close(self):
        self.running=False
        if self.loop is not None:
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.run_thread.join()
        if self.client is not None:
            self.client.close()
        self.client=None
        self.loop=None
        self.run_thread=None
        self.setting["mqtt_host"]=self.host
        self.setting["mqtt_port"]=self.port
        self.setting["mqtt_setting_topic"]=self.setting_topic
       
        
        



if __name__ == "__main__":
    async def publish_once():
        async with Client("test.mosquitto.org") as client:  # 默认端口 1883
            await client.publish("demo/aiomqtt", "Hello from aiomqtt!", qos=1)
        print(">>> 消息已发布")
    asyncio.run(publish_once())