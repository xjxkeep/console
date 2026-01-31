from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ControlMessage(_message.Message):
    __slots__ = ("type",)
    class ControlType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        SEND_START: _ClassVar[ControlMessage.ControlType]
        SEND_STOP: _ClassVar[ControlMessage.ControlType]
    SEND_START: ControlMessage.ControlType
    SEND_STOP: ControlMessage.ControlType
    TYPE_FIELD_NUMBER: _ClassVar[int]
    type: ControlMessage.ControlType
    def __init__(self, type: _Optional[_Union[ControlMessage.ControlType, str]] = ...) -> None: ...

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
        AUDIO: _ClassVar[Device.MessageType]
        DEVICEPARAM: _ClassVar[Device.MessageType]
        CLOCKSYNCHRONIZATIONPARAM: _ClassVar[Device.MessageType]
        VIDEO_FEEDBACK: _ClassVar[Device.MessageType]
        DATAGRAM: _ClassVar[Device.MessageType]
        STREAM_CONTROL: _ClassVar[Device.MessageType]
    VIDEO: Device.MessageType
    CONTROL: Device.MessageType
    REPORT: Device.MessageType
    FILE: Device.MessageType
    AUDIO: Device.MessageType
    DEVICEPARAM: Device.MessageType
    CLOCKSYNCHRONIZATIONPARAM: Device.MessageType
    VIDEO_FEEDBACK: Device.MessageType
    DATAGRAM: Device.MessageType
    STREAM_CONTROL: Device.MessageType
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
    def __init__(self, device: _Optional[_Union[Device, _Mapping]] = ..., subscribe_device: _Optional[_Union[Device, _Mapping]] = ..., token: _Optional[str] = ..., read_only: _Optional[bool] = ...) -> None: ...

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
    __slots__ = ("raw", "timestamp", "frame_id", "slice_id", "slice_count", "nalu_type", "code_type")
    class NaluType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        NALU_TYPE_UNSPECIFIED: _ClassVar[Video.NaluType]
        NALU_TYPE_NON_IDR_SLICE: _ClassVar[Video.NaluType]
        NALU_TYPE_DATA_PARTITION_A: _ClassVar[Video.NaluType]
        NALU_TYPE_DATA_PARTITION_B: _ClassVar[Video.NaluType]
        NALU_TYPE_DATA_PARTITION_C: _ClassVar[Video.NaluType]
        NALU_TYPE_IDR_SLICE: _ClassVar[Video.NaluType]
        NALU_TYPE_SEI: _ClassVar[Video.NaluType]
        NALU_TYPE_SPS: _ClassVar[Video.NaluType]
        NALU_TYPE_PPS: _ClassVar[Video.NaluType]
        NALU_TYPE_ACCESS_UNIT_DELIMITER: _ClassVar[Video.NaluType]
        NALU_TYPE_END_OF_SEQUENCE: _ClassVar[Video.NaluType]
        NALU_TYPE_END_OF_STREAM: _ClassVar[Video.NaluType]
        NALU_TYPE_FILLER_DATA: _ClassVar[Video.NaluType]
        NALU_TYPE_SPS_EXTENSION: _ClassVar[Video.NaluType]
        NALU_TYPE_PREFIX_NALU: _ClassVar[Video.NaluType]
        NALU_TYPE_SUBSET_SPS: _ClassVar[Video.NaluType]
        NALU_TYPE_DEPTH_PARAMETER_SET: _ClassVar[Video.NaluType]
        NALU_TYPE_DEPTH_VIEW_SLICE: _ClassVar[Video.NaluType]
    NALU_TYPE_UNSPECIFIED: Video.NaluType
    NALU_TYPE_NON_IDR_SLICE: Video.NaluType
    NALU_TYPE_DATA_PARTITION_A: Video.NaluType
    NALU_TYPE_DATA_PARTITION_B: Video.NaluType
    NALU_TYPE_DATA_PARTITION_C: Video.NaluType
    NALU_TYPE_IDR_SLICE: Video.NaluType
    NALU_TYPE_SEI: Video.NaluType
    NALU_TYPE_SPS: Video.NaluType
    NALU_TYPE_PPS: Video.NaluType
    NALU_TYPE_ACCESS_UNIT_DELIMITER: Video.NaluType
    NALU_TYPE_END_OF_SEQUENCE: Video.NaluType
    NALU_TYPE_END_OF_STREAM: Video.NaluType
    NALU_TYPE_FILLER_DATA: Video.NaluType
    NALU_TYPE_SPS_EXTENSION: Video.NaluType
    NALU_TYPE_PREFIX_NALU: Video.NaluType
    NALU_TYPE_SUBSET_SPS: Video.NaluType
    NALU_TYPE_DEPTH_PARAMETER_SET: Video.NaluType
    NALU_TYPE_DEPTH_VIEW_SLICE: Video.NaluType
    class CodeType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        H264: _ClassVar[Video.CodeType]
        H265: _ClassVar[Video.CodeType]
    H264: Video.CodeType
    H265: Video.CodeType
    RAW_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    FRAME_ID_FIELD_NUMBER: _ClassVar[int]
    SLICE_ID_FIELD_NUMBER: _ClassVar[int]
    SLICE_COUNT_FIELD_NUMBER: _ClassVar[int]
    NALU_TYPE_FIELD_NUMBER: _ClassVar[int]
    CODE_TYPE_FIELD_NUMBER: _ClassVar[int]
    raw: bytes
    timestamp: int
    frame_id: int
    slice_id: int
    slice_count: int
    nalu_type: Video.NaluType
    code_type: Video.CodeType
    def __init__(self, raw: _Optional[bytes] = ..., timestamp: _Optional[int] = ..., frame_id: _Optional[int] = ..., slice_id: _Optional[int] = ..., slice_count: _Optional[int] = ..., nalu_type: _Optional[_Union[Video.NaluType, str]] = ..., code_type: _Optional[_Union[Video.CodeType, str]] = ...) -> None: ...

