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


class Setting:
    """应用程序配置类 - 基于 QSettings 的包装器"""

    def __init__(self):
        from pkg.settings_manager import settings_manager
        self._manager = settings_manager

    # 服务器配置
    @property
    def host(self) -> str:
        return self._manager.host

    @host.setter
    def host(self, value: str):
        self._manager.host = value

    @property
    def port(self) -> int:
        return self._manager.port

    @port.setter
    def port(self, value: int):
        self._manager.port = value

    @property
    def insecure(self) -> bool:
        return self._manager.insecure

    @insecure.setter
    def insecure(self, value: bool):
        self._manager.insecure = value

    # 设备配置
    @property
    def subscribe_id(self) -> int:
        return self._manager.subscribe_id

    @subscribe_id.setter
    def subscribe_id(self, value: int):
        self._manager.subscribe_id = value

    @property
    def device_id(self) -> int:
        return self._manager.device_id

    @device_id.setter
    def device_id(self, value: int):
        self._manager.device_id = value

    @property
    def channel_count(self) -> int:
        return self._manager.channel_count

    @channel_count.setter
    def channel_count(self, value: int):
        self._manager.channel_count = value

    @property
    def token(self) -> str:
        return self._manager.token

    @token.setter
    def token(self, value: str):
        self._manager.token = value

    @property
    def arch(self) -> str:
        return self._manager.arch

    @arch.setter
    def arch(self, value: str):
        self._manager.arch = value

    @property
    def p2p(self) -> bool:
        return self._manager.p2p

    @p2p.setter
    def p2p(self, value: bool):
        self._manager.p2p = value

    @property
    def room_id(self) -> str:
        return self._manager.room_id

    @room_id.setter
    def room_id(self, value: str):
        self._manager.room_id = value

    # MQTT 配置
    @property
    def mqtt_host(self) -> str:
        return self._manager.mqtt_host

    @mqtt_host.setter
    def mqtt_host(self, value: str):
        self._manager.mqtt_host = value

    @property
    def mqtt_port(self) -> int:
        return self._manager.mqtt_port

    @mqtt_port.setter
    def mqtt_port(self, value: int):
        self._manager.mqtt_port = value

    @property
    def mqtt_setting_topic(self) -> str:
        return self._manager.mqtt_setting_topic

    @mqtt_setting_topic.setter
    def mqtt_setting_topic(self, value: str):
        self._manager.mqtt_setting_topic = value

    # API 配置
    @property
    def base_url(self) -> str:
        return self._manager.base_url

    @base_url.setter
    def base_url(self, value: str):
        self._manager.base_url = value

    @property
    def user_agent(self) -> str:
        return self._manager.user_agent

    @user_agent.setter
    def user_agent(self, value: str):
        self._manager.user_agent = value

    # 窗口配置
    @property
    def window_width(self) -> int:
        return self._manager.window_width

    @window_width.setter
    def window_width(self, value: int):
        self._manager.window_width = value

    @property
    def window_height(self) -> int:
        return self._manager.window_height

    @window_height.setter
    def window_height(self, value: int):
        self._manager.window_height = value

    @property
    def window_x(self) -> int:
        return self._manager.window_x

    @window_x.setter
    def window_x(self, value: int):
        self._manager.window_x = value

    @property
    def window_y(self) -> int:
        return self._manager.window_y

    @window_y.setter
    def window_y(self, value: int):
        self._manager.window_y = value

    # 通道配置
    @property
    def channels(self) -> list:
        return self._manager.channels

    @channels.setter
    def channels(self, value: list):
        self._manager.channels = value

    # 日志配置
    @property
    def log_level(self) -> str:
        return self._manager.log_level

    @log_level.setter
    def log_level(self, value: str):
        self._manager.log_level = value

    def model_dump(self) -> dict:
        """兼容 Pydantic 的 model_dump 方法"""
        return self._manager.to_dict()

    def sync(self):
        """同步配置到磁盘"""
        self._manager.sync()

    @classmethod
    def model_validate_json(cls, json_data: str) -> 'Setting':
        """兼容 Pydantic 的 model_validate_json 方法（用于迁移旧配置）"""
        import json
        data = json.loads(json_data)
        setting = cls()
        setting._manager.from_dict(data)
        return setting

    def __str__(self) -> str:
        return str(self.model_dump())