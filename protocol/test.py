from highway_pb2 import Device, Register, Control, Report, Video

device = Device(id=1)
register = Register(device=device)
control = Control(channels=[1, 2, 3])
report = Report(battery=100)
video = Video(raw=b"1234567890")

print(register)
print(control)
print(report)
print(video)

print(register.SerializeToString())
print(control.SerializeToString())
print(report.SerializeToString())
print(video.SerializeToString())

