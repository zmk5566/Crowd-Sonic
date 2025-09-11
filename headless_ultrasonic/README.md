# Headless超声波可视化器

基于FastAPI + SSE的实时FFT数据流服务，支持前后端分离和远程监控。

## 🚀 快速开始

### 1. 环境准备

```bash
# 创建conda环境
conda create -n headless-ultrasonic python=3.11 -y
conda activate headless-ultrasonic

# 安装依赖
pip install fastapi uvicorn pydantic numpy scipy sounddevice
```

### 2. 启动服务器

**方法一：直接运行**
```bash
cd headless_ultrasonic
python -c "
import uvicorn
from main import app
print('🎵 启动Headless超声波可视化器...')
print('服务器地址: http://localhost:8380')
uvicorn.run(app, host='0.0.0.0', port=8380, log_level='info')
"
```

**方法二：使用运行脚本（如果导入问题已修复）**
```bash
cd headless_ultrasonic  
python run.py
```

### 3. 访问服务

- **Web界面**: http://localhost:8380 - 🆕 **集成实时频谱可视化！**
- **API文档**: http://localhost:8380/docs  
- **SSE数据流**: http://localhost:8380/api/stream

### 🎨 Web界面功能

新的Web界面包含完整的可视化系统：

- **实时频谱图表** - 使用Chart.js显示0-100kHz频谱
- **实时数据指标** - FPS、峰值频率、声压级、数据速率等
- **系统控制面板** - 启停、FPS调节、连接状态
- **事件日志** - 实时显示数据接收和系统状态
- **数据导出** - 一键导出分析数据

## 📡 API端点

### 控制API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 获取系统状态 |
| `/api/start` | POST | 启动音频采集 |
| `/api/stop` | POST | 停止音频采集 |
| `/api/config/stream` | GET/POST | 获取/设置流配置 |
| `/api/config/fps` | POST | 快速设置FPS |
| `/api/devices` | GET | 列出音频设备 |

### 数据流API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/stream` | GET | SSE实时FFT数据流 |
| `/api/stream/test` | GET | SSE连接测试 |
| `/api/stream/stats` | GET | 流传输统计 |

## 🔧 使用示例

### 1. 控制系统

```bash
# 启动音频采集
curl -X POST http://localhost:8380/api/start

# 查看状态
curl http://localhost:8380/api/status

# 设置FPS
curl -X POST http://localhost:8380/api/config/fps \
  -H "Content-Type: application/json" \
  -d '60'

# 停止采集
curl -X POST http://localhost:8380/api/stop
```

### 2. 前端SSE连接

```javascript
// 连接SSE数据流
const eventSource = new EventSource('http://localhost:8380/api/stream');

eventSource.onmessage = function(event) {
    const fftFrame = JSON.parse(event.data);
    
    console.log('时间戳:', fftFrame.timestamp);
    console.log('序列号:', fftFrame.sequence_id);
    console.log('采样率:', fftFrame.sample_rate);
    console.log('峰值频率:', fftFrame.peak_frequency_hz);
    console.log('声压级:', fftFrame.spl_db);
    
    // 解压缩FFT数据
    const compressedData = fftFrame.data_compressed;
    // 需要使用pako或其他库解压缩gzip数据
};

eventSource.onerror = function(event) {
    console.error('SSE连接错误:', event);
};
```

### 3. 简单的Web监控页面

```html
<!DOCTYPE html>
<html>
<head>
    <title>超声波监控</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pako/2.0.4/pako.min.js"></script>
</head>
<body>
    <h1>实时超声波数据</h1>
    <div id="status">未连接</div>
    <div id="data"></div>
    
    <script>
        const eventSource = new EventSource('http://localhost:8380/api/stream');
        
        eventSource.onopen = function() {
            document.getElementById('status').textContent = '已连接';
        };
        
        eventSource.onmessage = function(event) {
            const frame = JSON.parse(event.data);
            
            // 显示基本信息
            document.getElementById('data').innerHTML = `
                <p>时间戳: ${new Date(frame.timestamp).toLocaleTimeString()}</p>
                <p>序列号: ${frame.sequence_id}</p>
                <p>FPS: ${frame.fps.toFixed(1)}</p>
                <p>峰值频率: ${(frame.peak_frequency_hz/1000).toFixed(1)} kHz</p>
                <p>峰值幅度: ${frame.peak_magnitude_db.toFixed(1)} dB</p>
                <p>声压级: ${frame.spl_db.toFixed(1)} dB SPL</p>
                <p>数据大小: ${frame.data_size_bytes} bytes</p>
                <p>压缩比: ${(frame.data_size_bytes/frame.original_size_bytes*100).toFixed(1)}%</p>
            `;
        };
        
        eventSource.onerror = function() {
            document.getElementById('status').textContent = '连接错误';
        };
    </script>
</body>
</html>
```

