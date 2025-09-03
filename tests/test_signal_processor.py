"""
信号处理模块测试
"""
import pytest
import numpy as np
import sys
import os

# 添加src路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from signal_processor import SignalProcessor


class TestSignalProcessor:
    
    def setup_method(self):
        """测试前设置"""
        self.processor = SignalProcessor()
    
    def test_initialization(self):
        """测试初始化"""
        assert self.processor is not None
        assert self.processor.sample_rate == 384000
        assert self.processor.fft_size == 2048
        assert len(self.processor.window) == self.processor.fft_size
        assert len(self.processor.frequencies) == self.processor.fft_size // 2 + 1
    
    def test_window_functions(self):
        """测试不同窗函数"""
        # 测试不同的窗函数
        window_types = ['hann', 'hamming', 'blackman', 'kaiser', 'rect']
        
        for window_type in window_types:
            processor = SignalProcessor()
            processor.window_type = window_type
            window = processor._create_window()
            
            assert len(window) == processor.fft_size
            assert np.all(np.isfinite(window))
    
    def test_process_audio_chunk(self):
        """测试音频块处理"""
        # 生成测试信号
        duration = 0.1
        t = np.linspace(0, duration, int(self.processor.sample_rate * duration))
        
        # 1kHz正弦波
        test_signal = np.sin(2 * np.pi * 1000 * t)
        
        # 处理信号
        frequencies, magnitude = self.processor.process_audio_chunk(test_signal)
        
        # 检查输出
        assert len(frequencies) == self.processor.fft_size // 2 + 1
        assert len(magnitude) == len(frequencies)
        assert np.all(np.isfinite(magnitude))
        
        # 检查峰值应该在1kHz附近
        peak_idx = np.argmax(magnitude)
        peak_freq = frequencies[peak_idx]
        assert 950 <= peak_freq <= 1050  # 允许一定误差
    
    def test_multi_frequency_signal(self):
        """测试多频率信号"""
        duration = 0.1
        t = np.linspace(0, duration, int(self.processor.sample_rate * duration))
        
        # 混合信号：1kHz + 25kHz + 50kHz
        test_signal = (np.sin(2 * np.pi * 1000 * t) +
                      0.5 * np.sin(2 * np.pi * 25000 * t) +
                      0.3 * np.sin(2 * np.pi * 50000 * t))
        
        frequencies, magnitude = self.processor.process_audio_chunk(test_signal)
        
        # 应该能检测到所有三个频率的峰值
        # 找出幅度较高的频率点
        peaks = []
        for i in range(1, len(magnitude) - 1):
            if (magnitude[i] > magnitude[i-1] and 
                magnitude[i] > magnitude[i+1] and 
                magnitude[i] > -20):  # 阈值
                peaks.append(frequencies[i])
        
        # 应该检测到接近目标频率的峰值
        target_freqs = [1000, 25000, 50000]
        detected_count = 0
        for target in target_freqs:
            for peak in peaks:
                if abs(peak - target) < target * 0.05:  # 5%误差
                    detected_count += 1
                    break
        
        assert detected_count >= 2  # 至少检测到2个频率
    
    def test_spectrum_features(self):
        """测试频谱特征计算"""
        duration = 0.1
        t = np.linspace(0, duration, int(self.processor.sample_rate * duration))
        
        # 25kHz信号（超声波）
        test_signal = np.sin(2 * np.pi * 25000 * t)
        
        frequencies, magnitude = self.processor.process_audio_chunk(test_signal)
        features = self.processor.calculate_spectrum_features(frequencies, magnitude)
        
        # 检查特征完整性
        required_features = [
            'total_power', 'peak_frequency', 'peak_magnitude',
            'spectral_centroid', 'spectral_bandwidth', 'spectral_rolloff',
            'ultrasonic_power', 'ultrasonic_ratio'
        ]
        
        for feature in required_features:
            assert feature in features
            assert np.isfinite(features[feature])
        
        # 峰值频率应该接近25kHz
        assert 24000 <= features['peak_frequency'] <= 26000
        
        # 超声波比例应该很高（25kHz > 20kHz）
        assert features['ultrasonic_ratio'] > 0.8
    
    def test_frequency_filter(self):
        """测试频率滤波"""
        duration = 0.1
        t = np.linspace(0, duration, int(self.processor.sample_rate * duration))
        test_signal = np.sin(2 * np.pi * 10000 * t)
        
        frequencies, magnitude = self.processor.process_audio_chunk(test_signal)
        
        # 滤波到5-15kHz范围
        freq_range = (5000, 15000)
        filtered_freq, filtered_mag = self.processor.apply_frequency_filter(
            frequencies, magnitude, freq_range
        )
        
        # 检查滤波结果
        assert len(filtered_freq) <= len(frequencies)
        assert len(filtered_mag) == len(filtered_freq)
        assert np.all(filtered_freq >= freq_range[0])
        assert np.all(filtered_freq <= freq_range[1])
    
    def test_frequency_bands(self):
        """测试频段分析"""
        duration = 0.1
        t = np.linspace(0, duration, int(self.processor.sample_rate * duration))
        
        # 多频段信号
        test_signal = (np.sin(2 * np.pi * 100 * t) +      # bass
                      np.sin(2 * np.pi * 2000 * t) +      # mid
                      np.sin(2 * np.pi * 10000 * t) +     # presence
                      np.sin(2 * np.pi * 30000 * t))      # ultrasonic
        
        frequencies, magnitude = self.processor.process_audio_chunk(test_signal)
        bands = self.processor.get_frequency_bands(frequencies, magnitude)
        
        # 检查频段信息完整性
        expected_bands = [
            'bass', 'mid', 'presence', 'ultrasonic_low'
        ]
        
        for band in expected_bands:
            assert band in bands
            assert 'power' in bands[band]
            assert 'freq_range' in bands[band]
            assert 'peak_freq' in bands[band]
            assert bands[band]['power'] > 0  # 应该有能量
    
    def test_overlapped_processing(self):
        """测试重叠处理"""
        # 生成较长的测试信号
        duration = 0.5
        t = np.linspace(0, duration, int(self.processor.sample_rate * duration))
        test_signal = np.sin(2 * np.pi * 5000 * t)
        
        # 分块处理
        hop_size = self.processor.hop_size
        results = []
        
        for i in range(0, len(test_signal) - hop_size, hop_size):
            chunk = test_signal[i:i + hop_size]
            result = self.processor.process_overlapped_chunk(chunk)
            if result is not None:
                results.append(result)
        
        # 应该有多个处理结果
        assert len(results) > 1
        
        # 每个结果都应该是有效的
        for frequencies, magnitude in results:
            assert len(frequencies) == len(magnitude)
            assert np.all(np.isfinite(magnitude))