from zfec.easyfec import Encoder, Decoder

print("=" * 70)
print("FEC K+M 冗余编码最简单示例")
print("=" * 70)

# ============ 参数设置 ============
K = 3  # 原始数据块数（必需块数）
M = 2  # 冗余块数
N = K + M  # 总块数 = 5

print(f"\n配置:")
print(f"  K = {K} (原始数据块数，至少需要 K 个块才能恢复)")
print(f"  M = {M} (冗余块数)")
print(f"  N = {N} (总块数)")
print(f"  含义：将数据分成 {K} 块，生成 {N} 个编码块（包含原始数据）")
print(f"        只要收到任意 {K} 个块就能恢复完整数据")
print(f"        最多可以丢失 {M} 个块")

# ============ 创建编码器和解码器 ============
encoder = Encoder(K, N)
decoder = Decoder(K, N)

# ============ 原始数据 ============
original_data = b"Hello, this is a FEC test with K+M redundancy!"
data_len = len(original_data)
print(f"\n原始数据 ({data_len} 字节):")
print(f"  {original_data}")

# ============ 编码 ============
# encode() 接收字节串，返回 N 个编码块的列表
encoded_blocks = encoder.encode(original_data)

# 计算填充长度（padlen）
# 每个块的大小 = ceil(data_len / K)
block_size = (data_len + K - 1) // K  # 向上取整
padlen = block_size * K - data_len  # 填充的字节数

print(f"\n编码结果:")
print(f"  原始数据长度: {data_len} 字节")
print(f"  每个块大小: {block_size} 字节")
print(f"  填充长度 (padlen): {padlen} 字节")
print(f"  生成了 {len(encoded_blocks)} 个编码块")
for i, block in enumerate(encoded_blocks):
    print(f"  块 {i}: 长度={len(block)} 字节, 前20字节={block[:20].hex()}")

# ============ 模拟丢包 ============
print(f"\n模拟丢包场景:")

# 场景1: 丢失2个块（在容忍范围内，M=2）
print(f"\n【场景1】丢失 2 个块（块0 和 块3）- 应该能恢复")
available_ids_1 = [1, 2, 4]  # 收到的块的索引
received_blocks_1 = [encoded_blocks[i] for i in available_ids_1]  # 只包含收到的K个块

print(f"  丢失: 块0, 块3")
print(f"  收到: 块{available_ids_1} (共 {len(available_ids_1)} 个)")

# 解码（第一个参数必须恰好包含 K 个块）
try:
    decoded_data_1 = decoder.decode(received_blocks_1, available_ids_1, padlen)
    print(f"  解码成功: {decoded_data_1}")
    
    if decoded_data_1 == original_data:
        print(f"  ✓ 数据完全恢复！")
    else:
        print(f"  ✗ 数据恢复失败")
except Exception as e:
    print(f"  ✗ 解码失败: {e}")

# 场景2: 丢失3个块（超出容忍范围）
print(f"\n【场景2】丢失 3 个块（块0, 块2, 块3）- 无法恢复")
available_ids_2 = [1, 4]  # 只收到2个块
received_blocks_2 = [encoded_blocks[i] for i in available_ids_2]

print(f"  丢失: 块0, 块2, 块3")
print(f"  收到: 块{available_ids_2} (共 {len(available_ids_2)} 个，少于 K={K})")

try:
    decoded_data_2 = decoder.decode(received_blocks_2, available_ids_2, padlen)
    print(f"  意外成功: {decoded_data_2}")
except Exception as e:
    print(f"  ✓ 预期失败: 收到的块数 ({len(available_ids_2)}) < K ({K})")

# 场景3: 收到任意K个块就能恢复
print(f"\n【场景3】收到最后 {K} 个块（块2, 块3, 块4）- 应该能恢复")
available_ids_3 = [2, 3, 4]
received_blocks_3 = [encoded_blocks[i] for i in available_ids_3]

print(f"  丢失: 块0, 块1")
print(f"  收到: 块{available_ids_3} (共 {len(available_ids_3)} 个)")

try:
    decoded_data_3 = decoder.decode(received_blocks_3, available_ids_3, padlen)
    print(f"  解码成功: {decoded_data_3}")
    
    if decoded_data_3 == original_data:
        print(f"  ✓ 数据完全恢复！（证明任意 K 个块都可以）")
    else:
        print(f"  ✗ 数据恢复失败")
except Exception as e:
    print(f"  ✗ 解码失败: {e}")



# ============ 部分数据恢复测试 ============
print(f"\n【场景4】部分数据恢复测试（收到块数 < K）")

