"""
实时信号处理模块
处理高采样率音频数据，进行FFT分析和频谱计算
"""
import numpy as np
from scipy import signal
from typing import Optional, Tuple
import yaml


class SignalProcessor:
    def __init__(self, config_path: str = "config/default.yaml"):
        """初始化信号处理器"""
        self.config = self._load_config(config_path)
        self.sample_rate = self.config['audio']['sample_rate']
        self.fft_size = self.config['processing']['fft_size']
        self.overlap = self.config['processing']['overlap']
        self.window_type = self.config['processing']['window_type']
        
        # 创建窗函数
        self.window = self._create_window()
        
        # 用于重叠处理的缓冲区
        self.overlap_size = int(self.fft_size * self.overlap)
        self.hop_size = self.fft_size - self.overlap_size
        self.buffer = np.zeros(self.overlap_size, dtype=np.float32)
        
        # 频率轴
        self.frequencies = np.fft.rfftfreq(self.fft_size, 1/self.sample_rate)
        
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {
                'audio': {'sample_rate': 384000},
                'processing': {
                    'fft_size': 2048,
                    'overlap': 0.5,
                    'window_type': 'hann'
                }
            }
    
    def _create_window(self) -> np.ndarray:
        """创建窗函数"""
        if self.window_type == 'hann':
            return np.hanning(self.fft_size)
        elif self.window_type == 'hamming':
            return np.hamming(self.fft_size)
        elif self.window_type == 'blackman':
            return np.blackman(self.fft_size)
        elif self.window_type == 'kaiser':
            return np.kaiser(self.fft_size, beta=8.6)
        else:
            return np.ones(self.fft_size)  # 矩形窗
    
    def process_audio_chunk(self, audio_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        处理音频块，返回频率和幅度谱
        
        Args:
            audio_data: 音频数据 (shape: [samples, channels] 或 [samples])
            
        Returns:
            frequencies: 频率轴
            magnitude: 幅度谱
        """
        # 如果是多通道，取第一通道
        if audio_data.ndim > 1:
            audio_data = audio_data[:, 0]
            
        # 确保数据长度足够
        if len(audio_data) < self.fft_size:
            # 零填充
            padded_data = np.zeros(self.fft_size)
            padded_data[:len(audio_data)] = audio_data
            audio_data = padded_data
        elif len(audio_data) > self.fft_size:
            # 截取最新的数据
            audio_data = audio_data[-self.fft_size:]
        
        # 应用窗函数
        windowed_data = audio_data * self.window
        
        # FFT计算
        fft_result = np.fft.rfft(windowed_data)
        
        # 计算幅度谱（dB）
        magnitude = 20 * np.log10(np.abs(fft_result) + 1e-10)
        
        return self.frequencies, magnitude
    
    def process_overlapped_chunk(self, audio_data: np.ndarray) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        使用重叠处理音频块
        
        Args:
            audio_data: 新的音频数据
            
        Returns:
            frequencies, magnitude 或 None（如果数据不足）
        """
        if len(audio_data) < self.hop_size:
            return None
            
        # 取最新的hop_size个样本
        new_samples = audio_data[-self.hop_size:].flatten()
        
        # 与缓冲区拼接
        frame = np.concatenate([self.buffer, new_samples])
        
        # 更新缓冲区
        self.buffer = frame[-self.overlap_size:]
        
        # 处理完整帧
        return self.process_audio_chunk(frame)
    
    def calculate_spectrum_features(self, frequencies: np.ndarray, 
                                  magnitude: np.ndarray) -> dict:
        """
        计算频谱特征
        
        Args:
            frequencies: 频率轴
            magnitude: 幅度谱
            
        Returns:
            features: 包含各种频谱特征的字典
        """
        # 线性幅度
        linear_magnitude = 10 ** (magnitude / 20)
        
        # 总功率
        total_power = np.sum(linear_magnitude ** 2)
        
        # 峰值频率
        peak_idx = np.argmax(magnitude)
        peak_frequency = frequencies[peak_idx]
        peak_magnitude = magnitude[peak_idx]
        
        # 重心频率（质心）
        centroid = np.sum(frequencies * linear_magnitude) / np.sum(linear_magnitude)
        
        # 频谱带宽
        bandwidth = np.sqrt(np.sum(((frequencies - centroid) ** 2) * linear_magnitude) / 
                           np.sum(linear_magnitude))
        
        # 频谱滚降点（95%能量）
        cumsum = np.cumsum(linear_magnitude ** 2)
        rolloff_idx = np.where(cumsum >= 0.95 * total_power)[0]
        rolloff_freq = frequencies[rolloff_idx[0]] if len(rolloff_idx) > 0 else frequencies[-1]
        
        # 超声波频段功率（20kHz以上）
        ultrasonic_mask = frequencies >= 20000
        ultrasonic_power = np.sum(linear_magnitude[ultrasonic_mask] ** 2) if np.any(ultrasonic_mask) else 0
        ultrasonic_ratio = ultrasonic_power / total_power if total_power > 0 else 0
        
        return {
            'total_power': total_power,
            'peak_frequency': peak_frequency,
            'peak_magnitude': peak_magnitude,
            'spectral_centroid': centroid,
            'spectral_bandwidth': bandwidth,
            'spectral_rolloff': rolloff_freq,
            'ultrasonic_power': ultrasonic_power,
            'ultrasonic_ratio': ultrasonic_ratio
        }
    
    def apply_frequency_filter(self, frequencies: np.ndarray, magnitude: np.ndarray,
                             freq_range: Tuple[float, float]) -> Tuple[np.ndarray, np.ndarray]:
        """
        应用频率范围滤波
        
        Args:
            frequencies: 频率轴
            magnitude: 幅度谱
            freq_range: 频率范围 (min_freq, max_freq)
            
        Returns:
            filtered_frequencies, filtered_magnitude
        """
        min_freq, max_freq = freq_range
        mask = (frequencies >= min_freq) & (frequencies <= max_freq)
        return frequencies[mask], magnitude[mask]
    
    def get_frequency_bands(self, frequencies: np.ndarray, magnitude: np.ndarray) -> dict:
        """
        获取不同频段的信息
        
        Returns:
            bands: 包含各频段信息的字典
        """
        bands = {
            'sub_bass': (20, 60),
            'bass': (60, 250),
            'low_mid': (250, 1000),
            'mid': (1000, 4000),
            'high_mid': (4000, 8000),
            'presence': (8000, 12000),
            'brilliance': (12000, 20000),
            'ultrasonic_low': (20000, 50000),
            'ultrasonic_mid': (50000, 100000),
            'ultrasonic_high': (100000, 200000)
        }
        
        band_powers = {}
        linear_magnitude = 10 ** (magnitude / 20)
        
        for band_name, (min_freq, max_freq) in bands.items():
            mask = (frequencies >= min_freq) & (frequencies <= max_freq)
            if np.any(mask):
                band_power = np.sum(linear_magnitude[mask] ** 2)
                band_powers[band_name] = {
                    'power': band_power,
                    'freq_range': (min_freq, max_freq),
                    'peak_freq': frequencies[mask][np.argmax(magnitude[mask])] if np.any(mask) else 0,
                    'peak_magnitude': np.max(magnitude[mask]) if np.any(mask) else -np.inf
                }
            else:
                band_powers[band_name] = {
                    'power': 0,
                    'freq_range': (min_freq, max_freq),
                    'peak_freq': 0,
                    'peak_magnitude': -np.inf
                }
        
        return band_powers


if __name__ == "__main__":
    # 测试代码
    processor = SignalProcessor()
    
    # 生成测试信号（包含多个频率成分）
    duration = 0.1  # 100ms
    t = np.linspace(0, duration, int(processor.sample_rate * duration))
    
    # 混合信号：1kHz + 25kHz + 50kHz（超声波）
    test_signal = (np.sin(2 * np.pi * 1000 * t) +
                  0.5 * np.sin(2 * np.pi * 25000 * t) +
                  0.3 * np.sin(2 * np.pi * 50000 * t))
    
    # 处理信号
    frequencies, magnitude = processor.process_audio_chunk(test_signal)
    
    # 计算特征
    features = processor.calculate_spectrum_features(frequencies, magnitude)
    
    print(f"信号特征:")
    print(f"  峰值频率: {features['peak_frequency']:.2f} Hz")
    print(f"  频谱质心: {features['spectral_centroid']:.2f} Hz") 
    print(f"  频谱带宽: {features['spectral_bandwidth']:.2f} Hz")
    print(f"  超声波比例: {features['ultrasonic_ratio']:.3f}")
    
    # 频段分析
    bands = processor.get_frequency_bands(frequencies, magnitude)
    print(f"\n各频段功率:")
    for band_name, info in bands.items():
        if info['power'] > 1e-6:
            print(f"  {band_name}: {info['power']:.6f} (峰值: {info['peak_freq']:.0f} Hz)")