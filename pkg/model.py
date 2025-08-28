import string
from pydantic import BaseModel



class HIDBody(BaseModel):
    type: str = ""
    cmd: str = ""
    request_id: str = ""
    args: dict = {}
    returns: dict = {}

class Device(BaseModel):
    ID :int =0
    name: str = ""
    device_id: int = 0
    subscribe_id: int = 0
    register_ip: str = ""
    mac: str = ""
    version: str = ""
    token: str = ""

class Version(BaseModel):
    version: str = ""
    url: str = ""
    desc: str = ""
    force: bool = False
    arch: str = ""
    md5: str = ""

class VersionResponse(BaseModel):
    code: int = 0
    msg: str = ""
    data: Version

class DeviceResponse(BaseModel):
    code: int = 0
    msg: str = ""
    data: Device


class MqttMessage(BaseModel):
    width: int = 0
    height: int = 0
    video_encode_type: str = ""
    bABR: int = 0



class Setting(BaseModel):
    host: str = "stream.api.andless.tech"
    port: int = 30042
    insecure: bool = True
    source_device_id: int = 0
    channel_count: int = 10
    device_id: int = 1
    mqtt_port: int = 31883
    mqtt_setting_topic: str = "andless/device/aiomqtt"
    mqtt_host: str = "stream.api.andless.tech"
    base_url: str = "http://139.224.218.82:30080"
    user_agent: str = "Python-Client/1.0"
    token: str = "0"
    arch: str = "x86_64"
    channels: list[int] = [0]*10 
    window_width: int = 600
    window_height: int = 800