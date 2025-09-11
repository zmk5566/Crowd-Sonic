#!/usr/bin/env python3
"""
控制API端点
提供配置管理和系统控制功能
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from models import StreamConfig, AudioConfig, SystemStatus, ControlResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["control"])

# 全局组件引用 (将在main.py中设置)
audio_capture = None
fft_processor = None
data_streamer = None
stream_config = None
audio_config = None

def set_components(capture, processor, streamer, s_config, a_config):
    """设置全局组件引用"""
    global audio_capture, fft_processor, data_streamer, stream_config, audio_config
    audio_capture = capture
    fft_processor = processor
    data_streamer = streamer
    stream_config = s_config
    audio_config = a_config

@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """获取系统状态"""
    if not all([audio_capture, fft_processor, data_streamer]):
        raise HTTPException(status_code=503, detail="系统组件未初始化")
    
    # 合并各组件的统计信息
    audio_stats = audio_capture.get_stats()
    fft_stats = fft_processor.get_stats()
    stream_stats = data_streamer.get_stats()
    
    return SystemStatus(
        is_running=audio_stats["is_running"],
        current_fps=stream_stats.get("current_fps", 0.0),
        connected_clients=stream_stats.get("connected_clients", 0),
        total_frames_sent=stream_stats.get("total_frames_sent", 0),
        total_bytes_sent=stream_stats.get("total_bytes_sent", 0),
        uptime_seconds=stream_stats.get("uptime_seconds", 0.0),
        audio_device_name=audio_stats.get("device_name"),
        last_error=audio_stats.get("last_error")
    )

@router.post("/start", response_model=ControlResponse)
async def start_system():
    """启动音频采集和数据流"""
    if not audio_capture:
        raise HTTPException(status_code=503, detail="音频采集组件未初始化")
    
    try:
        success = audio_capture.start()
        if success:
            logger.info("系统启动成功")
            return ControlResponse.success("系统已启动")
        else:
            return ControlResponse.error("启动失败，请检查音频设备")
    except Exception as e:
        logger.error(f"启动系统失败: {e}")
        return ControlResponse.error(f"启动失败: {str(e)}")

@router.post("/stop", response_model=ControlResponse)
async def stop_system():
    """停止音频采集和数据流"""
    if not audio_capture:
        raise HTTPException(status_code=503, detail="音频采集组件未初始化")
    
    try:
        audio_capture.stop()
        logger.info("系统已停止")
        return ControlResponse.success("系统已停止")
    except Exception as e:
        logger.error(f"停止系统失败: {e}")
        return ControlResponse.error(f"停止失败: {str(e)}")

@router.get("/config/stream", response_model=StreamConfig)
async def get_stream_config():
    """获取流配置"""
    if not stream_config:
        raise HTTPException(status_code=503, detail="流配置未初始化")
    return stream_config

@router.post("/config/stream", response_model=ControlResponse)
async def update_stream_config(config: StreamConfig):
    """更新流配置"""
    if not data_streamer:
        raise HTTPException(status_code=503, detail="数据流组件未初始化")
    
    try:
        data_streamer.update_config(config)
        # 更新全局配置
        global stream_config
        stream_config = config
        
        logger.info(f"流配置已更新: FPS={config.target_fps}")
        return ControlResponse.success(f"配置已更新，目标FPS: {config.target_fps}")
    except Exception as e:
        logger.error(f"更新流配置失败: {e}")
        return ControlResponse.error(f"配置更新失败: {str(e)}")

@router.get("/config/audio", response_model=AudioConfig)
async def get_audio_config():
    """获取音频配置"""
    if not audio_config:
        raise HTTPException(status_code=503, detail="音频配置未初始化")
    return audio_config

# FPS端点已移动到 /api/config/fps (在api/config.py中)
# 保留旧的端点作为兼容性支持，但使用query参数
@router.post("/config/fps_legacy", response_model=ControlResponse)  
async def set_fps_legacy(fps: int):
    """快速设置目标FPS (遗留端点)"""
    if not (5 <= fps <= 60):
        raise HTTPException(status_code=400, detail="FPS必须在5-60之间")
    
    if not data_streamer:
        raise HTTPException(status_code=503, detail="数据流组件未初始化")
    
    try:
        # 更新配置
        global stream_config
        stream_config.target_fps = fps
        data_streamer.update_config(stream_config)
        
        logger.info(f"FPS已设置为: {fps}")
        return ControlResponse.success(f"FPS已设置为: {fps}")
    except Exception as e:
        logger.error(f"设置FPS失败: {e}")
        return ControlResponse.error(f"设置FPS失败: {str(e)}")

@router.get("/stats/detailed")
async def get_detailed_stats():
    """获取详细的统计信息"""
    if not all([audio_capture, fft_processor, data_streamer]):
        raise HTTPException(status_code=503, detail="系统组件未初始化")
    
    return {
        "timestamp": __import__('time').time() * 1000,
        "audio": audio_capture.get_stats(),
        "fft": fft_processor.get_stats(), 
        "stream": data_streamer.get_stats(),
        "config": {
            "stream": stream_config.dict() if stream_config else None,
            "audio": audio_config.dict() if audio_config else None
        }
    }

@router.get("/devices")
async def list_audio_devices():
    """列出可用的音频设备"""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        
        input_devices = []
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices.append({
                    "id": i,
                    "name": device['name'],
                    "max_channels": device['max_input_channels'],
                    "default_samplerate": device['default_samplerate'],
                    "is_default": i == sd.default.device[0] if hasattr(sd.default, 'device') else False
                })
        
        return {
            "devices": input_devices,
            "timestamp": __import__('time').time() * 1000
        }
    except Exception as e:
        logger.error(f"获取音频设备列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取设备列表失败: {str(e)}")

@router.post("/test/compression")
async def test_compression_performance():
    """测试压缩性能"""
    if not fft_processor:
        raise HTTPException(status_code=503, detail="FFT处理器未初始化")
    
    try:
        import numpy as np
        import time
        
        # 生成测试数据
        test_data = np.random.random(4097).astype(np.float32) * 100 - 50  # 模拟FFT数据
        
        # 测试压缩
        start_time = time.time()
        compressed, compressed_size, original_size = fft_processor.compress_fft_data(test_data)
        compression_time = (time.time() - start_time) * 1000
        
        compression_ratio = compressed_size / original_size
        
        return {
            "original_size_bytes": original_size,
            "compressed_size_bytes": compressed_size,
            "compression_ratio": compression_ratio,
            "compression_time_ms": compression_time,
            "data_sample": compressed[:100] + "..." if len(compressed) > 100 else compressed,
            "timestamp": time.time() * 1000
        }
    except Exception as e:
        logger.error(f"压缩性能测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")