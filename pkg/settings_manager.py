"""
使用 QSettings 管理应用程序配置
"""
import logging
from typing import Any, Optional

from PyQt5.QtCore import QSettings


class SettingsManager:
    """基于 QSettings 的配置管理器"""

    # 单例实例
    _instance: Optional['SettingsManager'] = None

    # 默认配置值
    DEFAULTS = {
        # 服务器配置
        "server/host": "stream.api.andless.tech",
        "server/port": 30042,
        "server/insecure": True,

        # 设备配置
        "device/source_device_id": 1,
        "device/device_id": 1,
        "device/channel_count": 10,
        "device/token": "0",
        "device/arch": "x86_64",

        # MQTT 配置
        "mqtt/host": "stream.api.andless.tech",
        "mqtt/port": 31883,
        "mqtt/setting_topic": "andless/device/aiomqtt",

        # API 配置
        "api/base_url": "http://139.224.218.82:30080",
        "api/user_agent": "Python-Client/1.0",

        # 窗口配置
        "window/width": 600,
        "window/height": 800,
        "window/x": 0,
        "window/y": 0,

        # 通道配置
        "channels/values": [0] * 10,

        # 日志配置
        "log/level": "DEBUG",
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # 使用 INI 格式存储，文件名为 settings.ini
        self._settings = QSettings(
            QSettings.IniFormat,
            QSettings.UserScope,
            "Andless",
            "Console"
        )
        logging.info(f"Settings file: {self._settings.fileName()}")

    @property
    def settings(self) -> QSettings:
        return self._settings

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        if default is None:
            default = self.DEFAULTS.get(key)
        value = self._settings.value(key, default)

        # QSettings 会将某些类型转换为字符串，需要处理
        if isinstance(default, bool) and isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        if isinstance(default, int) and isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return default
        if isinstance(default, list) and isinstance(value, str):
            # 处理列表类型
            return default
        return value

    def set(self, key: str, value: Any):
        """设置配置值"""
        self._settings.setValue(key, value)

    def sync(self):
        """同步配置到磁盘"""
        self._settings.sync()

    def remove(self, key: str):
        """删除配置项"""
        self._settings.remove(key)

    def contains(self, key: str) -> bool:
        """检查配置项是否存在"""
        return self._settings.contains(key)

    def all_keys(self) -> list:
        """获取所有配置键"""
        return self._settings.allKeys()

    def clear(self):
        """清空所有配置"""
        self._settings.clear()

    # ========== 便捷属性访问 ==========

    # 服务器配置
    @property
    def host(self) -> str:
        return self.get("server/host")

    @host.setter
    def host(self, value: str):
        self.set("server/host", value)

    @property
    def port(self) -> int:
        return self.get("server/port")

    @port.setter
    def port(self, value: int):
        self.set("server/port", value)

    @property
    def insecure(self) -> bool:
        return self.get("server/insecure")

    @insecure.setter
    def insecure(self, value: bool):
        self.set("server/insecure", value)

    # 设备配置
    @property
    def source_device_id(self) -> int:
        return self.get("device/source_device_id")

    @source_device_id.setter
    def source_device_id(self, value: int):
        self.set("device/source_device_id", value)

    @property
    def device_id(self) -> int:
        return self.get("device/device_id")

    @device_id.setter
    def device_id(self, value: int):
        self.set("device/device_id", value)

    @property
    def channel_count(self) -> int:
        return self.get("device/channel_count")

    @channel_count.setter
    def channel_count(self, value: int):
        self.set("device/channel_count", value)

    @property
    def token(self) -> str:
        return self.get("device/token")

    @token.setter
    def token(self, value: str):
        self.set("device/token", value)

    @property
    def arch(self) -> str:
        return self.get("device/arch")

    @arch.setter
    def arch(self, value: str):
        self.set("device/arch", value)

    # MQTT 配置
    @property
    def mqtt_host(self) -> str:
        return self.get("mqtt/host")

    @mqtt_host.setter
    def mqtt_host(self, value: str):
        self.set("mqtt/host", value)

    @property
    def mqtt_port(self) -> int:
        return self.get("mqtt/port")

    @mqtt_port.setter
    def mqtt_port(self, value: int):
        self.set("mqtt/port", value)

    @property
    def mqtt_setting_topic(self) -> str:
        return self.get("mqtt/setting_topic")

    @mqtt_setting_topic.setter
    def mqtt_setting_topic(self, value: str):
        self.set("mqtt/setting_topic", value)

    # API 配置
    @property
    def base_url(self) -> str:
        return self.get("api/base_url")

    @base_url.setter
    def base_url(self, value: str):
        self.set("api/base_url", value)

    @property
    def user_agent(self) -> str:
        return self.get("api/user_agent")

    @user_agent.setter
    def user_agent(self, value: str):
        self.set("api/user_agent", value)

    # 窗口配置
    @property
    def window_width(self) -> int:
        return self.get("window/width")

    @window_width.setter
    def window_width(self, value: int):
        self.set("window/width", value)

    @property
    def window_height(self) -> int:
        return self.get("window/height")

    @window_height.setter
    def window_height(self, value: int):
        self.set("window/height", value)

    @property
    def window_x(self) -> int:
        return self.get("window/x")

    @window_x.setter
    def window_x(self, value: int):
        self.set("window/x", value)

    @property
    def window_y(self) -> int:
        return self.get("window/y")

    @window_y.setter
    def window_y(self, value: int):
        self.set("window/y", value)

    # 通道配置
    @property
    def channels(self) -> list:
        value = self.get("channels/values")
        if isinstance(value, list):
            return value
        # 如果是字符串格式，尝试解析
        if isinstance(value, str):
            try:
                import json
                return json.loads(value)
            except:
                pass
        return [0] * 10

    @channels.setter
    def channels(self, value: list):
        import json
        self.set("channels/values", json.dumps(value))

    # 日志配置
    @property
    def log_level(self) -> str:
        return self.get("log/level")

    @log_level.setter
    def log_level(self, value: str):
        self.set("log/level", value)

    def to_dict(self) -> dict:
        """将配置转换为字典格式（兼容旧代码）"""
        return {
            "host": self.host,
            "port": self.port,
            "insecure": self.insecure,
            "source_device_id": self.source_device_id,
            "device_id": self.device_id,
            "channel_count": self.channel_count,
            "token": self.token,
            "arch": self.arch,
            "mqtt_host": self.mqtt_host,
            "mqtt_port": self.mqtt_port,
            "mqtt_setting_topic": self.mqtt_setting_topic,
            "base_url": self.base_url,
            "user_agent": self.user_agent,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "window_x": self.window_x,
            "window_y": self.window_y,
            "channels": self.channels,
            "log_level": self.log_level,
        }

    def from_dict(self, data: dict):
        """从字典加载配置（兼容旧代码）"""
        key_mapping = {
            "host": "server/host",
            "port": "server/port",
            "insecure": "server/insecure",
            "source_device_id": "device/source_device_id",
            "device_id": "device/device_id",
            "channel_count": "device/channel_count",
            "token": "device/token",
            "arch": "device/arch",
            "mqtt_host": "mqtt/host",
            "mqtt_port": "mqtt/port",
            "mqtt_setting_topic": "mqtt/setting_topic",
            "base_url": "api/base_url",
            "user_agent": "api/user_agent",
            "window_width": "window/width",
            "window_height": "window/height",
            "window_x": "window/x",
            "window_y": "window/y",
            "log_level": "log/level",
        }

        for old_key, new_key in key_mapping.items():
            if old_key in data:
                self.set(new_key, data[old_key])

        # 特殊处理 channels
        if "channels" in data:
            self.channels = data["channels"]

        self.sync()


# 全局单例访问
settings_manager = SettingsManager()
