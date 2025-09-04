# Simple UAC Visualizer

一个跨平台的实时超声波数据可视化工具，专为支持384kHz采样率的UAC（USB Audio Class）设备设计。

## 功能特性

- 🎵 **实时音频捕获**: 支持最高384kHz采样率的UAC设备
- 📊 **频谱分析**: 实时FFT分析和频谱显示
- 🔊 **超声波可视化**: 专门优化的超声波频段（20kHz+）显示
- 🖥️ **跨平台支持**: Windows、Linux、macOS
- 📈 **多视图显示**: 频谱图、分频段图和瀑布图
- ⚡ **低延迟**: 优化的实时处理管道
- 🆚 **对比分析**: 超声波与普通麦克风的同坐标系对比功能

## 安装依赖

### 1. Python环境
确保你的系统安装了Python 3.8+

### 2. 安装依赖包
```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\\Scripts\\activate   # Windows

# 安装主要依赖
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install -r requirements-dev.txt
```

### 3. 系统特定设置

**Linux**:
```bash
# 安装PortAudio开发包
sudo apt-get install portaudio19-dev python3-pyaudio
```

**Windows**:
- 建议使用ASIO驱动以获得最低延迟
- 确保UAC设备驱动正确安装

**macOS**:
```bash
# 使用Homebrew安装PortAudio
brew install portaudio
```

## 使用方法

### 1. 超声波可视化器（UltraMic384K）
高性能384kHz超声波设备可视化：
```bash
python fast_ultrasonic.py
```

### 2. 默认麦克风可视化器（对比分析）
使用系统默认麦克风，坐标系与超声波版本完全一致：
```bash
python fast_microphone.py
```

**对比分析功能**：
- 两个可视化器使用完全相同的坐标系（0-200kHz）
- 麦克风数据显示在0-22kHz范围，22kHz以上为平坦基线
- 可同时运行进行对比分析，观察超声波与普通音频的差异
- 相同的界面布局和颜色映射，便于直接比较

### 3. 启动GUI界面（传统版本）
```bash
python main.py
```

### 4. 列出音频设备
```bash
python main.py --list-devices
```

### 5. 测试设备连接
```bash
# 测试设备ID为1的设备
python main.py --test-device 1
```

### 6. 指定设备启动
```bash
python main.py --device 1
```

## GUI界面使用

### 控制面板
- **设备选择**: 从下拉菜单选择你的UAC设备
- **频率范围**: 调整显示的频率范围（支持0-200kHz）
- **开始/停止**: 控制音频流的录制

### 可视化区域
- **上方**: 实时频谱图，显示当前时刻的频率分布
- **下方**: 声谱图，显示频率随时间的变化

### 状态信息
- **峰值频率**: 当前最强信号的频率
- **峰值幅度**: 最强信号的幅度值
- **频谱质心**: 频谱能量的中心频率
- **超声波占比**: 超声波频段的能量比例

## 配置文件

程序使用`config/default.yaml`配置文件，你可以修改以下参数：

```yaml
audio:
  sample_rate: 384000    # 采样率
  channels: 1            # 通道数
  buffer_size: 1024      # 缓冲区大小

processing:
  fft_size: 2048         # FFT窗口大小
  overlap: 0.5           # 窗口重叠率
  window_type: "hann"    # 窗函数类型

visualization:
  update_rate: 30        # 显示刷新率
  colormap: "viridis"    # 颜色映射
```

## 超声波应用场景

这个工具特别适合以下应用：

- 🦇 **动物声学研究**: 蝙蝠回声定位、海豚通信
- 🏭 **工业检测**: 超声波无损检测、泄漏检测  
- 🔬 **科学研究**: 材料特性分析、流体动力学
- 📡 **声学测量**: 环境噪声监测、设备性能测试

## 故障排除

### 设备无法识别
1. 确认UAC设备正确连接并被系统识别
2. 检查设备驱动是否正确安装
3. 尝试在其他音频应用中测试设备

### 音频流启动失败
1. 检查采样率是否受设备支持
2. 尝试降低缓冲区大小
3. 确认设备未被其他应用占用

### 性能问题
1. 降低FFT窗口大小
2. 减少显示刷新率
3. 关闭不必要的其他程序

## 开发和贡献

### 运行测试
```bash
pytest tests/
```

### 代码格式化
```bash
black src/ tests/
isort src/ tests/
```

### 代码检查
```bash
flake8 src/ tests/
pylint src/
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 联系方式

如有问题或建议，请在GitHub上提交Issue。