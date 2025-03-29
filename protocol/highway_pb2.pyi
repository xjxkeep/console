from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

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
        FILE: _ClassVar[Device.MessageType]
    VIDEO: Device.MessageType
    CONTROL: Device.MessageType
    REPORT: Device.MessageType
    FILE: Device.MessageType
    DEVICE_TYPE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_TYPE_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    device_type: Device.DeviceType
    message_type: Device.MessageType
    id: int
    def __init__(self, device_type: _Optional[_Union[Device.DeviceType, str]] = ..., message_type: _Optional[_Union[Device.MessageType, str]] = ..., id: _Optional[int] = ...) -> None: ...

class Register(_message.Message):
    __slots__ = ("device", "subscribe_device", "token", "read_only")
    DEVICE_FIELD_NUMBER: _ClassVar[int]
    SUBSCRIBE_DEVICE_FIELD_NUMBER: _ClassVar[int]
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    READ_ONLY_FIELD_NUMBER: _ClassVar[int]
    device: Device
    subscribe_device: Device
    token: str
    read_only: bool
    def __init__(self, device: _Optional[_Union[Device, _Mapping]] = ..., subscribe_device: _Optional[_Union[Device, _Mapping]] = ..., token: _Optional[str] = ..., read_only: bool = ...) -> None: ...

class Control(_message.Message):
    __slots__ = ("channels",)
    CHANNELS_FIELD_NUMBER: _ClassVar[int]
    channels: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, channels: _Optional[_Iterable[int]] = ...) -> None: ...

class Report(_message.Message):
    __slots__ = ("battery",)
    BATTERY_FIELD_NUMBER: _ClassVar[int]
    battery: float
    def __init__(self, battery: _Optional[float] = ...) -> None: ...

class Video(_message.Message):
    __slots__ = ("raw", "timestamp", "counter")
    RAW_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    COUNTER_FIELD_NUMBER: _ClassVar[int]
    raw: bytes
    timestamp: int
    counter: int
    def __init__(self, raw: _Optional[bytes] = ..., timestamp: _Optional[int] = ..., counter: _Optional[int] = ...) -> None: ...

class File(_message.Message):
    __slots__ = ("name", "offset", "total_size", "data", "checksum", "block_id", "last_block")
    NAME_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    TOTAL_SIZE_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    CHECKSUM_FIELD_NUMBER: _ClassVar[int]
    BLOCK_ID_FIELD_NUMBER: _ClassVar[int]
    LAST_BLOCK_FIELD_NUMBER: _ClassVar[int]
    name: str
    offset: int
    total_size: int
    data: bytes
    checksum: int
    block_id: int
    last_block: bool
    def __init__(self, name: _Optional[str] = ..., offset: _Optional[int] = ..., total_size: _Optional[int] = ..., data: _Optional[bytes] = ..., checksum: _Optional[int] = ..., block_id: _Optional[int] = ..., last_block: bool = ...) -> None: ...
