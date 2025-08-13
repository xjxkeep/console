from pydantic import BaseModel



class HIDBody(BaseModel):
    type: str = ""
    cmd: str = None
    request_id: str = None
    args: dict = {}
    returns: dict = {}

class Device(BaseModel):
    ID :int =None
    name: str = None
    device_id: str = None
    subscribe_id: str = None
    register_ip: str = None
    mac: str = None
    version: str = None
    token: str = None

class Version(BaseModel):
    version: str = None
    url: str = None
    desc: str = None
    force: bool = False
    arch: str = None
    md5: str = None

class VersionResponse(BaseModel):
    code: int
    msg: str
    data: Version

class DeviceResponse(BaseModel):
    code: int
    msg: str
    data: Device
