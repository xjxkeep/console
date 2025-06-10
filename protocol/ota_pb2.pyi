from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class VersionPublishMessage(_message.Message):
    __slots__ = ("version", "release_date", "size", "content_md5", "url", "changelog", "arch")
    class ARCH(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        ALL: _ClassVar[VersionPublishMessage.ARCH]
        ARM32: _ClassVar[VersionPublishMessage.ARCH]
        ARM64: _ClassVar[VersionPublishMessage.ARCH]
        X86_32: _ClassVar[VersionPublishMessage.ARCH]
        X86_64: _ClassVar[VersionPublishMessage.ARCH]
    ALL: VersionPublishMessage.ARCH
    ARM32: VersionPublishMessage.ARCH
    ARM64: VersionPublishMessage.ARCH
    X86_32: VersionPublishMessage.ARCH
    X86_64: VersionPublishMessage.ARCH
    VERSION_FIELD_NUMBER: _ClassVar[int]
    RELEASE_DATE_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_MD5_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    CHANGELOG_FIELD_NUMBER: _ClassVar[int]
    ARCH_FIELD_NUMBER: _ClassVar[int]
    version: str
    release_date: int
    size: int
    content_md5: str
    url: str
    changelog: str
    arch: VersionPublishMessage.ARCH
    def __init__(self, version: _Optional[str] = ..., release_date: _Optional[int] = ..., size: _Optional[int] = ..., content_md5: _Optional[str] = ..., url: _Optional[str] = ..., changelog: _Optional[str] = ..., arch: _Optional[_Union[VersionPublishMessage.ARCH, str]] = ...) -> None: ...