## 🐛 问题排查

### 常见问题

1. **ImportError: attempted relative import with no known parent package**
   - 问题：Python模块导入路径错误
   - 解决：使用绝对导入或直接运行main.py

2. **音频设备未找到**
   - 检查可用设备：`curl http://localhost:8380/api/devices`
   - 配置环境变量：`export DEVICE_NAMES="YourDevice"`

3. **SSE连接超时**
   - 检查防火墙设置
   - 确认服务器正常启动：`curl http://localhost:8380/api/status`

4. **数据压缩/解压错误**
   - 前端需要pako.js或类似库解压gzip数据
   - 检查Base64解码是否正确

### 调试方法

```bash
# 1. 检查服务器状态
curl -v http://localhost:8380/api/status

# 2. 测试SSE连接（超时退出）
timeout 10 curl -N http://localhost:8380/api/stream/test

# 3. 检查端口占用
lsof -i :8380

# 4. 查看详细日志
export LOG_LEVEL=DEBUG
python main.py

# 5. 测试压缩性能
curl -X POST http://localhost:8380/api/test/compression
```

## 🔧 配置参数

### 环境变量

```bash
# 服务器配置
export HOST="0.0.0.0"           # 监听地址
export PORT="8380"              # 监听端口
export DEBUG="true"             # 调试模式

# 音频配置  
export SAMPLE_RATE="384000"     # 采样率
export FFT_SIZE="8192"          # FFT大小
export DEVICE_NAMES="UltraMic384K,UltraMic"  # 设备名称

# 流配置
export TARGET_FPS="30"          # 目标帧率
export COMPRESSION_LEVEL="6"    # 压缩级别 (1-9)
export MAGNITUDE_THRESHOLD="-80.0"  # 幅度阈值
```

### 配置文件

修改 `config.py` 中的默认值：

```python
class Config:
    HOST = "localhost"          # 只监听本地
    PORT = 8380                 # 自定义端口
    
    @classmethod
    def get_stream_config(cls):
        return StreamConfig(
            target_fps=60,          # 高帧率
            compression_level=9,    # 最高压缩
            enable_adaptive_fps=False  # 固定帧率
        )
```

## 📊 性能指标

### 数据量估算

| 配置 | 原始数据/帧 | 压缩后/帧 | 30FPS总量 | 60FPS总量 |
|------|------------|-----------|-----------|-----------|
| 默认 | ~16KB | ~5KB | 1.2MB/s | 2.4MB/s |
| 高压缩 | ~16KB | ~3KB | 0.7MB/s | 1.4MB/s |

### 网络要求

- **局域网**: ✅ 千兆网络完全支持
- **WiFi**: ✅ WiFi 5及以上推荐  
- **4G/LTE**: ⚠️ 需降低FPS到10-15
- **远程VPN**: ⚠️ 建议使用低FPS + 高压缩

## 🚀 部署建议

### 生产环境

```bash
# 使用gunicorn部署
pip install gunicorn
gunicorn main:app -w 1 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8380 --timeout 300

# 或使用systemd服务
sudo systemctl enable headless-ultrasonic
sudo systemctl start headless-ultrasonic
```

### Docker部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8380

CMD ["python", "-c", "import uvicorn; from main import app; uvicorn.run(app, host='0.0.0.0', port=8380)"]
```

## 🤝 贡献指南

1. Fork本仓库
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交修改：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 提交Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件