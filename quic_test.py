import os
import json
from pkg.quic import HighwayQuicClient
import time
def load_setting():
    if os.path.exists("setting.json"):
        with open("setting.json", "r") as f:
            setting = json.load(f)
        return setting
    else:
        setting = {
            "host":"127.0.0.1",
            "port":30042,
            "insecure":True,
            "source_device_id":1,
            "channel_count":10,
            "device_id":1
        }
        return setting
    

setting=load_setting()
client=HighwayQuicClient(setting)
client.start()

while True:
    time.sleep(10)