class VideoFeedback(_message.Message):
    __slots__ = ("received_frame_index", "lost_frame_count")
    RECEIVED_FRAME_INDEX_FIELD_NUMBER: _ClassVar[int]
    LOST_FRAME_COUNT_FIELD_NUMBER: _ClassVar[int]
    received_frame_index: int
    lost_frame_count: int
    def __init__(self, received_frame_index: _Optional[int] = ..., lost_frame_count: _Optional[int] = ...) -> None: ...

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
    def __init__(self, name: _Optional[str] = ..., offset: _Optional[int] = ..., total_size: _Optional[int] = ..., data: _Optional[bytes] = ..., checksum: _Optional[int] = ..., block_id: _Optional[int] = ..., last_block: _Optional[bool] = ...) -> None: ...

class Audio(_message.Message):
    __slots__ = ("raw", "timestamp", "counter")
    RAW_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    COUNTER_FIELD_NUMBER: _ClassVar[int]
    raw: bytes
    timestamp: int
    counter: int
    def __init__(self, raw: _Optional[bytes] = ..., timestamp: _Optional[int] = ..., counter: _Optional[int] = ...) -> None: ...

class IMUParam(_message.Message):
    __slots__ = ("gyroscope_x", "gyroscope_y", "gyroscope_z", "acceleration_x", "acceleration_y", "acceleration_z")
    GYROSCOPE_X_FIELD_NUMBER: _ClassVar[int]
    GYROSCOPE_Y_FIELD_NUMBER: _ClassVar[int]
    GYROSCOPE_Z_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_X_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_Y_FIELD_NUMBER: _ClassVar[int]
    ACCELERATION_Z_FIELD_NUMBER: _ClassVar[int]
    gyroscope_x: float
    gyroscope_y: float
    gyroscope_z: float
    acceleration_x: float
    acceleration_y: float
    acceleration_z: float
    def __init__(self, gyroscope_x: _Optional[float] = ..., gyroscope_y: _Optional[float] = ..., gyroscope_z: _Optional[float] = ..., acceleration_x: _Optional[float] = ..., acceleration_y: _Optional[float] = ..., acceleration_z: _Optional[float] = ...) -> None: ...

class DeviceParam(_message.Message):
    __slots__ = ("timestamp", "imu_param", "temperature", "memory_usage", "cpu_usage", "power", "rssi_dbm", "voltage")
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    IMU_PARAM_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    MEMORY_USAGE_FIELD_NUMBER: _ClassVar[int]
    CPU_USAGE_FIELD_NUMBER: _ClassVar[int]
    POWER_FIELD_NUMBER: _ClassVar[int]
    RSSI_DBM_FIELD_NUMBER: _ClassVar[int]
    VOLTAGE_FIELD_NUMBER: _ClassVar[int]
    timestamp: int
    imu_param: IMUParam
    temperature: float
    memory_usage: float
    cpu_usage: float
    power: int
    rssi_dbm: int
    voltage: float
    def __init__(self, timestamp: _Optional[int] = ..., imu_param: _Optional[_Union[IMUParam, _Mapping]] = ..., temperature: _Optional[float] = ..., memory_usage: _Optional[float] = ..., cpu_usage: _Optional[float] = ..., power: _Optional[int] = ..., rssi_dbm: _Optional[int] = ..., voltage: _Optional[float] = ...) -> None: ...

class ClockSynchronizationParam(_message.Message):
    __slots__ = ("req_tx_ms", "req_rx_ms", "resp_tx_ms")
    REQ_TX_MS_FIELD_NUMBER: _ClassVar[int]
    REQ_RX_MS_FIELD_NUMBER: _ClassVar[int]
    RESP_TX_MS_FIELD_NUMBER: _ClassVar[int]
    req_tx_ms: int
    req_rx_ms: int
    resp_tx_ms: int
    def __init__(self, req_tx_ms: _Optional[int] = ..., req_rx_ms: _Optional[int] = ..., resp_tx_ms: _Optional[int] = ...) -> None: ...