def try_partial_recovery(available_blocks, available_ids, original_data, block_size):
    """
    尝试部分数据恢复
    当收到的块数 < K 时，尝试恢复尽可能多的数据
    """
    print(f"\n  尝试部分恢复：")
    print(f"  收到 {len(available_blocks)} 个块，需要 {K} 个块才能完全恢复")
    
    # 方法1：直接拼接收到的块（简单但可能不完整）
    print(f"\n  方法1：直接拼接收到的块")
    try:
        # 计算每个块应该包含的原始数据范围
        recovered_data = b""
        for i, block_id in enumerate(available_ids):
            if block_id < K:  # 只处理原始数据块（前K个）
                start_pos = block_id * block_size
                end_pos = min((block_id + 1) * block_size, len(original_data))
                recovered_data += available_blocks[i][:end_pos - start_pos]
                print(f"    块{block_id}: 恢复位置 {start_pos}-{end_pos}")
        
        print(f"    恢复数据长度: {len(recovered_data)} / {len(original_data)} 字节")
        print(f"    恢复率: {len(recovered_data)/len(original_data)*100:.1f}%")
        
        # 显示恢复的数据
        if len(recovered_data) > 0:
            print(f"    恢复的数据: {recovered_data}")
            # 计算与原始数据的匹配度
            match_count = 0
            for i in range(min(len(recovered_data), len(original_data))):
                if recovered_data[i] == original_data[i]:
                    match_count += 1
            print(f"    数据匹配度: {match_count}/{len(recovered_data)} = {match_count/len(recovered_data)*100:.1f}%")
        
        return recovered_data
    except Exception as e:
        print(f"    部分恢复失败: {e}")
        return b""

# 测试场景：只收到2个块（少于K=3）
print(f"\n【场景4a】只收到2个块（块1, 块4）- 尝试部分恢复")
available_ids_4a = [1, 4]  # 只收到2个块
received_blocks_4a = [encoded_blocks[i] for i in available_ids_4a]

print(f"  丢失: 块0, 块2, 块3")
print(f"  收到: 块{available_ids_4a} (共 {len(available_ids_4a)} 个，少于 K={K})")

# 尝试部分恢复
recovered_data_4a = try_partial_recovery(received_blocks_4a, available_ids_4a, original_data, block_size)

# 测试场景：只收到1个块
print(f"\n【场景4b】只收到1个块（块2）- 尝试部分恢复")
available_ids_4b = [2]  # 只收到1个块
received_blocks_4b = [encoded_blocks[i] for i in available_ids_4b]

print(f"  丢失: 块0, 块1, 块3, 块4")
print(f"  收到: 块{available_ids_4b} (共 {len(available_ids_4b)} 个，远少于 K={K})")

# 尝试部分恢复
recovered_data_4b = try_partial_recovery(received_blocks_4b, available_ids_4b, original_data, block_size)

# 测试场景：收到冗余块（块3, 块4）
print(f"\n【场景4c】只收到冗余块（块3, 块4）- 无法直接恢复")
available_ids_4c = [3, 4]  # 只收到冗余块
received_blocks_4c = [encoded_blocks[i] for i in available_ids_4c]

print(f"  丢失: 块0, 块1, 块2")
print(f"  收到: 块{available_ids_4c} (共 {len(available_ids_4c)} 个，都是冗余块)")

# 尝试部分恢复
recovered_data_4c = try_partial_recovery(received_blocks_4c, available_ids_4c, original_data, block_size)
# ============ 总结 ============
print("\n" + "=" * 70)
print("总结")
print("=" * 70)
print(f"""
FEC (K, N, M) 参数含义：
  - K = {K}: 原始数据块数，最少需要 K 个块才能恢复数据
  - M = {M}: 冗余块数，最多可以丢失 M 个块
  - N = {N}: 总块数 = K + M

工作原理：
  1. 编码：将数据编码成 N 个块
  2. 传输：通过网络发送这 N 个块（可能丢失部分）
  3. 解码：只要收到任意 K 个块，就能恢复原始数据
  
解码调用格式：
  decoder.decode(received_blocks, available_ids, padlen)
  
  参数说明：
  - received_blocks: 收到的 K 个块的列表（不是 N 个！）
    示例：[encoded_blocks[1], encoded_blocks[2], encoded_blocks[4]]
  - available_ids: 这 K 个块在原始 N 个块中的索引
    示例：[1, 2, 4]
  - padlen: 填充长度 = block_size × K - data_len

块大小计算：
  - 块大小 = ⌈数据长度 / K⌉ = ⌈{data_len} / {K}⌉ = {block_size} 字节
  - 填充长度 (padlen) = 块大小 × K - 数据长度 = {padlen} 字节

开销：
  - 冗余开销 = M/K = {M}/{K} = {M/K*100:.1f}%
  - 实际传输 = {N} 个块 × {block_size} 字节 = {N * block_size} 字节
  - 原始数据 = {data_len} 字节

部分数据恢复策略：
  当收到块数 < K 时：
  1. 直接拼接：将收到的原始数据块（块0到块K-1）直接拼接
  2. 恢复率：收到的原始块数 / K
  3. 限制：只能恢复原始数据块，冗余块无法单独使用
  
  示例：
  - 收到块1, 块4：只能恢复块1对应的数据段（33%）
  - 收到块2：只能恢复块2对应的数据段（33%）
  - 收到块3, 块4：无法恢复（都是冗余块）

应用场景：
  - 视频直播：允许部分包丢失，但仍能播放
  - 文件传输：减少重传次数
  - 分布式存储：节点故障时仍可恢复数据
  - 卫星通信：高丢包率环境
  - 实时通信：即使部分数据丢失，也能获得部分信息
""")
print("=" * 70)