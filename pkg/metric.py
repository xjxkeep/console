import time
from tensorboardX import SummaryWriter


writer = SummaryWriter(log_dir="logs/metric")

def get_global_step():
    return (int(time.time()*1000))%(24*60*60*1000)


def add_metric(tag,value):
    writer.add_scalar(tag,value,get_global_step())


