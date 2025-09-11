#!/usr/bin/env python3
"""
Headless超声波可视化器主应用
基于FastAPI + SSE，提供实时FFT数据流
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from config import Config
from models import FFTFrame
from core import AudioCapture, FFTProcessor, DataStreamer
from api import stream_router, control_router
from api.stream import set_data_streamer
from api.control import set_components

# 配置日志
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format=Config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# 全局组件
audio_capture = None
fft_processor = None  
data_streamer = None
stream_config = None
audio_config = None
processing_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化组件
    await startup_event()
    
    yield
    
    # 关闭时清理资源
    await shutdown_event()

async def startup_event():
    """启动事件：初始化所有组件"""
    global audio_capture, fft_processor, data_streamer, stream_config, audio_config, processing_task
    
    logger.info("正在启动Headless超声波可视化器...")
    
    try:
        # 加载配置
        stream_config = Config.get_stream_config()
        audio_config = Config.get_audio_config()
        
        logger.info(f"流配置: FPS={stream_config.target_fps}, 压缩级别={stream_config.compression_level}")
        logger.info(f"音频配置: 采样率={audio_config.sample_rate}Hz, FFT大小={audio_config.fft_size}")
        
        # 初始化组件
        fft_processor = FFTProcessor(
            sample_rate=audio_config.sample_rate,
            fft_size=audio_config.fft_size,
            overlap=audio_config.overlap,
            window_type=audio_config.window_type,
            compression_level=stream_config.compression_level
        )
        
        data_streamer = DataStreamer(stream_config)
        
        audio_capture = AudioCapture(
            device_names=audio_config.device_names,
            fallback_device_id=audio_config.fallback_device_id,
            sample_rate=audio_config.sample_rate,
            channels=audio_config.channels,
            blocksize=audio_config.blocksize
        )
        
        # 设置音频回调
        audio_capture.add_callback(audio_callback)
        
        # 设置API组件引用
        set_data_streamer(data_streamer)
        set_components(audio_capture, fft_processor, data_streamer, stream_config, audio_config)
        
        # 启动数据处理任务
        processing_task = asyncio.create_task(data_processing_loop())
        
        logger.info("所有组件初始化完成")
        logger.info(f"服务器将监听: http://{Config.HOST}:{Config.PORT}")
        logger.info("API端点:")
        logger.info("  GET  /api/stream       - SSE数据流")
        logger.info("  GET  /api/status       - 系统状态")  
        logger.info("  POST /api/start        - 启动采集")
        logger.info("  POST /api/stop         - 停止采集")
        logger.info("  GET  /api/stream/test  - SSE连接测试")
        
    except Exception as e:
        logger.error(f"启动失败: {e}")
        raise

async def shutdown_event():
    """关闭事件：清理资源"""
    global audio_capture, processing_task
    
    logger.info("正在关闭应用...")
    
    try:
        # 停止音频采集
        if audio_capture:
            audio_capture.stop()
        
        # 取消处理任务
        if processing_task and not processing_task.done():
            processing_task.cancel()
            try:
                await processing_task
            except asyncio.CancelledError:
                pass
                
        logger.info("应用已清理完成")
        
    except Exception as e:
        logger.error(f"关闭时出错: {e}")

def audio_callback(audio_data, timestamp):
    """音频数据回调"""
    if fft_processor:
        logger.debug(f"音频回调: 数据长度={len(audio_data)}, 时间戳={timestamp}")
        fft_processor.add_audio_data(audio_data)

async def data_processing_loop():
    """主数据处理循环"""
    logger.info("数据处理循环已启动")
    sequence_id = 0
    
    try:
        loop_count = 0
        while True:
            loop_count += 1
            # 每1000次循环输出一次调试信息
            if loop_count % 1000 == 0:
                buffer_stats = fft_processor.get_stats()
                logger.debug(f"处理循环 #{loop_count}: 缓冲区大小={buffer_stats['buffer_size']}, 可处理={buffer_stats['buffer_ready']}")
            
            # 检查是否有足够数据处理FFT
            if not fft_processor.can_process():
                await asyncio.sleep(0.001)  # 1ms等待
                continue
            
            logger.debug(f"开始FFT处理 #{sequence_id + 1}")
            # 处理FFT
            result = fft_processor.process_fft()
            if result is None:
                logger.debug("FFT处理返回None")
                continue
            
            logger.debug(f"FFT处理完成，数据长度={len(result[0])}")
                
            magnitude_db, metadata = result
            
            # 检查是否应该发送帧
            current_time = time.time()
            should_send_time = data_streamer.should_send_frame(current_time)
            logger.debug(f"时间检查: 应该发送={should_send_time}")
            if not should_send_time:
                continue
                
            # 智能跳帧检查 - 临时禁用以测试数据流
            should_send_smart = True
            if False:  # 临时禁用智能跳帧
                should_send_smart = fft_processor.should_send_frame(
                    magnitude_db, 
                    stream_config.similarity_threshold,
                    stream_config.magnitude_threshold_db
                )
                logger.debug(f"智能跳帧检查: 应该发送={should_send_smart}, 阈值={stream_config.magnitude_threshold_db}dB")
            
            if not should_send_smart:
                continue
            
            # 压缩数据
            compressed_data, compressed_size, original_size = fft_processor.compress_fft_data(magnitude_db)
            if not compressed_data:
                continue
            
            # 创建FFT帧
            sequence_id += 1
            fft_frame = FFTFrame(
                timestamp=current_time * 1000,  # 毫秒时间戳
                sequence_id=sequence_id,
                sample_rate=audio_config.sample_rate,
                fft_size=audio_config.fft_size,
                data_compressed=compressed_data,
                compression_method="gzip",
                data_size_bytes=compressed_size,
                original_size_bytes=original_size,
                peak_frequency_hz=metadata["peak_frequency_hz"],
                peak_magnitude_db=metadata["peak_magnitude_db"],
                spl_db=metadata["spl_db"],
                fps=0.0  # 将在data_streamer中更新
            )
            
            # 广播到所有客户端
            logger.debug(f"准备广播帧 #{sequence_id} 到客户端")
            await data_streamer.broadcast_frame(fft_frame)
            logger.debug(f"广播完成帧 #{sequence_id}")
            
            # 小延迟避免CPU过载
            await asyncio.sleep(0.001)
            
    except asyncio.CancelledError:
        logger.info("数据处理循环已停止")
    except Exception as e:
        logger.error(f"数据处理循环出错: {e}")

# 创建FastAPI应用
app = FastAPI(
    title="Headless超声波可视化器",
    description="基于FastAPI + SSE的实时FFT数据流服务",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(stream_router)
app.include_router(control_router)

# 根路径
@app.get("/", response_class=HTMLResponse)
async def root():
    """主页面 - 集成实时频谱可视化"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Headless超声波可视化器</title>
        <meta charset="utf-8">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/pako/2.0.4/pako.min.js"></script>
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                margin: 0; padding: 20px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
            }
            .container { 
                max-width: 1400px; margin: 0 auto; 
                background: rgba(255,255,255,0.95); 
                border-radius: 15px; padding: 30px; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }
            .header {
                text-align: center; margin-bottom: 30px;
                background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                background-clip: text; color: transparent;
            }
            .controls-panel {
                display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px;
            }
            .status-card, .control-card {
                background: #f8f9fa; padding: 20px; border-radius: 10px;
                border-left: 5px solid #007cba; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .visualization-panel {
                display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 30px;
            }
            .spectrum-container {
                background: #f8f9fa; padding: 20px; border-radius: 10px;
                border-left: 5px solid #28a745; min-height: 400px;
            }
            .info-panel {
                background: #f8f9fa; padding: 20px; border-radius: 10px;
                border-left: 5px solid #ffc107;
            }
            button {
                background: linear-gradient(45deg, #007cba, #0056b3);
                color: white; border: none; padding: 12px 20px; margin: 5px;
                border-radius: 6px; cursor: pointer; font-weight: 500;
                transition: all 0.3s ease;
            }
            button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,123,186,0.3); }
            button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
            
            .metric-grid {
                display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;
            }
            .metric-item {
                text-align: center; padding: 10px; background: white; border-radius: 8px;
            }
            .metric-value { font-size: 1.5em; font-weight: bold; color: #007cba; }
            .metric-label { font-size: 0.9em; color: #666; margin-top: 5px; }
            
            .connection-status {
                display: inline-block; padding: 5px 10px; border-radius: 15px;
                font-size: 0.9em; font-weight: bold;
            }
            .connected { background: #d4edda; color: #155724; }
            .disconnected { background: #f8d7da; color: #721c24; }
            .connecting { background: #fff3cd; color: #856404; }
            
            #spectrumCanvas { 
                width: 100%; height: 350px; 
                border: 1px solid #ddd; border-radius: 8px;
                background: linear-gradient(to bottom, #1a1a2e, #16213e);
                cursor: crosshair;
            }
            
            .log-container {
                background: #2d3748; color: #e2e8f0; padding: 20px; border-radius: 10px;
                height: 200px; overflow-y: auto; font-family: 'Monaco', 'Consolas', monospace;
                font-size: 12px; margin-top: 20px;
            }
            
            .fps-selector {
                display: flex; gap: 10px; align-items: center; margin: 10px 0;
            }
            .fps-selector input[type="range"] {
                flex: 1; height: 6px; border-radius: 3px; background: #ddd;
                outline: none; -webkit-appearance: none;
            }
            
            @media (max-width: 768px) {
                .controls-panel, .visualization-panel { grid-template-columns: 1fr; }
                .container { padding: 15px; margin: 10px; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎵 Headless超声波可视化器</h1>
                <p>实时FFT频谱分析 | 基于FastAPI + SSE</p>
            </div>
            
            <div class="controls-panel">
                <div class="status-card">
                    <h3>🔊 系统状态</h3>
                    <div id="status">正在加载...</div>
                    <div style="margin-top: 15px;">
                        <button onclick="startSystem()" id="startBtn">启动系统</button>
                        <button onclick="stopSystem()" id="stopBtn">停止系统</button>
                        <button onclick="loadStatus()">刷新状态</button>
                    </div>
                </div>
                
                <div class="control-card">
                    <h3>⚙️ 控制面板</h3>
                    <div class="fps-selector">
                        <label>目标FPS:</label>
                        <input type="range" id="fpsSlider" min="5" max="60" value="30" oninput="updateFPS(this.value)">
                        <span id="fpsValue">30</span>
                    </div>
                    <button onclick="toggleVisualization()" id="vizBtn">开始可视化</button>
                    <button onclick="exportData()">导出数据</button>
                    <div style="margin-top: 10px;">
                        <span>连接状态: </span>
                        <span id="connectionStatus" class="connection-status disconnected">未连接</span>
                    </div>
                </div>
            </div>
            
            <div class="visualization-panel">
                <div class="spectrum-container">
                    <h3>📊 实时频谱分析</h3>
                    <canvas id="spectrumCanvas" width="800" height="350"></canvas>
                    <div style="margin-top: 10px; font-size: 12px; color: #666;">
                        <span>0 Hz</span>
                        <span style="float: right;">100 kHz</span>
                    </div>
                </div>
                
                <div class="info-panel">
                    <h3>📈 实时数据</h3>
                    <div class="metric-grid" id="metricsGrid">
                        <div class="metric-item">
                            <div class="metric-value" id="currentFPS">--</div>
                            <div class="metric-label">当前FPS</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-value" id="peakFreq">--</div>
                            <div class="metric-label">峰值频率 (kHz)</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-value" id="peakMag">--</div>
                            <div class="metric-label">峰值幅度 (dB)</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-value" id="splLevel">--</div>
                            <div class="metric-label">声压级 (dB)</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-value" id="dataRate">--</div>
                            <div class="metric-label">数据速率 (KB/s)</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-value" id="compressionRatio">--</div>
                            <div class="metric-label">压缩比 (%)</div>
                        </div>
                    </div>
                    
                    <h4>📋 最近事件</h4>
                    <div id="eventLog" style="height: 120px; overflow-y: auto; background: white; padding: 10px; border-radius: 5px; font-size: 11px;">
                        <div style="color: #666;">等待数据流连接...</div>
                    </div>
                </div>
            </div>
            
            <div class="log-container" id="systemLog">
                <div style="color: #4fd1c7;">[系统] 超声波可视化器已加载，等待用户操作...</div>
            </div>
        </div>
        
        <script>
            // 全局变量
            let eventSource = null;
            let canvas = null;
            let ctx = null;
            let isVisualizationActive = false;
            let lastDataTime = 0;
            let frameCount = 0;
            let totalBytesReceived = 0;
            
            // 频谱显示参数
            const CANVAS_WIDTH = 800;
            const CANVAS_HEIGHT = 350;
            const PADDING = 40;
            const PLOT_WIDTH = CANVAS_WIDTH - 2 * PADDING;
            const PLOT_HEIGHT = CANVAS_HEIGHT - 2 * PADDING;
            const MAX_FREQ_KHZ = 100;
            const MIN_DB = -100;
            const MAX_DB = 0;
            
            // 初始化Canvas
            function initSpectrumCanvas() {
                canvas = document.getElementById('spectrumCanvas');
                ctx = canvas.getContext('2d');
                
                // 设置高DPI支持
                const dpr = window.devicePixelRatio || 1;
                canvas.width = CANVAS_WIDTH * dpr;
                canvas.height = CANVAS_HEIGHT * dpr;
                ctx.scale(dpr, dpr);
                
                // 绘制背景网格
                drawBackground();
            }
            
            // 绘制背景网格和标签
            function drawBackground() {
                // 清空画布
                ctx.fillStyle = '#1a1a2e';
                ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
                
                // 绘制网格
                ctx.strokeStyle = 'rgba(255,255,255,0.1)';
                ctx.lineWidth = 1;
                
                // 垂直网格线 (频率)
                for (let i = 0; i <= 10; i++) {
                    const x = PADDING + (i / 10) * PLOT_WIDTH;
                    ctx.beginPath();
                    ctx.moveTo(x, PADDING);
                    ctx.lineTo(x, PADDING + PLOT_HEIGHT);
                    ctx.stroke();
                }
                
                // 水平网格线 (幅度)
                for (let i = 0; i <= 10; i++) {
                    const y = PADDING + (i / 10) * PLOT_HEIGHT;
                    ctx.beginPath();
                    ctx.moveTo(PADDING, y);
                    ctx.lineTo(PADDING + PLOT_WIDTH, y);
                    ctx.stroke();
                }
                
                // 绘制坐标轴标签
                ctx.fillStyle = 'rgba(255,255,255,0.7)';
                ctx.font = '12px Arial';
                ctx.textAlign = 'center';
                
                // X轴标签 (频率)
                for (let i = 0; i <= 10; i++) {
                    const x = PADDING + (i / 10) * PLOT_WIDTH;
                    const freq = (i / 10) * MAX_FREQ_KHZ;
                    ctx.fillText(freq.toFixed(0) + 'k', x, CANVAS_HEIGHT - 10);
                }
                
                // Y轴标签 (幅度)
                ctx.textAlign = 'right';
                for (let i = 0; i <= 10; i++) {
                    const y = PADDING + (i / 10) * PLOT_HEIGHT;
                    const db = MAX_DB - (i / 10) * (MAX_DB - MIN_DB);
                    ctx.fillText(db.toFixed(0) + 'dB', PADDING - 10, y + 4);
                }
                
                // 坐标轴标题
                ctx.textAlign = 'center';
                ctx.fillText('频率 (kHz)', CANVAS_WIDTH / 2, CANVAS_HEIGHT - 5);
                
                ctx.save();
                ctx.translate(15, CANVAS_HEIGHT / 2);
                ctx.rotate(-Math.PI / 2);
                ctx.fillText('幅度 (dB)', 0, 0);
                ctx.restore();
            }
            
            // 添加系统日志
            function addSystemLog(message, type = 'info') {
                const timestamp = new Date().toLocaleTimeString();
                const colors = {
                    info: '#4fd1c7',
                    success: '#68d391',
                    error: '#fc8181',
                    warning: '#f6ad55'
                };
                const log = document.getElementById('systemLog');
                log.innerHTML += `<div style="color: ${colors[type] || colors.info}">[${timestamp}] ${message}</div>`;
                log.scrollTop = log.scrollHeight;
            }
            
            // 添加事件日志
            function addEventLog(message) {
                const eventLog = document.getElementById('eventLog');
                const timestamp = new Date().toLocaleTimeString();
                eventLog.innerHTML += `<div>[${timestamp}] ${message}</div>`;
                eventLog.scrollTop = eventLog.scrollHeight;
            }
            
            // 更新连接状态
            function updateConnectionStatus(status) {
                const statusEl = document.getElementById('connectionStatus');
                statusEl.className = 'connection-status ' + status;
                statusEl.textContent = {
                    'connected': '已连接',
                    'connecting': '连接中...',
                    'disconnected': '未连接'
                }[status];
            }
            
            // 解压缩FFT数据
            function decompressFFTData(compressedData) {
                try {
                    console.log('🗜️ 解压缩输入:', {
                        compressedLength: compressedData.length,
                        firstChars: compressedData.substring(0, 20),
                        hasPako: typeof pako !== 'undefined'
                    });
                    
                    const binaryString = atob(compressedData);
                    console.log('📝 Base64解码完成, 长度:', binaryString.length);
                    
                    const bytes = new Uint8Array(binaryString.length);
                    for (let i = 0; i < binaryString.length; i++) {
                        bytes[i] = binaryString.charCodeAt(i);
                    }
                    console.log('📦 字节数组创建完成, 长度:', bytes.length);
                    
                    const decompressed = pako.inflate(bytes);
                    console.log('🔓 Gzip解压完成, 长度:', decompressed.length);
                    
                    const float32Array = new Float32Array(decompressed.buffer);
                    console.log('🔢 Float32数组创建完成, 长度:', float32Array.length);
                    
                    return float32Array;
                } catch (e) {
                    console.error('❌ 解压缩失败:', e);
                    return null;
                }
            }
            
            // 开始/停止可视化
            function toggleVisualization() {
                if (!isVisualizationActive) {
                    startVisualization();
                } else {
                    stopVisualization();
                }
            }
            
            // 启动可视化
            function startVisualization() {
                if (eventSource) {
                    stopVisualization();
                }
                
                addSystemLog('正在连接FFT数据流...', 'info');
                updateConnectionStatus('connecting');
                
                eventSource = new EventSource('/api/stream');
                
                eventSource.onopen = function() {
                    addSystemLog('数据流连接成功', 'success');
                    updateConnectionStatus('connected');
                    isVisualizationActive = true;
                    document.getElementById('vizBtn').textContent = '停止可视化';
                    lastDataTime = Date.now();
                };
                
                eventSource.onmessage = function(event) {
                    try {
                        const fftFrame = JSON.parse(event.data);
                        console.log('📡 收到SSE数据:', fftFrame);
                        
                        // 跳过非FFT数据
                        if (!fftFrame.data_compressed || fftFrame.type) {
                            console.log('⏭️ 跳过非FFT数据:', {
                                hasCompressed: !!fftFrame.data_compressed,
                                type: fftFrame.type
                            });
                            return;
                        }
                        
                        console.log('🗜️ 开始解压缩数据...');
                        // 解压缩FFT数据
                        const fftData = decompressFFTData(fftFrame.data_compressed);
                        if (!fftData) {
                            console.error('❌ 解压缩失败');
                            return;
                        }
                        console.log('✅ 解压缩成功, FFT数据长度:', fftData.length);
                        
                        // 绘制频谱
                        console.log('🎨 开始绘制频谱...');
                        drawSpectrum(fftData, fftFrame.sample_rate, fftFrame.fft_size);
                        console.log('✅ 频谱绘制完成');
                        
                        // 更新指标
                        updateMetrics(fftFrame);
                        
                        // 更新统计
                        frameCount++;
                        totalBytesReceived += fftFrame.data_size_bytes;
                        
                        // 记录事件
                        if (frameCount % 30 === 0) { // 每30帧记录一次
                            addEventLog(`接收第${frameCount}帧, 峰值: ${(fftFrame.peak_frequency_hz/1000).toFixed(1)}kHz`);
                        }
                        
                    } catch (e) {
                        console.error('❌ 处理FFT数据失败:', e, event.data);
                        addSystemLog('前端数据处理错误: ' + e.message, 'error');
                    }
                };
                
                eventSource.onerror = function() {
                    addSystemLog('数据流连接错误', 'error');
                    updateConnectionStatus('disconnected');
                    stopVisualization();
                };
            }
            
            // 停止可视化
            function stopVisualization() {
                if (eventSource) {
                    eventSource.close();
                    eventSource = null;
                }
                isVisualizationActive = false;
                updateConnectionStatus('disconnected');
                document.getElementById('vizBtn').textContent = '开始可视化';
                addSystemLog('数据流已断开', 'info');
            }
            
            // 绘制频谱数据
            function drawSpectrum(fftData, sampleRate, fftSize) {
                console.log('🎨 drawSpectrum 开始:', {
                    hasCtx: !!ctx,
                    dataLength: fftData.length,
                    sampleRate: sampleRate,
                    fftSize: fftSize
                });
                
                if (!ctx) {
                    console.error('❌ Canvas context 不存在');
                    return;
                }
                
                // 重绘背景
                drawBackground();
                
                // 计算频率步长
                const freqStep = sampleRate / fftSize / 1000; // kHz
                const maxFreqIndex = Math.min(fftData.length, Math.floor(MAX_FREQ_KHZ / freqStep));
                
                console.log('📊 频谱计算:', {
                    freqStep: freqStep,
                    maxFreqIndex: maxFreqIndex,
                    MAX_FREQ_KHZ: MAX_FREQ_KHZ
                });
                
                if (maxFreqIndex < 2) {
                    console.warn('⚠️ maxFreqIndex太小:', maxFreqIndex);
                    return;
                }
                
                // 绘制频谱线
                ctx.strokeStyle = '#00ff88';
                ctx.lineWidth = 2;
                ctx.beginPath();
                
                let firstPoint = true;
                for (let i = 0; i < maxFreqIndex; i++) {
                    const freq = i * freqStep;
                    const db = fftData[i];
                    
                    // 转换为画布坐标
                    const x = PADDING + (freq / MAX_FREQ_KHZ) * PLOT_WIDTH;
                    const y = PADDING + PLOT_HEIGHT - ((db - MIN_DB) / (MAX_DB - MIN_DB)) * PLOT_HEIGHT;
                    
                    if (firstPoint) {
                        ctx.moveTo(x, y);
                        firstPoint = false;
                    } else {
                        ctx.lineTo(x, y);
                    }
                }
                ctx.stroke();
                
                // 绘制填充区域
                ctx.fillStyle = 'rgba(0, 255, 136, 0.1)';
                ctx.beginPath();
                ctx.moveTo(PADDING, PADDING + PLOT_HEIGHT);
                
                for (let i = 0; i < maxFreqIndex; i++) {
                    const freq = i * freqStep;
                    const db = fftData[i];
                    const x = PADDING + (freq / MAX_FREQ_KHZ) * PLOT_WIDTH;
                    const y = PADDING + PLOT_HEIGHT - ((db - MIN_DB) / (MAX_DB - MIN_DB)) * PLOT_HEIGHT;
                    ctx.lineTo(x, y);
                }
                ctx.lineTo(PADDING + (maxFreqIndex * freqStep / MAX_FREQ_KHZ) * PLOT_WIDTH, PADDING + PLOT_HEIGHT);
                ctx.closePath();
                ctx.fill();
                
                // 绘制峰值标记
                const peakIndex = fftData.slice(0, maxFreqIndex).indexOf(Math.max(...fftData.slice(0, maxFreqIndex)));
                if (peakIndex > 0) {
                    const peakFreq = peakIndex * freqStep;
                    const peakDb = fftData[peakIndex];
                    const peakX = PADDING + (peakFreq / MAX_FREQ_KHZ) * PLOT_WIDTH;
                    const peakY = PADDING + PLOT_HEIGHT - ((peakDb - MIN_DB) / (MAX_DB - MIN_DB)) * PLOT_HEIGHT;
                    
                    // 峰值点
                    ctx.fillStyle = '#ff4444';
                    ctx.beginPath();
                    ctx.arc(peakX, peakY, 4, 0, 2 * Math.PI);
                    ctx.fill();
                    
                    // 峰值标签
                    ctx.fillStyle = '#ffffff';
                    ctx.font = '12px Arial';
                    ctx.textAlign = 'center';
                    ctx.fillText(`${peakFreq.toFixed(1)}kHz`, peakX, peakY - 10);
                }
            }
            
            // 更新指标显示
            function updateMetrics(fftFrame) {
                document.getElementById('currentFPS').textContent = fftFrame.fps.toFixed(1);
                document.getElementById('peakFreq').textContent = (fftFrame.peak_frequency_hz / 1000).toFixed(1);
                document.getElementById('peakMag').textContent = fftFrame.peak_magnitude_db.toFixed(1);
                document.getElementById('splLevel').textContent = fftFrame.spl_db.toFixed(1);
                
                // 计算数据速率
                const currentTime = Date.now();
                const timeDiff = (currentTime - lastDataTime) / 1000;
                if (timeDiff > 0) {
                    const dataRate = (fftFrame.data_size_bytes / timeDiff / 1024).toFixed(1);
                    document.getElementById('dataRate').textContent = dataRate;
                }
                lastDataTime = currentTime;
                
                // 压缩比
                const compression = (fftFrame.data_size_bytes / fftFrame.original_size_bytes * 100).toFixed(1);
                document.getElementById('compressionRatio').textContent = compression;
            }
            
            // 其他功能函数
            async function loadStatus() {
                try {
                    const response = await fetch('/api/status');
                    const status = await response.json();
                    document.getElementById('status').innerHTML = `
                        <div><strong>运行状态:</strong> ${status.is_running ? '🟢 运行中' : '🔴 已停止'}</div>
                        <div><strong>音频设备:</strong> ${status.audio_device_name || '未知'}</div>
                        <div><strong>连接客户端:</strong> ${status.connected_clients}</div>
                        <div><strong>已发送帧数:</strong> ${status.total_frames_sent}</div>
                        <div><strong>运行时间:</strong> ${Math.round(status.uptime_seconds)}秒</div>
                    `;
                } catch (e) {
                    addSystemLog('获取状态失败: ' + e.message, 'error');
                }
            }
            
            async function startSystem() {
                try {
                    const response = await fetch('/api/start', { method: 'POST' });
                    const result = await response.json();
                    addSystemLog('启动系统: ' + result.message, result.status === 'success' ? 'success' : 'error');
                    loadStatus();
                } catch (e) {
                    addSystemLog('启动失败: ' + e.message, 'error');
                }
            }
            
            async function stopSystem() {
                try {
                    stopVisualization(); // 先停止可视化
                    const response = await fetch('/api/stop', { method: 'POST' });
                    const result = await response.json();
                    addSystemLog('停止系统: ' + result.message, result.status === 'success' ? 'success' : 'error');
                    loadStatus();
                } catch (e) {
                    addSystemLog('停止失败: ' + e.message, 'error');
                }
            }
            
            function updateFPS(value) {
                document.getElementById('fpsValue').textContent = value;
                fetch('/api/config/fps', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(parseInt(value))
                });
            }
            
            function exportData() {
                const data = {
                    timestamp: new Date().toISOString(),
                    frameCount: frameCount,
                    totalBytes: totalBytesReceived,
                    compressionStats: document.getElementById('compressionRatio').textContent
                };
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'ultrasonic_data_' + Date.now() + '.json';
                a.click();
            }
            
            // 页面初始化
            document.addEventListener('DOMContentLoaded', function() {
                initSpectrumCanvas();
                loadStatus();
                setInterval(loadStatus, 5000);
                
                // 页面卸载时清理
                window.addEventListener('beforeunload', function() {
                    if (eventSource) {
                        eventSource.close();
                    }
                });
            });
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        log_level=Config.LOG_LEVEL.lower()
    )