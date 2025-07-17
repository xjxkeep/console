from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class VideoAttributeMessage(_message.Message):
    __slots__ = ("width", "height", "max_rate", "frame_rate", "video_encode_type")
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    MAX_RATE_FIELD_NUMBER: _ClassVar[int]
    FRAME_RATE_FIELD_NUMBER: _ClassVar[int]
    VIDEO_ENCODE_TYPE_FIELD_NUMBER: _ClassVar[int]
    width: int
    height: int
    max_rate: int
    frame_rate: int
    video_encode_type: str
    def __init__(self, width: _Optional[int] = ..., height: _Optional[int] = ..., max_rate: _Optional[int] = ..., frame_rate: _Optional[int] = ..., video_encode_type: _Optional[str] = ...) -> None: ...
