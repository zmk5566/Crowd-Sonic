"""
跨平台UAC音频设备捕获模块
支持高采样率（384kHz）实时音频流处理
"""
import sounddevice as sd
import numpy as np
import threading
import queue
from typing import Optional, Callable, List, Dict
import yaml


class AudioCapture:
    def __init__(self, config_path: str = "config/default.yaml"):
        """初始化音频捕获器"""
        self.config = self._load_config(config_path)
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.stream = None
        self.callback_func = None
        
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            # 默认配置
            return {
                'audio': {
                    'sample_rate': 384000,
                    'channels': 1,
                    'buffer_size': 1024,
                    'device_name': None
                }
            }
    
    @staticmethod
    def list_audio_devices() -> List[Dict]:
        """列出所有可用的音频设备"""
        devices = []
        device_list = sd.query_devices()
        
        for i, device in enumerate(device_list):
            if device['max_input_channels'] > 0:  # 只显示输入设备
                devices.append({
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate'],
                    'hostapi': sd.query_hostapis(device['hostapi'])['name']
                })
        
        return devices
    
    def find_uac_device(self) -> Optional[int]:
        """自动查找UAC设备"""
        devices = self.list_audio_devices()
        
        # 优先查找支持高采样率的设备
        target_sample_rate = self.config['audio']['sample_rate']
        
        for device in devices:
            try:
                # 测试设备是否支持目标采样率
                sd.check_input_settings(
                    device=device['index'],
                    channels=self.config['audio']['channels'],
                    samplerate=target_sample_rate
                )
                # 如果支持，优先选择名称包含UAC相关关键词的设备
                device_name = device['name'].lower()
                if any(keyword in device_name for keyword in ['uac', 'usb', 'audio']):
                    return device['index']
                    
            except sd.PortAudioError:
                continue
                
        # 如果没有找到UAC设备，返回第一个支持高采样率的设备
        for device in devices:
            try:
                sd.check_input_settings(
                    device=device['index'],
                    channels=self.config['audio']['channels'], 
                    samplerate=target_sample_rate
                )
                return device['index']
            except sd.PortAudioError:
                continue
                
        return None
    
    def _audio_callback(self, indata, frames, time, status):
        """音频流回调函数"""
        if status:
            print(f"Audio callback status: {status}")
            
        # 将音频数据放入队列
        audio_data = indata.copy()
        try:
            self.audio_queue.put_nowait(audio_data)
        except queue.Full:
            # 队列满时丢弃最旧的数据
            try:
                self.audio_queue.get_nowait()
                self.audio_queue.put_nowait(audio_data)
            except queue.Empty:
                pass
    
    def start_stream(self, device_index: Optional[int] = None, 
                    callback: Optional[Callable] = None) -> bool:
        """启动音频流"""
        try:
            if device_index is None:
                device_index = self.find_uac_device()
                
            if device_index is None:
                print("未找到合适的UAC设备")
                return False
            
            self.callback_func = callback
            
            # 配置音频流参数
            audio_config = self.config['audio']
            
            self.stream = sd.InputStream(
                device=device_index,
                channels=audio_config['channels'],
                samplerate=audio_config['sample_rate'],
                blocksize=audio_config['buffer_size'],
                callback=self._audio_callback,
                dtype=np.float32
            )
            
            self.stream.start()
            self.is_recording = True
            
            # 获取实际设备信息
            device_info = sd.query_devices(device_index)
            print(f"已连接设备: {device_info['name']}")
            print(f"采样率: {audio_config['sample_rate']} Hz")
            print(f"通道数: {audio_config['channels']}")
            
            return True
            
        except Exception as e:
            print(f"启动音频流失败: {e}")
            return False
    
    def stop_stream(self):
        """停止音频流"""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.is_recording = False
        
        # 清空队列
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
    
    def get_audio_data(self) -> Optional[np.ndarray]:
        """获取最新的音频数据"""
        try:
            return self.audio_queue.get_nowait()
        except queue.Empty:
            return None
    
    def get_device_info(self, device_index: int) -> Dict:
        """获取指定设备的详细信息"""
        device = sd.query_devices(device_index)
        hostapi = sd.query_hostapis(device['hostapi'])
        
        return {
            'name': device['name'],
            'channels': device['max_input_channels'],
            'sample_rate': device['default_samplerate'],
            'hostapi': hostapi['name'],
            'latency': device['default_low_input_latency']
        }
    
    def get_supported_sample_rates(self, device_index: int, channels: int = 1) -> List[int]:
        """获取设备支持的采样率列表"""
        common_sample_rates = [8000, 11025, 16000, 22050, 32000, 44100, 48000, 
                             88200, 96000, 176400, 192000, 352800, 384000, 768000]
        
        supported_rates = []
        
        for sample_rate in common_sample_rates:
            try:
                # 测试设备是否支持该采样率
                sd.check_input_settings(
                    device=device_index,
                    channels=channels,
                    samplerate=sample_rate
                )
                supported_rates.append(sample_rate)
            except sd.PortAudioError:
                # 不支持该采样率
                continue
                
        return supported_rates


if __name__ == "__main__":
    # 测试代码
    capture = AudioCapture()
    
    print("可用音频设备:")
    devices = capture.list_audio_devices()
    for device in devices:
        print(f"  {device['index']}: {device['name']} "
              f"({device['channels']}ch, {device['sample_rate']}Hz, {device['hostapi']})")
    
    print(f"\n寻找UAC设备...")
    uac_device = capture.find_uac_device()
    if uac_device is not None:
        print(f"找到UAC设备: {uac_device}")
        device_info = capture.get_device_info(uac_device)
        print(f"设备详情: {device_info}")
        
        # 显示支持的采样率
        supported_rates = capture.get_supported_sample_rates(uac_device)
        print(f"支持的采样率: {supported_rates}")
    else:
        print("未找到合适的UAC设备")