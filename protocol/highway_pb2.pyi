from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Device(_message.Message):
    __slots__ = ("device_type", "message_type", "id")
    class DeviceType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        CONTROLLER: _ClassVar[Device.DeviceType]
        RECEIVER: _ClassVar[Device.DeviceType]
    CONTROLLER: Device.DeviceType
    RECEIVER: Device.DeviceType
    class MessageType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        VIDEO: _ClassVar[Device.MessageType]
        CONTROL: _ClassVar[Device.MessageType]
        REPORT: _ClassVar[Device.MessageType]
    VIDEO: Device.MessageType
    CONTROL: Device.MessageType
    REPORT: Device.MessageType
    DEVICE_TYPE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_TYPE_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    device_type: Device.DeviceType
    message_type: Device.MessageType
    id: int
    def __init__(self, device_type: _Optional[_Union[Device.DeviceType, str]] = ..., message_type: _Optional[_Union[Device.MessageType, str]] = ..., id: _Optional[int] = ...) -> None: ...

class Register(_message.Message):
    __slots__ = ("device", "subscribe_device", "token")
    DEVICE_FIELD_NUMBER: _ClassVar[int]
    SUBSCRIBE_DEVICE_FIELD_NUMBER: _ClassVar[int]
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    device: Device
    subscribe_device: Device
    token: str
    def __init__(self, device: _Optional[_Union[Device, _Mapping]] = ..., subscribe_device: _Optional[_Union[Device, _Mapping]] = ..., token: _Optional[str] = ...) -> None: ...

class Control(_message.Message):
    __slots__ = ("channels",)
    CHANNELS_FIELD_NUMBER: _ClassVar[int]
    channels: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, channels: _Optional[_Iterable[int]] = ...) -> None: ...

class Video(_message.Message):
    __slots__ = ("raw",)
    RAW_FIELD_NUMBER: _ClassVar[int]
    raw: bytes
    def __init__(self, raw: _Optional[bytes] = ...) -> None: ...

class Report(_message.Message):
    __slots__ = ("battery",)
    BATTERY_FIELD_NUMBER: _ClassVar[int]
    battery: float
    def __init__(self, battery: _Optional[float] = ...) -> None: ...
