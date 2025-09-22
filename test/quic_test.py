import os
import json
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pkg.quic import HighwayQuicClient
from pkg.model import Setting
import time

    

setting=Setting(host="localhost")
client=HighwayQuicClient(setting)
client.start()
client.send_video_test()

time.sleep(10)

client.close()


print("exit")