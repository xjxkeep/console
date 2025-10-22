



def generate_crc8_table():
    crc8_table = [0] * 256
    for i in range(256):
        crc = i
        for j in range(8):
            if crc & 0x80:
                crc = ((crc << 1) & 0xFF) ^ 0x07
            else:
                crc = (crc << 1) & 0xFF
        crc8_table[i] = crc
    return crc8_table


# 生成全局查找表
CRC8_TABLE = generate_crc8_table()


def calculate_uint16_crc8(data: int) -> int:
    crc = 0
    # 获取低字节和高字节
    low_byte = data & 0xFF
    high_byte = (data >> 8) & 0xFF
    
    # 使用查表法计算CRC8
    crc = CRC8_TABLE[crc ^ low_byte]
    crc = CRC8_TABLE[crc ^ high_byte]
    
    return crc

def calculate_crc8(data:bytes) -> int:
    crc=0
    for byte in data:
        crc = CRC8_TABLE[crc ^ byte]
    return crc


