# UltraMic384K 关键格式标准

## 关键格式参数

### 音频格式要求
```
采样率: 384,000 Hz
格式: S16_LE (16位有符号小端序整数)
声道: 1 (单声道)
缓冲区: 3,840 样本 (10ms)
```

### 为什么是这些参数？

**16位整数格式 (S16_LE)**
- UltraMic384K硬件**严格要求**16位整数
- 浮点格式(float32)会被设备**拒绝**
- 这是通过对比Audacity录音成功而我们的程序失败发现的
- Audacity使用的就是S16_LE格式

**384kHz采样率**
- 设备的**固定**采样率，不支持其他采样率
- 对应192kHz的Nyquist频率，覆盖完整超声波频段

## ALSA设备访问

### 设备路径格式
```
hw:X,Y  (X=声卡编号, Y=设备编号)
例: hw:3,0
```

### 设备识别方法

**通过名称匹配**（推荐）
```python
devices = sd.query_devices()
for i, device in enumerate(devices):
    if "UltraMic384K" in device['name']:
        return i
```

**直接ALSA路径**（备用）
```python
device = "hw:3,0"  # 直接指定ALSA设备路径
```

### 为什么使用ALSA？

**直接硬件访问**
- 绕过PulseAudio等音频服务器
- 减少延迟和格式转换
- 确保获得设备的原生格式支持

**格式控制**
- ALSA允许精确控制音频格式
- 避免自动重采样和格式转换
- 保证384kHz/16bit的严格要求

## 实际配置代码

```python
# 音频线程参数
self.sample_rate = 384000
self.dtype = np.int16        # 关键：必须是16位整数
self.channels = 1
self.blocksize = 3840

# sounddevice流配置
sd.InputStream(
    device=device_index,     # 通过名称查找或使用hw:X,Y
    samplerate=384000,       # 固定采样率
    dtype=np.int16,          # 关键：16位整数
    channels=1,
    blocksize=3840
)
```

## 验证方法

**测试设备格式支持**
```bash
# 使用arecord测试
arecord -D hw:3,0 -f S16_LE -r 384000 -c 1 test.wav
```

**Python验证**
```python
# 检查设备能力
device_info = sd.query_devices(device_index)
print(f"Max sample rate: {device_info['default_samplerate']}")
```

---

*核心发现：Audacity成功 → 我们失败 → 发现格式差异 → 改用S16_LE → 成功*