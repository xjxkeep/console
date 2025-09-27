from prometheus_client import  Counter, Gauge, Histogram
# TODO 缓冲区数据打点

NETWORK_UPLOAD_BYTES = Counter(
    'network_upload_bytes',
    'Total number of bytes uploaded'
)
NETWORK_DOWNLOAD_BYTES = Counter(
    'network_download_bytes',
    'Total number of bytes downloaded'
)

PROTOBUF_FIFO_SIZE = Gauge(
    'protobuf_fifo_size',
    'Size of protobuf fifo',
    ["type"]
)

PROTOBUF_LATENCY = Histogram(
    'protobuf_latency',
    'Latency of protobuf',
    ["type"]
)

FRAME_FIFO_SIZE = Gauge(
    'frame_fifo_size',
    'Size of frame fifo'
)


DECODER_FIFO_SIZE = Gauge(
    'decoder_fifo_size',
    'Size of decoder fifo'
)


DECODE_FRAME_COUNT = Counter(
    'decode_frame_count',
    'Total number of frames'
)

DISPLAY_FRAME_COUNT = Counter(
    'display_frame_count',
    'Total number of frames'
)

VIDEO_PROTOBUF_COUNT = Counter(
    'video_protobuf_count',
    'Total number of protobuf',
    ["slice_id","nalu_type","counter"]
)


