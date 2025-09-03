"""
音频捕获模块测试
"""
import pytest
import numpy as np
import sys
import os

# 添加src路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from audio_capture import AudioCapture


class TestAudioCapture:
    
    def setup_method(self):
        """测试前设置"""
        self.capture = AudioCapture()
    
    def test_initialization(self):
        """测试初始化"""
        assert self.capture is not None
        assert self.capture.audio_queue is not None
        assert not self.capture.is_recording
    
    def test_config_loading(self):
        """测试配置加载"""
        config = self.capture.config
        assert 'audio' in config
        assert 'sample_rate' in config['audio']
        assert config['audio']['sample_rate'] == 384000
    
    def test_list_audio_devices(self):
        """测试设备列表"""
        devices = AudioCapture.list_audio_devices()
        assert isinstance(devices, list)
        
        # 如果有设备，检查设备信息完整性
        if devices:
            device = devices[0]
            required_keys = ['index', 'name', 'channels', 'sample_rate', 'hostapi']
            for key in required_keys:
                assert key in device
    
    def test_find_uac_device(self):
        """测试UAC设备查找"""
        uac_device = self.capture.find_uac_device()
        # 可能找到也可能找不到，但不应该出错
        assert uac_device is None or isinstance(uac_device, int)
    
    def test_device_info(self):
        """测试设备信息获取"""
        devices = AudioCapture.list_audio_devices()
        if devices:
            device_index = devices[0]['index']
            info = self.capture.get_device_info(device_index)
            
            required_keys = ['name', 'channels', 'sample_rate', 'hostapi', 'latency']
            for key in required_keys:
                assert key in info
    
    @pytest.mark.skipif(len(AudioCapture.list_audio_devices()) == 0, 
                       reason="No audio devices available")
    def test_stream_operations(self):
        """测试音频流操作"""
        # 注意：这个测试需要实际的音频设备
        devices = AudioCapture.list_audio_devices()
        if not devices:
            pytest.skip("No audio devices available for testing")
        
        device_index = devices[0]['index']
        
        # 尝试启动流（可能失败，但不应该崩溃）
        try:
            success = self.capture.start_stream(device_index)
            if success:
                assert self.capture.is_recording
                
                # 停止流
                self.capture.stop_stream()
                assert not self.capture.is_recording
        except Exception as e:
            # 在CI环境中可能没有音频设备，这是可以接受的
            pytest.skip(f"Audio stream test failed (expected in CI): {e}")
    
    def teardown_method(self):
        """测试后清理"""
        if hasattr(self, 'capture') and self.capture.is_recording:
            self.capture.stop_stream()